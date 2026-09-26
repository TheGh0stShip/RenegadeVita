#pragma once
#include "statemachine.h"
#include "ramfile.h"
#include <cstdio>
#include <string>

namespace OriginalStateMachineProbe {
struct Owner {
    StateMachineClass<Owner> machine;
    std::string trace;
    bool allow = false;
    Owner() : machine(this) {
        ADD_STATE_TO_MACHINE(machine, A);
        ADD_STATE_TO_MACHINE(machine, B);
    }
    void On_A_Think() { trace += 't'; }
    bool On_A_Request_End(int) { trace += 'q'; return allow; }
    void On_A_Begin() { trace += 'b'; }
    void On_A_End() { trace += 'e'; }
    void On_B_Think() { trace += 'T'; }
    bool On_B_Request_End(int) { trace += 'Q'; return true; }
    void On_B_Begin() { trace += 'B'; }
    void On_B_End() { trace += 'E'; }
};

inline int Run() {
    Owner owner;
    owner.machine.Set_State(0);
    owner.machine.Think();
    owner.machine.Set_State(1);
    if (owner.machine.Get_State() != 0 || owner.trace != "btq") return 1;
    owner.machine.Set_State(1, true);
    owner.machine.Think();
    owner.machine.Halt_State();
    owner.machine.Halt_State();
    owner.machine.Think();
    owner.machine.Resume_State();
    owner.machine.Resume_State();
    owner.machine.Set_State(99);
    if (owner.machine.Get_State() != -1 || owner.trace != "btqeBTEBQE") return 2;

    owner.machine.Set_State(1);
    owner.machine.Halt_State();
    unsigned char bytes[256] = {};
    RAMFileClass file(bytes, sizeof(bytes));
    if (!file.Open(FileClass::WRITE)) return 3;
    ChunkSaveClass save(&file);
    owner.machine.Save(save);
    const int length = file.Tell();
    file.Close();
    RAMFileClass saved(bytes, length);
    if (!saved.Open(FileClass::READ)) return 4;
    ChunkLoadClass load(&saved);
    Owner restored;
    restored.machine.Load(load);
    restored.machine.Think();
    if (restored.machine.Get_State() != 1 || !restored.trace.empty()) return 5;
    restored.machine.Resume_State();
    restored.machine.Think();
    restored.machine.Set_State(0);
    restored.allow = true;
    restored.machine.Set_State(1);
    if (restored.trace != "BTQEbqeB") return 6;
    puts("original_state_machine.callbacks_denial_force_halt_resume_save_load=PASS");
    return 0;
}
}
