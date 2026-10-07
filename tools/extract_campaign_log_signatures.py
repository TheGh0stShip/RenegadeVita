#!/usr/bin/env python3
"""Grep a pulled Renegade Vita runtime log for the campaign test-plan signatures.

Companion to reports/campaign/PHYSICAL_CAMPAIGN_TEST_PLAN.md.  Read-only: it
parses one runtime log (ux0:data/renegade/user/logs/<candidate>-runtime.log)
and, optionally, checks which signatures a candidate ELF can emit at all.

    python3 tools/extract_campaign_log_signatures.py LOG [--json] [--only M05]
    python3 tools/extract_campaign_log_signatures.py LOG --elf candidate.elf
    python3 tools/extract_campaign_log_signatures.py --elf candidate.elf

The log is cut into per-mission sessions at every
"A4 campaign: original selection source=... archive=..." line, so every hit is
attributed to the mission session that produced it.  The result is evidence
from a log only.  It never proves visual, audio or control correctness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# kind: flow = expected on a healthy run; mission = mission-specific evidence;
# warn = fallback or anomaly worth reading; bad = should never appear.
# elf: literal text the candidate must contain for the line to be emittable
# (None = no literal check).  compiled_out: Debug_Say/WWDEBUG_SAY lines that
# the Vita build (no WWDEBUG define) compiles to nothing; never expect them.
SIGNATURES = [
    # id, kind, mission scope, regex, elf literal, note
    ("sel", "flow", "all", r"A4 campaign: original selection source=(?P<source>\S+) archive=(?P<archive>\S+) save=(?P<save>\d)", "A4 campaign: original selection source=", "mission level load"),
    ("done", "flow", "all", r"A3\.5 mission completion: original Combat event observed success=(?P<ok>\d)", "A3.5 mission completion: original Combat event observed success=", "Mission_Complete(true/false) reached the Vita misc handler"),
    ("star_killed", "warn", "all", r"A3\.5 mission completion: original Combat star-killed event observed", "A3.5 mission completion: original Combat star-killed", "player death"),
    ("dispatch", "flow", "all", r"A4 campaign: dispatching observed mission success to original CampaignManager", "A4 campaign: dispatching observed mission success", "success handed to CampaignManager"),
    ("interm", "flow", "all", r"A4 campaign: original intermission frame=\d+ score/movie=(?P<score>\d)/(?P<movie>\d)", "A4 campaign: original intermission frame=", "Score/Movie intermission pump"),
    ("latched", "flow", "all", r"A4 campaign: original intermission latched next source=(?P<next>\S+)", "A4 campaign: original intermission latched next source=", "next Level latched"),
    ("released", "flow", "all", r"A4 campaign: clean session released; entering original next source=(?P<next>\S+)", "A4 campaign: clean session released; entering original next", "session torn down, handoff"),
    ("restored", "flow", "all", r"A4 campaign: restored original CampaignManager chunk bytes=(?P<bytes>\d+) source=(?P<source>\S+)", "A4 campaign: restored original CampaignManager chunk", "next session restored campaign state"),
    ("rank", "flow", "all", r"A3\.5 mission ranks: write=(?P<ok>\d) op=set key=(?P<key>\S+) value=(?P<value>\d+) entries=(?P<entries>\d+)", "A3.5 mission ranks: write=", "rank write at score screen"),
    ("rank_load", "flow", "all", r"A3\.5 mission ranks: load=(?P<ok>\d) entries=(?P<entries>\d+)", "A3.5 mission ranks: load=", "rank file read at session start"),
    ("save", "flow", "all", r"A3\.5 save write: path=(?P<path>\S+) bytes=(?P<bytes>-?\d+) elapsed_us=(?P<us>\d+) success=(?P<ok>\d)", "A3.5 save write: path=", "every atomic save (quick/manual/auto)"),
    ("residual", "flow", "all", r"\[LIFECYCLE\] SESSION residual index=(?P<index>\d+)", "[LIFECYCLE] SESSION residual index=", "per-session heap/vitaGL residual (parsed into the residual table)"),
    ("preload", "flow", "all", r"A4 campaign preload: original mission dependency list return archive=(?P<archive>\S+) elapsed_ms=(?P<ms>\d+)", "A4 campaign preload: original mission dependency list return", "mission preload time"),
    ("m08_fallback", "mission", "M01,M04", r"A4 campaign: retail M08 texture fallback mounted archive=(?P<archive>\S+) for lv8_hbag\.tga", "A4 campaign: retail M08 texture fallback mounted", "lv8_hbag.tga supplement (M01 and M04 only)"),
    ("m08_fallback_missing", "warn", "M01,M04", r"A4 campaign: retail M08\.mix unavailable", "A4 campaign: retail M08.mix unavailable", "supplement mount failed"),
    ("anim_prep", "mission", "all", r"A4 cinematic animation preparation: archive=(?P<archive>\S+) named=(?P<named>\d+) attempted=(?P<att>\d+) loaded=(?P<loaded>\d+) memory_floor=(?P<floor>\d+)", "A4 cinematic animation preparation: archive=", "cinematic anim prewarm (want memory_floor=0, loaded==named)"),
    ("preset_prep", "mission", "all", r"A4 cinematic preset preparation: archive=(?P<archive>\S+) scripts=(?P<scripts>\d+) presets=(?P<presets>\d+) warmed=(?P<warmed>\d+) memory_floor=(?P<floor>\d+)", "A4 cinematic preset preparation: archive=", "preset warm (memory_floor=1 means it stopped early)"),
    ("slow_cmd", "warn", "all", r"A4 slow campaign cinematic command: file=(?P<file>\S+) owner_id=(?P<owner>-?\d+) us=(?P<us>\d+)", "A4 slow campaign cinematic command: file=", ">=100 ms cinematic command (first 48 per run)"),
    ("m01_cmd", "mission", "M01", r"A4 M01 cinematic command (?P<phase>begin|end): n=(?P<n>\d+) file=(?P<file>\S+)", "A4 M01 cinematic command begin", "M01 intro breadcrumbs (first 160 X1* commands)"),
    ("m01_phase", "mission", "M01", r"A4 M01 intro phase: frame=(?P<frame>\d+) phase=(?P<phase>\S+)", "A4 M01 intro phase: frame=", "M01 intro frame stage (first 120 frames)"),
    ("m01_prep", "mission", "M01", r"A4 M01 (?P<what>\w+) preparation:", "A4 M01 %s preparation: model=", "M01 retained render-object preparation"),
    ("pct_watchdog", "warn", "M01", r"A4 M01 PCT unlock watchdog", "A4 M01 PCT unlock watchdog", "PCT EVA chain did not finish within 30 s; pen unlocked by fallback"),
    ("gate_fallback", "warn", "M01", r"A4 M01 open-gate objective fallback", "A4 M01 open-gate objective fallback", "'Open the gate' objective added by 30 s fallback"),
    ("duncan", "mission", "M01", r"A4 M01 Duncan(?: shack zone)?: (?P<what>.*)", "A4 M01 Duncan", "Duncan / ion beacon handoff"),
    ("m13_finale", "mission", "M13", r"M13 finale: (?P<what>.*)", "M13 finale:", "M13 finale delivery trace"),
    ("mendoza_wp", "warn", "M05,M06", r"A3\.5 Mendoza death camera: waypath 3000100 unusable", "A3.5 Mendoza death camera: waypath", "boss death-camera fallback (data should make this unreachable)"),
    ("raveshaw_land", "warn", "M08", r"A3\.8 Raveshaw jump: grounded landing fallback", "A3.8 Raveshaw jump: grounded landing fallback", "boss jump-landing fallback fired (max 4/run)"),
    ("elev_timeout", "warn", "M09,M11,all", r"A4 elevator entry timeout v1: obj=(?P<obj>-?\d+) def=(?P<def>\S+) elevator=(?P<elev>\d+) floor=(?P<floor>-?\d+) entry_seconds=(?P<sec>[\d.]+) dist=(?P<dist>[\d.]+) inside=(?P<inside>[01]) action=(?P<action>\S+)", "A4 elevator entry timeout v1:", "AI elevator ENTERING 5 s fallback (inside=1 fired; inside=0 still stuck)"),
    ("anim_forced", "warn", "M09,M11,all", r"A4 animation action forced complete: obj=(?P<obj>-?\d+) def=(?P<def>\S+) anim=(?P<anim>\S+) stalled_seconds=(?P<sec>[\d.]+)", "A4 animation action forced complete: obj=", "5 s animation-stall watchdog"),
    ("death_popup", "warn", "all", r"A4 death: original popup active dialogs=(?P<dialogs>\d+)", "A4 death: original popup active", "death/failure popup shown"),
    ("reload", "warn", "all", r"A4 (?P<owner>[\w-]+): original reload begin map=(?P<map>\S+)", "original reload begin map=", "restart/load reload inside the same process"),
    ("replay", "mission", "all", r"A4 replay: original CampaignManager started source=(?P<source>\S+) difficulty=(?P<d>\d)", "A4 replay: original CampaignManager started", "mission replay"),
    ("autosave_cleared", "warn", "all", r"A4 campaign: cleared unconsumed autosave request at session end", "A4 campaign: cleared unconsumed autosave request", "autosave request dropped (pause->quit on frame 1)"),
    ("circle_latch", "mission", "all", r"Circle tap latched original crouch key", "Circle tap latched original crouch key", "first quick Circle tap latched crouch"),
    ("power", "warn", "all", r"A3\.6 power: (?:resume observed|WARNING low battery)", "A3.6 power: ", "suspend/resume or low battery"),
    # Never expected: compiled out on the Vita build (no WWDEBUG). Listed so nobody waits for them.
    ("swept", "compiled_out", "all", r"ScriptZone \d+ swept entry", None, "Debug_Say, not in the Vita log; judge swept entry by the objective effect"),
    ("script_missing", "compiled_out", "all", r"native provider missing script|Unable to create script", None, "Debug_Say/WWDEBUG_SAY, not in the Vita log"),
    # Evidence-health problems.
    ("trunc", "bad", "all", r"\[runtime-log\] TRUNCATED", "[runtime-log] TRUNCATED",  "4 MiB log cap hit: only [LIFECYCLE]/FATAL/crash/Teardown/Overall lines follow"),
    ("fatal", "bad", "all", r"\bFATAL\b|\bcrash(?:ed)?\b", None, "fatal/crash text (priority lines)"),
    ("controlled_fail", "bad", "all", r"\[LIFECYCLE\] END status=controlled-failure", "[LIFECYCLE] END status=controlled-failure", "controlled failure exit"),
    ("handoff_fail", "bad", "all", r"A4 campaign: (?:handoff failure|failed handoff|controlled handoff recovery|rejected invalid session handoff|rejected save campaign/source mismatch|original mission MIX unavailable|retail campaign catalog missing)|A4 load: local failure", None, "campaign handoff or load failure"),
    ("rank_fail", "bad", "all", r"A3\.5 mission ranks: write=0", None, "rank write failed"),
    ("save_fail", "bad", "all", r"A3\.5 save write: .* success=0", None, "save write failed"),
    ("unsupported", "bad", "all", r"unsupported-submit", None, "renderer rejected a submission"),
]
COMPILED = [(s[0], s[1], s[2], re.compile(s[3]), s[4], s[5]) for s in SIGNATURES]
RESIDUAL = re.compile(r"\[LIFECYCLE\] SESSION residual index=(\d+) frames=(\d+) heap arena/in_use/free/free_chunks=(\d+)/(\d+)/(\d+)/(\d+) vitagl=(\d) ram/vram/all_free=(\d+)/(\d+)/(\d+) user_free=(-?\d+)")
PERF = re.compile(r"A3\.5 perf: frames=(\d+) .*?avg_fps=([\d.]+) frame_us min/p50/p95/p99/max=(\d+)/(\d+)/(\d+)/(\d+)/(\d+).*?backend_errors=(\d+)")
MIB = 1024 * 1024
GROWTH_WARN = MIB  # SESSION_CHAIN_ACCUMULATION.md: >= 1 MiB per handoff is retained state


def read_log(path: Path):
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def segment(lines):
    """Split into mission sessions at each selection line; label M01.mix#1 etc."""
    segs, current, seen = [], {"label": "(boot/menu)", "start": 1, "lines": []}, {}
    sel = next(s for s in COMPILED if s[0] == "sel")[3]
    for number, text in enumerate(lines, 1):
        match = sel.search(text)
        if match:
            segs.append(current)
            archive = match.group("archive").split("\\")[-1].split("/")[-1]
            seen[archive] = seen.get(archive, 0) + 1
            current = {"label": f"{archive}#{seen[archive]}", "archive": archive, "start": number, "lines": []}
        current["lines"].append((number, text))
    segs.append(current)
    return [s for s in segs if s["lines"]]


def mission_of(label):
    m = re.match(r"(M\d+)", label)
    return m.group(1) if m else None


def scan_segment(seg):
    hits = {}
    for number, text in seg["lines"]:
        for sid, kind, scope, rx, _lit, _note in COMPILED:
            match = rx.search(text)
            if match:
                hits.setdefault(sid, []).append((number, match, text))
    return hits


def m01_unmatched(hits):
    """A trailing 'begin' with no 'end' names the stalled M01 intro command."""
    begins, ends = {}, set()
    for number, match, text in hits.get("m01_cmd", []):
        if match.group("phase") == "begin":
            begins[match.group("n")] = (number, text)
        else:
            ends.add(match.group("n"))
    return [(n, begins[n]) for n in begins if n not in ends]


def analyse(lines):
    segs = segment(lines)
    trunc_line = next((i for i, t in enumerate(lines, 1) if "[runtime-log] TRUNCATED" in t), None)
    report = {"lines": len(lines), "truncated_at_line": trunc_line, "segments": [], "residual": [], "ranks": []}
    prev = None
    for seg in segs:
        hits = scan_segment(seg)
        mission = mission_of(seg["label"])
        entry = {"label": seg["label"], "start_line": seg["start"], "hits": {}, "verdicts": [], "flags": []}
        for sid, items in hits.items():
            entry["hits"][sid] = {"count": len(items), "first_line": items[0][0], "first": items[0][2].strip()[:200]}
        done = hits.get("done", [])
        if mission:
            if not done:
                entry["verdicts"].append("no mission-completion line (still playing, failed, or log capped)")
            else:
                oks = [m.group("ok") for _n, m, _t in done]
                entry["verdicts"].append("success=1 seen" if "1" in oks else "only success=0 seen")
            ranks = [m for _n, m, _t in hits.get("rank", [])]
            if ranks:
                entry["verdicts"].append("rank " + ", ".join(f"{m.group('key')}={m.group('value')}(write={m.group('ok')},entries={m.group('entries')})" for m in ranks))
                for m in ranks:
                    report["ranks"].append((m.group("key"), int(m.group("value")), int(m.group("ok"))))
            elif done:
                entry["flags"].append("success without a rank write line")
        for n, (line, text) in m01_unmatched(hits) if mission == "M01" else []:
            entry["flags"].append(f"M01 intro command begin with no end: n={n} line {line}: {text.strip()[:140]}")
        phases = hits.get("m01_phase", [])
        if mission == "M01" and phases:
            last = phases[-1]
            entry["verdicts"].append(f"last M01 intro phase: frame={last[1].group('frame')} {last[1].group('phase')} (line {last[0]})")
        for _n, m, _t in hits.get("anim_prep", []):
            if m.group("floor") != "0" or m.group("loaded") != m.group("named"):
                entry["flags"].append(f"animation prewarm incomplete: archive={m.group('archive')} named={m.group('named')} loaded={m.group('loaded')} memory_floor={m.group('floor')}")
        for _n, m, _t in hits.get("elev_timeout", []):
            if m.group("inside") == "0":
                entry["flags"].append(f"elevator ENTERING still outside the zone after 5 s: obj={m.group('obj')} def={m.group('def')}")
        for _n, m, _t in hits.get("anim_forced", []):
            if m.group("obj") in ("2000010",):
                entry["flags"].append("animation watchdog fired on Mobius (2000010)")
        perf = [PERF.search(t) for _n, t in seg["lines"]]
        perf = [p for p in perf if p]
        if perf:
            fps = min(float(p.group(2)) for p in perf)
            p99 = max(int(p.group(6)) for p in perf)
            worst = max(int(p.group(7)) for p in perf)
            errors = max(int(p.group(8)) for p in perf)
            entry["perf"] = {"windows": len(perf), "min_avg_fps": fps, "max_p99_us": p99, "max_frame_us": worst, "max_backend_errors": errors}
            if errors:
                entry["flags"].append(f"backend_errors reached {errors}")
        if report["truncated_at_line"] and seg["start"] > report["truncated_at_line"]:
            entry["flags"].append("session starts after the log cap: only priority lines are available")
        for sid in ("trunc", "fatal", "controlled_fail", "handoff_fail", "rank_fail", "save_fail", "unsupported", "star_killed", "death_popup", "reload", "pct_watchdog", "gate_fallback", "raveshaw_land", "mendoza_wp", "m08_fallback_missing", "autosave_cleared"):
            if sid in hits:
                entry["flags"].append(f"{sid} x{len(hits[sid])} (first line {hits[sid][0][0]})")
        for number, text in seg["lines"]:
            r = RESIDUAL.search(text)
            if r:
                v = [int(x) for x in r.groups()]
                row = {"line": number, "segment": seg["label"], "index": v[0], "frames": v[1], "in_use": v[3], "free_chunks": v[5], "all_free": v[9], "user_free": v[10]}
                if prev is not None and row["index"] == prev["index"] + 1:
                    row["in_use_delta"] = row["in_use"] - prev["in_use"]
                    row["all_free_delta"] = row["all_free"] - prev["all_free"]
                prev = row
                report["residual"].append(row)
        report["segments"].append(entry)
    return report


def elf_check(path: Path):
    blob = path.read_bytes()
    rows = []
    for sid, kind, scope, _rx, literal, note in COMPILED:
        if kind == "compiled_out":
            rows.append((sid, "NEVER (compiled out on Vita)", note))
        elif literal is None:
            rows.append((sid, "n/a (no literal)", note))
        else:
            rows.append((sid, "ARMED" if literal.encode() in blob else "MISSING", note))
    return rows


def render(report):
    out = [f"log lines: {report['lines']}"]
    if report["truncated_at_line"]:
        out.append(f"!! log cap reached at line {report['truncated_at_line']}: later non-priority evidence is lost")
    for seg in report["segments"]:
        out.append("")
        out.append(f"== {seg['label']} (line {seg['start_line']})")
        for v in seg["verdicts"]:
            out.append(f"   . {v}")
        if "perf" in seg:
            p = seg["perf"]
            out.append(f"   . perf windows={p['windows']} min_avg_fps={p['min_avg_fps']:.2f} max_p99={p['max_p99_us']}us max_frame={p['max_frame_us']}us backend_errors_max={p['max_backend_errors']}")
        for flag in seg["flags"]:
            out.append(f"   ! {flag}")
        interesting = [k for k in seg["hits"] if k not in ("sel", "rank", "done", "save", "residual")]
        if interesting:
            out.append("   hits: " + ", ".join(f"{k} x{seg['hits'][k]['count']}@{seg['hits'][k]['first_line']}" for k in sorted(interesting)))
        saves = seg["hits"].get("save")
        if saves:
            out.append(f"   saves: {saves['count']} (first line {saves['first_line']}: {saves['first'][:120]})")
    if report["residual"]:
        out += ["", "== [LIFECYCLE] SESSION residual (want flat in_use / all_free between consecutive sessions)"]
        for r in report["residual"]:
            delta = ""
            if "in_use_delta" in r:
                mark = "  <-- GROWTH >= 1 MiB" if r["in_use_delta"] >= GROWTH_WARN else ""
                delta = f" d_in_use={r['in_use_delta']:+d} d_all_free={r['all_free_delta']:+d}{mark}"
            out.append(f"   idx={r['index']:>2} {r['segment']:<12} frames={r['frames']:<6} in_use={r['in_use'] / MIB:7.2f}MiB all_free={r['all_free'] / MIB:7.2f}MiB free_chunks={r['free_chunks']}{delta}")
    keys = [k for k, _v, ok in report["ranks"] if ok]
    if keys:
        out += ["", "== mission-rank writes in log order: " + " ".join(keys),
                "   expected on a full run: M13 M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11"]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("log", nargs="?", type=Path, help="pulled <candidate>-runtime.log")
    parser.add_argument("--elf", type=Path, help="candidate ELF: report which signatures it can emit")
    parser.add_argument("--only", help="show only sessions whose label starts with this (e.g. M05)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    if not args.log and not args.elf:
        parser.error("give a log, an --elf, or both")
    result, text = {}, []
    if args.elf:
        rows = elf_check(args.elf)
        result["elf"] = [{"id": a, "state": b, "note": c} for a, b, c in rows]
        text.append("signature armed in ELF?\n" + "\n".join(f"   {a:<18} {b:<30} {c}" for a, b, c in rows))
    if args.log:
        report = analyse(read_log(args.log))
        if args.only:
            report["segments"] = [s for s in report["segments"] if s["label"].upper().startswith(args.only.upper())]
        result["log"] = report
        text.append(render(report))
    print(json.dumps(result, indent=1) if args.json else "\n\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
