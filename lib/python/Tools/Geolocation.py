from json import loads
from urllib2 import URLError, urlopen

from Components.config import ConfigYesNo, config

# Data available from http://ip-api.com/json/:
#
# 	Name		Description				Example			Type	Collected
# 	--------------	--------------------------------------	----------------------	------	---------
# 	status		success or fail				success			string	Yes
# 	message		Included only when status is fail. Can
# 			be one of the following: private range,
# 			reserved range, invalid query		invalid query		string	Yes
# 	continent	Continent name				North America		string	No
# 	continentCode	Two-letter continent code		NA			string	No
# 	country		Country name				United States		string	No
# 	countryCode	Two-letter country code
# 			ISO 3166-1 alpha-2			US			string	No
# 	region		Region/state short code (FIPS or ISO)	CA or 10		string	No
# 	regionName	Region/state				California		string	No
# 	city		City					Mountain View		string	No
# 	district	District (subdivision of city)		Old Farm District	string	No
# 	zip		Zip code				94043			string	No
# 	lat		Latitude				37.4192			float	No
# 	lon		Longitude				-122.0574		float	No
# 	timezone	City timezone				America/Los_Angeles	string	Yes
# 	currency	National currency			USD			string	No
# 	isp		ISP name				Google			string	No
# 	org		Organization name			Google			string	No
# 	as		AS number and organization, separated
# 			by space (RIR). Empty for IP blocks 
# 			not being announced in BGP tables.	AS15169 Google Inc.	string	No
# 	asname		AS name (RIR). Empty for IP blocks not
# 			being announced in BGP tables.		GOOGLE			string	No
# 	reverse		Reverse DNS of the IP
# 			(Not fetched as it delays response)	wi-in-f94.1e100.net	string	No
# 	mobile		Mobile (cellular) connection		true			bool	No
# 	proxy		Proxy, VPN or Tor exit address		true			bool	Yes
# 	hosting		Hosting, colocated or data center	true			bool	No
# 	query		IP used for the query			173.194.67.94		string	No

config.misc.enableGeolocation = ConfigYesNo(default=True)
geolocation = {}


def InitGeolocation():
	global geolocation
	if config.misc.enableGeolocation.value:
		if len(geolocation) == 0:
			try:
				response = urlopen("http://ip-api.com/json/?fields=status,message,timezone,proxy", data=None, timeout=10).read()
				# print "[Geolocation] DEBUG:", response
				if response:
					geolocation = loads(response)
				status = geolocation.get("status", None)
				if status and status == "success":
					print "[Geolocation] Geolocation data initialised."
					config.misc.enableGeolocation.value = False
					config.misc.enableGeolocation.save()
				else:
					print "[Geolocation] Error: Geolocation lookup returned a '%s' status!  Message '%s' returned." % (status, geolocation.get("message", None))
			except URLError as err:
				if hasattr(err, 'code'):
					print "[Geolocation] Error: Geolocation data not available! (Code: %s)" % err.code
				if hasattr(err, 'reason'):
					print "[Geolocation] Error: Geolocation data not available! (Reason: %s)" % err.reason
			except ValueError:
				print "[Geolocation] Error: Geolocation data returned can not be processed!"
			except Exception:
				print "[Geolocation] Error: Geolocation network connection failed!"
		else:
			print "[Geolocation] Note: Geolocation has already been run for this boot."
	else:
		geolocation = {}
		print "[Geolocation] Warning: Geolocation has been disabled by user configuration!"


def RefreshGeolocation():
	global geolocation
	geolocation = {}
	InitGeolocation()
