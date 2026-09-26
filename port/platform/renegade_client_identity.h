#pragma once

#include <stdint.h>

namespace RenegadeClientIdentity {
// The seed is credential material. Never log it or the generated response.
bool Serial_Hash(const char *seed, char (&hash)[33]);
bool Response(const char *seed, const char *challenge, uint32_t nonce,
    char (&response)[73]);
}

class StringClass;
class BitStreamClass;
bool Renegade_Answer_Serial_Challenge(const char *challenge, StringClass &response);
// One-shot diagnostic selection; does not advertise a complete TT game client.
void Renegade_Arm_TT_Greeting_Probe();
bool Renegade_Append_Client_Greeting(BitStreamClass &packet, bool remote_client, bool *modern = nullptr);
