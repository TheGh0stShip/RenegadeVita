#include "renegade_client_identity.h"
#include "a31_client_connect_boundary.h"
#include "ffactory.h"
#include "wwfile.h"
#include "wwstring.h"
#include "renegade_tt_client_greeting.h"
#include <errno.h>
#include <stdio.h>
#if defined(__vita__)
#include <psp2/kernel/rng.h>
#else
#include <sys/random.h>
#endif

namespace {
bool GreetingProbe = false;

void Wipe(char *data, unsigned size)
{
    volatile char *wipe = data;
    for (unsigned i = 0; i < size; ++i) wipe[i] = 0;
}

bool Load_Seed(char (&seed)[34])
{
    bool loaded = false;
    // Use only the writable rooted factory: no retail/MIX/mod fallback.
    FileClass *file = _TheWritingFileFactory ?
        _TheWritingFileFactory->Get_File("user/config/tt-identity-v1.txt") : nullptr;
    if (file) {
        if (file->Open(FileClass::READ)) {
            loaded = file->Read(seed, sizeof(seed)) == 33 && seed[32] == '\n';
            file->Close();
        }
        _TheWritingFileFactory->Return_File(file);
    }
    seed[32] = 0;
    return loaded;
}
}

void Renegade_Arm_TT_Greeting_Probe() { GreetingProbe = true; }

bool Renegade_Append_Client_Greeting(BitStreamClass &packet, bool remote_client, bool *modern)
{
    if (modern) *modern = false;
    const bool requested = GreetingProbe;
    GreetingProbe = false;
    if (!requested) return true;
    if (!remote_client) return false;
    char seed[34] = {}, hash[33] = {};
    // No fabricated Windows hardware identifier or borrowed attestation.
    const bool ok = Load_Seed(seed) && RenegadeClientIdentity::Serial_Hash(seed, hash) &&
        Renegade_Write_TT_Client_Greeting(packet, hash, "");
    Wipe(seed, sizeof(seed));
    Wipe(hash, sizeof(hash));
    if (modern) *modern = ok;
    fprintf(stderr, "client-connect: experimental TT greeting %s; identity redacted; gameplay unverified\n",
        ok ? "prepared" : "failed");
    return ok;
}

bool Renegade_Answer_Serial_Challenge(const char *challenge, StringClass &response)
{
    response = "";
    char seed[34] = {};
    const bool loaded = Load_Seed(seed);
    uint32_t nonce = 0;
#if defined(__vita__)
    const bool random_ok = sceKernelGetRandomNumber(&nonce, sizeof(nonce)) == 0;
#else
    ssize_t count;
    do { count = getrandom(&nonce, sizeof(nonce), 0); } while (count < 0 && errno == EINTR);
    const bool random_ok = count == sizeof(nonce);
#endif
    char answer[73] = {};
    const bool ok = loaded && random_ok &&
        RenegadeClientIdentity::Response(seed, challenge, nonce, answer);
    if (ok) response = answer;
    Wipe(seed, sizeof(seed));
    Wipe(answer, sizeof(answer));
    if (!ok) A31ClientConnect::Identity_Failed();
    else fprintf(stderr, "client-connect: serial challenge response prepared (redacted)\n");
    return ok;
}
