from enigma import loadPNG, loadJPG, loadSVG

# If cached is not supplied, LoadPixmap defaults to caching PNGs and not caching JPGs
# Split alpha channel JPGs are never cached as the C++ layer's caching is based on
# a single file per image in the cache
def LoadPixmap(path, desktop=None, cached=None, _size=None):
	if path[-4:] == ".png":
		# cache unless caller explicity requests to not cache
		ptr = loadPNG(path, 0, 0 if cached == False else 1)
	elif path[-4:] == ".jpg":
		# don't cache unless caller explicity requests caching
		ptr = loadJPG(path, 1 if cached == True else 0)
	elif path[-4:] == ".svg":
		ptr = loadSVG(path, 0 if cached == False else 1, _size.height() if _size else 0, _size.width() if _size else 0)
	elif path[-1:] == ".":
		# caching mechanism isn't suitable for multi file images, so it's explicitly disabled
		alpha = loadPNG(path + "a.png", 0, 0)
		ptr = loadJPG(path + "rgb.jpg", alpha, 0)
	else:
		raise Exception("Neither .png nor .jpg nor .svg, please fix file extension")
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
