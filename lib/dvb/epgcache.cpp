#include <lib/dvb/epgcache.h>

#undef EPG_DEBUG

#ifdef EPG_DEBUG
#include <lib/service/event.h>
#endif

#include <fcntl.h>
#include <fstream>
#include <sys/vfs.h> // for statfs
#include <lib/base/encoding.h>
#include <lib/base/estring.h>
#include <lib/dvb/db.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/epgchanneldata.h>
#include <lib/dvb/epgtransponderdatareader.h>
#include <lib/dvb/lowlevel/eit.h>
#include <lib/base/nconfig.h>
#include <dvbsi++/descriptor_tag.h>

/* Interval between "garbage collect" cycles */
#define CLEAN_INTERVAL 60000    //  1 min

struct DescriptorPair
{
	int reference_count;
	__u8* data;

	DescriptorPair() {}
	DescriptorPair(int c, __u8* d): reference_count(c), data(d) {}
};

typedef std::tr1::unordered_map<uint32_t, DescriptorPair> DescriptorMap;

struct eventData
{
	uint8_t rawEITdata[10];
	uint8_t n_crc;
	uint8_t type;
	uint32_t *crc_list;
	static DescriptorMap descriptors;
	static uint8_t data[];
	static unsigned int CacheSize;
	static bool isCacheCorrupt;
	eventData(const eit_event_struct* e = NULL, int size = 0, int type = 0, int tsidonid = 0);
	~eventData();
	static void load(FILE *);
	static void save(FILE *);
	static void cacheCorrupt(const char* context);
	const eit_event_struct* get() const;
	int getEventID() const
	{
		return (rawEITdata[0] << 8) | rawEITdata[1];
	}
	time_t getStartTime() const
	{
		return parseDVBtime(&rawEITdata[2]);
	}
	int getDuration() const
	{
		return fromBCD(rawEITdata[7])*3600+fromBCD(rawEITdata[8])*60+fromBCD(rawEITdata[9]);
	}
};

unsigned int eventData::CacheSize = 0;
bool eventData::isCacheCorrupt = 0;
DescriptorMap eventData::descriptors;
uint8_t eventData::data[2 * 4096 + 12];
extern const uint32_t crc32_table[256];

const eServiceReference &handleGroup(const eServiceReference &ref)
{
	if (ref.flags & eServiceReference::isGroup)
	{
		ePtr<eDVBResourceManager> res;
		if (!eDVBResourceManager::getInstance(res))
		{
			ePtr<iDVBChannelList> db;
			if (!res->getChannelList(db))
			{
				eBouquet *bouquet = NULL;
				if (!db->getBouquet(ref, bouquet))
				{
					std::list<eServiceReference>::iterator it(bouquet->m_services.begin());
					if (it != bouquet->m_services.end())
						return *it;
				}
			}
		}
	}
	return ref;
}

static uint32_t calculate_crc_hash(const uint8_t *data, int size)
{
	uint32_t crc = 0;
	for (int i = 0; i < size; ++i)
		crc = (crc << 8) ^ crc32_table[((crc >> 24) ^ data[i]) & 0xFF];
	return crc;
}

eventData::eventData(const eit_event_struct* e, int size, int _type, int tsidonid)
	:n_crc(0), type(_type & 0xFF), crc_list(NULL)
{
	if (!e)
		return; /* Used when loading from file */

	uint32_t descr[65];
	uint32_t *pdescr=descr;

	uint8_t *data = (uint8_t*)e;
	int ptr=12;
	size -= 12;

	while(size > 1)
	{
		uint8_t *descr = data + ptr;
		int descr_len = descr[1];
		descr_len += 2;
		if (size >= descr_len)
		{
			switch (descr[0])
			{
				case EXTENDED_EVENT_DESCRIPTOR:
				case LINKAGE_DESCRIPTOR:
				case COMPONENT_DESCRIPTOR:
				case CONTENT_DESCRIPTOR:
				case PARENTAL_RATING_DESCRIPTOR:
				case PDC_DESCRIPTOR:
				{
					uint32_t crc = calculate_crc_hash(descr, descr_len);
					DescriptorMap::iterator it = descriptors.find(crc);
					if ( it == descriptors.end() )
					{
						CacheSize+=descr_len;
						uint8_t *d = new uint8_t[descr_len];
						memcpy(d, descr, descr_len);
						descriptors[crc] = DescriptorPair(1, d);
					}
					else
						++it->second.reference_count;
					*pdescr++ = crc;
					break;
				}
				case SHORT_EVENT_DESCRIPTOR:
				{
					//parse the data out from the short event descriptor
					//get the country code, which will be used for converting to UTF8
					std::string cc( (const char*)&descr[2], 3);
					std::transform(cc.begin(), cc.end(), cc.begin(), tolower);
					int table = encodingHandler.getCountryCodeDefaultMapping(cc);

					int eventNameLen = descr[5];
					int eventTextLen = descr[6 + eventNameLen];

					//convert our strings to UTF8
					std::string eventNameUTF8 = convertDVBUTF8((const unsigned char*)&descr[6], eventNameLen, table, tsidonid);
					std::string text((const char*)&descr[7 + eventNameLen], eventTextLen);
					unsigned int eventNameUTF8len = eventNameUTF8.length();

					//Rebuild the short event descriptor with UTF-8 strings

					//Save the title first
					if( eventNameUTF8len > 0 ) //only store the data if there is something to store
					{
						/*this will actually cause us to save some memory
						 previously some descriptors didnt match because there text was different and titles the same.
						 Now that we store them seperatly we can save some space on title data some rough calculation show anywhere from 20 - 40% savings
						*/
						eventNameUTF8len = truncateUTF8(eventNameUTF8, 255 - 6);
						int title_len = 6 + eventNameUTF8len;
						uint8_t *title_data = new uint8_t[title_len + 2];
						title_data[0] = SHORT_EVENT_DESCRIPTOR;
						title_data[1] = title_len;
						title_data[2] = descr[2];
						title_data[3] = descr[3];
						title_data[4] = descr[4];
						title_data[5] = eventNameUTF8len + 1;
						title_data[6] = 0x15; //identify event name as UTF-8
						memcpy(&title_data[7], eventNameUTF8.data(), eventNameUTF8len);
						title_data[7 + eventNameUTF8len] = 0;

						//Calculate the CRC, based on our new data
						title_len += 2; //add 2 the length to include the 2 bytes in the header
						uint32_t title_crc = calculate_crc_hash(title_data, title_len);

						DescriptorMap::iterator it = descriptors.find(title_crc);
						if ( it == descriptors.end() )
						{
							CacheSize += title_len;
							descriptors[title_crc] = DescriptorPair(1, title_data);
						}
						else
						{
							++it->second.reference_count;
							delete [] title_data;
						}
						*pdescr++ = title_crc;
					}

					//save text with original encoding
					if( eventTextLen > 0 ) //only store the data if there is something to store
					{
						int text_len = 6 + eventTextLen;
						uint8_t *text_data = new uint8_t[text_len + 2];
						text_data[0] = SHORT_EVENT_DESCRIPTOR;
						text_data[1] = text_len;
						text_data[2] = descr[2];
						text_data[3] = descr[3];
						text_data[4] = descr[4];
						text_data[5] = 0;
						text_data[6] = eventTextLen;
						memcpy(&text_data[7], text.data(), eventTextLen);

						text_len += 2; //add 2 the length to include the 2 bytes in the header
						uint32_t text_crc = calculate_crc_hash(text_data, text_len);

						DescriptorMap::iterator it = descriptors.find(text_crc);
						if ( it == descriptors.end() )
						{
							CacheSize += text_len;
							descriptors[text_crc] = DescriptorPair(1, text_data);
						}
						else
						{
							++it->second.reference_count;
							delete [] text_data;
						}
						*pdescr++ = text_crc;
					}
					break;
				}
				default: // do not cache all other descriptors
					break;
			}
			ptr += descr_len;
			size -= descr_len;
		}
		else
			break;
	}
	memcpy(rawEITdata, (uint8_t*)e, 10);
	ASSERT(pdescr <= &descr[65]);
	n_crc = pdescr - descr;
	if (n_crc)
	{
		crc_list = new uint32_t[n_crc];
		memcpy(crc_list, descr, n_crc * sizeof(uint32_t));
	}
	CacheSize += sizeof(*this) + n_crc * sizeof(uint32_t);
}

const eit_event_struct* eventData::get() const
{
	unsigned int pos = 12;
	memcpy(data, rawEITdata, 10);
	unsigned int descriptors_length = 0;
	for (uint8_t i = 0; i < n_crc; ++i)
	{
		DescriptorMap::iterator it = descriptors.find(crc_list[i]);
		if (it != descriptors.end())
		{
			unsigned int b = it->second.data[1] + 2;
			if (pos + b < sizeof(data))
			{
				memcpy(data + pos, it->second.data, b);
				pos += b;
				descriptors_length += b;
			}
		}
		else
			cacheCorrupt("eventData::get");
	}
	data[10] = (descriptors_length >> 8) & 0x0F;
	data[11] = descriptors_length & 0xFF;
	return (eit_event_struct*)data;
}

eventData::~eventData()
{
	for ( uint8_t i = 0; i < n_crc; ++i )
	{
		DescriptorMap::iterator it = descriptors.find(crc_list[i]);
		if ( it != descriptors.end() )
		{
			DescriptorPair &p = it->second;
			if (p.reference_count == 0)
			{
				eDebug("[eEPGCache] Eventdata reference count is already zero!");
			}
			if (!--p.reference_count) // no more used descriptor
			{
				CacheSize -= it->second.data[1];
				delete [] it->second.data;  	// free descriptor memory
				descriptors.erase(it);	// remove entry from descriptor map
			}
		}
		else
		{
			cacheCorrupt("eventData::~eventData");
		}
	}
	delete [] crc_list;
	CacheSize -= sizeof(*this) + n_crc * sizeof(uint32_t);
}

void eventData::load(FILE *f)
{
	int size = 0;
	int id=0;
	DescriptorPair p;
	uint8_t header[2];
	size_t ret; /* dummy value to store fread return values */
	ret = fread(&size, sizeof(int), 1, f);
	descriptors.rehash(size);
	while(size)
	{
		ret = fread(&id, sizeof(uint32_t), 1, f);
		ret = fread(&p.reference_count, sizeof(int), 1, f);
		ret = fread(header, 2, 1, f);
		int bytes = header[1]+2;
		p.data = new uint8_t[bytes];
		p.data[0] = header[0];
		p.data[1] = header[1];
		ret = fread(p.data+2, bytes-2, 1, f);
		// make sure we are not leaking memory
		DescriptorMap::iterator it = descriptors.find(id);
		if (it != descriptors.end())
		{
			delete [] it->second.data; // free descriptor memory
		}
		descriptors[id] = p;
		--size;
	}
	(void)ret;
}

void eventData::save(FILE *f)
{
	if (isCacheCorrupt)
		return;
	int size=descriptors.size();
	DescriptorMap::iterator it(descriptors.begin());
	fwrite(&size, sizeof(int), 1, f);
	while(size)
	{
		fwrite(&it->first, sizeof(uint32_t), 1, f);
		fwrite(&it->second.reference_count, sizeof(int), 1, f);
		fwrite(it->second.data, it->second.data[1]+2, 1, f);
		++it;
		--size;
	}
}

void eventData::cacheCorrupt(const char* context)
{

	eDebug("[eventData] EPG Cache is corrupt (%s), you should restart Enigma!", context);
	if (!isCacheCorrupt)
	{
		isCacheCorrupt = true;
		if (!eEPGCache::instance->m_filename.empty())
			unlink(eEPGCache::instance->m_filename.c_str()); // Remove corrupt EPG data
	}
}


eEPGCache* eEPGCache::instance;
static pthread_mutex_t cache_lock =
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

DEFINE_REF(eEPGCache)

eEPGCache::eEPGCache()
	:messages(this,1), m_running(false), m_enabledEpgSources(0), cleanTimer(eTimer::create(this)), m_timeQueryRef(nullptr)
{
	eDebug("[eEPGCache] Initialized EPGCache (wait for setCacheFile call now)");

	load_epg = eConfigManager::getConfigValue("config.usage.remote_fallback_import").find("epg") == std::string::npos;

	historySeconds = 0;

	CONNECT(messages.recv_msg, eEPGCache::gotMessage);
	CONNECT(eDVBLocalTimeHandler::getInstance()->m_timeUpdated, eEPGCache::timeUpdated);
	CONNECT(cleanTimer->timeout, eEPGCache::cleanLoop);

	std::ifstream onid_file;
	onid_file.open("/etc/enigma2/blacklist.onid");
	int tmp_onid;

	while (onid_file >> std::hex >>tmp_onid)
		onid_blacklist.insert(onid_blacklist.end(),1,tmp_onid);
	onid_file.close();

	instance=this;
}

void eEPGCache::setCacheFile(const char *path)
{
	bool inited = !m_filename.empty();
	m_filename = path;
	if (!inited)
	{
		eDebug("[eEPGCache] setCacheFile read/write epg data from/to '%s'", m_filename.c_str());
		if (eDVBLocalTimeHandler::getInstance()->ready())
			timeUpdated();
	}
}

void eEPGCache::timeUpdated()
{
	if (!m_filename.empty())
	{
		if (!m_running)
		{
			eDebug("[eEPGCache] time updated.. start EPG Mainloop");
			run();
			m_running = true;
			/*emit*/ epgCacheStarted();
		} else
			messages.send(Message(Message::timeChanged));
	}
	else
		eDebug("[eEPGCache] time updated.. but cache file not set yet.. dont start epg!!");
}

bool eEPGCache::FixOverlapping(EventCacheItem &servicemap, time_t TM, int duration, const timeMap::iterator &tm_it, const uniqueEPGKey &service)
{
	bool ret = false;
	timeMap::iterator tmp = tm_it;

	while ((tmp->first + tmp->second->getDuration() - 60) > TM)
	{
		if(tmp->first != TM
#ifdef ENABLE_PRIVATE_EPG
			&& tmp->second->type != PRIVATE
#endif
#ifdef ENABLE_MHW_EPG
			&& tmp->second->type != MHW
#endif
			)
		{
			uint16_t event_id = tmp->second->getEventID();
			servicemap.byEvent.erase(event_id);
#ifdef EPG_DEBUG
			Event evt((uint8_t*)tmp->second->get());
			eServiceEvent event;
			event.parseFrom(&evt, service.sid<<16|service.onid);
			eDebug("[eEPGCache] (1)erase no more used event %04x %d\n%s %s\n%s",
				service.sid, event_id,
				event.getBeginTimeString().c_str(),
				event.getEventName().c_str(),
				event.getExtendedDescription().c_str());
#endif
			delete tmp->second;
			if (tmp == servicemap.byTime.begin())
			{
				servicemap.byTime.erase(tmp);
				break;
			}
			else
				servicemap.byTime.erase(tmp--);
			ret = true;
		}
		else
		{
			if (tmp == servicemap.byTime.begin())
				break;
			--tmp;
		}
	}

	tmp = tm_it;
	while(tmp->first < (TM + duration - 60))
	{
		if (tmp->first != TM && tmp->second->type != PRIVATE)
		{
			uint16_t event_id = tmp->second->getEventID();
			servicemap.byEvent.erase(event_id);
#ifdef EPG_DEBUG
			Event evt((uint8_t*)tmp->second->get());
			eServiceEvent event;
			event.parseFrom(&evt, service.sid<<16|service.onid);
			eDebug("[eEPGCache] (2)erase no more used event %04x %d\n%s %s\n%s",
				service.sid, event_id,
				event.getBeginTimeString().c_str(),
				event.getEventName().c_str(),
				event.getExtendedDescription().c_str());
#endif
			delete tmp->second;
			servicemap.byTime.erase(tmp++);
			ret = true;
		}
		else
			++tmp;
		if (tmp == servicemap.byTime.end())
			break;
	}
	return ret;
}

void eEPGCache::sectionRead(const uint8_t *data, int source, eEPGChannelData *channel)
{
	const eit_t *eit = (const eit_t*) data;

	int len = eit->getSectionLength() - 1;
	int ptr = EIT_SIZE;
	if ( ptr >= len )
		return;

#if 0
		/*
		 * disable for now, as this hack breaks EIT parsing for
		 * services with a low segment_last_table_id
		 *
		 * Multichoice should be the exception, not the rule...
		 */

	// This fixed the EPG on the Multichoice irdeto systems
	// the EIT packet is non-compliant.. their EIT packet stinks
	if ( data[ptr-1] < 0x40 )
		--ptr;
#endif

	int onid = eit->getOriginalNetworkId();
	int tsid  = eit->getTransportStreamId();

	// Cablecom HACK .. tsid / onid in eit data are incorrect.. so we use
	// it from running channel (just for current transport stream eit data)
	/*
	 * Make an exception for BEV (onid 0x100, 0x101), which doesn't use
	 * SCHEDULE_OTHER. As a result SCHEDULE will contain data for different tsid's,
	 * so we should not replace it with the current tsid.
	 */
	bool use_transponder_chid = onid != 0x101 && onid != 0x100 && (source == SCHEDULE || (source == NOWNEXT && data[0] == 0x4E));

	if (use_transponder_chid && channel)
	{
		eDVBChannelID chid = channel->channel->getChannelID();

		onid = chid.original_network_id.get();
		tsid = chid.transport_stream_id.get();
	}
	uniqueEPGKey service( eit->getServiceID(), onid, tsid);

	eit_event_struct* eit_event = (eit_event_struct*) (data+ptr);
	int eit_event_size;
	int duration;

	time_t TM = parseDVBtime((const uint8_t*)eit_event + 2);
	time_t now = ::time(0);

	if ( TM != 3599 && TM > -1 && channel)
		channel->haveData |= source;

	singleLock s(cache_lock);
	// hier wird immer eine eventMap zurck gegeben.. entweder eine vorhandene..
	// oder eine durch [] erzeugte
	EventCacheItem &servicemap = eventDB[service];
	eventMap::iterator prevEventIt = servicemap.byEvent.end();
	timeMap::iterator prevTimeIt = servicemap.byTime.end();

	while (ptr<len)
	{
		uint16_t event_hash;
		eit_event_size = eit_event->getDescriptorsLoopLength()+EIT_LOOP_SIZE;

		duration = fromBCD(eit_event->duration_1)*3600+fromBCD(eit_event->duration_2)*60+fromBCD(eit_event->duration_3);
		TM = parseDVBtime((const uint8_t*)eit_event + 2, &event_hash);

		std::vector<int>::iterator m_it=find(onid_blacklist.begin(),onid_blacklist.end(),onid);
		if (m_it != onid_blacklist.end())
			goto next;

		if ( (TM != 3599) &&		// NVOD Service
		     (now <= (TM+duration)) &&	// skip old events
		     (TM < (now+28*24*60*60)) &&	// no more than 4 weeks in future
		     ( (onid != 1714) || (duration != (24*3600-1)) )	// PlatformaHD invalid event
		   )
		{
			uint16_t event_id = eit_event->getEventId();
			eventData *evt = 0;
			int ev_erase_count = 0;
			int tm_erase_count = 0;

			if (event_id == 0) {
				// hack for some polsat services on 13.0E..... but this also replaces other valid event_ids with value 0..
				// but we dont care about it...
				event_id = event_hash;
				eit_event->event_id_hi = event_hash >> 8;
				eit_event->event_id_lo = event_hash & 0xFF;
			}

			// search in eventmap
			eventMap::iterator ev_it =
				servicemap.byEvent.find(event_id);

//			eDebug("[eEPGCache] event_id is %d sid is %04x", event_id, service.sid);

			// entry with this event_id is already exist ?
			if ( ev_it != servicemap.byEvent.end() )
			{
				if ( source > ev_it->second->type )  // update needed ?
					goto next; // when not.. then skip this entry

				// search this event in timemap
				timeMap::iterator tm_it_tmp =
					servicemap.byTime.find(ev_it->second->getStartTime());

				if ( tm_it_tmp != servicemap.byTime.end() )
				{
					if ( tm_it_tmp->first == TM ) // just update eventdata
					{
						// exempt memory
						eventData *tmp = ev_it->second;
						ev_it->second = tm_it_tmp->second =
							new eventData(eit_event, eit_event_size, source, (tsid<<16)|onid);
						if (FixOverlapping(servicemap, TM, duration, tm_it_tmp, service))
						{
							prevEventIt = servicemap.byEvent.end();
							prevTimeIt = servicemap.byTime.end();
						}
						delete tmp;
						goto next;
					}
					else  // event has new event begin time
					{
						tm_erase_count++;
						// delete the found record from timemap
						servicemap.byTime.erase(tm_it_tmp);
						prevTimeIt = servicemap.byTime.end();
					}
				}
			}

			// search in timemap, for check of a case if new time has coincided with time of other event
			// or event was is not found in eventmap
			timeMap::iterator tm_it =
				servicemap.byTime.find(TM);

			if ( tm_it != servicemap.byTime.end() )
			{
				// event with same start time but another event_id...
				if ( source > tm_it->second->type &&
					ev_it == servicemap.byEvent.end() )
					goto next; // when not.. then skip this entry

				// search this time in eventmap
				eventMap::iterator ev_it_tmp =
					servicemap.byEvent.find(tm_it->second->getEventID());

				if ( ev_it_tmp != servicemap.byEvent.end() )
				{
					ev_erase_count++;
					// delete the found record from eventmap
					servicemap.byEvent.erase(ev_it_tmp);
					prevEventIt = servicemap.byEvent.end();
				}
			}
			evt = new eventData(eit_event, eit_event_size, source, (tsid<<16)|onid);
#ifdef EPG_DEBUG
			bool consistencyCheck=true;
#endif
			if (ev_erase_count > 0 && tm_erase_count > 0) // 2 different pairs have been removed
			{
				// exempt memory
				delete ev_it->second;
				delete tm_it->second;
				ev_it->second=evt;
				tm_it->second=evt;
			}
			else if (ev_erase_count == 0 && tm_erase_count > 0)
			{
				// exempt memory
				delete ev_it->second;
				tm_it = prevTimeIt = servicemap.byTime.insert( prevTimeIt, std::pair<const time_t, eventData*>( TM, evt ) );
				ev_it->second = evt;
			}
			else if (ev_erase_count > 0 && tm_erase_count == 0)
			{
				// exempt memory
				delete tm_it->second;
				ev_it = prevEventIt = servicemap.byEvent.insert( prevEventIt, std::pair<const uint16_t, eventData*>( event_id, evt) );
				tm_it->second = evt;
			}
			else // added new eventData
			{
#ifdef EPG_DEBUG
				consistencyCheck=false;
#endif
				ev_it = prevEventIt = servicemap.byEvent.insert( prevEventIt, std::pair<const uint16_t, eventData*>( event_id, evt) );
				tm_it = prevTimeIt = servicemap.byTime.insert( prevTimeIt, std::pair<const time_t, eventData*>( TM, evt ) );
			}

#ifdef EPG_DEBUG
			if ( consistencyCheck )
			{
				if ( tm_it->second != evt || ev_it->second != evt )
					eFatal("[eEPGCache] tm_it->second != ev_it->second");
				else if ( tm_it->second->getStartTime() != tm_it->first )
					eFatal("[eEPGCache] event start_time(%d) non equal timemap key(%d)",
						tm_it->second->getStartTime(), tm_it->first );
				else if ( tm_it->first != TM )
					eFatal("[eEPGCache] timemap key(%d) non equal TM(%d)",
						tm_it->first, TM);
				else if ( ev_it->second->getEventID() != ev_it->first )
					eFatal("[eEPGCache] event_id (%d) non equal event_map key(%d)",
						ev_it->second->getEventID(), ev_it->first);
				else if ( ev_it->first != event_id )
					eFatal("[eEPGCache] eventmap key(%d) non equal event_id(%d)",
						ev_it->first, event_id );
			}
#endif
			if (FixOverlapping(servicemap, TM, duration, tm_it, service))
			{
				prevEventIt = servicemap.byEvent.end();
				prevTimeIt = servicemap.byTime.end();
			}
		}
next:
#ifdef EPG_DEBUG
		if ( servicemap.byEvent.size() != servicemap.byTime.size() )
		{
			{
				CFile f("/media/hdd/event_map.txt", "w+");
				int i = 0;
				for (eventMap::iterator it(servicemap.byEvent.begin()); it != servicemap.byEvent.end(); ++it )
				{
					fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n",
					i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
				}
			}
			{
				CFile f("/media/hdd/time_map.txt", "w+");
				int i = 0;
				for (timeMap::iterator it(servicemap.byTime.begin()); it != servicemap.byTime.end(); ++it )
				{
					fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n",
						i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
				}
			}
			eFatal("[eEPGCache] (1)map sizes not equal :( sid %04x tsid %04x onid %04x size %zu size2 %zu",
				service.sid, service.tsid, service.onid,
				servicemap.byEvent.size(), servicemap.byTime.size() );
		}
#endif
		ptr += eit_event_size;
		eit_event = (eit_event_struct*)(((uint8_t*)eit_event) + eit_event_size);
	}
}

// epg cache needs to be locked(cache_lock) before calling the procedure
void eEPGCache::clearCompleteEPGCache()
{
	// cache_lock needs to be set in calling procedure!
	for (eventCache::iterator it(eventDB.begin()); it != eventDB.end(); ++it)
	{
		eventMap &evMap = it->second.byEvent;
		timeMap &tmMap = it->second.byTime;
		for (eventMap::iterator i = evMap.begin(); i != evMap.end(); ++i)
			delete i->second;
		evMap.clear();
		tmMap.clear();
	}
	eventDB.clear();
#ifdef ENABLE_PRIVATE_EPG
	content_time_tables.clear();
#endif
	eEPGTransponderDataReader::getInstance()->restartReader();
}

void eEPGCache::flushEPG(const uniqueEPGKey & s, bool lock) // lock only affects complete flush
{
	eDebug("[eEPGCache] flushEPG %d", (int)(bool)s);
	if (s)  // clear only this service
	{
		singleLock l(cache_lock);
		eventCache::iterator it = eventDB.find(s);
		if ( it != eventDB.end() )
		{
			eventMap &evMap = it->second.byEvent;
			timeMap &tmMap = it->second.byTime;
			tmMap.clear();
			for (eventMap::iterator i = evMap.begin(); i != evMap.end(); ++i)
				delete i->second;
			evMap.clear();
			eventDB.erase(it);

			// TODO .. search corresponding channel for removed service and remove this channel from lastupdated map
#ifdef ENABLE_PRIVATE_EPG
			contentMaps::iterator it =
				content_time_tables.find(s);
			if ( it != content_time_tables.end() )
			{
				it->second.clear();
				content_time_tables.erase(it);
			}
#endif
		}
	}
	else // clear complete EPG Cache
	{
		if (lock)
		{
			singleLock l(cache_lock);
			clearCompleteEPGCache();
		}
		else
			clearCompleteEPGCache();
	}
}

void eEPGCache::cleanLoop()
{
	{ /* scope for cache lock */
		time_t now = ::time(0) - historySeconds;
		singleLock s(cache_lock);

		for (eventCache::iterator DBIt = eventDB.begin(); DBIt != eventDB.end(); DBIt++)
		{
			bool updated = false;
			for (timeMap::iterator It = DBIt->second.byTime.begin(); It != DBIt->second.byTime.end() && It->first < now;)
			{
				if ( now > (It->first+It->second->getDuration()) )  // outdated normal entry (nvod references to)
				{
					// remove entry from eventMap
					eventMap::iterator b(DBIt->second.byEvent.find(It->second->getEventID()));
					if ( b != DBIt->second.byEvent.end() )
					{
						// release Heap Memory for this entry   (new ....)
//						eDebug("[eEPGCache] delete old event (evmap)");
						DBIt->second.byEvent.erase(b);
					}

					// remove entry from timeMap
//					eDebug("[eEPGCache] release heap mem");
					delete It->second;
					DBIt->second.byTime.erase(It++);
//					eDebug("[eEPGCache] delete old event (timeMap)");
					updated = true;
				}
				else
					++It;
			}
#ifdef ENABLE_PRIVATE_EPG
			if ( updated )
			{
				contentMaps::iterator x =
					content_time_tables.find( DBIt->first );
				if ( x != content_time_tables.end() )
				{
					timeMap &tmMap = DBIt->second.byTime;
					for ( contentMap::iterator i = x->second.begin(); i != x->second.end(); )
					{
						for ( contentTimeMap::iterator it(i->second.begin());
							it != i->second.end(); )
						{
							if ( tmMap.find(it->second.first) == tmMap.end() )
								i->second.erase(it++);
							else
								++it;
						}
						if ( i->second.size() )
							++i;
						else
							x->second.erase(i++);
					}
				}
			}
#endif
		}
	} /* release lock */
	cleanTimer->start(CLEAN_INTERVAL,true);
}

eEPGCache::~eEPGCache()
{
	m_running = false;
	messages.send(Message::quit);
	kill(); // waiting for thread shutdown
	singleLock s(cache_lock);
	for (eventCache::iterator evIt = eventDB.begin(); evIt != eventDB.end(); evIt++)
		for (eventMap::iterator It = evIt->second.byEvent.begin(); It != evIt->second.byEvent.end(); It++)
			delete It->second;
}

void eEPGCache::gotMessage( const Message &msg )
{
	switch (msg.type)
	{
		case Message::flush:
			flushEPG(msg.service);
			break;
		case Message::quit:
			quit(0);
			break;
		case Message::timeChanged:
			cleanLoop();
			break;
		default:
			eDebug("[eEPGCache] unhandled EPGCache Message!!");
			break;
	}
}

void eEPGCache::thread()
{
	hasStarted();
	if (nice(4) == -1)
	{
		eDebug("[eEPGCache] thread failed to modify scheduling priority (%m)");
	}
	if (load_epg) { load(); }
	cleanLoop();
	runLoop();
	save();
}

static const char* EPGDAT_IN_FLASH = "/epg.dat";

void eEPGCache::load()
{
	if (m_filename.empty())
		m_filename = "/media/hdd/epg.dat";
	const char* EPGDAT = m_filename.c_str();
	std::string filenamex = m_filename + ".loading";
	const char* EPGDATX = filenamex.c_str();
	FILE *f = fopen(EPGDAT, "rb");
	int renameResult;
	size_t ret; /* dummy value to store fread return values */
	if (f == NULL)
	{
		/* No EPG on harddisk, so try internal flash */
		eDebug("[eEPGCache] %s not found, try /epg.dat", EPGDAT);
		EPGDAT = EPGDAT_IN_FLASH;
		f = fopen(EPGDAT, "rb");
		if (f == NULL)
			return;
		renameResult = -1;
	}
	else
	{
		unlink(EPGDATX);
		renameResult = rename(EPGDAT, EPGDATX);
		if (renameResult) eDebug("[eEPGCache] failed to rename %s", EPGDAT);
	}
	{
		int size=0;
		int cnt=0;
		unsigned int magic=0;
		unlink(EPGDAT_IN_FLASH);/* Don't keep it around when in flash */
		ret = fread( &magic, sizeof(int), 1, f);
		if (magic != 0x98765432)
		{
			eDebug("[eEPGCache] epg file has incorrect byte order.. dont read it");
			fclose(f);
			return;
		}
		char text1[13];
		ret = fread( text1, 13, 1, f);
		if ( !memcmp( text1, "ENIGMA_EPG_V7", 13) )
		{
			singleLock s(cache_lock);
			if (eventDB.size() > 0)
			{
				clearCompleteEPGCache();
			}
			ret = fread( &size, sizeof(int), 1, f);
			eventDB.rehash(size); /* Reserve buckets in advance */
			while(size--)
			{
				uniqueEPGKey key;
				int size=0;
				ret = fread( &key, sizeof(uniqueEPGKey), 1, f);
				ret = fread( &size, sizeof(int), 1, f);
				EventCacheItem& item = eventDB[key]; /* Constructs new entry */
				while(size--)
				{
					uint8_t len=0;
					uint8_t type=0;
					eventData *event=0;
					ret = fread( &type, sizeof(uint8_t), 1, f);
					ret = fread( &len, sizeof(uint8_t), 1, f);
					event = new eventData(0, len, type);
					event->n_crc = (len-10) / sizeof(uint32_t);
					ret = fread( event->rawEITdata, 10, 1, f);
					if (event->n_crc)
					{
						event->crc_list = new uint32_t[event->n_crc];
						ret = fread( event->crc_list, sizeof(uint32_t), event->n_crc, f);
					}
					eventData::CacheSize += sizeof(eventData) + event->n_crc * sizeof(uint32_t);
					item.byEvent[event->getEventID()] = event;
					item.byTime[event->getStartTime()] = event;
					++cnt;
				}
			}
			eventData::load(f);
			eDebug("[eEPGCache] %d events read from %s", cnt, EPGDAT);
#ifdef ENABLE_PRIVATE_EPG
			char text2[11];
			ret = fread( text2, 11, 1, f);
			if ( !memcmp( text2, "PRIVATE_EPG", 11) )
			{
				size=0;
				ret = fread( &size, sizeof(int), 1, f);
				while(size--)
				{
					int size=0;
					uniqueEPGKey key;
					ret = fread( &key, sizeof(uniqueEPGKey), 1, f);
					eventMap &evMap = eventDB[key].byEvent;
					ret = fread( &size, sizeof(int), 1, f);
					while(size--)
					{
						int size;
						int content_id;
						ret = fread( &content_id, sizeof(int), 1, f);
						ret = fread( &size, sizeof(int), 1, f);
						while(size--)
						{
							time_t time1, time2;
							uint16_t event_id;
							ret = fread( &time1, sizeof(time_t), 1, f);
							ret = fread( &time2, sizeof(time_t), 1, f);
							ret = fread( &event_id, sizeof(uint16_t), 1, f);
							content_time_tables[key][content_id][time1]=std::pair<time_t, uint16_t>(time2, event_id);
							eventMap::iterator it =
								evMap.find(event_id);
							if (it != evMap.end())
								it->second->type = PRIVATE;
						}
					}
				}
			}
#endif // ENABLE_PRIVATE_EPG
		}
		else
			eDebug("[eEPGCache] don't read old epg database");
		posix_fadvise(fileno(f), 0, 0, POSIX_FADV_DONTNEED);
		fclose(f);
		// We got this far, so the EPG file is okay.
		if (renameResult == 0)
		{
			renameResult = rename(EPGDATX, EPGDAT);
			if (renameResult) eDebug("[eEPGCache] failed to rename epg.dat back");
		}
	}
	(void)ret;
}

void eEPGCache::save()
{
	if (!load_epg)
		return;
	const char* EPGDAT = m_filename.c_str();
	if (eventData::isCacheCorrupt)
		return;
	// only save epg.dat if it's worth the trouble...
	if (eventData::CacheSize < 10240)
		return;

	/* create empty file */
	FILE *f = fopen(EPGDAT, "wb");
	if (!f)
	{
		eDebug("[eEPGCache] Failed to open %s: %m", EPGDAT);
		EPGDAT = EPGDAT_IN_FLASH;
		f = fopen(EPGDAT, "wb");
		if (!f)
			return;
	}

	char* buf = realpath(EPGDAT, NULL);
	if (!buf)
	{
		eDebug("[eEPGCache] realpath to %s failed in save: %m", EPGDAT);
		fclose(f);
		return;
	}

	eDebug("[eEPGCache] store epg to realpath '%s'", buf);

	struct statfs s;
	off64_t tmp;
	if (statfs(buf, &s) < 0) {
		eDebug("[eEPGCache] statfs %s failed in save: %m", buf);
		fclose(f);
		free(buf);
		return;
	}

	// check for enough free space on storage
	tmp=s.f_bfree;
	tmp*=s.f_bsize;
	if ( tmp < (eventData::CacheSize*12)/10 ) // 20% overhead
	{
		eDebug("[eEPGCache] not enough free space at '%s' %jd bytes available but %u needed", buf, (intmax_t)tmp, (eventData::CacheSize*12)/10);
		free(buf);
		fclose(f);
		return;
	}

	free(buf);

	singleLock lockcache(cache_lock);

	int cnt=0;
	unsigned int magic = 0x98765432;
	fwrite( &magic, sizeof(int), 1, f);
	const char *text = "UNFINISHED_V7";
	fwrite( text, 13, 1, f );
	int size = eventDB.size();
	fwrite( &size, sizeof(int), 1, f );
	for (eventCache::iterator service_it(eventDB.begin()); service_it != eventDB.end(); ++service_it)
	{
		timeMap &timemap = service_it->second.byTime;
		fwrite( &service_it->first, sizeof(uniqueEPGKey), 1, f);
		size = timemap.size();
		fwrite( &size, sizeof(int), 1, f);
		for (timeMap::iterator time_it(timemap.begin()); time_it != timemap.end(); ++time_it)
		{
			uint8_t len = time_it->second->n_crc * sizeof(uint32_t) + 10;
			fwrite( &time_it->second->type, sizeof(uint8_t), 1, f );
			fwrite( &len, sizeof(uint8_t), 1, f);
			fwrite( time_it->second->rawEITdata, 10, 1, f);
			fwrite( time_it->second->crc_list, sizeof(uint32_t), time_it->second->n_crc, f);
			++cnt;
		}
	}
	eDebug("[eEPGCache] %d events written to %s", cnt, EPGDAT);
	eventData::save(f);
#ifdef ENABLE_PRIVATE_EPG
	const char* text3 = "PRIVATE_EPG";
	fwrite( text3, 11, 1, f );
	size = content_time_tables.size();
	fwrite( &size, sizeof(int), 1, f);
	for (contentMaps::iterator a = content_time_tables.begin(); a != content_time_tables.end(); ++a)
	{
		contentMap &content_time_table = a->second;
		fwrite( &a->first, sizeof(uniqueEPGKey), 1, f);
		int size = content_time_table.size();
		fwrite( &size, sizeof(int), 1, f);
		for (contentMap::iterator i = content_time_table.begin(); i != content_time_table.end(); ++i )
		{
			int size = i->second.size();
			fwrite( &i->first, sizeof(int), 1, f);
			fwrite( &size, sizeof(int), 1, f);
			for ( contentTimeMap::iterator it(i->second.begin());
				it != i->second.end(); ++it )
			{
				fwrite( &it->first, sizeof(time_t), 1, f);
				fwrite( &it->second.first, sizeof(time_t), 1, f);
				fwrite( &it->second.second, sizeof(uint16_t), 1, f);
			}
		}
	}
#endif
	// write version string after binary data
	// has been written to disk.
	fsync(fileno(f));
	fseek(f, sizeof(int), SEEK_SET);
	fwrite("ENIGMA_EPG_V7", 13, 1, f);
	fclose(f);
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eventData *&result, int direction)
// if t == -1 we search the current event...
{
	uniqueEPGKey key(handleGroup(service));

	// check if EPG for this service is ready...
	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.byEvent.empty() ) // entrys cached ?
	{
		if (t==-1)
			t = ::time(0);
		timeMap::iterator i = direction <= 0 ? It->second.byTime.lower_bound(t) :  // find > or equal
			It->second.byTime.upper_bound(t); // just >
		if ( i != It->second.byTime.end() )
		{
			if ( direction < 0 || (direction == 0 && i->first > t) )
			{
				timeMap::iterator x = i;
				--x;
				if ( x != It->second.byTime.end() )
				{
					time_t start_time = x->first;
					if (direction >= 0)
					{
						if (t < start_time)
							return -1;
						if (t > (start_time+x->second->getDuration()))
							return -1;
					}
					i = x;
				}
				else
					return -1;
			}
			result = i->second;
			return 0;
		}
	}
	return -1;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, Event *& result, int direction)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data, direction);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, ePtr<eServiceEvent> &result, int direction)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data, direction);
	result = NULL;
	if ( !ret && data )
	{
		Event ev((uint8_t*)data->get());
		result = new eServiceEvent();
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)service;
		ret = result->parseFrom(&ev, (ref.getTransportStreamID().get()<<16)|ref.getOriginalNetworkID().get());
	}
	return ret;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, const eventData *&result )
{
	uniqueEPGKey key(handleGroup(service));

	eventCache::iterator It = eventDB.find(key);
	if (It != eventDB.end())
	{
		eventMap::iterator i = It->second.byEvent.find(event_id);
		if ( i != It->second.byEvent.end() )
		{
			result = i->second;
			return 0;
		}
		else
		{
			result = 0;
			eDebug("[eEPGCache] event %04x not found in epgcache", event_id);
		}
	}
	return -1;
}

RESULT eEPGCache::saveEventToFile(const char* filename, const eServiceReference &service, int eit_event_id, time_t begTime, time_t endTime)
{
	RESULT ret = -1;
	singleLock s(cache_lock);
	const eventData *data = NULL;
	if ( eit_event_id != -1 )
	{
		eDebug("[eEPGCache] %s epg event id %x", __func__, eit_event_id);
		ret = lookupEventId(service, eit_event_id, data);
	}
	if ( (ret != 0) && (begTime != -1) )
	{
		time_t queryTime = begTime;
		if (endTime != -1)
			queryTime += (endTime - begTime) / 2;
		ret = lookupEventTime(service, queryTime, data);
	}
	if (ret == 0)
	{
		int fd = open(filename, O_CREAT|O_WRONLY, 0666);
		if (fd < 0)
		{
			eDebug("[eEPGCache] Failed to create file: %s", filename);
			return fd;
		}
		const eit_event_struct *event = data->get();
		int evLen = event->getDescriptorsLoopLength() + 12/*EIT_LOOP_SIZE*/;
		int wr = ::write( fd, event, evLen );
		::close(fd);
		if ( wr != evLen )
		{
			::unlink(filename); /* Remove faulty file */
			eDebug("[eEPGCache] eit write error on %s: %m", filename);
			ret = (wr < 0) ? wr : -1;
		}
	}
	return ret;
}


RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, Event *& result)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventId(service, event_id, data);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, ePtr<eServiceEvent> &result)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventId(service, event_id, data);
	result = NULL;
	if ( !ret && data )
	{
		Event ev((uint8_t*)data->get());
		result = new eServiceEvent();
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)service;
		ret = result->parseFrom(&ev, (ref.getTransportStreamID().get()<<16)|ref.getOriginalNetworkID().get());
	}
	return ret;
}

RESULT eEPGCache::startTimeQuery(const eServiceReference &service, time_t begin, int minutes)
{
	singleLock s(cache_lock);

	if (m_timeQueryRef)
		delete m_timeQueryRef;
	m_timeQueryRef = (eServiceReferenceDVB*)new eServiceReference(handleGroup(service));

	if (begin == -1)
		begin = ::time(0);

	m_timeQueryBegin = begin;
	m_timeQueryMinutes = minutes;
	m_timeQueryCount = 0;

	eventCache::iterator It = eventDB.find(*m_timeQueryRef);
	if ( It != eventDB.end() && !It->second.byTime.empty() )
	{
		timeMap::iterator timemap_it = It->second.byTime.lower_bound(m_timeQueryBegin);
		if ( timemap_it != It->second.byTime.end() )
		{
			if ( timemap_it->first != m_timeQueryBegin )
			{
				timeMap::iterator x = timemap_it;
				--x;
				if ( x != It->second.byTime.end() )
				{
					time_t start_time = x->first;
					if ( m_timeQueryBegin > start_time && m_timeQueryBegin < (start_time+x->second->getDuration()))
						timemap_it = x;
				}
			}
		}

		timeMap::iterator timemap_end;
		if (m_timeQueryMinutes != -1)
			timemap_end = It->second.byTime.lower_bound(m_timeQueryBegin + m_timeQueryMinutes * 60);
		else
			timemap_end = It->second.byTime.end();

		return timemap_it == timemap_end ? -1 : 0;
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(Event *&result)
{
	singleLock s(cache_lock);
	eventCache::iterator It = eventDB.find(*m_timeQueryRef);
	if ( It != eventDB.end() && !It->second.byTime.empty() )
	{
		timeMap::iterator timemap_it = It->second.byTime.lower_bound(m_timeQueryBegin);
		if ( timemap_it != It->second.byTime.end() )
		{
			if ( timemap_it->first != m_timeQueryBegin )
			{
				timeMap::iterator x = timemap_it;
				--x;
				if ( x != It->second.byTime.end() )
				{
					time_t start_time = x->first;
					if ( m_timeQueryBegin > start_time && m_timeQueryBegin < (start_time+x->second->getDuration()))
						timemap_it = x;
				}
			}
		}

		timeMap::iterator timemap_end;
		if (m_timeQueryMinutes != -1)
			timemap_end = It->second.byTime.lower_bound(m_timeQueryBegin + m_timeQueryMinutes * 60);
		else
			timemap_end = It->second.byTime.end();

		for (int i = 0; i < m_timeQueryCount; i++)
		{
			if ( timemap_it == timemap_end )
				return -1;
			else
				timemap_it++;
		}
		if ( timemap_it != timemap_end )
		{
			result = new Event((uint8_t*)timemap_it->second->get());
			m_timeQueryCount++;
			return 0;
		}
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(ePtr<eServiceEvent> &result)
{
	singleLock s(cache_lock);
	eventCache::iterator It = eventDB.find(*m_timeQueryRef);
	if ( It != eventDB.end() && !It->second.byTime.empty() )
	{
		timeMap::iterator timemap_it = It->second.byTime.lower_bound(m_timeQueryBegin);
		if ( timemap_it != It->second.byTime.end() )
		{
			if ( timemap_it->first != m_timeQueryBegin )
			{
				timeMap::iterator x = timemap_it;
				--x;
				if ( x != It->second.byTime.end() )
				{
					time_t start_time = x->first;
					if ( m_timeQueryBegin > start_time && m_timeQueryBegin < (start_time+x->second->getDuration()))
						timemap_it = x;
				}
			}
		}

		timeMap::iterator timemap_end;
		if (m_timeQueryMinutes != -1)
			timemap_end = It->second.byTime.lower_bound(m_timeQueryBegin + m_timeQueryMinutes * 60);
		else
			timemap_end = It->second.byTime.end();

		for (int i = 0; i < m_timeQueryCount; i++)
		{
			if ( timemap_it == timemap_end )
				return -1;
			else
				timemap_it++;
		}
		if ( timemap_it != timemap_end )
		{
			Event ev((uint8_t*)timemap_it->second->get());
			result = new eServiceEvent();
			int currentQueryTsidOnid = (m_timeQueryRef->getTransportStreamID().get()<<16) | m_timeQueryRef->getOriginalNetworkID().get();
			m_timeQueryCount++;
			return result->parseFrom(&ev, currentQueryTsidOnid);
		}
	}
	return -1;
}

void fillTuple(ePyObject tuple, const char *argstring, int argcount, ePyObject service_reference, eServiceEvent *ptr, ePyObject service_name, ePyObject nowTime, eventData *evData )
{
	// eDebug("[eEPGCache] fillTuple arg=%s argcnt=%d, ptr=%d evData=%d", argstring, argcount, ptr ? 1 : 0, evData ? 1 : 0);
	ePyObject tmp;
	int spos=0, tpos=0;
	char c;
	while(spos < argcount)
	{
		bool inc_refcount=false;
		switch((c=argstring[spos++]))
		{
			case '0': // PyLong 0
				tmp = PyLong_FromLong(0);
				break;
			case 'I': // Event Id
				tmp = evData ? PyLong_FromLong(evData->getEventID()) : (ptr ? PyLong_FromLong(ptr->getEventId()) : ePyObject());
				break;
			case 'B': // Event Begin Time
				tmp = ptr ? PyLong_FromLong(ptr->getBeginTime()) : (evData ? PyLong_FromLong(evData->getStartTime()) : ePyObject());
				break;
			case 'D': // Event Duration
				tmp = ptr ? PyLong_FromLong(ptr->getDuration()) : (evData ? PyLong_FromLong(evData->getDuration()) : ePyObject());
				break;
			case 'T': // Event Title
				tmp = ptr ? PyString_FromString(ptr->getEventName().c_str()) : ePyObject();
				break;
			case 'S': // Event Short Description
				tmp = ptr ? PyString_FromString(ptr->getShortDescription().c_str()) : ePyObject();
				break;
			case 'E': // Event Extended Description
				tmp = ptr ? PyString_FromString(ptr->getExtendedDescription().c_str()) : ePyObject();
				break;
			case 'P': // Event Parental Rating
				tmp = ptr ? ePyObject(ptr->getParentalData()) : ePyObject();
				break;
			case 'W': // Event Content Description
				tmp = ptr ? ePyObject(ptr->getGenreData()) : ePyObject();
				break;
			case 'C': // Current Time
				tmp = nowTime;
				inc_refcount = true;
				break;
			case 'R': // service reference string
				tmp = service_reference;
				inc_refcount = true;
				break;
			case 'n': // short service name
			case 'N': // service name
				tmp = service_name;
				inc_refcount = true;
				break;
			case 'X':
				++argcount;
				continue;
			default:  // ignore unknown
				tmp = ePyObject();
				eDebug("[eEPGCache] fillTuple unknown '%c'... insert 'None' in result", c);
		}
		if (!tmp)
		{
			tmp = Py_None;
			inc_refcount = true;
		}
		if (inc_refcount)
			Py_INCREF(tmp);
		PyTuple_SET_ITEM(tuple, tpos++, tmp);
	}
}

int handleEvent(eServiceEvent *ptr, ePyObject dest_list, const char* argstring, int argcount, ePyObject service, ePyObject nowTime, ePyObject service_name, ePyObject convertFunc, ePyObject convertFuncArgs)
{
	if (convertFunc)
	{
		fillTuple(convertFuncArgs, argstring, argcount, service, ptr, service_name, nowTime, 0);
		ePyObject result = PyObject_CallObject(convertFunc, convertFuncArgs);
		if (!result)
		{
			if (service_name)
				Py_DECREF(service_name);
			if (nowTime)
				Py_DECREF(nowTime);
			Py_DECREF(convertFuncArgs);
			Py_DECREF(dest_list);
			PyErr_SetString(PyExc_StandardError,
				"error in convertFunc execute");
			eDebug("[eEPGCache] handleEvent: error in convertFunc execute");
			return -1;
		}
		PyList_Append(dest_list, result);
		Py_DECREF(result);
	}
	else
	{
		ePyObject tuple = PyTuple_New(argcount);
		fillTuple(tuple, argstring, argcount, service, ptr, service_name, nowTime, 0);
		PyList_Append(dest_list, tuple);
		Py_DECREF(tuple);
	}
	return 0;
}

// here we get a python list
// the first entry in the list is a python string to specify the format of the returned tuples (in a list)
//   0 = PyLong(0)
//   I = Event Id
//   B = Event Begin Time
//   D = Event Duration
//   T = Event Title
//   S = Event Short Description
//   E = Event Extended Description
//   P = Event Parental Rating
//   W = Event Content Description ('W'hat)
//   C = Current Time
//   R = Service Reference
//   N = Service Name
//   n = Short Service Name
//   X = Return a minimum of one tuple per service in the result list... even when no event was found.
//       The returned tuple is filled with all available infos... non avail is filled as None
//       The position and existence of 'X' in the format string has no influence on the result tuple... its completely ignored..
// then for each service follows a tuple
//   first tuple entry is the servicereference (as string... use the ref.toString() function)
//   the second is the type of query
//     2 = event_id
//    -1 = event before given start_time
//     0 = event intersects given start_time
//    +1 = event after given start_time
//   the third
//      when type is eventid it is the event_id
//      when type is time then it is the start_time ( -1 for now_time )
//   the fourth is the end_time .. ( optional .. for query all events in time range)

PyObject *eEPGCache::lookupEvent(ePyObject list, ePyObject convertFunc)
{
	ePyObject convertFuncArgs;
	int argcount=0;
	const char *argstring=NULL;
	if (!PyList_Check(list))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
		eDebug("[eEPGCache] no list");
		return NULL;
	}
	int listIt=0;
	int listSize=PyList_Size(list);
	if (!listSize)
	{
		PyErr_SetString(PyExc_StandardError,
			"no params given");
		eDebug("[eEPGCache] no params given");
		return NULL;
	}
	else
	{
		ePyObject argv=PyList_GET_ITEM(list, 0); // borrowed reference!
		if (PyString_Check(argv))
		{
			argstring = PyString_AS_STRING(argv);
			++listIt;
		}
		else
			argstring = "I"; // just event id as default
		argcount = strlen(argstring);
//		eDebug("[eEPGCache] have %d args('%s')", argcount, argstring);
	}

	bool forceReturnOne = strchr(argstring, 'X') ? true : false;
	if (forceReturnOne)
		--argcount;

	if (convertFunc)
	{
		if (!PyCallable_Check(convertFunc))
		{
			PyErr_SetString(PyExc_StandardError,
				"convertFunc must be callable");
			eDebug("[eEPGCache] convertFunc is not callable");
			return NULL;
		}
		convertFuncArgs = PyTuple_New(argcount);
	}

	ePyObject nowTime = strchr(argstring, 'C') ?
		PyLong_FromLong(::time(0)) :
		ePyObject();

	int must_get_service_name = strchr(argstring, 'N') ? 1 : strchr(argstring, 'n') ? 2 : 0;

	// create dest list
	ePyObject dest_list=PyList_New(0);
	while(listSize > listIt)
	{
		ePyObject item=PyList_GET_ITEM(list, listIt++); // borrowed reference!
		if (PyTuple_Check(item))
		{
			bool service_changed=false;
			int type=0;
			long event_id=-1;
			time_t stime=-1;
			int minutes=0;
			int tupleSize=PyTuple_Size(item);
			int tupleIt=0;
			ePyObject service;
			while(tupleSize > tupleIt)  // parse query args
			{
				ePyObject entry=PyTuple_GET_ITEM(item, tupleIt); // borrowed reference!
				switch(tupleIt++)
				{
					case 0:
					{
						if (!PyString_Check(entry))
						{
							eDebug("[eEPGCache] tuple entry 0 is no a string");
							goto skip_entry;
						}
						service = entry;
						break;
					}
					case 1:
						type=PyInt_AsLong(entry);
						if (type < -1 || type > 2)
						{
							eDebug("[eEPGCache] unknown type %d", type);
							goto skip_entry;
						}
						break;
					case 2:
						event_id=stime=PyInt_AsLong(entry);
						break;
					case 3:
						minutes=PyInt_AsLong(entry);
						break;
					default:
						eDebug("[eEPGCache] unneeded extra argument");
						break;
				}
			}

			if (minutes && stime == -1)
				stime = ::time(0);

			eServiceReference ref(handleGroup(eServiceReference(PyString_AS_STRING(service))));
			// redirect subservice querys to parent service
			eServiceReferenceDVB &dvb_ref = (eServiceReferenceDVB&)ref;
			if (dvb_ref.getParentTransportStreamID().get()) // linkage subservice
			{
				eServiceCenterPtr service_center;
				if (!eServiceCenter::getPrivInstance(service_center))
				{
					dvb_ref.setTransportStreamID( dvb_ref.getParentTransportStreamID() );
					dvb_ref.setServiceID( dvb_ref.getParentServiceID() );
					dvb_ref.setParentTransportStreamID(eTransportStreamID(0));
					dvb_ref.setParentServiceID(eServiceID(0));
					dvb_ref.name="";
					service = PyString_FromString(dvb_ref.toString().c_str());
					service_changed = true;
				}
			}

			ePyObject service_name;
			if (must_get_service_name)
			{
				ePtr<iStaticServiceInformation> sptr;
				eServiceCenterPtr service_center;
				eServiceCenter::getPrivInstance(service_center);
				if (service_center)
				{
					service_center->info(ref, sptr);
					if (sptr)
					{
						std::string name;
						sptr->getName(ref, name);

						if (must_get_service_name == 1)
						{
							size_t pos;
							// filter short name brakets
							while((pos = name.find("\xc2\x86")) != std::string::npos)
								name.erase(pos,2);
							while((pos = name.find("\xc2\x87")) != std::string::npos)
								name.erase(pos,2);
						}
						else
							name = buildShortName(name);

						if (name.length())
							service_name = PyString_FromString(name.c_str());
					}
				}
				if (!service_name)
					service_name = PyString_FromString("<n/a>");
			}
			if (minutes)
			{
				if (!startTimeQuery(ref, stime, minutes))
				{
					ePtr<eServiceEvent> evt;
					while ( getNextTimeEntry(evt) != -1 )
					{
						if (handleEvent(evt, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
							return 0;  // error
					}
				}
				else if (forceReturnOne && handleEvent(0, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
					return 0;  // error
			}
			else
			{
				eServiceEvent evt;
				const eventData *ev_data=0;
				if (stime)
				{
					singleLock s(cache_lock);
					if (type == 2)
						lookupEventId(ref, event_id, ev_data);
					else
						lookupEventTime(ref, stime, ev_data, type);
					if (ev_data)
					{
						const eServiceReferenceDVB &dref = (const eServiceReferenceDVB&)ref;
						Event ev((uint8_t*)ev_data->get());
						evt.parseFrom(&ev, (dref.getTransportStreamID().get()<<16)|dref.getOriginalNetworkID().get());
					}
				}
				if (ev_data)
				{
					if (handleEvent(&evt, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
						return 0; // error
				}
				else if (forceReturnOne && handleEvent(0, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
					return 0; // error
			}
			if (service_changed)
				Py_DECREF(service);
			if (service_name)
				Py_DECREF(service_name);
		}
skip_entry:
		;
	}
	if (convertFuncArgs)
		Py_DECREF(convertFuncArgs);
	if (nowTime)
		Py_DECREF(nowTime);
	return dest_list;
}

static void fill_eit_start(eit_event_struct *evt, time_t t)
{
    tm *time = gmtime(&t);

    int l = 0;
    int month = time->tm_mon + 1;
    if (month == 1 || month == 2)
        l = 1;
    int mjd = 14956 + time->tm_mday + (int)((time->tm_year - l) * 365.25) + (int)((month + 1 + l*12) * 30.6001);
    evt->start_time_1 = mjd >> 8;
    evt->start_time_2 = mjd & 0xFF;

    evt->start_time_3 = toBCD(time->tm_hour);
    evt->start_time_4 = toBCD(time->tm_min);
    evt->start_time_5 = toBCD(time->tm_sec);

}

static void fill_eit_duration(eit_event_struct *evt, int time)
{
    //time is given in second
    //convert to hour, minutes, seconds
    evt->duration_1 = toBCD(time / 3600);
    evt->duration_2 = toBCD((time % 3600) / 60);
    evt->duration_3 = toBCD((time % 3600) % 60);
}

static inline uint8_t HI(int x) { return (uint8_t) ((x >> 8) & 0xFF); }
static inline uint8_t LO(int x) { return (uint8_t) (x & 0xFF); }

// convert from set of strings to DVB format (EIT)
void eEPGCache::submitEventData(const std::vector<eServiceReferenceDVB>& serviceRefs, long start,
	long duration, const char* title, const char* short_summary,
	const char* long_description, char event_type)
{
	std::vector<int> sids;
	std::vector<eDVBChannelID> chids;
	for (std::vector<eServiceReferenceDVB>::const_iterator serviceRef = serviceRefs.begin();
		serviceRef != serviceRefs.end();
		++serviceRef)
	{
		eDVBChannelID chid;
		serviceRef->getChannelID(chid);
		chids.push_back(chid);
		sids.push_back(serviceRef->getServiceID().get());

		// disable EIT event parsing when using EPG_IMPORT
		ePtr<eDVBService> service;
		if (!eDVBDB::getInstance()->getService(*serviceRef, service) && service->useEIT())
		{
			service->m_flags |= eDVBService::dxNoEIT;
		}
	}
	submitEventData(sids, chids, start, duration, title, short_summary, long_description, event_type, 0, EPG_IMPORT);
}

void eEPGCache::submitEventData(const std::vector<int>& sids, const std::vector<eDVBChannelID>& chids, long start,
	long duration, const char* title, const char* short_summary,
	const char* long_description, char event_type, int event_id, int source)
{
	if (!title)
		return;
	if (sids.size() != chids.size())
		return;
	static const int EIT_LENGTH = 4108;
	static const uint8_t codePage = 0x15; // UTF-8 encoding
	uint8_t data[EIT_LENGTH];

	eit_t *packet = (eit_t *) data;
	packet->table_id = 0x50;
	packet->section_syntax_indicator = 1;

	packet->version_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->current_next_indicator = 0;
	packet->section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->last_section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment

	packet->segment_last_section_number = 0; // eEPGCache::sectionRead() will dig this for the moment
	packet->segment_last_table_id = 0x50;

	eit_event_t *evt_struct = (eit_event_t*) (data + EIT_SIZE);

	uint16_t eventId = (event_id == 0) ? start & 0xFFFF : event_id;
	evt_struct->setEventId(eventId);

	//6 bytes start time, 3 bytes duration
	fill_eit_start(evt_struct, start);
	fill_eit_duration(evt_struct, duration);

	evt_struct->running_status = 0;
	evt_struct->free_CA_mode = 0;

	//no support for different code pages, only DVB's latin1 character set
	//TODO: convert text to correct character set (data is probably passed in as UTF-8)
	uint8_t *x = (uint8_t *) evt_struct;
	x += EIT_LOOP_SIZE;
	int nameLength = strnlen(title, 246);
	int descLength = short_summary ? strnlen(short_summary, 246 - nameLength) : 0;

	eit_short_event_descriptor_struct *short_evt = (eit_short_event_descriptor_struct*) x;
	short_evt->descriptor_tag = SHORT_EVENT_DESCRIPTOR;
	short_evt->descriptor_length = EIT_SHORT_EVENT_DESCRIPTOR_SIZE + nameLength + descLength + 1 - 2; //+1 for length of short description, -2 for tag and length
	if (nameLength) ++short_evt->descriptor_length; // +1 for codepage byte
	if (descLength) ++short_evt->descriptor_length;
	short_evt->language_code_1 = 'e';
	short_evt->language_code_2 = 'n';
	short_evt->language_code_3 = 'g';
	short_evt->event_name_length = nameLength ? nameLength + 1 : 0;
	x = (uint8_t *) short_evt;
	x += EIT_SHORT_EVENT_DESCRIPTOR_SIZE;
	*x = codePage;
	++x;
	memcpy(x, title, nameLength);
	x += nameLength;
	if (descLength)
	{
		*x = descLength + 1;
		++x;
		*x = codePage;
		++x;
		memcpy(x, short_summary, descLength);
		x += descLength;
	}
	else
	{
		*x = 0;
		++x;
	}

	//Content type
	if (event_type != 0)
	{
		x[0] = 0x54;
		x[1] = 2;
		x[2] = event_type;
		x[3] = 0;
		x += 4;
	}

	//Long description
	int currentLoopLength = x - (uint8_t*)short_evt;
	static const int overheadPerDescriptor = 9; //increase if codepages are added!!!
	static const int MAX_LEN = 256 - overheadPerDescriptor;

	int textLength = long_description ? strnlen(long_description, EIT_LENGTH) : 0;//EIT_LENGTH is a bit too much, but it's only here as a reasonable end point
	int lastDescriptorNumber = (textLength + MAX_LEN-1) / MAX_LEN - 1;
	int remainingTextLength = textLength - lastDescriptorNumber * MAX_LEN;

	//if long description is too long, just try to fill as many descriptors as possible
	while ( (lastDescriptorNumber+1) * 256 + currentLoopLength > EIT_LENGTH - EIT_LOOP_SIZE)
	{
		lastDescriptorNumber--;
		remainingTextLength = MAX_LEN;
	}

	for (int descrIndex = 0; descrIndex <= lastDescriptorNumber; ++descrIndex)
	{
		eit_extended_descriptor_struct *ext_evt = (eit_extended_descriptor_struct*) x;
		ext_evt->descriptor_tag = EIT_EXTENDED_EVENT_DESCRIPOR;
		//descriptor header length is 6, including the 2 tag and length bytes
		//so the length field must be: stringlength + 1 (2 4-bits numbers) + 3 (lang code) + 2 bytes for item info length field and text length field
		int currentTextLength = descrIndex < lastDescriptorNumber ? MAX_LEN : remainingTextLength;
		ext_evt->descriptor_length = 6 + currentTextLength + 1;

		ext_evt->descriptor_number = descrIndex;
		ext_evt->last_descriptor_number = lastDescriptorNumber;
		ext_evt->iso_639_2_language_code_1 = 'e';
		ext_evt->iso_639_2_language_code_2 = 'n';
		ext_evt->iso_639_2_language_code_3 = 'g';

		x[6] = 0; //item information (car, year, director, etc. Unsupported for now)
		x[7] = currentTextLength + 1; //length of description string (part in this message)
		x[8] = codePage;
		memcpy(x + 9, &long_description[descrIndex*MAX_LEN], currentTextLength);

		x += 2 + ext_evt->descriptor_length;
	}

	//TODO: add age and more
	int desc_loop_length = x - ((uint8_t*)evt_struct + EIT_LOOP_SIZE);
	evt_struct->setDescriptorsLoopLength(desc_loop_length);

	int packet_length = (x - data) - 3; //should add 1 for crc....
	packet->setSectionLength(packet_length);
	// Add channelrefs and submit data.
	for (unsigned int i = 0; i < chids.size(); i++)
	{
		packet->setServiceId(sids[i]);
		packet->setTransportStreamId(chids[i].transport_stream_id.get());
		packet->setOriginalNetworkId(chids[i].original_network_id.get());
		sectionRead(data, source, 0);
	}
}

void eEPGCache::setEpgHistorySeconds(time_t seconds)
{
	historySeconds = seconds;
}

void eEPGCache::setEpgSources(unsigned int mask)
{
	m_enabledEpgSources = mask;
}

unsigned int eEPGCache::getEpgSources()
{
	return m_enabledEpgSources;
}

static const char* getStringFromPython(ePyObject obj)
{
	char *result = 0;
	if (PyString_Check(obj))
	{
		result = PyString_AS_STRING(obj);
	}
	return result;
}

void eEPGCache::importEvent(ePyObject serviceReference, ePyObject list)
{
	importEvents(serviceReference, list);
}

//here we get a python tuple of tuples ;)
// consider it an array of objects with the following data
// 1. start time (long)
// 2. duration (int)
// 3. event title (string)
// 4. short description (string)
// 5. extended description (string)
// 6. event type (byte)
void eEPGCache::importEvents(ePyObject serviceReferences, ePyObject list)
{
	std::vector<eServiceReferenceDVB> refs;

	if (PyString_Check(serviceReferences))
	{
		char *refstr;
		refstr = PyString_AS_STRING(serviceReferences);
	        if (!refstr)
	        {
			eDebug("[eEPGCache:import] serviceReference string is 0, aborting");
                	return;
	        }
		refs.push_back(eServiceReferenceDVB(refstr));
	}
	else if (PyList_Check(serviceReferences))
	{
		int nRefs = PyList_Size(serviceReferences);
		for (int i = 0; i < nRefs; ++i)
		{
			PyObject* item = PyList_GET_ITEM(serviceReferences, i);
			char *refstr;
	                refstr = PyString_AS_STRING(item);
	                if (!refstr)
        	        {
				eDebug("[eEPGCache:import] a serviceref item is not a string");
                        }
			else
		        {
		                refs.push_back(eServiceReferenceDVB(refstr));
			}
		}
	}
	else
	{
		eDebug("[eEPGCache:import] serviceReference string is neither string nor list, aborting");
		return;
	}

	bool isTuple = PyTuple_Check(list);
	if (!isTuple && !PyList_Check(list))
	{

		eDebug("[eEPGCache:import] argument 'list' is neither list nor tuple.");
		return;
	}

	int numberOfEvents = isTuple ? PyTuple_Size(list) : PyList_Size(list);

	for (int i = 0; i < numberOfEvents;  ++i)
	{
		ePyObject singleEvent = isTuple ? PyTuple_GET_ITEM(list, i) : PyList_GET_ITEM(list, i);
		if (!PyTuple_Check(singleEvent))
		{
			eDebug("[eEPGCache:import] eventdata tuple does not pass PyTuple_Check, aborting");
			return;
		}
		int tupleSize = PyTuple_Size(singleEvent);
		if (tupleSize < 5)
		{
			eDebug("[eEPGCache:import] eventdata tuple does not contain enough fields, aborting");
			return;
		}

		long start = PyLong_AsLong(PyTuple_GET_ITEM(singleEvent, 0));
		long duration = PyInt_AsLong(PyTuple_GET_ITEM(singleEvent, 1));
		const char *title = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 2));
		const char *short_summary = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 3));
		const char *long_description = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 4));
		char event_type = (char) PyInt_AsLong(PyTuple_GET_ITEM(singleEvent, 5));

		Py_BEGIN_ALLOW_THREADS;
		submitEventData(refs, start, duration, title, short_summary, long_description, event_type);
		Py_END_ALLOW_THREADS;
	}
}


// here we get a python tuple
// the first entry in the tuple is a python string to specify the format of the returned tuples (in a list)
//   I = Event Id
//   B = Event Begin Time
//   D = Event Duration
//   T = Event Title
//   S = Event Short Description
//   P = Event Parental Rating
//   W = Event Content Description
//   E = Event Extended Description
//   R = Service Reference
//   N = Service Name
//   n = Short Service Name
//  the second tuple entry is the MAX matches value
//  the third tuple entry is the type of query
//     0 = search for similar broadcastings (SIMILAR_BROADCASTINGS_SEARCH)
//     1 = search events with exactly title name (EXACT_TITLE_SEARCH)
//     2 = search events with text in title name (PARTIAL_TITLE_SEARCH)
//     3 = search events starting with title name (START_TITLE_SEARCH)
//     4 = search events ending with title name (END_TITLE_SEARCH)
//     5 = search events with text in description (PARTIAL_DESCRIPTION_SEARCH)
//  when type is 0 (SIMILAR_BROADCASTINGS_SEARCH)
//   the fourth is the servicereference string
//   the fifth is the eventid
//  when type > 0 (*_TITLE_SEARCH)
//   the fourth is the search text
//   the fifth is
//     0 = case sensitive (CASE_CHECK)
//     1 = case insensitive (NO_CASECHECK)

PyObject *eEPGCache::search(ePyObject arg)
{
	ePyObject ret;
	std::deque<uint32_t> descr;
	int eventid = -1;
	const char *argstring=0;
	char *refstr=0;
	int argcount=0;
	int querytype=-1;
	bool needServiceEvent=false;
	int maxmatches=0;
	int must_get_service_name = 0;
	bool must_get_service_reference = false;

	if (PyTuple_Check(arg))
	{
		int tuplesize=PyTuple_Size(arg);
		if (tuplesize > 0)
		{
			ePyObject obj = PyTuple_GET_ITEM(arg,0);
			if (PyString_Check(obj))
			{
#if PY_VERSION_HEX < 0x02060000
				argcount = PyString_GET_SIZE(obj);
#else
				argcount = PyString_Size(obj);
#endif
				argstring = PyString_AS_STRING(obj);
				for (int i=0; i < argcount; ++i)
					switch(argstring[i])
					{
					case 'S':
					case 'E':
					case 'T':
					case 'P':
					case 'W':
						needServiceEvent=true;
						break;
					case 'N':
						must_get_service_name = 1;
						break;
					case 'n':
						must_get_service_name = 2;
						break;
					case 'R':
						must_get_service_reference = true;
						break;
					default:
						break;
					}
			}
			else
			{
				PyErr_SetString(PyExc_StandardError,
					"type error");
				eDebug("[eEPGCache] tuple arg 0 is not a string");
				return NULL;
			}
		}
		if (tuplesize > 1)
			maxmatches = PyLong_AsLong(PyTuple_GET_ITEM(arg, 1));
		if (tuplesize > 2)
		{
			querytype = PyLong_AsLong(PyTuple_GET_ITEM(arg, 2));
			if (tuplesize > 4 && querytype == 0)
			{
				ePyObject obj = PyTuple_GET_ITEM(arg, 3);
				if (PyString_Check(obj))
				{
					refstr = PyString_AS_STRING(obj);
					eServiceReferenceDVB ref(refstr);
					if (ref.valid())
					{
						eventid = PyLong_AsLong(PyTuple_GET_ITEM(arg, 4));
						singleLock s(cache_lock);
						const eventData *evData = 0;
						lookupEventId(ref, eventid, evData);
						if (evData)
						{
							// search short and extended event descriptors
							for (uint8_t i = 0; i < evData->n_crc; ++i)
							{
								uint32_t crc = evData->crc_list[i];
								DescriptorMap::iterator it =
									eventData::descriptors.find(crc);
								if (it != eventData::descriptors.end())
								{
									uint8_t *descr_data = it->second.data;
									switch(descr_data[0])
									{
									case 0x4D ... 0x4E:
										descr.push_back(crc);
										break;
									default:
										break;
									}
								}
							}
						}
						if (descr.empty())
							eDebug("[eEPGCache] event not found");
					}
					else
					{
						PyErr_SetString(PyExc_StandardError, "type error");
						eDebug("[eEPGCache] tuple arg 4 is not a valid service reference string");
						return NULL;
					}
				}
				else
				{
					PyErr_SetString(PyExc_StandardError, "type error");
					eDebug("[eEPGCache] tuple arg 4 is not a string");
					return NULL;
				}
			}
			else if (tuplesize > 4 && (querytype > 0) )
			{
				ePyObject obj = PyTuple_GET_ITEM(arg, 3);
				if (PyString_Check(obj))
				{
					int casetype = PyLong_AsLong(PyTuple_GET_ITEM(arg, 4));
					const char *str = PyString_AS_STRING(obj);
#if PY_VERSION_HEX < 0x02060000
					int strlen = PyString_GET_SIZE(obj);
#else
					int strlen = PyString_Size(obj);
#endif
					switch (querytype)
					{
						case 1:
							eDebug("[eEPGCache] lookup events with '%s' as title (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 2:
							eDebug("[eEPGCache] lookup events with '%s' in title (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 3:
							eDebug("[eEPGCache] lookup events, title starting with '%s' (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 4:
							eDebug("[eEPGCache] lookup events, title ending with '%s' (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 5:
							eDebug("[eEPGCache] lookup events with '%s' in the description (%s)", str, casetype?"ignore case":"case sensitive");
							break;
					}
					Py_BEGIN_ALLOW_THREADS; /* No Python code in this section, so other threads can run */
					{
						/* new block to release epgcache lock before Py_END_ALLOW_THREADS is called
						   otherwise there might be a deadlock with other python thread waiting for the epgcache lock */
						singleLock s(cache_lock);
						std::string text;
						for (DescriptorMap::iterator it(eventData::descriptors.begin());
							it != eventData::descriptors.end(); ++it)
						{
							uint8_t *data = it->second.data;
							int textlen = 0;
							const char *textptr = NULL;
							if ( data[0] == 0x4D && querytype > 0 && querytype < 5 ) // short event descriptor
							{
								textptr = (const char*)&data[6];
								textlen = data[5];
								if (data[6] < 0x20)
								{
									/* custom encoding */
									text = convertDVBUTF8((unsigned char*)textptr, textlen, 0x40, 0);
									textptr = text.data();
									textlen = text.length();
								}
							}
							else if ( data[0] == 0x4E && querytype == 5 ) // extended event descriptor
							{
								textptr = (const char*)&data[8];
								textlen = data[7];
								if (data[8] < 0x20)
								{
									/* custom encoding */
									text = convertDVBUTF8((unsigned char*)textptr, textlen, 0x40, 0);
									textptr = text.data();
									textlen = text.length();
								}
							}
							/* if we have a descriptor, the argument may not be bigger */
							if (textlen > 0 && strlen <= textlen )
							{
								if (querytype == 1)
								{
									/* require exact text match */
									if (textlen != strlen)
										continue;
								}
								else if (querytype == 3)
								{
									/* Do a "startswith" match by pretending the text isn't that long */
									textlen = strlen;
								}
								else if (querytype == 4)
								{
									/* Offset to adjust the pointer based on the text length difference */
									textptr = textptr + textlen - strlen;
									textlen = strlen;
								}
								if (casetype)
								{
									while (textlen >= strlen)
									{
										if (!strncasecmp(textptr, str, strlen))
										{
											descr.push_back(it->first);
											break;
										}
										textlen--;
										textptr++;
									}
								}
								else
								{
									while (textlen >= strlen)
									{
										if (!memcmp(textptr, str, strlen))
										{
											descr.push_back(it->first);
											break;
										}
										textlen--;
										textptr++;
									}
								}
							}
						}
					}
					Py_END_ALLOW_THREADS;
				}
				else
				{
					PyErr_SetString(PyExc_StandardError,
						"type error");
					eDebug("[eEPGCache] tuple arg 4 is not a string");
					return NULL;
				}
			}
			else
			{
				PyErr_SetString(PyExc_StandardError,
					"type error");
				eDebug("[eEPGCache] tuple arg 3(%d) is not a known querytype(0..3)", querytype);
				return NULL;
			}
		}
		else
		{
			PyErr_SetString(PyExc_StandardError,
				"type error");
			eDebug("[eEPGCache] not enough args in tuple");
			return NULL;
		}
	}
	else
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
		eDebug("[eEPGCache] arg 0 is not a tuple");
		return NULL;
	}

	if (!descr.empty())
	{
		int maxcount=maxmatches;
		eServiceReferenceDVB ref(refstr?(const eServiceReferenceDVB&)handleGroup(eServiceReference(refstr)):eServiceReferenceDVB(""));
		// ref is only valid in SIMILAR_BROADCASTING_SEARCH
		// in this case we start searching with the base service
		bool first = ref.valid() ? true : false;
		singleLock s(cache_lock);
		eventCache::iterator cit(ref.valid() ? eventDB.find(ref) : eventDB.begin());
		while(cit != eventDB.end() && maxcount)
		{
			if ( ref.valid() && !first && cit->first == ref )
			{
				// do not scan base service twice ( only in SIMILAR BROADCASTING SEARCH )
				++cit;
				continue;
			}
			timeMap &evmap = cit->second.byTime;
			// check all events
			for (timeMap::iterator evit(evmap.begin()); evit != evmap.end() && maxcount; ++evit)
			{
				if (querytype == 0)
				{
					/* ignore the current event, when looking for similar events */
					if (evit->second->getEventID() == eventid)
						continue;
				}
				// check if any of our descriptor used by this event
				unsigned int cnt = 0;
				for (uint8_t i = 0; i < evit->second->n_crc; ++i)
				{
					uint32_t crc32 = evit->second->crc_list[i];
					for (std::deque<uint32_t>::const_iterator it = descr.begin();
						it != descr.end(); ++it)
					{
						if (*it == crc32)  // found...
						{
							++cnt;
							if (querytype)
							{
								/* we need only one match, when we're not looking for similar broadcasting events */
								i = evit->second->n_crc;
								break;
							}
						}
					}
				}
				if ( (querytype == 0 && cnt == descr.size()) ||
					 ((querytype > 0) && cnt != 0) )
				{
					const uniqueEPGKey &service = cit->first;
					std::vector<eServiceReference> refs;
					eDVBDB::getInstance()->searchAllReferences(refs, service.tsid, service.onid, service.sid);
					for (unsigned int i = 0; i < refs.size(); i++)
					{
						eServiceReference ref = refs[i];
						if (ref.valid())
						{
							ePyObject service_name;
							ePyObject service_reference;
						// create servive event
							eServiceEvent ptr;
							const eventData *ev_data=0;
							if (needServiceEvent)
							{
								if (lookupEventId(ref, evit->second->getEventID(), ev_data))
									eDebug("[eEPGCache] event not found !!!!!!!!!!!");
								else
								{
									const eServiceReferenceDVB &dref = (const eServiceReferenceDVB&)ref;
									Event ev((uint8_t*)ev_data->get());
									ptr.parseFrom(&ev, (dref.getTransportStreamID().get()<<16)|dref.getOriginalNetworkID().get());
								}
							}
						// create service name
							if (must_get_service_name && !service_name)
							{
								ePtr<iStaticServiceInformation> sptr;
								eServiceCenterPtr service_center;
								eServiceCenter::getPrivInstance(service_center);
								if (service_center)
								{
									service_center->info(ref, sptr);
									if (sptr)
									{
										std::string name;
										sptr->getName(ref, name);

										if (must_get_service_name == 1)
										{
											size_t pos;
											// filter short name brakets
											while((pos = name.find("\xc2\x86")) != std::string::npos)
												name.erase(pos,2);
											while((pos = name.find("\xc2\x87")) != std::string::npos)
												name.erase(pos,2);
										}
										else
											name = buildShortName(name);

										if (name.length())
											service_name = PyString_FromString(name.c_str());
									}
								}
								if (!service_name)
									service_name = PyString_FromString("<n/a>");
							}
						// create servicereference string
							if (must_get_service_reference && !service_reference)
								service_reference = PyString_FromString(ref.toString().c_str());
						// create list
							if (!ret)
								ret = PyList_New(0);
						// create tuple
							ePyObject tuple = PyTuple_New(argcount);
						// fill tuple
							ePyObject tmp = ePyObject();
							fillTuple(tuple, argstring, argcount, service_reference, ev_data ? &ptr : 0, service_name, tmp, evit->second);
							PyList_Append(ret, tuple);
							Py_DECREF(tuple);
							if (service_name)
								Py_DECREF(service_name);
							if (service_reference)
								Py_DECREF(service_reference);
							--maxcount;
						}
					}
				}
			}
			if (first)
			{
				// now start at first service in epgcache database ( only in SIMILAR BROADCASTING SEARCH )
				first=false;
				cit=eventDB.begin();
			}
			else
				++cit;
		}
	}

	if (!ret)
		Py_RETURN_NONE;

	return ret;
}

#ifdef ENABLE_PRIVATE_EPG
struct date_time
{
	uint8_t data[5];
	time_t tm;
	date_time( const date_time &a )
	{
		memcpy(data, a.data, 5);
		tm = a.tm;
	}
	date_time( const uint8_t data[5])
	{
		memcpy(this->data, data, 5);
		tm = parseDVBtime(data);
	}
	date_time()
	{
	}
	const uint8_t& operator[](int pos) const
	{
		return data[pos];
	}
};

struct less_datetime
{
	bool operator()( const date_time &a, const date_time &b ) const
	{
		return abs(a.tm-b.tm) < 360 ? false : a.tm < b.tm;
	}
};

void eEPGCache::privateSectionRead(const uniqueEPGKey &current_service, const uint8_t *data)
{
	contentMap &content_time_table = content_time_tables[current_service];
	singleLock s(cache_lock);
	std::map< date_time, std::list<uniqueEPGKey>, less_datetime > start_times;
	EventCacheItem &eventDBitem = eventDB[current_service];
	eventMap &evMap = eventDBitem.byEvent;
	timeMap &tmMap = eventDBitem.byTime;
	int ptr = 8;
	int content_id = data[ptr++] << 24;
	content_id |= data[ptr++] << 16;
	content_id |= data[ptr++] << 8;
	content_id |= data[ptr++];

	contentTimeMap &time_event_map =
		content_time_table[content_id];
	for ( contentTimeMap::iterator it( time_event_map.begin() );
		it != time_event_map.end(); ++it )
	{
		eventMap::iterator evIt( evMap.find(it->second.second) );
		if ( evIt != evMap.end() )
		{
			// time_event_map can have other timestamp -> get timestamp from eventData
			time_t ev_time = evIt->second->getStartTime();
			delete evIt->second;
			evMap.erase(evIt);
			tmMap.erase(ev_time);
		}
	}
	time_event_map.clear();

	uint8_t duration[3];
	memcpy(duration, data+ptr, 3);
	ptr+=3;
	int duration_sec =
		fromBCD(duration[0])*3600+fromBCD(duration[1])*60+fromBCD(duration[2]);

	const uint8_t *descriptors[65];
	const uint8_t **pdescr = descriptors;

	int descriptors_length = (data[ptr++]&0x0F) << 8;
	descriptors_length |= data[ptr++];
	while ( descriptors_length > 1 )
	{
		int descr_type = data[ptr];
		int descr_len = data[ptr+1];
		descriptors_length -= 2;
		if (descriptors_length >= descr_len)
		{
			descriptors_length -= descr_len;
			if ( descr_type == 0xf2 && descr_len > 5)
			{
				ptr+=2;
				int tsid = data[ptr++] << 8;
				tsid |= data[ptr++];
				int onid = data[ptr++] << 8;
				onid |= data[ptr++];
				int sid = data[ptr++] << 8;
				sid |= data[ptr++];

// WORKAROUND for wrong transmitted epg data (01.10.2007)
				if ( onid == 0x85 )
				{
					switch( (tsid << 16) | sid )
					{
						case 0x01030b: sid = 0x1b; tsid = 4; break;  // Premiere Win
						case 0x0300f0: sid = 0xe0; tsid = 2; break;
						case 0x0300f1: sid = 0xe1; tsid = 2; break;
						case 0x0300f5: sid = 0xdc; break;
						case 0x0400d2: sid = 0xe2; tsid = 0x11; break;
						case 0x1100d3: sid = 0xe3; break;
						case 0x0100d4: sid = 0xe4; tsid = 4; break;
					}
				}
////////////////////////////////////////////

				uniqueEPGKey service( sid, onid, tsid );
				descr_len -= 6;
				while( descr_len > 2 )
				{
					uint8_t datetime[5];
					datetime[0] = data[ptr++];
					datetime[1] = data[ptr++];
					int tmp_len = data[ptr++];
					descr_len -= 3;
					if (descr_len >= tmp_len)
					{
						descr_len -= tmp_len;
						while( tmp_len > 2 )
						{
							memcpy(datetime+2, data+ptr, 3);
							ptr += 3;
							tmp_len -= 3;
							start_times[datetime].push_back(service);
						}
					}
				}
			}
			else
			{
				*pdescr++=data+ptr;
				ptr += 2;
				ptr += descr_len;
			}
		}
	}
	ASSERT(pdescr <= &descriptors[65]);
	uint8_t event[4098];
	eit_event_struct *ev_struct = (eit_event_struct*) event;
	ev_struct->running_status = 0;
	ev_struct->free_CA_mode = 1;
	memcpy(event+7, duration, 3);
	ptr = 12;
	const uint8_t **d=descriptors;
	while ( d < pdescr )
	{
		memcpy(event+ptr, *d, ((*d)[1])+2);
		ptr+=(*d++)[1];
		ptr+=2;
	}
	ASSERT(ptr <= 4098);
	for ( std::map< date_time, std::list<uniqueEPGKey> >::iterator it(start_times.begin()); it != start_times.end(); ++it )
	{
		time_t now = ::time(0);
		if ( (it->first.tm + duration_sec) < now )
			continue;
		memcpy(event+2, it->first.data, 5);
		int bptr = ptr;
		int cnt=0;
		for (std::list<uniqueEPGKey>::iterator i(it->second.begin()); i != it->second.end(); ++i)
		{
			event[bptr++] = 0x4A;
			uint8_t *len = event+(bptr++);
			event[bptr++] = (i->tsid & 0xFF00) >> 8;
			event[bptr++] = (i->tsid & 0xFF);
			event[bptr++] = (i->onid & 0xFF00) >> 8;
			event[bptr++] = (i->onid & 0xFF);
			event[bptr++] = (i->sid & 0xFF00) >> 8;
			event[bptr++] = (i->sid & 0xFF);
			event[bptr++] = 0xB0;
			bptr += sprintf((char*)(event+bptr), "Option %d", ++cnt);
			*len = ((event+bptr) - len)-1;
		}
		int llen = bptr - 12;
		ev_struct->descriptors_loop_length_hi = (llen & 0xF00) >> 8;
		ev_struct->descriptors_loop_length_lo = (llen & 0xFF);

		time_t stime = it->first.tm;
		while( tmMap.find(stime) != tmMap.end() )
			++stime;
		event[6] += (stime - it->first.tm);
		uint16_t event_id = 0;
		while( evMap.find(event_id) != evMap.end() )
			++event_id;
		event[0] = (event_id & 0xFF00) >> 8;
		event[1] = (event_id & 0xFF);
		time_event_map[it->first.tm]=std::pair<time_t, uint16_t>(stime, event_id);
		eventData *d = new eventData( ev_struct, bptr, eEPGCache::PRIVATE );
		evMap[event_id] = d;
		tmMap[stime] = d;
		ASSERT(bptr <= 4098);
	}
}
#endif
