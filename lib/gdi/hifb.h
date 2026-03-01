/**
 * \file
 * \brief Describes the information about HiSilicion frame buffer (HiFB).
 */

#ifndef __HIFB_H__
#define __HIFB_H__

#ifdef __cplusplus
#if __cplusplus
extern "C"{
#endif
#endif /* __cplusplus */

#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <linux/fb.h>

#define IOC_TYPE_HIFB       'F'


/**Waits for the vertical blanking interrupt of a graphics layer.*/
#define FBIOGET_VBLANK_HIFB                    _IO(IOC_TYPE_HIFB, 100)

/**Sets the information about a graphics layer.*/
#define FBIOPUT_LAYER_INFO                _IOW(IOC_TYPE_HIFB, 120, HIFB_LAYER_INFO_S)

/**Obtains the information about a graphics layer.*/
#define FBIOGET_LAYER_INFO                _IOR(IOC_TYPE_HIFB, 121, HIFB_LAYER_INFO_S)

/**Obtains a canvas buffer.*/
#define FBIOGET_CANVAS_BUFFER             _IOR(IOC_TYPE_HIFB, 123, HIFB_BUFFER_S)

/**Refreshes a graphics layer.*/
#define FBIO_REFRESH                      _IOW(IOC_TYPE_HIFB, 124, HIFB_BUFFER_S)

/**sync refresh*/
#define FBIO_WAITFOR_FREFRESH_DONE        _IO(IOC_TYPE_HIFB, 125)

/**Pixel format*/
typedef enum
{
    HIFB_FMT_RGB565 = 0,    /**<  RGB565 16bpp */
    HIFB_FMT_RGB888,        /**<  RGB888 24bpp */
    HIFB_FMT_KRGB444,       /**<  RGB444 16bpp */
    HIFB_FMT_KRGB555,       /**<  RGB555 16bpp */

    HIFB_FMT_KRGB888,       /**<  RGB888 32bpp */
    HIFB_FMT_ARGB4444,      /**< ARGB4444 */
    HIFB_FMT_ARGB1555,      /**< ARGB1555 */
    HIFB_FMT_ARGB8888,      /**< ARGB8888 */

    HIFB_FMT_ARGB8565,      /**< ARGB8565 */
    HIFB_FMT_RGBA4444,      /**< ARGB4444 */
    HIFB_FMT_RGBA5551,      /**< RGBA5551 */
    HIFB_FMT_RGBA5658,      /**< RGBA5658 */

    HIFB_FMT_RGBA8888,      /**< RGBA8888 */
    HIFB_FMT_BGR565,        /**< BGR565 */
    HIFB_FMT_BGR888,        /**< BGR888 */
    HIFB_FMT_ABGR4444,      /**< ABGR4444 */

    HIFB_FMT_ABGR1555,      /**< ABGR1555 */
    HIFB_FMT_ABGR8888,      /**< ABGR8888 */
    HIFB_FMT_ABGR8565,      /**< ABGR8565 */
    HIFB_FMT_KBGR444,       /**< BGR444 16bpp */

    HIFB_FMT_KBGR555,       /**< BGR555 16bpp */
    HIFB_FMT_KBGR888,       /**< BGR888 32bpp */
    HIFB_FMT_1BPP,          /**<  clut1 */
    HIFB_FMT_2BPP,          /**<  clut2 */

    HIFB_FMT_4BPP,          /**<  clut4 */
    HIFB_FMT_8BPP,          /**< clut8 */
    HIFB_FMT_ACLUT44,       /**< AClUT44*/
    HIFB_FMT_ACLUT88,       /**< ACLUT88 */

    HIFB_FMT_PUYVY,         /**< UYVY */
    HIFB_FMT_PYUYV,         /**< YUYV */
    HIFB_FMT_PYVYU,         /**< YVYU */
    HIFB_FMT_YUV888,        /**< YUV888 */

    HIFB_FMT_AYUV8888,      /**< AYUV8888 */
    HIFB_FMT_YUVA8888,      /**< YUVA8888 */

    HIFB_FMT_BUTT
}HIFB_COLOR_FMT_E;

/**antiflicker level*/
/**Auto means fb will choose a appropriate antiflicker level automatically according to the color info of map*/
typedef enum
{
    HIFB_LAYER_ANTIFLICKER_NONE = 0x0,    /**< no antiflicker*/
    HIFB_LAYER_ANTIFLICKER_LOW = 0x1,     /**< low level*/
    HIFB_LAYER_ANTIFLICKER_MIDDLE = 0x2,  /**< middle level*/
    HIFB_LAYER_ANTIFLICKER_HIGH = 0x3,    /**< high level*/
    HIFB_LAYER_ANTIFLICKER_AUTO = 0x4,    /**< auto*/
    HIFB_LAYER_ANTIFLICKER_BUTT
}HIFB_LAYER_ANTIFLICKER_LEVEL_E;

/*layer info maskbit*/
typedef enum
{
    HIFB_LAYERMASK_BUFMODE = 0x1,           /**< Whether the buffer mode in HIFB_LAYER_INFO_S is masked when the graphics layer information is set.*/
    HIFB_LAYERMASK_ANTIFLICKER_MODE = 0x2,  /**< Whether the anti-flicker mode is masked.*/
    HIFB_LAYERMASK_POS = 0x4,               /**< Whether the graphics layer position is masked.*/
    HIFB_LAYERMASK_CANVASSIZE = 0x8,        /**< Whether the canvas size is masked.*/
    HIFB_LAYERMASK_DISPSIZE = 0x10,         /**< Whether the display size is masked.*/
    HIFB_LAYERMASK_SCREENSIZE = 0x20,       /**< Whether the screen size is masked.*/
    HIFB_LAYERMASK_BMUL = 0x40,             /**< Whether the premultiplexed mode is masked.*/
    HIFB_LAYERMASK_BUTT
}HIFB_LAYER_INFO_MASKBIT;

/*refresh mode*/
typedef enum
{
    HIFB_LAYER_BUF_DOUBLE = 0x0,         /**< 2 display buf in fb */
    HIFB_LAYER_BUF_ONE    = 0x1,         /**< 1 display buf in fb */
    HIFB_LAYER_BUF_NONE   = 0x2,         /**< no display buf in fb,the buf user refreshed will be directly set to VO*/
    HIFB_LAYER_BUF_DOUBLE_IMMEDIATE=0x3, /**< 2 display buf in fb, each refresh will be displayed*/
    HIFB_LAYER_BUF_STANDARD = 0x4,       /**< standard refresh*/
    HIFB_LAYER_BUF_BUTT
} HIFB_LAYER_BUF_E;

/* surface info */
typedef struct
{
    unsigned long  u32PhyAddr;     /**<  start physical address */
    unsigned long  u32Width;       /**<  width pixels */
    unsigned long  u32Height;      /**<  height pixels */
    unsigned long  u32Pitch;       /**<  line pixels */
    HIFB_COLOR_FMT_E enFmt;        /**<  color format ARGB1555 == 6, ARGB8888 == 7 */
}HIFB_SURFACE_S;

/* Rectangle information */
typedef struct
{
    long x, y;    /**<x: horizontal coordinate of the upper left point of the rectangle; y: vertical coordinate of the upper left point of the rectangle*/
    long w, h;    /**< w: rectangle width; h: rectangle height*/
} HIFB_RECT;


/* refresh surface info */
typedef struct
{
    HIFB_SURFACE_S stCanvas;
    HIFB_RECT UpdateRect;       /**< refresh region*/
}HIFB_BUFFER_S;

/* layer info */
typedef struct
{
    int BufMode;
    int eAntiflickerLevel;
    long s32XPos;                       /**<  the x pos of origion point in screen */
    long s32YPos;                       /**<  the y pos of origion point in screen */
    long u32CanvasWidth;                /**<  the width of canvas buffer */
    long u32CanvasHeight;               /**<  the height of canvas buffer */
    unsigned long u32DisplayWidth;      /**<  the width of display buf in fb.for 0 buf ,there is no display buf in fb, so it's effectless*/
    unsigned long u32DisplayHeight;     /**<  the height of display buf in fb. */
    unsigned long u32ScreenWidth;       /**<  the width of screen */
    unsigned long u32ScreenHeight;      /**<  the height of screen */
    int bPreMul;                        /**<  The data drawed in buf is premul data or not*/
    int bUseNewScreen;                  /**<  whether use new screen*/
    unsigned long u32Mask;              /**<  param modify mask bit*/
}HIFB_LAYER_INFO_S;



#ifdef __cplusplus
#if __cplusplus
}
#endif
#endif /* __cplusplus */


#endif /* __HIFB_H__ */
