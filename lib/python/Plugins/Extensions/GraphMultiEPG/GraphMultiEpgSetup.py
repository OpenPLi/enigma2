from Screens.Setup import Setup


class GraphMultiEpgSetup(Setup):
	def __init__(self, session, args=None):
		Setup.__init__(self, session, "graphmultiepgsetup", plugin="Extensions/GraphMultiEPG")
