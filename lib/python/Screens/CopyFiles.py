import os
import Components.Task
from twisted.internet import task

class GiveupOnSendfile(Exception):
	pass

def nosendfile(*args):
	raise GiveupOnSendfile("sendfile() not available")

try:
	from sendfile import sendfile
except:
	sendfile = nosendfile

class FailedPostcondition(Components.Task.Condition):
	def __init__(self, exception):
		self.exception = exception
	def getErrorMessage(self, task):
		return str(self.exception)
	def check(self, task):
		return self.exception is None

# Same as Python 3.3 open(filename, "x"), we must be the creator
def openex(filename, flags=os.O_CREAT | os.O_EXCL | os.O_WRONLY):
	return os.fdopen(os.open(filename, flags), 'wb', 0)

class CopyFileTask(Components.Task.PythonTask):
	def openFiles(self, fileList):
		self.callback = None
		self.fileList = fileList
		self.handles = [(open(fn[0], 'rb', buffering=0), openex(fn[1])) for fn in fileList]
		self.end = 0
		for src,dst in fileList:
			try:
				self.end += os.stat(src).st_size
			except:
				print "Failed to stat", src
		if not self.end:
			self.end = 1
		print "[CopyFileTask] size:", self.end
	def work(self):
		print "[CopyFileTask] handles ", len(self.handles)
		try:
			for src, dst in self.handles:
				try:
					bs = 1048576 # 1MB chunks
					offset = 0
					fdd = dst.fileno()
					fds = src.fileno()
					while 1:
						if self.aborted:
							print "[CopyFileTask] aborting"
							raise Exception, "Aborted"
						try:
							l = sendfile(fdd, fds, offset, bs)
						except OSError as ex:
							if offset == 0:
								raise GiveupOnSendfile("sendfile failed, probably not suitable for mmap")
						self.pos += l
						if l < bs:
							break
						offset += l
				except GiveupOnSendfile as ex:
					print "[CopyFileTask]", ex
					bs = 65536
					d = bytearray(bs)
					while 1:
						if self.aborted:
							print "[CopyFileTask] aborting"
							raise Exception, "Aborted"
						l = src.readinto(d)
						if l < bs:
							if not l:
								# EOF
								src.close()
								dst.close()
								break
							dst.write(buffer(d, 0, l))
						else:
							dst.write(d)
						self.pos += l
		except:
			# In any event, close all handles
			for src, dst in self.handles:
				src.close()
				dst.close()
			for s,d in self.fileList:
				# Remove incomplete data.
				try:
					os.unlink(d)
				except:
					pass
			raise

class MoveFileTask(CopyFileTask):
	def work(self):
		CopyFileTask.work(self)
		print "[MoveFileTask]: delete source files"
		errors = []
		for s,d in self.fileList:
			try:
				os.unlink(s)
			except Exception, e:
				errors.append(e)
		if errors:
			raise errors[0]

def copyFiles(fileList, name):
	name = _("Copy") + " " + name
	job = Components.Task.Job(name)
	task = CopyFileTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)

def moveFiles(fileList, name):
	name = _("Move") + " " + name
	job = Components.Task.Job(name)
	task = MoveFileTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)
