from Components.Converter.EventName import EventName

class RatingSort(EventName):
	def __init__(self, type):
		EventName.__init__(self, "Rating")

	def getText(self):
		if not getattr(self.source, "ratingSortActive", False):
			return ""
		return EventName.getText(self)

	text = property(getText)