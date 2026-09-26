#include "renegade_client_identity.h"
#include "global.h"
#include "md5.h"
#include <stdio.h>
#include <string.h>

static_assert(sizeof(UINT4) == 4, "MD5 requires 32-bit words on host and ARM");

namespace {
void Digest(const char *text, char *hex)
{
    MD5_CTX context;
    unsigned char digest[16];
    MD5Init(&context);
    MD5Update(&context, reinterpret_cast<unsigned char *>(const_cast<char *>(text)),
        static_cast<unsigned int>(strlen(text)));
    MD5Final(digest, &context);
    const char digits[] = "0123456789abcdef";
    for (unsigned i = 0; i < sizeof(digest); ++i) {
        hex[i * 2] = digits[digest[i] >> 4];
        hex[i * 2 + 1] = digits[digest[i] & 15];
    }
    hex[32] = 0;
}
}

bool RenegadeClientIdentity::Serial_Hash(const char *seed, char (&hash)[33])
{
    memset(hash, 0, sizeof(hash));
    if (!seed || strnlen(seed, 33) != 32) return false;
    for (unsigned i = 0; i < 32; ++i)
        if (!(seed[i] >= '0' && seed[i] <= '9') &&
            !(seed[i] >= 'a' && seed[i] <= 'f')) return false;
    Digest(seed, hash);
    return true;
}

bool RenegadeClientIdentity::Response(const char *seed, const char *challenge,
    uint32_t nonce, char (&response)[73])
{
    memset(response, 0, sizeof(response));
    if (!challenge || strnlen(challenge, 129) > 128 ||
        !Serial_Hash(seed, *reinterpret_cast<char (*)[33]>(response))) return false;
    // TT b9000's legacy challenge: MD5(seed), nonce hex, MD5(seed +
    // decimal(nonce modulo 65535) + challenge). The seed is MD5(serial).
    char material[32 + 5 + 128 + 1];
    snprintf(material, sizeof(material), "%s%u%s", seed,
        static_cast<unsigned>(nonce % 65535u), challenge);
    snprintf(response + 32, 9, "%08x", static_cast<unsigned>(nonce));
    Digest(material, response + 40);
    volatile char *wipe = material;
    for (unsigned i = 0; i < sizeof(material); ++i) wipe[i] = 0;
    return true;
}
