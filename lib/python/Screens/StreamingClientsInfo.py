from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.Converter.ClientsStreaming import ClientsStreaming
import enigma

class StreamingClientsInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Streaming clients info"))

		clients = ClientsStreaming("INFO_RESOLVE")
		text = clients.getText()

		self["ScrollLabel"] = ScrollLabel(text or _("No stream clients"))
		self["key_red"] = Button(text and _("Stop Streams") or "")

		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"red": self.stopStreams,
			"up": self["ScrollLabel"].pageUp,
			"down": self["ScrollLabel"].pageDown
		})

	def stopStreams(self):
		streamServer = enigma.eStreamServer.getInstance()
		if not streamServer:
			return

		for x in streamServer.getConnectedClients():
			streamServer.stopStream()

		self.close()
