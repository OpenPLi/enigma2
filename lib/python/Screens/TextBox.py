from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText


class TextBox(Screen):
	def __init__(self, session, text="", title=None, pigless=False, label=None, buttons=None, disableOK=False):
		Screen.__init__(self, session)
		if pigless:
			self.skinName = ["TextBoxPigLess", "TextBox"]
		self.text = text
		self.label = label if label else "text"
		self[self.label] = ScrollLabel(self.text)

		if buttons is None:
			buttons = {"red": (_("Cancel"), None)}

		actions = {
			"cancel": self.close,
			"up": self[self.label].pageUp,
			"down": self[self.label].pageDown,
		}
		if not disableOK:
			actions["ok"] = self.close

		for color in ("red", "green", "yellow", "blue"):
			button = buttons.get(color)
			self["key_" + color] = StaticText(button[0] if button else "")
			if button:
				if button[1] is None:
					actions[color] = self.close
				else:
					actions[color] = lambda value=button[1]: self.close(value)

		self["actions"] = ActionMap(
			["OkCancelActions", "DirectionActions", "ColorActions"],
			actions, -1)

		if title:
			self.setTitle(title)
