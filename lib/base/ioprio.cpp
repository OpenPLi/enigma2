#include <lib/base/ioprio.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>
#include <sys/syscall.h>

#include <lib/base/eerror.h>

static inline int ioprio_set(int which, int who, int ioprio)
{
	return syscall(SYS_ioprio_set, which, who, ioprio);
}

static inline int ioprio_get(int which, int who)
{
	return syscall(SYS_ioprio_get, which, who);
}

#define IOPRIO_CLASS_SHIFT	13

enum {
	IOPRIO_WHO_PROCESS = 1,
	IOPRIO_WHO_PGRP,
	IOPRIO_WHO_USER,
};

const char *to_prio[] = { "none", "realtime", "best-effort", "idle", };

void setIoPrio(int prio_class, int prio)
{
	if (prio_class < 0 || prio_class > 3)
	{
		eDebug("[setIoPrio] class(%d) out of valid range (0..3)", prio_class);
		return;
	}
	if (prio < 0 || prio > 7)
	{
		eDebug("[setIoPrio] level(%d) out of range (0..7)", prio);
		return;
	}
	if (ioprio_set(IOPRIO_WHO_PROCESS, 0 /*pid 0 .. current process*/, prio | prio_class << IOPRIO_CLASS_SHIFT) == -1)
		eDebug("[setIoPrio] failed: %m");
	else
		eDebug("[setIoPrio] %s level %d ok", to_prio[prio_class], prio);
}

void printIoPrio()
{
	int pid = 0, ioprio = ioprio_get(IOPRIO_WHO_PROCESS, pid);

	eDebug("[printIoPrio] pid=%d, %d", pid, ioprio);

	if (ioprio == -1)
		eDebug("[printIoPrio] ioprio_get(%m)");
	else {
		int ioprio_class = ioprio >> IOPRIO_CLASS_SHIFT;
		ioprio = ioprio & 0xff;
		eDebug("[printIoPrio] %s: prio %d", to_prio[ioprio_class], ioprio);
	}
}
