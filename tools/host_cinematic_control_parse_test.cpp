// Reuse the original script/framework fixture, without executing its legacy main.
#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main

static std::string Payload;
static size_t Cursor;
static void Ignore_Debug_Message(char *,...) {}

int main()
{
    ScriptCommands commands={};
    commands.Debug_Message=Ignore_Debug_Message;
    commands.Text_File_Open=[](const char *) { Cursor=0; return 1; };
    commands.Text_File_Close=[](int handle) { assert(handle==1); };
    commands.Text_File_Get_String=[](int handle,char *buffer,int size) {
        assert(handle==1 && size==199);
        int written=0;
        while(Cursor<Payload.size()) {
            char ch=Payload[Cursor++];
            if(written<size) buffer[written++]=ch;
            if(ch=='\n') break;
        }
        buffer[written]=0;
        return buffer[0]!=0;
    };
    Commands=&commands;
    unsigned char bytes[4];
    while(fread(bytes,1,4,stdin)==4) {
        uint32_t length=uint32_t(bytes[0]) | uint32_t(bytes[1])<<8 |
                        uint32_t(bytes[2])<<16 | uint32_t(bytes[3])<<24;
        assert(length<16U*1024U*1024U);
        Payload.resize(length);
        assert(fread(Payload.data(),1,length,stdin)==length);
        Test_Cinematic script;
        script.Load_Control_File("fixture");
        unsigned count=0;
        for(auto *node=script.Controls;node;node=node->Next) ++count;
        printf("%u",count);
        for(auto *node=script.Controls;node;node=node->Next) {
            uint32_t time;
            static_assert(sizeof(time)==sizeof(node->Time),"original float bits");
            memcpy(&time,&node->Time,sizeof(time));
            uint64_t hash=14695981039346656037ULL;
            for(const unsigned char *p=reinterpret_cast<const unsigned char*>(node->Command);*p;++p)
                hash=(hash^*p)*1099511628211ULL;
            printf(" %08x:%016llx",time,static_cast<unsigned long long>(hash));
        }
        puts("");
    }
    Commands=nullptr;
}
