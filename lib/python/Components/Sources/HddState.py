from Source import Source
from Components.Element import cached
from Components.Harddisk import harddiskmanager
from Components.config import config
from enigma import eTimer
from Components.SystemInfo import SystemInfo


class HddState(Source):
	ALL = 0
	INTERNAL = 1
	INTERNAL_HDD = 2
	INTERNAL_SSD = 3
	EXTERNAL = 4

	def __init__(self, session, poll=600, type=0, diskName=True, allVisible=False):
		Source.__init__(self)
		self.session = session
		if type == 1:
			self.type = self.INTERNAL
		elif type == 2:
			self.type = self.INTERNAL_HDD
		elif type == 3:
			self.type = self.INTERNAL_SSD
		elif type == 4:
			self.type = self.EXTERNAL
		else:
			self.type = self.ALL
		self.isSleeping = False
		self.state_text = ""
		self.isHDD()
		self.diskName = diskName
		self.allVisible = allVisible
		self.standby_time = poll
		self.timer = eTimer()
		self.timer.callback.append(self.updateHddState)
		self.idle_time = int(config.usage.hdd_standby.value)
		config.usage.hdd_standby.addNotifier(self.setStandbyTime, initial_call=False)
		if self.hdd_list:
			self.updateHddState(force=True)
		if self.onPartitionAddRemove not in harddiskmanager.on_partition_list_change:
			harddiskmanager.on_partition_list_change.append(self.onPartitionAddRemove)

	def onPartitionAddRemove(self, state, part):
		self.timer.stop()
		self.isHDD()
		self.updateHddState(force=True)

	def updateHddState(self, force=False):
		prev_state = self.isSleeping
		string = ""
		state = False
		if self.hdd_list:
			for hdd in self.hdd_list:
				if string and self.diskName:
					string += " "
				if (hdd[1].max_idle_time or force) and not hdd[1].isSleeping():
					state = True
				if self.diskName:
					color = state and "\c0000??00" or "\c00????00"
					string += color
					name = "I"
					if not hdd[1].internal:
						name = "E"
					elif not hdd[1].rotational:
						name = "S"
					string += name
			if not state:
				if self.allVisible:
					if not string:
						string = "\c0000??00"
						string += "standby" 
				self.isSleeping = False
				idle = self.standby_time
			else:
				if not string:
					string = "\c0000??00"
					string += "active"
				self.isSleeping = True
				idle = self.idle_time
			if self.idle_time:
				timeout = len(self.hdd_list) > 1 and self.standby_time or idle
				self.timer.start(timeout * 100, True) 
		else:
			self.isSleeping = False
		if string:
			string = "Disk state: " + string
		self.state_text = string
		if prev_state != self.isSleeping or force:
			if SystemInfo["LCDsymbol_hdd"]:
				open(SystemInfo["LCDsymbol_hdd"], "w").write(self.isSleeping and "1" or "0")
			self.changed((self.CHANGED_ALL,))

	def setStandbyTime(self, cfgElem):
		self.timer.stop()
		self.idle_time = int(cfgElem.value)
		self.updateHddState(force=True)

	def isHDD(self):
		self.hdd_list = []
		if harddiskmanager.HDDCount():
			for hdd in harddiskmanager.HDDList():
				if hdd[1].idle_running and not hdd[1].card:
					if self.type == self.ALL:
						self.hdd_list.append(hdd)
					elif self.type == self.INTERNAL:
						if hdd[1].internal:
							self.hdd_list.append(hdd)
					elif self.type == self.INTERNAL_HDD:
						if hdd[1].internal and hdd[1].rotational:
							self.hdd_list.append(hdd)
					elif self.type == self.INTERNAL_SSD:
						if hdd[1].internal and not hdd[1].rotational:
							self.hdd_list.append(hdd)
					elif self.type == self.EXTERNAL:
						if not hdd[1].internal:
							self.hdd_list.append(hdd)

	def doSuspend(self, suspended):
		pass

	@cached
	def getText(self):
		return self.state_text
	text = property(getText)

	@cached
	def getBoolean(self):
		return self.isSleeping and True or False
	boolean = property(getBoolean)

	@cached
	def getValue(self):
		return self.isSleeping
	value = property(getValue)
