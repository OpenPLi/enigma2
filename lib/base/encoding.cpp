#include <cstdio>
#include <cstdlib>
#include <lib/base/cfile.h>
#include <lib/base/encoding.h>
#include <lib/base/eerror.h>
#include <lib/base/eenv.h>

eDVBTextEncodingHandler encodingHandler;  // the one and only instance
int defaultEncodingTable=1;   // the one and only instance

inline char toupper(char c)
{
	switch (c)
	{
		case 'a' ... 'z':
			return c-32;
	}
	return c;
}

eDVBTextEncodingHandler::eDVBTextEncodingHandler()
{
	std::string file = eEnv::resolve("${sysconfdir}/enigma2/encoding.conf");
	if (::access(file.c_str(), R_OK) < 0)
	{
		/* no personalized encoding.conf, fallback to the system default */
		file = eEnv::resolve("${datadir}/enigma2/encoding.conf");
	}
	CFile f(file.c_str(), "rt");
	if (f)
	{
		char *line = (char*) malloc(256);
		size_t bufsize=256;
		char countrycode[256];
		char *s_table = (char*) malloc(256);
		char *lowerline = (char*) malloc(256);
		while( getline(&line, &bufsize, f) != -1 )
		{
			if ( line[0] == '#' )
				continue;
			int j=0;
			for(int i=0;line[i];i++){
				if(line[i] == '#'){
					line[i]=0;
					lowerline[j]=0;
					break;
				}
				if(j==0 && line[i] > 0 && line[i] < ' ')
					continue;
				if(line[i] >= 'A' && line[i] <= 'Z')
					lowerline[j++]=line[i]+0x20;
				else
					lowerline[j++]=line[i];
			}
			lowerline[j]=0;
			if( j == 0 )
				continue;

			int tsid, onid, encoding;

			if ( (sscanf( lowerline, "0x%x 0x%x iso8859-%d", &tsid, &onid, &encoding ) == 3 )
				||(sscanf( lowerline, "%d %d iso8859-%d", &tsid, &onid, &encoding ) == 3 ) )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=encoding;
			else if ( (sscanf( lowerline, "0x%x 0x%x iso%d", &tsid, &onid, &encoding ) == 3 && encoding == 6937 )
					||(sscanf( line, "%d %d iso%d", &tsid, &onid, &encoding ) == 3 && encoding == 6937 ) )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=0;
			else if ( ((sscanf( lowerline, "0x%x 0x%x gb%d", &tsid, &onid, &encoding ) == 3 )
					&& ((encoding == 18030) || (encoding == 2312)))
			        ||((sscanf( lowerline, "%d %d gb%d", &tsid, &onid, &encoding ) == 3 )
					&& ((encoding == 18030) || (encoding == 2312)))
			        ||((sscanf( lowerline, "0x%x 0x%x cp%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 936)
			        ||((sscanf( lowerline, "%d %d cp%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 936)
			        ||((sscanf( lowerline, "0x%x 0x%x %s", &tsid, &onid, s_table ) == 3 )
					&& strcasecmp(s_table,"gbk")==0)
			        ||((sscanf( lowerline, "%d %d %s", &tsid, &onid, s_table ) == 3 )
					&& strcasecmp(s_table,"gbk")==0)
				 )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=GB18030_ENCODING;
			else if ( ((sscanf( lowerline, "0x%x 0x%x big%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 5)
				||((sscanf( lowerline, "%d %d big%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 5)
			        ||((sscanf( lowerline, "0x%x 0x%x cp%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 950)
				||((sscanf( lowerline, "%d %d cp%d", &tsid, &onid, &encoding ) == 3 )
					&& encoding == 950)
				 )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=BIG5_ENCODING;
			else if ( ((sscanf( lowerline, "0x%x 0x%x %s", &tsid, &onid, s_table ) == 3 )
						&& (strcasecmp(s_table, "utf8")==0 || strcasecmp(s_table, "utf-8")==0 ) )
					||((sscanf( lowerline, "%d %d %s", &tsid, &onid, s_table ) == 3 )
						&&  (strcasecmp(s_table, "utf8")==0 || strcasecmp(s_table, "utf-8")==0 ) )
				 )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=UTF8_ENCODING;
			else if ( ((sscanf( lowerline, "0x%x 0x%x %s", &tsid, &onid, s_table ) == 3 )
						&& strcasecmp(s_table, "utf16be")==0)
					||((sscanf( lowerline, "%d %d %s", &tsid, &onid, s_table ) == 3 )
						&& strcasecmp(s_table, "utf16be")==0)
				 )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=UTF16BE_ENCODING;
			else if ( ((sscanf( lowerline, "0x%x 0x%x %s", &tsid, &onid, s_table ) == 3 )
						&& strcasecmp(s_table, "utf16le")==0)
					||((sscanf( lowerline, "%d %d %s", &tsid, &onid, s_table ) == 3 )
						&& strcasecmp(s_table, "utf16le")==0)
				 )
				m_TransponderDefaultMapping[(tsid<<16)|onid]=UTF16LE_ENCODING;
			else if ( (sscanf( line, "0x%x 0x%x", &tsid, &onid ) == 2 )
					||(sscanf( line, "%d %d", &tsid, &onid ) == 2 ) )
				m_TransponderUseTwoCharMapping.insert((tsid<<16)|onid);
			else if ( sscanf( lowerline, "%s iso8859-%d", countrycode, &encoding ) == 2)
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=encoding;
			   }
                           else
				defaultEncodingTable=encoding;
			}
			else if ( (sscanf( lowerline, "%s gb%d", countrycode, &encoding ) == 2 && encoding == 18030)
				  ||(sscanf( lowerline, "%s gb%d", countrycode, &encoding ) == 2 && encoding == 2312)
				  ||(sscanf( lowerline, "%s cp%d", countrycode, &encoding ) == 2 && encoding == 936))
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=GB18030_ENCODING;
			   }
                           else
				defaultEncodingTable=GB18030_ENCODING;
			}
			else if ( (sscanf( lowerline, "%s big%d", countrycode, &encoding ) == 2 && encoding ==5)
				||(sscanf( lowerline, "%s cp%d", countrycode, &encoding ) == 2 && encoding == 950))
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=BIG5_ENCODING;
			   }
                           else
				defaultEncodingTable=BIG5_ENCODING;
			}
			else if ( sscanf( lowerline, "%s %s", countrycode, s_table ) == 2 &&
				  strcasecmp(s_table, "utf8")==0)
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=UTF8_ENCODING;
			   }
                           else
				defaultEncodingTable=UTF8_ENCODING;
			}
			else if ( sscanf( lowerline, "%s %s", countrycode, s_table ) == 2 &&
				  (strcasecmp(s_table, "utf16be")==0 || strcasecmp(s_table, "unicode")==0) )
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=UTF16BE_ENCODING;
			   }
                           else
				defaultEncodingTable=UTF16BE_ENCODING;
			}
			else if ( sscanf( lowerline, "%s %s", countrycode, s_table ) == 2 &&
				  strcasecmp(s_table, "utf16le")==0)
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=UTF16LE_ENCODING;
			   }
                           else
				defaultEncodingTable=UTF16LE_ENCODING;
			}
			else if ( sscanf( lowerline, "%s iso%d", countrycode, &encoding ) == 2 && encoding == 6937 )
			{
			   if ( countrycode[0] != '*' ){
				countrycode[0]=toupper(countrycode[0]);
				countrycode[1]=toupper(countrycode[1]);
				countrycode[2]=toupper(countrycode[2]);
				m_CountryCodeDefaultMapping[countrycode]=0;
			   }
                           else
				defaultEncodingTable=0;
			}
			else
				eDebug("[eDVBTextEncodingHandler] encoding.conf: couldn't parse %s", line);
		}
		free(line);
		free(lowerline);
		free(s_table);
	}
	else
		eDebug("[eDVBTextEncodingHandler] couldn't open %s: %m", file.c_str());
}

void eDVBTextEncodingHandler::getTransponderDefaultMapping(int tsidonid, int &table)
{
	std::map<int, int>::iterator it =
		m_TransponderDefaultMapping.find(tsidonid);
	if ( it != m_TransponderDefaultMapping.end() )
		table = it->second;
}

bool eDVBTextEncodingHandler::getTransponderUseTwoCharMapping(int tsidonid)
{
	return m_TransponderUseTwoCharMapping.find(tsidonid) != m_TransponderUseTwoCharMapping.end();
}

int eDVBTextEncodingHandler::getCountryCodeDefaultMapping( const std::string &country_code )
{
	std::map<std::string, int>::iterator it =
		m_CountryCodeDefaultMapping.find(country_code);
	if ( it != m_CountryCodeDefaultMapping.end() )
		return it->second;
	return defaultEncodingTable;
}
