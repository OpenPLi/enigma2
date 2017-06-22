from Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Sources.StreamService import StreamServiceList
from Components.Button import Button
from Components.Label import Label
from enigma import eStreamServer
from ServiceReference import ServiceReference
import socket
try:
	from Plugins.Extensions.OpenWebif.controllers.stream import streamList
except:
	streamList = []

class StreamingClientsInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.streamServer = eStreamServer.getInstance()
		self.clients = []
		self["menu"] = MenuList(self.clients)
		self["key_red"] = Button(_("Close"))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["info"] = Label()
		self.updateClients()
		self["actions"] = ActionMap(["ColorActions", "SetupActions"],
		{
			"cancel": self.close,
			"ok": self.stopCurrentStream,
			"red": self.close,
			"green": self.stopAllStreams,
			"yellow": self.stopCurrentStream
		})

	def updateClients(self):
		self["key_green"].setText("")
		self["key_yellow"].setText("")
		self.setTitle(_("Streaming clients info"))
		self.clients = []
		if self.streamServer:
			for x in self.streamServer.getConnectedClients():
				service_name = ServiceReference(x[1]).getServiceName() or "(unknown service)"
				ip = x[0]
				if int(x[2]) == 0:
					strtype = "S"
				else:
					strtype = "T"
				try:
					raw = socket.gethostbyaddr(ip)
					ip = raw[0]
				except:
					pass
				info = ("%s %-8s %s") % (strtype, ip, service_name)
				self.clients.append((info, (x[0], x[1])))
		if StreamServiceList and streamList:
			for x in StreamServiceList:
				ip = "ip n/a"
				service_name = "(unknown service)"
				for stream in streamList:
					if hasattr(stream, 'getService') and stream.getService() and stream.getService().__deref__() == x:
						service_name = ServiceReference(stream.ref.toString()).getServiceName()
						ip = stream.clientIP or ip
			info = ("T %s %s %s") % (ip, service_name, _("(VU+ type)"))
			self.clients.append((info,(-1, x)))
		self["menu"].setList(self.clients)
		if self.clients:
			self["info"].setText("")
			self["key_green"].setText(_("Stop all streams"))
			self["key_yellow"].setText(_("Stop current stream"))
		else:
			self["info"].setText(_("No stream clients"))

	def stopCurrentStream(self):
		self.updateClients()
		if self.clients:
			client = self["menu"].l.getCurrentSelection()
			if client:
				self.session.openWithCallback(self.stopCurrentStreamCallback, MessageBox, client[0] +" \n\n" + _("Stop current stream") + "?", MessageBox.TYPE_YESNO)

	def stopCurrentStreamCallback(self, answer):
		if answer:
			client = self["menu"].l.getCurrentSelection()
			if client:
				if client[1][0] != -1:
					if self.streamServer:
						for x in self.streamServer.getConnectedClients():
							if client[1][0] == x[0] and client[1][1] == x[1]:
								if not self.streamServer.stopStreamClient(client[1][0], client[1][1]):
									self.session.open(MessageBox,  client[0] +" \n\n" + _("Error stop stream!"), MessageBox.TYPE_WARNING)
				elif StreamServiceList and streamList:
					self.session.open(MessageBox,  client[0] +" \n\n" + _("Not yet implemented!"), MessageBox.TYPE_WARNING)
					# TODO
					#for x in streamList[:]:
					#	if hasattr(x, 'getService') and x.getService() and x.getService().__deref__() == client[1][1]:
					#		x.execEnd()
					#		if x in streamList:
					#			streamList.remove(x)
				self.updateClients()

	def stopAllStreams(self):
		self.updateClients()
		if self.clients:
			self.session.openWithCallback(self.stopAllStreamsCallback, MessageBox, _("Stop all streams") + "?", MessageBox.TYPE_YESNO)

	def stopAllStreamsCallback(self, answer):
		if answer:
			if self.streamServer:
				for x in self.streamServer.getConnectedClients():
					self.streamServer.stopStream()
			# TODO
			#if StreamServiceList and streamList:
			#	for x in streamList[:]:
			#		if hasattr(x, 'execEnd'):
			#			x.execEnd()
			#			if x in streamList:
			#				streamList.remove(x)
			self.updateClients()
			if not self.clients:
				self.close()
