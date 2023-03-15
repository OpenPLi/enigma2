from Components.Converter.StringList import StringList

from enigma import eListbox


class TemplatedMultiContent(StringList):
	"""Turns a python tuple list into a multi-content list which can be used in a listbox renderer."""

	def __init__(self, args):
		StringList.__init__(self, args)
		from enigma import BT_SCALE, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eListboxPythonMultiContent, gFont
		from skin import parseFont, getSkinFactor
		from Components.MultiContent import MultiContentEntryPixmap, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryProgressPixmap, MultiContentEntryText, MultiContentTemplateColor
		f = getSkinFactor()
		loc = locals()
		del loc["self"]  # Cleanup locals a bit.
		del loc["args"]
		self.active_style = None
		self.template = eval(args, {}, loc)
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		assert "fonts" in self.template
		assert "itemHeight" in self.template
		assert "template" in self.template or "templates" in self.template
		assert "template" in self.template or "default" in self.template["templates"]  # We need to have a default template.
		if "template" not in self.template:  # Default template can be ["template"] or ["templates"]["default"].
			self.template["template"] = self.template["templates"]["default"][1] # mandatory
			self.template["itemHeight"] = self.template["template"][0] # mandatory
			self.template["selectionEnabled"] = self.template["template"][2] if len(self.template["template"]) > 2 and self.template["template"][2] is not None else True  # optional. To skip use None padding.
			self.template["scrollbarMode"] = self.template["template"][3] if len(self.template["template"]) > 3 and self.template["template"][3] is not None  else "showOnDemand"  # optional. To skip use None padding.
			# if present self.template["template"][4] is a dict which should have "orientation" and "itemWidth"
			self.template["itemWidth"] =  self.template["template"][4].get("itemWidth") if len(self.template["template"]) > 4 else None # optional
			self.template["orientation"] = self.template["template"][4].get("orientation") if len(self.template["template"]) > 4 else None # optional

	def changed(self, what):
		if not self.content:
			from enigma import eListboxPythonMultiContent
			self.content = eListboxPythonMultiContent()
			for index, font in enumerate(self.template["fonts"]):  # Setup fonts (also given by source).
				self.content.setFont(index, font)
		if what[0] == self.CHANGED_SPECIFIC and what[1] == "style":  # If only template changed, don't reload list.
			pass
		elif self.source:
			self.content.setList(self.source.list)
		self.setTemplate()
		self.downstream_elements.changed(what)

	def setTemplate(self):
		if self.source:
			style = self.source.style
			if style == self.active_style:
				return
			templates = self.template.get("templates")  # If skin defined "templates", that means that it defines multiple styles in a dict. template should still be a default.
			template = self.template.get("template")
			itemheight = self.template["itemHeight"]
			itemwidth = self.template.get("itemWidth")
			orientation = self.template.get("orientation")
			selectionEnabled = self.template.get("selectionEnabled", True)
			scrollbarMode = self.template.get("scrollbarMode", "showOnDemand")
			if templates and style and style in templates:  # If we have a custom style defined in the source, and different templates in the skin, look it up
				# "template" and "itemheight" are mandatory in a template. selectionEnabled, scrollbarMode, itemwidth, and orientation are optional.
				template = templates[style][1]
				itemheight = templates[style][0]
				if len(templates[style]) > 2 and templates[style][2] is not None:
					selectionEnabled = templates[style][2]
				if len(templates[style]) > 3 and templates[style][3] is not None:
					scrollbarMode = templates[style][3]
				if len(templates[style]) > 4 and templates[style][4] is not None and templates[style][4].get("itemWidth") is not None and templates[style][4].get("orientation") is not None:
					itemwidth = templates[style][4]["itemWidth"]
					orientation = templates[style][4]["orientation"]
				
			self.content.setTemplate(template)
			if orientation is not None and itemwidth is not None:
				self.content.setOrientation(self.orientations.get(orientation, self.orientations["orVertical"]))
				self.content.setItemWidth(int(itemwidth))
			self.content.setItemHeight(int(itemheight))
			self.selectionEnabled = selectionEnabled
			self.scrollbarMode = scrollbarMode
			self.active_style = style
