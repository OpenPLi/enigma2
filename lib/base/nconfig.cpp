#include <lib/base/nconfig.h>

eConfigManager *eConfigManager::instance = NULL;

eConfigManager::eConfigManager()
{
	instance = this;
}

eConfigManager::~eConfigManager()
{
	instance = NULL;
}

eConfigManager *eConfigManager::getInstance()
{
	return instance;
}

std::string eConfigManager::getString(const char *key, const char *defaultvalue)
{
	return instance ? instance->getConfig(key) : defaultvalue;
}

std::string eConfigManager::getString(const std::string &key, const char *defaultvalue /*= ""*/)
{
	return getString(key.c_str());
}

int eConfigManager::getInt(const char *key, int defaultvalue)
{
	std::string value = getString(key);
	return (value != "") ? atoi(value.c_str()) : defaultvalue;
}

bool eConfigManager::getBool(const char *key, bool defaultvalue)
{
	std::string value = getString(key);
	if (value == "True" || value == "true") return true;
	if (value == "False" || value == "false") return false;
	return defaultvalue;
}
