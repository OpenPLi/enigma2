#include "filepush.h"
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <poll.h>
#include <signal.h>

//#define SHOW_WRITE_TIME

DEFINE_REF(eFilePushThread);

static void global_signal_SIGUSR1_handler(int x)
{
	eDebug("signal SIGUSR1 caught");
}

eFilePushThread::eFilePushThread(int blocksize, size_t buffersize):
	 m_sg(NULL),
	 m_stop(1),
	 m_send_pvr_commit(0),
	 m_stream_mode(0),
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

void eFilePushThread::thread()
{
	struct sigaction action;

	/* we set the signal to not restart syscalls, so we can detect our signal.
	 * SIGUSR1 is used to signal stopping from the parent thread */

	action.sa_handler = global_signal_SIGUSR1_handler;
	action.sa_flags = 0;
	sigaction(SIGUSR1, &action, 0);

	hasStarted(); /* "start()" blocks until we get here */
	setIoPrio(IOPRIO_CLASS_BE, 0);
	eDebug("[eFilePushThread] START thread");

	do
	{
	int eofcount = 0;
	int buf_end = 0;
	size_t bytes_read = 0;
	off_t current_span_offset = 0;
	size_t current_span_remaining = 0;
	m_sof = 0;

	while (!m_stop)
	{
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
			struct timeval starttime;
			struct timeval now;
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
			if (m_stop) {
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
				struct pollfd pfd;
				pfd.fd = m_fd_dest;
				pfd.events = POLLIN;
				switch (poll(&pfd, 1, 250)) // wait for 250ms
				{
					case 0:
						eDebug("[eFilePushThread] wait for driver eof timeout");
						continue;
					case 1:
						eDebug("[eFilePushThread] wait for driver eof ok");
						break;
					default:
						eDebug("[eFilePushThread] wait for driver eof aborted by signal");
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
							break;
						continue;
				}
			}

			if (m_stop)
				break;

				/* in stream_mode, we are sending EOF events
				   over and over until somebody responds.

				   in stream_mode, think of evtEOF as "buffer underrun occurred". */
			if (m_sof == 0)
				sendEvent(evtEOF);
			else
				sendEvent(evtUser); // start of file event

			if (m_stream_mode)
			{
				eDebug("[eFilePushThread] reached EOF, but we are in stream mode. delaying 1 second.");
				sleep(1);
				continue;
			}
			else if (++eofcount < 10)
			{
				eDebug("[eFilePushThread] reached EOF, but the file may grow. delaying 1 second.");
				sleep(1);
				continue;
			}
			break;
		} else
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
					if (m_stop) {
						w = 0;
						buf_start = 0;
						buf_end = 0;
						break;
					}
					if (w < 0 && (errno == EINTR || errno == EAGAIN || errno == EBUSY))
						continue;
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
		while (m_stop == 2) {
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
	struct sigaction action;

	m_source = source;
	m_fd_dest = fd_dest;
	m_current_position = 0;
	m_run_state = 1;
	m_stop = 0;

	/* prevent enigma main thread/process from being
	 * actually killed when a thread is signalled
	 * that not (yet) has signal handler or is not
	 * (yet) blocking signals. NB this is still in
	 * parent context */

	action.sa_handler = global_signal_SIGUSR1_handler;
	action.sa_flags = 0;
	sigaction(SIGUSR1, &action, 0);

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
	while (m_run_state) {
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
	m_messagepump(eApp, 0)
{
	CONNECT(m_messagepump.recv_msg, eFilePushThreadRecorder::recvEvent);
}

void eFilePushThreadRecorder::thread()
{
	struct pollfd pfd;
	struct timespec timeout;
	sigset_t sigset;
	int result;
	int bytes;

	setIoPrio(IOPRIO_CLASS_RT, 7);

	eDebug("[eFilePushThreadRecorder] THREAD START");

	/* block SIGUSR1 in this thread so it's delayed until the ppoll()
	 * call where it will be handled. ppoll() will lift the block
	 * momentarily and atomically, preventing a race condition */

	sigemptyset(&sigset);
	sigaddset(&sigset, SIGUSR1);
	pthread_sigmask(SIG_BLOCK, &sigset, (sigset_t *)0);

	hasStarted();

	/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
		/* this works around the buggy Broadcom encoder that always returns even if there is no data */
		/* (works like O_NONBLOCK even when not opened as such), prevent idle waiting for the data */
		/* this won't ever hurt, because it will return immediately when there is data or an error condition */

		pfd.fd = m_fd_source;
		pfd.events = POLLIN;
		pfd.revents = 0;
		timeout.tv_sec = 0;
		timeout.tv_nsec = 100 * 1000000;
		sigemptyset(&sigset);

		/* this ppoll call will all of: 1) enforce a short delay if there is nothing to be read
		 * (see above comment), 2) check if something actually can be read without blocking and
		 * 3) check whether a SIGUSR1 is pending.
		 * This is required to prevent a race condition leading to a deadlock, where a signal
		 * is sent by the parent, the signal is consumed by the call to poll() and so it
		 * doesn't interrupt the read call, which will never complete. */

		result = ppoll(&pfd, 1, &timeout, &sigset);

		if(result < 0)
		{
			if(errno == EINTR)
				continue; /* caught an SIGUSR1 interrupt; continue, this will test m_stop immediately -> while(!m_stop) */

			bytes = result; /* poll failed; this is unlikely, handle like read() returned the error */
		}
		else
		{
			if(result == 0) /* nothing happened, try again, handle like read() return EAGAIN */
			{
				errno = EAGAIN;
				bytes = -1;
			}
			else
			{
				if(result == 1)
				{
					if(pfd.revents & POLLIN) /* something really happened, we can read */
						bytes = ::read(m_fd_source, m_buffer, m_buffersize);
					else /* an error occured on the fd, don't read it and stop or abort whatever is applicable */
					{
						if(m_stop)
							errno = EAGAIN; /* stop after SIGUSR1 */
						else
							errno = EINVAL; /* abort after actual error */
						bytes = -1;
					}
				}
				else /* catch-all, shouldn't happen */
				{
					errno = EINVAL;
					bytes = -1;
				}
			}
		}

		if (bytes < 0)
		{
			bytes = 0;

			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
				continue; /* this will test m_stop immediately -> while(!m_stop) */

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

#ifdef SHOW_WRITE_TIME
		struct timeval starttime;
		struct timeval now;
		gettimeofday(&starttime, NULL);
#endif
		int w = writeData(bytes);
#ifdef SHOW_WRITE_TIME
		gettimeofday(&now, NULL);
		suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
		eDebug("[eFilePushThreadRecorder] write %d bytes time: %9u us", bytes, (unsigned int)diff);
#endif
		if (w < 0)
		{
			eWarning("[eFilePushThreadRecorder] WRITE ERROR, aborting thread: %m");
			sendEvent(evtWriteError);
			break;
		}
	}
	flush();
	sendEvent(evtStopped);
	eDebug("[eFilePushThreadRecorder] THREAD STOP");
}

void eFilePushThreadRecorder::start(int fd)
{
	struct sigaction action;

	m_fd_source = fd;
	m_stop = 0;

	/* prevent enigma main thread/process from being
	 * actually killed when a thread is signalled
	 * that not (yet) has signal handler or is not
	 * (yet) blocking signals. NB this is still in
	 * parent context. */
	action.sa_handler = global_signal_SIGUSR1_handler;
	action.sa_flags = 0;
	sigaction(SIGUSR1, &action, 0);

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
