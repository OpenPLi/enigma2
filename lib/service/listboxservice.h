#ifndef __lib_service_listboxservice_h
#define __lib_service_listboxservice_h

#include <lib/gdi/gpixmap.h>
#include <lib/gui/elistbox.h>
#include <lib/service/iservice.h>
#include <lib/python/python.h>
#include <set>

class eListboxServiceContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxServiceContent);
	static ePyObject m_GetPiconNameFunc;
public:
	eListboxServiceContent();

	void addService(const eServiceReference &ref, bool beforeCurrent=false);
	void removeCurrent();
	void FillFinished();

	void setIgnoreService( const eServiceReference &service );
	void setRoot(const eServiceReference &ref, bool justSet=false);
	void getCurrent(eServiceReference &ref);
	void getPrev(eServiceReference &ref);
	void getNext(eServiceReference &ref);
	PyObject *getList();

	int getNextBeginningWithChar(char c);
	int getPrevMarkerPos();
	int getNextMarkerPos();
	int getCurrentSelectionIndex() { return cursorResolve(m_cursor_number); }
	eSize getItemSize() { return m_itemsize; }
	int getListSize() { return m_size_visible; }

		/* support for marked services */
	void initMarked();
	void addMarked(const eServiceReference &ref);
	void removeMarked(const eServiceReference &ref);
	int isMarked(const eServiceReference &ref);

		/* this is NOT thread safe! */
	void markedQueryStart();
	int markedQueryNext(eServiceReference &ref);

	int lookupService(const eServiceReference &ref);
	bool setCurrent(const eServiceReference &ref);

	enum {
		visModeSimple,
		visModeComplex,
		visSkinDefined
	};

	void setVisualMode(int mode);

		/* only in complex mode: */
	enum {
		celServiceNumber,
		celMarkerPixmap,
		celFolderPixmap,
		celServiceEventProgressbar,
		celServiceName,
		celServiceInfo, // "now" event
		celServiceNextInfo, // "next" event
		celServiceTypePixmap,
		celServiceInfoRemainingTime,
		celElements
	};

	enum {
		picDVB_S,
		picDVB_T,
		picDVB_C,
		picStream,
		picServiceGroup,
		picFolder,
		picMarker,
		picServiceEventProgressbar,
		picCrypto,
		picRecord,
		pic4K,
		picHD,
		picSD,
		picBackup,
		picCatchup,
		picElements
	};

	void setElementPosition(int element, eRect where);
	void setElementFont(int element, gFont *font);
	void setPixmap(int type, ePtr<gPixmap> &pic);

	void sort();

	int setCurrentMarked(bool);

	int getItemHeight() { return m_itemheight; }
	void setItemHeight(int height);
	void setHideNumberMarker(bool doHide) { m_hide_number_marker = doHide; }
	void setServiceTypeIconMode(int mode) { m_servicetype_icon_mode = mode; }
	void setCryptoIconMode(int mode) { m_crypto_icon_mode = mode; }
	void setRecordIndicatorMode(int mode) { m_record_indicator_mode = mode; }
	void setColumnWidth(int value) { m_column_width = value; }
	void setProgressbarHeight(int value) {	m_progressbar_height = value; }
	void setProgressbarBorderWidth(int value) { m_progressbar_border_width = value; }
	void setNonplayableMargins(int value) { m_nonplayable_margins = value; }
	void setItemsDistances(int value) { m_items_distances = value; }
	void setSidesMargin(int value) { m_sides_margin = value; }
	void setMarkerAsLine(int value) { m_marker_as_line = value; }
	void setChannelNumbersVisible(bool visible) { m_chanel_number_visible = visible; }
	void setAlternativeNumberingMode(bool b) { m_alternative_numbering = b; }
	void setProgressBarMode(std::string s) { m_progress_mode = s; }
	void setAlternativeRecordMatching(bool b) { m_alternative_record_match = b; }
	void setHasNextEvent(bool b) { m_has_next_event = b; }

	void setNextTitle(const std::string &string) { m_next_title = string; }
	void setTextTime(const std::string &string) { m_text_time = string; }
	void setTextSeparator(const std::string &string) { m_separator = string; }
	void setMarkerTextAlignment(const std::string &string) { m_marker_alignment = string; } // currently supports left and center
	void setMarkerLineColor(const gRGB &col) { 
		m_markerline_color = col;
		m_markerline_color_set = 1;
	}

	static void setGetPiconNameFunc(SWIG_PYOBJECT(ePyObject) func);

	enum {
		markedForeground,
		markedForegroundSelected,
		markedBackground,
		markedBackgroundSelected,
		serviceNotAvail,
		eventForeground,
		eventForegroundSelected,
		eventborderForeground,
		eventborderForegroundSelected,
		eventForegroundFallback,
		eventForegroundSelectedFallback,
		eventNextForeground,
		eventNextForegroundSelected,
		eventNextForegroundFallback,
		eventNextForegroundSelectedFallback,
		serviceItemFallback,
		serviceSelectedFallback,
		serviceEventProgressbarColor,
		serviceEventProgressbarColorSelected,
		serviceEventProgressbarBorderColor,
		serviceEventProgressbarBorderColorSelected,
		serviceRecorded,
		eventRemainingForeground,
		eventRemainingForegroundSelected,
		eventRemainingForegroundFallback,
		eventRemainingForegroundSelectedFallback,
		colorElements
	};

	void setColor(int color, gRGB &col);
	bool checkServiceIsRecorded(eServiceReference ref);
protected:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count=1);
	int cursorValid();
	int cursorSet(int n);
	int cursorResolve(int);
	int cursorGet();
	int currentCursorSelectable();

	void cursorSave();
	void cursorRestore();
	int size();

	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);

		/* the following functions always refer to the selected item */
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);

	int m_visual_mode;
		/* for complex mode */
	eRect m_element_position[celElements];
	ePtr<gFont> m_element_font[celElements];
	ePtr<gPixmap> m_pixmaps[picElements];
	gRGB m_color[colorElements];
	bool m_color_set[colorElements];
private:
	typedef std::list<eServiceReference> list;

	list m_list;
	list::iterator m_cursor, m_saved_cursor;

	int m_cursor_number, m_saved_cursor_number;
	int m_size, m_size_visible;

	eSize m_itemsize;
	ePtr<iServiceHandler> m_service_center;
	ePtr<iListableService> m_lst;

	eServiceReference m_root;

		/* support for marked services */
	std::set<eServiceReference> m_marked;
	std::set<eServiceReference>::const_iterator m_marked_iterator;

		/* support for movemode */
	bool m_current_marked;
	void swapServices(list::iterator, list::iterator);

	eServiceReference m_is_playable_ignore;

	int m_itemheight;
	bool m_hide_number_marker;
	bool m_chanel_number_visible;
	bool m_alternative_numbering;
	int m_servicetype_icon_mode;
	int m_crypto_icon_mode;
	int m_record_indicator_mode;
	int m_column_width;
	int m_progressbar_height;
	int m_progressbar_border_width;
	int m_nonplayable_margins;
	int m_items_distances;
	int m_sides_margin;
	int m_marker_as_line;
	gRGB m_markerline_color;
	int m_markerline_color_set;
	bool m_alternative_record_match;
	bool m_has_next_event;

	std::string m_text_time;
	std::string m_next_title;
	std::string m_separator;
	std::string m_marker_alignment;
	std::string m_progress_mode;
};

#endif
