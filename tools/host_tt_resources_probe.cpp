#include "renegade_tt_resources.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" {
void *resources_create() { return new RenegadeTTResources; }
void resources_destroy(void *state) { delete static_cast<RenegadeTTResources *>(state); }
void resources_reset(void *state) { static_cast<RenegadeTTResources *>(state)->Reset(); }
int resources_receive(void *state, const unsigned char *data, unsigned bits, unsigned prefix) {
    if (bits > 4000 || prefix > 7) return 0;
    cBitPacker packet;
    if (prefix) packet.Add_Bits(0, prefix);
    for (unsigned bit = 0; bit < bits; ++bit)
        packet.Add_Bits((data[bit / 8] >> (7 - bit % 8)) & 1, 1);
    ULONG ignored = 0;
    if (prefix) packet.Get_Bits(ignored, prefix);
    return static_cast<RenegadeTTResources *>(state)->Receive(packet);
}
unsigned resources_groups(void *state) { return static_cast<RenegadeTTResources *>(state)->Get_Groups().size(); }
unsigned resources_remaining(void *state) { return static_cast<RenegadeTTResources *>(state)->Get_Remaining(); }
unsigned resources_generation(void *state) { return static_cast<RenegadeTTResources *>(state)->Get_Generation(); }
unsigned resources_id(void *state, unsigned index) {
    return static_cast<RenegadeTTResources *>(state)->Get_Groups().at(index).Id;
}
const char *resources_name(void *state, unsigned index) {
    return static_cast<RenegadeTTResources *>(state)->Get_Groups().at(index).Name.c_str();
}
unsigned resources_count(void *state, unsigned index) {
    return static_cast<RenegadeTTResources *>(state)->Get_Groups().at(index).Packages.size();
}
unsigned resources_package(void *state, unsigned index, unsigned package) {
    return static_cast<RenegadeTTResources *>(state)->Get_Groups().at(index).Packages.at(package);
}
}
