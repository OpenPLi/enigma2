from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel


class TextBox(Screen):
	def __init__(self, session, text="", title=None, pigless=False, label=None):
		Screen.__init__(self, session)
		if pigless:
			self.skinName = ["TextBoxPigLess", "TextBox"]
		self.text = text
		self.label = label if label else "text"
		self[self.label] = ScrollLabel(self.text)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
				{
					"cancel": self.close,
					"ok": self.close,
					"up": self[self.label].pageUp,
					"down": self[self.label].pageDown,
				}, -1)

		if title:
			self.setTitle(title)
