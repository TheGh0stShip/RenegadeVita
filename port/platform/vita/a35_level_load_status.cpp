#include "a35_level_load_status.h"

#include <atomic>

namespace {
std::atomic<uint32_t> first_failure{A35_LOAD_NO_FAILURE};
static_assert(sizeof(uint32_t) == 4, "load status requires explicit uint32");
}

void A35_Level_Load_Reset_Failure()
{
    first_failure.store(A35_LOAD_NO_FAILURE, std::memory_order_release);
}

void A35_Level_Load_Record_Failure(A35LevelLoadFailure failure)
{
    if (failure == A35_LOAD_NO_FAILURE) return;
    uint32_t expected = A35_LOAD_NO_FAILURE;
    first_failure.compare_exchange_strong(expected, static_cast<uint32_t>(failure),
                                         std::memory_order_release,
                                         std::memory_order_relaxed);
}

A35LevelLoadFailure A35_Level_Load_Get_Failure()
{
    return static_cast<A35LevelLoadFailure>(first_failure.load(std::memory_order_acquire));
}
