#include "filepush.h"
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <poll.h>

//#define SHOW_WRITE_TIME

DEFINE_REF(eFilePushThread);

eFilePushThread::eFilePushThread(int blocksize, size_t buffersize, int flags):
	 m_sg(NULL),
	 m_stop(1),
	 m_send_pvr_commit(0),
	 m_stream_mode(0),
	 m_flags(flags),
	 m_blocksize(blocksize),
	 m_buffersize(buffersize),
	 m_buffer((unsigned char *)malloc(buffersize)),
	 m_messagepump(eApp, 0),
	 m_run_state(0)
{
	if (m_buffer == NULL)
		eFatal("[eFilePushThread] Failed to allocate %zu bytes", buffersize);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
}

eFilePushThread::~eFilePushThread()
{
	stop(); /* eThread is borked, always call stop() from d'tor */
	free(m_buffer);
}

static void signal_handler(int x)
{
}

static void ignore_but_report_signals()
{
#ifndef HAVE_HISILICON
	/* we must set a signal mask for the thread otherwise signals don't have any effect */
	sigset_t sigmask;
	sigemptyset(&sigmask);
	sigaddset(&sigmask, SIGUSR1);
	pthread_sigmask(SIG_UNBLOCK, &sigmask, NULL);
#endif

	/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act = {};
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
}

void eFilePushThread::thread()
{
	ignore_but_report_signals();
	hasStarted(); /* "start()" blocks until we get here */
	eDebug("[eFilePushThread] START thread");

	do
	{
		int eofcount = 0;
		int buf_end = 0;
		int poll_timeout_count = 0;
		size_t bytes_read = 0;
		off_t current_span_offset = 0;
		size_t current_span_remaining = 0;
		m_sof = 0;

		while (!m_stop)
		{
			// eTrace("[FilePushThread][DATA] Pumping data at pos=%lld", (long long)m_current_position);
			if (m_sg && !current_span_remaining)
			{
				m_sg->getNextSourceSpan(m_current_position, bytes_read, current_span_offset, current_span_remaining, m_blocksize, m_sof);
				ASSERT(!(current_span_remaining % m_blocksize));
				m_current_position = current_span_offset;
				bytes_read = 0;
			}

			size_t maxread = m_buffersize;

			/* if we have a source span, don't read past the end */
			if (m_sg && maxread > current_span_remaining)
				maxread = current_span_remaining;

			/* align to blocksize */
			maxread -= maxread % m_blocksize;

			if (maxread && !m_sof)
			{
#ifdef SHOW_WRITE_TIME
				struct timeval starttime = {};
				struct timeval now = {};
				gettimeofday(&starttime, NULL);
#endif
				buf_end = m_source->read(m_current_position, m_buffer, maxread);
#ifdef SHOW_WRITE_TIME
				gettimeofday(&now, NULL);
				suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
				eDebug("[eFilePushThread] read %d bytes time: %9u us", buf_end, (unsigned int)diff);
#endif
			}
			else
				buf_end = 0;

			if (buf_end < 0)
			{
				buf_end = 0;
				/* Check m_stop after interrupted syscall. */
				if (m_stop)
				{
					break;
				}
				if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
					continue;
				if (errno == EOVERFLOW)
				{
					eWarning("[eFilePushThread] OVERFLOW while playback?");
					continue;
				}
				eDebug("[eFilePushThread] read error: %m");
			}

			/* a read might be mis-aligned in case of a short read. */
			int d = buf_end % m_blocksize;
			if (d)
				buf_end -= d;

			if (buf_end == 0 || m_sof == 1)
			{
				/* on EOF, try COMMITting once. */
				if (m_send_pvr_commit)
				{
					struct pollfd pfd = {};
					pfd.fd = m_fd_dest;
					pfd.events = POLLIN;
					switch (poll(&pfd, 1, 250)) // wait for 250ms
					{
					case 0:
						if ((++poll_timeout_count % 20) == 0)
							eDebug("[eFilePushThread] wait for driver eof timeout - %ds", poll_timeout_count / 4);
						continue;
					case 1:
						eDebug("[eFilePushThread] wait for driver eof ok / m_flags %d" , m_flags);
						break;
					default:
						eDebug("[eFilePushThread] wait for driver eof aborted by signal");
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
							break;
						continue;
					}
				}
				else
					poll_timeout_count = 0;

				if (m_stop)
					break;

				/* in stream_mode, we are sending EOF events
				   over and over until somebody responds.

				   in stream_mode, think of evtEOF as "buffer underrun occurred". */
				if (m_sof == 0)
					sendEvent(evtEOF);
				else
					sendEvent(evtUser); // start of file event

				if (m_stream_mode) {
					eDebug("[eFilePushThread] reached EOF, but we are in stream mode. delaying 1 second.");
					sleep(1);
					continue;
				}
				else if (m_flags == 1) { // timeshift
					usleep(200000);  // 200 milliseconds
					continue;
				}
				else if (++eofcount < 10)
				{
					eDebug("[eFilePushThread] reached EOF, but the file may grow. delaying 1 second.");
					sleep(1);
					continue;
				}
				break;
			}
			else
			{
				/* Write data to mux */
				int buf_start = 0;
				filterRecordData(m_buffer, buf_end);
				while ((buf_start != buf_end) && !m_stop)
				{
					int w = write(m_fd_dest, m_buffer + buf_start, buf_end - buf_start);

					if (w <= 0)
					{
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
						{
							w = 0;
							buf_start = 0;
							buf_end = 0;
							break;
						}
						if (w < 0 && (errno == EINTR || errno == EAGAIN || errno == EBUSY))
						{
#if HAVE_HISILICON
							usleep(100000);
#endif
							continue;
						}
						eDebug("[eFilePushThread] write: %m");
						sendEvent(evtWriteError);
						break;
					}
					buf_start += w;
				}

				eofcount = 0;
				m_current_position += buf_end;
				bytes_read += buf_end;
				if (m_sg)
					current_span_remaining -= buf_end;
			}
		}
		sendEvent(evtStopped);

		{ /* mutex lock scope */
			eSingleLocker lock(m_run_mutex);
			m_run_state = 0;
			m_run_cond.signal(); /* Tell them we're here */
			while (m_stop == 2)
			{
				eDebug("[eFilePushThread] PAUSED");
				m_run_cond.wait(m_run_mutex);
			}
			if (m_stop == 0)
				m_run_state = 1;
		}

	} while (m_stop == 0);
	eDebug("[eFilePushThread] STOP");
}

void eFilePushThread::start(ePtr<iTsSource> &source, int fd_dest)
{
	m_source = source;
	m_fd_dest = fd_dest;
	m_current_position = 0;
	m_run_state = 1;
	m_stop = 0;
	run();
}

void eFilePushThread::stop()
{
	/* if we aren't running, don't bother stopping. */
	if (m_stop == 1)
		return;
	m_stop = 1;
	eDebug("[eFilePushThread] stopping thread");
	m_run_cond.signal(); /* Break out of pause if needed */
	sendSignal(SIGUSR1);
	kill(); /* Kill means join actually */
}

void eFilePushThread::pause()
{
	if (m_stop == 1)
	{
		eWarning("[eFilePushThread] pause called while not running");
		return;
	}
	/* Set thread into a paused state by setting m_stop to 2 and wait
	 * for the thread to acknowledge that */
	eSingleLocker lock(m_run_mutex);
	m_stop = 2;
	sendSignal(SIGUSR1);
	m_run_cond.signal(); /* Trigger if in weird state */
	while (m_run_state)
	{
		eDebug("[eFilePushThread] waiting for pause");
		m_run_cond.wait(m_run_mutex);
	}
}

void eFilePushThread::resume()
{
	if (m_stop != 2)
	{
		eWarning("[eFilePushThread] resume called while not paused");
		return;
	}
	/* Resume the paused thread by resetting the flag and
	 * signal the thread to release it */
	eSingleLocker lock(m_run_mutex);
	m_stop = 0;
	m_run_cond.signal(); /* Tell we're ready to resume */
}

void eFilePushThread::enablePVRCommit(int s)
{
	m_send_pvr_commit = s;
}

void eFilePushThread::setStreamMode(int s)
{
	m_stream_mode = s;
}

void eFilePushThread::setScatterGather(iFilePushScatterGather *sg)
{
	m_sg = sg;
}

void eFilePushThread::sendEvent(int evt)
{
	/* add a ref, to make sure the object is not destroyed while the messagepump contains unhandled messages */
	AddRef();
	m_messagepump.send(evt);
}

void eFilePushThread::recvEvent(const int &evt)
{
	m_event(evt);
	/* release the ref which we grabbed in sendEvent() */
	Release();
}

void eFilePushThread::filterRecordData(const unsigned char *data, int len)
{
}




eFilePushThreadRecorder::eFilePushThreadRecorder(unsigned char* buffer, size_t buffersize):
	m_fd_source(-1),
	m_buffersize(buffersize),
	m_buffer(buffer),
	m_overflow_count(0),
	m_stop(1),
	m_buffer_fill(0),
	m_buffer_min_write(0),
	m_messagepump(eApp, 0)
{
	CONNECT(m_messagepump.recv_msg, eFilePushThreadRecorder::recvEvent);

	/* Ensure min_write doesn't exceed buffer size */
	if (m_buffer_min_write > m_buffersize)
		m_buffer_min_write = m_buffersize;
}

void eFilePushThreadRecorder::thread()
{
#ifndef HAVE_HISILICON
	ignore_but_report_signals();
	hasStarted(); /* "start()" blocks until we get here */
#endif
	eDebug("[eFilePushThreadRecorder] THREAD START (min_write=%zu KB, buffersize=%zu KB)", m_buffer_min_write >> 10, m_buffersize >> 10);

#ifdef HAVE_HISILICON
	/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act = {};
	memset(&act, 0, sizeof(act));
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	hasStarted();
#endif


	m_buffer_fill = 0;

	/* m_stop must be evaluated after each syscall */
	/* if it isn't, there's a chance of the thread becoming deadlocked when recordings are finishing */
	while (!m_stop)
	{
		ssize_t bytes;
		{
		/* this works around the buggy Broadcom encoder that always returns even if there is no data */
		/* (works like O_NONBLOCK even when not opened as such), prevent idle waiting for the data */
		/* this won't ever hurt, because it will return immediately when there is data or an error condition */
		/* All platforms now use poll() - this replaces the HiSilicon-specific usleep(100000) */

		struct pollfd pfd = { m_fd_source, POLLIN, 0 };
		int poll_ret = poll(&pfd, 1, 100);
		/* Reminder: m_stop *must* be evaluated after each syscall. */
		if (m_stop)
			break;

		if (poll_ret == 0)
		{
			/* Timeout - flush accumulated data if any */
			if (m_buffer_fill > 0)
			{
				int w = writeData(m_buffer_fill);
				if (w < 0)
				{
					eDebug("[eFilePushThreadRecorder] WRITE ERROR on timeout flush: %m");
					sendEvent(evtWriteError);
					break;
				}
				m_buffer_fill = 0;
			}
			continue;
		}

		if (poll_ret < 0)
		{
			if (errno == EINTR)
				continue;
			eDebug("[eFilePushThreadRecorder] poll error: %m");
			break;
		}

		/* Read into buffer at current fill position */
		bytes = ::read(m_fd_source, m_buffer + m_buffer_fill, m_buffersize - m_buffer_fill);
		/* And again: Check m_stop regardless of read success. */
		if (m_stop)
			break;
		}

		if (bytes < 0)
		{
			bytes = 0;
			if (m_stop)
				break;
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
			{
				/* No data available - flush what we have if any */
				if (m_buffer_fill > 0)
				{
					int w = writeData(m_buffer_fill);
					if (w < 0)
					{
						eDebug("[eFilePushThreadRecorder] WRITE ERROR on EAGAIN flush: %m");
						sendEvent(evtWriteError);
						break;
					}
					m_buffer_fill = 0;
				}
				continue;
			}
			if (errno == EOVERFLOW)
			{
				eWarning("[eFilePushThreadRecorder] OVERFLOW while recording");
				++m_overflow_count;
				continue;
			}
			eDebug("[eFilePushThreadRecorder] *read error* (%m) - aborting thread because i don't know what else to do.");
			sendEvent(evtReadError);
			break;
		}

		/* Accumulate data */
		m_buffer_fill += bytes;

		/* Check if we have enough data to write */
		if (m_buffer_fill >= m_buffer_min_write || m_buffer_fill >= m_buffersize)
		{
#ifdef SHOW_WRITE_TIME
			struct timeval starttime = {};
			struct timeval now = {};
			gettimeofday(&starttime, NULL);
#endif
			int w = writeData(m_buffer_fill);
#ifdef SHOW_WRITE_TIME
			gettimeofday(&now, NULL);
			suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
			eDebug("[eFilePushThreadRecorder] write %zu bytes time: %9u us", m_buffer_fill, (unsigned int)diff);
#endif
			if (w < 0)
			{
				eDebug("[eFilePushThreadRecorder] WRITE ERROR, aborting thread: %m");
				sendEvent(evtWriteError);
				break;
			}
			if (w == 0)
			{
				/* writeData returned 0 (destination not ready / poll timeout) */
				/* Keep data in buffer and retry on next iteration */
				usleep(1000);
			}
			else
			{
				/* Write successful, clear buffer */
				m_buffer_fill = 0;
			}
		}
	}

	/* Flush remaining data */
	if (m_buffer_fill > 0)
	{
		writeData(m_buffer_fill);
		m_buffer_fill = 0;
	}

	flush();
	sendEvent(evtStopped);
	eDebug("[eFilePushThreadRecorder] THREAD STOP");
}

void eFilePushThreadRecorder::start(int fd)
{
	m_fd_source = fd;
	m_stop = 0;
	run();
}

void eFilePushThreadRecorder::stop()
{
	/* if we aren't running, don't bother stopping. */
	if (m_stop == 1)
		return;
	m_stop = 1;
	eDebug("[eFilePushThreadRecorder] stopping thread."); /* just do it ONCE. it won't help to do this more than once. */
	sendSignal(SIGUSR1);
	kill();
}

void eFilePushThreadRecorder::sendEvent(int evt)
{
	m_messagepump.send(evt);
}

void eFilePushThreadRecorder::recvEvent(const int &evt)
{
	m_event(evt);
}
