import enigma

class ConsoleItem:
	def __init__(self, containers, cmd, callback, extra_args):
		self.extra_args = extra_args
		self.callback = callback
		self.container = enigma.eConsoleAppContainer()
		self.containers = containers
		# Create a unique name
		name = cmd
		if name in containers:
			name = str(cmd) + '@' + hex(id(self))
		self.name = name
		containers[name] = self
		# If the caller isn't interested in our results, we don't need
		# to store the output either.
		if callback is not None:
			self.appResults = []
			self.container.dataAvail.append(self.dataAvailCB)
		self.container.appClosed.append(self.finishedCB)
		if isinstance(cmd, str): # until .execute supports a better api
			cmd = [cmd]
		retval = self.container.execute(*cmd)
		if retval:
			self.finishedCB(retval)
	def dataAvailCB(self, data):
		self.appResults.append(data)
	def finishedCB(self, retval):
		print "[Console] finished:", self.name
		del self.containers[self.name]
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container
		callback = self.callback
		if callback is not None:
			data = ''.join(self.appResults)
			callback(data, retval, self.extra_args)

class Console(object):
	def __init__(self):
		# Still called appContainers because Network.py accesses it to
		# know if there's still stuff running
		self.appContainers = {}

	def ePopen(self, cmd, callback=None, extra_args=[]):
		print "[Console] command:", cmd
		return ConsoleItem(self.appContainers, cmd, callback, extra_args)

	def eBatch(self, cmds, callback, extra_args=[], debug=False):
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retval, _extra_args):
		(cmds, callback, extra_args) = _extra_args
		if self.debug:
			print '[eBatch] retval=%s, cmds left=%d, data:\n%s' % (retval, len(cmds), data)
		if cmds:
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])
		else:
			callback(extra_args)

	def kill(self, name):
		if name in self.appContainers:
			print "[Console] killing: ", name
			self.appContainers[name].container.kill()

	def killAll(self):
		for name, item in self.appContainers.items():
			print "[Console] killing: ", name
			item.container.kill()

class ePopen():
	def __init__(self, command, callback=None, datacallback=None):
		self.callback = callback
		self.datacallback = datacallback
		self.data = []
		self.container = enigma.eConsoleAppContainer()
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.appClosed)
		try:
			if self.container.execute(command):
				raise Exception, "failed to execute: %s" % command
		except Exception, e:
			self.appClosed(e)

	def dataAvail(self, str):
		if self.datacallback:
			self.datacallback(str)
		if self.callback:
			self.data.append(str)

	def appClosed(self, retval):
		self.container.dataAvail.remove(self.dataAvail)
		self.container.appClosed.remove(self.appClosed)
		del self.container
		if self.callback:
			self.callback(retval, "".join(self.data))
