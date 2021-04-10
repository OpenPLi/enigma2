from Plugins.Plugin import PluginDescriptor
from Components.config import config

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def startSetup(menuid):
	# show only in the menu when set at expert level
	if menuid == "video" and config.usage.setup_level.index == 2:
		return [(_("Testscreens"), videoFinetuneMain, "video_finetune", None)]
	return []

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Testscreens"), description=_("Testscreens that are helpfull to fine-tune your display"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup)
