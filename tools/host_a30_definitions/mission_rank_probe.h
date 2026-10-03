#pragma once

#include "renegade_mission_ranks.h"
#include "dlgloadspgame.h"
#include "registry.h"
#include "_globals.h"
#include <stdlib.h>
#include <unistd.h>

namespace MissionRankProbe {
inline int Run()
{
    char directory[] = "/tmp/renegade-mission-ranks-XXXXXX";
    if (mkdtemp(directory) == NULL) return 1;
    char path[256];
    snprintf(path, sizeof(path), "%s/ranks.cfg", directory);
    char key[RenegadeMissionRanks::NameBytes];
    const char *original_key = Build_Registry_Location_String(
        const_cast<char *>(APP_SUB_KEY), NULL, const_cast<char *>("Ranks"));
    snprintf(key, sizeof(key), "%s", original_key);
    bool passed = RenegadeMissionRanks::Configure(path, key);
    LoadSPGameMenuClass::Set_Game_Rank("M13.mix", 3);
    LoadSPGameMenuClass::Set_Game_Rank("m13.LSD", 1);
    LoadSPGameMenuClass::Set_Game_Rank("M01.mix", 5);
    RegistryClass ranks(key);
    passed = passed && ranks.Get_Int("m13") == 3 &&
        ranks.Get_Int("M01") == 5 && ranks.Get_Int("M02") == 0;
    RegistryClass::Set_Read_Only(true);
    LoadSPGameMenuClass::Set_Game_Rank("M13.mix", 5);
    RegistryClass::Set_Read_Only(false);
    passed = passed && ranks.Get_Int("M13") == 3;
    RenegadeMissionRanks::Configure(NULL, NULL);
    passed = RenegadeMissionRanks::Configure(path, key) && passed;
    passed = passed && ranks.Get_Int("M13") == 3 && ranks.Get_Int("m01") == 5;
    ranks.Delete_Value("m01");
    passed = RenegadeMissionRanks::Configure(path, key) && passed;
    passed = passed && ranks.Get_Int("M01") == 0 && ranks.Get_Int("M13") == 3;
    RenegadeMissionRanks::Configure(NULL, NULL);
    remove(path);
    rmdir(directory);
    printf("Original mission rank storage: max rank, case, read-only, reload and delete %s\n", passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}
} // namespace MissionRankProbe
