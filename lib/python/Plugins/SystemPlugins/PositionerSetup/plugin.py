from Plugins.Plugin import PluginDescriptor
from Components.NimManager import nimmanager


def getUsableRotorNims(only_first=False):
	usableRotorNims = []
	nimList = nimmanager.getNimListOfType("DVB-S")
	for nim in nimList:
		if nimmanager.getRotorSatListForNim(nim, only_first=only_first):
			usableRotorNims.append(nim)
			if only_first:
				break
	return usableRotorNims


def PositionerMain(session, **kwargs):
	from ui import PositionerSetup, RotorNimSelection
	usableRotorNims = getUsableRotorNims()
	if len(usableRotorNims) == 1:
		session.open(PositionerSetup, usableRotorNims[0])
	elif len(usableRotorNims) > 1:
		session.open(RotorNimSelection, usableRotorNims)


def PositionerSetupStart(menuid, **kwargs):
	if menuid == "scan" and getUsableRotorNims(True):
		return [(_("Positioner setup"), PositionerMain, "positioner_setup", None)]
	return []


def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S"):
		return PluginDescriptor(name=_("Positioner setup"), description=_("Setup your positioner"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=PositionerSetupStart)
	else:
		return []
