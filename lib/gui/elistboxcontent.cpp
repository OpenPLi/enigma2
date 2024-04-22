#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gdi/font.h>
#include <lib/python/python.h>
#include <lib/gdi/epng.h>
#include <lib/gui/ewindowstyleskinned.h>
/*
    The basic idea is to have an interface which gives all relevant list
    processing functions, and can be used by the listbox to browse trough
    the list.

    The listbox directly uses the implemented cursor. It tries hard to avoid
    iterating trough the (possibly very large) list, so it should be O(1),
    i.e. the performance should not be influenced by the size of the list.

    The list interface knows how to draw the current entry to a specified
    offset. Different interfaces can be used to adapt different lists,
    pre-filter lists on the fly etc.

		cursorSave/Restore is used to avoid re-iterating the list on redraw.
		The current selection is always selected as cursor position, the
    cursor is then positioned to the start, and then iterated. This gives
    at most 2x m_items_per_page cursor movements per redraw, indepenent
    of the size of the list.

    Although cursorSet is provided, it should be only used when there is no
    other way, as it involves iterating trough the list.
 */

iListboxContent::~iListboxContent()
{
}

iListboxContent::iListboxContent(): m_listbox(0)
{
}

void iListboxContent::setListbox(eListbox *lb)
{
	m_listbox = lb;
	m_listbox->setItemHeight(getItemHeight());
	m_listbox->setItemWidth(getItemWidth());
	m_listbox->setOrientation(getOrientation());
}

int iListboxContent::currentCursorSelectable()
{
	return 1;
}

//////////////////////////////////////

DEFINE_REF(eListboxPythonStringContent);

eListboxPythonStringContent::eListboxPythonStringContent()
	:m_cursor(0), m_saved_cursor(0), m_itemheight(25), m_itemwidth(25), m_max_text_width(0), m_orientation(1)
{
}

eListboxPythonStringContent::~eListboxPythonStringContent()
{
	Py_XDECREF(m_list);
}

void eListboxPythonStringContent::cursorHome()
{
	m_cursor = 0;
}

void eListboxPythonStringContent::cursorEnd()
{
	m_cursor = size();
}

int eListboxPythonStringContent::cursorMove(int count)
{
	m_cursor += count;

	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxPythonStringContent::cursorValid()
{
	return m_cursor < size();
}

int eListboxPythonStringContent::cursorSet(int n)
{
	m_cursor = n;

	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxPythonStringContent::cursorGet()
{
	return m_cursor;
}

int eListboxPythonStringContent::currentCursorSelectable()
{
	if (m_list && cursorValid())
	{
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor);
		if (!PyTuple_Check(item))
			return 1;
		if (PyTuple_Size(item) >= 2)
			return 1;
	}
	return 0;
}

void eListboxPythonStringContent::cursorSave()
{
	m_saved_cursor = m_cursor;
}

void eListboxPythonStringContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
}

int eListboxPythonStringContent::size()
{
	if (!m_list)
		return 0;
	return PyList_Size(m_list);
}

void eListboxPythonStringContent::setSize(const eSize &size)
{
	m_itemsize = size;
}

int eListboxPythonStringContent::getMaxItemTextWidth()
{
	ePtr<gFont> fnt;
	eListboxStyle *local_style = 0;
	int m_text_offset = 1;
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();
	if (local_style) {
		fnt = local_style->m_font;
		m_text_offset = local_style->m_text_offset.x();
	}
	if (!fnt) fnt = new gFont("Regular", 20);

	for (int i = 0; i < size(); i++)
	{
		ePyObject item = PyList_GET_ITEM(m_list, i);
		if (PyTuple_Check(item))
		{
			item = PyTuple_GET_ITEM(item, 0);
		}
		if (item != Py_None) {
			const char *string = PyUnicode_Check(item) ? PyUnicode_AsUTF8(item) : "<not-a-string>";
			eRect textRect = eRect(0,0, 8000, 100);

			ePtr<eTextPara> para = new eTextPara(textRect);
			para->setFont(fnt);
			para->renderString(string);
			int textWidth = para->getBoundBox().width();
			if (textWidth > m_max_text_width) {
				m_max_text_width = textWidth;
			}
		}
	}

	return m_max_text_width + (m_text_offset*2);
}

void eListboxPythonStringContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt;
	eRect itemRect(offset, m_itemsize);
	painter.clip(itemRect);
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	bool validitem = (m_list && cursorValid());
	eListboxStyle *local_style = 0;
	bool cursorValid = this->cursorValid();
	gRGB border_color;
	int border_size = 0;
	int radius = 0;
	int edges = 0;

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	if (local_style)
	{
		border_size = local_style->m_border_size;
		border_color = local_style->m_border_color;
		radius = local_style->cornerRadius(selected ? 1:0);
		edges = local_style->cornerRadiusEdges(selected ? 1:0);
		fnt = local_style->m_font;
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
	if (!fnt) fnt = new gFont("Regular", 20);
	bool isverticallb = m_listbox && m_listbox->getOrientation() == 1;
	/* if we have no transparent background */
	if (!local_style || !local_style->m_transparent_background)
	{
			/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background && cursorValid)
		{
			if (isverticallb){
				if (validitem) painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_background->size().height()) / 2), eRect(), 0);
			} else {
				if (validitem) painter.blit(local_style->m_background, ePoint(offset.x() + (m_itemsize.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), 0);
			}
		}
		else if (local_style && !local_style->m_background && cursorValid && radius)
		{
			if(radius)
				painter.setRadius(radius, edges);
			painter.drawRectangle(itemRect);
		}
		else
			painter.clear();
	} else
	{
		if (local_style->m_background && cursorValid)
		{
			if (isverticallb){
				if (validitem) painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_background->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
			} else {
				if (validitem) painter.blit(local_style->m_background, ePoint(offset.x() + (m_itemsize.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
			}
		}
		else if (selected && !local_style->m_selection && cursorValid && !radius && !local_style->m_background)
			painter.clear();
	}

	// Draw frame here so to be under the content
	if (selected && (!local_style || !local_style->m_selection) && (!local_style || !local_style->m_border_set))
		style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

	if (validitem)
	{
		int gray = 0;
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
		painter.setFont(fnt);

			/* the user can supply tuples, in this case the first one will be displayed. */
		if (PyTuple_Check(item))
		{
			if (PyTuple_Size(item) == 1)
				gray = 1;
			item = PyTuple_GET_ITEM(item, 0);
		}

		if (selected && local_style && local_style->m_selection)
		{
			if (isverticallb)
				painter.blit(local_style->m_selection, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_selection->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
			else
				painter.blit(local_style->m_selection, ePoint(offset.x() + (m_itemsize.width() - local_style->m_selection->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
		}
		else if (selected && local_style && radius && !local_style->m_selection) {
			if(radius)
				painter.setRadius(radius, edges);
			painter.drawRectangle(itemRect);
		}

		if (item == Py_None)
		{
				/* seperator */
			if (isverticallb)
			{
				int half_height = m_itemsize.height() / 2;
				painter.fill(eRect(offset.x() + half_height, offset.y() + half_height - 2, m_itemsize.width() - m_itemsize.height(), 4));
			}
			else
			{
				int half_width = m_itemsize.width() / 2;
				painter.fill(eRect(offset.x() + half_width, offset.y() + half_width - 2, m_itemsize.width() - m_itemsize.height(), 4));
			}
		} else
		{
			const char *string = PyUnicode_Check(item) ? PyUnicode_AsUTF8(item) : "<not-a-string>";
			ePoint text_offset = offset;
			ePoint style_text_offset = ePoint(0, 0);
			if (gray)
				painter.setForegroundColor(gRGB(0x808080));

			int flags = 0;
			if (local_style)
			{
				style_text_offset = local_style->m_text_offset;
				text_offset += style_text_offset;

				if (local_style->m_valign == eListboxStyle::alignTop)
					flags |= gPainter::RT_VALIGN_TOP;
				else if (local_style->m_valign == eListboxStyle::alignCenter)
					flags |= gPainter::RT_VALIGN_CENTER;
				else if (local_style->m_valign == eListboxStyle::alignBottom)
					flags |= gPainter::RT_VALIGN_BOTTOM;

				if (local_style->m_halign == eListboxStyle::alignLeft)
					flags |= gPainter::RT_HALIGN_LEFT;
				else if (local_style->m_halign == eListboxStyle::alignCenter)
					flags |= gPainter::RT_HALIGN_CENTER;
				else if (local_style->m_halign == eListboxStyle::alignRight)
					flags |= gPainter::RT_HALIGN_RIGHT;
				else if (local_style->m_halign == eListboxStyle::alignBlock)
					flags |= gPainter::RT_HALIGN_BLOCK;
			}

			// Here we have to compensate the local style text offset from both sides
			painter.renderText(eRect(text_offset.x(), text_offset.y(), m_itemsize.width() - style_text_offset.x()*2, m_itemsize.height() - style_text_offset.y()*2), string, flags, border_color, border_size);
		}
	}

	painter.clippop();
}

void eListboxPythonStringContent::setList(ePyObject list)
{
	Py_XDECREF(m_list);
	if (!PyList_Check(list))
	{
		m_list = ePyObject();
	} else
	{
		m_list = list;
		Py_INCREF(m_list);
	}

	if (m_listbox)
		m_listbox->entryReset(false);
}

void eListboxPythonStringContent::setOrientation(int orientation)
{
	m_orientation = orientation;
	if (m_listbox){
		m_listbox->setOrientation(orientation);
	}
}

void eListboxPythonStringContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox)
		m_listbox->setItemHeight(height);
}

void eListboxPythonStringContent::setItemWidth(int width)
{
	m_itemwidth = width;
	if (m_listbox)
		m_listbox->setItemWidth(width);
}

PyObject *eListboxPythonStringContent::getCurrentSelection()
{
	if (!(m_list && cursorValid()))
		Py_RETURN_NONE;

	ePyObject r = PyList_GET_ITEM(m_list, m_cursor);
	Py_XINCREF(r);
	return r;
}

void eListboxPythonStringContent::invalidateEntry(int index)
{
	if (m_listbox)
		m_listbox->entryChanged(index);
}

void eListboxPythonStringContent::invalidate()
{
	if (m_listbox)
	{
		int s = size();
		if ( m_cursor >= s )
			m_listbox->moveSelectionTo(s?s-1:0);
		else
			m_listbox->invalidate();
	}
}

//////////////////////////////////////

RESULT SwigFromPython(ePtr<gPixmap> &res, PyObject *obj);

void eListboxPythonConfigContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt;
	ePtr<gFont> fnt2;
	eRect itemrect(offset, m_itemsize);
	eListboxStyle *local_style = 0;
	bool cursorValid = this->cursorValid();
	gRGB border_color;
	int border_size = 0;
	int radius = 0;
	int edges = 0;

	painter.clip(itemrect);
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	if (local_style)
	{
		border_size = local_style->m_border_size;
		border_color = local_style->m_border_color;
		fnt = local_style->m_font;
		fnt2 = local_style->m_secondfont;
		radius = local_style->cornerRadius(selected ? 1:0);
		edges = local_style->cornerRadiusEdges(selected ? 1:0);
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

	if (!fnt)
		fnt = new gFont("Regular", 20);
	if (!fnt2)
		fnt2 = new gFont(fnt->family, fnt->pointSize - fnt->pointSize/5);

	if (!local_style || !local_style->m_transparent_background)
		/* if we have no transparent background */
	{
		/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background && cursorValid) {
			if (m_listbox && m_listbox->getOrientation() == 1)
				painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_background->size().height()) / 2), eRect(), 0);
			else
				painter.blit(local_style->m_background, ePoint(offset.x() + (m_itemsize.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), 0);
		}
		else if (local_style && !local_style->m_background && cursorValid && radius)
		{
			if(radius)
				painter.setRadius(radius, edges);
			painter.drawRectangle(itemrect);
		}
		else
			painter.clear();
	} else
	{
		if (local_style->m_background && cursorValid)
			if (m_listbox && m_listbox->getOrientation() == 1)
				painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_background->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
			else
				painter.blit(local_style->m_background, ePoint(offset.x() + (m_itemsize.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
		else if (selected && !local_style->m_selection && !radius)
			painter.clear();
	}

	// Draw frame here so to be drawn under icons
	if (selected && (!local_style || !local_style->m_selection) && (!local_style || !local_style->m_border_set))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

	if (m_list && cursorValid)
	{
			/* get current list item */
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
		ePyObject text, value;
		painter.setFont(fnt);

		if (selected && local_style && local_style->m_selection){
			if (m_listbox && m_listbox->getOrientation() == 1)
				painter.blit(local_style->m_selection, ePoint(offset.x(), offset.y() + (m_itemsize.height() - local_style->m_selection->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
			else
				painter.blit(local_style->m_selection, ePoint(offset.x() + (m_itemsize.width() - local_style->m_selection->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
		} else if (selected && radius && !local_style->m_selection) {
			if(radius)
				painter.setRadius(radius, edges);
			painter.drawRectangle(itemrect);
		}
			/* the first tuple element is a string for the left side.
			   the second one will be called, and the result shall be an tuple.

			   of this tuple,
			   the first one is the type (string).
			   the second one is the value. */
		if (PyTuple_Check(item))
		{
				/* handle left part. get item from tuple, convert to string, display. */
			text = PyTuple_GET_ITEM(item, 0);
			text = PyObject_Str(text); /* creates a new object - old object was borrowed! */
			const char *string = (text && PyUnicode_Check(text)) ? PyUnicode_AsUTF8(text) : "<not-a-string>";
			painter.renderText(eRect(ePoint(offset.x()+15, offset.y()), m_itemsize), string,
			gPainter::RT_HALIGN_LEFT | gPainter::RT_VALIGN_CENTER, border_color, border_size);
			Py_XDECREF(text);

				/* when we have no label, align value to the left. (FIXME:
				   don't we want to specifiy this individually?) */
			int value_alignment_left = !*string;

				/* now, handle the value. get 2nd part from tuple*/
			if (PyTuple_Size(item) >= 2) // when no 2nd entry is in tuple this is a non selectable entry without config part
				value = PyTuple_GET_ITEM(item, 1);

			if (value)
			{
				ePyObject args = PyTuple_New(1);
				PyTuple_SET_ITEM(args, 0, PyLong_FromLong(selected));

					/* CallObject will call __call__ which should return the value tuple */
				value = PyObject_CallObject(value, args);

				if (PyErr_Occurred())
					PyErr_Print();

				Py_DECREF(args);
					/* the PyInt was stolen. */
			}

				/*  check if this is really a tuple */
			if (value && PyTuple_Check(value))
			{
					/* convert type to string */
				ePyObject type = PyTuple_GET_ITEM(value, 0);
				const char *atype = (type && PyUnicode_Check(type)) ? PyUnicode_AsUTF8(type) : 0;

				if (atype)
				{
					if (!strcmp(atype, "text"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						const char *value = (pvalue && PyUnicode_Check(pvalue)) ? PyUnicode_AsUTF8(pvalue) : "<not-a-string>";
						painter.setFont(fnt2);
						if (value_alignment_left)
							painter.renderText(eRect(ePoint(offset.x()-15, offset.y()), m_itemsize), value, gPainter::RT_HALIGN_LEFT | gPainter::RT_VALIGN_CENTER, border_color, border_size);
						else
							painter.renderText(eRect(ePoint(offset.x()-15, offset.y()), m_itemsize), value, gPainter::RT_HALIGN_RIGHT| gPainter::RT_VALIGN_CENTER, border_color, border_size);

							/* pvalue is borrowed */
					} else if (!strcmp(atype, "slider"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						ePyObject psize = PyTuple_GET_ITEM(value, 2);

							/* convert value to Long. fallback to -1 on error. */
						int value = (pvalue && PyLong_Check(pvalue)) ? PyLong_AsLong(pvalue) : -1;
						int size = (pvalue && PyLong_Check(psize)) ? PyLong_AsLong(psize) : 100;

							/* calc. slider length */
						int width = (m_itemsize.width() - m_seperation - 15) * value / size;
						int height = m_itemsize.height();


							/* draw slider */
						//painter.fill(eRect(offset.x() + m_seperation, offset.y(), width, height));
						if (m_slider_height % 2 != height % 2)
							m_slider_height -= 1;
						if(m_slider_height + 2*m_slider_space >= height) // frame out of selector = without frame
							m_slider_space = 0;
						int slider_y_offset = (height - m_slider_height) / 2;
						if (m_slider_space)
						{
							ePoint tl(offset.x() + m_seperation, offset.y() + slider_y_offset - m_slider_space - 1);
							ePoint tr(offset.x() + m_itemsize.width() - 15 - 1, tl.y());
							ePoint bl(tl.x(), offset.y() + slider_y_offset + m_slider_height + m_slider_space);
							ePoint br(tr.x(), bl.y());
							painter.line(tl, tr);
							painter.line(tr, br);
							painter.line(br, bl);
							painter.line(bl, tl);
							painter.fill(eRect(offset.x() + m_seperation + m_slider_space + 1, offset.y() + slider_y_offset, width - 2*(m_slider_space + 1), m_slider_height));
						}
						else
						{
							painter.fill(eRect(offset.x() + m_seperation, offset.y() + slider_y_offset, width, m_slider_height));
						}

							/* pvalue is borrowed */
					} else if (!strcmp(atype, "mtext"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						const char *text = (pvalue && PyUnicode_Check(pvalue)) ? PyUnicode_AsUTF8(pvalue) : "<not-a-string>";
						ePtr<eTextPara> para = new eTextPara(eRect(ePoint(offset.x()-15, offset.y()), m_itemsize));
						para->setFont(fnt2);
						para->renderString(text, 0);

						if (value_alignment_left)
							para->realign(eTextPara::dirLeft);
						else
							para->realign(eTextPara::dirRight);

						int glyphs = para->size();

						ePyObject plist;

						if (PyTuple_Size(value) >= 3)
							plist = PyTuple_GET_ITEM(value, 2);

						int entries = 0;

						if (plist && PyList_Check(plist))
							entries = PyList_Size(plist);

						int left=0, right=0, last=-1, top=0, bottom=0;
						bool isVertLB = m_listbox && m_listbox->getOrientation() == 1;
						eRect bbox;
						eRect pbox = para->getBoundBox();
						for (int i = 0; i < entries; ++i)
						{
							ePyObject entry = PyList_GET_ITEM(plist, i);
							int num = PyLong_Check(entry) ? PyLong_AsLong(entry) : -1;

							if ((num < 0) || (num >= glyphs))
								eWarning("[eListboxPythonMultiContent] glyph index %d in PythonConfigList out of bounds!", num);
							else
							{
								if (last+1 != num && last != -1) {
									if (isVertLB)
										bbox = eRect(left, offset.y(), right-left, (m_itemsize.height() - pbox.height()) / 2);
									else
										bbox = eRect(offset.x(), top, bottom-top, (m_itemsize.width() - pbox.width()) / 2);
									painter.fill(bbox);
								}
								para->setGlyphFlag(num, GS_INVERT);
								bbox = para->getGlyphBBox(num);
								if (last+1 != num || last == -1){
									if (isVertLB)
										left = bbox.left();
									else
										top = bbox.top();
								}
								if (isVertLB)
									right = bbox.left() + bbox.width();
								else
									bottom = bbox.top() + bbox.height();
								last = num;
							}
							/* entry is borrowed */
						}
						if (last != -1) {
							if (isVertLB)
								bbox = eRect(left, offset.y() + (m_itemsize.height() - pbox.height()) / 2, right - left, pbox.height());
							else
								bbox = eRect(offset.x() + (m_itemsize.width() - pbox.width()) / 2, top , bottom - top, pbox.width());
							painter.fill(bbox);
						}
						if (isVertLB)
							painter.renderPara(para, ePoint(0, m_itemsize.height() - pbox.height()) / 2);
						else
							painter.renderPara(para, ePoint(m_itemsize.width() - pbox.width(), 0) / 2);
						/* pvalue is borrowed */
						/* plist is 0 or borrowed */
					}
					else if (!strcmp(atype, "pixmap"))
					{
						ePyObject data;
						ePyObject ppixmap = PyTuple_GET_ITEM(value, 1);

						if (PyLong_Check(ppixmap) && data) /* if the pixemap is in fact a number, it refers to the 'data' list. */
							ppixmap = PyTuple_GetItem(data, PyLong_AsLong(ppixmap));

						ePtr<gPixmap> pixmap;
						if (SwigFromPython(pixmap, ppixmap))
						{
							eDebug("[eListboxPythonMultiContent] (Pixmap) get pixmap failed");
							const char *value = (ppixmap && PyUnicode_Check(ppixmap)) ? PyUnicode_AsUTF8(ppixmap) : "<not-a-string>";
							painter.setFont(fnt2);
							if (value_alignment_left)
								painter.renderText(eRect(ePoint(offset.x()-15, offset.y()), m_itemsize), value, gPainter::RT_HALIGN_LEFT | gPainter::RT_VALIGN_CENTER, border_color, border_size);
							else
								painter.renderText(eRect(ePoint(offset.x()-15, offset.y()), m_itemsize), value, gPainter::RT_HALIGN_RIGHT| gPainter::RT_VALIGN_CENTER, border_color, border_size);
						}
						else
						{
							eRect rect(ePoint(m_itemsize.width() - pixmap->size().width() - 15, offset.y() + (m_itemsize.height() - pixmap->size().height()) / 2), pixmap->size());
							painter.clip(rect);
							painter.blit(pixmap, rect.topLeft(), rect, gPainter::BT_ALPHABLEND);
							painter.clippop();
						}
					}
				}
				/* type is borrowed */
			} else if (value)
				eWarning("[eListboxPythonConfigContent] second value of tuple is not a tuple.");
			if (value)
				Py_DECREF(value);
		}

	}

	painter.clippop();
}

int eListboxPythonConfigContent::currentCursorSelectable()
{
	return eListboxPythonStringContent::currentCursorSelectable();
}

//////////////////////////////////////

	/* todo: make a real infrastructure here! */
RESULT SwigFromPython(ePtr<gPixmap> &res, PyObject *obj);

eListboxPythonMultiContent::eListboxPythonMultiContent()
	:m_clip(gRegion::invalidRegion()), m_old_clip(gRegion::invalidRegion())
{
}

eListboxPythonMultiContent::~eListboxPythonMultiContent()
{
	Py_XDECREF(m_buildFunc);
	Py_XDECREF(m_selectableFunc);
	Py_XDECREF(m_template);
}

void eListboxPythonMultiContent::setSelectionClip(eRect &rect, bool update)
{
	m_selection_clip = rect;
	if (m_listbox)
		rect.moveBy(ePoint(0, m_listbox->getEntryTop()));
	if (m_clip.valid())
		m_clip |= rect;
	else
		m_clip = rect;
	if (update && m_listbox)
		m_listbox->entryChanged(m_cursor);
}

static void clearRegionHelper(gPainter &painter, eListboxStyle *local_style, const ePoint &offset, const eSize &size, ePyObject &pbackColor, bool cursorValid, bool clear=true, bool isverticallb=true)
{
	if (pbackColor)
	{
		unsigned int color = PyLong_AsUnsignedLongMask(pbackColor);
		painter.setBackgroundColor(gRGB(color));
	}
	else if (local_style)
	{
		if (local_style->m_background_color_set)
			painter.setBackgroundColor(local_style->m_background_color);
		if (local_style->m_background && cursorValid)
		{
			if (isverticallb)
			{
				if (local_style->m_transparent_background)
					painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (size.height() - local_style->m_background->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
				else
					painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (size.height() - local_style->m_background->size().height()) / 2), eRect(), 0);
			}
			else
			{
				if (local_style->m_transparent_background)
					painter.blit(local_style->m_background, ePoint(offset.x() + (size.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
				else
					painter.blit(local_style->m_background, ePoint(offset.x() + (size.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), 0);
			}
			return;
		}
		else if (local_style->m_transparent_background)
			return;
	}
	if (clear)
		painter.clear();
}

static void clearRegionSelectedHelper(gPainter &painter, eListboxStyle *local_style, const ePoint &offset, const eSize &size, ePyObject &pbackColorSelected, bool cursorValid, bool clear=true, bool isverticallb=true)
{
	if (pbackColorSelected)
	{
		unsigned int color = PyLong_AsUnsignedLongMask(pbackColorSelected);
		painter.setBackgroundColor(gRGB(color));
	}
	else if (local_style)
	{
		if (local_style->m_background_color_selected_set)
			painter.setBackgroundColor(local_style->m_background_color_selected);
		if (local_style->m_background && cursorValid)
		{
			if (isverticallb)
			{
				if (local_style->m_transparent_background)
					painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (size.height() - local_style->m_background->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
				else
					painter.blit(local_style->m_background, ePoint(offset.x(), offset.y() + (size.height() - local_style->m_background->size().height()) / 2), eRect(), 0);
			}
			else
			{
				if (local_style->m_transparent_background)
					painter.blit(local_style->m_background, ePoint(offset.x() + (size.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
				else
					painter.blit(local_style->m_background, ePoint(offset.x() + (size.width() - local_style->m_background->size().width()) / 2, offset.y()), eRect(), 0);
			}
			return;
		}
	}
	if (clear)
		painter.clear();
}

static void clearRegion(gPainter &painter, eWindowStyle &style, eListboxStyle *local_style, ePyObject pforeColor, ePyObject pforeColorSelected, ePyObject pbackColor, ePyObject pbackColorSelected, int selected, gRegion &rc, eRect &sel_clip, const ePoint &offset, const eSize &size, bool cursorValid, bool clear=true, bool isverticallb=true)
{
	if (selected && sel_clip.valid())
	{
		gRegion part = rc - sel_clip;
		if (!part.empty())
		{
			painter.clip(part);
			style.setStyle(painter, eWindowStyle::styleListboxNormal);
			clearRegionHelper(painter, local_style, offset, size, pbackColor, cursorValid, clear, isverticallb);
			painter.clippop();
			selected = 0;
		}
		part = rc & sel_clip;
		if (!part.empty())
		{
			painter.clip(part);
			style.setStyle(painter, eWindowStyle::styleListboxSelected);
			clearRegionSelectedHelper(painter, local_style, offset, size, pbackColorSelected, cursorValid, clear, isverticallb);
			painter.clippop();
			selected = 1;
		}
	}
	else if (selected)
	{
		style.setStyle(painter, eWindowStyle::styleListboxSelected);
		clearRegionSelectedHelper(painter, local_style, offset, size, pbackColorSelected, cursorValid, clear, isverticallb);
		if (local_style && local_style->m_selection) {
			if (isverticallb)
				painter.blit(local_style->m_selection, ePoint(offset.x(), offset.y() + (size.height() - local_style->m_selection->size().height()) / 2), eRect(), gPainter::BT_ALPHATEST);
			else
				painter.blit(local_style->m_selection, ePoint(offset.x() + (size.width() - local_style->m_selection->size().width()) / 2, offset.y()), eRect(), gPainter::BT_ALPHATEST);
		}
	}
	else
	{
		style.setStyle(painter, eWindowStyle::styleListboxNormal);
		clearRegionHelper(painter, local_style, offset, size, pbackColor, cursorValid, clear, isverticallb);
	}

	if (selected)
	{
		if (pforeColorSelected)
		{
			unsigned int color = PyLong_AsUnsignedLongMask(pforeColorSelected);
			painter.setForegroundColor(gRGB(color));
		}
		/* if we have a local foreground color set, use that. */
		else if (local_style && local_style->m_foreground_color_selected_set)
			painter.setForegroundColor(local_style->m_foreground_color_selected);
	}
	else
	{
		if (pforeColor)
		{
			unsigned int color = PyLong_AsUnsignedLongMask(pforeColor);
			painter.setForegroundColor(gRGB(color));
		}
		/* if we have a local foreground color set, use that. */
		else if (local_style && local_style->m_foreground_color_set)
			painter.setForegroundColor(local_style->m_foreground_color);
	}
}

static ePyObject lookupColor(ePyObject color, ePyObject data)
{
	if (color == Py_None)
		return ePyObject();

	if ((!color) && (!data))
		return color;

	unsigned int icolor = PyLong_AsUnsignedLongMask(color);

		/* check if we have the "magic" template color */
	if (data && (icolor & 0xFF000000) == 0xFF000000)
	{
		int index = icolor & 0xFFFFFF;
		if (PyTuple_GetItem(data, index) == Py_None)
			return ePyObject();
		return PyTuple_GetItem(data, index);
	}

	if (color == Py_None)
		return ePyObject();

	return color;
}

int eListboxPythonMultiContent::getMaxItemTextWidth()
{
	ePtr<gFont> fnt;
	eListboxStyle *local_style = 0;
	int m_text_offset = 1;
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();
	if (local_style) {
		fnt = local_style->m_font;
		m_text_offset = local_style->m_text_offset.x();
	}
	if (!fnt) fnt = new gFont("Regular", 20);

	ePyObject items, buildfunc_ret;
	if (m_list) {
		for (int k = 0; k < size(); k++)
		{
			items = PyList_GET_ITEM(m_list, k); // borrowed reference!

			if (m_buildFunc)
			{
				if (PyCallable_Check(m_buildFunc))  // when we have a buildFunc then call it
				{
					if (PyTuple_Check(items))
						buildfunc_ret = items = PyObject_CallObject(m_buildFunc, items);
					else
						eDebug("[eListboxPythonMultiContent] items is not a tuple");
				}
				else
					eDebug("[eListboxPythonMultiContent] buildfunc is not callable");
			}

			ePyObject data;

				/* if we have a template, use the template for the actual formatting.
					we will later detect that "data" is present, and refer to that, instead
					of the immediate value. */
			int start = 1;
			if (m_template)
			{
				data = items;
				items = m_template;
				start = 0;
			}

			int items_size = PyList_Size(items);
			for (int i = start; i < items_size; ++i) {
				ePyObject item = PyList_GET_ITEM(items, i); // borrowed reference!

				if (!item)
				{
					eDebug("[eListboxPythonMultiContent] no items[%d] ?", i);
					continue;
				}

				if (!PyTuple_Check(item))
				{
					eDebug("[eListboxPythonMultiContent] items[%d] is not a tuple.", i);
					continue;
				}

				int size = PyTuple_Size(item);

				if (!size)
				{
					eDebug("[eListboxPythonMultiContent] items[%d] is an empty tuple.", i);
					continue;
				}

				int type = PyLong_AsLong(PyTuple_GET_ITEM(item, 0));

				switch (type)
				{
				case TYPE_TEXT: // text
				{
					ePyObject px = PyTuple_GET_ITEM(item, 1), pfnt = PyTuple_GET_ITEM(item, 5), pstring = PyTuple_GET_ITEM(item, 7);

					if (PyLong_Check(pstring) && data) /* if the string is in fact a number, it refers to the 'data' list. */
						pstring = PyTuple_GetItem(data, PyLong_AsLong(pstring));

					if (pfnt) {
						int fnt_i = PyLong_AsLong(pfnt);
						if (m_font.find(fnt_i) != m_font.end()) fnt = m_font[fnt_i];
					}

								/* don't do anything if we have 'None' as string */
					if (pstring == Py_None)
						continue;

					const char *string = (PyUnicode_Check(pstring)) ? PyUnicode_AsUTF8(pstring) : "<not-a-string>";
					eRect textRect = eRect(0,0, 9999, 100);

					ePtr<eTextPara> para = new eTextPara(textRect);
					para->setFont(fnt);
					para->renderString(string);
					int textWidth = para->getBoundBox().width() + PyLong_AsLong(px);
					if (textWidth > m_max_text_width) {
						m_max_text_width = textWidth;
					}
					break;
				}
				}

			}
		}

	}

	return m_max_text_width + (m_text_offset*2);
}

void eListboxPythonMultiContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	eRect itemRect = eRect(offset, m_itemsize);
	gRegion itemregion(itemRect);
	eListboxStyle *local_style = 0;
	eRect sel_clip(m_selection_clip);
	bool cursorValid = this->cursorValid();
	bool isverticallb = true;

	if (sel_clip.valid())
		sel_clip.moveBy(offset);

		/* get local listbox style, if present */
	if (m_listbox)
	{
		local_style = m_listbox->getLocalStyle();
		isverticallb = m_listbox->getOrientation() == 1;
	}

	painter.clip(itemregion);

	if(local_style) {
		int mode = (selected) ? 1:0;
		int radius = local_style->cornerRadius(mode);
		int edges = local_style->cornerRadiusEdges(mode);
		if (radius) {
			gRGB color = style.getColor(selected ? eWindowStyleSkinned::colListboxSelectedBackground : eWindowStyleSkinned::colListboxBackground);;
			if (selected && local_style->m_background_color_selected_set)
				color = local_style->m_background_color_selected;
			if (!selected && local_style->m_background_color_set)
				color = local_style->m_background_color;

			painter.setRadius(radius, edges);
			painter.setBackgroundColor(gRGB(color));
			painter.drawRectangle(itemRect);
		}
		else
			clearRegion(painter, style, local_style, ePyObject(), ePyObject(), ePyObject(), ePyObject(), selected, itemregion, sel_clip, offset, m_itemsize, cursorValid, true, isverticallb);
	}
	else
		clearRegion(painter, style, local_style, ePyObject(), ePyObject(), ePyObject(), ePyObject(), selected, itemregion, sel_clip, offset, m_itemsize, cursorValid, true, isverticallb);

	// Draw frame here so to be under the content
	if (selected && !sel_clip.valid() && (!local_style || !local_style->m_selection) && (!local_style || !local_style->m_border_set))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

	ePyObject items, buildfunc_ret;

	if (m_list && cursorValid)
	{
			/* a multicontent list can be used in two ways:
				either each item is a list of (TYPE,...)-tuples,
				or there is a template defined, which is a list of (TYPE,...)-tuples,
				and the list is an unformatted tuple. The template then references items from the list.
			*/
		items = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!

		if (m_buildFunc)
		{
			if (PyCallable_Check(m_buildFunc))  // when we have a buildFunc then call it
			{
				if (PyTuple_Check(items))
					buildfunc_ret = items = PyObject_CallObject(m_buildFunc, items);
				else
					eDebug("[eListboxPythonMultiContent] items is not a tuple");
			}
			else
				eDebug("[eListboxPythonMultiContent] buildfunc is not callable");
		}

		if (!items)
		{
			PyErr_Print();
			eDebug("[eListboxPythonMultiContent] error getting item %d", m_cursor);
			goto error_out;
		}

		if (!m_template)
		{
			if (!PyList_Check(items))
			{
				eDebug("[eListboxPythonMultiContent] list entry %d is not a list (non-templated)", m_cursor);
				goto error_out;
			}
		} else
		{
			if (!PyTuple_Check(items))
			{
				eDebug("[eListboxPythonMultiContent] list entry %d is not a tuple (templated)", m_cursor);
				goto error_out;
			}
		}

		ePyObject data;

			/* if we have a template, use the template for the actual formatting.
				we will later detect that "data" is present, and refer to that, instead
				of the immediate value. */
		int start = 1;
		if (m_template)
		{
			data = items;
			items = m_template;
			start = 0;
		}

		int items_size = PyList_Size(items);
		for (int i = start; i < items_size; ++i)
		{
			ePyObject item = PyList_GET_ITEM(items, i); // borrowed reference!

			if (!item)
			{
				eDebug("[eListboxPythonMultiContent] no items[%d] ?", i);
				goto error_out;
			}

			if (!PyTuple_Check(item))
			{
				eDebug("[eListboxPythonMultiContent] items[%d] is not a tuple.", i);
				goto error_out;
			}

			int size = PyTuple_Size(item);

			if (!size)
			{
				eDebug("[eListboxPythonMultiContent] items[%d] is an empty tuple.", i);
				goto error_out;
			}

			int type = PyLong_AsLong(PyTuple_GET_ITEM(item, 0));

			switch (type)
			{
			case TYPE_TEXT: // text
			{
			/*
				(0, x, y, width, height, fnt, flags, "bla" [, color, colorSelected, backColor, backColorSelected, borderWidth, borderColor] )
			*/
				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							pfnt = PyTuple_GET_ITEM(item, 5),
							pflags = PyTuple_GET_ITEM(item, 6),
							pstring = PyTuple_GET_ITEM(item, 7),
							pforeColor, pforeColorSelected, pbackColor, pbackColorSelected, pborderWidth, pborderColor, pCornerRadius, pCornerEdges, pTextBorderWidth, pTextBorderColor;

				if (!(px && py && pwidth && pheight && pfnt && pflags && pstring))
				{
					eDebug("[eListboxPythonMultiContent] tuple too small (must be (TYPE_TEXT, x, y, width, height, font, flags, string [, color, colorSelected, backColor, backColorSelected, borderWidth, borderColor])");
					goto error_out;
				}

				if (size > 8)
					pforeColor = lookupColor(PyTuple_GET_ITEM(item, 8), data);

				if (size > 9)
					pforeColorSelected = lookupColor(PyTuple_GET_ITEM(item, 9), data);

				if (size > 10)
					pbackColor = lookupColor(PyTuple_GET_ITEM(item, 10), data);

				if (size > 11)
					pbackColorSelected = lookupColor(PyTuple_GET_ITEM(item, 11), data);

				if (size > 12)
				{
					pborderWidth = PyTuple_GET_ITEM(item, 12);
					if (pborderWidth == Py_None)
						pborderWidth=ePyObject();
				}
				if (size > 13)
					pborderColor = lookupColor(PyTuple_GET_ITEM(item, 13), data);

				if (size > 14)
					pCornerRadius = PyTuple_GET_ITEM(item, 14);

				if (size > 15)
					pCornerEdges = PyTuple_GET_ITEM(item, 15);

				if (size > 16)
					pTextBorderWidth = PyTuple_GET_ITEM(item, 16);

				if (size > 17)
					pTextBorderColor = lookupColor(PyTuple_GET_ITEM(item, 17), data);

				if (PyLong_Check(pstring) && data) /* if the string is in fact a number, it refers to the 'data' list. */
					pstring = PyTuple_GetItem(data, PyLong_AsLong(pstring));

							/* don't do anything if we have 'None' as string */
				if (pstring == Py_None)
					continue;

				const char *string = (PyUnicode_Check(pstring)) ? PyUnicode_AsUTF8(pstring) : "<not-a-string>";
				int x = (PyFloat_Check(px) ? (int)PyFloat_AsDouble(px) : PyLong_AsLong(px)) + offset.x();
				int y = (PyFloat_Check(py) ? (int)PyFloat_AsDouble(py) : PyLong_AsLong(py)) + offset.y();
				int width = PyFloat_Check(pwidth) ? (int)PyFloat_AsDouble(pwidth) : PyLong_AsLong(pwidth);
				int height = PyFloat_Check(pheight) ? (int)PyFloat_AsDouble(pheight) : PyLong_AsLong(pheight);
				int flags = PyLong_AsLong(pflags);
				int fnt = PyLong_AsLong(pfnt);
				int bwidth = pborderWidth ? PyLong_AsLong(pborderWidth) : 0;
				int btwidth = pTextBorderWidth ? PyLong_AsLong(pTextBorderWidth) : 0;

				int cornerRadius = pCornerRadius ? PyLong_AsLong(pCornerRadius) : 0;
				int cornerEdges = pCornerEdges ? PyLong_AsLong(pCornerEdges) : 0;
				if (cornerRadius || cornerEdges)
					bwidth = 0; // border not supported for rounded edges

				if (m_font.find(fnt) == m_font.end())
				{
					eDebug("[eListboxPythonMultiContent] specified font %d was not found!", fnt);
					goto error_out;
				}

				eRect rect(x+bwidth, y+bwidth, width-bwidth*2, height-bwidth*2);
				painter.clip(rect);

				{
					if(cornerRadius && (pbackColor || pbackColorSelected))
					{
						if(selected && !pbackColorSelected)
							pbackColorSelected = pbackColor;
						unsigned int color = PyLong_AsUnsignedLongMask(selected ? pbackColorSelected : pbackColor);
						painter.setBackgroundColor(gRGB(color));
						painter.setRadius(cornerRadius, cornerEdges);
						painter.drawRectangle(itemRect);
					}
					else
					{
						gRegion rc(rect);
						bool mustClear = (selected && pbackColorSelected) || (!selected && pbackColor);
						clearRegion(painter, style, local_style, pforeColor, pforeColorSelected, pbackColor, pbackColorSelected, selected, rc, sel_clip, offset, m_itemsize, cursorValid, mustClear, isverticallb);
					}
				}

				unsigned int textBColor = pTextBorderColor ? PyLong_AsUnsignedLongMask(pTextBorderColor) : 0x000000;
				painter.setFont(m_font[fnt]);
				painter.renderText(rect, string, flags, gRGB(textBColor), btwidth);
				painter.clippop();

				// draw border
				if (bwidth && cornerRadius == 0)
				{
					eRect rect(eRect(x, y, width, height));
					painter.clip(rect);
					if (pborderColor)
					{
						unsigned int color = PyLong_AsUnsignedLongMask(pborderColor);
						painter.setForegroundColor(gRGB(color));
					}

					rect.setRect(x, y, width, bwidth);
					painter.fill(rect);

					rect.setRect(x, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);

					rect.setRect(x+bwidth, y+height-bwidth, width-bwidth, bwidth);
					painter.fill(rect);

					rect.setRect(x+width-bwidth, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);

					painter.clippop();
				}
				break;
			}
			case TYPE_PROGRESS_PIXMAP: // Progress
			/*
				(1, x, y, width, height, filled_percent, pixmap [, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected] )
			*/
			case TYPE_PROGRESS: // Progress
			{
			/*
				(1, x, y, width, height, filled_percent [, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected] )
			*/
				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							pfilled_perc = PyTuple_GET_ITEM(item, 5),
							ppixmap, pborderWidth, pforeColor, pforeColorSelected, pbackColor, pbackColorSelected;
				int idx = 6;
				if (type == TYPE_PROGRESS)
				{
					if (!(px && py && pwidth && pheight && pfilled_perc))
					{
						eDebug("[eListboxPythonMultiContent] tuple too small (must be (TYPE_PROGRESS, x, y, width, height, filled percent [, borderWidth, color, colorSelected, backColor, backColorSelected]))");
						goto error_out;
					}
				}
				else
				{
					ppixmap = PyTuple_GET_ITEM(item, idx++);
					if (ppixmap == Py_None)
						continue;
					if (!(px && py && pwidth && pheight && pfilled_perc, ppixmap))
					{
						eDebug("[eListboxPythonMultiContent] tuple too small (must be (TYPE_PROGRESS_PIXMAP, x, y, width, height, filled percent, pixmap, [,borderWidth, color, colorSelected, backColor, backColorSelected]))");
						goto error_out;
					}
				}

				if (size > idx)
				{
					pborderWidth = PyTuple_GET_ITEM(item, idx++);
					if (pborderWidth == Py_None)
						pborderWidth = ePyObject();
				}
				if (size > idx)
				{
					pforeColor = PyTuple_GET_ITEM(item, idx++);
					if (pforeColor == Py_None)
						pforeColor = ePyObject();
				}
				if (size > idx)
				{
					pforeColorSelected = PyTuple_GET_ITEM(item, idx++);
					if (pforeColorSelected == Py_None)
						pforeColorSelected=ePyObject();
				}
				if (size > idx)
				{
					pbackColor = PyTuple_GET_ITEM(item, idx++);
					if (pbackColor == Py_None)
						pbackColor=ePyObject();
				}
				if (size > idx)
				{
					pbackColorSelected = PyTuple_GET_ITEM(item, idx++);
					if (pbackColorSelected == Py_None)
						pbackColorSelected=ePyObject();
				}

				int x = (PyFloat_Check(px) ? (int)PyFloat_AsDouble(px) : PyLong_AsLong(px)) + offset.x();
				int y = (PyFloat_Check(py) ? (int)PyFloat_AsDouble(py) : PyLong_AsLong(py)) + offset.y();
				int width = PyFloat_Check(pwidth) ? (int)PyFloat_AsDouble(pwidth) : PyLong_AsLong(pwidth);
				int height = PyFloat_Check(pheight) ? (int)PyFloat_AsDouble(pheight) : PyLong_AsLong(pheight);
				int filled = PyFloat_Check(pfilled_perc) ? (int)PyFloat_AsDouble(pfilled_perc) : PyLong_AsLong(pfilled_perc);

				if ((filled < 0) && data) /* if the string is in a negative number, it refers to the 'data' list. */
					filled = PyLong_AsLong(PyTuple_GetItem(data, -filled));

							/* don't do anything if percent out of range */
				if ((filled < 0) || (filled > 100))
					continue;

				int bwidth = pborderWidth ? PyLong_AsLong(pborderWidth) : 2;

				eRect rect(x, y, width, height);
				painter.clip(rect);

				{
					gRegion rc(rect);
					bool mustClear = (selected && pbackColorSelected) || (!selected && pbackColor);
					clearRegion(painter, style, local_style, pforeColor, pforeColorSelected, pbackColor, pbackColorSelected, selected, rc, sel_clip, offset, m_itemsize, cursorValid, mustClear, isverticallb);
				}

				// border
				if (bwidth) {
					rect.setRect(x, y, width, bwidth);
					painter.fill(rect);

					rect.setRect(x, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);

					rect.setRect(x+bwidth, y+height-bwidth, width-bwidth, bwidth);
					painter.fill(rect);

					rect.setRect(x+width-bwidth, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);
				}

				rect.setRect(x+bwidth, y+bwidth, (width-bwidth*2) * filled / 100, height-bwidth*2);

				// progress
				if (ppixmap)
				{
					ePtr<gPixmap> pixmap;
					if (PyLong_Check(ppixmap) && data) /* if the pixmap is in fact a number, it refers to the data list */
						ppixmap = PyTuple_GetItem(data, PyLong_AsLong(ppixmap));

					if (SwigFromPython(pixmap, ppixmap))
					{
						eDebug("[eListboxPythonMultiContent] progressbar get pixmap failed");
						painter.clippop();
						continue;
					}
					painter.blit(pixmap, rect.topLeft(), rect, 0);
				}
				else
					painter.fill(rect);

				painter.clippop();
				break;
			}
			case TYPE_PIXMAP_ALPHABLEND:
			case TYPE_PIXMAP_ALPHATEST:
			case TYPE_PIXMAP: // pixmap
			{
			/*
				(2, x, y, width, height, pixmap [, backColor, backColorSelected, flags] )
			*/

				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							ppixmap = PyTuple_GET_ITEM(item, 5),
							pbackColor, pbackColorSelected;

				if (!(px && py && pwidth && pheight && ppixmap))
				{
					eDebug("[eListboxPythonMultiContent] tuple too small (must be (TYPE_PIXMAP, x, y, width, height, pixmap [, backColor, backColorSelected, flags] ))");
					goto error_out;
				}

				if (PyLong_Check(ppixmap) && data) /* if the pixmap is in fact a number, it refers to the 'data' list. */
					ppixmap = PyTuple_GetItem(data, PyLong_AsLong(ppixmap));

							/* don't do anything if we have 'None' as pixmap */
				if (ppixmap == Py_None)
					continue;

				int x = (PyFloat_Check(px) ? (int)PyFloat_AsDouble(px) : PyLong_AsLong(px)) + offset.x();
				int y = (PyFloat_Check(py) ? (int)PyFloat_AsDouble(py) : PyLong_AsLong(py)) + offset.y();
				int width = PyFloat_Check(pwidth) ? (int)PyFloat_AsDouble(pwidth) : PyLong_AsLong(pwidth);
				int height = PyFloat_Check(pheight) ? (int)PyFloat_AsDouble(pheight) : PyLong_AsLong(pheight);
				int flags = 0;
				int radius = 0;
				int edges = 0;
				ePtr<gPixmap> pixmap;
				if (SwigFromPython(pixmap, ppixmap))
				{
					eDebug("[eListboxPythonMultiContent] (Pixmap) get pixmap failed");
					goto error_out;
				}

				if (size > 6)
					pbackColor = lookupColor(PyTuple_GET_ITEM(item, 6), data);

				if (size > 7)
					pbackColorSelected = lookupColor(PyTuple_GET_ITEM(item, 7), data);

				if (size > 8)
					flags = PyLong_AsLong(PyTuple_GET_ITEM(item, 8));

				if (size > 9)
					radius = PyLong_AsLong(PyTuple_GET_ITEM(item, 9));

				if (size > 10)
					edges = PyLong_AsLong(PyTuple_GET_ITEM(item, 10));

				eRect rect(x, y, width, height);
				painter.clip(rect);

				{
					gRegion rc(rect);
					bool mustClear = (selected && pbackColorSelected) || (!selected && pbackColor);
					clearRegion(painter, style, local_style, ePyObject(), ePyObject(), pbackColor, pbackColorSelected, selected, rc, sel_clip, offset, m_itemsize, cursorValid, mustClear, isverticallb);
				}
				flags |= (type == TYPE_PIXMAP_ALPHATEST) ? gPainter::BT_ALPHATEST : (type == TYPE_PIXMAP_ALPHABLEND) ? gPainter::BT_ALPHABLEND : 0;
				if(radius && edges)
					painter.setRadius(radius, edges);
				painter.blit(pixmap, rect, rect, flags);
				painter.clippop();
				break;
			}
			default:
				eWarning("[eListboxPythonMultiContent] received unknown type (%d)", type);
				goto error_out;
			}
		}
	}



error_out:
	if (buildfunc_ret)
		Py_DECREF(buildfunc_ret);

	painter.clippop();
}

void eListboxPythonMultiContent::setBuildFunc(ePyObject cb)
{
	Py_XDECREF(m_buildFunc);
	m_buildFunc=cb;
	Py_XINCREF(m_buildFunc);
}

void eListboxPythonMultiContent::setSelectableFunc(ePyObject cb)
{
	Py_XDECREF(m_selectableFunc);
	m_selectableFunc=cb;
	Py_XINCREF(m_selectableFunc);
}

int eListboxPythonMultiContent::currentCursorSelectable()
{
	/* each list-entry is a list of tuples. if the first of these is none, it's not selectable */
	if (m_list && cursorValid())
	{
		if (m_selectableFunc && PyCallable_Check(m_selectableFunc))
		{
			ePyObject args = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
			if (PyTuple_Check(args))
			{
				ePyObject ret = PyObject_CallObject(m_selectableFunc, args);
				if (ret)
				{
					bool retval = ret == Py_True;
					Py_DECREF(ret);
					return retval;
				}
				eDebug("[eListboxPythonMultiContent] call m_selectableFunc failed!!! assume not callable");
			}
			else
				eDebug("[eListboxPythonMultiContent] m_list[m_cursor] is not a tuple!!! assume not callable");
		}
		else
		{
			ePyObject item = PyList_GET_ITEM(m_list, m_cursor);
			if (PyList_Check(item))
			{
				item = PyList_GET_ITEM(item, 0);
				if (item != Py_None)
					return 1;
			} else if (PyTuple_Check(item))
			{
				item = PyTuple_GET_ITEM(item, 0);
				if (item != Py_None)
					return 1;
			}
			else if (m_buildFunc && PyCallable_Check(m_buildFunc))
				return 1;
		}
	}
	return 0;
}

void eListboxPythonMultiContent::setFont(int fnt, gFont *font)
{
	if (font)
		m_font[fnt] = font;
	else
		m_font.erase(fnt);
}

void eListboxPythonMultiContent::setOrientation(int orientation)
{
	m_orientation = orientation;
	if (m_listbox){
		m_listbox->setOrientation(orientation);
	}
}

void eListboxPythonMultiContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox){
		m_listbox->setItemHeight(height);
	}
}

void eListboxPythonMultiContent::setItemWidth(int width)
{
	m_itemwidth = width;
	if (m_listbox){
		m_listbox->setItemWidth(width);
	}
}

void eListboxPythonMultiContent::setList(ePyObject list)
{
	m_old_clip = m_clip = gRegion::invalidRegion();
	eListboxPythonStringContent::setList(list);
}

void eListboxPythonMultiContent::resetClip()
{
	m_old_clip = m_clip = gRegion::invalidRegion();
}

void eListboxPythonMultiContent::updateClip(gRegion &clip)
{
	if (m_clip.valid())
	{
		clip &= m_clip;
		if (m_old_clip.valid() && !(m_clip-m_old_clip).empty())
			m_clip -= m_old_clip;
		m_old_clip = m_clip;
	}
	else
		m_old_clip = m_clip = gRegion::invalidRegion();
}

void eListboxPythonMultiContent::entryRemoved(int idx)
{
	if (m_listbox)
		m_listbox->entryRemoved(idx);
}

void eListboxPythonMultiContent::setTemplate(ePyObject tmplate)
{
	Py_XDECREF(m_template);
	m_template = tmplate;
	Py_XINCREF(m_template);
}
