import enigma, ctypes, os

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
		self.container = None
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

class PosixSpawn():
	def __init__(self):
		self.libc = ctypes.cdll.LoadLibrary("libc.so.6")
		self._posix_spawn = self.libc.posix_spawn
		self._posix_spawn.restype = ctypes.c_int
		self._posix_spawn.argtypes = (
			ctypes.POINTER(ctypes.c_int),
			ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p,
			ctypes.POINTER(ctypes.c_char_p),
			ctypes.POINTER(ctypes.c_char_p)
		)
		# dirty hack: hardcoded struct sizes
		self.attrs = self.libc.malloc(336)
		self.actions = self.libc.malloc(80)
		self.devnull = open("/dev/null","wb")
		self.env = [x+"="+os.environ[x] for x in os.environ] + [ 0 ]

	def execute(self, exe, args=[]):
		print "[Console] PosixSpawn command: %s" % exe
		pid = ctypes.c_int()
		args = [exe] + args + [ 0 ]
		argv = (ctypes.c_char_p * 5) (*args)
		env = (ctypes.c_char_p * ( len(self.env) ))(*self.env)
		self.libc.posix_spawnattr_init(self.attrs)
		self.libc.posix_spawnattr_setflags(self.attrs, 0x40)
		self.libc.posix_spawn_file_actions_init(self.actions)
		self.libc.posix_spawn_file_actions_adddup2(self.actions, self.devnull.fileno(), 1)
		self._posix_spawn(ctypes.byref(pid), ctypes.c_char_p(exe),
			self.actions, self.attrs,
			ctypes.cast(argv, ctypes.POINTER(ctypes.c_char_p)),
			ctypes.cast(env, ctypes.POINTER(ctypes.c_char_p)))
		status = ctypes.c_int()
		self.libc.waitpid(pid.value, ctypes.byref(status), 0)