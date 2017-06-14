#include <lib/base/eerror.h>
#include <lib/dvb/ecm.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

DEFINE_REF(eDVBECMParser);

eDVBECMParser::eDVBECMParser(iDVBDemux *demux)
{
	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("[eDVBECMParser] failed to create ECM PES reader!");
	else
		m_pes_reader->connectRead(sigc::mem_fun(*this, &eDVBECMParser::processData), m_read_connection);
}

eDVBECMParser::~eDVBECMParser()
{
}

int eDVBECMParser::start(int pid)
{
	if (m_pes_reader)
	{
		m_pid = pid;
		return m_pes_reader->start(pid);
	}
	else
		return -1;
}

int eDVBECMParser::stop()
{
	if (m_pes_reader)
	{
		eDebug("[eDVBECMParser] stop ecm");
		return m_pes_reader->stop();
	}
	return -1;
}

void eDVBECMParser::processData(const __u8 *p, int len)
{
}

void eDVBECMParser::processPESPacket(__u8 *pkt, int len)
{
}
