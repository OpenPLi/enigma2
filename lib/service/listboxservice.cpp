#include <lib/base/wrappers.h>
#include <lib/service/listboxservice.h>
#include <lib/service/service.h>
#include <lib/gdi/font.h>
#include <lib/gdi/epng.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
#include <lib/nav/core.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>
#include <ctype.h>
#include <string>
#include <algorithm>
#include <lib/base/estring.h>

ePyObject eListboxServiceContent::m_GetPiconNameFunc;

std::string toLower(std::string& data) {
	std::string data_tmp = data;
	std::transform(data_tmp.begin(), data_tmp.end(), data_tmp.begin(), tolower);
    return data_tmp;
}

// Next two functions are used for finding correct recording in case of dynamic iptv service url

bool compareServices(const eServiceReference &ref1, const eServiceReference &ref2, bool alternativeMatching) {
	std::vector<std::string> ref_split = split(ref1.toString(), ":");
	std::vector<std::string> s_split = split(ref2.toString(), ":");

	if (ref_split[1] == "7" || s_split[1] == "7") {
		return ref1 == ref2;
	}

	std::vector<std::string> ref_split_r(ref_split.begin(), ref_split.begin() + 10);
	std::string ref_s;
	join_str(ref_split_r, ':', ref_s);

	std::vector<std::string> s_split_r(s_split.begin(), s_split.begin() + 10);
	std::string s_s;
	join_str(s_split_r, ':', s_s);

	if (!alternativeMatching) {
		if (ref1 == ref2) return true;
	} else {
		if (ref_s == s_s) return true;
	}
	// If "127.0.0.1" is in the service reference this is probably a stream relay
	// so use partial matching logic
	if (ref2.toString().find("127.0.0.1") != std::string::npos) {
		std::string url_sr = s_split[s_split.size() - 2];
		std::vector<std::string> sr_split = split(url_sr, "/");
		std::string ref_orig = sr_split.back();
		ref_orig = replace_all(ref_orig, "%3a", ":");
		return ref1.toString() == ref_orig;
	}

	return false;
}

void eListboxServiceContent::addService(const eServiceReference &service, bool beforeCurrent)
{
	if (beforeCurrent && m_size)
		m_list.insert(m_cursor, service);
	else
		m_list.push_back(service);
	if (m_size++)
	{
		++m_cursor_number;
		if (m_listbox)
			m_listbox->entryAdded(cursorResolve(m_cursor_number-1));
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number=0;
		m_listbox->entryAdded(0);
	}
}

void eListboxServiceContent::removeCurrent()
{
	if (m_size && m_listbox)
	{
		if (m_cursor_number == --m_size)
		{
			m_list.erase(m_cursor--);
			if (m_size)
			{
				--m_cursor_number;
				m_listbox->entryRemoved(cursorResolve(m_cursor_number+1));
			}
			else
				m_listbox->entryRemoved(cursorResolve(m_cursor_number));
		}
		else
		{
			m_list.erase(m_cursor++);
			m_listbox->entryRemoved(cursorResolve(m_cursor_number));
		}

		// prevent a crash in case we are deleting an marked item while in move mode
		m_current_marked = false;
	}
}

void eListboxServiceContent::FillFinished()
{
	m_size = m_list.size();
	m_size_visible = cursorResolve(m_size - 1) + 1;
	cursorHome();

	if (m_listbox)
		m_listbox->entryReset();
}

void eListboxServiceContent::setRoot(const eServiceReference &root, bool justSet)
{
	m_list.clear();
	m_cursor = m_list.end();
	m_root = root;

	if (justSet)
	{
		m_lst=0;
		return;
	}
	ASSERT(m_service_center);

	if (m_service_center->list(m_root, m_lst))
		eDebug("[eListboxServiceContent] no list available!");
	else if (m_lst->getContent(m_list))
		eDebug("[eListboxServiceContent] getContent failed");

	FillFinished();
}

bool eListboxServiceContent::setCurrent(const eServiceReference &ref)
{
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
	{
		if ( *i == ref )
		{
			m_cursor = i;
			m_cursor_number = index;
			if (m_listbox)
			{
				m_listbox->moveSelectionTo(cursorResolve(index));
				return true;
			}
			break;
		}
	}
	return false;
}

void eListboxServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_cursor;
	else
		ref = eServiceReference();
}

void eListboxServiceContent::getPrev(eServiceReference &ref)
{
	list::iterator cursor;

	if (cursorValid())
	{
		cursor = m_cursor;

		if (cursor == m_list.begin())
			cursor = m_list.end();

		ref = *(--cursor);
	}
	else
		ref = eServiceReference();
}

void eListboxServiceContent::getNext(eServiceReference &ref)
{
	list::iterator cursor;

	if (cursorValid())
	{
		cursor = m_cursor;

		cursor++;

		if (cursor == m_list.end())
			cursor = m_list.begin();

		ref = *(cursor);
	}
	else
		ref = eServiceReference();
}

PyObject *eListboxServiceContent::getList()
{
	ePyObject result = PyList_New(m_list.size());
	int pos=0;
	for (list::iterator it(m_list.begin()); it != m_list.end(); ++it)
	{
		PyList_SET_ITEM(result, pos++, NEW_eServiceReference(*it));
	}
	return result;
}

int eListboxServiceContent::getNextBeginningWithChar(char c)
{
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
	{
		std::string text;
		ePtr<iStaticServiceInformation> service_info;
		if (m_service_center->info(*i, service_info))
		{
			continue; // failed to find service handler
		}
		service_info->getName(*i, text);

		int idx=0;
		int len=text.length();
		while ( idx <= len )
		{
			char cc = text[idx++];
			if (isprint(cc))
			{
				if (cc == c)
					return index;
				break;
			}
		}
	}
	return 0;
}

int eListboxServiceContent::getPrevMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;
	while (index) // Find marker for this section
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	//eDebug("[eListboxServiceContent] prevMarkerIndex= %i; curSelIndex= %i; index= %i", cursorResolve(prevMarkerIndex), cursorResolve(m_cursor_number), index);

	// if currently selected service is not the first after the marker found - return the found marker index
	if (cursorResolve(index) + 1 != cursorResolve(m_cursor_number)) return cursorResolve(index);


	while (index)
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	return cursorResolve(index);
}

int eListboxServiceContent::getNextMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;
	while (index < (m_size-1))
	{
		++i;
		++index;

		if (i->flags == eServiceReference::isMarker)
			break;
	}
	return cursorResolve(index);
}

void eListboxServiceContent::initMarked()
{
	m_marked.clear();
}

void eListboxServiceContent::addMarked(const eServiceReference &ref)
{
	m_marked.insert(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

void eListboxServiceContent::removeMarked(const eServiceReference &ref)
{
	m_marked.erase(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

int eListboxServiceContent::isMarked(const eServiceReference &ref)
{
	return m_marked.find(ref) != m_marked.end();
}

void eListboxServiceContent::markedQueryStart()
{
	m_marked_iterator = m_marked.begin();
}

int eListboxServiceContent::markedQueryNext(eServiceReference &ref)
{
	if (m_marked_iterator == m_marked.end())
		return -1;
	ref = *m_marked_iterator++;
	return 0;
}

int eListboxServiceContent::lookupService(const eServiceReference &ref)
{
		/* shortcut for cursor */
	if (ref == *m_cursor)
		return m_cursor_number;
		/* otherwise, search in the list.. */
	int index = 0;
	for (list::const_iterator i(m_list.begin()); i != m_list.end(); ++i, ++index);

		/* this is ok even when the index was not found. */
	return index;
}

void eListboxServiceContent::setVisualMode(int mode)
{
	for (int i=0; i < celElements; ++i)
	{
		m_element_position[i] = eRect();
		m_element_font[i] = 0;
	}

	m_visual_mode = mode;

	if (m_visual_mode == visModeSimple)
	{
		m_element_position[celServiceName] = eRect(ePoint(0, 0), m_itemsize);
		m_element_font[celServiceName] = new gFont("Regular", 23);
	}
}

void eListboxServiceContent::setElementPosition(int element, eRect where)
{
	if ((element >= 0) && (element < celElements))
		m_element_position[element] = where;
}

void eListboxServiceContent::setElementFont(int element, gFont *font)
{
	if ((element >= 0) && (element < celElements))
		m_element_font[element] = font;
}

void eListboxServiceContent::setPixmap(int type, ePtr<gPixmap> &pic)
{
	if ((type >=0) && (type < picElements))
		m_pixmaps[type] = pic;
}

void eListboxServiceContent::sort()
{
	if (!m_lst)
		m_service_center->list(m_root, m_lst);
	if (m_lst)
	{
		m_list.sort(iListableServiceCompare(m_lst));
			/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
}

DEFINE_REF(eListboxServiceContent);

eListboxServiceContent::eListboxServiceContent()
	:m_visual_mode(visModeSimple), m_size(0), m_current_marked(false), m_itemheight(25), m_hide_number_marker(false), m_servicetype_icon_mode(0), m_crypto_icon_mode(0), m_record_indicator_mode(0), m_column_width(0), m_progressbar_height(6), m_progressbar_border_width(2), m_nonplayable_margins(10), m_items_distances(8), m_sides_margin(0), m_marker_as_line(0), m_markerline_color_set(0)
{
	memset(m_color_set, 0, sizeof(m_color_set));
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
}

void eListboxServiceContent::setColor(int color, gRGB &col)
{
	if ((color >= 0) && (color < colorElements))
	{
		m_color_set[color] = true;
		m_color[color] = col;
	}
}

void eListboxServiceContent::swapServices(list::iterator a, list::iterator b)
{
	std::iter_swap(a, b);
	int temp = a->getChannelNum();
	a->setChannelNum(b->getChannelNum());
	b->setChannelNum(temp);
}

void eListboxServiceContent::cursorHome()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		if (m_cursor_number >= m_size)
		{
			m_cursor_number = m_size-1;
			--m_cursor;
		}
		while (m_cursor_number)
		{
			swapServices(m_cursor--, m_cursor);
			--m_cursor_number;
			if (m_listbox && m_cursor_number)
				m_listbox->entryChanged(cursorResolve(m_cursor_number));
		}
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number = 0;
		while (m_cursor != m_list.end())
		{
			if (!((m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) || (m_cursor->flags & eServiceReference::isInvisible)))
				break;
			m_cursor++;
			m_cursor_number++;
		}
	}
}

void eListboxServiceContent::cursorEnd()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		while (m_cursor != m_list.end())
		{
			list::iterator prev = m_cursor++;
			++m_cursor_number;
			if ( prev != m_list.end() && m_cursor != m_list.end() )
			{
				swapServices(m_cursor, prev);
				if ( m_listbox )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
		}
	}
	else
	{
		m_cursor = m_list.end();
		m_cursor_number = m_size;
	}
}

int eListboxServiceContent::setCurrentMarked(bool state)
{
	bool prev = m_current_marked;
	m_current_marked = state;

	if (state != prev && m_listbox)
	{
		m_listbox->entryChanged(cursorResolve(m_cursor_number));
		if (!state)
		{
			if (!m_lst)
				m_service_center->list(m_root, m_lst);
			if (m_lst)
			{
				ePtr<iMutableServiceList> list;
				if (m_lst->startEdit(list))
					eDebug("[eListboxServiceContent] no editable list");
				else
				{
					eServiceReference ref;
					getCurrent(ref);
					if(!ref)
						eDebug("[eListboxServiceContent] no valid service selected");
					else
					{
						int pos = cursorGet();
						eDebugNoNewLineStart("[eListboxServiceContent] move %s to %d ", ref.toString().c_str(), pos);
						if (list->moveService(ref, cursorGet()))
							eDebugNoNewLine("failed\n");
						else
							eDebugNoNewLine("ok\n");
					}
				}
			}
			else
				eDebug("[eListboxServiceContent] no list available!");
		}
	}

	return 0;
}

int eListboxServiceContent::cursorMove(int count)
{
	int prev = m_cursor_number, last = m_cursor_number + count;
	if (count > 0)
	{
		while(count && m_cursor != m_list.end())
		{
			list::iterator prev_it = m_cursor++;
			if ( m_current_marked && m_cursor != m_list.end() && m_saved_cursor == m_list.end() )
			{
				swapServices(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
			++m_cursor_number;
			if (!(m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) && !(m_cursor->flags & eServiceReference::isInvisible))
				--count;
		}
	}
	else if (count < 0)
	{
		while (count && m_cursor != m_list.begin())
		{
			list::iterator prev_it = m_cursor--;
			if ( m_current_marked && m_cursor != m_list.end() && prev_it != m_list.end() && m_saved_cursor == m_list.end() )
			{
				swapServices(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
			--m_cursor_number;
			if (!(m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) && !(m_cursor->flags & eServiceReference::isInvisible))
				++count;
		}
		while (m_cursor != m_list.end())
		{
			if (!((m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) || (m_cursor->flags & eServiceReference::isInvisible)))
				break;
			m_cursor++;
			m_cursor_number++;
		}
	}
	return 0;
}

int eListboxServiceContent::cursorValid()
{
	return m_cursor != m_list.end();
}

int eListboxServiceContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);
	return 0;
}

int eListboxServiceContent::cursorResolve(int cursorPosition)
{
	int strippedCursor = 0;
	int count = 0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i)
	{
		if (count == cursorPosition)
			break;
		count++;
		if ((m_marked.empty() && m_hide_number_marker && (i->flags & eServiceReference::isNumberedMarker)) || (i->flags & eServiceReference::isInvisible))
			continue;
		strippedCursor++;
	}
	return strippedCursor;
}

int eListboxServiceContent::cursorGet()
{
	return cursorResolve(m_cursor_number);
}

int eListboxServiceContent::currentCursorSelectable()
{
	if (cursorValid())
	{
		/* don't allow markers to be selected, unless we're in edit mode (because we want to provide some method to the user to remove a marker) */
		if ((m_cursor->flags & eServiceReference::isMarker) && m_marked.empty())
			return 0;
		else
			return 1;
	}
	return 0;
}

void eListboxServiceContent::cursorSave()
{
	m_saved_cursor = m_cursor;
	m_saved_cursor_number = m_cursor_number;
}

void eListboxServiceContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
	m_cursor_number = m_saved_cursor_number;
	m_saved_cursor = m_list.end();
}

int eListboxServiceContent::size()
{
	int size = 0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i)
	{
		if ((m_marked.empty() && m_hide_number_marker && (i->flags & eServiceReference::isNumberedMarker)) || (i->flags & eServiceReference::isInvisible))
			continue;
		size++;
	}

	return size;
}

void eListboxServiceContent::setSize(const eSize &size)
{
	m_itemsize = size;
	if (m_visual_mode == visModeSimple)
		setVisualMode(m_visual_mode);
}

void eListboxServiceContent::setGetPiconNameFunc(ePyObject func)
{
	if (m_GetPiconNameFunc)
		Py_DECREF(m_GetPiconNameFunc);
	m_GetPiconNameFunc = func;
	if (m_GetPiconNameFunc)
		Py_INCREF(m_GetPiconNameFunc);
}

void eListboxServiceContent::setIgnoreService( const eServiceReference &service )
{
	m_is_playable_ignore=service;
	if (m_listbox && m_listbox->isVisible())
		m_listbox->invalidate();
}

void eListboxServiceContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox)
		m_listbox->setItemHeight(height);
}

bool eListboxServiceContent::checkServiceIsRecorded(eServiceReference ref)
{
	std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > recordedServices;
	recordedServices = eNavigation::getInstance()->getRecordingsServices();
	for (std::map<ePtr<iRecordableService>, eServiceReference >::iterator it = recordedServices.begin(); it != recordedServices.end(); ++it)
	{
		if (ref.flags & eServiceReference::isGroup)
		{
			ePtr<iDVBChannelList> db;
			ePtr<eDVBResourceManager> res;
			eDVBResourceManager::getInstance(res);
			res->getChannelList(db);
			eBouquet *bouquet = NULL;
			if (!db->getBouquet(ref, bouquet))
			{
				for (std::list<eServiceReference>::iterator i(bouquet->m_services.begin()); i != bouquet->m_services.end(); ++i){
					if (compareServices(*i, it->second, m_alternative_record_match))
						return true;
				}
			}
		}
		else {
			if (compareServices(ref, it->second, m_alternative_record_match))
				return true;
		}
	}
	return false;
}

void eListboxServiceContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	painter.clip(eRect(offset, m_itemsize));

	int marked = 0;

	if (m_current_marked && selected)
		marked = 2;
	else if (cursorValid() && isMarked(*m_cursor))
	{
		if (selected)
			marked = 2;
		else
			marked = 1;
	}
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

	eListboxStyle *local_style = 0;
	eRect itemRect = eRect(offset, m_itemsize);
	int radius = 0;
	int edges = 0;

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	if (local_style) {
		radius = local_style->cornerRadius(selected ? 1:0);
		edges = local_style->cornerRadiusEdges(selected ? 1:0);
	}

	if (marked == 1)  // marked
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
		if (m_color_set[markedForeground])
			painter.setForegroundColor(m_color[markedForeground]);
		if (m_color_set[markedBackground])
			painter.setBackgroundColor(m_color[markedBackground]);
	}
	else if (marked == 2) // marked and selected
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarkedAndSelected);
		if (m_color_set[markedForegroundSelected])
			painter.setForegroundColor(m_color[markedForegroundSelected]);
		if (m_color_set[markedBackgroundSelected])
			painter.setBackgroundColor(m_color[markedBackgroundSelected]);
	}
	else if (local_style)
	{
		if (selected)
		{
			/* if we have a local background color set, use that. */
			if (local_style->m_background_color_selected_set)
				painter.setBackgroundColor(local_style->m_background_color_selected);
			/* same for foreground */
			if (local_style->m_foreground_color_selected_set)
				painter.setForegroundColor(local_style->m_foreground_color_selected);
		}
		else
		{
			/* if we have a local background color set, use that. */
			if (local_style->m_background_color_set)
				painter.setBackgroundColor(local_style->m_background_color);
			/* same for foreground */
			if (local_style->m_foreground_color_set)
				painter.setForegroundColor(local_style->m_foreground_color);
		}
	}

	if (!local_style || !local_style->m_transparent_background)
		/* if we have no transparent background */
	{
		/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), 0);
		else if (local_style && !local_style->m_background && radius)
		{
			if(radius)
				painter.setRadius(radius, edges);
			painter.drawRectangle(itemRect);
		}
		else
			painter.clear();
	} else
	{
		if (local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHABLEND);
		else if (selected && !local_style->m_selection && !local_style->m_selection_large && !radius)
			painter.clear();
	}

	if (cursorValid())
	{
		if (selected && local_style && local_style->m_selection && m_visual_mode != visSkinDefined){
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHABLEND);
		}
		if (selected && local_style && local_style->m_selection_large && m_visual_mode == visSkinDefined){
			painter.blit(local_style->m_selection_large, offset, eRect(), gPainter::BT_ALPHABLEND);
		}

		// Draw the frame for selected item here so to be under the content
		if (selected && (!local_style || (!local_style->m_selection && !local_style->m_selection_large)) && !radius)
			style.drawFrame(painter, itemRect, eWindowStyle::frameListboxEntry);

		eServiceReference ref = *m_cursor;
		std::string orig_ref_str = ref.toString();
		std::string service_res_str =  toLower(split(orig_ref_str, ":")[2]);

		bool isBackupAvailable = false;
		int catchUpDays = 0;
		if (orig_ref_str.find("@") != std::string::npos) {
			isBackupAvailable = true;
		}

		if (orig_ref_str.find("|<|") != std::string::npos) {
			catchUpDays = std::stoi(split(split(orig_ref_str, "|<|")[1], "@")[0]);
		}

		/* get service information */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(ref, service_info);
		bool isMarker = ref.flags & eServiceReference::isMarker;
		bool isDirectory = ref.flags & eServiceReference::isDirectory;
		bool isPlayable = !(isDirectory || isMarker);
		bool isRecorded = isPlayable && checkServiceIsRecorded(ref);
		ePtr<eServiceEvent> evt, evt_next;
		bool serviceAvail = true;
		bool serviceFallback = false;
		int isplayable_value;
		gRGB EventProgressbarColor = 0xe7b53f;
		ePtr<iPlayableService> refCur;

		if (!marked && isPlayable && service_info && m_is_playable_ignore.valid())
		{
			isplayable_value = service_info->isPlayable(*m_cursor, m_is_playable_ignore);
			if (isplayable_value == 0) // service unavailable
			{
				if (m_color_set[serviceNotAvail])
					painter.setForegroundColor(m_color[serviceNotAvail]);
				else
					painter.setForegroundColor(gRGB(0xbbbbbb));
				serviceAvail = false;
			}
			else
			{
				if (isplayable_value == 2) // fallback receiver service
				{
					if (m_color_set[serviceItemFallback])
						painter.setForegroundColor(m_color[serviceItemFallback]);
					serviceFallback = true;
				}
			}
		}
		if (m_record_indicator_mode == 3 && isRecorded)
		{
			if (m_color_set[serviceRecorded])
				painter.setForegroundColor(m_color[serviceRecorded]);
			else
				painter.setForegroundColor(gRGB(0xb40431));
		}

		int xoffset=0, xoffs=0, xoffs_col=0;  // used as offset when painting the folder/marker symbol or the serviceevent progress

		if (m_separator == "") m_separator = "  ";

		std::string text = "<N/A>";

		bool hasChannelNumbers = m_chanel_number_visible;

		time_t now = time(0);

		std::string event_name = "", next_event_name = "";
		int event_begin = 0, event_duration = 0, xlpos = m_itemsize.width(), ctrlHeight=m_itemheight, yoffs=0, yoffs_orig=0;
		bool is_event = isPlayable && service_info && !service_info->getEvent(ref, evt);
		if (m_visual_mode == visSkinDefined) {
			if (is_event){
				event_name = evt->getEventName();
			}
			if (!event_name.empty()) {
				ctrlHeight = m_itemheight/2;
				yoffs_orig = 5;
				yoffs = m_has_next_event ? ctrlHeight - 2 : 5;
			}
			if (!isMarker && !isDirectory) {
				ePtr<gPixmap> &pixmap =  service_res_str == "1f" ? m_pixmaps[pic4K] : (service_res_str == "19" || service_res_str == "11") ? 
					m_pixmaps[picHD] : m_pixmaps[picSD];

				if (pixmap)
				{
					eSize pixmap_size = pixmap->size();
					xlpos -= 15 + pixmap_size.width();
					eRect res_area = eRect(xlpos, offset.y() + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(res_area);
					painter.blit(pixmap, ePoint(res_area.left(), res_area.top()), res_area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				int orbpos = m_cursor->getUnsignedData(4) >> 16;
				if (m_servicetype_icon_mode) {
					const char *filename = ref.path.c_str();
					ePtr<gPixmap> &pixmap_system  =
						(m_cursor->flags & eServiceReference::isGroup) ? m_pixmaps[picServiceGroup] :
						(strstr(filename, "://")) ? m_pixmaps[picStream] :
						(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
						(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];

					if (pixmap_system)
					{
						eSize pixmap_size = pixmap_system->size();
						xlpos -= 15 + pixmap_size.width();
						eRect area = eRect(xlpos, offset.y() + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
						painter.clip(area);
						painter.blit(pixmap_system, ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
						painter.clippop();
					}
				}

				if (m_crypto_icon_mode && m_pixmaps[picCrypto] && service_info && service_info->isCrypted())
				{
					eSize pixmap_size = m_pixmaps[picCrypto]->size();
					xlpos -= 15 + pixmap_size.width();
					eRect area = eRect(xlpos, offset.y()  + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picCrypto], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (m_pixmaps[picBackup] && isBackupAvailable)
				{
					eSize pixmap_size = m_pixmaps[picBackup]->size();
					xlpos -= 15 + pixmap_size.width();
					eRect area = eRect(xlpos, offset.y() + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picBackup], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (m_pixmaps[picCatchup] && catchUpDays > 0)
				{
					eSize pixmap_size = m_pixmaps[picCatchup]->size();
					xlpos -= 15 + pixmap_size.width();
					eRect area = eRect(xlpos, offset.y() + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picCatchup], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (m_pixmaps[picRecord] && isRecorded && ((m_record_indicator_mode == 1) || (m_record_indicator_mode == 2)))
				{
					eSize pixmap_size = m_pixmaps[picRecord]->size();
					xlpos -= 15 + pixmap_size.width();
					eRect area = eRect(xlpos, offset.y() + yoffs + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picRecord], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}
			}
			ePtr<gPixmap> piconPixmap;
			bool isPIconSVG = false;
			bool hasPicon = PyCallable_Check(m_GetPiconNameFunc);
			if (isPlayable && hasPicon)
			{
				ePyObject pArgs = PyTuple_New(1);
				PyTuple_SET_ITEM(pArgs, 0, PyUnicode_FromString(ref.toString().c_str()));
				ePyObject pRet = PyObject_CallObject(m_GetPiconNameFunc, pArgs);
				Py_DECREF(pArgs);
				if (pRet)
				{
					if (PyUnicode_Check(pRet))
					{
						std::string piconFilename = PyUnicode_AsUTF8(pRet);
						if (endsWith(piconFilename, ".svg")) {
							isPIconSVG = true;
						}
						if (!piconFilename.empty())
							loadImage(piconPixmap, piconFilename.c_str(), 0, isPIconSVG ? 125 : 0);
					}
					Py_DECREF(pRet);
				}
			}
			xoffs = xoffset + 16;

			if (hasPicon)
			{
				eRect piconArea =  eRect(xoffs, offset.y(), 125, m_itemheight);
				/* PIcons are usually about 100:60. Make it a
				* bit wider in case the icons are diffently
				* shaped, and to add a bit of margin between
				* icon and text. */
				int pflags = gPainter::BT_ALPHABLEND | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
				if (!isPIconSVG) {
					pflags = gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
				}
				if (piconPixmap)
				{
					painter.clip(piconArea);
					if (isPIconSVG) {
						painter.blit(piconPixmap,
						eRect(xoffs, offset.y(), 125, m_itemheight),
						eRect(),
						pflags
						);
					} else {
						painter.blitScale(piconPixmap,
							eRect(xoffs, offset.y(), 125, m_itemheight),
							piconArea,
							pflags);
					}
					painter.clippop();
				}
				if (!(isMarker || isDirectory))	xoffs += 125 + 16 + 8;
			}

			// channel number + name
			if (service_info)
				service_info->getName(ref, text);

			ePtr<eTextPara> paraName = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight/2));
			paraName->setFont(m_element_font[celServiceName]);
			paraName->renderString(text.c_str());
			eRect bboxName = paraName->getBoundBox();

			int xoffsMarker = xoffs + ((isDirectory || isMarker) ? ((hasPicon && isMarker ? 125 : m_itemheight) + 16 + 8) : 0);
			int correction = 0;
			int service_name_end = 0;
			if (!m_marker_alignment.empty() && m_marker_alignment == "center" && isMarker) {
				xoffsMarker = (m_itemsize.width() - bboxName.width()) / 2;
				correction = 16;
			}

			if (!isMarker && !isDirectory) {
				std::string chNum = "";
				if (hasChannelNumbers && m_cursor->getChannelNum() != 0) {
					char buffer[15];
					snprintf(buffer, sizeof(buffer), "%d", m_cursor->getChannelNum() );
					chNum = buffer;
				}
				if (chNum != "") text = chNum + m_separator + text;
			}
			ePtr<gPixmap> &pixmap_mDir = isMarker ? m_pixmaps[picMarker] : isDirectory ? m_pixmaps[picFolder] : m_pixmaps[picElements];;
			if (isMarker || isDirectory) {
				if (isDirectory || (isMarker && !m_marker_as_line)) {
					eSize pixmap_size = pixmap_mDir->size();
					if (pixmap_size.width() < 125 || pixmap_size.height() < m_itemheight)
						xoffsMarker = xoffs + pixmap_size.width() + 16;
				}
			}

			ePtr<eTextPara> para = new eTextPara(eRect(0, 0, xlpos - xoffsMarker, m_itemheight/2));
			para->setFont(m_element_font[celServiceName]);
			para->renderString(text.c_str());
			eRect bbox = para->getBoundBox();
			service_name_end = xoffsMarker - correction + bbox.width() + m_items_distances;
			painter.renderPara(para, ePoint(xoffsMarker - correction, offset.y() + yoffs_orig + ((ctrlHeight - bbox.height())/2)));

			if (isDirectory || (isMarker && !m_marker_as_line)) {
				if (pixmap_mDir) {
					eSize pixmap_size = pixmap_mDir->size();
					if (pixmap_size.width() < 125 || pixmap_size.height() < m_itemheight){
						eRect area = eRect(xoffs, offset.y() + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
						painter.clip(area);
						painter.blit(pixmap_mDir, ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					} else {
						int pflags = gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
						eRect area = eRect(xoffs, offset.y(), 125, m_itemheight);
						painter.clip(area);
						painter.blitScale(pixmap_mDir, eRect(xoffs, offset.y(), 125, m_itemheight), area, pflags);
					}
					painter.clippop();
				}
			} else if (isMarker && m_marker_as_line) {
				if (m_markerline_color_set) painter.setForegroundColor(m_markerline_color);
				eRect firstLineRect = eRect(xoffs, offset.y() + (m_itemheight - m_marker_as_line) / 2, xoffsMarker - 16 - 8 - xoffs - correction, m_marker_as_line);
				painter.fill(firstLineRect);
				int secondLineOffset = xoffsMarker + bboxName.width() + 16 + 8 - correction;
				eRect secondLineRect = eRect(secondLineOffset, offset.y() + (m_itemheight - m_marker_as_line) / 2, m_itemsize.width() - secondLineOffset - 16 - 8, m_marker_as_line);
				painter.fill(secondLineRect);
			}

			// event name
			if (is_event)
			{
				event_name = evt->getEventName();
				event_begin = evt->getBeginTime();
				event_duration = evt->getDuration();
				int timeLeft = event_begin + event_duration - now;
				eRect progressBarRect = m_element_position[celServiceEventProgressbar];
				if (m_has_next_event && event_begin > 0 && !service_info->getEvent(*m_cursor, evt_next, (event_begin + event_duration)))
					next_event_name = evt_next->getEventName();

				if (!event_name.empty())
				{
					int pb_xpos = xoffs;
					//--------------------------------------------------- Event Progressbar -----------------------------------------------------------------
					if (progressBarRect.width() > 0) {
						int pb_yoffs_corr = m_itemheight/2;
						if (m_has_next_event) pb_yoffs_corr = 5;
						if (m_has_next_event) {
							pb_xpos = m_itemsize.width() - 15 - progressBarRect.width();
						}
						int pb_ypos = offset.y() + pb_yoffs_corr + (m_itemheight/2 - m_progressbar_height - 2 * m_progressbar_border_width) / 2;
						int pb_width = progressBarRect.width() - 2 * m_progressbar_border_width;
						gRGB ProgressbarBorderColor = 0xdfdfdf;
						int evt_done = pb_width * (now - event_begin) / event_duration;

						if (!startsWith(m_progress_mode, "perc")) {
							// the progress data...
							eRect tmp = eRect(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width, evt_done, m_progressbar_height);
							ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
							if (pixmap) {
								painter.clip(tmp);
								painter.blit(pixmap, ePoint(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width), tmp, gPainter::BT_ALPHABLEND);
								painter.clippop();
							}
							else {
								if (!selected && m_color_set[serviceEventProgressbarColor])
									painter.setForegroundColor(m_color[serviceEventProgressbarColor]);
								else if (selected && m_color_set[serviceEventProgressbarColorSelected])
									painter.setForegroundColor(m_color[serviceEventProgressbarColorSelected]);
								painter.fill(tmp);
							}

							// the progressbar border
							if (!selected)  {
								if (m_color_set[serviceEventProgressbarBorderColor])
									ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColor];
								else if (m_color_set[eventborderForeground])
									ProgressbarBorderColor = m_color[eventborderForeground];
							}
							else { /* !selected */
								if (m_color_set[serviceEventProgressbarBorderColorSelected])
									ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColorSelected];
								else if (m_color_set[eventborderForegroundSelected])
									ProgressbarBorderColor = m_color[eventborderForegroundSelected];
							}
							painter.setForegroundColor(ProgressbarBorderColor);

							if (m_progressbar_border_width)
							{
								painter.fill(eRect(pb_xpos, pb_ypos, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
								painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width + m_progressbar_height, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
								painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
								painter.fill(eRect(pb_xpos + m_progressbar_border_width + pb_width, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
							}
							else
								painter.fill(eRect(pb_xpos + evt_done, pb_ypos, pb_width - evt_done,  m_progressbar_height));
							if (!m_has_next_event)	xoffs += pb_width + 16;
						}
					}

					//------------------------------------------------------- Event Name  --------------------------------------------------------------------
					text = event_name;
					std::replace(text.begin(), text.end(), '\n', ' ');
					if (serviceAvail)
					{
						if (!selected && m_color_set[eventForeground])
						{
							painter.setForegroundColor(m_color[eventForeground]);
						}
						else if (selected && m_color_set[eventForegroundSelected])
						{
							painter.setForegroundColor(m_color[eventForegroundSelected]);
						}
						else
							painter.setForegroundColor(gRGB(0xe7b53f));

						if (serviceFallback && !selected && m_color_set[eventForegroundFallback]) // fallback receiver
						{
							painter.setForegroundColor(m_color[eventForegroundFallback]);
						}
						else if (serviceFallback && selected && m_color_set[eventForegroundSelectedFallback])
						{
							painter.setForegroundColor(m_color[eventForegroundSelectedFallback]);
						}
					}

					std::string percent = "";
					if (startsWith(m_progress_mode, "perc")) {
						char buffer[15];
						snprintf(buffer, sizeof(buffer), "%d %%", (int)(100 * (now - event_begin) / event_duration));
						percent = buffer;
					}

					//------------------------------------------------- Event name ------------------------------------------------------------------------------
					if (m_has_next_event) {
						ePtr<eTextPara> para = new eTextPara(eRect(0, 0, pb_xpos - service_name_end - m_items_distances - 15, m_itemheight/2));
						para->setFont(m_element_font[celServiceInfo]);
						para->renderString(text.c_str());
						eRect bbox = para->getBoundBox();
						painter.renderPara(para, ePoint(service_name_end, offset.y() + yoffs_orig + ((ctrlHeight - bbox.height())/2)));

						if (!percent.empty()) {
							ePtr<eTextPara> paraPrec = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight/2));
							paraPrec->setFont(m_element_font[celServiceInfo]);
							paraPrec->renderString(percent.c_str());
							eRect bboxPerc = paraPrec->getBoundBox();
							painter.renderPara(paraPrec, ePoint(m_itemsize.width() - 15 - bboxPerc.width() , offset.y() + yoffs_orig + ((ctrlHeight - bboxPerc.height())/2)));
						}

						if (!next_event_name.empty()) {
							if (serviceAvail)
							{
								if (!selected && m_color_set[eventNextForeground])
								{
									painter.setForegroundColor(m_color[eventNextForeground]);
								}
								else if (selected && m_color_set[eventNextForegroundSelected])
								{
									painter.setForegroundColor(m_color[eventNextForegroundSelected]);
								}
								else
									painter.setForegroundColor(gRGB(0x787878));

								if (serviceFallback && !selected && m_color_set[eventNextForegroundFallback]) // fallback receiver
								{
									painter.setForegroundColor(m_color[eventNextForegroundFallback]);
								}
								else if (serviceFallback && selected && m_color_set[eventNextForegroundSelectedFallback])
								{
									painter.setForegroundColor(m_color[eventNextForegroundSelectedFallback]);
								}
							}
							ePtr<eTextPara> paraNext = new eTextPara(eRect(0, 0, xlpos - xoffs - m_items_distances, m_itemheight/2));
							paraNext->setFont(m_element_font[celServiceNextInfo]);
							paraNext->renderString((m_next_title + next_event_name).c_str());
							eRect bboxNext = paraNext->getBoundBox();
							painter.renderPara(paraNext, ePoint(xoffs, offset.y() - 2 + m_itemheight/2 + ((m_itemheight/2 - bboxNext.height())/2)));
						}
					} else {
						//------------------------------------------------ Event remaining ------------------------------------------------------------------------
						std::string timeLeft_str = "";
						char buffer[15];
						snprintf(buffer, sizeof(buffer), "%s%d %s", timeLeft < 60 ? "" : "+", timeLeft/60, m_text_time.c_str());
						timeLeft_str = buffer;
						ePtr<eTextPara> paraLeft = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight/2));
						paraLeft->setFont(m_element_font[celServiceInfoRemainingTime]);
						paraLeft->renderString(timeLeft_str.c_str());
						eRect bboxtLeft = paraLeft->getBoundBox();

						ePtr<eTextPara> para = new eTextPara(eRect(0, 0, m_itemsize.width() - xoffs - bboxtLeft.width() - 25 - m_items_distances, m_itemheight/2));
						para->setFont(m_element_font[celServiceInfo]);
						para->renderString(((!percent.empty() ? (percent + m_separator) : "") + text).c_str());
						eRect bbox = para->getBoundBox();
						painter.renderPara(para, ePoint(xoffs, offset.y() - 2 + m_itemheight/2 + ((m_itemheight/2 - bbox.height())/2)));

						if (serviceAvail)
						{
							if (!selected && m_color_set[eventRemainingForeground])
							{
								painter.setForegroundColor(m_color[eventRemainingForeground]);
							}
							else if (selected && m_color_set[eventRemainingForegroundSelected])
							{
								painter.setForegroundColor(m_color[eventRemainingForegroundSelected]);
							}
							else
								painter.setForegroundColor(gRGB(0x787878));

							if (serviceFallback && !selected && m_color_set[eventRemainingForegroundFallback]) // fallback receiver
							{
								painter.setForegroundColor(m_color[eventRemainingForegroundFallback]);
							}
							else if (serviceFallback && selected && m_color_set[eventRemainingForegroundSelectedFallback])
							{
								painter.setForegroundColor(m_color[eventRemainingForegroundSelectedFallback]);
							}
						}

						painter.renderPara(paraLeft, ePoint(m_itemsize.width() - bboxtLeft.width() - 15, offset.y() - 2 + m_itemheight/2 + ((m_itemheight/2 - bboxtLeft.height())/2)));
					}
				}
			}
		} else {
			// Single line mode goes here
			if (service_info)
				service_info->getName(ref, text);

			xoffs += m_sides_margin;
			if (is_event)
			{
				event_name = evt->getEventName();
				event_begin = evt->getBeginTime();
				event_duration = evt->getDuration();
			}
			int orbpos = m_cursor->getUnsignedData(4) >> 16;
			const char *filename = ref.path.c_str();

			ePtr<gPixmap> &pixmap_system  =
						(m_cursor->flags & eServiceReference::isGroup) ? m_pixmaps[picServiceGroup] :
						(strstr(filename, "://")) ? m_pixmaps[picStream] :
						(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
						(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];

			eSize pixmap_system_size = eSize();
			eSize pixmap_crypto_size = eSize();
			eSize pixmap_rec_size = eSize();

			if (pixmap_system) {
				pixmap_system_size = pixmap_system->size();
			}

			if (m_pixmaps[picCrypto]) {
				pixmap_crypto_size = m_pixmaps[picCrypto]->size();
			}

			if (m_pixmaps[picRecord]) {
				pixmap_rec_size = m_pixmaps[picRecord]->size();
			}

			bool hasPicons = PyCallable_Check(m_GetPiconNameFunc);
			bool isAlternativeNumberingMode = m_alternative_numbering;
			std::string eventProgressConfig = m_progress_mode;
			int serviceNameWidth = m_column_width > -1 && !isDirectory && !isMarker ? m_column_width : m_itemsize.width();
			bool shouldCorrect = serviceNameWidth >= m_column_width - pixmap_system_size.width()*3;

			if (m_servicetype_icon_mode == 2 && m_column_width > -1 && shouldCorrect) serviceNameWidth -= pixmap_system_size.width() + m_items_distances;
			if (m_crypto_icon_mode == 2 && m_column_width > -1 && shouldCorrect) serviceNameWidth -= pixmap_crypto_size.width() + m_items_distances;
			if (isRecorded && m_record_indicator_mode == 2 && m_column_width > -1 && shouldCorrect) serviceNameWidth -= pixmap_rec_size.width() + m_items_distances;
			if ((m_servicetype_icon_mode == 2 || m_crypto_icon_mode == 2 || (isRecorded && m_record_indicator_mode == 2)) && m_column_width > -1)
				serviceNameWidth -= m_items_distances;

			if (serviceNameWidth < 0) serviceNameWidth = 0;

			ePtr<eTextPara> paraServiceName = new eTextPara(eRect(0, 0, serviceNameWidth, m_itemheight));
			paraServiceName->setFont(m_element_font[celServiceName]);
			paraServiceName->renderString(text.c_str());
			eRect bboxServiceName = paraServiceName->getBoundBox();

			if (isDirectory || (isMarker && !m_marker_as_line)) {
				ePtr<gPixmap> &pixmap_mDir = isMarker ? m_pixmaps[picMarker] : isDirectory ? m_pixmaps[picFolder] : m_pixmaps[picElements];;
				eSize pixmap_size = pixmap_mDir->size();
				if (pixmap_size.height() < m_itemheight){
					eRect area = eRect(xoffs, offset.y() + (ctrlHeight - pixmap_size.height())/2, pixmap_size.width(), pixmap_size.height());
					painter.clip(area);
					painter.blit(pixmap_mDir, ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
				} else {
					int pflags = gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
					eRect area = eRect(xoffs, offset.y(), m_itemheight, m_itemheight);
					painter.clip(area);
					painter.blitScale(pixmap_mDir, eRect(xoffs, offset.y(), m_itemheight, m_itemheight), area, pflags);
				}
				painter.clippop();

				painter.renderPara(paraServiceName, ePoint(xoffs + pixmap_size.width() + m_items_distances, offset.y() + ((ctrlHeight - bboxServiceName.height())/2)));

			} else if (isMarker && m_marker_as_line) {
				int mTextLeft = (m_itemsize.width() - bboxServiceName.width())/2;
				if (m_marker_alignment != "center") {
					mTextLeft = 125 + m_items_distances;
				}
				painter.renderPara(paraServiceName, ePoint(mTextLeft, offset.y() + ((ctrlHeight - bboxServiceName.height())/2)));

				if (m_markerline_color_set) painter.setForegroundColor(m_markerline_color);
				eRect firstLineRect = eRect(xoffs + m_items_distances, offset.y() + (m_itemheight - m_marker_as_line) / 2, mTextLeft - m_items_distances*2 - xoffs - 16, m_marker_as_line);
				painter.fill(firstLineRect);
				int secondLineOffset = mTextLeft + bboxServiceName.width() + m_items_distances + 16;
				eRect secondLineRect = eRect(secondLineOffset, offset.y() + (m_itemheight - m_marker_as_line) / 2, m_itemsize.width() - secondLineOffset - m_items_distances - m_sides_margin, m_marker_as_line);
				painter.fill(secondLineRect);
			}

			if (!isDirectory && !isMarker) {

				ePtr<eTextPara> paraCtrlText = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight));
				paraCtrlText->setFont(m_element_font[celServiceNumber]);
				paraCtrlText->renderString((isAlternativeNumberingMode ? "0000" : "00000"));
				eRect bboxCtrlText = paraCtrlText->getBoundBox();

				if (hasChannelNumbers && m_cursor->getChannelNum() > 0) {
					char buffer[15];
					snprintf(buffer, sizeof(buffer), "%d", m_cursor->getChannelNum() );
					std::string num = buffer;
					ePtr<eTextPara> para = new eTextPara(eRect(xoffs, 0, bboxCtrlText.width(), m_itemheight));
					para->setFont(m_element_font[celServiceNumber]);
					para->renderString(num.c_str());
					eRect bbox = para->getBoundBox();
					painter.renderPara(para, ePoint(xoffs + (bboxCtrlText.width() - bbox.width()), offset.y() + (ctrlHeight - bbox.height())/2));
					xoffs += bboxCtrlText.width() + m_items_distances;
				}

				eRect progressBarRect = m_element_position[celServiceEventProgressbar];

				int pb_xpos = xoffs;
				int pb_ypos = offset.y() + (m_itemheight - m_progressbar_height - 2 * m_progressbar_border_width) / 2;
				int pb_width = progressBarRect.width() - 2 * m_progressbar_border_width;
				gRGB ProgressbarBorderColor = 0xdfdfdf;
				int evt_done = pb_width * (now - event_begin) / event_duration;

				if (eventProgressConfig == "barleft" || eventProgressConfig == "percleft") {
					xoffs += progressBarRect.width() + m_items_distances;
				}

				ePtr<gPixmap> piconPixmap;
				bool isPIconSVG = false;
				int piconWidth = m_itemheight*1.67;
				if (isPlayable && hasPicons)
				{
					ePyObject pArgs = PyTuple_New(1);
					PyTuple_SET_ITEM(pArgs, 0, PyUnicode_FromString(ref.toString().c_str()));
					ePyObject pRet = PyObject_CallObject(m_GetPiconNameFunc, pArgs);
					Py_DECREF(pArgs);
					if (pRet)
					{
						if (PyUnicode_Check(pRet))
						{
							std::string piconFilename = PyUnicode_AsUTF8(pRet);
							if (endsWith(piconFilename, ".svg")) {
								isPIconSVG = true;
							}
							if (!piconFilename.empty())
								loadImage(piconPixmap, piconFilename.c_str(), 0, isPIconSVG ? piconWidth : 0);
						}
						Py_DECREF(pRet);
					}
				}

				if (hasPicons) {
					eRect piconArea =  eRect(xoffs, offset.y(), piconWidth, m_itemheight);
					/* PIcons are usually about 100:60. Make it a
					* bit wider in case the icons are diffently
					* shaped, and to add a bit of margin between
					* icon and text. */
					int pflags = gPainter::BT_ALPHABLEND | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
					if (!isPIconSVG) {
						pflags = gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER;
					}
					if (piconPixmap)
					{
						painter.clip(piconArea);
						if (isPIconSVG) {
							painter.blit(piconPixmap,
							eRect(xoffs, offset.y(), piconWidth, m_itemheight),
							eRect(),
							pflags
							);
						} else {
							painter.blitScale(piconPixmap,
								eRect(xoffs, offset.y(), piconWidth, m_itemheight),
								piconArea,
								pflags);
						}
						painter.clippop();
					}
					xoffs += piconWidth + m_items_distances;
				}

				int iconSystemPosX = xoffs + m_items_distances;
				int iconCryptoPosX = iconSystemPosX;
				int iconRecordPosX = iconSystemPosX;
				int iconOffsX = iconSystemPosX;

				if (m_servicetype_icon_mode == 1 && pixmap_system) {
					iconCryptoPosX += pixmap_system_size.width() + m_items_distances;
					iconRecordPosX = iconCryptoPosX;
					iconOffsX += pixmap_system_size.width() + m_items_distances;
				}

				if (m_crypto_icon_mode == 1 && m_pixmaps[picCrypto]) {
					iconRecordPosX += pixmap_crypto_size.width() + m_items_distances;
					iconOffsX += pixmap_crypto_size.width() + m_items_distances;
				}

				if (isRecorded && m_record_indicator_mode == 1 && m_pixmaps[picRecord]) {
					iconOffsX += pixmap_rec_size.width() + m_items_distances;
				}

				if (m_servicetype_icon_mode == 1 && pixmap_system) {
					eRect area = eRect(iconSystemPosX, offset.y() + (ctrlHeight - pixmap_system_size.height())/2, pixmap_system_size.width(), pixmap_system_size.height());
					painter.clip(area);
					painter.blit(pixmap_system, ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (m_crypto_icon_mode == 1 && m_pixmaps[picCrypto] && service_info && service_info->isCrypted()) {
					eRect area = eRect(iconCryptoPosX, offset.y() + (ctrlHeight - pixmap_crypto_size.height())/2, pixmap_crypto_size.width(), pixmap_crypto_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picCrypto], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (isRecorded && m_pixmaps[picRecord] && m_record_indicator_mode == 1) {
					eRect area = eRect(iconRecordPosX, offset.y() + (ctrlHeight - pixmap_rec_size.height())/2, pixmap_rec_size.width(), pixmap_rec_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picRecord], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				xoffs = iconOffsX;
				xoffs_col = xoffs + m_column_width;

				painter.renderPara(paraServiceName, ePoint(xoffs, offset.y() + (ctrlHeight - bboxServiceName.height())/2));

				xoffs += std::min(serviceNameWidth, bboxServiceName.width()) + m_items_distances;

				iconSystemPosX = xoffs;
				iconCryptoPosX = iconSystemPosX;
				iconRecordPosX = iconSystemPosX;
				iconOffsX = iconSystemPosX;

				if (m_servicetype_icon_mode == 2 && pixmap_system) {
					iconCryptoPosX += pixmap_system_size.width() + m_items_distances;
					iconRecordPosX = iconCryptoPosX;
					iconOffsX += pixmap_system_size.width() + m_items_distances;
					xoffs = iconOffsX;
				}

				if (m_crypto_icon_mode == 2 && m_pixmaps[picCrypto] && service_info && service_info->isCrypted()) {
					iconRecordPosX += pixmap_crypto_size.width() + m_items_distances;
					iconOffsX += pixmap_crypto_size.width() + m_items_distances;
					xoffs = iconOffsX;
				}

				if (isRecorded && m_record_indicator_mode == 2 && m_pixmaps[picRecord]) {
					iconOffsX += pixmap_rec_size.width() + m_items_distances;
					xoffs = iconOffsX;
				}

				if (m_servicetype_icon_mode == 2 && pixmap_system) {
					eRect area = eRect(iconSystemPosX, offset.y() + (ctrlHeight - pixmap_system_size.height())/2, pixmap_system_size.width(), pixmap_system_size.height());
					painter.clip(area);
					painter.blit(pixmap_system, ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (m_crypto_icon_mode == 2 && m_pixmaps[picCrypto] && service_info && service_info->isCrypted()) {
					eRect area = eRect(iconCryptoPosX, offset.y() + (ctrlHeight - pixmap_crypto_size.height())/2, pixmap_crypto_size.width(), pixmap_crypto_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picCrypto], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (isRecorded && m_pixmaps[picRecord] && m_record_indicator_mode == 2) {
					eRect area = eRect(iconRecordPosX, offset.y() + (ctrlHeight - pixmap_rec_size.height())/2, pixmap_rec_size.width(), pixmap_rec_size.height());
					painter.clip(area);
					painter.blit(m_pixmaps[picRecord], ePoint(area.left(), area.top()), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}

				if (eventProgressConfig == "barright" || eventProgressConfig == "percright") {
					pb_xpos = m_itemsize.width() - progressBarRect.width() - m_items_distances*2 - m_sides_margin*2 - m_progressbar_border_width*2;
				}

				if (is_event && !event_name.empty()) {
					text = event_name;
					std::replace(text.begin(), text.end(), '\n', ' ');
					if (serviceAvail)
					{
						if (!selected && m_color_set[eventForeground])
						{
							painter.setForegroundColor(m_color[eventForeground]);
							EventProgressbarColor = m_color[eventForeground];
						}
						else if (selected && m_color_set[eventForegroundSelected])
						{
							painter.setForegroundColor(m_color[eventForegroundSelected]);
							EventProgressbarColor = m_color[eventForegroundSelected];
						}
						else
							painter.setForegroundColor(gRGB(0xe7b53f));

						if (serviceFallback && !selected && m_color_set[eventForegroundFallback]) // fallback receiver
						{
							painter.setForegroundColor(m_color[eventForegroundFallback]);
							EventProgressbarColor = m_color[eventForegroundFallback];
						}
						else if (serviceFallback && selected && m_color_set[eventForegroundSelectedFallback])
						{
							painter.setForegroundColor(m_color[eventForegroundSelectedFallback]);
							EventProgressbarColor = m_color[eventForegroundSelectedFallback];
						}
					}

					int eventTextWidth = (eventProgressConfig == "barright" || eventProgressConfig == "percright") ?
							(pb_xpos - (m_column_width > 0 ? xoffs_col : xoffs) - m_items_distances*2 ) : (m_itemsize.width() - m_sides_margin*2 - (m_column_width > 0 ? xoffs_col : xoffs) - m_items_distances*2);

					ePtr<eTextPara> para = new eTextPara(eRect(0, 0, eventTextWidth, m_itemheight));
					para->setFont(m_element_font[celServiceInfo]);
					para->renderString(text.c_str());
					eRect bbox = para->getBoundBox();
					painter.renderPara(para, ePoint(m_column_width > 0 ? xoffs_col : xoffs, offset.y() + (m_itemheight - bbox.height())/2));

					if (eventProgressConfig != "no" && !startsWith(eventProgressConfig, "perc")) {
						// the progress data...
						eRect tmp = eRect(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width, evt_done, m_progressbar_height);
						ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
						if (pixmap) {
							painter.clip(tmp);
							painter.blit(pixmap, ePoint(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width), tmp, gPainter::BT_ALPHABLEND);
							painter.clippop();
						}
						else {
							if (!selected && m_color_set[serviceEventProgressbarColor])
								painter.setForegroundColor(m_color[serviceEventProgressbarColor]);
							else if (selected && m_color_set[serviceEventProgressbarColorSelected])
								painter.setForegroundColor(m_color[serviceEventProgressbarColorSelected]);
							painter.fill(tmp);
						}

						// the progressbar border
						if (!selected)  {
							if (m_color_set[serviceEventProgressbarBorderColor])
								ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColor];
							else if (m_color_set[eventborderForeground])
								ProgressbarBorderColor = m_color[eventborderForeground];
						}
						else { /* !selected */
							if (m_color_set[serviceEventProgressbarBorderColorSelected])
								ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColorSelected];
							else if (m_color_set[eventborderForegroundSelected])
								ProgressbarBorderColor = m_color[eventborderForegroundSelected];
						}
						painter.setForegroundColor(ProgressbarBorderColor);

						if (m_progressbar_border_width)
						{
							painter.fill(eRect(pb_xpos, pb_ypos, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
							painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width + m_progressbar_height, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
							painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
							painter.fill(eRect(pb_xpos + m_progressbar_border_width + pb_width, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
						}
						else
							painter.fill(eRect(pb_xpos + evt_done, pb_ypos, pb_width - evt_done,  m_progressbar_height));
					}
					if (startsWith(eventProgressConfig, "perc") && is_event) {
						if (!selected && m_color_set[eventForeground])
							painter.setForegroundColor(m_color[eventForeground]);
						else if (selected && m_color_set[eventForegroundSelected])
							painter.setForegroundColor(m_color[eventForegroundSelected]);
						else
							painter.setForegroundColor(gRGB(0x787878));

						if (isRecorded && m_record_indicator_mode == 3) {
							painter.setForegroundColor(m_color[serviceRecorded]);
						}

						char buffer[15];
						snprintf(buffer, sizeof(buffer), "%d %%", (int)(100 * (now - event_begin) / event_duration));
						std::string percent = buffer;
						ePtr<eTextPara> paraPerc = new eTextPara(eRect(pb_xpos, 0, progressBarRect.width(), m_itemheight));
						paraPerc->setFont(m_element_font[celServiceInfo]);
						paraPerc->renderString(percent.c_str());
						eRect bboxPerc = paraPerc->getBoundBox();
						painter.renderPara(paraPerc, ePoint((progressBarRect.width() - bboxPerc.width())/(eventProgressConfig == "percright" ? 1 : 2), offset.y() + (ctrlHeight - bboxPerc.height())/2));
					}
				}
			}
		}
	}
	painter.clippop();
}
