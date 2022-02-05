from enigma import eDVBDB, getLinkedSlotID, eDVBResourceManager
from Screens.Screen import Screen
from Components.SystemInfo import SystemInfo
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager
from Components.Button import Button
from Components.Label import Label
from Components.UsageConfig import showrotorpositionChoicesUpdate, preferredTunerChoicesUpdate
from Components.SelectionList import SelectionList, SelectionEntryComponent
from Components.config import getConfigListEntry, config, ConfigNothing, ConfigYesNo, configfile, ConfigBoolean, ConfigSelection
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.ServiceStopScreen import ServiceStopScreen
from Screens.AutoDiseqc import AutoDiseqc
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists

from time import mktime, localtime, time
from datetime import datetime


class NimSetup(ConfigListScreen, ServiceStopScreen, Screen):
	def createSimpleSetup(self, list, mode):
		nim = self.nimConfig

		if mode == "single":
			self.singleSatEntry = getConfigListEntry(self.indent % _("Satellite"), nim.diseqcA, _("Select the satellite your dish receives from. If you are unsure select 'automatic' and the receiver will attempt to determine this for you."))
			list.append(self.singleSatEntry)
			if nim.diseqcA.value in ("360", "560"):
				list.append(getConfigListEntry(self.indent % _("Use circular LNB"), nim.simpleDiSEqCSetCircularLNB, _("If you are using a Circular polarised LNB select 'yes', otherwise select 'no'.")))
			list.append(getConfigListEntry(self.indent % _("Send DiSEqC"), nim.simpleSingleSendDiSEqC, _("Only select 'yes' if you are using a multiswich that requires a DiSEqC Port-A command signal. For all other setups select 'no'.")))
		else:
			list.append(getConfigListEntry(self.indent % _("Port A"), nim.diseqcA, _("Select the satellite which is connected to Port-A of your switch. If you are unsure select 'automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'nothing connected'.")))

		if mode in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
			list.append(getConfigListEntry(self.indent % _("Port B"), nim.diseqcB, _("Select the satellite which is connected to Port-B of your switch. If you are unsure select 'automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'nothing connected'.")))
			if mode == "diseqc_a_b_c_d":
				list.append(getConfigListEntry(self.indent % _("Port C"), nim.diseqcC, _("Select the satellite which is connected to Port-C of your switch. If you are unsure select 'automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'nothing connected'.")))
				list.append(getConfigListEntry(self.indent % _("Port D"), nim.diseqcD, _("Select the satellite which is connected to Port-D of your switch. If you are unsure select 'automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'nothing connected'.")))
			if mode != "toneburst_a_b":
				list.append(getConfigListEntry(self.indent % _("Set voltage and 22KHz"), nim.simpleDiSEqCSetVoltageTone, _("Leave this set to 'yes' unless you fully understand why you are adjusting it.")))
				list.append(getConfigListEntry(self.indent % _("Send DiSEqC only on satellite change"), nim.simpleDiSEqCOnlyOnSatChange, _("Select 'yes' to only send the DiSEqC command when changing from one satellite to another, or select 'no' for the DiSEqC command to be resent on every zap.")))

	def createPositionerSetup(self, list):
		nim = self.nimConfig
		if nim.diseqcMode.value == "positioner_select":
			self.selectSatsEntry = getConfigListEntry(self.indent % _("Press OK to select satellites"), self.nimConfig.pressOKtoList, _("Press OK to select a group of satellites to configure in one block."))
			list.append(self.selectSatsEntry)
		list.append(getConfigListEntry(self.indent % _("Longitude"), nim.longitude, _("Enter your current longitude. This is the number of degrees you are from zero meridian as a decimal.")))
		list.append(getConfigListEntry(" ", nim.longitudeOrientation, _("Enter if you are in the east or west hemisphere.")))
		list.append(getConfigListEntry(self.indent % _("Latitude"), nim.latitude, _("Enter your current latitude. This is the number of degrees you are from the equator as a decimal.")))
		list.append(getConfigListEntry(" ", nim.latitudeOrientation, _("Enter if you are north or south of the equator.")))
		if SystemInfo["CanMeasureFrontendInputPower"]:
			self.advancedPowerMeasurement = getConfigListEntry(self.indent % _("Use power measurement"), nim.powerMeasurement, _("Power management. Consult your receiver's manual for more information."))
			list.append(self.advancedPowerMeasurement)
			if nim.powerMeasurement.value:
				list.append(getConfigListEntry(self.indent % _("Power threshold in mA"), nim.powerThreshold, _("Power threshold. Consult your receiver's manual for more information.")))
				self.turningSpeed = getConfigListEntry(self.indent % _("Rotor turning speed"), nim.turningSpeed, _("Select how quickly the dish should move between satellites."))
				list.append(self.turningSpeed)
				if nim.turningSpeed.value == "fast epoch":
					self.turnFastEpochBegin = getConfigListEntry(self.indent % _("Begin time"), nim.fastTurningBegin, _("Only move the dish quickly after this hour."))
					self.turnFastEpochEnd = getConfigListEntry(self.indent % _("End time"), nim.fastTurningEnd, _("Only move the dish quickly before this hour."))
					list.append(self.turnFastEpochBegin)
					list.append(self.turnFastEpochEnd)
		else:
			if nim.powerMeasurement.value:
				nim.powerMeasurement.value = False
				nim.powerMeasurement.save()
		if not hasattr(self, 'additionalMotorOptions'):
			self.additionalMotorOptions = ConfigBoolean(default=any([x.value != x.default for x in (nim.turningspeedH, nim.turningspeedV, nim.tuningstepsize, nim.rotorPositions)]), descriptions={False: _("Show sub-menu"), True: _("Hide sub-menu")})
		self.showAdditionalMotorOptions = getConfigListEntry(self.indent % _("Extra motor options"), self.additionalMotorOptions, _("Additional motor options allow you to enter details from your motor's spec sheet so enigma can work out how long it will take to move the dish from one satellite to another satellite."))
		self.list.append(self.showAdditionalMotorOptions)
		if self.additionalMotorOptions.value:
			self.list.append(getConfigListEntry(self.indent % ("   %s [%s/sec]" % (_("Horizontal turning speed"), chr(176))), nim.turningspeedH, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry(self.indent % ("   %s [%s/sec]" % (_("Vertical turning speed"), chr(176))), nim.turningspeedV, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry(self.indent % ("   %s [%s]" % (_("Turning step size"), chr(176))), nim.tuningstepsize, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry(self.indent % ("   %s" % _("Max memory positions")), nim.rotorPositions, _("Consult your motor's spec sheet for this information, or leave the default setting.")))

	def adaptConfigModeChoices(self):
		if self.nim.isCompatible("DVB-S") and not self.nim.isFBCLink():
			#redefine configMode choices with only the possible/required options.
			#We have to pre-define them here as here all tuner configs are known
			config_mode_choices = {"simple": _("Simple"), "advanced": _("Advanced")}
			if not self.nim.multi_type:
				config_mode_choices["nothing"] = _("Disabled")
			if nimmanager.canEqualTo(self.slotid):
				config_mode_choices["equal"] = _("Equal to")
			if nimmanager.canDependOn(self.slotid):
				config_mode_choices["satposdepends"] = _("Second cable of motorized LNB")
			if nimmanager.canConnectTo(self.slotid):
				config_mode_choices["loopthrough"] = _("Loop through from")
			self.nimConfig.configMode.setChoices(config_mode_choices, "simple")

	def createSetup(self):
		self.adaptConfigModeChoices()
		self.list = []

		self.multiType = self.configMode = self.diseqcModeEntry = self.advancedSatsEntry = self.advancedLnbsEntry = self.advancedDiseqcMode = self.advancedUsalsEntry = self.advancedLof =\
		self.advancedPowerMeasurement = self.turningSpeed = self.turnFastEpochBegin = self.turnFastEpochEnd = self.toneburst = self.committedDiseqcCommand = self.uncommittedDiseqcCommand =\
		self.commandOrder = self.cableScanType = self.cableConfigScanDetails = self.advancedUnicable = self.advancedFormat = self.advancedPosition = self.advancedType = self.advancedManufacturer =\
		self.advancedSCR = self.advancedConnected = self.showAdditionalMotorOptions = self.selectSatsEntry = self.advancedSelectSatsEntry = self.singleSatEntry = self.toneamplitude = self.scpc =\
		self.t2mirawmode = self.forcelnbpower = self.forcetoneburst = self.terrestrialRegionsEntry = self.cableRegionsEntry = self.configModeDVBS = self.configModeDVBC = self.configModeDVBT =\
		self.configModeATSC = self.externallyPowered = None

		self.have_advanced = False
		self.indent = "  %s" if self.nim.isCombined() else "%s"
		if not hasattr(self, "terrestrialCountriesEntry"):
			self.terrestrialCountriesEntry = None
		if not hasattr(self, "cableCountriesEntry"):
			self.cableCountriesEntry = None

		if self.nim.isMultiType():
			self.multiType = getConfigListEntry(_("Tuner type"), self.nimConfig.multiType, _("This is a multitype tuner. Available options depend on the hardware."))
			self.list.append(self.multiType)
			if self.nimConfig.multiType.value == "nothing":
				self.nimConfig.configMode.value = "nothing"
			elif self.nim.isCompatible("DVB-S"):
				if self.nimConfig.configMode.value in ("nothing", "enabled"):
					self.nimConfig.configMode.value = "simple"
			else:
				self.nimConfig.configMode.value = "enabled"

		if self.nim.isCompatible("DVB-S") or (self.nim.isCombined() and self.nim.canBeCompatible("DVB-S")):
			if self.nim.isCombined():
				self.configModeDVBS = getConfigListEntry(_("Configure DVB-S"), self.nimConfig.configModeDVBS, _("Select 'Yes' when you want to configure this tuner for DVB-S"))
				self.list.append(self.configModeDVBS)
			if (not self.nim.isMultiType() or self.nimConfig.configMode.value != "nothing") and (not self.nim.isCombined() or self.nimConfig.configModeDVBS.value):
				self.configMode = getConfigListEntry(self.indent % _("Configuration mode"), self.nimConfig.configMode, _("Select 'FBC SCR' if this tuner will connect to a SCR (Unicable/JESS) device. For all other setups select 'FBC automatic'.") if self.nim.isFBCLink() else _("Configure this tuner using simple or advanced options, or loop it through to another tuner, or copy a configuration from another tuner, or disable it."))
				self.list.append(self.configMode)
				warning_text = _(" Warning: the selected tuner should not use SCR Unicable type for LNBs because each tuner need a own SCR number.")
				if self.nimConfig.configMode.value == "simple":			#simple setup
					self.diseqcModeEntry = getConfigListEntry(self.indent % pgettext("Satellite configuration mode", "Mode"), self.nimConfig.diseqcMode, _("Select how the satellite dish is set up. i.e. fixed dish, single LNB, DiSEqC switch, positioner, etc."))
					self.list.append(self.diseqcModeEntry)
					if self.nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
						self.createSimpleSetup(self.list, self.nimConfig.diseqcMode.value)
					if self.nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
						self.createPositionerSetup(self.list)
				elif self.nimConfig.configMode.value == "equal":
					self.nimConfig.connectedTo.setChoices([((str(id), nimmanager.getNimDescription(id))) for id in nimmanager.canEqualTo(self.slotid)])
					self.list.append(getConfigListEntry(self.indent % _("Tuner"), self.nimConfig.connectedTo, _("This setting allows the tuner configuration to be a duplication of how another tuner is already configured.") + warning_text))
				elif self.nimConfig.configMode.value == "satposdepends":
					self.nimConfig.connectedTo.setChoices([((str(id), nimmanager.getNimDescription(id))) for id in nimmanager.canDependOn(self.slotid)])
					self.list.append(getConfigListEntry(self.indent % _("Tuner"), self.nimConfig.connectedTo, _("Select the tuner that controls the motorised dish.") + warning_text))
				elif self.nimConfig.configMode.value == "loopthrough":
					self.nimConfig.connectedTo.setChoices([((str(id), nimmanager.getNimDescription(id))) for id in nimmanager.canConnectTo(self.slotid)])
					self.list.append(getConfigListEntry(self.indent % _("Connected to"), self.nimConfig.connectedTo, _("Select the tuner that this loopthrough depends on.") + warning_text))
				elif self.nimConfig.configMode.value == "nothing":
					pass
				elif self.nimConfig.configMode.value == "advanced":
					advanced_setchoices = False
					advanced_satposdepends_satlist_choices = ("3607", _("Additional cable of motorized LNB"))
					advanced_satlist_choices = self.nimConfig.advanced.sats.choices.choices[:]
					if self.nim.isFBCLink() and ("3602", _('All satellites 2 (USALS)')) in advanced_satlist_choices:
						advanced_satlist_choices = [(str(orbpos), desc) for (orbpos, desc, flags) in nimmanager.satList[:]]
						advanced_setchoices = True
					candependonable = nimmanager.canDependOn(self.slotid, advanced_satposdepends=self.nim.isFBCLink() and "fbc" or "all")
					if candependonable:
						if advanced_satposdepends_satlist_choices not in advanced_satlist_choices:
							advanced_satlist_choices.append(advanced_satposdepends_satlist_choices)
							advanced_setchoices = True
					elif advanced_satposdepends_satlist_choices in advanced_satlist_choices:
						advanced_satlist_choices.remove(advanced_satposdepends_satlist_choices)
						advanced_setchoices = True
					if advanced_setchoices:
						saved_value = self.nimConfig.advanced.sats.saved_value
						default = saved_value or self.nimConfig.advanced.sats.value
						if not candependonable and (saved_value is not None and saved_value == "3607" or self.nimConfig.advanced.sats.value == "3607"):
							default = saved_value = None
						self.nimConfig.advanced.sats.setChoices(advanced_satlist_choices, default=default)
						if saved_value is not None:
							self.nimConfig.advanced.sats.value = saved_value
						self.nimConfig.advanced.sats.save_forced = True
					self.advancedSatsEntry = getConfigListEntry(self.indent % _("Satellite"), self.nimConfig.advanced.sats, _("Select the satellite you want to configure. Once that satellite is configured you can select and configure other satellites that will be accessed using this same tuner."))
					self.list.append(self.advancedSatsEntry)
					current_config_sats = self.nimConfig.advanced.sats.value
					if current_config_sats == "3607":
						self.nimConfig.connectedTo.setChoices([((str(id), nimmanager.getNimDescription(id))) for id in candependonable])
						self.list.append(getConfigListEntry(self.indent % _("Tuner"), self.nimConfig.connectedTo, _("Select the tuner that controls the motorised dish.")))
					if current_config_sats in ("3605", "3606", "3607"):
						if current_config_sats != "3607":
							self.advancedSelectSatsEntry = getConfigListEntry(self.indent % _("Press OK to select satellites"), self.nimConfig.pressOKtoList, _("Selecting this option allows you to configure a group of satellites in one block."))
							self.list.append(self.advancedSelectSatsEntry)
						self.fillListWithAdvancedSatEntrys(self.nimConfig.advanced.sat[int(current_config_sats)])
					else:
						cur_orb_pos = self.nimConfig.advanced.sats.orbital_position
						if cur_orb_pos is not None:
							if cur_orb_pos not in self.nimConfig.advanced.sat.keys():
								cur_orb_pos = next(iter(self.nimConfig.advanced.sat)) # get first key
							self.fillListWithAdvancedSatEntrys(self.nimConfig.advanced.sat[cur_orb_pos])
					self.have_advanced = True
				if self.nimConfig.configMode.value != "nothing" and config.usage.setup_level.index >= 2:
					if fileExists("/proc/stb/frontend/%d/tone_amplitude" % self.nim.slot):
						self.toneamplitude = getConfigListEntry(self.indent % _("Tone amplitude"), self.nimConfig.toneAmplitude, _("Your receiver can use tone amplitude. Consult your receiver's manual for more information."))
						self.list.append(self.toneamplitude)
					if fileExists("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % self.nim.slot):
						self.scpc = getConfigListEntry(self.indent % _("SCPC optimized search range"), self.nimConfig.scpcSearchRange, _("Your receiver can use SCPC optimized search range. Consult your receiver's manual for more information."))
						self.list.append(self.scpc)
					if fileExists("/proc/stb/frontend/%d/t2mirawmode" % self.nim.slot):
						self.t2mirawmode = getConfigListEntry(self.indent % _("T2MI RAW Mode"), self.nimConfig.t2miRawMode, _("With T2MI RAW mode disabled (default) we can use single T2MI PLP de-encapsulation. With T2MI RAW mode enabled we can use astra-sm to analyze T2MI"))
						self.list.append(self.t2mirawmode)
		if self.nim.isCompatible("DVB-C") or (self.nim.isCombined() and self.nim.canBeCompatible("DVB-C")):
			if self.nim.isCombined():
				self.configModeDVBC = getConfigListEntry(_("Configure DVB-C"), self.nimConfig.configModeDVBC, _("Select 'Yes' when you want to configure this tuner for DVB-C"))
				self.list.append(self.configModeDVBC)
			elif not self.nim.isMultiType():
				warning_text = ""
				if "Vuplus DVB-C NIM(BCM3148)" in self.nim.description and self.nim.isFBCRoot() and self.nim.is_fbc[2] != 1:
					warning_text = _("Warning: FBC-C V1 tuner should be connected to the first slot to work correctly. Otherwise, only 2 out of 8 demodulators will be available when connected in the second slot. ")
				self.configMode = getConfigListEntry(self.indent % _("Configuration mode"), self.nimConfig.configMode, warning_text + _("Select 'enabled' if this tuner has a signal cable connected, otherwise select 'nothing connected'."))
				self.list.append(self.configMode)
			if self.nimConfig.configModeDVBC.value if self.nim.isCombined() else self.nimConfig.configMode.value != "nothing":
				self.list.append(getConfigListEntry(self.indent % _("Network ID"), self.nimConfig.cable.scan_networkid, _("This setting depends on your cable provider and location. If you don't know the correct setting refer to the menu in the official cable receiver, or get it from your cable provider, or seek help via internet forum.")))
				self.cableScanType = getConfigListEntry(self.indent % _("Used service scan type"), self.nimConfig.cable.scan_type, _("Select 'provider' to scan from the predefined list of cable multiplexes. Select 'bands' to only scan certain parts of the spectrum. Select 'steps' to scan in steps of a particular frequency bandwidth."))
				self.list.append(self.cableScanType)
				if self.nimConfig.cable.scan_type.value == "provider":
					# country/region tier one
					if self.cableCountriesEntry is None:
						cablecountrycodelist = nimmanager.getCablesCountrycodeList()
						cablecountrycode = nimmanager.getCableCountrycode(self.slotid)
						default = cablecountrycode in cablecountrycodelist and cablecountrycode or None
						choices = [("all", _("All"))] + sorted([(x, self.countrycodeToCountry(x)) for x in cablecountrycodelist], key=lambda listItem: listItem[1])
						self.cableCountries = ConfigSelection(default=default, choices=choices)
						self.cableCountriesEntry = getConfigListEntry(self.indent % _("Country"), self.cableCountries, _("Select your country. If not available select 'all'."))
						self.originalCableRegion = self.nimConfig.cable.scan_provider.value
					# country/region tier two
					if self.cableCountries.value == "all":
						cableNames = [x[0] for x in sorted(sorted(nimmanager.getCablesList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
					else:
						cableNames = sorted([x[0] for x in nimmanager.getCablesByCountrycode(self.cableCountries.value)])
					default = self.nimConfig.cable.scan_provider.value in cableNames and self.nimConfig.cable.scan_provider.value or None
					self.cableRegions = ConfigSelection(default=default, choices=cableNames)

					def updateCableProvider(configEntry):
						self.nimConfig.cable.scan_provider.value = configEntry.value
						self.nimConfig.cable.scan_provider.save()
					self.cableRegions.addNotifier(updateCableProvider)
					self.cableRegionsEntry = getConfigListEntry(self.indent % _("Region"), self.cableRegions, _("Select your provider and region. If not present in this list you will need to select one of the other 'service scan types'."))
					self.list.append(self.cableCountriesEntry)
					self.list.append(self.cableRegionsEntry)
				else:
					self.cableConfigScanDetails = getConfigListEntry(self.indent % _("Config Scan Details"), self.nimConfig.cable.config_scan_details, _("Select 'yes' to choose what bands or step sizes will be scanned."))
					self.list.append(self.cableConfigScanDetails)
					if self.nimConfig.cable.config_scan_details.value:
						if self.nimConfig.cable.scan_type.value == "bands":
							# TRANSLATORS: option name, indicating which type of (DVB-C) band should be scanned. The name of the band is printed in '%s'. E.g.: 'Scan EU MID band'
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU VHF I")), self.nimConfig.cable.scan_band_EU_VHF_I, _("Select 'yes' to include the %s band in your search.") % ("EU VHF I")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU MID")), self.nimConfig.cable.scan_band_EU_MID, _("Select 'yes' to include the %s band in your search.") % ("EU MID")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU VHF III")), self.nimConfig.cable.scan_band_EU_VHF_III, _("Select 'yes' to include the %s band in your search.") % ("EU VHF III")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU UHF IV")), self.nimConfig.cable.scan_band_EU_UHF_IV, _("Select 'yes' to include the %s band in your search.") % ("EU VHF IV")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU UHF V")), self.nimConfig.cable.scan_band_EU_UHF_V, _("Select 'yes' to include the %s band in your search.") % ("EU VHF V")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU SUPER")), self.nimConfig.cable.scan_band_EU_SUPER, _("Select 'yes' to include the %s band in your search.") % ("EU SUPER")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("EU HYPER")), self.nimConfig.cable.scan_band_EU_HYPER, _("Select 'yes' to include the %s band in your search.") % ("EU HYPER")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("US LOW")), self.nimConfig.cable.scan_band_US_LOW, _("Select 'yes' to include the %s band in your search.") % ("US LOW")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("US MID")), self.nimConfig.cable.scan_band_US_MID, _("Select 'yes' to include the %s band in your search.") % ("US MID")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("US HIGH")), self.nimConfig.cable.scan_band_US_HIGH, _("Select 'yes' to include the %s band in your search.") % ("US HIGH")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("US SUPER")), self.nimConfig.cable.scan_band_US_SUPER, _("Select 'yes' to include the %s band in your search.") % ("US SUPER")))
							self.list.append(getConfigListEntry(self.indent % (_("Scan %s band") % ("US HYPER")), self.nimConfig.cable.scan_band_US_HYPER, _("Select 'yes' to include the %s band in your search.") % ("US HYPER")))
						else:
							self.list.append(getConfigListEntry(self.indent % _("Frequency scan step size(khz)"), self.nimConfig.cable.scan_frequency_steps, _("Enter the frequency step size for the tuner to use when searching for cable multiplexes. For more information consult your cable provider's documentation.")))
						# TRANSLATORS: option name, indicating which type of (DVB-C) modulation should be scanned. The modulation type is printed in '%s'. E.g.: 'Scan QAM16'
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("QAM16")), self.nimConfig.cable.scan_mod_qam16, _("Select 'yes' to include %s multiplexes in your search.") % ("QAM16")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("QAM32")), self.nimConfig.cable.scan_mod_qam32, _("Select 'yes' to include %s multiplexes in your search.") % ("QAM32")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("QAM64")), self.nimConfig.cable.scan_mod_qam64, _("Select 'yes' to include %s multiplexes in your search.") % ("QAM64")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("QAM128")), self.nimConfig.cable.scan_mod_qam128, _("Select 'yes' to include %s multiplexes in your search.") % ("QAM128")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("QAM256")), self.nimConfig.cable.scan_mod_qam256, _("Select 'yes' to include %s multiplexes in your search.") % ("QAM256")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("SR6900")), self.nimConfig.cable.scan_sr_6900, _("Select 'yes' to include symbol rate %s in your search.") % ("6900")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan %s") % ("SR6875")), self.nimConfig.cable.scan_sr_6875, _("Select 'yes' to include symbol rate %s in your search.") % ("6875")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan additional SR")), self.nimConfig.cable.scan_sr_ext1, _("This field allows you to search an additional symbol rate up to %s.") % ("7320")))
						self.list.append(getConfigListEntry(self.indent % (_("Scan additional SR")), self.nimConfig.cable.scan_sr_ext2, _("This field allows you to search an additional symbol rate up to %s.") % ("7320")))
		if self.nim.isCompatible("DVB-T") or (self.nim.isCombined() and self.nim.canBeCompatible("DVB-T")):
			if self.nim.isCombined():
				self.configModeDVBT = getConfigListEntry(_("Configure DVB-T"), self.nimConfig.configModeDVBT, _("Select 'Yes' when you want to configure this tuner for DVB-T"))
				self.list.append(self.configModeDVBT)
			elif not self.nim.isMultiType():
				self.configMode = getConfigListEntry(self.indent % _("Configuration mode"), self.nimConfig.configMode, _("Select 'enabled' if this tuner has a signal cable connected, otherwise select 'nothing connected'."))
				self.list.append(self.configMode)
			if self.nimConfig.configModeDVBT.value if self.nim.isCombined() else self.nimConfig.configMode.value != "nothing":
				# country/region tier one
				if self.terrestrialCountriesEntry is None:
					terrestrialcountrycodelist = nimmanager.getTerrestrialsCountrycodeList()
					terrestrialcountrycode = nimmanager.getTerrestrialCountrycode(self.slotid)
					default = terrestrialcountrycode in terrestrialcountrycodelist and terrestrialcountrycode or None
					choices = [("all", _("All"))] + sorted([(x, self.countrycodeToCountry(x)) for x in terrestrialcountrycodelist], key=lambda listItem: listItem[1])
					self.terrestrialCountries = ConfigSelection(default=default, choices=choices)
					self.terrestrialCountriesEntry = getConfigListEntry(self.indent % _("Country"), self.terrestrialCountries, _("Select your country. If not available select 'all'."))
					self.originalTerrestrialRegion = self.nimConfig.terrestrial.value
				# country/region tier two
				if self.terrestrialCountries.value == "all":
					terrstrialNames = [x[0] for x in sorted(sorted(nimmanager.getTerrestrialsList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
				else:
					terrstrialNames = sorted([x[0] for x in nimmanager.getTerrestrialsByCountrycode(self.terrestrialCountries.value)])
				default = self.nimConfig.terrestrial.value in terrstrialNames and self.nimConfig.terrestrial.value or None
				self.terrestrialRegions = ConfigSelection(default=default, choices=terrstrialNames)

				def updateTerrestrialProvider(configEntry):
					self.nimConfig.terrestrial.value = configEntry.value
					self.nimConfig.terrestrial.save()
				self.terrestrialRegions.addNotifier(updateTerrestrialProvider)
				self.terrestrialRegionsEntry = getConfigListEntry(self.indent % _("Region"), self.terrestrialRegions, _("Select your region. If not available change 'Country' to 'all' and select one of the default alternatives."))
				self.list.append(self.terrestrialCountriesEntry)
				self.list.append(self.terrestrialRegionsEntry)
				self.list.append(getConfigListEntry(self.indent % _("Enable 5V for active antenna"), self.nimConfig.terrestrial_5V, _("Enable this setting if your aerial system needs power")))
		if self.nim.isCompatible("ATSC") or (self.nim.isCombined() and self.nim.canBeCompatible("ATSC")):
			if self.nim.isCombined():
				self.configModeATSC = getConfigListEntry(_("Configure ATSC"), self.nimConfig.configModeATSC, _("Select 'Yes' when you want to configure this tuner for ATSC"))
				self.list.append(self.configModeATSC)
			elif not self.nim.isMultiType():
				self.configMode = getConfigListEntry(self.indent % _("Configuration mode"), self.nimConfig.configMode, _("Select 'enabled' if this tuner has a signal cable connected, otherwise select 'nothing connected'."))
				self.list.append(self.configMode)
			if self.nimConfig.configModeATSC.value if self.nim.isCombined() else self.nimConfig.configMode.value != "nothing":
				self.list.append(getConfigListEntry(self.indent % _("ATSC provider"), self.nimConfig.atsc, _("Select your ATSC provider.")))

		if self.nimConfig.configMode.value != "nothing" and config.usage.setup_level.index > 1 and not self.nim.isFBCLink():
			self.list.append(getConfigListEntry(_("Force legacy signal stats"), self.nimConfig.force_legacy_signal_stats, _("If set to 'yes' signal values (SNR, etc) will be calculated from API V3. This is an old API version that has now been superseded.")))

		self["config"].list = self.list
		self.setTextKeyYellow()

	def newConfig(self):
		self.setTextKeyBlue()
		if self["config"].getCurrent() == self.multiType:
			update_slots = [self.slotid]
			from Components.NimManager import InitNimManager
			InitNimManager(nimmanager, update_slots)
			self.nim = nimmanager.nim_slots[self.slotid]
			self.nimConfig = self.nim.config
		if self["config"].getCurrent() in (self.configMode, self.configModeDVBS, self.configModeDVBC, self.configModeDVBT, self.configModeATSC, self.diseqcModeEntry, self.advancedSatsEntry, self.advancedLnbsEntry, self.advancedDiseqcMode, self.advancedUsalsEntry,
			self.advancedLof, self.advancedPowerMeasurement, self.turningSpeed, self.advancedType, self.advancedSCR, self.advancedPosition, self.advancedFormat, self.advancedManufacturer,
			self.advancedUnicable, self.advancedConnected, self.toneburst, self.committedDiseqcCommand, self.uncommittedDiseqcCommand, self.singleSatEntry, self.commandOrder,
			self.showAdditionalMotorOptions, self.cableScanType, self.multiType, self.cableConfigScanDetails, self.terrestrialCountriesEntry, self.cableCountriesEntry,
			self.toneamplitude, self.scpc, self.t2mirawmode, self.forcelnbpower, self.forcetoneburst, self.externallyPowered):
				self.createSetup()

	def run(self):
		if self.nimConfig.configMode.value == "simple" and self.nimConfig.diseqcMode.value in ("single", "diseqc_a_b", "diseqc_a_b_c_d") and (not self.nim.isCombined() or self.nimConfig.configModeDVBS.value):
			autodiseqc_ports = 0
			if self.nimConfig.diseqcMode.value == "single":
				if self.nimConfig.diseqcA.orbital_position == 3600:
					autodiseqc_ports = 1
			elif self.nimConfig.diseqcMode.value == "diseqc_a_b":
				if self.nimConfig.diseqcA.orbital_position == 3600 or self.nimConfig.diseqcB.orbital_position == 3600:
					autodiseqc_ports = 2
			elif self.nimConfig.diseqcMode.value == "diseqc_a_b_c_d":
				if self.nimConfig.diseqcA.orbital_position == 3600 or self.nimConfig.diseqcB.orbital_position == 3600 or self.nimConfig.diseqcC.orbital_position == 3600 or self.nimConfig.diseqcD.orbital_position == 3600:
					autodiseqc_ports = 4
			if autodiseqc_ports:
				self.autoDiseqcRun(autodiseqc_ports)
				return False
		if self.have_advanced and self.nim.config_mode == "advanced":
			# fillAdvancedList resets self.list so some entries like t2mirawmode removed
			# saveAll will save any unsaved data before self.list entries are gone
			self.saveAll()
			self.fillAdvancedList()
		for x in self.list:
			if x in (self.turnFastEpochBegin, self.turnFastEpochEnd):
				# workaround for storing only hour*3600+min*60 value in configfile
				# not really needed.. just for cosmetics..
				tm = localtime(x[1].value)
				dt = datetime(1970, 1, 1, tm.tm_hour, tm.tm_min)
				x[1].value = int(mktime(dt.timetuple()))
			x[1].save()
		nimmanager.sec.update()
		self.saveAll(reopen=True)
		return True

	def autoDiseqcRun(self, ports):
		self.stopService()
		self.session.openWithCallback(self.autoDiseqcCallback, AutoDiseqc, self.slotid, ports, self.nimConfig.simpleDiSEqCSetVoltageTone, self.nimConfig.simpleDiSEqCOnlyOnSatChange)

	def autoDiseqcCallback(self, result):
		from Screens.Wizard import Wizard
		if Wizard.instance is not None:
			Wizard.instance.back()
		else:
			self.restartPrevService(close=False)
			self.createSetup()

	def fillListWithAdvancedSatEntrys(self, Sat):
		lnbnum = int(Sat.lnb.value)
		currLnb = self.nimConfig.advanced.lnb[lnbnum]

		if isinstance(currLnb, ConfigNothing):
			currLnb = None

		# LNBs
		self.advancedLnbsEntry = getConfigListEntry(self.indent % _("LNB"), Sat.lnb, _("Allocate a number to the physical LNB you are configuring. You will be able to select this LNB again for other satellites (e.g. motorised dishes) to save setting up the same LNB multiple times."))
		self.list.append(self.advancedLnbsEntry)

		if currLnb:
			if self.nim.isFBCLink():
				currLnb.lof.value = "unicable"
			self.list.append(getConfigListEntry(self.indent % _("Priority"), currLnb.prio, _("This setting is for special setups only. It gives this LNB higher priority over other LNBs with lower values. The free LNB with the highest priority will be the first LNB selected for tuning services.")))
			self.advancedLof = getConfigListEntry(self.indent % _("Type of LNB/device"), currLnb.lof, _("Select the type of LNB/device being used (normally 'Universal'). If your LNB type is not available select 'user defined'."))
			self.list.append(self.advancedLof)
			if currLnb.lof.value == "user_defined":
				self.list.append(getConfigListEntry(self.indent % "LOF/L", currLnb.lofl, _("Enter your low band local oscillator frequency. For more information consult the spec sheet of your LNB.")))
				self.list.append(getConfigListEntry(self.indent % "LOF/H", currLnb.lofh, _("Enter your high band local oscillator frequency. For more information consult the spec sheet of your LNB.")))
				self.list.append(getConfigListEntry(self.indent % _("Threshold"), currLnb.threshold, _("Enter the frequency at which you LNB switches between low band and high band. For more information consult the spec sheet of your LNB.")))

			if currLnb.lof.value == "unicable":
				warning_text = ""
				if "Vuplus DVB-S NIM(AVL6222)" in self.nim.description and self.nim.internallyConnectableTo() is not None:
					warning_text = _("Warning: the second input of this dual tuner may not support SCR LNBs. ")
				self.advancedUnicable = getConfigListEntry(self.indent % ("%s%s" % ("SCR (Unicable/JESS) ", _("type"))), currLnb.unicable, warning_text + _("Select the type of Single Cable Reception device you are using."))
				self.list.append(self.advancedUnicable)
				self.externallyPowered = getConfigListEntry(self.indent % _("Externally powered"), currLnb.powerinserter, _("Select whether your SCR device is externally powered."))
				if currLnb.unicable.value == "unicable_user":
					self.advancedFormat = getConfigListEntry(self.indent % _("Format"), currLnb.format, _("Select the protocol used by your SCR device. Choices are 'SCR Unicable' (Unicable), or 'SCR JESS' (JESS, also known as Unicable II)."))
					self.advancedPosition = getConfigListEntry(self.indent % _("Position"), currLnb.positionNumber, _("Only change this setting if you are using a SCR device that has been reprogrammed with a custom programmer. For further information check with the person that reprogrammed the device."))
					self.advancedSCR = getConfigListEntry(self.indent % _("Channel"), currLnb.scrList, _("Select the User Band channel to be assigned to this tuner. This is an index into the table of frequencies the SCR switch or SCR LNB uses to pass the requested transponder to the tuner."))
					self.list.append(self.advancedFormat)
					self.list.append(self.advancedPosition)
					self.list.append(self.advancedSCR)
					self.list.append(getConfigListEntry(self.indent % _("Frequency"), currLnb.scrfrequency, _("Select the User Band frequency to be assigned to this tuner. This is the frequency the SCR switch or SCR LNB uses to pass the requested transponder to the tuner.")))
					self.list.append(getConfigListEntry(self.indent % "LOF/L", currLnb.lofl, _("Consult your SCR device spec sheet for this information.")))
					self.list.append(getConfigListEntry(self.indent % "LOF/H", currLnb.lofh, _("Consult your SCR device spec sheet for this information.")))
					self.list.append(getConfigListEntry(self.indent % _("Threshold"), currLnb.threshold, _("Consult your SCR device spec sheet for this information.")))
					if not SystemInfo["FbcTunerPowerAlwaysOn"] or not self.nim.isFBCTuner():
						self.list.append(self.externallyPowered)
					if not currLnb.powerinserter.value:
						self.list.append(getConfigListEntry(self.indent % _("Bootup time"), currLnb.bootuptime, _("Consult your SCR device spec sheet for this information.")))
				else:
					self.advancedManufacturer = getConfigListEntry(self.indent % _("Manufacturer"), currLnb.unicableManufacturer, _("Select the manufacturer of your SCR device. If the manufacturer is not listed, set 'SCR' to 'user defined' and enter the device parameters manually according to its spec sheet."))
					self.advancedType = getConfigListEntry(self.indent % _("Model"), currLnb.unicableProduct, _("Select the model number of your SCR device. If the model number is not listed, set 'SCR' to 'user defined' and enter the device parameters manually according to its spec sheet."))
					self.advancedSCR = getConfigListEntry(self.indent % _("Channel"), currLnb.scrList, _("Select the User Band to be assigned to this tuner. This is an index into the table of frequencies the SCR switch or SCR LNB uses to pass the requested transponder to the tuner."))
					self.advancedPosition = getConfigListEntry(self.indent % _("Position"), currLnb.positionNumber, _("Only change this setting if you are using a SCR device that has been reprogrammed with a custom programmer. For further information check with the person that reprogrammed the device."))
					self.list.append(self.advancedManufacturer)
					self.list.append(self.advancedType)
					if currLnb.positions.value > 1:
						self.list.append(self.advancedPosition)
					self.list.append(self.advancedSCR)
					if not SystemInfo["FbcTunerPowerAlwaysOn"] or not self.nim.isFBCTuner():
						self.list.append(self.externallyPowered)
				choices = []
				connectable = nimmanager.canConnectTo(self.slotid)
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id) + (not nimmanager.isUnicableLNBmode(id) and _(" - Unicable/JESS LNBs not found") or "")))
				if len(choices):
					if self.nim.isFBCLink():
						if not self.nimConfig.advanced.unicableconnected.value:
							self.nimConfig.advanced.unicableconnected.value = True
					self.advancedConnected = getConfigListEntry(self.indent % _("Connected"), self.nimConfig.advanced.unicableconnected, _("Select 'yes' if this tuner is connected to the SCR device through another tuner, otherwise select 'no'."))
					self.list.append(self.advancedConnected)
					if self.nimConfig.advanced.unicableconnected.value:
						self.nimConfig.advanced.unicableconnectedTo.setChoices(choices)
						self.list.append(getConfigListEntry(self.indent % _("Connected to"), self.nimConfig.advanced.unicableconnectedTo, _("Select the tuner to which the signal cable of the SCR device is connected.")))

			else:	#kein Unicable
				self.list.append(getConfigListEntry(self.indent % _("Voltage mode"), Sat.voltage, _("Select 'polarisation' if using a 'universal' LNB, otherwise consult your LNB spec sheet.")))
				self.list.append(getConfigListEntry(self.indent % _("Increased voltage"), currLnb.increased_voltage))
				self.list.append(getConfigListEntry(self.indent % _("Tone mode"), Sat.tonemode, _("Select 'band' if using a 'universal' LNB, otherwise consult your LNB spec sheet.")))

			if lnbnum < 65 or lnbnum == 71:
				if self.nim.isFBCLink() and ("1_2", "1.2") in currLnb.diseqcMode.choices.choices:
					currLnb.diseqcMode.setChoices([("none", _("none")), ("1_0", "1.0"), ("1_1", "1.1")], "none")
				self.advancedDiseqcMode = getConfigListEntry(self.indent % _("DiSEqC mode"), currLnb.diseqcMode, _("Select '1.0' for standard committed switches, '1.1' for uncommitted switches, and '1.2' for systems using a positioner."))
				self.list.append(self.advancedDiseqcMode)
			if currLnb.diseqcMode.value != "none":
				self.list.append(getConfigListEntry(self.indent % _("Fast DiSEqC"), currLnb.fastDiseqc, _("Select Fast DiSEqC if your aerial system supports this. If you are unsure select 'no'.")))
				self.toneburst = getConfigListEntry(self.indent % _("Toneburst"), currLnb.toneburst, _("Select 'A' or 'B' if your aerial system requires this, otherwise select 'none'. If you are unsure select 'none'."))
				self.list.append(self.toneburst)
				self.committedDiseqcCommand = getConfigListEntry(self.indent % _("DiSEqC 1.0 command"), currLnb.commitedDiseqcCommand, _("If you are using a DiSEqC committed switch enter the port letter required to access the LNB used for this satellite."))
				self.list.append(self.committedDiseqcCommand)
				if currLnb.diseqcMode.value == "1_0":
					if currLnb.toneburst.index and currLnb.commitedDiseqcCommand.index:
						self.list.append(getConfigListEntry(self.indent % _("Command order"), currLnb.commandOrder1_0, _("This is the order in which DiSEqC commands are sent to the aerial system. The order must correspond exactly with the order the physical devices are arranged along the signal cable (starting from the receiver end).")))
				else:
					self.uncommittedDiseqcCommand = getConfigListEntry(self.indent % _("DiSEqC 1.1 command"), currLnb.uncommittedDiseqcCommand, _("If you are using a DiSEqC uncommitted switch enter the port number required to access the LNB used for this satellite."))
					self.list.append(self.uncommittedDiseqcCommand)
					if currLnb.uncommittedDiseqcCommand.index:
						if currLnb.commandOrder.value == "ct":
							currLnb.commandOrder.value = "cut"
						elif currLnb.commandOrder.value == "tc":
							currLnb.commandOrder.value = "tcu"
					else:
						if currLnb.commandOrder.index & 1:
							currLnb.commandOrder.value = "tc"
						else:
							currLnb.commandOrder.value = "ct"
					self.commandOrder = getConfigListEntry(self.indent % _("Command order"), currLnb.commandOrder, _("This is the order in which DiSEqC commands are sent to the aerial system. The order must correspond exactly with the order the physical devices are arranged along the signal cable (starting from the receiver end)."))
					if 1 < ((1 if currLnb.uncommittedDiseqcCommand.index else 0) + (1 if currLnb.commitedDiseqcCommand.index else 0) + (1 if currLnb.toneburst.index else 0)):
						self.list.append(self.commandOrder)
					if currLnb.uncommittedDiseqcCommand.index:
						self.list.append(getConfigListEntry(self.indent % _("DiSEqC 1.1 repeats"), currLnb.diseqcRepeats, _("If using multiple uncommitted switches the DiSEqC commands must be sent multiple times. Set to the number of uncommitted switches in the chain minus one.")))
				self.list.append(getConfigListEntry(self.indent % _("Sequence repeat"), currLnb.sequenceRepeat, _("Set sequence repeats if your aerial system requires this. Normally if the aerial system has been configured correctly sequence repeats will not be necessary. If yours does, recheck you have command order set correctly.")))
				if currLnb.diseqcMode.value == "1_2":
					if SystemInfo["CanMeasureFrontendInputPower"]:
						self.advancedPowerMeasurement = getConfigListEntry(self.indent % _("Use power measurement"), currLnb.powerMeasurement, _("Power management. Consult your receiver's manual for more information."))
						self.list.append(self.advancedPowerMeasurement)
						if currLnb.powerMeasurement.value:
							self.list.append(getConfigListEntry(self.indent % _("Power threshold in mA"), currLnb.powerThreshold, _("Power threshold. Consult your receiver's manual for more information.")))
							self.turningSpeed = getConfigListEntry(self.indent % _("Rotor turning speed"), currLnb.turningSpeed, _("Select how quickly the dish should move between satellites."))
							self.list.append(self.turningSpeed)
							if currLnb.turningSpeed.value == "fast epoch":
								self.turnFastEpochBegin = getConfigListEntry(self.indent % _("Begin time"), currLnb.fastTurningBegin, _("Only move the dish quickly after this hour."))
								self.turnFastEpochEnd = getConfigListEntry(self.indent % _("End time"), currLnb.fastTurningEnd, _("Only move the dish quickly before this hour."))
								self.list.append(self.turnFastEpochBegin)
								self.list.append(self.turnFastEpochEnd)
					else:
						if currLnb.powerMeasurement.value:
							currLnb.powerMeasurement.value = False
							currLnb.powerMeasurement.save()
					self.advancedUsalsEntry = getConfigListEntry(self.indent % _("Use USALS for this sat"), Sat.usals, _("USALS automatically moves a motorised dish to the correct satellite based on the coordinates entered by the user. Without USALS each satellite will need to be setup and saved individually."))
					if lnbnum < 65:
						self.list.append(self.advancedUsalsEntry)
					if Sat.usals.value:
						self.list.append(getConfigListEntry(self.indent % _("Longitude"), currLnb.longitude, _("Enter your current longitude. This is the number of degrees you are from zero meridian as a decimal.")))
						self.list.append(getConfigListEntry(" ", currLnb.longitudeOrientation, _("Enter if you are in the east or west hemisphere.")))
						self.list.append(getConfigListEntry(self.indent % _("Latitude"), currLnb.latitude, _("Enter your current latitude. This is the number of degrees you are from the equator as a decimal.")))
						self.list.append(getConfigListEntry(" ", currLnb.latitudeOrientation, _("Enter if you are north or south of the equator.")))
					else:
						self.list.append(getConfigListEntry(self.indent % _("Stored position"), Sat.rotorposition, _("Enter the number stored in the positioner that corresponds to this satellite.")))
					if not hasattr(self, 'additionalMotorOptions'):
						self.additionalMotorOptions = ConfigBoolean(default=any([x.value != x.default for x in (currLnb.turningspeedH, currLnb.turningspeedV, currLnb.tuningstepsize, currLnb.rotorPositions)]), descriptions={False: _("Show sub-menu"), True: _("Hide sub-menu")})
					self.showAdditionalMotorOptions = getConfigListEntry(self.indent % _("Extra motor options"), self.additionalMotorOptions, _("Additional motor options allow you to enter details from your motor's spec sheet so enigma can work out how long it will take to move to another satellite."))
					self.list.append(self.showAdditionalMotorOptions)
					if self.additionalMotorOptions.value:
						self.list.append(getConfigListEntry(self.indent % ("  %s" % _("Horizontal turning speed")) + " [" + chr(176) + "/sec]", currLnb.turningspeedH, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry(self.indent % ("  %s" % _("Vertical turning speed")) + " [" + chr(176) + "/sec]", currLnb.turningspeedV, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry(self.indent % ("  %s" % _("Turning step size")) + " [" + chr(176) + "]", currLnb.tuningstepsize, _("Consult your motor's spec sheet for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry(self.indent % ("  %s" % _("Max memory positions")), currLnb.rotorPositions, _("Consult your motor's spec sheet for this information, or leave the default setting.")))

	def fillAdvancedList(self):
		self.list = []
		self.configMode = getConfigListEntry(self.indent % _("Configuration mode"), self.nimConfig.configMode)
		self.list.append(self.configMode)
		self.advancedSatsEntry = getConfigListEntry(self.indent % _("Satellite"), self.nimConfig.advanced.sats)
		self.list.append(self.advancedSatsEntry)
		for x in self.nimConfig.advanced.sat.keys():
			Sat = self.nimConfig.advanced.sat[x]
			self.fillListWithAdvancedSatEntrys(Sat)
		self["config"].list = self.list

	def keyOk(self):
		if self.isChanged():
			self.stopService()
		if self["config"].getCurrent() == self.advancedSelectSatsEntry:
			conf = self.nimConfig.advanced.sat[int(self.nimConfig.advanced.sats.value)].userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		elif self["config"].getCurrent() == self.selectSatsEntry:
			conf = self.nimConfig.userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		else:
			self.keySave()

	def updateConfUserSatellitesList(self, conf, val=None):
		if val is not None:
			conf.value = val
			conf.save()

	def keySave(self):
		if self.isChanged():
			self.stopService()
		old_configured_sats = nimmanager.getConfiguredSats()
		if not self.run():
			return
		new_configured_sats = nimmanager.getConfiguredSats()
		self.unconfed_sats = old_configured_sats - new_configured_sats
		self.satpos_to_remove = None
		self.deleteConfirmed((None, "no"))

	def deleteConfirmed(self, confirmed):
		if confirmed is None:
			confirmed = (None, "no")

		if confirmed[1] == "yes" or confirmed[1] == "yestoall":
			eDVBDB.getInstance().removeServices(-1, -1, -1, self.satpos_to_remove)

		if self.satpos_to_remove is not None:
			self.unconfed_sats.remove(self.satpos_to_remove)

		self.satpos_to_remove = None
		for orbpos in self.unconfed_sats:
			self.satpos_to_remove = orbpos
			orbpos = self.satpos_to_remove
			try:
				# why we need this cast?
				sat_name = str(nimmanager.getSatDescription(orbpos))
			except:
				if orbpos > 1800: # west
					orbpos = 3600 - orbpos
					h = _("W")
				else:
					h = _("E")
				sat_name = ("%d.%d" + h) % (orbpos / 10, orbpos % 10)

			if confirmed[1] == "yes" or confirmed[1] == "no":
				# TRANSLATORS: The satellite with name '%s' is no longer used after a configuration change. The user is asked whether or not the satellite should be deleted.
				self.session.openWithCallback(self.deleteConfirmed, ChoiceBox, _("%s is no longer used. Should it be deleted?") % sat_name, [(_("Yes"), "yes"), (_("No"), "no"), (_("Yes to all"), "yestoall"), (_("No to all"), "notoall")], None, 1)
			if confirmed[1] == "yestoall" or confirmed[1] == "notoall":
				self.deleteConfirmed(confirmed)
			break
		else:
			self.restartPrevService()

	def __init__(self, session, slotid):
		Screen.__init__(self, session)
		self.list = []
		ServiceStopScreen.__init__(self)
		ConfigListScreen.__init__(self, self.list)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["description"] = Label("")
		self["actions"] = ActionMap(["SetupActions", "SatlistShortcutAction"],
		{
			"ok": self.keyOk,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"changetype": self.changeConfigurationMode,
			"nothingconnected": self.nothingConnectedShortcut
		}, -2)

		self.slotid = slotid
		self.nim = nimmanager.nim_slots[slotid]
		self.nimConfig = self.nim.config
		self.createSetup()
		self.setTitle(_("Setup") + " " + self.nim.friendly_full_description)

	def keyLeft(self):
		if self.nim.isFBCLink() and self["config"].getCurrent() in (self.advancedLof, self.advancedConnected):
			return
		ConfigListScreen.keyLeft(self)
		if self["config"].getCurrent() in (self.advancedSelectSatsEntry, self.selectSatsEntry):
			self.keyOk()
		else:
			self.newConfig()

	def setTextKeyYellow(self):
		self["key_yellow"].setText((self.nimConfig.configMode.value == "simple" and self.nimConfig.diseqcMode.value in ("single", "diseqc_a_b", "diseqc_a_b_c_d") and (not self.nim.isCombined() or self.nimConfig.configModeDVBS.value)) and _("Auto DiSEqC") or self.configMode and _("Configuration mode") or "")

	def setTextKeyBlue(self):
		self["key_blue"].setText(self.isChanged() and _("Set default") or "")

	def keyRight(self):
		if self.nim.isFBCLink() and self["config"].getCurrent() in (self.advancedLof, self.advancedConnected):
			return
		ConfigListScreen.keyRight(self)
		if self["config"].getCurrent() in (self.advancedSelectSatsEntry, self.selectSatsEntry):
			self.keyOk()
		else:
			self.newConfig()

	def handleKeyFileCallback(self, answer):
		ConfigListScreen.handleKeyFileCallback(self, answer)
		self.newConfig()

	def keyCancel(self):
		if self.isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.restartPrevService()

	def isChanged(self):
		is_changed = False
		for x in self["config"].list:
			if x == self.showAdditionalMotorOptions:
				continue
			is_changed |= x[1].isChanged()
		return is_changed

	def saveAll(self, reopen=False):
		if self.nim.isCompatible("DVB-S"):
			# reset connectedTo to all choices to properly store the default value
			choices = []
			nimlist = nimmanager.getNimListOfType("DVB-S", self.slotid)
			for id in nimlist:
				choices.append((str(id), nimmanager.getNimDescription(id)))
			self.nimConfig.connectedTo.setChoices(choices)
			# sanity check for empty sat list
			if not (self.nimConfig.configMode.value == "satposdepends" or self.nimConfig.configMode.value == "advanced" and int(self.nimConfig.advanced.sat[3607].lnb.value) != 0) and len(nimmanager.getSatListForNim(self.slotid)) < 1:
				self.nimConfig.configMode.value = "nothing"
		elif self.nim.isCompatible("DVB-C") and self.nim.isFBCRoot():
			value = "nothing"
			if self.nimConfig.configMode.value == "enabled":
				value = "enabled"
			for slot in nimmanager.nim_slots:
				if slot.isFBCLink() and slot.is_fbc[2] == self.nim.is_fbc[2] and slot.config.configMode.value != value:
					slot.config.configMode.value = value
					slot.config.configMode.save()
		if reopen and self.oldref and self.slot_number == self.slotid:
			type_service = self.oldAlternativeref.getUnsignedData(4) >> 16
			force_reopen = False
			if type_service == 0xEEEE and (self.nim.isCompatible("DVB-T") and self.nimConfig.configMode.value == "nothing") or (self.nim.isCombined() and self.nim.canBeCompatible("DVB-T") and not self.nimConfig.configModeDVBT.value):
				force_reopen = True
			elif type_service == 0xFFFF and ((self.nim.isCompatible("DVB-C") and self.nimConfig.configMode.value == "nothing") or (self.nim.isCombined() and self.nim.canBeCompatible("DVB-C") and not self.nimConfig.configModeDVBC.value)) or ((self.nim.isCompatible("ATSC") and self.nimConfig.configMode.value == "nothing") or (self.nim.isCombined() and self.nim.canBeCompatible("ATSC") and not self.nimConfig.configModeATSC.value)):
				force_reopen = True
			if force_reopen:
				raw_channel = eDVBResourceManager.getInstance().allocateRawChannel(self.slotid)
				if raw_channel:
					frontend = raw_channel.getFrontend()
					if frontend:
						frontend.closeFrontend()
						frontend.reopenFrontend()
				del raw_channel
		if self.isChanged():
			for x in self["config"].list:
				x[1].save()
			configfile.save()
		showrotorpositionChoicesUpdate(update=True)
		preferredTunerChoicesUpdate(update=True)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		if hasattr(self, "originalTerrestrialRegion"):
			self.nimConfig.terrestrial.value = self.originalTerrestrialRegion
			self.nimConfig.terrestrial.save()
		if hasattr(self, "originalCableRegion"):
			self.nimConfig.cable.scan_provider.value = self.originalCableRegion
			self.nimConfig.cable.scan_provider.save()
		# we need to call saveAll to reset the connectedTo choices
		self.saveAll()
		self.restartPrevService()

	def changeConfigurationMode(self):
		if self.nimConfig.configMode.value == "simple" and self.nimConfig.diseqcMode.value in ("single", "diseqc_a_b", "diseqc_a_b_c_d") and (not self.nim.isCombined() or self.nimConfig.configModeDVBS.value):
			self.autoDiseqcRun(self.nimConfig.diseqcMode.value == "diseqc_a_b_c_d" and 4 or self.nimConfig.diseqcMode.value == "diseqc_a_b" and 2 or 1)
		elif self.configMode:
			self.nimConfig.configMode.selectNext()
			self["config"].invalidate(self.configMode)
			self.setTextKeyBlue()
			self.createSetup()

	def nothingConnectedShortcut(self):
		if self.isChanged():
			for x in self["config"].list:
				x[1].cancel()
			self.setTextKeyBlue()
			self.createSetup()

	def countrycodeToCountry(self, cc):
		if not hasattr(self, 'countrycodes'):
			self.countrycodes = {}
			from Tools.CountryCodes import ISO3166
			for country in ISO3166:
				self.countrycodes[country[2]] = country[0]
		if cc.upper() in self.countrycodes:
			return self.countrycodes[cc.upper()]
		return cc


class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = [None] * nimmanager.getSlotCount()
		self["nimlist"] = List(self.list)
		self.updateList()

		self.setResultClass()

		self["actions"] = ActionMap(["OkCancelActions", "MenuActions", "ChannelSelectEPGActions"],
		{
			"ok": self.okbuttonClick,
			"info": self.extraInfo,
			"epg": self.extraInfo,
			"cancel": self.close,
			"menu": self.exit,
		}, -2)
		self.setTitle(_("Choose Tuner"))

	def exit(self):
		self.close(True)

	def setResultClass(self):
		self.resultclass = NimSetup

	def OrbToStr(self, orbpos=-1):
		if orbpos == -1 or orbpos > 3600:
			return "??"
		if orbpos > 1800:
			orbpos = 3600 - orbpos
			return "%d.%dW" % (orbpos / 10, orbpos % 10)
		return "%d.%dE" % (orbpos / 10, orbpos % 10)

	def extraInfo(self):
		current = self["nimlist"].getCurrent()
		nim = current and len(current) > 2 and hasattr(current[3], "slot") and current[3]
		if config.usage.setup_level.index >= 2 and nim:
			text = _("Capabilities: ") + eDVBResourceManager.getInstance().getFrontendCapabilities(nim.slot)
			self.session.open(MessageBox, text, MessageBox.TYPE_INFO, simple=True)

	def okbuttonClick(self):
		recordings = self.session.nav.getRecordings()
		next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time and next_rec_time > 0 and (next_rec_time - time()) < 360):
			self.session.open(MessageBox, _("Recording(s) are in progress or coming up in few seconds!"), MessageBox.TYPE_INFO, timeout=5, enable_input=False)
		else:
			current = self["nimlist"].getCurrent()
			nim = current and len(current) > 2 and hasattr(current[3], "slot") and current[3]
			if nim:
				nimConfig = nimmanager.getNimConfig(nim.slot)
				if nim.isFBCLink() and nimConfig.configMode.value == "nothing" and not getLinkedSlotID(nim.slot) == -1:
					return
				if (not nim.empty or nim.isMultiType()) and nim.isSupported():
					self.session.openWithCallback(boundFunction(self.NimSetupCB, self["nimlist"].getIndex()), self.resultclass, nim.slot)

	def NimSetupCB(self, index=None):
		self.updateList(index)

	def showNim(self, nim):
		return True

	def updateList(self, index=None):
		self.list = []
		for x in nimmanager.nim_slots:
			if x.isFBCLink() and not x.isFBCLinkEnabled():
				continue
			slotid = x.slot
			nimConfig = nimmanager.getNimConfig(x.slot)
			text = ""
			if self.showNim(x):
				fbc_text = ""
				if x.isFBCTuner():
					fbc_text = (x.isFBCRoot() and _("Slot %s / FBC in %s") % (x.is_fbc[2], x.is_fbc[1])) or _("Slot %s / FBC virtual %s") % (x.is_fbc[2], x.is_fbc[1] - (x.isCompatible("DVB-S") and 2 or 1))
				if x.isCompatible("DVB-S"):
					if nimConfig.configMode.value in ("loopthrough", "equal", "satposdepends"):
						if x.isFBCLink():
							text = _("FBC automatic\nconnected to")
						else:
							text = "%s %s" % ({"loopthrough": _("Loop through from"), "equal": _("Equal to"), "satposdepends": _("Second cable of motorized LNB")}[nimConfig.configMode.value],
								nimmanager.getNim(int(nimConfig.connectedTo.value)).slot_name)
						if fbc_text:
							text += "\n" + fbc_text
					elif nimConfig.configMode.value == "nothing":
						if x.isFBCLink():
							link = getLinkedSlotID(x.slot)
							if link == -1:
								text = _("FBC automatic\ninactive")
							else:
								link = nimmanager.getNim(link).slot_name
								text = _("FBC automatic\nconnected to %s") % link
						else:
							text = _("Disabled")
						if fbc_text:
							text += "\n" + fbc_text
					elif nimConfig.configMode.value == "simple":
						if nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
							text = "%s\n%s: " % ({"single": _("Single"), "toneburst_a_b": _("Toneburst A/B"), "diseqc_a_b": _("DiSEqC A/B"), "diseqc_a_b_c_d": _("DiSEqC A/B/C/D")}[nimConfig.diseqcMode.value],
								_("Sats"))
							satnames = []
							if nimConfig.diseqcA.orbital_position < 3600:
								satnames.append(nimmanager.getSatName(int(nimConfig.diseqcA.value)))
							if nimConfig.diseqcMode.value in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
								if nimConfig.diseqcB.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcB.value)))
							if nimConfig.diseqcMode.value == "diseqc_a_b_c_d":
								if nimConfig.diseqcC.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcC.value)))
								if nimConfig.diseqcD.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcD.value)))
							if len(satnames) <= 2:
								text += ", ".join(satnames)
							elif len(satnames) > 2:
								# basic info - orbital positions only
								text += ', '.join(sat.split()[0] for sat in satnames)
						elif nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
							text = "%s: " % {"positioner": _("Positioner"), "positioner_select": _("Positioner (selecting satellites)")}[nimConfig.diseqcMode.value]
							if nimConfig.positionerMode.value == "usals":
								text += "USALS"
							elif nimConfig.positionerMode.value == "manual":
								text += _("Manual")
						else:
							text = _("Simple")
						if fbc_text:
							text = fbc_text + " / " + text
					elif nimConfig.configMode.value == "advanced":
						satnames = []
						sat_list = nimmanager.getSatListForNim(slotid)
						for sat in sat_list:
							satnames.append(self.OrbToStr(int(sat[0])))
						description = ""
						unicableconnecto = ""
						if hasattr(nimConfig.advanced, "unicableconnected") and nimConfig.advanced.unicableconnected.value:
							nim2 = nimConfig.advanced.unicableconnectedTo.value
							if nim2.isdigit():
								unicableconnecto = " / " + _("Connected to") + " " + nimmanager.getNim(int(nim2)).slot_name
						if int(nimConfig.advanced.sat[3607].lnb.value) != 0:
							ident = satnames and " + " or " "
							description = "%s(%s %s)" % (ident, (x.isFBCLink() and unicableconnecto and _(" unicable LNB input of rotor")) or _("additional cable of rotor"), (unicableconnecto and " " or nimmanager.getNim(int(nimConfig.connectedTo.value)).slot_name))
						else:
							rotor_sat_list = nimmanager.getRotorSatListForNim(slotid)
							if rotor_sat_list:
								ident = len(sat_list) > len(rotor_sat_list) and " + " or " "
								description = "%s(%s)" % (ident, _("rotor"))
						if fbc_text:
							fbc_text = fbc_text + " / "
						if satnames or not description:
							text = "%s\n%s: " % (fbc_text + _("Advanced") + unicableconnecto + description, _("Sats"))
							text += ", ".join(satnames)
						elif description:
							text = "%s\n%s: " % (fbc_text + _("Advanced") + unicableconnecto, _("Sats"))
							text += description
				elif x.isCompatible("DVB-T") or x.isCompatible("DVB-C") or x.isCompatible("ATSC"):
					if nimConfig.configMode.value == "nothing":
						text = _("Disabled")
					elif nimConfig.configMode.value == "enabled" and not x.isCombined():
						text = _("Enabled")
					if x.isCompatible("DVB-C") and fbc_text:
						text += "\n" + fbc_text
				if x.multi_type:
					enabledTuners = "/".join([y[1].replace("DVB-", "") for y in sorted([({"DVB-S": 1, "DVB-C": 2, "DVB-T": 3, "ATSC": 4}[y[:5]], y) for y in x.getTunerTypesEnabled()])] if nimConfig.configMode.value != "nothing" else [])
					text = ("%s: %s\n%s" % (_("Modes") if "/" in enabledTuners else _("Mode"), enabledTuners if enabledTuners == 'ATSC' else "DVB-%s" % enabledTuners, text)) if enabledTuners else _("Disabled")
				if not x.isSupported():
					text = _("Tuner is not supported")
				if x.isCompatible("DVB-T") and ("DVB-T" in (text + x.friendly_full_description) or "/T" in (text + x.friendly_full_description)) and _("Disabled") not in text and hasattr(nimConfig, "terrestrial_5V") and nimConfig.terrestrial_5V.value:
					text += _(" (+5 volt terrestrial)")
				self.list.append((slotid, x.friendly_full_description, text or nimConfig.configMode.value, x))
		self["nimlist"].setList(self.list)
		self["nimlist"].updateList(self.list)
		if index is not None:
			self["nimlist"].setIndex(index)


class SelectSatsEntryScreen(Screen):
	skin = """
		<screen name="SelectSatsEntryScreen" position="center,center" size="560,410" title="Select Sats Entry" >
			<ePixmap name="red" position="0,0"   zPosition="2" size="140,40" pixmap="buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="green" position="140,0" zPosition="2" size="140,40" pixmap="buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap name="blue" position="420,0" zPosition="2" size="140,40" pixmap="buttons/blue.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="list" position="10,40" size="540,330" scrollbarMode="showNever" />
			<ePixmap pixmap="div-h.png" position="0,375" zPosition="1" size="540,2" transparent="1" alphatest="on" />
			<widget name="hint" position="10,380" size="540,25" font="Regular;19" halign="center" transparent="1" />
		</screen>"""

	def __init__(self, session, userSatlist=""):
		Screen.__init__(self, session)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Sort by"))
		self["key_blue"] = Button(_("Select all"))
		self["hint"] = Label(_("Press OK to toggle the selection"))
		SatList = []
		if not isinstance(userSatlist, str):
			userSatlist = ""
		else:
			userSatlist = userSatlist.replace("]", "").replace("[", "")
		for sat in nimmanager.getSatList():
			selected = False
			sat_str = str(sat[0])
			if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))):
				selected = True
			SatList.append((sat[0], sat[1], sat[2], selected))
		sat_list = [SelectionEntryComponent(x[1], x[0], x[2], x[3]) for x in SatList]
		self["list"] = SelectionList(sat_list, enableWrapAround=True)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"yellow": self.sortBy,
			"blue": self["list"].toggleAllSelection,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self["list"].toggleSelection,
		}, -2)
		self.setTitle(_("Select satellites"))

	def save(self):
		val = [x[0][1] for x in self["list"].list if x[0][3]]
		self.close(str(val))

	def cancel(self):
		self.close(None)

	def sortBy(self):
		lst = self["list"].list
		if len(lst) > 1:
			menu = [(_("Reverse list"), "2"), (_("Standard list"), "1")]
			connected_sat = [x[0][1] for x in lst if x[0][3]]
			if len(connected_sat) > 0:
				menu.insert(0, (_("Connected satellites"), "3"))

			def sortAction(choice):
				if choice:
					reverse_flag = False
					sort_type = int(choice[1])
					if choice[1] == "2":
						sort_type = reverse_flag = 1
					elif choice[1] == "3":
						reverse_flag = not reverse_flag
					self["list"].sort(sortType=sort_type, flag=reverse_flag)
					self["list"].moveToIndex(0)
			self.session.openWithCallback(sortAction, ChoiceBox, title=_("Select sort method:"), list=menu)
