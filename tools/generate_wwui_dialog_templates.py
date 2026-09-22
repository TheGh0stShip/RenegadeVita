#!/usr/bin/env python3
"""Compile selected original chat.rc DIALOG records into Win32 template bytes."""
import argparse, re, struct
from pathlib import Path

# Original EVA shell and all seven child tabs must travel together.
IDS = {128,130,131,145,169,209,210,211,231,232,233,243,255,256} | set(range(146,154))
CAMPAIGN_IDS = IDS | {196,197,239}
FLAGS = {'DS_MODALFRAME':0x80,'DS_SETFONT':0x40,'WS_POPUP':0x80000000,'WS_CAPTION':0x00C00000,'WS_GROUP':0x20000,'WS_TABSTOP':0x10000,
 'BS_PUSHBUTTON':0,'BS_DEFPUSHBUTTON':1,'BS_CHECKBOX':2,'BS_AUTOCHECKBOX':3,'BS_OWNERDRAW':0xB,'BS_LEFT':0x100,'BS_CENTER':0x300,'BS_FLAT':0x8000,
 'SS_LEFT':0,'SS_CENTER':1,'SS_RIGHT':2,'SS_BITMAP':0xE,'ES_MULTILINE':4,'ES_AUTOVSCROLL':0x40,'LBS_NOTIFY':1}
FLAGS.update({'WS_SYSMENU':0x80000,'WS_BORDER':0x800000,
 'WS_CHILD':0x40000000,'WS_VISIBLE':0x10000000,'WS_DISABLED':0x08000000,
 'SS_BLACKFRAME':7,
 'SS_CENTERIMAGE':0x200,'SS_LEFTNOWORDWRAP':0xC,
 'ES_AUTOHSCROLL':0x80,'LVS_REPORT':1,'LVS_NOCOLUMNHEADER':0x4000,
 'LVS_SINGLESEL':4,'LVS_SHOWSELALWAYS':8,'LVS_SORTASCENDING':0x10,
 'LVS_AUTOARRANGE':0x100,'LVS_NOSORTHEADER':0x8000,
 'TBS_AUTOTICKS':1,'TBS_BOTH':8,'TBS_NOTICKS':0x10,
 'CBS_DROPDOWNLIST':3,'WS_VSCROLL':0x200000,'SS_ETCHEDHORZ':0x10})
CAPTIONLESS = {'EDITTEXT','LISTBOX','COMBOBOX','SCROLLBAR'}
CLASS = {'PUSHBUTTON':0x80,'DEFPUSHBUTTON':0x80,'CHECKBOX':0x80,'AUTOCHECKBOX':0x80,'LTEXT':0x82,'CTEXT':0x82,'RTEXT':0x82,'GROUPBOX':0x82,'EDITTEXT':0x81,'LISTBOX':0x83,'COMBOBOX':0x85,'SCROLLBAR':0x84}
# RC statements supply these styles even when they are absent from chat.rc.
# Original DialogTextClass explicitly checks WS_VISIBLE before drawing.
DEFAULT_STYLE = {'LTEXT':0x20000, 'CTEXT':0x20001, 'RTEXT':0x20002,
 'PUSHBUTTON':0x10000, 'DEFPUSHBUTTON':0x10001,
 'CHECKBOX':0x10002, 'AUTOCHECKBOX':0x10003, 'GROUPBOX':7,
 'EDITTEXT':0x810000, 'LISTBOX':0x800001, 'COMBOBOX':0x10001,
 'SCROLLBAR':0}

def macros(paths):
 d=dict(FLAGS); d.update({'IDOK':1,'IDCANCEL':2,'IDYES':6,'IDNO':7,'IDC_STATIC':-1})
 raw={}
 for path in paths:
  for line in Path(path).read_text(encoding='latin1').splitlines():
   m=re.match(r'\s*#define\s+(\w+)\s+(.+?)\s*(?://.*)?$',line)
   if m: raw[m.group(1)]=m.group(2).strip()
 def resolve(name, active=()):
  if name in d:return d[name]
  if name in active or name not in raw:return 0
  expr=raw[name]
  if not re.match(r'^[A-Za-z0-9_xX+|() \t-]+$',expr):return 0
  expr=re.sub(r'\b[A-Za-z_]\w*\b',lambda m:str(resolve(m.group(0),active+(name,))),expr)
  try:value=int(eval(expr,{'__builtins__':{}},{}))
  except (SyntaxError,ValueError):value=0
  d[name]=value
  return value
 for name in raw:resolve(name)
 return d
def split(s):
 out=[]; q=False; cur=''
 for c in s:
  if c=='"':q=not q
  if c==',' and not q:out.append(cur.strip());cur=''
  else:cur+=c
 out.append(cur.strip()); return out
def val(expr, d, default=0):
 total=default
 for x in expr.split('|'):
  x=x.strip(); negate=x.startswith('NOT ')
  if negate: x=x[4:].strip()
  value=d.get(x, int(x,0) if re.match(r'^-?(0x[0-9a-fA-F]+|\d+)$',x) else 0)
  total = total & ~value if negate else total | value
 return total
def text(x):
 x=x.strip(); return x[1:-1].replace('""','"') if x.startswith('"') else ''
def field(s): return struct.pack('<H',0) if not s else s.encode('utf-16le')+b'\0\0'
def ordinal(x): return struct.pack('<HH',0xffff,x)
def align(b,n): return b+b'\0'*((-len(b))%n)
def control(parts,d):
 head=parts[0].split(None,1); kind=head[0].upper(); parts=[kind]+(head[1:])+parts[1:]; style=0; cls=CLASS.get(kind); title=''
 defaults=d['WS_CHILD'] | d['WS_VISIBLE'] | DEFAULT_STYLE.get(kind,0)
 if kind=='CONTROL':
  title=text(parts[1]); ident=val(parts[2],d); cname=text(parts[3]); style=val(','.join(parts[4:-4]),d,defaults); coords=[val(x,d) for x in parts[-4:]]
  cls={'BUTTON':0x80,'STATIC':0x82,'EDIT':0x81,'COMBOBOX':0x85}.get(cname.upper()); cfield=ordinal(cls) if cls else field(cname)
 elif kind in CAPTIONLESS:
  ident=val(parts[1],d)
  coords=[val(x,d) for x in parts[2:6]]
  style=val(','.join(parts[6:]),d,defaults)
  cfield=ordinal(cls)
 else:
  title=text(parts[1]) if len(parts)>1 else ''; ident=val(parts[2],d); coords=[val(x,d) for x in parts[3:7]]; style=val(','.join(parts[7:]),d,defaults); cfield=ordinal(cls)
 return align(struct.pack('<IIhhhhH',style,0,*coords,ident & 0xffff)+cfield+field(title)+struct.pack('<H',0),4)
def parse(rc,d,selected_ids=IDS):
 lines=Path(rc).read_text(encoding='latin1').splitlines(); got={}; i=0
 while i<len(lines):
  m=re.match(r'\s*(\w+)\s+DIALOG(?:EX)?\s+DISCARDABLE\s+(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)',lines[i])
  if not m:i+=1;continue
  name=m.group(1); ident=val(name,d); i+=1; style=0; title=''; body=[]; font_size=0; font_face=''
  while i<len(lines) and lines[i].strip()!='BEGIN':
   s=lines[i].strip()
   if s.startswith('STYLE '): style=val(s[6:],d)
   if s.startswith('CAPTION '): title=text(s[8:])
   if s.startswith('FONT '):
    font=re.match(r'FONT\s+(\d+)\s*,\s*"([^"]*)"',s)
    if not font: raise SystemExit('unsupported canonical font declaration: '+s)
    style|=d['DS_SETFONT']; font_size=int(font.group(1)); font_face=font.group(2)
   i+=1
  i+=1; stmt=''
  while i<len(lines) and lines[i].strip()!='END':
   s=lines[i].split('//')[0].strip(); i+=1
   if not s:continue
   stmt+=((' ' if stmt else '')+s)
   if s.endswith(',') or s.endswith('|'):continue
   p=split(stmt); stmt=''
   if ident in selected_ids and p and (p[0].split(None,1)[0].upper() in CLASS or p[0].split(None,1)[0].upper()=='CONTROL'): body.append(control(p,d))
  if ident in selected_ids:
   font=struct.pack('<H',font_size)+field(font_face) if style & d['DS_SETFONT'] else b''
   header=struct.pack('<IIHhhhh',style,0,len(body),0,0,int(m.group(4)),int(m.group(5)))+field('')+field('')+field(title)+font
   got[ident]=align(header,4)+b''.join(body)
  i+=1
 missing=selected_ids-set(got)
 if missing: raise SystemExit('missing original dialogs: '+','.join(map(str,sorted(missing))))
 return got
def main():
 a=argparse.ArgumentParser();a.add_argument('--rc',required=True);a.add_argument('--resource-h',required=True);a.add_argument('--dialog-resource-h',required=True);a.add_argument('--out',required=True);a.add_argument('--campaign-dialogs',action='store_true');q=a.parse_args(); data=parse(q.rc,macros((q.resource_h,q.dialog_resource_h)),CAMPAIGN_IDS if q.campaign_dialogs else IDS)
 with open(q.out,'w') as f:
  f.write('struct RenegadeDialogTemplate { uint16_t Id; const unsigned char *Bytes; size_t Size; };\n')
  for ident,b in sorted(data.items()): f.write('static const unsigned char kDialog%d[] = {%s};\n'%(ident,','.join(str(x) for x in b)))
  f.write('static const RenegadeDialogTemplate kRenegadeDialogTemplates[] = {%s};\n'%(','.join('{%d,kDialog%d,sizeof(kDialog%d)}'%(i,i,i) for i in sorted(data))))
  f.write('static const size_t kRenegadeDialogTemplateCount = sizeof(kRenegadeDialogTemplates)/sizeof(kRenegadeDialogTemplates[0]);\n')
if __name__=='__main__':main()
