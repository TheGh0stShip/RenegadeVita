// Original level-load failure latch counterexamples; host evidence only.
#include "a35_level_load_status.h"
#include <cassert>

int main()
{
    A35_Level_Load_Reset_Failure();
    assert(A35_Level_Load_Get_Failure() == A35_LOAD_NO_FAILURE);
    A35_Level_Load_Record_Failure(A35_LOAD_NO_FAILURE);
    assert(A35_Level_Load_Get_Failure() == A35_LOAD_NO_FAILURE);
    for (uint32_t code = A35_LOAD_DYNAMIC_UNAVAILABLE;
         code <= A35_LOAD_DYNAMIC_DATA_MISSING; ++code) {
        A35_Level_Load_Reset_Failure();
        A35_Level_Load_Record_Failure(static_cast<A35LevelLoadFailure>(code));
        A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_DATA_MISSING);
        assert(static_cast<uint32_t>(A35_Level_Load_Get_Failure()) == code);
    }
    A35_Level_Load_Reset_Failure();
    assert(A35_Level_Load_Get_Failure() == A35_LOAD_NO_FAILURE);
}
