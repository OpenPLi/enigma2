#ifndef CRC32_H
#define CRC32_H

#include <cstdint>
#include <cstdio>

/* $Id: crc32.h,v 1.1 2003-10-17 15:35:49 tmbinc Exp $ */

extern const uint32_t crc32_table[256];

namespace crc32
{
/* Return a 32-bit CRC of the contents of the buffer. */
uint32_t crc32(uint32_t val, const void *ss, int len);

/* Return crc32 (seed from 0) from buffer */
uint32_t calculate_crc_hash(const uint8_t *data, int size);

/* Return crc32 (seed from 0) from FILE pointer, limited by size */
uint32_t calculate_file_crc_hash(FILE *fp, int size);

} // namespace crc32


#endif
