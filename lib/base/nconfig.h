#ifndef __lib_base_nconfig_h_
#define __lib_base_nconfig_h_

#include <string>
#include <stdbool.h>

class eConfigManager
{
protected:
	static eConfigManager *instance;
	static eConfigManager *getInstance();

	virtual std::string getConfig(const char *key) = 0;

public:
	eConfigManager();
	virtual ~eConfigManager();

	static std::string getString(const char *key, const char *defaultvalue = "");
	static std::string getString(const std::string &key, const char *defaultvalue = "");
	static int getInt(const char *key, int defaultvalue = 0);
	static bool getBool(const char *key, bool defaultvalue = false);
};

#endif /* __lib_base_nconfig_h_ */
