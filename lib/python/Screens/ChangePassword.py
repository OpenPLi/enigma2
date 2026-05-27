from enigma import eConsoleAppContainer, checkLogin
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Components.config import getConfigListEntry, ConfigText


class ChangePasswordScreen(Setup):

	def __init__(self, session, args=0):
		self.skinName = ["Setup"]
		Setup.__init__(self, session)
		self.skinName = ["Setup"]
		self.setTitle(_("Change Root Password"))

	def createSetup(self):
		self.currentPassword = ConfigText(default="", fixed_size=False)
		self.newPassword = ConfigText(default="", fixed_size=False)
		self.repeatPassword = ConfigText(default="", fixed_size=False)
		self.isPasswordSet = self.checkIfPasswordisSet()
		self.list = []
		if self.isPasswordSet:
			self.list.append(getConfigListEntry(_('Enter current password'), self.currentPassword))
		self.list.append(getConfigListEntry(_('Enter new password'), self.newPassword))
		self.list.append(getConfigListEntry(_('Repeat new password'), self.repeatPassword))
		self["config"].list = self.list

	def checkIfPasswordisSet(self):
		with open('/etc/shadow', 'r') as filehandler:
			for line in filehandler.readlines():
				if line.startswith('root:'):
					return line.startswith('root:$')

	def keySave(self):
		if self.newPassword.value != self.repeatPassword.value:
			message = _("New password not the same as the repeat password")
		elif not self.isPasswordSet or checkLogin('root', self.currentPassword.value):
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(self.runFinished)
			self.container.dataAvail.append(self.dataAvail)
			if self.newPassword.value:
				if  self.container.execute("passwd root") == 0:
					message = _("Successfully changed password for root user")
				else:
					message = _("Unable to change password for root user")
			elif self.container.execute("passwd -d root") == 0:
				message = _("Successfully cleared password for root user")
			else:
				message = _("Unable to clear password for root user")
		else:
			message = _("Current password incorrect")
		self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=5, simple=True)

	def dataAvail(self, data):
		if data.find(b'password'):
			self.container.write("%s\n" % self.newPassword.value)

	def runFinished(self, retval):
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container
		if retval == 0:
			self.close()
