#include <lib/gui/eslider.h>

eSlider::eSlider(eWidget *parent)
	:eWidget(parent), m_have_border_color(false), m_have_foreground_color(false), m_have_background_color(false),
	m_have_sliderborder_color(false), m_have_sliderforeground_color(false), m_have_sliderborder_width(false),
	m_min(0), m_max(0), m_value(0), m_start(0), m_orientation(orHorizontal), m_orientation_swapped(0),
	m_border_width(0), m_sliderborder_width(0)
{
}

void eSlider::setPixmap(ePtr<gPixmap> &pixmap)
{
	setPixmap(pixmap.operator->());
}

void eSlider::setPixmap(gPixmap *pixmap)
{
	m_pixmap = pixmap;
	event(evtChangedSlider);
}

void eSlider::setBackgroundPixmap(ePtr<gPixmap> &pixmap)
{
	setBackgroundPixmap(pixmap.operator->());
}

void eSlider::setBackgroundPixmap(gPixmap *pixmap)
{
	m_backgroundpixmap = pixmap;
	invalidate();
}

void eSlider::setAlphatest(int alphatest)
{
	setTransparent(alphatest);
}

void eSlider::setBorderWidth(int pixel)
{
	m_border_width=pixel;
	invalidate();
}

void eSlider::setBorderColor(const gRGB &color)
{
	m_border_color=color;
	m_have_border_color=true;
	invalidate();
}

void eSlider::setForegroundColor(const gRGB &color)
{
	m_foreground_color = color;
	m_have_foreground_color = true;
	invalidate();
}

void eSlider::setBackgroundColor(const gRGB &col)
{
	m_background_color = col;
	m_have_background_color = true;
	invalidate();
}

void eSlider::setSliderBorderWidth(int pixel)
{
	m_sliderborder_width = pixel;
	m_have_sliderborder_width = true;
	invalidate();
}

void eSlider::setSliderBorderColor(const gRGB &color)
{
	m_sliderborder_color = color;
	m_have_sliderborder_color = true;
	invalidate();
}

void eSlider::setSliderForegroundColor(const gRGB &color)
{
	m_sliderforeground_color = color;
	m_have_sliderforeground_color = true;
	invalidate();
}

int eSlider::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		eSize s(size());
		getStyle(style);
		/* paint background */
		int cornerRadius = getCornerRadius();
		if(!cornerRadius) // don't call eWidget paint if radius or gradient
			eWidget::event(evtPaint, data, data2);

		gPainter &painter = *(gPainter*)data2;

		bool drawborder = m_border_width;


		if (m_backgroundpixmap)
		{
			if (cornerRadius)
				painter.setRadius(cornerRadius, getCornerRadiusEdges());
			painter.blit(m_backgroundpixmap, ePoint(0, 0), eRect(), isTransparent() ? gPainter::BT_ALPHABLEND : 0);
		} else if(m_have_background_color && !cornerRadius) {
			painter.setBackgroundColor(m_background_color);
			painter.clear();
		}

		if(cornerRadius)
		{
			if(m_have_background_color) {
				painter.setBackgroundColor(m_background_color);
			} 
			painter.setRadius(cornerRadius, getCornerRadiusEdges());

			if (drawborder)
			{
				if (m_have_border_color)
					painter.setBackgroundColor(m_border_color);
				else
				{
					gRGB color = style->getColor(eWindowStyle::styleLabel);
					painter.setBackgroundColor(color);
				}
				painter.drawRectangle(eRect(ePoint(0, 0), size()));
 				painter.setBackgroundColor((m_have_background_color) ? m_background_color : gRGB(0, 0, 0));
				painter.setRadius(cornerRadius, getCornerRadiusEdges());
				painter.drawRectangle(eRect(m_border_width, m_border_width, size().width() - m_border_width * 2, size().height() - m_border_width * 2));
				drawborder = false;
			}
			else {
				painter.drawRectangle(eRect(ePoint(0, 0), size()));
			}
		}

		style->setStyle(painter, eWindowStyle::styleLabel); // TODO - own style

		if (!m_pixmap)
		{
			if (cornerRadius)
			{
				if (m_have_foreground_color)
					painter.setBackgroundColor(m_foreground_color);
				painter.setRadius(cornerRadius, getCornerRadiusEdges());
				eRect rect = eRect(m_currently_filled.extends);
				if (m_orientation == orHorizontal)
					rect.setHeight(size().height()-m_border_width*2);
				else
					rect.setWidth(size().width()-m_border_width*2);
				painter.drawRectangle(rect);
			}
			else {
				if (m_have_sliderforeground_color)
				    painter.setForegroundColor(m_sliderforeground_color);
			    else if (m_have_foreground_color)
					painter.setForegroundColor(m_foreground_color);

                painter.fill(m_currently_filled);
			}
		}
		else {

			if (cornerRadius)
				painter.setRadius(cornerRadius, getCornerRadiusEdges());
			painter.blit(m_pixmap, ePoint(0, 0), m_currently_filled.extends, isTransparent() ? gPainter::BT_ALPHABLEND : 0);
		}
        // border
        if(drawborder) {
		    if (m_have_sliderborder_color)
			    painter.setForegroundColor(m_sliderborder_color);
		    else if (m_have_border_color)
			    painter.setForegroundColor(m_border_color);

		    int border_width;
		    if(m_have_sliderborder_width)
			    border_width = m_sliderborder_width;
		    else
			    border_width = m_border_width;
		    painter.fill(eRect(0, 0, s.width(), border_width));
		    painter.fill(eRect(0, border_width, border_width, s.height() - border_width));
		    painter.fill(eRect(border_width, s.height() - border_width, s.width() - border_width, border_width));
            painter.fill(eRect(s.width() - border_width, border_width, border_width, s.height() - border_width));
		}

		return 0;
	}
	case evtChangedSlider:
	{
		int num_pix = 0, start_pix = 0;
		gRegion old_currently_filled = m_currently_filled;

		int pixsize = (m_orientation == orHorizontal) ? size().width() : size().height();

		if (m_min < m_max)
		{
			int val_range = m_max - m_min;
			num_pix = (pixsize * (m_value - m_start) + val_range - 1) / val_range; /* properly round up */
			start_pix = (pixsize * m_start + val_range - 1) / val_range;

			if (m_orientation_swapped)
				start_pix = pixsize - num_pix - start_pix;
		}

		if  (start_pix < 0)
		{
			num_pix += start_pix;
			start_pix = 0;
		}

		if (num_pix < 0)
			num_pix = 0;

		if (m_orientation == orHorizontal)
			m_currently_filled = eRect(start_pix + m_border_width, m_border_width, num_pix, pixsize);
		else
			m_currently_filled = eRect(m_border_width, start_pix + m_border_width, pixsize, num_pix);

		const int cornerRadius = getCornerRadius();

		if (cornerRadius)
		{
			invalidate(old_currently_filled);
			invalidate(m_currently_filled);
		}
		else
		{
			// redraw what *was* filled before and now isn't.
			invalidate(m_currently_filled - old_currently_filled);
			// redraw what wasn't filled before and is now.
			invalidate(old_currently_filled - m_currently_filled);
		}

		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eSlider::setValue(int value)
{
	m_value = value;
	event(evtChangedSlider);
}

void eSlider::setStartEnd(int start, int end)
{
	m_value = end;
	m_start = start;
	event(evtChangedSlider);
}

void eSlider::setOrientation(int orientation, int swapped)
{
	m_orientation = orientation;
	m_orientation_swapped = swapped;
	event(evtChangedSlider);
}

void eSlider::setRange(int min, int max)
{
	m_min = min;
	m_max = max;
	event(evtChangedSlider);
}
