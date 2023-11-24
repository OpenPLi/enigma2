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
void join(const std::vector<std::string>& v, char c, std::string& s) {

   s.clear();

   for (std::vector<std::string>::const_iterator p = v.begin();
        p != v.end(); ++p) {
      s += *p;
      if (p != v.end() - 1)
        s += c;
   }
}

bool compareServices(const eServiceReference &ref1, const eServiceReference &ref2) {
	eServiceReference r_i = ref1;
	std::vector<std::string> ref_split = split(r_i.toString(), ":");
	std::vector<std::string> s_split = split(ref2.toString(), ":");

	if (ref_split[1] == "7" || s_split[1] == "7") {
		return ref1 == ref2;
	}

	std::vector<std::string> ref_split_r(ref_split.begin(), ref_split.begin() + 10);
	std::string ref_s;
	join(ref_split_r, ':', ref_s);

	std::vector<std::string> s_split_r(s_split.begin(), s_split.begin() + 10);
	std::string s_s;
	join(s_split_r, ':', s_s);

	if (ref_s == s_s) return true;
	// Check is it having a localhost in the service reference. If it do probably a stream relay
	// so use different logic
	if (ref2.toString().find("127.0.0.1") != std::string::npos) {
		std::string url_sr = s_split[s_split.size() - 2];
		std::vector<std::string> sr_split = split(url_sr, "/");
		std::string ref_orig = sr_split.back();
		ref_orig = replace_all(ref_orig, "%3a", ":");
		//eDebug("Ref1: %s || Ref2: %s", ref_s.c_str(), ref_orig.c_str());
		return ref_s + ":" == ref_orig;
	}

	return ref_s == s_s;
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
					if (compareServices(*i, it->second))
						return true;
				}
			}
		}
		else {
			if (compareServices(ref, it->second))
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

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

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
		else
			painter.clear();
	} else
	{
		if (local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHABLEND);
		else if (selected && !local_style->m_selection)
			painter.clear();
	}

	if (cursorValid())
	{
		if (selected && local_style && local_style->m_selection)
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHABLEND);

		// Draw the frame for selected item here so to be under the content
		if (selected && (!local_style || !local_style->m_selection))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

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
			
			eNavigation::getInstance()->getCurrentService(refCur);
			ePtr<iServiceInformation> tmp_info;
			refCur->info(tmp_info);
			std::string ref =  tmp_info->getInfoString(iServiceInformation::sServiceref);
			std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > recordedServices;
			recordedServices = eNavigation::getInstance()->getRecordingsServices();
			if (ref.find("127.0.0.1") != std::string::npos && recordedServices.size() == 0) {
				isplayable_value = 1;
			} else {
				isplayable_value = service_info->isPlayable(*m_cursor, m_is_playable_ignore);
			}

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

		int xoffset=0, xoffs=0;  // used as offset when painting the folder/marker symbol or the serviceevent progress
		int nameLeft=0, nameWidth=0, nameYoffs=0, nextYoffs=0; // used as temporary values for 'show two lines' option

		if (m_separator == "") m_separator = "  ";

		std::string text = "<N/A>";

		time_t now = time(0);

		std::string event_name = "", next_event_name = "";
		int event_begin = 0, event_duration = 0, xlpos = m_itemsize.width(), ctrlHeight=m_itemheight, yoffs=0;
		bool is_event = isPlayable && service_info && !service_info->getEvent(ref, evt);
		if (m_visual_mode == visSkinDefined) {
			if (is_event){
				event_name = evt->getEventName();
			}
			if (!event_name.empty()) {
				ctrlHeight = m_itemheight/2;
				yoffs = 5;
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

				if (m_pixmaps[picRecord] && isRecorded)
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
			if (!m_marker_alignment.empty() && m_marker_alignment == "center" && isMarker) {
				xoffsMarker = (m_itemsize.width() - bboxName.width()) / 2;
				correction = 16;
			}

			if (!isMarker && !isDirectory) {
				std::string chNum = "";
				eRect serviceNumberRect = m_element_position[celServiceNumber];
				if (serviceNumberRect.width() > 0 && m_cursor->getChannelNum() != 0) {
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
			painter.renderPara(para, ePoint(xoffsMarker - correction, offset.y() + yoffs + ((ctrlHeight - bbox.height())/2)));

			
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
				
				if (!event_name.empty())
				{
					//--------------------------------------------------- Event Progressbar -----------------------------------------------------------------
					if (progressBarRect.width() > 0) {
						int pb_xpos = xoffs;
						int pb_ypos = offset.y() + m_itemheight/2 + (m_itemheight/2 - m_progressbar_height - 2 * m_progressbar_border_width) / 2;
						int pb_width = 75 - 2 * m_progressbar_border_width;
						gRGB ProgressbarBorderColor = 0xdfdfdf;
						int evt_done = pb_width * (now - event_begin) / event_duration;

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

						xoffs += pb_width + 16;
					}

					//------------------------------------------------------- Event Name  --------------------------------------------------------------------
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

					//------------------------------------------------ Event remaining ------------------------------------------------------------------------
					std::string timeLeft_str = "";
					char buffer[15];
					snprintf(buffer, sizeof(buffer), "+%d min", timeLeft/60 );
					timeLeft_str = buffer;
					ePtr<eTextPara> paraLeft = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight/2));
					paraLeft->setFont(m_element_font[celServiceInfo]);
					paraLeft->renderString(timeLeft_str.c_str());
					eRect bboxtLeft = paraLeft->getBoundBox();
					painter.renderPara(paraLeft, ePoint(m_itemsize.width() - bboxtLeft.width() - 15, offset.y() - 2 + m_itemheight/2 + ((m_itemheight/2 - bboxtLeft.height())/2)));

					//------------------------------------------------- Event name ------------------------------------------------------------------------------
					ePtr<eTextPara> para = new eTextPara(eRect(0, 0, m_itemsize.width() - xoffs - bboxtLeft.width() - 25 - m_items_distances, m_itemheight/2));
					para->setFont(m_element_font[celServiceInfo]);
					para->renderString(text.c_str());
					eRect bbox = para->getBoundBox();
					painter.renderPara(para, ePoint(xoffs, offset.y() - 2 + m_itemheight/2 + ((m_itemheight/2 - bbox.height())/2)));
				}
			}
		} else {
			
			// Single line mode goes here
			if (is_event)
			{
				event_name = evt->getEventName();
				event_begin = evt->getBeginTime();
				event_duration = evt->getDuration();
			}
			bool hasPicons = PyCallable_Check(m_GetPiconNameFunc);

			eRect p_area = m_element_position[celServiceInfo];
			int iconWidth =	p_area.height() * 9 / 5;
			int xoffeset_marker = 0;
			int marker_text_width = 0;
			for (int e = 0; e != celServiceTypePixmap; ++e)
			{
				if (m_element_font[e])
				{
					int flags=gPainter::RT_VALIGN_CENTER;
					int yoffs = 0;
					eRect area = m_element_position[e];
					std::string text = "<N/A>";
					switch (e)
					{
					case celServiceNumber:
					{
						if (area.width() <= 0)
							continue; // no point in going on if we won't paint anything

						if( m_cursor->getChannelNum() == 0 )
							continue;

						char buffer[15];
						snprintf(buffer, sizeof(buffer), "%d", m_cursor->getChannelNum() );
						text = buffer;
						flags|=gPainter::RT_HALIGN_RIGHT;
						if (isPlayable && serviceFallback && selected && m_color_set[serviceSelectedFallback])
							painter.setForegroundColor(m_color[serviceSelectedFallback]);
						break;
					}
					case celServiceName:
					{
						if (service_info)
							service_info->getName(*m_cursor, text);
						if (!isPlayable)
						{
							area.setWidth(area.width() + m_element_position[celServiceEventProgressbar].width() +  m_nonplayable_margins);
							if (m_element_position[celServiceEventProgressbar].left() == 0)
								area.setLeft(0);
							if (m_element_position[celServiceNumber].width() && m_element_position[celServiceEventProgressbar].left() == m_element_position[celServiceNumber].width() +  m_nonplayable_margins)
								area.setLeft(m_element_position[celServiceNumber].width() +  m_nonplayable_margins);
						}
						if (!(m_record_indicator_mode == 3 && isRecorded) && isPlayable && serviceFallback && selected && m_color_set[serviceSelectedFallback])
							painter.setForegroundColor(m_color[serviceSelectedFallback]);
						if (!m_marker_alignment.empty() && m_marker_alignment == "center" && isMarker) {
							ePtr<eTextPara> paraName = new eTextPara(eRect(0, 0, m_itemsize.width(), m_itemheight/2));
							paraName->setFont(m_element_font[celServiceName]);
							paraName->renderString(text.c_str());
							eRect bboxName = paraName->getBoundBox();
							xoffeset_marker = (m_itemsize.width() - bboxName.width()) / 2;
							marker_text_width = bboxName.width();
							area.setLeft(xoffeset_marker);
							area.setWidth(marker_text_width);
						}
						break;
					}
					case celServiceInfo:
					{
						if (!event_name.empty())
						{
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
							break;
						}
						continue;
					}
					case celServiceNextInfo:
					{
						if (!next_event_name.empty())
						{
							text = m_next_title + next_event_name;
							std::replace(text.begin(), text.end(), '\n', ' ');
							if (serviceAvail)
							{
								if (!selected && m_color_set[eventNextForeground])
									painter.setForegroundColor(m_color[eventNextForeground]);
								else if (selected && m_color_set[eventNextForegroundSelected])
									painter.setForegroundColor(m_color[eventNextForegroundSelected]);
								else
									painter.setForegroundColor(gRGB(0x787878));

								if (serviceFallback && !selected && m_color_set[eventNextForegroundFallback]) // fallback receiver
									painter.setForegroundColor(m_color[eventNextForegroundFallback]);
								else if (serviceFallback && selected && m_color_set[eventNextForegroundSelectedFallback])
									painter.setForegroundColor(m_color[eventNextForegroundSelectedFallback]);
							}
							break;
						}
						continue;
					}
					case celServiceEventProgressbar:
					{
						if (area.width() > 0 && is_event)
						{
							char buffer[15];
							snprintf(buffer, sizeof(buffer), "%d %%", (int)(100 * (now - event_begin) / event_duration));
							text = buffer;
							flags|=gPainter::RT_HALIGN_RIGHT;
							break;
						}
						continue;
					}
					}

					eRect tmp = area;
					int xoffs = 0;
					ePtr<gPixmap> piconPixmap;
					bool isPIconSVG = false;
					if (e == celServiceName)
					{
						//picon stuff
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
									if (endsWith(toLower(piconFilename), ".svg")) {
										isPIconSVG = true;
									}
									if (!piconFilename.empty()) {
										loadImage(piconPixmap, piconFilename.c_str(), 0, isPIconSVG ? iconWidth : 0);
									}
								}
								Py_DECREF(pRet);
							}
						}
						xoffs = xoffset;
						tmp.setWidth(((!isPlayable || m_column_width == -1 || (!piconPixmap && !m_column_width)) ? tmp.width() : m_column_width) - xoffs);
					}

					ePtr<eTextPara> para = new eTextPara(tmp);
					para->setFont(m_element_font[e]);
					para->renderString(text.c_str());

					if (e == celServiceName)
					{
						eRect bbox = para->getBoundBox();

						int servicenameWidth = ((!isPlayable || m_column_width == -1 || (!piconPixmap && !m_column_width)) ? bbox.width() : m_column_width);
						m_element_position[celServiceInfo].setLeft(area.left() + servicenameWidth + m_items_distances + xoffs);
						m_element_position[celServiceInfo].setTop(area.top());
						m_element_position[celServiceInfo].setWidth(area.width() - (servicenameWidth + m_items_distances + xoffs));
						m_element_position[celServiceInfo].setHeight(area.height());
						if (!next_event_name.empty())
							m_element_position[celServiceNextInfo].setHeight(area.height());
						nameLeft = area.left();
						nameWidth = area.width();

						if (isPlayable)
						{
							//picon stuff
							if (hasPicons || isDirectory || (isMarker && !m_marker_as_line)) {
								eRect area = m_element_position[celServiceInfo];

								iconWidth = area.height() * 9 / 5;

								m_element_position[celServiceInfo].setLeft(area.left() + iconWidth + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - iconWidth - m_items_distances);

								xoffs += iconWidth + m_items_distances;
							}

							if (hasPicons && (m_column_width || piconPixmap))
							{
								area = m_element_position[celServiceName];
								
								if (piconPixmap)
								{

									area.moveBy(offset);
									painter.clip(area);
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
										if (isPIconSVG) {
											painter.blit(piconPixmap,
											eRect(area.left(), area.top(), iconWidth, area.height()),
											eRect(),
											pflags
											);
										} else {
											painter.blitScale(piconPixmap,
												eRect(area.left(), area.top(), iconWidth, area.height()),
												area,
												pflags);
										}
									}
									painter.clippop();
								}
							}

							//record icon stuff part1
							int rec_pixmap_xoffs = m_items_distances;
							if (isRecorded && m_record_indicator_mode == 1 && m_pixmaps[picRecord])
								rec_pixmap_xoffs = m_pixmaps[picRecord]->size().width() + m_items_distances;
							int serviceNameWidthCorr = 0;
							//service type marker stuff
							if (m_servicetype_icon_mode)
							{
								int orbpos = m_cursor->getUnsignedData(4) >> 16;
								const char *filename = ref.path.c_str();
								ePtr<gPixmap> &pixmap =
									(m_cursor->flags & eServiceReference::isGroup) ? m_pixmaps[picServiceGroup] :
									(strstr(filename, "://")) ? m_pixmaps[picStream] :
									(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
									(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];
								if (pixmap)
								{
									eSize pixmap_size = pixmap->size();
									eRect area = m_element_position[celServiceInfo];
									int offs = rec_pixmap_xoffs;
									if (m_servicetype_icon_mode == 1)
									{
										m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
										m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - offs - m_items_distances * 2);
										area = m_element_position[celServiceName];
										offs = xoffs;
										xoffs += pixmap_size.width() + m_items_distances;
										serviceNameWidthCorr = servicenameWidth + m_items_distances;
									}
									else if (m_crypto_icon_mode == 1 && m_pixmaps[picCrypto]) {
										offs = offs + m_pixmaps[picCrypto]->size().width() + m_items_distances;
										m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
										m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - offs - m_items_distances * 2);
										serviceNameWidthCorr = servicenameWidth + m_items_distances;
									}
									if (m_servicetype_icon_mode == 2) {
										m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
										m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - offs - m_items_distances * 2);
									}
									
									int correction = (area.height() - pixmap_size.height()) / 2;
									area.moveBy(offset);
									painter.clip(area);
									painter.blit(pixmap, ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
									painter.clippop();
								}
							}

							//crypto icon stuff
							if (m_crypto_icon_mode && m_pixmaps[picCrypto])
							{
								eSize pixmap_size = m_pixmaps[picCrypto]->size();
								eRect area = m_element_position[celServiceInfo];
								int offs = rec_pixmap_xoffs;
								if (m_crypto_icon_mode == 1)
								{
									area = m_element_position[celServiceName];
									offs = xoffs;
									xoffs += pixmap_size.width() + m_items_distances;
									m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
									m_element_position[celServiceInfo].setWidth(area.width() - offs - pixmap_size.width() - m_items_distances * 2);
									serviceNameWidthCorr = servicenameWidth + m_items_distances;
								}
								int correction =  (area.height() - pixmap_size.height()) / 2;
								area.moveBy(offset);
								if (service_info && service_info->isCrypted())
								{
									if (m_crypto_icon_mode == 2)
									{
										m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
										m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - offs - m_items_distances * 2);
									}
									painter.clip(area);
									painter.blit(m_pixmaps[picCrypto], ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
									painter.clippop();
								}
							}

							//record icon stuff part2
							if (isRecorded && m_record_indicator_mode < 3 && m_pixmaps[picRecord])
							{
								eSize pixmap_size = m_pixmaps[picRecord]->size();
								eRect area = m_element_position[celServiceInfo];
								int offs = m_items_distances;
								if (m_record_indicator_mode == 1)
								{
									area = m_element_position[celServiceName];
									offs = xoffs;
									xoffs += pixmap_size.width() + m_items_distances;
									m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
									m_element_position[celServiceInfo].setWidth(area.width() - offs - pixmap_size.width() - m_items_distances * 2);
									serviceNameWidthCorr = servicenameWidth + m_items_distances;
								}
								int correction = (area.height() - pixmap_size.height()) / 2;
								area.moveBy(offset);
								if (m_record_indicator_mode == 2)
								{
									m_element_position[celServiceInfo].setLeft(area.left() + offs + pixmap_size.width() + m_items_distances);
									m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - offs - m_items_distances * 2);
								}
								painter.clip(area);
								painter.blit(m_pixmaps[picRecord], ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
								painter.clippop();
							}
							m_element_position[celServiceInfo].setLeft(m_element_position[celServiceInfo].left() + serviceNameWidthCorr);
							m_element_position[celServiceInfo].setWidth(m_element_position[celServiceInfo].width() - m_items_distances * (serviceNameWidthCorr > 0 ? 2 : 1) - m_sides_margin * 2);
						}
					}

					if (flags & gPainter::RT_HALIGN_RIGHT)
						para->realign(eTextPara::dirRight);
					else if (flags & gPainter::RT_HALIGN_CENTER)
						para->realign(eTextPara::dirCenter);
					else if (flags & gPainter::RT_HALIGN_BLOCK)
						para->realign(eTextPara::dirBlock);

					if (flags & gPainter::RT_VALIGN_CENTER)
					{
						eRect bbox = para->getBoundBox();
						
						if (!next_event_name.empty() && e == celServiceNextInfo)
							yoffs = (e == celServiceNextInfo ? nextYoffs : (area.height()/2) + (((area.height()/2) - bbox.height()) / 2) - (bbox.top() - nameYoffs));
						else
							yoffs = (area.height() - bbox.height())/2 - bbox.top();
					}

					painter.renderPara(para, offset+ePoint(xoffs, yoffs));
				}
				else if ((e == celFolderPixmap && m_cursor->flags & eServiceReference::isDirectory) ||
					(e == celMarkerPixmap && m_cursor->flags & eServiceReference::isMarker &&
					!(m_cursor->flags & eServiceReference::isNumberedMarker)))
				{
					ePtr<gPixmap> &pixmap =
						(e == celFolderPixmap) ? m_pixmaps[picFolder] : m_pixmaps[picMarker];
					if (pixmap && (isDirectory || (isMarker && !m_marker_as_line)))
					{
						eSize pixmap_size = pixmap->size();
						bool notScale = (e == celMarkerPixmap) && (pixmap_size.width() < 125 || pixmap_size.height() < m_itemheight);
						eRect area;
						if (e == celFolderPixmap || m_element_position[celServiceNumber].width() < m_itemheight)
						{
							area = m_element_position[celServiceName];
							if (m_element_position[celServiceEventProgressbar].left() == 0)
								area.setLeft(0);
							if (notScale) 
								xoffset = pixmap_size.width() + m_items_distances;
							else
								xoffset = m_itemheight + m_items_distances;
						}
						else
							area = m_element_position[celServiceNumber];
						area.moveBy(offset);
						painter.clip(area);
						if (notScale) {
							int correction = (area.height() - pixmap_size.height()) / 2;
							painter.blit(pixmap, ePoint(area.left(), offset.y() + correction), area, gPainter::BT_ALPHABLEND);
						} else {
							painter.blitScale(pixmap,
											eRect(area.left(), offset.y(), m_itemheight, area.height()),
											area,
											gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER);
						}
						painter.clippop();
					}

				}
			}

			eRect area = m_element_position[celServiceEventProgressbar];
			if (area.width() > 0 && evt && !m_element_font[celServiceEventProgressbar])
			{
				int pb_xpos = area.left();
				int pb_ypos = offset.y() + (m_itemsize.height() - m_progressbar_height - 2 * m_progressbar_border_width) / 2;
				int pb_width = area.width()- 2 * m_progressbar_border_width;
				gRGB ProgressbarBorderColor = 0xdfdfdf;
				int evt_done = pb_width * (now - event_begin) / event_duration;

				// the progress data...
				eRect tmp = eRect(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width, evt_done, m_progressbar_height);
				ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
				if (pixmap) {
					painter.clip(tmp);
					painter.blit(pixmap, ePoint(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width), tmp, gPainter::BT_ALPHATEST);
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

			if (isMarker && m_marker_as_line) {
				if (m_markerline_color_set) painter.setForegroundColor(m_markerline_color);
				eRect firstLineRect = eRect(m_sides_margin + xoffset + 16, offset.y() + (m_itemheight - m_marker_as_line) / 2, xoffeset_marker - 16 - 16 - m_sides_margin - xoffset, m_marker_as_line);
				painter.fill(firstLineRect);
				int secondLineOffset = xoffeset_marker + marker_text_width + 16;
				eRect secondLineRect = eRect(secondLineOffset, offset.y() + (m_itemheight - m_marker_as_line) / 2, m_itemsize.width() - secondLineOffset - m_sides_margin - 16, m_marker_as_line);
				painter.fill(secondLineRect);
			}
		} 
	}
	painter.clippop();
}
