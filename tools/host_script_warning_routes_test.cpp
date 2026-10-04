#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main
#include "../staging/scripts/toolkit.h"
#include WARNING_PROBE_SOURCE
#include "../staging/scripts/ScriptRegistrar.h"
#include <memory>
#include <type_traits>

template<class Slot, class Callback>
static void SetWarningCommand(Slot &slot, Callback callback)
{
    static_assert(std::is_same<Slot, decltype(+callback)>::value, "Exact callback ABI");
    slot = +callback;
}

static int ObjectStorage[64];
static GameObject *Object = reinterpret_cast<GameObject *>(&ObjectStorage[0]);
static int CreatedCount;
static std::vector<std::string> ApacheParameters;
static std::vector<int> TimerIds;
static std::vector<int> EventTypes;
static std::string Animation;

int main(int argc, char **argv)
{
    assert(argc == 3);
    const std::string mode = argv[1];
    ScriptCommands commands = {};
    SetWarningCommand(commands.Create_Object, [](const char *name, const Vector3 &) {
        assert(strcmp(name, "Nod_Apache") == 0 || strcmp(name, "Nod_Apache_No_Idle") == 0);
        return reinterpret_cast<GameObject *>(&ObjectStorage[++CreatedCount]);
    });
    SetWarningCommand(commands.Get_ID, [](GameObject *object) {
        for (int i = 0; i < 64; ++i)
            if (object == reinterpret_cast<GameObject *>(&ObjectStorage[i])) return i + 100;
        assert(false); return 0;
    });
    SetWarningCommand(commands.Find_Object, [](int) { return Object; });
    SetWarningCommand(commands.Enable_Engine, [](GameObject *, bool) {});
    SetWarningCommand(commands.Attach_Script, [](GameObject *, const char *name, const char *parameters) {
        assert(strcmp(name, "M08_Apache") == 0 || strcmp(name, "M10_Apache") == 0);
        ApacheParameters.emplace_back(parameters);
    });
    SetWarningCommand(commands.Send_Custom_Event, [](GameObject *, GameObject *, int type, int, float delay) {
        assert(delay == 0); EventTypes.push_back(type);
    });
    SetWarningCommand(commands.Start_Timer, [](GameObject *, ScriptClass *, float, int id) { TimerIds.push_back(id); });
    SetWarningCommand(commands.Action_Goto, [](GameObject *, const ActionParamsStruct &) {});
    SetWarningCommand(commands.Action_Play_Animation, [](GameObject *, const ActionParamsStruct &params) {
        Animation = params.AnimationName;
    });
    SetWarningCommand(commands.Get_Facing, [](GameObject *) { return 10.0f; });
    SetWarningCommand(commands.Set_Facing, [](GameObject *, float angle) { assert(angle == 190.0f); });
    Commands = &commands;
    std::unique_ptr<ScriptImpClass> script(ScriptRegistrar::CreateScript(argv[2]));
    assert(script);
    if (mode == "technician") {
        script->Set_Parameters_String("77,1,2,0,None");
        script->Created(Object);
        for (int value : {0, INT_MIN, INT_MAX}) {
            Animation.clear();
            script->Custom(Object, 77, value, Object);
            script->Action_Complete(Object, TECHNICIAN_MOVEMENT, ACTION_COMPLETE_NORMAL);
            assert(Animation == "s_a_human.h_a_con2");
        }
        puts("PASS technician_literal_payload_cases=3");
        return 0;
    }
    script->Created(Object);
    if (mode == "negative_destroy") {
        const size_t events = EventTypes.size();
        script->Custom(Object, 1000, -1, Object);
        assert(EventTypes.size() == events);
        puts("PASS apache_negative_event_guard");
    }
    else if (mode == "inactive_reload") {
        script->Custom(Object, 3000, 1, Object);
        script->Custom(Object, 3000, -1, Object);
        script->Custom(Object, 5000, 1, Object);
        assert(TimerIds.back() == 11 && EventTypes.back() == 500);
        puts("PASS apache_inactive_reload_uses_sender_area timer=11");
    }
    else if (mode == "timer_gap") {
        const size_t parameters = ApacheParameters.size();
        script->Timer_Expired(Object, 9);
        assert(ApacheParameters.size() == parameters);
        puts("PASS apache_timer_gap_guard");
    }
    else if (mode == "negative_timer") {
        const size_t parameters = ApacheParameters.size();
        script->Timer_Expired(Object, -1);
        assert(ApacheParameters.size() == parameters);
        puts("PASS apache_negative_timer_guard");
    }
    else if (mode == "high_timer") {
        const size_t parameters = ApacheParameters.size();
        const size_t events = EventTypes.size();
        script->Timer_Expired(Object, 13);
        script->Timer_Expired(Object, INT_MAX);
        assert(ApacheParameters.size() == parameters);
        assert(EventTypes.size() == events);
        puts("PASS apache_high_timer_noop 13/intmax");
    }
    else if (mode == "valid") {
        ApacheParameters.clear();
        for (int area = 0; area < 3; ++area) script->Timer_Expired(Object, area);
        assert((ApacheParameters == std::vector<std::string>{"0", "1", "2"}));
        script->Custom(Object, 3000, 1, Object);
        script->Custom(Object, 5000, 1, Object);
        assert(TimerIds.back() == 11);
        script->Custom(Object, 3000, -1, Object);
        puts("PASS apache_valid_replace_cases=3 reload_timer=11 exit_sentinel");
    }
    else if (mode == "medkit_null") {
        script->Custom(Object, CUSTOM_HAS_MEDKIT, 0, Object);
        puts("PASS medkit_null_response");
    }
    else assert(false);
}
