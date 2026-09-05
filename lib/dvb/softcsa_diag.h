#ifndef __softcsa_diag_h
#define __softcsa_diag_h

#include <atomic>

struct SoftCsaDiag {
	static std::atomic<int> pmtClientsAlive;
	static std::atomic<int> csaSessionsAlive;
	static std::atomic<int> cwConnectionsAlive;
};

void softcsaMemDiagDump();   // schreibt eine Zeile in Log + Datei
void softcsaMemDiagStart();  // hängt den periodischen Timer ein

#endif
