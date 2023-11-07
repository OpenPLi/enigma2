class VariableText:
	"""VariableText can be used for components which have a variable text, based on any widget with setText call"""

	def __init__(self):
		object.__init__(self)
		self.message = ""
		self.instance = None

	def setText(self, text):
		try:
			self.message = str(text)
		except:
			self.message = ""
		if self.instance:
			self.instance.setText(self.message)

	def setMarkedPos(self, pos):
		if self.instance:
			self.instance.setMarkedPos(int(pos))

	def getText(self):
		return self.message

	text = property(getText, setText)

	def postWidgetCreate(self, instance):
		try:
			self.message = str(self.message)
		except:
			self.message = ""
		instance.setText(self.message)
