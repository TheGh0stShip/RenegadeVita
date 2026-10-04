#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main
#include "../staging/scripts/Mission03.cpp"
#include "../staging/scripts/ScriptRegistrar.h"
#include <memory>
#include <type_traits>

template<class Slot, class Callback>
static void SetCommand(Slot &slot, Callback callback)
{
    static_assert(std::is_same<Slot, decltype(+callback)>::value, "Exact command callback ABI");
    slot=+callback;
}

static int Storage[3];
static GameObject *Player=reinterpret_cast<GameObject*>(&Storage[0]);
static GameObject *Soldier=reinterpret_cast<GameObject*>(&Storage[1]);
static GameObject *Other=reinterpret_cast<GameObject*>(&Storage[2]);
static ScriptImpClass *Commando;
static ScriptImpClass *Reinforcements;
static int LastParameter;
static int PointerEvents;
static int Conversations;

int main()
{
    static_assert(sizeof(void*)>sizeof(int),"This regression requires the LP64 host");
    ScriptCommands commands={};
    SetCommand(commands.Get_ID, [](GameObject *object) { return object==Soldier ? 1 : 2; });
    SetCommand(commands.Send_Custom_Event, [](GameObject *from,GameObject *to,int type,int parameter,float delay) {
        assert(delay==0 && RenegadeHostScriptPointerExchange::Resolve(parameter)!=nullptr);
        LastParameter=parameter;++PointerEvents;
        if(type==3000) Commando->Custom(to,type,parameter,from);
        else { assert(type==5000 || type==6300);Reinforcements->Custom(to,type,parameter,from); }
    });
    SetCommand(commands.Create_Conversation, [](const char *name,int priority,float distance,bool) {
        assert(strcmp(name,"M03CON041")==0 && priority==99 && distance==200);
        ++Conversations;return 42;
    });
    SetCommand(commands.Join_Conversation, [](GameObject*,int id,bool move,bool head,bool face) {
        assert(id==42 && move && head && face); });
    SetCommand(commands.Start_Conversation, [](int id,int action) { assert(id==42 && action==100041); });
    SetCommand(commands.Monitor_Conversation, [](GameObject*,int id) { assert(id==42); });
    Commands=&commands;
    std::unique_ptr<ScriptImpClass> commando(ScriptRegistrar::CreateScript("M03_Commando_Script"));
    std::unique_ptr<ScriptImpClass> reinforcements(ScriptRegistrar::CreateScript("M03_Reinforce_Area"));
    std::unique_ptr<ScriptImpClass> counter(ScriptRegistrar::CreateScript("M03_Area_Troop_Counter"));
    std::unique_ptr<ScriptImpClass> soldier(ScriptRegistrar::CreateScript("M03_Chinook_Spawned_Soldier_GDI"));
    assert(commando && reinforcements && counter && soldier);
    Commando=commando.get();Reinforcements=reinforcements.get();
    commando->Created(Player);reinforcements->Created(Other);counter->Created(Other);
    int last_token=0;
    for(auto item:{std::pair<GameObject*,int>{Soldier,0},{Other,1},{Soldier,-1}}) {
        int occupied=99;
        {
            RenegadeHostScriptPointerExchange exchange(&occupied);
            last_token=exchange.Parameter();
            commando->Custom(Player,3000,last_token,item.first);
            assert(occupied==item.second);
        }
        assert(RenegadeHostScriptPointerExchange::Resolve(last_token)==nullptr);
    }
    // Establish a different follower so the real Poked sender takes its blocked route.
    int occupied=99;
    { RenegadeHostScriptPointerExchange exchange(&occupied);
      commando->Custom(Player,3000,exchange.Parameter(),Soldier); }
    soldier->Poked(Other,Player);
    assert(PointerEvents==1 && Conversations==1);
    assert(RenegadeHostScriptPointerExchange::Resolve(LastParameter)==nullptr);
    counter->Custom(Other,1000,1000,nullptr);
    assert(PointerEvents==3);
    assert(RenegadeHostScriptPointerExchange::Resolve(LastParameter)==nullptr);
    for(auto item:{std::pair<int,int>{5000,0},{6300,3}}) {
        int output=-1;
        { RenegadeHostScriptPointerExchange exchange(&output);
          reinforcements->Custom(Other,item.first,exchange.Parameter(),nullptr); }
        assert(output==item.second);
    }
    int outer=1,inner=2;
    { RenegadeHostScriptPointerExchange first(&outer);
      { RenegadeHostScriptPointerExchange second(&inner);
        assert(first.Parameter()!=second.Parameter());
        assert(RenegadeHostScriptPointerExchange::Resolve(first.Parameter())==&outer);
        assert(RenegadeHostScriptPointerExchange::Resolve(second.Parameter())==&inner); }
      assert(RenegadeHostScriptPointerExchange::Resolve(first.Parameter())==&outer); }
    assert(RenegadeHostScriptPointerExchange::Resolve(0)==nullptr);
    puts("Original M03 pointer exchange PASS escort_states=3 area_queries=2 real_senders=3 scoped_release nested_tokens");
}
