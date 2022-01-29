from twisted.web import client
from twisted.internet import reactor, defer
from urllib.parse import urlparse


class HTTPProgressDownloader(client.HTTPDownloader):
	def __init__(self, url, outfile, headers=None):
		client.HTTPDownloader.__init__(self, url, outfile, headers=headers, agent=b"Enigma2 HbbTV/1.1.1 (+PVR+RTSP+DL;OpenPLi;;;)")
		self.status = self.progress_callback = self.error_callback = self.end_callback = None
		self.deferred = defer.Deferred()

	def noPage(self, reason):
		if self.status == b"304":
			client.HTTPDownloader.page(self, b"")
		else:
			client.HTTPDownloader.noPage(self, reason)
		if self.error_callback:
			self.error_callback(reason.getErrorMessage(), self.status)

	def gotHeaders(self, headers):
		if self.status == b"200":
			if b"content-length" in headers:
				self.totalbytes = int(headers[b"content-length"][0])
			else:
				self.totalbytes = 0
			self.currentbytes = 0.0
		return client.HTTPDownloader.gotHeaders(self, headers)

	def pagePart(self, packet):
		if self.status == b"200":
			self.currentbytes += len(packet)
		if self.totalbytes and self.progress_callback:
			self.progress_callback(self.currentbytes, self.totalbytes)
		return client.HTTPDownloader.pagePart(self, packet)

	def pageEnd(self):
		ret = client.HTTPDownloader.pageEnd(self)
		if self.end_callback:
			self.end_callback()
		return ret


class downloadWithProgress:
	def __init__(self, url, outputfile, contextFactory=None, *args, **kwargs):
		if isinstance(url, str):
			url = url.encode("UTF-8")
		parsed = urlparse(url)
		scheme = parsed.scheme
		host = parsed.hostname
		port = parsed.port or (443 if scheme == b'https' else 80)
		self.factory = HTTPProgressDownloader(url, outputfile, *args, **kwargs)
		if scheme == b'https':
			from twisted.internet import ssl
			if contextFactory is None:
				contextFactory = ssl.ClientContextFactory()
			self.connection = reactor.connectSSL(host, port, self.factory, contextFactory)
		else:
			self.connection = reactor.connectTCP(host, port, self.factory)

	def start(self):
		return self.factory.deferred

	def stop(self):
		if self.connection:
			self.factory.progress_callback = self.factory.end_callback = self.factory.error_callback = None
			self.connection.disconnect()

	def addProgress(self, progress_callback):
		self.factory.progress_callback = progress_callback

	def addEnd(self, end_callback):
		self.factory.end_callback = end_callback

	def addError(self, error_callback):
		self.factory.error_callback = error_callback
