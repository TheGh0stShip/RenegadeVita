#!/usr/bin/env python3
"""Audit campaign DECLARE_SCRIPT classes for member state that is not auto-saved.

Original save path (unchanged from upstream Code/Scripts/scripts.cpp): only
variables registered with REGISTER_VARIABLES()/SAVE_VARIABLE() are written;
ScriptImpClass::Save/Load call to Save_Data/Load_Data is commented out, and
ScriptableGameObj::On_Post_Load only replays Created() on a *first* (editor /
fresh level) load.  So after a savegame load every unregistered member keeps
its constructor value (or indeterminate heap contents when there is none).

Heuristic, report-only.  Usage:
    python3 tools/audit_script_save_state_gaps.py [--json out.json] [files...]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = [
    "Mission01.cpp", "Mission02.cpp", "Mission03.cpp", "Mission04.cpp",
    "Mission05.cpp", "Mission06.cpp", "Mission07.cpp", "mission08.cpp",
    "Mission09.cpp", "Mission10.cpp", "Mission11.cpp", "MissionX0.cpp",
    "Test_DLS.cpp",
]
EVENT_METHODS = {
    "Custom", "Timer_Expired", "Killed", "Damaged", "Entered", "Exited",
    "Action_Complete", "Poked", "Animation_Complete", "Destroyed",
    "Enemy_Seen", "Sound_Heard",
}
OBJECTIVE_RE = re.compile(
    r"\b(Add_Objective|Set_Objective_Status|Mission_Complete|"
    r"Set_Objective_Radar_Blip\w*|Set_Objective_HUD_Info\w*|Change_Objective\w*)\b")
EVENT_RE = re.compile(r"\b(Send_Custom_Event|Create_Conversation|Start_Conversation|"
                      r"Create_Object|Trigger_Spawner|Start_Timer)\b")
KEYWORDS = {"typedef", "enum", "friend", "using", "struct", "class", "union",
            "public", "private", "protected", "return", "virtual", "static", "const"}


def strip_code(text):
    """Blank comments and string/char literals, preserving offsets/newlines."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j])); i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + " " * (j - i - 2) + c if j - i >= 2 else c); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


def match_brace(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return len(s) - 1


def parse_decl(stmt):
    """Return [(name, type_text, is_pointer, is_array)] for a member declaration."""
    stmt = re.sub(r"^\s*(public|private|protected)\s*:\s*", "", stmt.strip())
    stmt = re.sub(r"\b(public|private|protected)\s*:", " ", stmt).strip()
    if not stmt or "(" in stmt or "#" in stmt:
        return []
    first = stmt.split()[0]
    if first in ("typedef", "enum", "friend", "using", "return"):
        return []
    parts, depth, cur = [], 0, ""
    for ch in stmt:
        if ch in "[{<":
            depth += 1
        elif ch in "]}>":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    parts.append(cur)
    m = re.match(r"^(.*?)([A-Za-z_]\w*)\s*((?:\[[^\]]*\]\s*)*)(=.*)?$", parts[0].strip(), re.S)
    if not m:
        return []
    base_type = m.group(1).strip()
    if not base_type or base_type.split()[-1].rstrip("*&") in ("", ) and "*" not in base_type:
        if not base_type:
            return []
    res = []
    base_no_ptr = base_type.rstrip("*& \t")
    res.append((m.group(2), base_type, "*" in base_type, bool(m.group(3))))
    for p in parts[1:]:
        mm = re.match(r"^\s*(\**)\s*([A-Za-z_]\w*)\s*((?:\[[^\]]*\]\s*)*)", p)
        if mm:
            res.append((mm.group(2), base_no_ptr + (" *" if mm.group(1) else ""),
                        bool(mm.group(1)) or "*" in base_type, bool(mm.group(3))))
    return [r for r in res if r[0] not in KEYWORDS]


def analyze_class(name, body, body_off, line_of):
    members, methods, registered, reg_line, dropped = [], [], [], None, []
    i, depth, stmt_start = 0, 0, 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == "{":
            header = body[stmt_start:i]
            end = match_brace(body, i)
            hdr = header.strip()
            mname = None
            mh = re.search(r"([A-Za-z_]\w*)\s*\([^()]*(?:\([^()]*\)[^()]*)*\)\s*(const)?\s*$", hdr)
            if "REGISTER_VARIABLES" in hdr:
                reg_line = line_of(body_off + i)
                seen_ids = {}
                for sm in re.finditer(r"SAVE_VARIABLE\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", body[i:end]):
                    var = re.sub(r"\[.*", "", sm.group(1)).strip()
                    try:
                        vid = int(sm.group(2), 0)
                    except ValueError:
                        vid = sm.group(2)
                    # ScriptImpClass::Auto_Save_Variable rejects a duplicate id or an
                    # id outside 0..255 (DebugPrint only): that variable is never saved.
                    if vid in seen_ids or (isinstance(vid, int) and not 0 <= vid <= 255):
                        dropped.append(dict(name=var, id=vid, kept=seen_ids.get(vid),
                                            line=line_of(body_off + i + sm.start())))
                        continue
                    seen_ids[vid] = var
                    registered.append(var)
            elif mh:
                mname = mh.group(1)
                methods.append((mname, body_off + i, body[i:end + 1]))
            elif re.search(r"\b(enum|struct|union)\b", hdr):
                pass
            i = end + 1
            # statements like 'enum {...};' consume trailing ';'
            k = i
            while k < n and body[k] in " \t\r\n":
                k += 1
            if k < n and body[k] == ";":
                i = k + 1
            stmt_start = i
            continue
        if c == ";":
            stmt = body[stmt_start:i]
            for (vname, vtype, ptr, arr) in parse_decl(stmt):
                off = body_off + stmt_start + stmt.find(vname)
                members.append(dict(name=vname, type=vtype, pointer=ptr, array=arr,
                                    line=line_of(off)))
            stmt_start = i + 1
        i += 1
    return members, methods, registered, reg_line, dropped


WRITE_TMPL = r"(?<![\w.>])(?:\+\+|--)?\s*{v}\b(?:\s*\[[^\]]*\])?\s*(?:=(?!=)|\+=|-=|\*=|/=|\|=|&=|\+\+|--)"


def classify(member, methods, line_of):
    v = re.escape(member["name"])
    wre = re.compile(WRITE_TMPL.format(v=v))
    pre = re.compile(r"(?:\+\+|--)\s*" + v + r"\b")
    rre = re.compile(r"(?<![\w.>])" + v + r"\b")
    writes, reads = {}, {}
    for (mname, off, text) in methods:
        for m in rre.finditer(text):
            seg = text[m.start():m.start() + 80]
            is_write = bool(wre.match(seg)) or bool(pre.search(text[max(0, m.start() - 3):m.end()]))
            entry = (mname, line_of(off + m.start()))
            (writes if is_write else reads).setdefault(mname, []).append(entry[1])
    return writes, reads


def risk_for(member, writes, reads, methods, cls):
    event_writes = {k: v for k, v in writes.items() if k in EVENT_METHODS}
    read_methods = set(reads)
    if not writes and not reads:
        return None
    obj_methods = {m for (m, _o, t) in methods if OBJECTIVE_RE.search(t)}
    evt_methods = {m for (m, _o, t) in methods if EVENT_RE.search(t)}
    cname = cls.lower()
    nm = member["name"].lower()
    progression_name = re.search(r"(count|kill|dead|done|complete|obj|id\b|_id|id$|flag|"
                                 r"state|stage|phase|step|alive|destroy|active|start|"
                                 r"num|total|first|trigger|spawn|enter|reach|gave|have|has)", nm)
    if event_writes and read_methods:
        level = "state"
    elif writes.get("Created") and (read_methods - {"Created"}):
        level = "created-only"
    else:
        return None
    score = 1
    if level == "state":
        score += 2
    if read_methods & obj_methods or set(writes) & obj_methods:
        score += 3
    elif read_methods & evt_methods:
        score += 1
    if progression_name:
        score += 1
    if "controller" in cname or "objective" in cname:
        score += 1
    if member["pointer"]:
        score += 1
    return dict(level=level, score=score,
                objective_link=bool(read_methods & obj_methods or set(writes) & obj_methods))


def audit_file(path):
    raw = path.read_text(encoding="latin-1")
    code = strip_code(raw)
    nl = [i for i, ch in enumerate(code) if ch == "\n"]
    import bisect

    def line_of(off):
        return bisect.bisect_right(nl, off - 1) + 1 if off > 0 else 1

    results = []
    for m in re.finditer(r"DECLARE_SCRIPT\s*\(\s*([A-Za-z_]\w*)", code):
        cls = m.group(1)
        ob = code.find("{", m.end())
        if ob < 0:
            continue
        cb = match_brace(code, ob)
        body = code[ob + 1:cb]
        members, methods, registered, reg_line, dropped = analyze_class(cls, body, ob + 1, line_of)
        reg_set = set(registered)
        entry = dict(cls=cls, line=line_of(m.start()), registered=registered,
                     reg_line=reg_line, gaps=[], raw_pointers=[], dropped_ids=dropped,
                     uses_save_data_override=bool(re.search(r"\bSAVE_DATA\s*\(|\bvoid\s+Save_Data\s*\(", body)))
        for mem in members:
            if mem["name"] in reg_set:
                if mem["pointer"]:
                    entry["raw_pointers"].append(dict(name=mem["name"], type=mem["type"],
                                                      line=mem["line"], array=mem["array"]))
                continue
            writes, reads = classify(mem, methods, line_of)
            r = risk_for(mem, writes, reads, methods, cls)
            if r:
                first_w = min((ln for lst in writes.values() for ln in lst), default=None)
                ev_w = sorted({ln for k, lst in writes.items() if k in EVENT_METHODS for ln in lst})
                entry["gaps"].append(dict(name=mem["name"], type=mem["type"], decl_line=mem["line"],
                                          pointer=mem["pointer"], array=mem["array"],
                                          write_methods=sorted(writes), read_methods=sorted(reads),
                                          event_write_lines=ev_w[:4], first_write=first_w, **r))
        results.append(entry)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--json")
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()
    files = [Path(f) for f in a.files] or [ROOT / "staging" / "scripts" / f for f in DEFAULT_FILES]
    report = {}
    for f in files:
        report[f.name] = audit_file(f)
    summary = []
    for fname, classes in report.items():
        ncls = len(classes)
        nreg = sum(1 for c in classes if c["registered"])
        ngap_cls = sum(1 for c in classes if c["gaps"])
        ngap = sum(len(c["gaps"]) for c in classes)
        nobj = sum(1 for c in classes for g in c["gaps"] if g["objective_link"])
        nptr = sum(len(c["raw_pointers"]) for c in classes)
        summary.append(dict(file=fname, classes=ncls, classes_with_registration=nreg,
                            classes_with_gaps=ngap_cls, gap_vars=ngap, objective_linked=nobj,
                            registered_raw_pointers=nptr))
        print(f"{fname}: classes={ncls} registered={nreg} gap_classes={ngap_cls} "
              f"gap_vars={ngap} objective_linked={nobj} raw_ptr_saved={nptr}")
        flat = sorted(((g["score"], c["cls"], g) for c in classes for g in c["gaps"]),
                      key=lambda t: -t[0])
        for score, cls, g in flat[:a.top]:
            print(f"   [{score}] {cls}::{g['name']} ({g['type']}) decl:{g['decl_line']} "
                  f"{g['level']} w={','.join(g['write_methods'])} r={','.join(g['read_methods'])} "
                  f"evw={g['event_write_lines']}{' OBJ' if g['objective_link'] else ''}")
        for c in classes:
            for d in c["dropped_ids"]:
                print(f"   DUPE-ID {c['cls']}::{d['name']} id={d['id']} (kept {d['kept']}) "
                      f"line:{d['line']}")
            for p in c["raw_pointers"]:
                print(f"   RAWPTR {c['cls']}::{p['name']} ({p['type']}) decl:{p['line']}")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=summary, files=report), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
