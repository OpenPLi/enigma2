#ifndef __db_h
#define __db_h

#ifndef SWIG
#include <lib/dvb/idvb.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eptrlist.h>
#include <set>
#include <vector>
#include <sstream>
class ServiceDescriptionSection;

struct LCNData
{
private:
	bool FOUND;

	std::vector<std::string> split_str(std::string s)
	{
		std::vector<std::string> tokens;
		std::string token;
		std::stringstream str(s);
		while (getline(str, token, ':')) {
			tokens.push_back(token);
		}
		return tokens;
	}

public:
	int NS;
	int ONID;
	int TSID;
	int SID;
	int SIGNAL;
	int LCN;
	LCNData()
	{
		LCN = 0;
		SIGNAL = -1;
		FOUND = true;
	}

	eServiceReferenceDVB parse(const char *line)
	{

		if (sscanf(line, "%x:%x:%x:%x:%d:%d", &NS, &ONID, &TSID, &SID, &LCN, &SIGNAL) == 6)
			return eServiceReferenceDVB(eDVBNamespace(NS), eTransportStreamID(TSID), eOriginalNetworkID(ONID), eServiceID(SID), 0);
		else
			return eServiceReferenceDVB();
		
	}

	void Update(uint16_t lcn, uint32_t signal)
	{
		LCN = lcn;
		SIGNAL = signal;
		FOUND = true;
	}

	void write(FILE *lf, const eServiceReferenceDVB &key)
	{
		if (FOUND)
		{
			int sid = key.getServiceID().get();
			int tsid = key.getTransportStreamID().get();
			int onid = key.getOriginalNetworkID().get();
			int ns = key.getDVBNamespace().get();
			fprintf(lf, "%x:%x:%x:%x:%d:%d\n", ns, onid, tsid, sid, LCN, SIGNAL);
		}
	}

	void resetFound()
	{
		FOUND = false;
	}

};

class eIPTVDBItem
{
	public:
		std::string s_ref;
		int ampeg_pid;
		int aac3_pid;
		int aac4_pid;
		int addp_pid;
		int aaach_pid;
		int aaac_pid;
		int adra_pid;
		int subtitle_pid;
		int v_pid;
		eIPTVDBItem(const std::string sref, const int ampegpid, const int aac3pid, const int aac4pid, const int addppid, const int aaachpid, 
					const int aaacpid, const int adrapid, const int subtitlepid, const int vpid) {
			s_ref = sref;
			ampeg_pid = ampegpid;
			aac3_pid = aac3pid;
			aac4_pid = aac4pid;
			addp_pid = addppid;
			aaach_pid = aaachpid;
			aaac_pid = aaacpid;
			adra_pid = adrapid;
			subtitle_pid = subtitlepid;
			v_pid = vpid;
		};
};
#endif

class eDVBDB: public iDVBChannelList
{
	DECLARE_REF(eDVBDB);
	static eDVBDB *instance;
	friend class eDVBDBQuery;
	friend class eDVBDBBouquetQuery;
	friend class eDVBDBSatellitesQuery;
	friend class eDVBDBProvidersQuery;

	struct channel
	{
		ePtr<iDVBFrontendParameters> m_frontendParameters;
	};

	std::map<eDVBChannelID, channel> m_channels;

	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_services;

	std::map<std::string, eBouquet> m_bouquets;
	
	bool m_numbering_mode;
	int m_load_unlinked_userbouquets;
#ifdef SWIG
	eDVBDB();
	~eDVBDB();
#endif
private:
	void loadServiceListV5(FILE * f);
	std::map<eServiceReferenceDVB, LCNData> m_lcnmap;
public:
	std::vector<eIPTVDBItem> iptv_services;
// iDVBChannelList
	RESULT removeFlags(unsigned int flagmask, int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeServices(int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeService(const eServiceReference &service);
	PyObject *getFlag(const eServiceReference &service);
	PyObject *getCachedPid(const eServiceReference &service, int id);
	bool isCrypted(const eServiceReference &service);
	bool hasCAID(const eServiceReference &service, unsigned int caid);
	RESULT addCAID(const eServiceReference &service, unsigned int caid);
	RESULT addFlag(const eServiceReference &service, unsigned int flagmask);
	RESULT removeFlag(const eServiceReference &service, unsigned int flagmask);
	RESULT addOrUpdateBouquet(const std::string &name, const std::string &filename, SWIG_PYOBJECT(ePyObject) services, bool isAddedFirst = false);
	RESULT addOrUpdateBouquet(const std::string &name, SWIG_PYOBJECT(ePyObject) services, const int type, bool isAddedFirst = false);
	RESULT appendServicesToBouquet(const std::string &filename, SWIG_PYOBJECT(ePyObject) services);
	RESULT removeBouquet(const std::string &filename);
	RESULT addChannelToDB(const eServiceReference &service, const eDVBFrontendParameters &feparam, SWIG_PYOBJECT(ePyObject) cachedPids, SWIG_PYOBJECT(ePyObject) caPids, const int serviceFlags);
	void removeServicesFlag(unsigned int flagmask);
	PyObject *readSatellites(SWIG_PYOBJECT(ePyObject) sat_list, SWIG_PYOBJECT(ePyObject) sat_dict, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readTerrestrials(SWIG_PYOBJECT(ePyObject) ter_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readCables(SWIG_PYOBJECT(ePyObject) cab_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readATSC(SWIG_PYOBJECT(ePyObject) atsc_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *getLcnDBData();
#ifndef SWIG
	RESULT removeFlags(unsigned int flagmask, eDVBChannelID chid, unsigned int orb_pos);
	RESULT removeServices(eDVBChannelID chid, unsigned int orb_pos);
	RESULT removeServices(iDVBFrontendParameters *feparm);

	RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm);
	RESULT removeChannel(const eDVBChannelID &id);

	RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm);

	RESULT addService(const eServiceReferenceDVB &referenc, eDVBService *service);
	RESULT addOrUpdateService(const eServiceReferenceDVB &referenc, eDVBService *service);
	RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service);
	RESULT getLcnDBData(std::map<eServiceReferenceDVB, LCNData> &data);
	RESULT flush();

	RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *q, const eServiceReference &source);

	RESULT getBouquet(const eServiceReference &ref, eBouquet* &bouquet);
//////
	void loadBouquet(const char *path);
	void deleteBouquet(const std::string filename);
	eServiceReference searchReference(int tsid, int onid, int sid);
	void searchAllReferences(std::vector<eServiceReference> &result, int tsid, int onid, int sid);
	eDVBDB();
	virtual ~eDVBDB();
	int renumberBouquet(eBouquet &bouquet, int startChannelNum = 1);
	void addLcnToDB(int ns, int onid, int tsid, int sid, uint16_t lcn, uint32_t signal);
	void resetLcnDB();
	void readLcnDBFile();
#endif
	void setNumberingMode(bool numberingMode);
	void setLoadUnlinkedUserbouquets(int value) { m_load_unlinked_userbouquets=value; }
	void renumberBouquet();
	void loadServicelist(const char *filename);
	static eDVBDB *getInstance() { return instance; }
	void reloadServicelist();
	void saveServicelist();
	void saveIptvServicelist();
	void saveServicelist(const char *file);
	void saveLcnDB();
	void reloadBouquets();
	void parseServiceData(ePtr<eDVBService> s, std::string str);
};

#ifndef SWIG
	// we have to add a possibility to invalidate here.
class eDVBDBQueryBase: public iDVBChannelListQuery
{
	DECLARE_REF(eDVBDBQueryBase);
protected:
	ePtr<eDVBDB> m_db;
	ePtr<eDVBChannelQuery> m_query;
	eServiceReference m_source;
public:
	eDVBDBQueryBase(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	virtual int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b);
};

class eDVBDBQuery: public eDVBDBQueryBase
{
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator m_cursor;
public:
	eDVBDBQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
};

class eDVBDBBouquetQuery: public eDVBDBQueryBase
{
	std::list<eServiceReference>::iterator m_cursor;
public:
	eDVBDBBouquetQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
};

class eDVBDBListQuery: public eDVBDBQueryBase
{
protected:
	std::list<eServiceReferenceDVB> m_list;
	std::list<eServiceReferenceDVB>::iterator m_cursor;
public:
	eDVBDBListQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
	int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b);
};

class eDVBDBSatellitesQuery: public eDVBDBListQuery
{
public:
	eDVBDBSatellitesQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
};

class eDVBDBProvidersQuery: public eDVBDBListQuery
{
public:
	eDVBDBProvidersQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
};
#endif // SWIG

#endif
