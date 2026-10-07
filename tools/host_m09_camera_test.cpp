#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main
#include M09_PROBE_SOURCE
#include "../staging/scripts/ScriptRegistrar.h"
#include <memory>
#include <type_traits>

template<class Slot, class Callback>
static void SetCameraCommand(Slot &slot, Callback callback)
{
    static_assert(std::is_same<Slot, decltype(+callback)>::value, "Exact callback ABI");
    slot = +callback;
}

// The staged M09 scripts log Vita lift/midtro recovery; discard on the host.
int A30_Vita_Log(const char *, ...) { return 0; }

static int CameraStorage;
static GameObject *CameraObject = reinterpret_cast<GameObject *>(&CameraStorage);
static std::vector<int> CameraQueries;
static int Attachments;

int main()
{
    ScriptCommands commands = {};
    SetCameraCommand(commands.Find_Object, [](int id) {
        CameraQueries.push_back(id);
        return CameraObject;
    });
    SetCameraCommand(commands.Attach_Script, [](GameObject *object, const char *name, const char *parameters) {
        assert(object == CameraObject);
        assert(strcmp(name, "RMV_Camera_Behavior") == 0);
        assert(strcmp(parameters, "90.0, 0, 1, 0.0") == 0);
        ++Attachments;
    });
    Commands = &commands;
    const std::pair<const char *, std::vector<int>> cases[] = {
        {"1,2,3,4,5", {1,2,3,4,5}},
        {"0,0,0,0,0", {}},
        {"1,0,3,0,5", {1,3,5}},
        {"0,0,0,0,5", {5}}
    };
    for (const auto &item : cases) {
        std::unique_ptr<ScriptImpClass> script(ScriptRegistrar::CreateScript("M09_Camera_Activate"));
        assert(script);
        script->Set_Parameters_String(item.first);
        script->Created(CameraObject);
        CameraQueries.clear();
        Attachments = 0;
        script->Entered(CameraObject, CameraObject);
        assert(CameraQueries == item.second && Attachments == int(item.second.size()));
        script->Entered(CameraObject, CameraObject);
        assert(CameraQueries == item.second && Attachments == int(item.second.size()));
    }
    puts("PASS camera_cases=4 five_slots zero_slots sparse_slots last_slot repeat_entry");
}
