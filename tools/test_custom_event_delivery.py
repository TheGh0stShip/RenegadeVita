"""Execute the original custom-event command with bounded observer/timer seams."""
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from tools.audit_missing_definition_callers import body

ROOT=Path(__file__).resolve().parents[1]

PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <limits>
#include <vector>
struct GameObject;
struct Observer {
 std::function<void(GameObject*,int,int,GameObject*)> callback;
 void Custom(GameObject *to,int type,int param,GameObject *from) { callback(to,type,param,from); }
};
struct GameObjObserverList {
 std::vector<Observer*> rows;
 int Count() const { return static_cast<int>(rows.size()); }
 Observer *operator[](int index) const { return rows.at(index); }
};
struct Timer { GameObject *from; float delay; int type; int param; };
struct GameObject {
 GameObjObserverList observers; std::vector<Timer> timers;
 const GameObjObserverList &Get_Observers() const { return observers; }
 void Start_Custom_Timer(GameObject *from,float delay,int type,int param) {
  timers.push_back({from,delay,type,param});
 }
};
#define SCRIPT_PTR_CHECK(x) if ((x)==nullptr) return
#define SCRIPT_TRACE(x)
#define WWASSERT(x) assert(x)
'''

SUFFIX=r'''
int main() {
 static_assert(sizeof(int)==4,"Original custom event ABI");
 GameObject sender,target,empty;
 std::vector<int> order;
 int value=-1;
 Observer first,second;
 first.callback=[&](GameObject *to,int type,int param,GameObject *from) {
  assert(to==&target);
  if(type==9) {
   assert(from==&sender && param==std::numeric_limits<int>::max());
   order.push_back(1); value=0;
   Send_Custom_Event(from,to,10,std::numeric_limits<int>::min(),0);
   order.push_back(4);
  } else if(type==10) {
   assert(param==std::numeric_limits<int>::min());order.push_back(2);
  } else { assert(type==11 && from==nullptr && param==-7);order.push_back(6); }
 };
 second.callback=[&](GameObject*,int type,int,GameObject*) {
  if(type==9) { assert(value==0);value=3;order.push_back(5); }
  else if(type==10) order.push_back(3);
  else order.push_back(7);
 };
 target.observers.rows={&first,&second};
 Send_Custom_Event(&sender,&target,9,std::numeric_limits<int>::max(),0);
 assert(value==3 && (order==std::vector<int>{1,2,3,4,5}) && target.timers.empty());
 order.clear();Send_Custom_Event(nullptr,&target,11,-7,-.5f);
 assert((order==std::vector<int>{6,7}) && target.timers.empty());
 order.clear();Send_Custom_Event(&sender,&target,12,6300,.25f);
 assert(order.empty() && target.timers.size()==1);
 const Timer &timer=target.timers[0];
 assert(timer.from==&sender && timer.delay==.25f && timer.type==12 && timer.param==6300);
 Send_Custom_Event(&sender,nullptr,9,0,0);assert(order.empty());
 Send_Custom_Event(&sender,&empty,9,0,0);assert(empty.timers.empty());
 Send_Custom_Event(nullptr,&empty,9,-7,1);assert(empty.timers.size()==1);
 puts("Original custom-event delivery PASS inline_order reentrant_order stack_mutation negative_delay null_sender positive_queue null_target empty_observers int32_extremes");
}
'''


class CustomEventDeliveryTests(unittest.TestCase):
    def test_original_inline_and_delayed_contract(self):
        original=ROOT/'upstream/CnC_Renegade/Code/Combat/scriptcommands.cpp'
        staged=ROOT/'staging/combat/scriptcommands.cpp'
        original_body,_=body(original.read_text(encoding='latin1'),'Send_Custom_Event')
        staged_body,line=body(staged.read_text(encoding='latin1'),'Send_Custom_Event')
        self.assertEqual(original_body,staged_body)
        header=ROOT/'staging/combat/gameobjobserver.h'
        constant=re.search(r'CUSTOM_EVENT_SYSTEM_FIRST\s*=\s*(\d+)',header.read_text(encoding='latin1'))
        self.assertIsNotNone(constant)
        source=PREFIX+'\nconstexpr int CUSTOM_EVENT_SYSTEM_FIRST='+constant[1]+';\n'
        source+='void Send_Custom_Event(GameObject *from,GameObject *to,int type,int param,float delay)'+staged_body+SUFFIX
        retained=os.environ.get('RENEGADE_CUSTOM_EVENT_PROBE_DIRECTORY')
        if retained:Path(retained).mkdir(parents=True,exist_ok=True)
        with (nullcontext(retained) if retained else tempfile.TemporaryDirectory()) as directory:
            path=Path(directory);(path/'delivery.cpp').write_text(source)
            compiled=subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
                '-fno-sanitize-recover=all',str(path/'delivery.cpp'),'-o',str(path/'delivery')],capture_output=True,text=True)
            if retained:(path/'compile.log').write_text(compiled.stdout+compiled.stderr)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(path/'delivery')],capture_output=True,text=True)
            if retained:(path/'runtime.log').write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS inline_order reentrant_order stack_mutation',result.stdout)
            arm_compiler=os.environ.get('RENEGADE_CUSTOM_EVENT_ARM_COMPILER')
            arm_receipt=None
            if arm_compiler:
                arm_object=path/'delivery-arm.o'
                arm=subprocess.run([arm_compiler,'-std=c++17','-O1','-g','-c',str(path/'delivery.cpp'),
                                    '-o',str(arm_object)],capture_output=True,text=True)
                if retained:(path/'arm-compile.log').write_text(arm.stdout+arm.stderr)
                self.assertEqual(arm.returncode,0,arm.stderr)
                readelf=Path(arm_compiler).with_name('arm-vita-eabi-readelf')
                attributes=subprocess.run([str(readelf),'-h','-A',str(arm_object)],capture_output=True,text=True)
                self.assertEqual(attributes.returncode,0,attributes.stderr)
                for value in ('ELF32','little endian','ARM','Tag_CPU_arch: v7','Tag_ABI_VFP_args: VFP registers'):
                    self.assertIn(value,attributes.stdout)
                if retained:(path/'arm-attributes.log').write_text(attributes.stdout)
                arm_receipt={'object_sha256':hashlib.sha256(arm_object.read_bytes()).hexdigest(),
                             'attributes_sha256':hashlib.sha256(attributes.stdout.encode()).hexdigest(),
                             'armv7_little_endian_vfp_arguments':True,'executed':False}
            if retained:
                digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
                receipt={'schema_version':1,'evidence_class':'host_original_custom_event_delivery_asan_ubsan',
                         'original_body_equals_staged':True,'owner_line':line,
                         'contracts_passed':['inline_order','reentrant_order','stack_mutation','negative_delay',
                                             'null_sender','positive_queue','null_target','empty_observers','int32_extremes'],
                         'binary_sha256':digest(path/'delivery'),
                         'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in (original,staged,header,ROOT/'tools/test_custom_event_delivery.py')},
                         'body_sha256':hashlib.sha256(staged_body.encode()).hexdigest(),
                         'arm_compile':arm_receipt,
                         'limits':['Synthetic observer list and timer queue; real observer lifetime and timer expiry remain open.',
                                   'Captured stack variable mutation proves inline timing, not Mission03 pointer-width compatibility.',
                                   'Trace logging omitted; null-target return and original assert predicate retained.',
                                   'No original Mission03 callbacks, ARM execution or native mission acceptance.']}
                (path/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    unittest.main()
