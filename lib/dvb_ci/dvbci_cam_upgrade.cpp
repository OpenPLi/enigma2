/* DVB CI CAM Firmware Upgrade Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_cam_upgrade.h>

int eDVBCICAMUpgradeSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eDebugNoNewLine("[CI CAMUP] SESSION(%d)/CAMUP %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebugNoNewLine("\n");
	if ((tag[0]==0x9f) && (tag[1]==0x9d))
	{
		switch (tag[2])
		{
		default:
			eDebug("[CI CAMUP] unknown APDU tag 9F 9D %02x", tag[2]);
			break;
		}
	}

	return 0;
}

int eDVBCICAMUpgradeSession::doAction()
{
	switch (state)
	{
	default:
		eDebug("[CI CAMUP] unknown state");
		break;
	}

	return 0;
}
