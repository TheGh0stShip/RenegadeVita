#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main

static std::vector<std::string> Calls;
static int ObjectStorage;
static GameObject *Object=reinterpret_cast<GameObject*>(&ObjectStorage);
static bool FailCreation=false;
static void Record(const char *name) { Calls.emplace_back(name); }

int main()
{
    ScriptCommands commands={};
    commands.Find_Object=[](int id) { return id ? Object : nullptr; };
    commands.Get_Position=[](GameObject*) { return Vector3(1,2,3); };
    commands.Get_Bone_Position=[](GameObject*,const char*) { return Vector3(1,2,3); };
    commands.Get_Facing=[](GameObject*) { return 17.f; };
    commands.Get_ID=[](GameObject*) { return 123; };
    commands.Get_The_Star=[]() { return Object; };
    commands.Create_Object=[](const char*,const Vector3&) { Record("create"); return FailCreation ? nullptr : Object; };
    commands.Create_Object_At_Bone=[](GameObject*,const char*,const char*) { Record("create_bone"); return Object; };
    commands.Add_To_Dirty_Cull_List=[](GameObject*) {};
    commands.Enable_Hibernation=[](GameObject*,bool) {};
    commands.Enable_Cinematic_Freeze=[](GameObject*,bool) {};
    commands.Enable_Engine=[](GameObject*,bool) {};
    commands.Set_Facing=[](GameObject*,float value) { assert(value==17.f); };
    commands.Set_Model=[](GameObject*,const char *name) { assert(strcmp(name,"Model")==0); Record("model"); };
    commands.Create_Explosion_At_Bone=[](const char *name,GameObject*,const char *bone,GameObject*) {
        assert(strcmp(name,"Explosion")==0 && strcmp(bone,"Bone")==0); Record("explosion"); };
    commands.Destroy_Object=[](GameObject*) { Record("destroy"); };
    commands.Set_Animation=[](GameObject*,const char *name,bool loop,const char *sub,float,float end,bool blend) {
        assert(strcmp(name,"Animation")==0 && loop && strcmp(sub,"Sub")==0 && end==-1 && blend); Record("animation"); };
    commands.Innate_Disable=[](GameObject*) {};
    commands.Create_2D_Sound=[](const char *name) { assert(strcmp(name,"Sound")==0); Record("sound2d"); return 1; };
    commands.Create_3D_Sound_At_Bone=[](const char *name,GameObject *object,const char *bone) {
        assert(strcmp(name,"Sound")==0 && object==Object && strcmp(bone,"Bone")==0);
        Record("sound3d"); return 1; };
    commands.Set_Camera_Host=[](GameObject *object) { Record(object ? "camera_on" : "camera_off"); };
    commands.Control_Enable=[](GameObject*,bool enabled) { Record(enabled ? "input_on" : "input_off"); };
    commands.Enable_HUD=[](bool enabled) { Record(enabled ? "hud_on" : "hud_off"); };
    commands.Send_Custom_Event=[](GameObject*,GameObject*,int type,int param,float delay) {
        assert(type==7 && param==123 && delay==0); Record("custom"); };
    commands.Attach_To_Object_Bone=[](GameObject *object,GameObject *host,const char *bone) {
        assert(object==Object);
        if(host) { assert(host==Object && strcmp(bone,"Bone")==0); Record("bone"); }
        else { assert(bone==nullptr); Record("detach"); } };
    commands.Attach_Script=[](GameObject*,const char *name,const char *params) {
        if(strcmp(name,"Script")==0) assert(strcmp(params,"a,b")==0);
        else { assert(strcmp(name,"Test_Cinematic_Primary_Killed")==0); assert(strcmp(params,"2147483647")==0); }
        Record("script"); };
    commands.Cinematic_Sniper_Control=[](bool enabled,float zoom) { assert(enabled && zoom==2); Record("sniper"); };
    commands.Shake_Camera=[](const Vector3&,float radius,float intensity,float duration) {
        assert(radius==100 && intensity==.5f && duration==2); Record("shake"); };
    commands.Enable_Shadow=[](GameObject*,bool enabled) { assert(enabled); Record("shadow"); };
    commands.Enable_Letterbox=[](bool enabled,float time) { assert(enabled && time==2); Record("letterbox"); };
    commands.Set_Screen_Fade_Color=[](float r,float g,float b,float time) {
        assert(r==.25f && g==.5f && b==1 && time==2); Record("color"); };
    commands.Set_Screen_Fade_Opacity=[](float opacity,float time) { assert(opacity==.5f && time==2); Record("opacity"); };
    Commands=&commands;
    Test_Cinematic script;
    script.ObjectSlots[0]=123; script.ObjectSlots[1]=123; script.MyID=2147483647;
    const std::pair<const char*,const char*> cases[]={
        {"Create_Object,3,Model","model"},{"Create_Real_Object,4,Preset,0,Bone","create_bone"},
        {"Create_Explosion,Explosion,0,Bone","explosion"},{"Destroy_Object,0","destroy"},
        {"Play_Animation,0,Animation,1,Sub,1","animation"},{"Play_Audio,Sound","sound2d"},
        {"Control_Camera,0","camera_on"},{"Send_Custom,#0,7,#1","custom"},
        {"Attach_To_Bone,0,1,Bone","bone"},{"Attach_Script,0,Script,\"a,b\"","script"},
        {"Set_Primary,0","script"},{"Move_Slot,2,1",nullptr},
        {"Sniper_Control,1,2","sniper"},{"Shake_Camera,0,.5,2","shake"},
        {"Enable_Shadow,0,1","shadow"},{"Enable_Letterbox,1,2","letterbox"},
        {"Set_Screen_Fade_Color,.25,.5,1,2","color"},{"Set_Screen_Fade_Opacity,.5,2","opacity"}};
    for(const auto &item:cases) {
        Calls.clear();std::string text=item.first;script.Parse_Command(text.data());
        if(item.second) assert(std::find(Calls.begin(),Calls.end(),item.second)!=Calls.end());
        else assert(script.ObjectSlots[2]==123 && script.ObjectSlots[1]==0);
    }
    assert(script.ObjectSlots[3]==123 && script.ObjectSlots[4]==123);
    Calls.clear();char release[]="Control_Camera,-1";script.Parse_Command(release);
    assert((Calls==std::vector<std::string>{"camera_off","input_on","hud_on"}));
    Calls.clear();char prefix[]="pLaY_AuDiO_suffix,Sound";script.Parse_Command(prefix);
    assert((Calls==std::vector<std::string>{"sound2d"}));
    Calls.clear();char unknown[]="Unknown,0";script.Parse_Command(unknown);assert(Calls.empty());
    auto parse=[&](const char *command) {
        Calls.clear();std::string text=command;script.Parse_Command(text.data());
    };
    parse("Play_Audio,Sound,0,Bone");
    assert((Calls==std::vector<std::string>{"sound3d"}));
    parse("Attach_To_Bone,0,-1,Bone");
    assert((Calls==std::vector<std::string>{"detach"}));
    parse("Create_Real_Object,5,Preset");
    assert((Calls==std::vector<std::string>{"create"}) && script.ObjectSlots[5]==123);
    FailCreation=true;
    script.ObjectSlots[6]=456;
    parse("Create_Object,6,Model");
    assert((Calls==std::vector<std::string>{"create"}) && script.ObjectSlots[6]==456);
    parse("Create_Real_Object,6,Preset");
    assert((Calls==std::vector<std::string>{"create"}) && script.ObjectSlots[6]==456);
    FailCreation=false;
    // Empty slots and explicitly guarded invalid slots must not invoke effects.
    script.ObjectSlots[7]=0;
    const char *guarded[]={
        "Destroy_Object,7","Destroy_Object,-1",
        "Play_Animation,7,Animation,1,Sub,1","Play_Animation,-1,Animation,1,Sub,1",
        "Play_Audio,Sound,7,Bone","Control_Camera,7",
        "Attach_To_Bone,7,0,Bone","Attach_To_Bone,0,7,Bone",
        "Attach_Script,7,Script,\"a,b\"","Attach_Script,-1,Script,\"a,b\"",
        "Set_Primary,7","Set_Primary,-1",
        "Shake_Camera,7,.5,2","Shake_Camera,-1,.5,2",
        "Enable_Shadow,7,1","Enable_Shadow,-1,1",
        "Send_Custom,#7,7,#0","Send_Custom,0,7,#0"};
    for(const char *command:guarded) { parse(command);assert(Calls.empty()); }
    const int original_slot=script.ObjectSlots[0];
    parse("Move_Slot,0,0");assert(script.ObjectSlots[0]==original_slot);
    parse("Move_Slot,-1,0");assert(script.ObjectSlots[0]==original_slot);
    Commands=nullptr;
    puts("Original cinematic dispatch PASS branches=18 camera_release=1 title_prefix=1 unknown=1 alternatives=5 guarded_no_effect=18 slot_preservation=2");
}
