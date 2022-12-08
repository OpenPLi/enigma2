from enigma import eDVBResourceManager, eDVBFrontendParametersSatellite, eDVBFrontendParametersTerrestrial, eTimer
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSelection, getConfigListEntry
from Components.NimManager import nimmanager, getConfigSatlist
from Components.Sources.FrontendStatus import FrontendStatus
from Components.SystemInfo import SystemInfo
from Components.TuneTest import Tuner
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.ScanSetup import ScanSetup, buildTerTransponder
from Screens.Screen import Screen # for services found class
from Screens.ServiceScan import ServiceScan
from Tools.Transponder import getChannelNumber, channel2frequency
from Tools.BoundFunction import boundFunction

try: # for reading the current transport stream (SatfinderExtra)
	from Plugins.SystemPlugins.AutoBouquetsMaker.scanner import dvbreader
	dvbreader_available = True
except ImportError:
	print("[Satfinder] import dvbreader not available")
	dvbreader_available = False

if dvbreader_available:
	from skin import parameters
	from Components.Sources.StaticText import StaticText
	from Components.ScrollLabel import ScrollLabel
	from Components.Label import Label
	from Tools.Hex2strColor import Hex2strColor
	import time
	import datetime
	import _thread as thread


class Satfinder(ScanSetup, ServiceScan):
	"""Inherits StaticText [key_red] and [key_green] properties from ScanSetup"""

	def __init__(self, session):
		self.initcomplete = False
		service = session and session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		self.frontendData = feinfo and feinfo.getAll(True)
		del feinfo
		del service

		self.typeOfTuningEntry = None
		self.systemEntry = None
		self.systemEntryATSC = None
		self.satfinderTunerEntry = None
		self.satEntry = None
		self.typeOfInputEntry = None
		self.DVB_TypeEntry = None
		self.systemEntryTerr = None
		self.preDefTransponderEntry = None
		self.preDefTransponderCableEntry = None
		self.preDefTransponderTerrEntry = None
		self.preDefTransponderAtscEntry = None
		self.frontend = None
		self.is_id_boolEntry = None
		self.t2mi_plp_id_boolEntry = None
		self.timer = eTimer()
		self.timer.callback.append(self.updateFrontendStatus)

		ScanSetup.__init__(self, session)
		self.setTitle(_("Signal finder"))
		self["Frontend"] = FrontendStatus(frontend_source=lambda: self.frontend, update_interval=100)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "InfobarMenuActions"],
		{
			"save": self.keyGoScan,
			"ok": self.keyGoScan,
			"cancel": self.keyCancel,
			"mainMenu": self.doCloseRecursive,
		}, -3)

		self.initcomplete = True
		self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		#self.session.nav.stopService()
		self.onClose.append(self.__onClose)
		self.onShow.append(self.prepareFrontend)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def prepareFrontend(self):
		self.frontend = None
		if not self.openFrontend():
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					from Screens.InfoBar import InfoBar
					InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)
		self.retune()

	def updateFrontendStatus(self):
		if self.frontend:
			dict = {}
			self.frontend.getFrontendStatus(dict)
			if dict["tuner_state"] == "FAILED" or dict["tuner_state"] == "LOSTLOCK":
				self.retune()
			else:
				self.timer.start(500, True)

	def __onClose(self):
		self.session.nav.playService(self.session.postScanService)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (
					self.typeOfTuningEntry,
					self.systemEntry,
					self.typeOfInputEntry,
					self.systemEntryATSC,
					self.DVB_TypeEntry,
					self.systemEntryTerr,
					self.satEntry
					):  # update screen and retune
			self.createSetup()
			self.retune()

		elif cur == self.satfinderTunerEntry: # switching tuners, update screen, get frontend, and retune (in prepareFrontend())
			self.feid = int(self.satfinder_scan_nims.value)
			self.createSetup()
			self.prepareFrontend()
			if self.frontend is None:
				msg = _("Tuner not available.")
				if self.session.nav.RecordTimer.isRecording():
					msg += _("\nRecording in progress.")
				self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)

		elif cur in (self.preDefTransponderEntry, self.preDefTransponderCableEntry, self.preDefTransponderTerrEntry, self.preDefTransponderAtscEntry): # retune only
			self.retune()
		elif cur == self.is_id_boolEntry:
			if self.is_id_boolEntry[1].value:
				self.scan_sat.is_id.value = 0 if self.is_id_memory < 0 else self.is_id_memory
				self.scan_sat.pls_mode.value = self.pls_mode_memory
				self.scan_sat.pls_code.value = self.pls_code_memory
			else:
				self.is_id_memory = self.scan_sat.is_id.value
				self.pls_mode_memory = self.scan_sat.pls_mode.value
				self.pls_code_memory = self.scan_sat.pls_code.value
				self.scan_sat.is_id.value = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
				self.scan_sat.pls_mode.value = eDVBFrontendParametersSatellite.PLS_Gold
				self.scan_sat.pls_code.value = eDVBFrontendParametersSatellite.PLS_Default_Gold_Code
			self.createSetup()
			self.retune()
		elif cur == self.t2mi_plp_id_boolEntry:
			if self.t2mi_plp_id_boolEntry[1].value:
				self.scan_sat.t2mi_plp_id.value = 0 if self.t2mi_plp_id_memory < 0 else self.t2mi_plp_id_memory
				self.scan_sat.t2mi_pid.value = self.t2mi_pid_memory
			else:
				self.t2mi_plp_id_memory = self.scan_sat.t2mi_plp_id.value
				self.t2mi_pid_memory = self.scan_sat.t2mi_pid.value
				self.scan_sat.t2mi_plp_id.value = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
				self.scan_sat.t2mi_pid.value = eDVBFrontendParametersSatellite.T2MI_Default_Pid
			self.createSetup()
			self.retune()

	def createSetup(self):
		self.list = []
		indent = "- "
		self.satfinderTunerEntry = getConfigListEntry(_("Tuner"), self.satfinder_scan_nims)
		self.list.append(self.satfinderTunerEntry)
		self.DVB_type = self.nim_type_dict[int(self.satfinder_scan_nims.value)]["selection"]
		self.DVB_TypeEntry = getConfigListEntry(_("DVB type"), self.DVB_type) # multitype?
		if len(self.nim_type_dict[int(self.satfinder_scan_nims.value)]["modes"]) > 1:
			self.list.append(self.DVB_TypeEntry)
		if self.DVB_type.value == "DVB-S":
			self.tuning_sat = self.scan_satselection[self.getSelectedSatIndex(self.feid)]
			self.satEntry = getConfigListEntry(_('Satellite'), self.tuning_sat)
			self.list.append(self.satEntry)
			self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
			if len(nimmanager.getTransponders(int(self.tuning_sat.value), self.feid)) < 1: # Only offer 'predefined transponder' if some transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)

			nim = nimmanager.nim_slots[self.feid]

			if self.tuning_type.value == "single_transponder":
				if nim.canBeCompatible("DVB-S2"):
					self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
					self.list.append(self.systemEntry)
				else:
					# downgrade to dvb-s, in case a -s2 config was active
					self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
				self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
				self.list.append(getConfigListEntry(_('Polarization'), self.scan_sat.polarization))
				self.list.append(getConfigListEntry(_('Symbol rate'), self.scan_sat.symbolrate))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
				if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
				elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
					self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
					self.list.append(self.modulationEntry)
					self.list.append(getConfigListEntry(_('Roll-off'), self.scan_sat.rolloff))
					self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
					if nim.isMultistream():
						self.is_id_boolEntry = getConfigListEntry(_('Transport Stream Type'), self.scan_sat.is_id_bool)
						self.list.append(self.is_id_boolEntry)
						if self.scan_sat.is_id_bool.value:
							self.list.append(getConfigListEntry(indent + _('Input Stream ID'), self.scan_sat.is_id))
							self.list.append(getConfigListEntry(indent + _('PLS Mode'), self.scan_sat.pls_mode))
							self.list.append(getConfigListEntry(indent + _('PLS Code'), self.scan_sat.pls_code))
					else:
						self.scan_sat.is_id.value = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
						self.scan_sat.pls_mode.value = eDVBFrontendParametersSatellite.PLS_Gold
						self.scan_sat.pls_code.value = eDVBFrontendParametersSatellite.PLS_Default_Gold_Code
					if nim.isT2MI():
						self.t2mi_plp_id_boolEntry = getConfigListEntry(_('T2MI PLP'), self.scan_sat.t2mi_plp_id_bool)
						self.list.append(self.t2mi_plp_id_boolEntry)
						if self.scan_sat.t2mi_plp_id_bool.value:
							self.list.append(getConfigListEntry(indent + _('T2MI PLP ID'), self.scan_sat.t2mi_plp_id))
							self.list.append(getConfigListEntry(indent + _('T2MI PID'), self.scan_sat.t2mi_pid))
					else:
						self.scan_sat.t2mi_plp_id.value = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
						self.scan_sat.t2mi_pid.value = eDVBFrontendParametersSatellite.T2MI_Default_Pid
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.updatePreDefTransponders()
				self.preDefTransponderEntry = getConfigListEntry(_("Transponder"), self.preDefTransponders)
				self.list.append(self.preDefTransponderEntry)
		elif self.DVB_type.value == "DVB-C":
			self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
			if config.Nims[self.feid].cable.scan_type.value != "provider" or len(nimmanager.getTranspondersCable(int(self.satfinder_scan_nims.value))) < 1: # only show 'predefined transponder' if in provider mode and transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency") + " kHz", self.scan_cab.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_cab.inversion))
				self.list.append(getConfigListEntry(_("Symbol rate"), self.scan_cab.symbolrate))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_cab.modulation))
				self.list.append(getConfigListEntry(_("FEC"), self.scan_cab.fec))
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedCabTranspondersList()
				self.preDefTransponderCableEntry = getConfigListEntry(_("Transponder"), self.CableTransponders)
				self.list.append(self.preDefTransponderCableEntry)
		elif self.DVB_type.value == "DVB-T":
			self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
			region = nimmanager.getTerrestrialDescription(int(self.satfinder_scan_nims.value))
			if len(nimmanager.getTranspondersTerrestrial(region)) < 1: # Only offer 'predefined transponder' if some transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				if nimmanager.nim_slots[int(self.satfinder_scan_nims.value)].canBeCompatible("DVB-T2"):
					self.systemEntryTerr = getConfigListEntry(_('System'), self.scan_ter.system)
					self.list.append(self.systemEntryTerr)
				else:
					self.scan_ter.system.value = eDVBFrontendParametersTerrestrial.System_DVB_T
				self.typeOfInputEntry = getConfigListEntry(_("Use frequency or channel"), self.scan_input_as)
				if self.ter_channel_input:
					self.list.append(self.typeOfInputEntry)
				else:
					self.scan_input_as.value = self.scan_input_as.choices[0]
				if self.ter_channel_input and self.scan_input_as.value == "channel":
					channel = getChannelNumber(self.scan_ter.frequency.floatint * 1000, self.ter_tnumber)
					if channel:
						self.scan_ter.channel.value = int(channel.replace("+", "").replace("-", ""))
					self.list.append(getConfigListEntry(_("Channel"), self.scan_ter.channel))
				else:
					prev_val = self.scan_ter.frequency.floatint
					self.scan_ter.frequency.floatint = channel2frequency(self.scan_ter.channel.value, self.ter_tnumber) // 1000
					if self.scan_ter.frequency.floatint == 474000:
						self.scan_ter.frequency.floatint = prev_val
					self.list.append(getConfigListEntry(_("Frequency") + " kHz"), self.scan_ter.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ter.inversion))
				self.list.append(getConfigListEntry(_("Bandwidth"), self.scan_ter.bandwidth))
				self.list.append(getConfigListEntry(_("Code rate HP"), self.scan_ter.fechigh))
				self.list.append(getConfigListEntry(_("Code rate LP"), self.scan_ter.feclow))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ter.modulation))
				self.list.append(getConfigListEntry(_("Transmission mode"), self.scan_ter.transmission))
				self.list.append(getConfigListEntry(_("Guard interval"), self.scan_ter.guard))
				self.list.append(getConfigListEntry(_("Hierarchy info"), self.scan_ter.hierarchy))
				if self.scan_ter.system.value == eDVBFrontendParametersTerrestrial.System_DVB_T2:
					self.list.append(getConfigListEntry(_('PLP ID'), self.scan_ter.plp_id))
			elif self.tuning_type.value == "predefined_transponder":
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedTerrTranspondersList()
				self.preDefTransponderTerrEntry = getConfigListEntry(_('Transponder'), self.TerrestrialTransponders)
				self.list.append(self.preDefTransponderTerrEntry)
		elif self.DVB_type.value == "ATSC":
			self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
			if len(nimmanager.getTranspondersATSC(int(self.satfinder_scan_nims.value))) < 1: # only show 'predefined transponder' if transponders exist
				self.tuning_type.value = "single_transponder"
			else:
				self.list.append(self.typeOfTuningEntry)
			if self.tuning_type.value == "single_transponder":
				self.systemEntryATSC = getConfigListEntry(_("System"), self.scan_ats.system)
				self.list.append(self.systemEntryATSC)
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_ats.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ats.inversion))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ats.modulation))
			elif self.tuning_type.value == "predefined_transponder":
				#FIXME add region
				self.scan_nims.value = self.satfinder_scan_nims.value
				self.predefinedATSCTranspondersList()
				self.preDefTransponderAtscEntry = getConfigListEntry(_('Transponder'), self.ATSCTransponders)
				self.list.append(self.preDefTransponderAtscEntry)
		self["config"].list = self.list

	def createConfig(self, foo):
		self.tuning_type = ConfigSelection(default="predefined_transponder", choices=[("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder"))])
		self.orbital_position = 192
		if self.frontendData and 'orbital_position' in self.frontendData:
			self.orbital_position = self.frontendData['orbital_position']
		ScanSetup.createConfig(self, self.frontendData)

		# The following are updated in self.newConfig(). Do not add here.
		# self.scan_sat.system, self.tuning_type, self.scan_input_as, self.scan_ats.system, self.DVB_type, self.scan_ter.system, self.satfinder_scan_nims, self.tuning_sat
		for x in (self.scan_sat.frequency,
			self.scan_sat.inversion, self.scan_sat.symbolrate,
			self.scan_sat.polarization, self.scan_sat.fec, self.scan_sat.pilot,
			self.scan_sat.fec_s2, self.scan_sat.fec, self.scan_sat.modulation,
			self.scan_sat.rolloff,
			self.scan_sat.is_id, self.scan_sat.pls_mode, self.scan_sat.pls_code,
			self.scan_sat.t2mi_plp_id, self.scan_sat.t2mi_pid,
			self.scan_ter.channel, self.scan_ter.frequency, self.scan_ter.inversion,
			self.scan_ter.bandwidth, self.scan_ter.fechigh, self.scan_ter.feclow,
			self.scan_ter.modulation, self.scan_ter.transmission,
			self.scan_ter.guard, self.scan_ter.hierarchy, self.scan_ter.plp_id,
			self.scan_cab.frequency, self.scan_cab.inversion, self.scan_cab.symbolrate,
			self.scan_cab.modulation, self.scan_cab.fec,
			self.scan_ats.frequency, self.scan_ats.modulation, self.scan_ats.inversion):
			x.addNotifier(self.retune, initial_call=False)

		satfinder_nim_list = []
		for n in nimmanager.nim_slots:
			if not any([n.isCompatible(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
				continue
			if n.config_mode in ("loopthrough", "satposdepends", "nothing"):
				continue
			if n.isCompatible("DVB-S") and n.config_mode in ("simple", "equal", "advanced") and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
			#if n.isCompatible("DVB-S") and n.isFBCTuner() and not n.isFBCRoot():
			#	continue

			satfinder_nim_list.append((str(n.slot), n.friendly_full_description))
		self.satfinder_scan_nims = ConfigSelection(choices=satfinder_nim_list)
		if self.frontendData is not None and len(satfinder_nim_list) > 0: # open the plugin with the currently active NIM as default
			active_nim = self.frontendData.get("tuner_number", int(satfinder_nim_list[0][0]))
			if not nimmanager.nim_slots[active_nim].isFBCLink():
				self.satfinder_scan_nims.setValue(str(active_nim))

		self.feid = int(self.satfinder_scan_nims.value)

		self.satList = []
		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
				self.scan_satselection.append(getConfigSatlist(self.orbital_position, self.satList[slot.slot]))
			else:
				self.satList.append(None)

		if self.frontendData:
			ttype = self.frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S" and self.predefinedTranspondersList(self.getSelectedSatIndex(self.feid)) is None and len(nimmanager.getTransponders(self.getSelectedSatIndex(self.feid), self.feid)) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "DVB-T" and self.predefinedTerrTranspondersList() is None and len(nimmanager.getTranspondersTerrestrial(nimmanager.getTerrestrialDescription(self.feid))) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "DVB-C" and self.predefinedCabTranspondersList() is None and len(nimmanager.getTranspondersCable(self.feid)) > 0:
				self.tuning_type.value = "single_transponder"
			elif ttype == "ATSC" and self.predefinedATSCTranspondersList() is None and len(nimmanager.getTranspondersATSC(self.feid)) > 0:
				self.tuning_type.value = "single_transponder"

	def getSelectedSatIndex(self, v):
		index = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] is None:
				none_cnt += 1
			if index == int(v):
				return index - none_cnt
			index += 1
		return -1

	def updatePreDefTransponders(self):
		ScanSetup.predefinedTranspondersList(self, self.tuning_sat.orbital_position)

	def retuneCab(self):
		if not self.initcomplete:
			return
		if self.tuning_type.value == "single_transponder":
			transponder = (
				self.scan_cab.frequency.floatint,
				self.scan_cab.symbolrate.value * 1000,
				self.scan_cab.modulation.value,
				self.scan_cab.fec.value,
				self.scan_cab.inversion.value
			)
			self.tuner.tuneCab(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTranspondersCable(int(self.satfinder_scan_nims.value))
			if len(tps) > self.CableTransponders.index:
				tp = tps[self.CableTransponders.index]
				# tp = 0 transponder type, 1 freq, 2 sym, 3 mod, 4 fec, 5 inv, 6 sys
				transponder = (tp[1], tp[2], tp[3], tp[4], tp[5])
				self.tuner.tuneCab(transponder)
				self.transponder = transponder

	def retuneTerr(self):
		if not self.initcomplete:
			return
		if self.scan_input_as.value == "channel":
			frequency = channel2frequency(self.scan_ter.channel.value, self.ter_tnumber)
		else:
			frequency = self.scan_ter.frequency.floatint * 1000
		if self.tuning_type.value == "single_transponder":
			transponder = [
				2, #TERRESTRIAL
				frequency,
				self.scan_ter.bandwidth.value,
				self.scan_ter.modulation.value,
				self.scan_ter.fechigh.value,
				self.scan_ter.feclow.value,
				self.scan_ter.guard.value,
				self.scan_ter.transmission.value,
				self.scan_ter.hierarchy.value,
				self.scan_ter.inversion.value,
				self.scan_ter.system.value,
				self.scan_ter.plp_id.value]
			self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			region = nimmanager.getTerrestrialDescription(int(self.satfinder_scan_nims.value))
			tps = nimmanager.getTranspondersTerrestrial(region)
			if len(tps) > self.TerrestrialTransponders.index:
				transponder = tps[self.TerrestrialTransponders.index]
				# frequency 1, inversion 9, bandwidth 2, fechigh 4, feclow 5, modulation 3, transmission 7, guard 6, hierarchy 8, system 10, plp_id 11
				self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
				self.transponder = transponder

	def retuneATSC(self):
		if not self.initcomplete:
			return
		if self.tuning_type.value == "single_transponder":
			transponder = (
				self.scan_ats.frequency.floatint * 1000,
				self.scan_ats.modulation.value,
				self.scan_ats.inversion.value,
				self.scan_ats.system.value,
			)
			self.tuner.tuneATSC(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTranspondersATSC(int(self.satfinder_scan_nims.value))
			if tps and len(tps) > self.ATSCTransponders.index:
				tp = tps[self.ATSCTransponders.index]
				transponder = (tp[1], tp[2], tp[3], tp[4])
				self.tuner.tuneATSC(transponder)
				self.transponder = transponder

	def retuneSat(self): #satellite
		if not self.tuning_sat.value:
			return
		satpos = int(self.tuning_sat.value)
		if self.tuning_type.value == "single_transponder":
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value
			transponder = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.value,
				fec,
				self.scan_sat.inversion.value,
				satpos,
				self.scan_sat.system.value,
				self.scan_sat.modulation.value,
				self.scan_sat.rolloff.value,
				self.scan_sat.pilot.value,
				self.scan_sat.is_id.value,
				self.scan_sat.pls_mode.value,
				self.scan_sat.pls_code.value,
				self.scan_sat.t2mi_plp_id.value,
				self.scan_sat.t2mi_pid.value)
			if self.initcomplete:
				self.tuner.tune(transponder)
			self.transponder = transponder
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTransponders(satpos, int(self.satfinder_scan_nims.value))
			if len(tps) > self.preDefTransponders.index:
				tp = tps[self.preDefTransponders.index]
				transponder = (tp[1] // 1000, tp[2] // 1000,
					tp[3], tp[4], 2, satpos, tp[5], tp[6], tp[8], tp[9], tp[10], tp[11], tp[12], tp[13], tp[14])
				if self.initcomplete:
					self.tuner.tune(transponder)
				self.transponder = transponder

	def retune(self, configElement=None):
		if self.DVB_type.value == "DVB-S":
			self.retuneSat()
		elif self.DVB_type.value == "DVB-T":
			self.retuneTerr()
		elif self.DVB_type.value == "DVB-C":
			self.retuneCab()
		elif self.DVB_type.value == "ATSC":
			self.retuneATSC()
		self.timer.start(500, True)

	def keyGoScan(self):
		self.frontend = None
		if self.raw_channel:
			del(self.raw_channel)
		tlist = []
		if self.DVB_type.value == "DVB-S":
			self.addSatTransponder(tlist,
				self.transponder[0],  # frequency
				self.transponder[1],  # sr
				self.transponder[2],  # pol
				self.transponder[3],  # fec
				self.transponder[4],  # inversion
				self.tuning_sat.orbital_position,
				self.transponder[6],  # system
				self.transponder[7],  # modulation
				self.transponder[8],  # rolloff
				self.transponder[9],  # pilot
				self.transponder[10], # input stream id
				self.transponder[11], # pls mode
				self.transponder[12], # pls code
				self.transponder[13], # t2mi_plp_id
				self.transponder[14]  # t2mi_pid
			)
		elif self.DVB_type.value == "DVB-T":
			parm = buildTerTransponder(
				self.transponder[1],  # frequency
				self.transponder[9],  # inversion
				self.transponder[2],  # bandwidth
				self.transponder[4],  # fechigh
				self.transponder[5],  # feclow
				self.transponder[3],  # modulation
				self.transponder[7],  # transmission
				self.transponder[6],  # guard
				self.transponder[8],  # hierarchy
				self.transponder[10], # system
				self.transponder[11]  # plp_id
			)
			tlist.append(parm)
		elif self.DVB_type.value == "DVB-C":
			self.addCabTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # sr
				self.transponder[2], # modulation
				self.transponder[3], # fec_inner
				self.transponder[4]  # inversion
			)
		elif self.DVB_type.value == "ATSC":
			self.addATSCTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # modulation
				self.transponder[2], # inversion
				self.transponder[3]  # system
			)
		self.startScan(tlist, self.feid)

	def startScan(self, tlist, feid):
		flags = 0
		networkid = 0
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def startScanCallback(self, answer=None):
		if answer:
			self.doCloseRecursive()

	def keyCancel(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(False)

	def doCloseRecursive(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(True)


class SatfinderExtra(Satfinder):
	# This class requires AutoBouquetsMaker to be installed.
	def __init__(self, session):
		Satfinder.__init__(self, session)
		self.skinName = ["Satfinder"]

		self["key_yellow"] = StaticText("")

		self["actions2"] = ActionMap(["ColorActions"],
		{
			"yellow": self.keyReadServices,
		}, -3)
		self["actions2"].setEnabled(False)

		# DVB stream info
		self.serviceList = []
		self["tsid"] = StaticText("")
		self["onid"] = StaticText("")
		self["pos"] = StaticText("")

	def retune(self, configElement=None):
		Satfinder.retune(self)
		self.dvb_read_stream()

	def openFrontend(self):
		if Satfinder.openFrontend(self):
			self.demux = self.raw_channel.reserveDemux() # used for keyReadServices()
			return True
		return False

	def prepareFrontend(self):
		self.demux = -1 # used for keyReadServices()
		Satfinder.prepareFrontend(self)

	def dvb_read_stream(self):
		print("[satfinder][dvb_read_stream] starting")
		thread.start_new_thread(self.getCurrentTsidOnid, (True,))

	def getCurrentTsidOnid(self, from_retune=False):
		self.currentProcess = currentProcess = datetime.datetime.now()
		self["tsid"].setText("")
		self["onid"].setText("")
		self["pos"].setText("") #(self.DVB_type.value)
		self["key_yellow"].setText("")
		self["actions2"].setEnabled(False)
		self.serviceList = []

		if not dvbreader_available or self.frontend is None or self.demux < 0:
			return

		if from_retune: # give the tuner a chance to retune or we will be reading the old stream
			time.sleep(1.0)

		if not self.tunerLock() and not self.waitTunerLock(currentProcess): # dont even try to read the transport stream if tuner is not locked
			return

		thread.start_new_thread(self.monitorTunerLock, (currentProcess,)) # if tuner loses lock we start again from scratch

		adapter = 0
		demuxer_device = "/dev/dvb/adapter%d/demux%d" % (adapter, self.demux)

		sdt_pid = 0x11
		sdt_current_table_id = 0x42
		mask = 0xff
		tsidOnidTimeout = 60 # maximum time allowed to read the service descriptor table (seconds)
		self.tsid = None
		self.onid = None

		sdt_current_version_number = -1
		sdt_current_sections_read = []
		sdt_current_sections_count = 0
		sdt_current_content = []
		sdt_current_completed = False

		fd = dvbreader.open(demuxer_device, sdt_pid, sdt_current_table_id, mask, self.feid)
		if fd < 0:
			print("[Satfinder][getCurrentTsidOnid] Cannot open the demuxer")
			return None

		timeout = datetime.datetime.now()
		timeout += datetime.timedelta(0, tsidOnidTimeout)

		while True:
			if datetime.datetime.now() > timeout:
				print("[Satfinder][getCurrentTsidOnid] Timed out")
				break

			if self.currentProcess != currentProcess or not self.tunerLock():
				dvbreader.close(fd)
				return

			section = dvbreader.read_sdt(fd, sdt_current_table_id, 0x00)
			if section is None:
				time.sleep(0.1)	# no data.. so we wait a bit
				continue

			if section["header"]["table_id"] == sdt_current_table_id and not sdt_current_completed:
				if section["header"]["version_number"] != sdt_current_version_number:
					sdt_current_version_number = section["header"]["version_number"]
					sdt_current_sections_read = []
					sdt_current_sections_count = section["header"]["last_section_number"] + 1
					sdt_current_content = []

				if section["header"]["section_number"] not in sdt_current_sections_read:
					sdt_current_sections_read.append(section["header"]["section_number"])
					sdt_current_content += section["content"]
					if self.tsid is None or self.onid is None: # write first find straight to the screen
						self.tsid = section["header"]["transport_stream_id"]
						self.onid = section["header"]["original_network_id"]
						self["tsid"].setText("%d" % (section["header"]["transport_stream_id"]))
						self["onid"].setText("%d" % (section["header"]["original_network_id"]))
						print("[Satfinder][getCurrentTsidOnid] tsid %d, onid %d" % (section["header"]["transport_stream_id"], section["header"]["original_network_id"]))

					if len(sdt_current_sections_read) == sdt_current_sections_count:
						sdt_current_completed = True

			if sdt_current_completed:
				break

		dvbreader.close(fd)

		if not sdt_current_content:
			print("[Satfinder][getCurrentTsidOnid] no services found on transponder")
			return

		for i in range(len(sdt_current_content)):
			if not sdt_current_content[i]["service_name"]: # if service name is empty use SID
				sdt_current_content[i]["service_name"] = "0x%x" % sdt_current_content[i]["service_id"]

		self.serviceList = sorted(sdt_current_content, key=lambda listItem: listItem["service_name"])
		if self.serviceList:
			self["key_yellow"].setText(_("Service list"))
			self["actions2"].setEnabled(True)

		self.getOrbPosFromNit(currentProcess)

	def getOrbPosFromNit(self, currentProcess):
		if self.DVB_type.value != "DVB-S" or not dvbreader_available or self.frontend is None or self.demux < 0:
			return

		adapter = 0
		demuxer_device = "/dev/dvb/adapter%d/demux%d" % (adapter, self.demux)

		nit_current_pid = 0x10
		nit_current_table_id = 0x40
		nit_other_table_id = 0x00 # don't read other table
		if nit_other_table_id == 0x00:
			mask = 0xff
		else:
			mask = nit_current_table_id ^ nit_other_table_id ^ 0xff
		nit_current_timeout = 60 # maximum time allowed to read the network information table (seconds)

		nit_current_version_number = -1
		nit_current_sections_read = []
		nit_current_sections_count = 0
		nit_current_content = []
		nit_current_completed = False

		fd = dvbreader.open(demuxer_device, nit_current_pid, nit_current_table_id, mask, self.feid)
		if fd < 0:
			print("[Satfinder][getOrbPosFromNit] Cannot open the demuxer")
			return

		timeout = datetime.datetime.now()
		timeout += datetime.timedelta(0, nit_current_timeout)

		while True:
			if datetime.datetime.now() > timeout:
				print("[Satfinder][getOrbPosFromNit] Timed out reading NIT")
				break

			if self.currentProcess != currentProcess or not self.tunerLock():
				dvbreader.close(fd)
				return

			section = dvbreader.read_nit(fd, nit_current_table_id, nit_other_table_id)
			if section is None:
				time.sleep(0.1)	# no data.. so we wait a bit
				continue

			if section["header"]["table_id"] == nit_current_table_id and not nit_current_completed:
				if section["header"]["version_number"] != nit_current_version_number:
					nit_current_version_number = section["header"]["version_number"]
					nit_current_sections_read = []
					nit_current_sections_count = section["header"]["last_section_number"] + 1
					nit_current_content = []

				if section["header"]["section_number"] not in nit_current_sections_read:
					nit_current_sections_read.append(section["header"]["section_number"])
					nit_current_content += section["content"]

					if len(nit_current_sections_read) == nit_current_sections_count:
						nit_current_completed = True

			if nit_current_completed:
				break

		dvbreader.close(fd)

		if not nit_current_content:
			print("[Satfinder][getOrbPosFromNit] current transponder not found")
			return

		transponders = [t for t in nit_current_content if "descriptor_tag" in t and t["descriptor_tag"] == 0x43 and t["original_network_id"] == self.onid and t["transport_stream_id"] == self.tsid]
		transponders2 = [t for t in nit_current_content if "descriptor_tag" in t and t["descriptor_tag"] == 0x43 and t["transport_stream_id"] == self.tsid]
		if transponders and "orbital_position" in transponders[0]:
			orb_pos = self.getOrbitalPosition(transponders[0]["orbital_position"], transponders[0]["west_east_flag"])
			self["pos"].setText(_("%s") % orb_pos)
			print("[satfinder][getOrbPosFromNit] orb_pos", orb_pos)
		elif transponders2 and "orbital_position" in transponders2[0]:
			orb_pos = self.getOrbitalPosition(transponders2[0]["orbital_position"], transponders2[0]["west_east_flag"])
			self["pos"].setText(_("%s?") % orb_pos)
			print("[satfinder][getOrbPosFromNit] orb_pos tentative, tsid match, onid mismatch between NIT and SDT", orb_pos)
		else:
			print("[satfinder][getOrbPosFromNit] no orbital position found")

	def getOrbitalPosition(self, bcd, w_e_flag=1):
		# 4 bit BCD (binary coded decimal)
		# w_e_flag, 0 == west, 1 == east
		op = 0
		bits = 4
		for i in range(bits):
			op += ((bcd >> 4 * i) & 0x0F) * 10**i
		if op > 1800:
			op = (3600 - op) * -1
		if w_e_flag == 0:
			op *= -1
		return "%0.1f%s" % (abs(op) / 10., "W" if op < 0 else "E")

	def tunerLock(self):
		frontendStatus = {}
		self.frontend.getFrontendStatus(frontendStatus)
		return frontendStatus["tuner_state"] == "LOCKED"

	def waitTunerLock(self, currentProcess):
		lock_timeout = 120

		timeout = datetime.datetime.now()
		timeout += datetime.timedelta(0, lock_timeout)

		while True:
			if datetime.datetime.now() > timeout:
				print("[Satfinder][waitTunerLock] tuner lock timeout reached, seconds:", lock_timeout)
				return False

			if self.currentProcess != currentProcess:
				return False

			frontendStatus = {}
			self.frontend.getFrontendStatus(frontendStatus)
			if frontendStatus["tuner_state"] == "FAILED":
				print("[Satfinder][waitTunerLock] TUNING FAILED FATAL") # enigma2 cpp code has given up trying
				return False

			if frontendStatus["tuner_state"] != "LOCKED":
				time.sleep(0.25)
				continue

			return True

	def monitorTunerLock(self, currentProcess):
		while True:
			if self.currentProcess != currentProcess:
				return
			frontendStatus = {}
			self.frontend.getFrontendStatus(frontendStatus)
			if frontendStatus["tuner_state"] != "LOCKED":
				print("[monitorTunerLock] starting again from scratch")
				self.getCurrentTsidOnid(False) # if tuner lock fails start again from beginning
				return
			time.sleep(1.0)

	def keyReadServices(self):
		if not self.serviceList:
			return
		tv = [1, 17, 22, 25, 31]
		radio = [2, 10]
		colors = parameters.get("SatfinderExtraColors", (0x0088FF88, 0x00FF8888, 0x00FFFF00, 0x007799FF, 0x00FFFFFF)) # "FTA", "encrypted", "data", "radio", "default" colors
		fta_color = Hex2strColor(colors[0])
		encrypted_color = Hex2strColor(colors[1])
		data_color = Hex2strColor(colors[2])
		radio_color = Hex2strColor(colors[3])
		default_color = Hex2strColor(colors[4])
		out = []
		legend = "%s%s%s:  %s%s%s  %s%s%s  %s%s%s  %s%s%s\n\n%s%s%s\n" % (default_color, _("Key"), default_color, fta_color, _("FTA TV"), default_color, encrypted_color, _("Encrypted TV"), default_color, radio_color, _("Radio"), default_color, data_color, _("Other"), default_color, default_color, _("Channels"), default_color)
#		out.append("%s%s%s:" % (default_color, _("Channels"), default_color))
		for service in self.serviceList:
			fta = "free_ca" in service and service["free_ca"] == 0
			if service["service_type"] in radio:
				color = radio_color
			elif service["service_type"] not in tv: # data/interactive/etc
				color = data_color
			elif fta:
				color = fta_color
			else:
				color = encrypted_color
			out.append("- %s%s (%s)%s" % (color, service["service_name"], service["service_id"], default_color))

		self.session.open(ServicesFound, "\n".join(out), legend)


class ServicesFound(Screen):
	skin = """
		<screen name="ServicesFound" position="center,center" size="600,570">
			<widget name="legend" position="0,0" size="590,80" zPosition="10" font="Regular;21" transparent="1"/>
			<widget name="servicesfound" position="0,85" size="590,425" zPosition="10" font="Regular;21" transparent="1"/>
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,525" size="140,40" alphatest="on" />
			<widget render="Label" source="key_red" position="10,500" zPosition="1" size="140,25" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
		</screen>"""

	def __init__(self, session, text, legend):
		Screen.__init__(self, session)
		self.setTitle(_("Information"))

		self["key_red"] = StaticText(_("Close"))
		self["legend"] = Label(legend)
		self["servicesfound"] = ScrollLabel(text)

		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"back": self.close,
			"red": self.close,
			"up": self.pageUp,
			"down": self.pageDown,
			"left": self.pageUp,
			"right": self.pageDown,
		}, -2)

	def pageUp(self):
		self["servicesfound"].pageUp()

	def pageDown(self):
		self["servicesfound"].pageDown()


def SatfinderCallback(close, answer):
	if close and answer:
		close(True)


def SatfinderMain(session, close=None, **kwargs):
	nims = nimmanager.nim_slots
	nimList = []
	for n in nims:
		if not any([n.isCompatible(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
			continue
		if n.config_mode in ("loopthrough", "satposdepends", "nothing"):
			continue
		if n.isCompatible("DVB-S") and n.config_mode in ("advanced", "equal", "simple") and len(nimmanager.getSatListForNim(n.slot)) < 1 and len(n.getTunerTypesEnabled()) < 2:
			continue
		nimList.append(n)

	if len(nimList) == 0:
		session.open(MessageBox, _("No satellite, terrestrial or cable tuner is configured. Please check your tuner setup."), MessageBox.TYPE_ERROR)
	else:
		if dvbreader_available:
			session.openWithCallback(boundFunction(SatfinderCallback, close), SatfinderExtra)
		else:
			session.openWithCallback(boundFunction(SatfinderCallback, close), Satfinder)


def SatfinderStart(menuid, **kwargs):
	if menuid == "scan" and nimmanager.somethingConnected():
		return [(_("Signal finder"), SatfinderMain, "satfinder", None)]
	else:
		return []


def Plugins(**kwargs):
	if any([nimmanager.hasNimType(x) for x in ("DVB-S", "DVB-T", "DVB-C", "ATSC")]):
		return PluginDescriptor(name=_("Signal finder"), description=_("Helps setting up your antenna"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=SatfinderStart)
	else:
		return []
