#ifndef __lib_dvb_ecm_h
#define __lib_dvb_ecm_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/dvb/pmt.h>
#include <lib/gdi/gpixmap.h>
#include <map>


class eDVBECMParser: public iObject, public ePESParser, public sigc::trackable
{
	DECLARE_REF(eDVBECMParser);
public:
	eDVBECMParser(iDVBDemux *demux);
	virtual ~eDVBECMParser();
	int start(int pid);
	int stop();
	void processData(const __u8 *p, int len);
private:
	void processPESPacket(__u8 *pkt, int len);
	int m_pid;

	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
};

#endif
