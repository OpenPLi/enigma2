/* DVB CI Resource Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_resmgr.h>
#include <lib/dvb_ci/dvbci_ccmgr_helper.h>

int eDVBCIResourceManagerSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eDebugNoNewLineStart("[CI RM] SESSION(%d) %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebugNoNewLine("\n");
	if ((tag[0]==0x9f) && (tag[1]==0x80))
	{
		switch (tag[2])
		{
		case 0x10:  // profile enquiry
			eDebug("[CI RM] cam profile inquiry");
			state=stateProfileEnquiry;
			return 1;
			break;
		case 0x11: // Tprofile
			eDebugNoNewLineStart("[CI RM] can do: ");
			if (!len)
				eDebugNoNewLine("nothing");
			else
				for (int i=0; i<len; i++)
					eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
			eDebugNoNewLine("\n");

			if (state == stateFirstProfileEnquiry)
			{
				// profile change
				return 1;
			}
			state=stateFinal;
			break;
		default:
			eDebug("[CI RM] unknown APDU tag 9F 80 %02x", tag[2]);
		}
	}

	return 0;
}

int eDVBCIResourceManagerSession::doAction()
{
	switch (state)
	{
	case stateStarted:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x10}; // profile enquiry
		sendAPDU(tag);
		state = stateFirstProfileEnquiry;
		return 0;
	}
	case stateFirstProfileEnquiry:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x12}; // profile change
		sendAPDU(tag);
		state=stateProfileChange;
		return 0;
	}
	case stateProfileChange:
	{
		eDebug("[CI RM] cannot deal with statProfileChange");
		break;
	}
	case stateProfileEnquiry:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x11};
		const unsigned char data[][4]=
			{
				{0x00, 0x01, 0x00, 0x41},
				{0x00, 0x02, 0x00, 0x41},
				{0x00, 0x03, 0x00, 0x41},
//				{0x00, 0x20, 0x00, 0x41}, // host control
				{0x00, 0x24, 0x00, 0x41},
				{0x00, 0x40, 0x00, 0x41},
//				{0x00, 0x10, 0x00, 0x41}, // auth.
			};
		const unsigned char data_v2[][4]=
			{
				{0x00, 0x01, 0x00, 0x41},
				{0x00, 0x01, 0x00, 0x42},
				{0x00, 0x02, 0x00, 0x41},
//				{0x00, 0x02, 0x00, 0x42},
				{0x00, 0x02, 0x00, 0x43},
				{0x00, 0x03, 0x00, 0x41},
				{0x00, 0x20, 0x00, 0x41},
//				{0x00, 0x20, 0x00, 0x42},
				{0x00, 0x24, 0x00, 0x41},
				{0x00, 0x40, 0x00, 0x41},
//				{0x00, 0x10, 0x00, 0x41},
				{0x00, 0x41, 0x00, 0x41},
//				{0x00, 0x41, 0x00, 0x42},
				{0x00, 0x8c, 0x10, 0x01},
//				{0x00, 0x8c, 0x10, 0x02},
				{0x00, 0x8d, 0x10, 0x01},
				{0x00, 0x8e, 0x10, 0x01},
//				{0x00, 0x8f, 0x10, 0x01},
//				{0x00, 0x97, 0x10, 0x01},
//				{0x00, 0x60, 0x60, 0x03},
//				{0x00, 0x04, 0x10, 0x01},
			};

		bool ciplus = (m_version == 1 || m_version == 2) and ciplus_cert_param_files_exists();
		const void *p = ciplus ? data_v2 : data;
		int len = ciplus ? sizeof(data_v2) : sizeof(data);
		sendAPDU(tag, p, len);
		state=stateFinal;
		return 0;
	}
	case stateFinal:
		eDebug("[CI RM] Should not happen: action on stateFinal");
	default:
		break;
	}
	return 0;
}
