#include "renegade_client_identity.h"
#include "renegade_client_message.h"
extern "C" bool identity_hash(const char *seed, char *result)
{
    return RenegadeClientIdentity::Serial_Hash(seed,
        *reinterpret_cast<char (*)[33]>(result));
}
extern "C" void redact_admission(char *text)
{
    Renegade_Redact_Admission_Message(text);
}
extern "C" bool identity_response(const char *seed, const char *challenge,
    unsigned nonce, char *result)
{
    return RenegadeClientIdentity::Response(seed, challenge, nonce,
        *reinterpret_cast<char (*)[73]>(result));
}
