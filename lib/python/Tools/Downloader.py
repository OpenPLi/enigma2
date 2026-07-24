from os import unlink

from time import time

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.web.client import Agent, RedirectAgent, BrowserLikePolicyForHTTPS, ResponseDone
from twisted.web.http_headers import Headers
from twisted.internet.protocol import Protocol

from urllib.request import Request, urlopen


# ------------------------------------------------------------
# NON-BLOCKING HEAD SUPPORT, run in deferToThread()
# ------------------------------------------------------------
def get_content_length(url, headers=None):
	try:
		req = Request(url, headers=headers or {}, method="HEAD")
		with urlopen(req, timeout=5) as r:
			val = r.headers.get("Content-Length")
			return int(val) if val else 0
	except Exception:
		return 0


# ------------------------------------------------------------
# STREAM PROTOCOL (no UI logic)
# ------------------------------------------------------------
class _DownloadProtocol(Protocol):
	def __init__(self, downloader, fd):
		self.downloader = downloader
		self.fd = fd
		self.recv = 0

	def dataReceived(self, data):
		if self.downloader.stopFlag:
			try:
				self.transport.abortConnection()
			except Exception:
				pass
			return

		self.recv += len(data)
		try:
			self.fd.write(data)
		except OSError as err:
			if callable(self.downloader.errorCallback):
				self.downloader.errorCallback(err)
			try:
				self.transport.abortConnection()
			except Exception:
				pass
			return

		self.downloader.progress = self.recv

		self.downloader._pendingProgress = (
			self.recv,
			self.downloader.totalSize
		)

		if not self.downloader._uiScheduled:
			self.downloader._uiScheduled = True
			reactor.callLater(0.2, self.downloader._flushUi)

	def connectionLost(self, reason):
		try:
			self.fd.close()
		except Exception:
			pass

		if reason.check(ResponseDone) and not self.downloader.stopFlag:
			if callable(self.downloader.endCallback):
				self.downloader.endCallback(self.downloader.outputFile)
			return

		try:
			unlink(self.downloader.outputFile)
		except OSError:
			pass

		if not self.downloader.stopFlag:
			if callable(self.downloader.errorCallback):
				self.downloader.errorCallback(reason)


# ------------------------------------------------------------
# DOWNLOADER
# ------------------------------------------------------------
class DownloadWithProgress:

	def __init__(self, url, outputFile, *args, **kwargs):
		self.url = url
		self.outputFile = outputFile

		userAgent = kwargs.get("userAgent", "Enigma2 Downloader")

		self.progress = 0
		self.totalSize = -1  # means size not set

		self.progressCallback = None
		self.endCallback = None
		self.errorCallback = None

		self.stopFlag = False

		self._pendingProgress = None
		self._uiScheduled = False
		self._request = None

		# for speed/eta functions
		self._startTime = None

		# headers (Twisted-safe: bytes in, bytes out)
		self.requestHeader = {
			b"User-Agent": userAgent.encode("utf-8"),
			b"Accept": b"*/*",
			b"Accept-Encoding": b"identity",
			b"Connection": b"keep-alive",
		}

		userHeader = kwargs.get("headers", None)
		if userHeader:
			for k, v in userHeader.items():
				k = k.encode("utf-8") if isinstance(k, str) else k
				v = v.encode("utf-8") if isinstance(v, str) else v
				self.requestHeader[k] = v

		base = Agent(reactor, contextFactory=BrowserLikePolicyForHTTPS())
		self.agent = RedirectAgent(base)

	def start(self):
		self.progress = 0
		self.totalSize = -1
		self._startTime = time()

		# NON-BLOCKING HEAD (hint only)
		deferToThread(self._getHeadSize).addCallback(self._gotHeadSize)

		self._startGet()
		return self

	def _getHeadSize(self):
		headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in self.requestHeader.items()}  # for urllib compatibility
		return get_content_length(self.url, headers)

	def _gotHeadSize(self, size):
		# never override a known good value from GET
		if self.totalSize > 0:
			return
		if size and size > 0:
			self.totalSize = size
		else:
			self.totalSize = -1

	# --------------------------------------------------------
	# GET REQUEST
	# --------------------------------------------------------
	def _startGet(self):
		try:
			headers = Headers({
				k: [v]
				for k, v in self.requestHeader.items()
			})

			self._request = self.agent.request(
				b"GET",
				self.url.encode("utf-8"),
				headers,
				None
			)

			self._request.addCallbacks(self._responseReceived, self._requestFailed)

		except Exception as err:
			if callable(self.errorCallback):
				self.errorCallback(err)

	# --------------------------------------------------------
	# RESPONSE
	# --------------------------------------------------------
	def _responseReceived(self, response):

		# STRICT HTTP GATE
		if not (200 <= response.code < 300):  # if not 2XX code means request failed
			try:
				response.transport.abortConnection()
			except Exception:
				pass

			if callable(self.errorCallback):
				self.errorCallback(Exception("HTTP %d" % response.code))
			return

		# content-length hint from server
		try:
			length = response.headers.getRawHeaders("content-length")
			if length:
				val = int(length[0])
				if val > 0:
					self.totalSize = val
		except Exception:
			pass

		try:  # catch any exception while trying to create the local file
			fd = open(self.outputFile, "wb")
		except Exception as err:
			if callable(self.errorCallback):
				self.errorCallback(err)
			return

		response.deliverBody(_DownloadProtocol(self, fd))

	# --------------------------------------------------------
	# UI FLUSH
	# --------------------------------------------------------
	def _flushUi(self):
		self._uiScheduled = False

		if self._pendingProgress and callable(self.progressCallback):
			progress, total = self._pendingProgress

			if total <= 0:
				total = -1

			self.progressCallback(progress, total)

	# --------------------------------------------------------
	# ERROR HANDLING
	# --------------------------------------------------------
	def _requestFailed(self, failure):
		if callable(self.errorCallback):
			self.errorCallback(failure)

	# --------------------------------------------------------
	# CONTROL
	# --------------------------------------------------------
	def stop(self):
		self.stopFlag = True

		if self._request:
			try:
				self._request.cancel()
			except Exception:
				pass

	# --------------------------------------------------------
	# CALLBACKS
	# --------------------------------------------------------
	def addProgress(self, progressCallback):
		self.progressCallback = progressCallback
		return self

	def addEnd(self, endCallback):
		self.endCallback = endCallback
		return self

	def addError(self, errorCallback):
		self.errorCallback = errorCallback
		return self

	def setAgent(self, userAgent):
		self.requestHeader[b"User-Agent"] = userAgent.encode("utf-8")

	def addErrback(self, errorCallback):  # Temporary support for deprecated callbacks.
		print("[Downloader] Warning: DownloadWithProgress 'addErrback' is deprecated use 'addError' instead!")
		return self.addError(errorCallback)

	def addCallback(self, endCallback):  # Temporary support for deprecated callbacks.
		print("[Downloader] Warning: DownloadWithProgress 'addCallback' is deprecated use 'addEnd' instead!")
		return self.addEnd(endCallback)

	# --------------------------------------------------------
	# SPEED / ETA, for use by newer UI
	# --------------------------------------------------------
	def getSpeed(self):
		"""
		Returns current average download speed in bytes/sec.
		Returns 0 if not enough information is available.
		"""
		if not self._startTime:
			return 0

		elapsed = time() - self._startTime

		if elapsed <= 0:
			return 0

		return float(self.progress) / elapsed

	def getEta(self):
		"""
		Returns estimated seconds remaining.
		Returns -1 if total size is unknown.
		"""
		if self.totalSize <= 0:
			return -1

		speed = self.getSpeed()

		if speed <= 0:
			return -1

		remaining = self.totalSize - self.progress

		if remaining <= 0:
			return 0

		return int(remaining / speed)


# ------------------------------------------------------------
# COMPATIBILITY,
# Class names should start with a Capital letter, this
# catches old code until that code can be updated.
# ------------------------------------------------------------
class downloadWithProgress(DownloadWithProgress):
	pass