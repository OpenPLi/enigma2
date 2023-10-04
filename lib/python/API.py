session = None

class API(object):
	def __init__(self):
		self.__session = None
		
	def setSession(self, current_session):
		global session
		session = current_session