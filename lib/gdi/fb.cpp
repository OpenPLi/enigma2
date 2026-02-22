#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <memory.h>
#include <linux/kd.h>

#include <lib/gdi/fb.h>

#ifdef HAVE_HIFBLAYER
#include "hifb.h"
#endif

#ifndef FBIO_WAITFORVSYNC
#define FBIO_WAITFORVSYNC _IOW('F', 0x20, uint32_t)
#endif

#ifndef FBIO_BLIT
#define FBIO_SET_MANUAL_BLIT _IOW('F', 0x21, __u8)
#define FBIO_BLIT 0x22
#endif

fbClass *fbClass::instance;

fbClass *fbClass::getInstance()
{
	return instance;
}

fbClass::fbClass(const char *fb)
{
	m_manual_blit=-1;
	instance=this;
	locked=0;
	lfb=0;
	m_lfb_base=0;

	available=0;
	m_available_total=0;

	m_phys_mem=0;
	m_phys_mem_base=0;

	cmap.start=0;
	cmap.len=256;
	cmap.red=red;
	cmap.green=green;
	cmap.blue=blue;
	cmap.transp=trans;

	fbFd=open(fb, O_RDWR);
	if (fbFd<0)
	{
		eDebug("[fb] %s %m", fb);
		goto nolfb;
	}


	if (ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo)<0)
	{
		eDebug("[fb] FBIOGET_VSCREENINFO: %m");
		goto nolfb;
	}

	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		eDebug("[fb] FBIOGET_FSCREENINFO: %m");
		goto nolfb;
	}

	m_available_total = fix.smem_len;
	m_phys_mem_base = fix.smem_start;
	available = m_available_total;
	m_phys_mem = m_phys_mem_base;
	eDebug("[fb] %s: %dk video mem", fb, m_available_total/1024);
	m_lfb_base=(unsigned char*)mmap(0, m_available_total, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 0);
	lfb = m_lfb_base;
	if (!m_lfb_base)
	{
		eDebug("[fb] mmap: %m");
		goto nolfb;
	}

	showConsole(0);

	enableManualBlit();
	return;
nolfb:
	if (fbFd >= 0)
	{
		::close(fbFd);
		fbFd = -1;
	}
	eDebug("[fb] framebuffer %s not available", fb);
	return;
}

int fbClass::showConsole(int state)
{
	int fd=open("/dev/tty0", O_RDWR);
	if(fd>=0)
	{
		if(ioctl(fd, KDSETMODE, state?KD_TEXT:KD_GRAPHICS)<0)
		{
			eDebug("[fb] setting /dev/tty0 status failed.");
		}
		close(fd);
	}
	return 0;
}

int fbClass::SetMode(int nxRes, int nyRes, int nbpp)
{
	if (fbFd < 0) return -1;
	screeninfo.xres_virtual=screeninfo.xres=nxRes;
	screeninfo.yres_virtual=(screeninfo.yres=nyRes)*2;
	screeninfo.height=0;
	screeninfo.width=0;
	screeninfo.xoffset=screeninfo.yoffset=0;
	screeninfo.bits_per_pixel=nbpp;

	switch (nbpp) {
	case 16:
		// ARGB 1555
		screeninfo.transp.offset = 15;
		screeninfo.transp.length = 1;
		screeninfo.red.offset = 10;
		screeninfo.red.length = 5;
		screeninfo.green.offset = 5;
		screeninfo.green.length = 5;
		screeninfo.blue.offset = 0;
		screeninfo.blue.length = 5;
		break;
	case 32:
		// ARGB 8888
		screeninfo.transp.offset = 24;
		screeninfo.transp.length = 8;
		screeninfo.red.offset = 16;
		screeninfo.red.length = 8;
		screeninfo.green.offset = 8;
		screeninfo.green.length = 8;
		screeninfo.blue.offset = 0;
		screeninfo.blue.length = 8;
		break;
	}

	if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
	{
		// try single buffering
		screeninfo.yres_virtual=screeninfo.yres=nyRes;

		if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
		{
			eDebug("[fb] FBIOPUT_VSCREENINFO: %m");
			return -1;
		}
		eDebug("[fb] double buffering not available.");
	} else
		eDebug("[fb] double buffering available!");

	m_number_of_pages = screeninfo.yres_virtual / nyRes;

	ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo);

	if ((screeninfo.xres != (unsigned int)nxRes) || (screeninfo.yres != (unsigned int)nyRes) ||
		(screeninfo.bits_per_pixel != (unsigned int)nbpp))
	{
		eDebug("[fb] SetMode failed: wanted: %dx%dx%d, got %dx%dx%d",
			nxRes, nyRes, nbpp,
			screeninfo.xres, screeninfo.yres, screeninfo.bits_per_pixel);
	}
	xRes=screeninfo.xres;
	yRes=screeninfo.yres;
	bpp=screeninfo.bits_per_pixel;
	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		eDebug("[fb] FBIOGET_FSCREENINFO: %m");
	}

	stride=fix.line_length;
	memset(lfb, 0, stride*yRes);

#ifdef HAVE_HIFBLAYER
	if (access("/etc/hifblayer", F_OK) == 0 && m_available_total > (stride * yRes * 3))
	{
		HIFB_LAYER_INFO_S layerinfo;
		if (ioctl(fbFd, FBIOGET_LAYER_INFO, &layerinfo) < 0)
		{
			eDebug("[fb] FBIOGET_LAYER_INFO: %m");
		}
		else
		{
			memset(&layerinfo, 0x00, sizeof(layerinfo));

			layerinfo.eAntiflickerLevel = HIFB_LAYER_ANTIFLICKER_NONE;
			layerinfo.BufMode = HIFB_LAYER_BUF_DOUBLE_IMMEDIATE;
			layerinfo.u32CanvasWidth = xRes;
			layerinfo.u32CanvasHeight = yRes;
			layerinfo.u32Mask |= HIFB_LAYERMASK_BUFMODE;
			layerinfo.u32Mask |= HIFB_LAYERMASK_ANTIFLICKER_MODE;
			layerinfo.u32Mask |= HIFB_LAYERMASK_CANVASSIZE;
			if (ioctl(fbFd, FBIOPUT_LAYER_INFO, &layerinfo) < 0)
			{
				eDebug("[fb] FBIOPUT_LAYER_INFO: %m");
				return (-1);
			}
			else
			{
				// We must use framebuffer-mapped memory for the canvas because
				// FBIOGET_CANVAS_BUFFER is not supported on the SF8008 platform.
				//
				// The first two framebuffer pages cannot be used, as they are reserved
				// by the driver for hardware double buffering.
				int frame_size = stride * yRes;
				m_phys_mem = m_phys_mem_base  + frame_size * 2;
				lfb        = m_lfb_base       + frame_size * 2;
				available  = m_available_total - frame_size * 2;

				// Double buffering is handled internally by the driver.
				// We account for this by skipping the first two framebuffer pages above.
				// See gdi/gfbdc.cpp for fb->getNumPages() usage.
				m_number_of_pages = 1;

				memset(lfb, 0, stride*yRes);
				eDebug("[fb] Use HIFB_LAYER");
			}
		}
	}
#endif // HAVE_HIFBLAYER

	blit();
	return 0;
}

void fbClass::getMode(int &xres, int &yres, int &bpp)
{
	xres = screeninfo.xres;
	yres = screeninfo.yres;
	bpp = screeninfo.bits_per_pixel;
}

int fbClass::setOffset(int off)
{
	if (fbFd < 0) return -1;
	screeninfo.xoffset = 0;
	screeninfo.yoffset = off;
	return ioctl(fbFd, FBIOPAN_DISPLAY, &screeninfo);
}

int fbClass::waitVSync()
{
	int c = 0;
	if (fbFd < 0) return -1;
	int ret = ioctl(fbFd, FBIO_WAITFORVSYNC, &c);
	return ret;
}

void fbClass::blit()
{

	if (fbFd < 0) return;
	if (m_manual_blit == 0) {
		return;
	}

	if (m_phys_mem == m_phys_mem_base)
	{
		if (ioctl(fbFd, FBIO_BLIT) < 0)
			eDebug("[fb] FBIO_BLIT: %m");
	}
#ifdef HAVE_HIFBLAYER
	else
	{
		// HI Buffer layer mode
		HIFB_BUFFER_S CanvasBuf;
		CanvasBuf.stCanvas.u32PhyAddr = m_phys_mem;
		CanvasBuf.stCanvas.u32Height  = yRes;
		CanvasBuf.stCanvas.u32Width   = xRes;

		switch (bpp) {
		case 16:
			CanvasBuf.stCanvas.enFmt  = HIFB_FMT_ARGB1555;
			break;
		case 32:
			CanvasBuf.stCanvas.enFmt  = HIFB_FMT_ARGB8888;
			break;
		default:
			eDebug("[fb] WRONG BPP: %d", bpp);
		}

		CanvasBuf.stCanvas.u32Pitch   = xRes * (bpp/8);

		// Ideally, only the dirty region modified by Enigma2 since the previous refresh
		// should be updated instead of refreshing the full screen.
		// However, the refresh is performed via DMA transfer, which is fast enough
		// to sustain full FPS (60 Hz and 50 Hz), so a full-screen update is acceptable.
		CanvasBuf.UpdateRect.x = 0;
		CanvasBuf.UpdateRect.y = 0;
		CanvasBuf.UpdateRect.w = CanvasBuf.stCanvas.u32Width;
		CanvasBuf.UpdateRect.h = CanvasBuf.stCanvas.u32Height;

		if (ioctl(fbFd, FBIO_REFRESH, &CanvasBuf) < 0)
		{
			eDebug("[fb] FBIO_REFRESH: %m");
		}

#if 0
		// Not required when using HIFB_LAYER_BUF_DOUBLE_IMMEDIATE,
		// as the refresh is applied immediately and does not need
		// an explicit wait for completion.
		if (ioctl(fbFd, FBIO_WAITFOR_FREFRESH_DONE, NULL) < 0)
		{
			eDebug("[fb] FBIO_WAITFOR_FREFRESH_DONE: %m");
		}
#endif
	}
#endif // HAVE_HIFBLAYER
}

fbClass::~fbClass()
{
	if (m_lfb_base)
	{
		msync(m_lfb_base, m_available_total, MS_SYNC);
		munmap(m_lfb_base, m_available_total);
	}
	showConsole(1);
	disableManualBlit();
	if (fbFd >= 0)
	{
		::close(fbFd);
		fbFd = -1;
	}
}

int fbClass::PutCMAP()
{
	if (fbFd < 0) return -1;
	return ioctl(fbFd, FBIOPUTCMAP, &cmap);
}

int fbClass::lock()
{
	if (locked)
		return -1;
	if (m_manual_blit == 1)
	{
		locked = 2;
		disableManualBlit();
	}
	else
		locked = 1;
	return fbFd;
}

void fbClass::unlock()
{
	if (!locked)
		return;
	if (locked == 2)  // re-enable manualBlit
		enableManualBlit();
	locked=0;
	SetMode(xRes, yRes, bpp);
	PutCMAP();
}

void fbClass::enableManualBlit()
{
	unsigned char tmp = 1;
	if (fbFd < 0) return;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] enable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 1;
}

void fbClass::disableManualBlit()
{
	unsigned char tmp = 0;
	if (fbFd < 0) return;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] disable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 0;
}

