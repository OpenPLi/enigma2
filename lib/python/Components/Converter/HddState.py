from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Harddisk import harddiskmanager
from Components.config import config
from Components.SystemInfo import SystemInfo
from skin import parameters
from enigma import eTimer


#***************************************************************
#	internalAll/internalHDD/internalSSD/external - disk type
#	Example : <convert type="HddState">internalAll</convert>
#	or all type - internal and external
#	Example : <convert type="HddState"></convert>
#	noLetterName - do not print a letter "I"(internal)/"S"(SSD)/"E"(external)
#	Example : <convert type="HddState">noLetterName</convert>
#	allVisible - show "Disk state: standby " when use noLetterName
#	Example : <convert type="HddState">noLetterName,allVisible</convert>
#***************************************************************


class HddState(Converter):
	ALL = 0
	INTERNAL_ALL = 1
	INTERNAL_HDD = 2
	INTERNAL_SSD = 3
	EXTERNAL = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		args = type.lower().split(",")
		self.notDiskLetterName = "nolettername" in args
		self.allVisible = "allvisible" in args
		if "internalall" in args:
			self.type = self.INTERNAL_ALL
		elif "internalhdd" in args:
			self.type = self.INTERNAL_HDD
		elif "internalssd" in args:
			self.type = self.INTERNAL_SSD
		elif "external" in args:
			self.type = self.EXTERNAL
		else:
			self.type = self.ALL
		self.standby_time = 150
		self.isActive = False
		self.state_text = ""
		self.isHDD()
		self.timer = eTimer()
		self.timer.callback.append(self.updateHddState)
		self.idle_time = int(config.usage.hdd_standby.value)
		config.usage.hdd_standby.addNotifier(self.setStandbyTime, initial_call=False)
		self.colors = parameters.get("HddStateColors", (0x00FFFF00, 0x0000FF00)) # standby - yellow, active - green
		if self.hdd_list:
			self.updateHddState(force=True)
		if self.onPartitionAddRemove not in harddiskmanager.on_partition_list_change:
			harddiskmanager.on_partition_list_change.append(self.onPartitionAddRemove)

	def onPartitionAddRemove(self, state, part):
		self.timer.stop()
		self.isHDD()
		self.updateHddState(force=True)

	def updateHddState(self, force=False):
		prev_state = self.isActive
		string = ""
		state = False
		if self.hdd_list:
			for hdd in self.hdd_list:
				if string and not self.notDiskLetterName:
					string += " "
				if (hdd[1].max_idle_time or force) and not hdd[1].isSleeping():
					state = True
				if not self.notDiskLetterName:
					string += "\c%08x" % (state and self.colors[1] or self.colors[0])
					name = "I"
					if not hdd[1].internal:
						name = "E"
					elif not hdd[1].rotational:
						name = "S"
					string += name
			if not state:
				if self.allVisible:
					if self.notDiskLetterName:
						string = "\c%08x" % self.colors[0]
						string += _("standby ")
				self.isActive = False
				idle = self.standby_time
			else:
				if self.notDiskLetterName:
					string = "\c%08x" % self.colors[1]
					string += _("active ")
				self.isActive = True
				idle = self.idle_time
			if self.idle_time:
				timeout = len(self.hdd_list) > 1 and self.standby_time or idle
				self.timer.start(timeout * 100, True)
		else:
			self.isActive = False
		if string:
			string = _("Disk state: ") + string
		self.state_text = string
		if prev_state != self.isActive or force:
			if SystemInfo["LCDsymbol_hdd"]:
				open(SystemInfo["LCDsymbol_hdd"], "w").write(self.isActive and "1" or "0")
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
					elif self.type == self.INTERNAL_ALL:
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
		return self.isActive and True or False
	boolean = property(getBoolean)

	@cached
	def getValue(self):
		return self.isActive and 1 or 0
	value = property(getValue)
