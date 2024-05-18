from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile
from Components.NimManager import nimmanager, InitNimManager
from Components.TuneTest import Tuner
from enigma import eDVBFrontendParametersSatellite, eDVBResourceManager, eTimer


class AutoDiseqc(ConfigListScreen, Screen):
	skin = """
		<screen position="c-250,c-100" size="500,250" title=" ">
			<widget source="statusbar" render="Label" position="10,5" zPosition="10" size="e-10,60" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="tunerstatusbar" render="Label" position="10,60" zPosition="10" size="e-10,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="10,100" size="e-10,100" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="buttons/red.png" position="c-140,e-45" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="c-140,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		</screen>"""

	diseqc_ports = [
		"A", "B", "C", "D"
	]

	sat_frequencies = [
		# Thor 0.8W Sky News
		(
			12418,
			28000,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_7_8,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3592,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			20,
			70,
			"Thor 5/6/7 0.8w"),

		# Eutelsat 9.0E CCTV Europe
		(
			11996,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			90,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			6400,
			156,
			"Eutelsat 9B 9.0e"),

		# Hotbird 13.0E Rai 1
		(
			10992,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			130,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			12400,
			318,
			"Hotbird 13.0e"),

		# Eutelsat 16.0E OTV
		(
			11345,
			30000,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			160,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			24100,
			366,
			"Eutelsat 16A 16.0e"),

		# Astra 19.2E ZDF
		(
			11954,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			192,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			1079,
			1,
			"Astra 1 19.2e"),

		# Astra 23.5E Astra SES
		(
			12168,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			235,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			3224,
			3,
			"Astra 3 23.5e"),

		# Astra 28.2E EPG background audio
		(
			11778,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			282,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			2004,
			2,
			"Astra 2 28.2e"),

		# Eutelsat 5.0W Fransat
		(
			11054,
			29950,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3550,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			20500,
			1375,
			"Eutelsat 5 West B 5.0w"),

		# Hispasat 30.0W TSA
		(
			10890,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3300,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			15,
			2,
			"Hispasat 30.0w"),
	]

	circular_sat_frequencies = [
		# Express AMU1 36.0E NTV Plus
		(
			11785,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_CircularRight,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			360,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			13,
			112,
			"Express AMU1 36.0e"),
	]

	SAT_TABLE_FREQUENCY = 0
	SAT_TABLE_SYMBOLRATE = 1
	SAT_TABLE_POLARISATION = 2
	SAT_TABLE_FEC = 3
	SAT_TABLE_INVERSION = 4
	SAT_TABLE_ORBPOS = 5
	SAT_TABLE_SYSTEM = 6
	SAT_TABLE_MODULATION = 7
	SAT_TABLE_ROLLOFF = 8
	SAT_TABLE_PILOT = 9
	SAT_TABLE_IS_ID = 10
	SAT_TABLE_PLS_MODE = 11
	SAT_TABLE_PLS_CODE = 12
	SAT_TABLE_T2MI_PLP_ID = 13
	SAT_TABLE_T2MI_PID = 14
	SAT_TABLE_TSID = 15
	SAT_TABLE_ONID = 16
	SAT_TABLE_NAME = 17

	def __init__(self, session, feid, nr_of_ports, simple_tone, simple_sat_change):
		self.skin = AutoDiseqc.skin
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(" ")
		self["tunerstatusbar"] = StaticText(" ")

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session)

		self["config"].list = self.list

		self["key_red"] = StaticText(_("Abort"))

		self.index = 0
		self.port_index = 0
		self.feid = feid
		self.nr_of_ports = nr_of_ports
		self.simple_tone = simple_tone
		self.simple_sat_change = simple_sat_change
		self.found_sats = []
		self.circular_setup = False
		sat_found = False
		for x in self.sat_frequencies:
			if x[self.SAT_TABLE_ORBPOS] == 360:
				sat_found = True
		if self.nr_of_ports == 1:
			if not sat_found:
				self.sat_frequencies += self.circular_sat_frequencies
		elif sat_found:
			self.sat_frequencies.remove(x)

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					if hasattr(self.session, 'infobar'):
						if self.session.infobar.servicelist and self.session.infobar.servicelist.dopipzap:
							self.session.infobar.servicelist.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
				if not self.openFrontend():
					self.frontend = None
					self.raw_channel = None

		if self.raw_channel:
			self.raw_channel.receivedTsidOnid.get().append(self.gotTsidOnid)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
		}, -2)

		self.count = 0
		self.state = 0
		self.abort = False

		self.diseqc = [
			config.Nims[self.feid].diseqcA.value,
			config.Nims[self.feid].diseqcB.value,
			config.Nims[self.feid].diseqcC.value,
			config.Nims[self.feid].diseqcD.value,
		]

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.tunerStatusTimer = eTimer()
		self.tunerStatusTimer.callback.append(self.tunerStatusCallback)
		self.startStatusTimer()
		self.onClose.append(self.__onClose)

	def __onClose(self):
		if self.raw_channel:
			self.raw_channel.receivedTsidOnid.get().remove(self.gotTsidOnid)

	def keyCancel(self):
		self.abort = True

	def keyOK(self):
		return

	def keyLeft(self):
		return

	def keyRight(self):
		return

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def statusCallback(self):
		if self.state == 0:
			if self.port_index == 0 and self.diseqc[0] == "3600":
				self.clearNimEntries()
				config.Nims[self.feid].diseqcA.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 1 and self.diseqc[1] == "3600":
				self.clearNimEntries()
				config.Nims[self.feid].diseqcB.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 2 and self.diseqc[2] == "3600":
				self.clearNimEntries()
				config.Nims[self.feid].diseqcC.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 3 and self.diseqc[3] == "3600":
				self.clearNimEntries()
				config.Nims[self.feid].diseqcD.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])

			if self.nr_of_ports == 4:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b_c_d"
			elif self.nr_of_ports == 2:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b"
			else:
				config.Nims[self.feid].diseqcMode.value = "single"
				if self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS] == 360 and not self.found_sats:
					config.Nims[self.feid].simpleDiSEqCSetCircularLNB.value = True
					self.circular_setup = True

			config.Nims[self.feid].configMode.value = "simple"
			config.Nims[self.feid].simpleDiSEqCSetVoltageTone = self.simple_tone
			config.Nims[self.feid].simpleDiSEqCOnlyOnSatChange = self.simple_sat_change

			self.saveAndReloadNimConfig()
			self.state += 1

		elif self.state == 1:
			if self.diseqc[self.port_index] != "3600":
				self.statusTimer.stop()
				self.count = 0
				self.state = 0
				self.index = len(self.sat_frequencies) - 1
				self.tunerStopScan(False)
				return

			if self.circular_setup:
				if self.raw_channel:
					self.raw_channel.receivedTsidOnid.get().remove(self.gotTsidOnid)
				del self.frontend
				del self.raw_channel
				if not self.openFrontend():
					self.frontend = None
					self.raw_channel = None
				if self.raw_channel:
					self.raw_channel.receivedTsidOnid.get().append(self.gotTsidOnid)

			InitNimManager(nimmanager)

			self.tuner = Tuner(self.frontend)
			if self.raw_channel:
				self.raw_channel.requestTsidOnid()
			self.tuner.tune(self.sat_frequencies[self.index])

			self["statusbar"].setText(_("Checking tuner %s\nDiSEqC port %s for %s") % (chr(self.feid + 65), self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self["tunerstatusbar"].setText(" ")

			self.count = 0
			self.state = 0

			self.startTunerStatusTimer()
			return

		self.startStatusTimer()

	def startStatusTimer(self):
		self.statusTimer.start(100, True)

	def setupSave(self):
		self.clearNimEntries()
		for x in self.found_sats:
			if x[0] == "A":
				config.Nims[self.feid].diseqcA.value = "%d" % (x[1])
			elif x[0] == "B":
				config.Nims[self.feid].diseqcB.value = "%d" % (x[1])
			elif x[0] == "C":
				config.Nims[self.feid].diseqcC.value = "%d" % (x[1])
			elif x[0] == "D":
				config.Nims[self.feid].diseqcD.value = "%d" % (x[1])
		self.saveAndReloadNimConfig()

	def setupClear(self):
		self.clearNimEntries()
		self.saveAndReloadNimConfig()

	def clearNimEntries(self):
		config.Nims[self.feid].diseqcA.value = "3601" if self.diseqc[0] == "3600" else self.diseqc[0]
		config.Nims[self.feid].diseqcB.value = "3601" if self.diseqc[1] == "3600" else self.diseqc[1]
		config.Nims[self.feid].diseqcC.value = "3601" if self.diseqc[2] == "3600" else self.diseqc[2]
		config.Nims[self.feid].diseqcD.value = "3601" if self.diseqc[3] == "3600" else self.diseqc[3]

	def saveAndReloadNimConfig(self):
		config.Nims[self.feid].save()
		configfile.save()
		configfile.load()
		nimmanager.sec.update()

	def tunerStatusCallback(self):
		dict = {}
		if self.frontend:
			self.frontend.getFrontendStatus(dict)
		else:
			self.tunerStopScan(False)
			return

		if dict["tuner_state"] == "TUNING":
			self["tunerstatusbar"].setText(_("Tuner status:") + " " + _("TUNING"))
		elif dict["tuner_state"] == "LOCKED":
			self["tunerstatusbar"].setText(_("Tuner status:") + " " + _("ACQUIRING TSID/ONID"))
		elif dict["tuner_state"] == "IDLE":
			self["tunerstatusbar"].setText(_("Tuner status:") + " " + _("IDLE"))
		elif dict["tuner_state"] == "UNKNOWN":
			self["tunerstatusbar"].setText(_("Tuner status:") + " " + _("UNKNOWN"))
		elif dict["tuner_state"] == "LOSTLOCK" or dict["tuner_state"] == "FAILED":
			self["tunerstatusbar"].setText(_("Tuner status:") + " " + _("FAILED"))
			self.tunerStopScan(False)
			return

		self.count += 1
		if self.count > 10:
			self.tunerStopScan(False)
		else:
			self.startTunerStatusTimer()

	def startTunerStatusTimer(self):
		self.tunerStatusTimer.start(1000, True)

	def gotTsidOnid(self, tsid, onid):
		self.tunerStatusTimer.stop()
		if tsid == self.sat_frequencies[self.index][self.SAT_TABLE_TSID] and onid == self.sat_frequencies[self.index][self.SAT_TABLE_ONID]:
			self.tunerStopScan(True)
		else:
			self.tunerStopScan(False)

	def tunerStopScan(self, result):
		if self.abort:
			self.setupClear()
			self.close(False)
			return
		if result:
			self.found_sats.append((self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self.index = 0
			self.port_index += 1
		else:
			self.index += 1
			if len(self.sat_frequencies) == self.index:
				self.index = 0
				self.port_index += 1

		if len(self.found_sats) > 0:
			self.list = []
			for x in self.found_sats:
				self.list.append(_("DiSEqC port %s: %s") % (x[0], x[2]))
			self["config"].l.setList(self.list)

		if self.nr_of_ports == self.port_index:
			self.state = 99
			self.setupSave()
			self.close(len(self.found_sats) > 0)
			return

		for x in self.found_sats:
			if x[1] == self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS]:
				self.tunerStopScan(False)
				return

		self.startStatusTimer()
