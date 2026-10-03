#ifndef RENEGADE_A35_LEVEL_LOAD_STATUS_H
#define RENEGADE_A35_LEVEL_LOAD_STATUS_H

#include <stdint.h>

enum A35LevelLoadFailure : uint32_t {
    A35_LOAD_NO_FAILURE = 0,
    A35_LOAD_DYNAMIC_UNAVAILABLE = 1,
    A35_LOAD_DYNAMIC_OPEN_FAILED = 2,
    A35_LOAD_DYNAMIC_SUBSYSTEM_FAILED = 3,
    A35_LOAD_STATIC_UNAVAILABLE = 4,
    A35_LOAD_STATIC_OPEN_FAILED = 5,
    A35_LOAD_STATIC_SUBSYSTEM_FAILED = 6,
    A35_LOAD_DYNAMIC_INFO_MISSING = 7,
    A35_LOAD_DYNAMIC_DATA_MISSING = 8
};

// Reset only before a new load, with no previous loader still running.
// No failure recorded is not a certificate of complete level validity.
void A35_Level_Load_Reset_Failure();
void A35_Level_Load_Record_Failure(A35LevelLoadFailure failure);
A35LevelLoadFailure A35_Level_Load_Get_Failure();

#endif
