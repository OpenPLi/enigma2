#include "softcsa_diag.h"
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <cstdio>
#include <malloc.h>

std::atomic<int> SoftCsaDiag::pmtClientsAlive{0};
std::atomic<int> SoftCsaDiag::csaSessionsAlive{0};
std::atomic<int> SoftCsaDiag::cwConnectionsAlive{0};

// diese drei Getter je einmal am Ende von cahandler.cpp / csasession.cpp ergänzen:
extern size_t getCsaCacheSize();       // return s_csa_cache.size();
extern size_t getServiceIdCacheSize(); // return s_serviceId_cache.size();
extern size_t getPmtCacheSize();       // return eDVBCAHandler-Instanz->pmtCache.size();

static long getRssKb()
{
	long rss_kb = 0;
	FILE *f = fopen("/proc/self/status", "r");
	if (f) {
	char line[256];
	while (fgets(line, sizeof(line), f))
	    if (!strncmp(line, "VmRSS:", 6)) { sscanf(line + 6, "%ld", &rss_kb); break; }
	fclose(f);
	}
	return rss_kb;
}

void softcsaMemDiagDump()
{
	struct mallinfo2 mi = mallinfo2();
	long rss = getRssKb();

	char buf[512];
	snprintf(buf, sizeof(buf),
	"[SoftCSA-Mem] t=%ld rss=%ldkB arena_used=%zukB arena_free=%zukB mmap=%zukB "
	"pmtClients=%d csaSessions=%d cwConn=%d csaCache=%zu svcIdCache=%zu pmtCache=%zu\n",
	(long)time(0), rss, mi.uordblks / 1024, mi.fordblks / 1024, mi.hblkhd / 1024,
	SoftCsaDiag::pmtClientsAlive.load(), SoftCsaDiag::csaSessionsAlive.load(),
	SoftCsaDiag::cwConnectionsAlive.load(),
	getCsaCacheSize(), getServiceIdCacheSize(), getPmtCacheSize());

	eDebug("%s", buf);

	// zusätzlich persistent wegschreiben, gleiche Fallback-Kette wie bsodFatal()
	static std::string path;
	if (path.empty())
	{
	if (access("/media/hdd", W_OK) == 0)      path = "/media/hdd/softcsa_mem.log";
	else if (access("/home/root", W_OK) == 0) path = "/home/root/softcsa_mem.log";
	else                                       path = "/tmp/softcsa_mem.log";
	}
	FILE *f = fopen(path.c_str(), "a");
	if (f) { fputs(buf, f); fclose(f); }
}

static ePtr<eTimer> s_memDiagTimer;

void softcsaMemDiagStart()
{
    s_memDiagTimer = eTimer::create(eApp);
    s_memDiagTimer->timeout.connect(sigc::ptr_fun(&softcsaMemDiagDump));
    s_memDiagTimer->start(15 * 60 * 1000, false); // alle 15 Min, wiederholend
    softcsaMemDiagDump(); // gleich einen ersten Datenpunkt beim Start
}
