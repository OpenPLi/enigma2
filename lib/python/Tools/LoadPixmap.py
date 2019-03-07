from enigma import loadPNG, loadJPG

# if cached is not supplied, defaults to caching PNGs and not caching JPGs
def LoadPixmap(path, desktop=None, cached=None):
	if path[-4:] == ".png":
		ptr = loadPNG(path, 0, 0 if cached == 0 else 1)
	elif path[-4:] == ".jpg":
		ptr = loadJPG(path, 0, 1 if cached == 1 else 0)
	elif path[-1:] == ".":
		alpha = loadPNG(path + "a.png", 0)
		ptr = loadJPG(path + "rgb.jpg", alpha, 0)
	else:
		raise Exception("neither .png nor .jpg, please fix file extension")
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
