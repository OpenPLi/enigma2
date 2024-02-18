from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from enigma import iServiceInformation
from Tools.GetEcmInfo import GetEcmInfo
from Components.Converter.Poll import Poll


class CryptoInfo(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)

		self.type = type
		self.active = False
		self.visible = config.usage.show_cryptoinfo.value
		self.textvalue = ""
		self.poll_interval = 1000
		self.poll_enabled = True
		self.ecmdata = GetEcmInfo()

	@cached
	def getText(self):
		if not config.usage.show_cryptoinfo.value:
			self.visible = False
			data = ''
		else:
			self.visible = True
			if self.type == "VerboseInfo":
				data = self.ecmdata.getEcmData()[0]
			elif self.type == "FullInfo":
				textvalue = ""
				server = ""
				service = self.source.service
				if service:
					info = service and service.info()
					if info:
						try:
							if info.getInfoObject(iServiceInformation.sCAIDs):
								ecm_info = self.ecmdata.getInfoRaw()
								if ecm_info:
									# caid
									caid = "%0.4X" % int(ecm_info.get('caid', ecm_info.get('CAID', '0')),16)
									#pid
									pid = "%0.4X" % int(ecm_info.get('pid', ecm_info.get('ECM PID', '0')),16)
									# oscam
									prov = "%0.6X" % int(ecm_info.get('provid', ecm_info.get('prov', ecm_info.get('Provider', '0'))),16)

									if ecm_info.get("ecm time", "").find("msec") > -1:
										ecm_time = ecm_info.get("ecm time", "")
									else:
										ecm_time = ecm_info.get("ecm time", "").replace(".","").lstrip("0") + " msec"
										
									#from (oscam)
									from_item = ecm_info.get("from", "")
									from_splitted = from_item.split(":")
									#protocol
									protocol = ecm_info.get("protocol", "")
									# server
									server = from_splitted[0].strip()
									#port
									port = from_splitted[1].strip() if len(from_splitted) > 1 else ""
									# source
									if from_splitted[0].strip() == "local":
										source = "sci"
									else:
										source = "net"
									# hops
									hops = ecm_info.get("hops", "")
									#system
									system = ecm_info.get("system", "")
									#provider
									provider = ecm_info.get("provider", "")
									# reader
									reader = ecm_info.get("reader", "")
									if source == "emu":
										textvalue = "%s - %s (Caid: %s, Prov: %s,)" % (source, caid, caid, prov)
									#new oscam ecm.info with port parametr
									elif reader != "" and source == "net" and port != "":
										textvalue = "%s - Caid: %s, Prov: %s, Reader: %s, %s (%s:%s@%s) - %s" % (source, caid, prov, reader, protocol, server, port, hops, ecm_time.replace('msec', 'ms'))
									elif reader != "" and source == "net":
										textvalue = "%s - Caid: %s, Prov: %s, Reader: %s, %s (%s@%s) - %s" % (source, caid, prov, reader, protocol, server, hops, ecm_time.replace('msec', 'ms'))
									elif reader != "" and source != "net":
										textvalue = "%s - Caid: %s, Prov: %s, Reader: %s, %s (local) - %s" % (source, caid, prov, reader, protocol, ecm_time.replace('msec', 'ms'))
									elif server == "" and port == "" and protocol != "":
										textvalue = "%s - Caid: %s, Prov: %s, %s - %s" % (source, caid, prov, protocol, ecm_time.replace('msec', 'ms'))
									elif server == "" and port == "" and protocol == "":
										textvalue = "%s - Caid: %s - %s, Prov: %s" % (source, prov, caid, ecm_time.replace('msec', 'ms'))
									else:
										try:
											textvalue = "%s - Caid: %s, Prov: %s, %s (%s:%s) - %s" % (source, caid, prov, protocol, server, port, ecm_time.replace('msec','ms'))
										except:
											pass
								else:
									textvalue = "No parse cannot emu"
							else:
								textvalue = "Free-to-air"
						except:
							pass
				return textvalue
			else:
				data = self.ecmdata.getInfo(self.type)
		return data
	text = property(getText)
