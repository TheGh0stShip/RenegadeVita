#!/usr/bin/env python3
"""Turn returned Renegade Vita runtime logs into a tutorial performance report.

Input: one runtime log (``ux0:data/renegade/user/logs/a35-devNNN-runtime.log``)
or two (A/B). Output: Markdown and/or JSON with

- a per-tutorial-segment table (frames, FPS, frame-time p50/p95/p99/worst,
  slow-frame counts, stage split), segments delimited by the original
  Mission00 conversation/objective breadcrumbs the runtime already logs in
  ``A3.5 mission progress`` lines (spawn, logan, sydney, gunner, vehicles,
  mobius, base, end), plus boot/load/post;
- top ``A3.6 frame-profile`` scopes per segment;
- memory and pool high-water (heap, vitaGL transient pools, static mesh and
  skin caches, decoded PCM) and audio allocation failures;
- renderer/simulation counters (static mesh cache, vertex arrays, GL-state
  shadow, texture state, FFP program compiles, missed vblanks, VIS census,
  Combat casts, campaign pacing drift);
- a hitch list (frames over ``--hitch-ms``) with the nearest preceding
  breadcrumb;
- level-load milestones, switch configuration and log-integrity notes;
- for two logs, an A/B delta table with a simple noise verdict.

Only the standard library is used. Unknown lines are counted, never fatal;
truncated logs (session cap, dropped lines, a cut final line) are reported.
Every number is derived from log fields; nothing is a hardware measurement
claim beyond what the log states. Percentiles over several 120-frame windows
are estimates (see ``mixture_quantile``); single-window values are exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.0"

# Original Mission00 route order (Scripts/Mission00.cpp): objective 1 is
# accomplished at MTU_SYDNEY_START, 2 at MTU_GUNNER_START, 3 at
# MTU_HOTWIRE_INTRO, 4 at MTU_MOBIUS_REFINERY, 5 at MTU_PETROVA_POWER and 6
# when the second Nod officer dies (MTU_TYPE_COUNT_OFFICERS).
TUTORIAL_SEGMENTS = ("spawn", "logan", "sydney", "gunner", "vehicles", "mobius", "base", "end")
SEGMENT_ORDER = ("boot", "load") + TUTORIAL_SEGMENTS + ("gameplay", "post")
SEGMENT_RANK = {name: index for index, name in enumerate(TUTORIAL_SEGMENTS)}
SEGMENT_TITLES = {
    "boot": "boot/frontend", "load": "level load", "spawn": "spawn (pre-Logan)",
    "logan": "Logan course", "sydney": "Sydney (health/armor)", "gunner": "Gunner range",
    "vehicles": "Hotwire vehicles", "mobius": "Mobius refinery",
    "base": "base (Petrova power, assault)", "end": "end (officers down)",
    "gameplay": "gameplay (non-tutorial level)", "post": "post-mission",
}

# Conversation names come from Say_Something (Mission00.cpp) and are logged
# by the runtime as "active=<name>". Logan's transitional lines belong to the
# segment they introduce.
CONVERSATION_RULES = (
    (re.compile(r"^MTU_(?:LOGAN_(?:START|CROUCH|CROUCH_TEST|HEARD|SNEAK_LOSE|SNEAK_WIN|"
                r"JUMP_TEST|EVA|POKE|COURSE_DONE|KEYCARDS|GO_INSIDE)|GDI_POKE)$"), "logan"),
    (re.compile(r"^MTU_SYDNEY_"), "sydney"),
    (re.compile(r"^MTU_(?:LOGAN_PREPARE_INFANTRY|LOGAN_INTRODUCE_BARRACKS|GUNNER_)"), "gunner"),
    (re.compile(r"^MTU_(?:LOGAN_INTRODUCE_WEAP|HOTWIRE_)"), "vehicles"),
    (re.compile(r"^MTU_(?:LOGAN_WHATSNEXT|LOGAN_INTRODUCE_REFINERY|MOBIUS_)"), "mobius"),
    (re.compile(r"^MTU_(?:LOGAN_PREPARE_POWER|LOGAN_INTRODUCE_POWER|PETROVA_|LOGAN_OUTRO|"
                r"LIEUTENANT_)"), "base"),
)
OBJECTIVE_SEGMENTS = {1: "sydney", 2: "gunner", 3: "vehicles", 4: "mobius", 5: "base", 6: "end"}
OBJECTIVE_PENDING, OBJECTIVE_ACCOMPLISHED, OBJECTIVE_FAILED, OBJECTIVE_HIDDEN = 0, 1, 2, 3

# --------------------------------------------------------------------------
# Line formats (emitters in port/platform/vita/a31_vita_runtime.cpp,
# port/platform/vita/renegade_vita_frame_profile.cpp,
# port/renderer/vita/ww3d_vita_renderer.cpp, ww3d_vita_ffp_program_warm.cpp,
# port/platform/a31_gameplay_boundary.cpp, port/platform/renegade_async_log.h,
# port/platform/vita/vita_platform.cpp).
# --------------------------------------------------------------------------
RE_LIFECYCLE_START = re.compile(r"^\[LIFECYCLE\] START (?P<body>.*)$")
RE_SESSION_RESIDUAL = re.compile(r"^\[LIFECYCLE\] SESSION residual (?P<body>.*)$")
RE_LOG_DROPPED = re.compile(r"^\[runtime-log\] dropped lines while the writer was behind: (\d+)")
RE_LOG_TRUNCATED = re.compile(r"^\[runtime-log\] TRUNCATED")
RE_LOG_SUPPRESSED = re.compile(r"^\[runtime-log\] suppressed lines past session cap: (\d+)")
RE_IDENTITY = re.compile(r"^Runtime identity: candidate=(\S+)")
RE_BREADCRUMB = re.compile(r"^\[(?P<milestone>\S+) (?P<subsystem>[A-Za-z0-9_.-]+) (?P<seq>\d+)\] ?(?P<body>.*)$")
RE_PERF = re.compile(r"^A3\.5 perf: (?P<body>.*)$")
RE_SLOW = re.compile(r"^A4 slow frame: frame=(\d+) total_us=(\d+)(?: sync_us=(\d+))?(?: simulation_us=(\d+))?(?: render_us=(\d+))?")
RE_PROFILE_CLOCK = re.compile(r"^A3\.6 frame-profile: clock-cost (?P<body>.*)$")
RE_PROFILE_CONFIG = re.compile(r"^A3\.6 frame-profile: configured (?P<body>.*)$")
RE_PROFILE = re.compile(r"^A3\.6 frame-profile: (?P<body>version=.*)$")
RE_PROFILE_WORST = re.compile(r"^A3\.6 frame-profile-worst: window=(\d+) frame_index=(\d+) frame_us=(\d+) scope_us:(?P<scopes>.*)$")
RE_PACING = re.compile(r"^A4 campaign pacing: (?P<body>.*)$")
RE_CASTS = re.compile(r"^A4 combat casts: (?P<body>.*)$")
RE_VIS = re.compile(r"^A3\.6 vis-census: (?P<body>.*)$")
RE_HEAP = re.compile(r"^A3\.5 heap: (?P<body>.*)$")
RE_AUDIO = re.compile(r"^A3\.5 audio: (?P<body>.*)$")
RE_LAST_ERROR = re.compile(r"\blast_error=(.*)$")
RE_PROGRESS = re.compile(r"^A3\.5 mission progress: frame=(\d+)(?P<body>.*)$")
RE_CONTROL = re.compile(r"^A3\.5 mission progress: original player control available for route activation frame=(\d+)")
RE_COMPLETION = re.compile(r"^A3\.5 mission completion: .*?success=(\d+)(?: frame=(\d+))?")
RE_TRANSITION = re.compile(r"^A3\.5 breadcrumb: original mission (success|failure) transition detected")
RE_FIRST_FRAME = re.compile(r"^A3\.1 breadcrumb: first original render frame PASS")
RE_CHECKPOINT = re.compile(r"^A3\.5 breadcrumb: (\d+)-frame checkpoint PASS")
RE_LEVEL_SELECT = re.compile(r"^A4 campaign: original selection source=(\S+) archive=(\S+)")
RE_LEVEL_LOAD = re.compile(r"^A3\.5 level load: original source=(\S+)")
RE_MAIN_MENU = re.compile(r"^A4 main menu: Display entry")
RE_INTERACTIVE_COMPLETE = re.compile(r"^A3\.1 interactive: complete (?P<body>.*)$")
RE_STATIC_DIRECT_MEMORY = re.compile(r"^A3\.5 static direct: .*\bmemory_user=")
RE_PRELOAD = re.compile(r"^A4 (\S+) round-4 preload: mode=(\d+)")
RE_ELAPSED_MS = re.compile(r"\belapsed_ms=(\d+)")
RE_ELAPSED_US = re.compile(r"\belapsed_us=(\d+)")
LOAD_MILESTONES = (
    (re.compile(r"^A3\.5 startup: .*startup_ms=(\d+)"), "startup"),
    (re.compile(r"^A3\.5 prewarm: startup-precache complete"), "startup precache complete"),
    (RE_LEVEL_SELECT, "level selection"),
    (re.compile(r"^A4 campaign preload: original mission dependency list begin"), "mission dependency preload begin"),
    (re.compile(r"^A4 campaign preload: original mission dependency list return"), "mission dependency preload return"),
    (RE_LEVEL_LOAD, "level load"),
    (re.compile(r"^A3\.1 M00 load: threaded load complete"), "threaded load complete"),
    (re.compile(r"^A3\.5 prewarm: m00-scene complete"), "M00 scene prewarm complete"),
    (RE_PRELOAD, "round-4 preload"),
    (re.compile(r"^\[\S+ ffp-program-cache \d+\] prewarm:"), "FFP program prewarm"),
    (RE_FIRST_FRAME, "first gameplay frame"),
    (RE_CONTROL, "player control available"),
    (RE_COMPLETION, "mission completion"),
    (re.compile(r"^A3\.5 mission completion: original Combat star-killed"), "player killed"),
    (RE_TRANSITION, "mission transition"),
    (RE_MAIN_MENU, "main menu"),
)

BREADCRUMB_LABEL_RE = re.compile(r"^([a-z][\w-]*):\s+(.*)$")
CONFIG_KEYS = ("enabled", "mode", "effective", "source", "default")
NAMES_VALUES_RE = re.compile(r"^([A-Za-z_][\w/]*):(-?[\d.]+(?:/-?[\d.]+)*)$")
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d*$")
SCOPE_RE = re.compile(r"(\S+?)=(\d+)/([\d.]+)")
WORST_SCOPE_RE = re.compile(r"(\S+?)=(\d+)(?=\s|$)")


def _number(text: str) -> Any:
    if INT_RE.match(text):
        return int(text)
    if FLOAT_RE.match(text):
        return float(text)
    return text


def _put(fields: dict, key: str, value: str) -> None:
    if key in fields:
        index = 2
        while f"{key}#{index}" in fields:
            index += 1
        key = f"{key}#{index}"
    fields[key] = _number(value)


def parse_fields(body: str) -> dict:
    """Parse ``key=value`` tokens, expanding ``a/b/c=1/2/3`` groups.

    A grouped key directly after a bare word takes that word as a prefix
    (``frame_us min/p50=1/2`` -> ``frame_us.min``, ``frame_us.p50``), and
    ``key=a/b:1/2`` becomes ``key.a``/``key.b``. Duplicate keys keep the first
    value and store later ones as ``key#2``.
    """
    fields: dict = {}
    prev_bare = None
    for token in body.split():
        if "=" not in token:
            prev_bare = token.rstrip(":")
            continue
        key, _, value = token.partition("=")
        if not key:
            prev_bare = None
            continue
        grouped = NAMES_VALUES_RE.match(value)
        if grouped and "/" in grouped.group(1):
            names, values = grouped.group(1).split("/"), grouped.group(2).split("/")
            if len(names) == len(values):
                for name, item in zip(names, values):
                    _put(fields, f"{key}.{name}", item)
            else:
                _put(fields, key, value)
        elif "/" in key:
            names, values = key.split("/"), value.split("/")
            prefix = f"{prev_bare}." if prev_bare else ""
            if len(names) == len(values):
                for name, item in zip(names, values):
                    _put(fields, prefix + name, item)
            else:
                _put(fields, prefix + key, value)
        else:
            _put(fields, key, value)
        prev_bare = None
    return fields


def _int(fields: dict, key: str) -> int | None:
    value = fields.get(key)
    return value if isinstance(value, int) else None


def _num(fields: dict, key: str) -> float | None:
    value = fields.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _triplet(value: Any) -> list[int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split("/")
    if not parts or not all(INT_RE.match(part) for part in parts):
        return None
    return [int(part) for part in parts]


def conversation_segment(name: str) -> str | None:
    for pattern, segment in CONVERSATION_RULES:
        if pattern.match(name):
            return segment
    return None


def mixture_quantile(windows: list[tuple[float, list[tuple[float, float]]]], q: float) -> float | None:
    """Quantile of a frame-weighted mixture of per-window piecewise CDFs.

    Each window contributes anchors (F, value): (0, low), (0.50, p50),
    (0.95, p95), (0.99, p99), (1, high) as logged. Between anchors the CDF is
    linear. With one window the logged p50/p95/p99 are reproduced exactly;
    with several it is an estimate of the pooled percentile.
    """
    usable = [(weight, anchors) for weight, anchors in windows if weight > 0 and anchors]
    if not usable:
        return None
    total = sum(weight for weight, _ in usable)

    def cdf(anchors: list[tuple[float, float]], value: float) -> float:
        if value < anchors[0][1]:
            return 0.0
        for (f0, v0), (f1, v1) in zip(anchors, anchors[1:]):
            if value <= v1:
                if v1 <= v0:
                    return f1
                return f0 + (f1 - f0) * (value - v0) / (v1 - v0)
        return 1.0

    low = min(anchors[0][1] for _, anchors in usable)
    high = max(anchors[-1][1] for _, anchors in usable)
    if q <= 0:
        return low
    for _ in range(100):
        if high - low <= 1e-6:
            break
        middle = (low + high) / 2.0
        mass = sum(weight * cdf(anchors, middle) for weight, anchors in usable) / total
        if mass < q:
            low = middle
        else:
            high = middle
    return high


def window_anchors(low: float | None, p50: float | None, p95: float | None,
                   p99: float | None, high: float | None) -> list[tuple[float, float]]:
    points = [(0.5, p50), (0.95, p95), (0.99, p99), (1.0, high)]
    present = [(f, float(v)) for f, v in points if v is not None]
    if not present:
        return []
    first = float(low) if low is not None else present[0][1]
    anchors = [(0.0, min(first, present[0][1]))]
    for f, v in present:
        anchors.append((f, max(v, anchors[-1][1])))
    if anchors[-1][0] < 1.0:
        anchors.append((1.0, anchors[-1][1]))
    return anchors


# --------------------------------------------------------------------------
# Per-segment accumulation
# --------------------------------------------------------------------------
def _new_segment() -> dict:
    return {
        "visits": 0, "lines": 0, "windows": [], "frames": 0, "time_us": 0.0,
        "slow": {"over_16_7ms": 0, "over_20ms": 0, "over_33ms": 0, "over_50ms": 0},
        "stage_us_total": {"sync": 0.0, "sim": 0.0, "render": 0.0}, "stage_frames": 0,
        "stage_error_us": 0.0, "worst": None, "profile": {"windows": 0, "frames": 0,
        "frame_us_total": 0, "scopes": {}, "est_clock_us_total": 0, "overflow_max": 0},
        "pacing": {"frames": 0, "totals": {}, "drift_ms": 0},
        "casts": {"frames": 0, "totals": {}},
        "vis": {"samples": 0, "totals": {}},
        "counters": {}, "maxima": {}, "minima": {}, "audio_errors": [],
        "renderer_frames": {},
    }


class CumulativeDeltas:
    """Deltas of monotonically increasing counters; a decrease is a reset."""

    def __init__(self) -> None:
        self.previous: dict[tuple, float] = {}
        self.resets = 0

    def delta(self, key: tuple, value: float | None) -> float:
        if value is None:
            return 0.0
        previous = self.previous.get(key)
        self.previous[key] = value
        if previous is None:
            return float(value)
        if value < previous:
            self.resets += 1
            return float(value)
        return float(value - previous)


class SessionAnalyzer:
    def __init__(self, lines: list[str], first_line: int, hitch_ms: float) -> None:
        self.lines = lines
        self.first_line = first_line
        self.hitch_us = hitch_ms * 1000.0
        self.segment = "boot"
        self.level: str | None = None
        self.levels: list[str] = []
        self.tutorial = None
        self.segments: dict[str, dict] = {}
        self.transitions: list[dict] = []
        self.events: list[dict] = []
        self.hitches: list[dict] = []
        self.load_milestones: list[dict] = []
        self.config: dict[str, Any] = {}
        self.integrity: dict[str, Any] = {
            "dropped_lines": 0, "suppressed_lines": 0, "truncated_at_line": None,
            "perf_windows": 0, "perf_window_gaps": 0, "counter_resets": 0,
            "unparsed_records": 0, "unknown_lines": 0, "unknown_prefixes": {},
        }
        self.candidate: str | None = None
        self.current_frame: int | None = None
        self.last_perf: dict | None = None
        self.last_perf_frames: int | None = None
        self.pending_profile: dict | None = None
        self.prev_progress: dict | None = None
        self.cumulative = CumulativeDeltas()
        self.run_summaries: list[dict] = []
        self.session_residuals: list[dict] = []
        self.profile_alignment = {"checked": 0, "aligned": 0}
        self.audio_last_error = None

    # ---- segment bookkeeping -------------------------------------------
    def seg(self, name: str | None = None) -> dict:
        name = name or self.segment
        if name not in self.segments:
            self.segments[name] = _new_segment()
        return self.segments[name]

    def transition(self, segment: str, line: int, trigger: str) -> None:
        if segment == self.segment and self.transitions:
            return
        self.segment = segment
        self.seg(segment)["visits"] += 1
        self.transitions.append({"segment": segment, "line": line, "frame": self.current_frame,
                                 "trigger": trigger})

    def advance_tutorial(self, segment: str | None, line: int, trigger: str) -> None:
        if segment is None or self.segment not in SEGMENT_RANK:
            return
        if SEGMENT_RANK[segment] > SEGMENT_RANK[self.segment]:
            self.transition(segment, line, trigger)

    def enter_gameplay(self, line: int, trigger: str) -> None:
        if self.segment in ("boot", "load"):
            gameplay = "gameplay" if self.tutorial is False else "spawn"
            self.transition(gameplay, line, trigger)

    def event(self, kind: str, label: str, line: int, frame: int | None = None) -> None:
        self.events.append({"kind": kind, "label": label, "line": line,
                            "frame": frame if frame is not None else self.current_frame,
                            "segment": self.segment})

    def segment_at_frame(self, frame: int | None, line: int) -> str:
        """Segment in effect at a gameplay frame no later than ``line``."""
        chosen = None
        for item in self.transitions:
            if item["line"] > line:
                break
            if frame is None or item["frame"] is None or item["frame"] <= frame:
                chosen = item["segment"]
        return chosen or "boot"

    def bump(self, kind: str, name: str, value: float | None, mode: str) -> None:
        if value is None:
            return
        bucket = self.seg()
        if mode == "max":
            store = bucket["maxima"]
            store[f"{kind}.{name}"] = max(store.get(f"{kind}.{name}", value), value)
        elif mode == "min":
            store = bucket["minima"]
            store[f"{kind}.{name}"] = min(store.get(f"{kind}.{name}", value), value)
        else:
            store = bucket["counters"]
            store[f"{kind}.{name}"] = store.get(f"{kind}.{name}", 0) + value

    # ---- parsing ---------------------------------------------------------
    def run(self) -> None:
        for offset, raw in enumerate(self.lines):
            line_no = self.first_line + offset
            text = raw.replace("\x00", "").rstrip("\r\n")
            if not text.strip():
                continue
            self.seg()["lines"] += 1
            if not self.dispatch(text, line_no):
                self.integrity["unknown_lines"] += 1
                prefix = re.sub(r"\d+", "N", text[:40]).split(":")[0].split("=")[0][:32]
                counts = self.integrity["unknown_prefixes"]
                counts[prefix] = counts.get(prefix, 0) + 1
        self.integrity["counter_resets"] += self.cumulative.resets

    def dispatch(self, text: str, line: int) -> bool:
        handled = self.parse_structural(text, line)
        milestone = self.parse_load_milestone(text, line)
        return handled or milestone

    def parse_load_milestone(self, text: str, line: int) -> bool:
        for pattern, label in LOAD_MILESTONES:
            if pattern.match(text):
                elapsed = None
                match = RE_ELAPSED_MS.search(text)
                if match:
                    elapsed = float(match.group(1))
                else:
                    match = RE_ELAPSED_US.search(text)
                    if match:
                        elapsed = int(match.group(1)) / 1000.0
                if len(self.load_milestones) < 200:
                    self.load_milestones.append({"label": label, "line": line,
                                                 "segment": self.segment, "frame": self.current_frame,
                                                 "elapsed_ms": elapsed, "text": text[:160]})
                self.event("milestone", label, line)
                return True
        return False

    def parse_structural(self, text: str, line: int) -> bool:  # noqa: C901 - flat dispatch
        match = RE_LOG_DROPPED.match(text)
        if match:
            self.integrity["dropped_lines"] += int(match.group(1))
            return True
        if RE_LOG_TRUNCATED.match(text):
            if self.integrity["truncated_at_line"] is None:
                self.integrity["truncated_at_line"] = line
            return True
        match = RE_LOG_SUPPRESSED.match(text)
        if match:
            self.integrity["suppressed_lines"] = max(self.integrity["suppressed_lines"], int(match.group(1)))
            return True
        if RE_LIFECYCLE_START.match(text):
            return True
        match = RE_SESSION_RESIDUAL.match(text)
        if match:
            fields = parse_fields(match.group("body"))
            fields["line"] = line
            self.session_residuals.append(fields)
            return True
        match = RE_IDENTITY.match(text)
        if match:
            self.candidate = self.candidate or match.group(1)
            return True
        match = RE_PERF.match(text)
        if match:
            self.on_perf(parse_fields(match.group("body")), line)
            return True
        match = RE_SLOW.match(text)
        if match:
            self.on_slow(match, line)
            return True
        match = RE_PROFILE_CLOCK.match(text)
        if match:
            self.config.setdefault("frame_profile_clock", parse_fields(match.group("body")))
            return True
        match = RE_PROFILE_CONFIG.match(text)
        if match:
            fields = parse_fields(match.group("body"))
            self.config["RVFP1 frame-profile"] = fields.get("enabled")
            return True
        match = RE_PROFILE.match(text)
        if match:
            self.on_profile(match.group("body"), line)
            return True
        match = RE_PROFILE_WORST.match(text)
        if match:
            self.on_profile_worst(match, line)
            return True
        match = RE_PROGRESS.match(text)
        if match:
            self.on_progress(int(match.group(1)), match.group("body"), line)
            return True
        match = RE_CONTROL.match(text)
        if match:
            self.current_frame = int(match.group(1))
            self.enter_gameplay(line, "player control available")
            return False  # also a load milestone
        match = RE_COMPLETION.match(text)
        if match:
            if match.group(2):
                self.current_frame = int(match.group(2))
            if self.segment not in ("boot", "load"):
                self.transition("post", line, f"mission completion success={match.group(1)}")
            return False
        if RE_TRANSITION.match(text) or RE_MAIN_MENU.match(text):
            if self.segment not in ("boot", "load"):
                self.transition("post", line, text[:60])
            return False
        if RE_FIRST_FRAME.match(text):
            self.enter_gameplay(line, "first gameplay frame")
            return False
        match = RE_CHECKPOINT.match(text)
        if match:
            self.current_frame = int(match.group(1))
            return True
        match = RE_LEVEL_SELECT.match(text) or RE_LEVEL_LOAD.match(text)
        if match:
            archive = match.group(match.lastindex or 1)
            self.on_level(archive, line)
            return False
        match = RE_PRELOAD.match(text)
        if match:
            self.config["RVPL1 preload mode"] = int(match.group(2))
            return False
        match = RE_PACING.match(text)
        if match:
            self.on_pacing(parse_fields(match.group("body")))
            return True
        match = RE_CASTS.match(text)
        if match:
            self.on_casts(parse_fields(match.group("body")))
            return True
        match = RE_VIS.match(text)
        if match:
            self.on_vis(parse_fields(match.group("body")))
            return True
        match = RE_HEAP.match(text)
        if match:
            fields = parse_fields(match.group("body"))
            self.bump("heap", "in_use_bytes", _num(fields, "in_use"), "max")
            self.bump("heap", "arena_bytes", _num(fields, "arena"), "max")
            self.bump("heap", "free_bytes", _num(fields, "free"), "min")
            return True
        match = RE_AUDIO.match(text)
        if match:
            self.on_audio(text, parse_fields(match.group("body")), line)
            return True
        match = RE_INTERACTIVE_COMPLETE.match(text)
        if match:
            fields = parse_fields(match.group("body"))
            fields["line"] = line
            self.run_summaries.append(fields)
            if self.segment not in ("boot", "load"):
                self.transition("post", line, "interactive run complete")
            return True
        if RE_STATIC_DIRECT_MEMORY.match(text):
            fields = parse_fields(text.split(":", 1)[1])
            self.bump("load_memory", "user_free_bytes", _num(fields, "memory_user"), "min")
            self.bump("load_memory", "vitagl_all_free_bytes", _num(fields, "vitagl_all_free"), "min")
            return True
        match = RE_BREADCRUMB.match(text)
        if match:
            return self.on_breadcrumb(match.group("subsystem"), match.group("body"), line)
        return False

    # ---- record handlers -------------------------------------------------
    def on_level(self, archive: str, line: int) -> None:
        name = archive.replace("\\", "/").rsplit("/", 1)[-1]
        is_tutorial = name.lower().startswith("m00_tutorial")
        if self.segment not in ("boot", "load") and name != self.level:
            self.transition("post", line, f"new level {name}")
        self.level = name
        if name not in self.levels:
            self.levels.append(name)
        self.tutorial = is_tutorial
        if self.segment in ("boot", "post") or self.segment in SEGMENT_RANK or self.segment == "gameplay":
            if self.segment != "load":
                self.transition("load", line, f"level {name}")
        self.prev_progress = None

    def on_perf(self, fields: dict, line: int) -> None:
        frames = _int(fields, "frames")
        avg_fps = _num(fields, "avg_fps")
        p50 = _num(fields, "frame_us.p50")
        if frames is None or avg_fps is None or p50 is None:
            self.integrity["unparsed_records"] += 1
            return
        self.enter_gameplay(line, "first perf window")
        self.current_frame = frames
        rolling = _int(fields, "rolling_samples") or min(frames, 120)
        total_us = frames * 1_000_000.0 / avg_fps if avg_fps > 0 else None
        previous = self.last_perf
        if previous is not None and frames < previous["frames"]:
            self.integrity["counter_resets"] += 1
            previous = None
        prev_frames = previous["frames"] if previous else 0
        prev_total = previous["total_us"] if previous else 0.0
        delta_frames = frames - prev_frames
        if delta_frames <= 0:
            return
        if delta_frames > rolling:
            self.integrity["perf_window_gaps"] += 1
        delta_time = (total_us - prev_total) if total_us is not None and prev_total is not None else None
        maximum = _num(fields, "frame_us.max")
        prev_max = previous["max"] if previous else None
        high, high_source = None, None
        if maximum is not None and (prev_max is None or maximum > prev_max):
            high, high_source = maximum, "perf-max"
        profile = self.pending_profile
        if profile is not None and profile.get("frames") == 120:
            self.profile_alignment["checked"] += 1
            if previous is None or delta_frames == 120:
                self.profile_alignment["aligned"] += 1
            if high is None:
                high, high_source = float(profile["worst_frame_us"]), "profile-worst"
        self.pending_profile = None
        p95, p99 = _num(fields, "frame_us.p95"), _num(fields, "frame_us.p99")
        bucket = self.seg()
        bucket["windows"].append({
            "line": line, "frames_end": frames, "frames": delta_frames,
            "weight": min(delta_frames, rolling),
            "time_us": delta_time, "p50": p50, "p95": p95, "p99": p99,
            "high": high, "high_source": high_source,
            "anchors": window_anchors(_num(fields, "frame_us.min"), p50, p95, p99,
                                      high if high is not None else (p99 or p95)),
        })
        bucket["frames"] += delta_frames
        if delta_time is not None and delta_time > 0:
            bucket["time_us"] += delta_time
        for key, name in (("slow_over_16_7ms", "over_16_7ms"), ("slow_over_20ms", "over_20ms"),
                          ("slow_over_33ms", "over_33ms"), ("slow_over_50ms", "over_50ms")):
            current = _int(fields, key)
            if current is not None:
                before = previous["slow"].get(key, 0) if previous else 0
                bucket["slow"][name] += max(0, current - before)
        stage_now = {name: _num(fields, f"stage_us.{name}") for name in ("sync", "sim", "render")}
        if all(value is not None for value in stage_now.values()):
            for name, value in stage_now.items():
                before = previous["stage"].get(name, 0.0) * prev_frames if previous else 0.0
                bucket["stage_us_total"][name] += value * frames - before
            bucket["stage_frames"] += delta_frames
            # Each logged average is truncated to whole microseconds.
            bucket["stage_error_us"] = max(bucket["stage_error_us"], frames / delta_frames)
        worst_candidates = [(high, high_source)] if high is not None else []
        worst_candidates.append((p99 or p95, "window-p99 (lower bound)"))
        for value, source in worst_candidates:
            if value is not None and (bucket["worst"] is None or value > bucket["worst"][0]):
                bucket["worst"] = (value, source)
        slow50_delta = 0
        current50 = _int(fields, "slow_over_50ms")
        if current50 is not None:
            slow50_delta = max(0, current50 - (previous["slow"].get("slow_over_50ms", 0) if previous else 0))
        # Individually known frames (slow-frame, profile-worst) in this window
        # are listed on their own; the window row carries only the remainder.
        listed = [h for h in self.hitches if h["source"] != "window" and h.get("frame") is not None
                  and prev_frames < h["frame"] <= frames]
        remaining = slow50_delta - len(listed)
        if remaining > 0:
            high_listed = high is not None and any(int(h["frame_us"]) == int(high) for h in listed)
            exact = high is not None and not high_listed
            self.hitches.append({
                "source": "window", "line": line, "segment": self.segment, "frame": frames,
                "frame_us": high if exact else (p99 or p95), "exact": exact,
                "count_over_threshold": remaining,
                "detail": (f"{remaining} more frame(s) >50 ms in window ending frame {frames}"
                           + (f" ({len(listed)} listed individually)" if listed else "")
                           + ("" if exact else "; value is the window p99")),
            })
        self.last_perf = {"frames": frames, "total_us": total_us, "max": maximum,
                          "slow": {key: fields.get(key, 0) for key in
                                   ("slow_over_16_7ms", "slow_over_20ms", "slow_over_33ms", "slow_over_50ms")},
                          "stage": {name: value for name, value in stage_now.items() if value is not None}}
        self.last_perf_frames = frames
        self.integrity["perf_windows"] += 1

    def on_slow(self, match: re.Match, line: int) -> None:
        frame, total = int(match.group(1)), int(match.group(2))
        self.current_frame = frame
        self.enter_gameplay(line, "slow frame")
        stages = {name: int(value) for name, value in zip(("sync_us", "simulation_us", "render_us"),
                                                           match.groups()[2:5]) if value is not None}
        bucket = self.seg()
        if bucket["worst"] is None or total > bucket["worst"][0]:
            bucket["worst"] = (float(total), "slow-frame")
        if total > self.hitch_us:
            self.hitches.append({"source": "slow-frame", "line": line, "segment": self.segment,
                                 "frame": frame, "frame_us": float(total), "exact": True,
                                 "stages_us": stages, "scopes_us": {}})

    def on_profile(self, body: str, line: int) -> None:
        head, _, scopes_text = body.partition(" top avg_us/calls_per_frame:")
        fields = parse_fields(head)
        frames = _int(fields, "frames")
        if frames is None or frames <= 0:
            self.integrity["unparsed_records"] += 1
            return
        record = {"line": line, "frames": frames, "window": _int(fields, "window"),
                  "avg_frame_us": _int(fields, "avg_frame_us"),
                  "worst_frame_us": _int(fields, "worst_frame_us") or 0,
                  "worst_frame_index": _int(fields, "worst_frame_index"),
                  "est_clock_us": _int(fields, "est_clock_us"), "overflow": _int(fields, "overflow")}
        self.pending_profile = record
        profile = self.seg()["profile"]
        profile["windows"] += 1
        profile["frames"] += frames
        if record["avg_frame_us"] is not None:
            profile["frame_us_total"] += record["avg_frame_us"] * frames
        if record["est_clock_us"] is not None:
            profile["est_clock_us_total"] += record["est_clock_us"] * frames
        profile["overflow_max"] = max(profile["overflow_max"], record["overflow"] or 0)
        for name, avg_us, calls in SCOPE_RE.findall(scopes_text):
            scope = profile["scopes"].setdefault(name, {"us_total": 0.0, "calls_total": 0.0, "windows": 0})
            scope["us_total"] += int(avg_us) * frames
            scope["calls_total"] += float(calls) * frames
            scope["windows"] += 1

    def on_profile_worst(self, match: re.Match, line: int) -> None:
        index, frame_us = int(match.group(2)), int(match.group(3))
        if frame_us <= self.hitch_us:
            return
        scopes = {name: int(value) for name, value in WORST_SCOPE_RE.findall(match.group("scopes"))}
        approx = (self.last_perf_frames + index + 1) if self.last_perf_frames is not None else self.current_frame
        for hitch in self.hitches:
            if hitch["source"] == "slow-frame" and int(hitch["frame_us"]) == frame_us and line - hitch["line"] < 400:
                hitch["scopes_us"] = scopes
                hitch["source"] = "slow-frame+profile"
                return
        self.hitches.append({"source": "profile-worst", "line": line,
                             "segment": self.segment_at_frame(approx, line), "frame": approx,
                             "frame_us": float(frame_us), "exact": True, "frame_is_approximate": True,
                             "window": int(match.group(1)), "scopes_us": scopes})

    def on_progress(self, frame: int, body: str, line: int) -> None:
        self.current_frame = frame
        self.enter_gameplay(line, "first mission progress")
        fields = parse_fields(body)
        active = fields.get("active")
        status = _triplet(fields.get("status_1_6"))
        previous = self.prev_progress
        if isinstance(active, str) and active != "none":
            if previous is None or previous.get("active") != active:
                self.event("conversation", active, line, frame)
                self.advance_tutorial(conversation_segment(active), line, f"conversation {active}")
        if status and previous and previous.get("status") and len(previous["status"]) == len(status):
            for index, (before, after) in enumerate(zip(previous["status"], status)):
                if before == after:
                    continue
                objective = index + 1
                if after == OBJECTIVE_ACCOMPLISHED and before in (OBJECTIVE_PENDING, OBJECTIVE_HIDDEN):
                    self.event("objective", f"objective {objective} accomplished", line, frame)
                    self.advance_tutorial(OBJECTIVE_SEGMENTS.get(objective), line,
                                          f"objective {objective} accomplished")
                elif after == OBJECTIVE_PENDING and before in (OBJECTIVE_HIDDEN, -1):
                    self.event("objective", f"objective {objective} shown", line, frame)
                elif after == OBJECTIVE_FAILED:
                    self.event("objective", f"objective {objective} failed", line, frame)
        self.prev_progress = {"active": active if isinstance(active, str) else
                              (previous or {}).get("active"),
                              "status": status or (previous or {}).get("status")}

    def on_pacing(self, fields: dict) -> None:
        """``A4 campaign pacing`` holds cumulative integer averages since the run began."""
        frames = _int(fields, "frames")
        if frames is None:
            return
        pacing = self.seg()["pacing"]
        previous_frames = self.cumulative.previous.get(("pacing", "frames"))
        fresh = previous_frames is None or frames < previous_frames
        delta_frames = self.cumulative.delta(("pacing", "frames"), frames)
        if delta_frames <= 0:
            return
        # avg x frames is a truncated running total, so it may dip by up to
        # `frames` microseconds between lines: use signed deltas, reset only
        # when the frame count restarts.
        for name in ("time", "input", "path", "control", "network", "combat", "other", "drift"):
            value = _num(fields, "drift_ms" if name == "drift" else f"avg_us.{name}")
            if value is None:
                continue
            total = value if name == "drift" else value * frames
            key = ("pacing-signed", name)
            previous_total = self.cumulative.previous.get(key, 0.0)
            self.cumulative.previous[key] = total
            delta_total = total if fresh else total - previous_total
            if name == "drift":
                pacing["drift_ms"] += delta_total
            else:
                pacing["totals"][name] = pacing["totals"].get(name, 0.0) + delta_total
        pacing["frames"] += delta_frames

    def on_casts(self, fields: dict) -> None:
        window = _int(fields, "window")
        if not window:
            return
        casts = self.seg()["casts"]
        casts["frames"] += window
        totals = casts["totals"]
        for key, value in fields.items():
            if key in ("frames", "window") or not isinstance(value, (int, float)):
                continue
            totals[key] = totals.get(key, 0.0) + float(value) * window

    def on_vis(self, fields: dict) -> None:
        vis = self.seg()["vis"]
        vis["samples"] += 1
        for key in ("static.collected", "dynamic.collected", "static.vis_saved", "static.in_frustum",
                    "census_us"):
            value = _num(fields, key)
            if value is not None:
                vis["totals"][key] = vis["totals"].get(key, 0.0) + value

    def on_audio(self, text: str, fields: dict, line: int) -> None:
        live = _num(fields, "pcm_live.high")
        self.bump("audio", "pcm_live_high_bytes", live, "max")
        self.bump("audio", "pcm_cache_bytes", _num(fields, "pcm.bytes"), "max")
        self.bump("audio", "allocated_samples", _num(fields, "allocated"), "max")
        # attempts/successes/failures triplets; failures are cumulative.
        for key, label in (("sample_file", "sample_file_failures"), ("sample_3d", "sample_3d_failures"),
                           ("stream", "stream_open_failures")):
            triplet = _triplet(fields.get(key))
            if triplet and len(triplet) >= 3:
                self.bump("audio", label, self.cumulative.delta(("audio", key), triplet[2]), "sum")
        # output_written/fail[/starved] expands to output_written, fail, starved.
        for key, label in (("fail", "output_write_failures"), ("starved", "output_starved_buffers")):
            value = _num(fields, key)
            if value is not None:
                self.bump("audio", label, self.cumulative.delta(("audio", key), value), "sum")
        error = RE_LAST_ERROR.search(text)
        if error:
            message = error.group(1).strip()
            if message not in ("none", "no error", "") and message != self.audio_last_error:
                self.seg()["audio_errors"].append({"line": line, "frame": _int(fields, "frame"),
                                                   "error": message[:120]})
                self.event("audio-error", message[:60], line)
            self.audio_last_error = message

    def on_breadcrumb(self, subsystem: str, body: str, line: int) -> bool:
        label, payload = "", body
        labelled = BREADCRUMB_LABEL_RE.match(body)
        if labelled:
            label, payload = labelled.group(1), labelled.group(2)
        elif body.startswith("thrash "):
            label, payload = "thrash", body[len("thrash "):]
        fields = parse_fields(payload)
        if fields.get("version") == 1 and "frame" not in fields:
            # Switch announcements (RVVA1/RVGS1/RVSM1/RVSD1/RVPW1/RVVS1/RVIR1 ...).
            keys = [key for key in CONFIG_KEYS if key in fields]
            if keys:
                self.config[f"{subsystem} {label}".strip()] = " ".join(f"{key}={fields[key]}" for key in keys)
        frame = _num(fields, "frame")
        if subsystem == "vitagl-pools":
            for name in ("immediate_peak", "circular_peak", "immediate_capacity", "circular_slice"):
                self.bump("vitagl_pools", name, _num(fields, name), "max")
            for name in ("immediate_overruns", "circular_overruns"):
                self.bump("vitagl_pools", name, _num(fields, name), "sum")
            return True
        if subsystem == "static-mesh-cache":
            if label == "thrash":
                self.bump("static_mesh_cache", "max_frame_builds", _num(fields, "max_frame_builds"), "max")
                self.bump("static_mesh_cache", "max_frame_upload_bytes",
                          _num(fields, "max_frame_upload_bytes"), "max")
                self.bump("static_mesh_cache", "upload_bytes",
                          self.cumulative.delta(("smc", "upload_bytes"), _num(fields, "upload_bytes")), "sum")
                return True
            if frame is None:
                return True
            self.renderer_frames(subsystem, frame)
            self.bump("static_mesh_cache", "bytes", _num(fields, "bytes"), "max")
            self.bump("static_mesh_cache", "entries", _num(fields, "entries"), "max")
            for name in ("hits", "builds", "rebuilds", "evictions", "allocation_failures", "volatile"):
                self.bump("static_mesh_cache", name,
                          self.cumulative.delta(("smc", name), _num(fields, name)), "sum")
            return True
        if subsystem == "skin-deform-cache":
            if frame is None:
                return True
            self.renderer_frames(subsystem, frame)
            self.bump("skin_cache", "bytes", _num(fields, "bytes"), "max")
            for name in ("hits", "misses", "overflows", "allocation_failures"):
                self.bump("skin_cache", name, self.cumulative.delta(("skin", name), _num(fields, name)), "sum")
            return True
        if subsystem == "vertex-array":
            if frame is None:
                return True
            self.renderer_frames(subsystem, frame)
            self.bump("vertex_array", "scratch_bytes", _num(fields, "scratch_bytes"), "max")
            self.bump("vertex_array", "batches",
                      self.cumulative.delta(("va", "batches"), _num(fields, "batches")), "sum")
            return True
        if subsystem == "gl-state-shadow":
            if frame is None:
                return True
            for name in ("raster_calls", "raster_skips", "transform_loads", "transform_skips"):
                self.bump("gl_state_shadow", name, _num(fields, name), "sum")
            return True
        if subsystem == "texture-state":
            if frame is None:
                return True
            for name in ("sampler_updates", "sampler_skips", "texenv_writes", "texenv_skips", "binds",
                         "bind_skips"):
                self.bump("texture_state", name,
                          self.cumulative.delta(("tex", name), _num(fields, name)), "sum")
            return True
        if subsystem == "ffp-program-cache":
            if label == "window":
                # compiles/disk_loads are vertex/fragment pairs for this window.
                pair = _triplet(fields.get("compiles"))
                if pair:
                    self.bump("ffp_programs", "compiles", float(sum(pair)), "sum")
                disk = _triplet(fields.get("disk_loads"))
                if disk:
                    self.bump("ffp_programs", "disk_loads", float(sum(disk)), "sum")
                self.bump("ffp_programs", "compile_ms", _num(fields, "compile_ms"), "sum")
                self.bump("ffp_programs", "max_compile_ms", _num(fields, "max_compile_ms"), "max")
                self.bump("ffp_programs", "rejects", _num(fields, "rejects"), "sum")
            elif label == "prewarm":
                self.config["ffp-program-cache prewarm keys->loaded"] = (
                    f"{fields.get('keys')}->{fields.get('loaded')} record={fields.get('record')}")
            return True
        if subsystem == "frame-vblank":
            self.bump("vblank", "missed", _num(fields, "missed_vblanks"), "sum")
            self.bump("vblank", "windows", 1.0, "sum")
            self.bump("vblank", "max_delta", _num(fields, "max_delta"), "max")
            return True
        if subsystem == "internal-resolution":
            if "to" in fields:
                self.config.setdefault("RVIR1 internal-resolution first", fields.get("to"))
                self.config["RVIR1 internal-resolution last"] = fields.get("to")
            return True
        if subsystem == "render-work-cache":
            if frame is not None:
                self.renderer_frames(subsystem, frame)
            return True
        return True  # other renderer breadcrumbs are known-format but not aggregated

    def renderer_frames(self, subsystem: str, frame: float) -> None:
        delta = self.cumulative.delta(("frames", subsystem), frame)
        store = self.seg()["renderer_frames"]
        store[subsystem] = store.get(subsystem, 0.0) + delta

    # ---- results ---------------------------------------------------------
    def nearest_breadcrumb(self, hitch: dict) -> dict | None:
        frame = hitch.get("frame")
        best = None
        for event in self.events:
            if event["line"] > hitch["line"]:
                break
            if event["kind"] == "audio-error":
                continue
            if hitch["source"] != "window" and frame is not None and event["frame"] is not None \
                    and event["frame"] > frame:
                continue
            best = event
        if best is None:
            return None
        result = {"kind": best["kind"], "label": best["label"], "line": best["line"], "frame": best["frame"]}
        if frame is not None and best["frame"] is not None:
            result["frames_before_hitch"] = frame - best["frame"]
        return result


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------
def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def summarize_segment(name: str, bucket: dict, top_scopes: int) -> dict:
    windows = bucket["windows"]
    weighted = [(w["weight"], w["anchors"]) for w in windows]
    frames, time_us = bucket["frames"], bucket["time_us"]
    per_window_ms = [w["time_us"] / w["frames"] / 1000.0 for w in windows
                     if w["time_us"] and w["time_us"] > 0 and w["frames"] > 0]
    stage_frames = bucket["stage_frames"]
    profile = bucket["profile"]
    scopes = []
    if profile["frames"]:
        for scope_name, scope in profile["scopes"].items():
            avg = scope["us_total"] / profile["frames"]
            scopes.append({"scope": scope_name, "avg_us_per_frame": round(avg, 1),
                           "calls_per_frame": round(scope["calls_total"] / profile["frames"], 2),
                           "windows_listed": scope["windows"]})
        scopes.sort(key=lambda item: (-item["avg_us_per_frame"], item["scope"]))
    pacing = bucket["pacing"]
    casts = bucket["casts"]
    vis = bucket["vis"]
    summary = {
        "segment": name, "title": SEGMENT_TITLES.get(name, name), "visits": bucket["visits"],
        "perf_windows": len(windows), "frames": frames,
        "time_s": _round(time_us / 1e6, 3) if time_us else None,
        "fps": _round(frames / (time_us / 1e6), 2) if time_us else None,
        "mean_frame_ms": _round(time_us / frames / 1000.0, 2) if time_us and frames else None,
        "p50_ms": _round((mixture_quantile(weighted, 0.50) or 0) / 1000.0) if weighted else None,
        "p95_ms": _round((mixture_quantile(weighted, 0.95) or 0) / 1000.0) if weighted else None,
        "p99_ms": _round((mixture_quantile(weighted, 0.99) or 0) / 1000.0) if weighted else None,
        "percentiles_exact": len(windows) == 1,
        "worst_ms": _round(bucket["worst"][0] / 1000.0) if bucket["worst"] else None,
        "worst_source": bucket["worst"][1] if bucket["worst"] else None,
        "slow_frames": dict(bucket["slow"]),
        "over_50ms_per_1000_frames": _round(bucket["slow"]["over_50ms"] * 1000.0 / frames) if frames else None,
        "stage_avg_ms": {key: _round(value / stage_frames / 1000.0, 3) for key, value in
                         bucket["stage_us_total"].items()} if stage_frames else {},
        "stage_avg_error_us": _round(bucket["stage_error_us"], 1),
        "window_mean_ms": per_window_ms,
        "profile": {
            "windows": profile["windows"], "frames": profile["frames"],
            "avg_frame_ms": _round(profile["frame_us_total"] / profile["frames"] / 1000.0)
            if profile["frames"] else None,
            "est_profiler_clock_us_per_frame": _round(profile["est_clock_us_total"] / profile["frames"], 1)
            if profile["frames"] else None,
            "overflow_max": profile["overflow_max"],
            "top_scopes": scopes[:top_scopes], "scopes_seen": len(scopes),
        },
        "pacing_avg_us": {key: _round(value / pacing["frames"], 1) for key, value in pacing["totals"].items()}
        if pacing["frames"] else {},
        "pacing_drift_ms": _round(pacing["drift_ms"], 1) if pacing["frames"] else None,
        "combat_casts": {key: _round(value / casts["frames"], 2) for key, value in casts["totals"].items()}
        if casts["frames"] else {},
        "vis_census_avg": {key: _round(value / vis["samples"], 1) for key, value in vis["totals"].items()}
        if vis["samples"] else {},
        "maxima": {key: value for key, value in sorted(bucket["maxima"].items())},
        "minima": {key: value for key, value in sorted(bucket["minima"].items())},
        "counters": {key: _round(value, 3) for key, value in sorted(bucket["counters"].items())},
        "renderer_frames": {key: int(value) for key, value in sorted(bucket["renderer_frames"].items())},
        "audio_errors": bucket["audio_errors"],
    }
    return summary


def read_log(path: Path) -> tuple[list[str], dict]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    meta = {"path": str(path), "name": path.name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "lines": len(lines),
            "ends_with_newline": data.endswith(b"\n"), "nul_bytes": data.count(b"\x00")}
    return lines, meta


def split_sessions(lines: list[str]) -> list[tuple[int, list[str]]]:
    starts = [index for index, line in enumerate(lines) if RE_LIFECYCLE_START.match(line.replace("\x00", ""))]
    if not starts:
        return [(1, lines)]
    sessions = []
    if starts[0] > 0 and any(line.strip() for line in lines[:starts[0]]):
        sessions.append((1, lines[:starts[0]]))
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        sessions.append((start + 1, lines[start:end]))
    return sessions


def choose_session(sessions: list[tuple[int, list[str]]], requested: str) -> int:
    if requested != "auto":
        index = int(requested)
        if index < 0:
            index += len(sessions)
        if not 0 <= index < len(sessions):
            raise ValueError(f"session {requested} out of range (found {len(sessions)})")
        return index
    scores = [sum("active=MTU_" in line for line in body) for _, body in sessions]
    if max(scores) > 0:
        best = max(scores)
        return max(index for index, score in enumerate(scores) if score == best)
    perf = [index for index, (_, body) in enumerate(sessions) if any(line.startswith("A3.5 perf:") for line in body)]
    return perf[-1] if perf else len(sessions) - 1


def analyze_log(path: Path, *, session: str = "auto", hitch_ms: float = 50.0,
                top_scopes: int = 8, top_hitches: int = 30, label: str | None = None) -> dict:
    lines, meta = read_log(path)
    sessions = split_sessions(lines)
    chosen = choose_session(sessions, session)
    first_line, body = sessions[chosen]
    analyzer = SessionAnalyzer(body, first_line, hitch_ms)
    analyzer.run()
    segments = []
    for name in SEGMENT_ORDER:
        if name in analyzer.segments:
            segments.append(summarize_segment(name, analyzer.segments[name], top_scopes))
    hitches = []
    for hitch in analyzer.hitches:
        item = dict(hitch)
        item["frame_ms"] = _round(hitch["frame_us"] / 1000.0) if hitch["frame_us"] is not None else None
        item["breadcrumb"] = analyzer.nearest_breadcrumb(hitch)
        hitches.append(item)
    individual = [h for h in hitches if h["source"] != "window"]
    hitches.sort(key=lambda h: (-(h["frame_us"] or 0), h["line"]))
    integrity = dict(analyzer.integrity)
    integrity["unknown_prefixes"] = dict(sorted(integrity["unknown_prefixes"].items(),
                                                key=lambda item: (-item[1], item[0]))[:12])
    integrity["sessions_found"] = len(sessions)
    integrity["session_analyzed"] = chosen
    integrity["session_first_line"] = first_line
    integrity["final_line_complete"] = meta["ends_with_newline"]
    integrity["profile_windows_aligned"] = analyzer.profile_alignment
    entered = {item["segment"] for item in analyzer.transitions}
    tutorial_seen = any(name.lower().startswith("m00_tutorial") for name in analyzer.levels)
    integrity["tutorial_segments_missing"] = [name for name in TUTORIAL_SEGMENTS if name not in entered] \
        if tutorial_seen or not analyzer.levels else []
    integrity["notes"] = integrity_notes(integrity, meta, analyzer)
    return {
        "label": label or path.stem, "input": meta, "candidate": analyzer.candidate,
        "level": next((n for n in analyzer.levels if n.lower().startswith("m00_tutorial")), analyzer.level),
        "levels": analyzer.levels,
        "tutorial": any(n.lower().startswith("m00_tutorial") for n in analyzer.levels)
        if analyzer.levels else None,
        "configuration": analyzer.config,
        "segments": segments, "transitions": analyzer.transitions,
        "hitch_threshold_ms": hitch_ms, "hitch_count_individual": len(individual),
        "hitches": hitches[:max(top_hitches, 0) or len(hitches)][:500],
        "hitches_total_listed": len(hitches),
        "load_milestones": analyzer.load_milestones,
        "breadcrumbs": [e for e in analyzer.events if e["kind"] in ("conversation", "objective")][:400],
        "run_summaries": analyzer.run_summaries, "session_residuals": analyzer.session_residuals,
        "integrity": integrity,
    }


def integrity_notes(integrity: dict, meta: dict, analyzer: SessionAnalyzer) -> list[str]:
    notes = []
    if integrity["truncated_at_line"] is not None:
        notes.append(f"session log cap reached at line {integrity['truncated_at_line']}: only priority "
                     "lines follow, so later segments have no perf data")
    if integrity["dropped_lines"]:
        notes.append(f"{integrity['dropped_lines']} line(s) dropped by the async log writer")
    if integrity["suppressed_lines"]:
        notes.append(f"{integrity['suppressed_lines']} line(s) suppressed past the session cap")
    if not meta["ends_with_newline"]:
        notes.append("final line is incomplete (log cut mid-write)")
    if meta["nul_bytes"]:
        notes.append(f"{meta['nul_bytes']} NUL byte(s) removed (unsynced tail)")
    if integrity["perf_window_gaps"]:
        notes.append(f"{integrity['perf_window_gaps']} perf window(s) cover more frames than their "
                     "rolling samples (missing checkpoint lines)")
    if integrity["counter_resets"]:
        notes.append(f"{integrity['counter_resets']} cumulative counter reset(s) (new run or level)")
    if integrity["sessions_found"] > 1:
        notes.append(f"{integrity['sessions_found']} sessions in file; analyzed session "
                     f"{integrity['session_analyzed']} (from line {integrity['session_first_line']})")
    if integrity["tutorial_segments_missing"]:
        notes.append("tutorial segment(s) never entered: " + ", ".join(integrity["tutorial_segments_missing"]))
    if not integrity["perf_windows"]:
        notes.append("no 'A3.5 perf' windows found: frame-time statistics unavailable")
    alignment = integrity["profile_windows_aligned"]
    if alignment["checked"] and alignment["aligned"] < alignment["checked"]:
        notes.append(f"frame-profile windows aligned with perf windows {alignment['aligned']}/"
                     f"{alignment['checked']}; profile-worst frame numbers are approximate")
    tutorial_levels = [name for name in analyzer.levels if name.lower().startswith("m00_tutorial")]
    if analyzer.levels and not tutorial_levels:
        notes.append(f"level {analyzer.level} is not the tutorial; gameplay is one segment")
    elif len(analyzer.levels) > 1:
        notes.append("levels in session: " + ", ".join(analyzer.levels) +
                     "; non-tutorial levels are aggregated as 'gameplay'")
    if analyzer.segment in SEGMENT_RANK and analyzer.segment != "end":
        notes.append(f"log ends inside segment '{analyzer.segment}' (run incomplete or log pulled mid-run)")
    return notes


# --------------------------------------------------------------------------
# A/B comparison
# --------------------------------------------------------------------------
def _delta(a: float | None, b: float | None) -> dict:
    if a is None or b is None:
        return {"a": a, "b": b, "delta": None, "percent": None}
    delta = b - a
    return {"a": a, "b": b, "delta": _round(delta, 3), "percent": _round(delta / a * 100.0, 1) if a else None}


def noise_verdict(a: dict, b: dict) -> dict:
    """Two-sided check of the mean frame time against window-to-window spread.

    Treats each 120-frame window mean as a sample. Adjacent windows are
    correlated and each arm is one run, so this under-states noise; it is a
    screen, not a significance test.
    """
    xa, xb = a.get("window_mean_ms") or [], b.get("window_mean_ms") or []
    result: dict[str, Any] = {"windows_a": len(xa), "windows_b": len(xb)}
    if len(xa) < 2 or len(xb) < 2 or a.get("mean_frame_ms") is None or b.get("mean_frame_ms") is None:
        result["verdict"] = "insufficient windows (need >=2 per arm)"
        return result
    se = math.sqrt(statistics.variance(xa) / len(xa) + statistics.variance(xb) / len(xb))
    delta = b["mean_frame_ms"] - a["mean_frame_ms"]
    result["mean_delta_ms"] = _round(delta, 3)
    result["two_se_ms"] = _round(2 * se, 3)
    if se == 0:
        result["verdict"] = "no window spread; repeat runs"
    elif abs(delta) > 2 * se:
        result["verdict"] = "B faster" if delta < 0 else "B slower"
    else:
        result["verdict"] = "within noise"
    frames_a, frames_b = a.get("frames") or 0, b.get("frames") or 0
    if frames_a and frames_b and not 0.5 <= frames_b / frames_a <= 2.0:
        result["route_note"] = "segment frame counts differ >2x; routes may not be comparable"
    return result


def compare(report_a: dict, report_b: dict) -> dict:
    by_a = {item["segment"]: item for item in report_a["segments"]}
    by_b = {item["segment"]: item for item in report_b["segments"]}
    rows = []
    for name in SEGMENT_ORDER:
        if name not in by_a and name not in by_b:
            continue
        a, b = by_a.get(name, {}), by_b.get(name, {})
        if not (a.get("frames") or b.get("frames")):
            continue
        row = {"segment": name, "title": SEGMENT_TITLES.get(name, name)}
        for key in ("fps", "mean_frame_ms", "p50_ms", "p95_ms", "p99_ms", "worst_ms",
                    "over_50ms_per_1000_frames", "frames"):
            row[key] = _delta(a.get(key), b.get(key))
        for stage in ("sim", "render"):
            row[f"{stage}_ms"] = _delta((a.get("stage_avg_ms") or {}).get(stage),
                                        (b.get("stage_avg_ms") or {}).get(stage))
        row["noise"] = noise_verdict(a, b) if a and b else {"verdict": "segment missing in one log"}
        rows.append(row)
    config_keys = sorted(set(report_a["configuration"]) | set(report_b["configuration"]))
    config = [{"switch": key, "a": report_a["configuration"].get(key), "b": report_b["configuration"].get(key)}
              for key in config_keys if not isinstance(report_a["configuration"].get(key), dict)
              and not isinstance(report_b["configuration"].get(key), dict)]
    return {"rows": rows, "configuration_differences": [item for item in config if item["a"] != item["b"]],
            "noise_method": "mean frame time delta vs 2x standard error of per-window means; "
                            "windows are autocorrelated and each arm is one run, so treat as a screen; "
                            "repeat each arm >=3 times before claiming a gain"}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _mb(value: Any) -> str:
    return "-" if value is None else f"{value / 1048576.0:.1f}"


def _kb(value: Any) -> str:
    return "-" if value is None else f"{value / 1024.0:.0f}"


def _pct(skips: float | None, calls: float | None) -> str:
    if not skips or not calls:
        return "-"
    return f"{skips * 100.0 / (skips + calls):.0f}%"


def _table_row(out: list[str], segment: str, cells: list[str]) -> None:
    """Append a segment row unless every cell is empty."""
    if all(cell in ("-", "-/-", "0") for cell in cells):
        return
    out.append(f"| {segment} | " + " | ".join(_cell(cell) for cell in cells) + " |")


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|")


def render_markdown(reports: list[dict], comparison: dict | None) -> str:
    out: list[str] = ["# Tutorial performance report", ""]
    out.append(f"Tool `tools/tutorial_perf_report.py` {TOOL_VERSION}, schema {SCHEMA_VERSION}. "
               "Derived from runtime log fields only; percentiles over several 120-frame "
               "windows are estimates (see Method).")
    out += ["", "| Arm | Log | SHA-256 (12) | Candidate | Level | Lines | Perf windows |",
            "| --- | --- | --- | --- | --- | ---: | ---: |"]
    for arm, report in zip("AB", reports):
        meta = report["input"]
        out.append(f"| {arm} ({report['label']}) | `{meta['name']}` | `{meta['sha256'][:12]}` | "
                   f"{report['candidate'] or '-'} | {report['level'] or '-'} | {meta['lines']} | "
                   f"{report['integrity']['perf_windows']} |")
    for arm, report in zip("AB", reports):
        notes = report["integrity"]["notes"]
        out += ["", f"## Integrity ({arm})", ""]
        out += [f"- {note}" for note in notes] if notes else ["- no integrity issues detected"]
        unknown = report["integrity"]["unknown_lines"]
        if unknown:
            top = ", ".join(f"`{k}` {v}" for k, v in list(report["integrity"]["unknown_prefixes"].items())[:5])
            out.append(f"- {unknown} line(s) of formats this tool does not aggregate were skipped (top: {top})")
    if comparison:
        out += ["", "## A/B delta (B minus A)", "",
                "| Segment | FPS A→B | Δ% | mean ms Δ | p50 Δ | p95 Δ | p99 Δ | worst Δ | >50ms/1k Δ | "
                "sim ms Δ | render ms Δ | Noise |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        for row in comparison["rows"]:
            fps = row["fps"]
            noise = row["noise"]
            verdict = noise.get("verdict", "-")
            if "two_se_ms" in noise:
                verdict += f" (±{noise['two_se_ms']:.2f} ms)"
            if noise.get("route_note"):
                verdict += "; " + noise["route_note"]
            out.append(
                f"| {row['segment']} | {_fmt(fps['a'])}→{_fmt(fps['b'])} | {_fmt(fps['percent'])} | "
                f"{_fmt(row['mean_frame_ms']['delta'], 2)} | {_fmt(row['p50_ms']['delta'], 2)} | "
                f"{_fmt(row['p95_ms']['delta'], 2)} | {_fmt(row['p99_ms']['delta'], 2)} | "
                f"{_fmt(row['worst_ms']['delta'], 1)} | {_fmt(row['over_50ms_per_1000_frames']['delta'], 1)} | "
                f"{_fmt(row['sim_ms']['delta'], 2)} | {_fmt(row['render_ms']['delta'], 2)} | {verdict} |")
        out += ["", f"Noise: {comparison['noise_method']}."]
        diffs = comparison["configuration_differences"]
        out += ["", "Switch differences: " + (", ".join(f"`{d['switch']}` {d['a']}→{d['b']}" for d in diffs)
                                            if diffs else "none detected (both arms log identical switches)")]
    for arm, report in zip("AB", reports):
        out += ["", f"## Segments ({arm}: {report['label']})", "",
                "| Segment | Frames | Time s | FPS | mean ms | p50 | p95 | p99 | worst | >33ms | >50ms | "
                "sim ms | render ms | windows |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for item in report["segments"]:
            stage = item["stage_avg_ms"]
            worst = _fmt(item["worst_ms"])
            if item["worst_source"] and "lower bound" in item["worst_source"]:
                worst = f"≥{worst}"
            out.append(f"| {item['segment']} | {item['frames']} | {_fmt(item['time_s'])} | {_fmt(item['fps'])} | "
                       f"{_fmt(item['mean_frame_ms'])} | {_fmt(item['p50_ms'])} | {_fmt(item['p95_ms'])} | "
                       f"{_fmt(item['p99_ms'])} | {worst} | {item['slow_frames']['over_33ms']} | "
                       f"{item['slow_frames']['over_50ms']} | {_fmt(stage.get('sim'))} | "
                       f"{_fmt(stage.get('render'))} | {item['perf_windows']} |")
        transitions = report["transitions"]
        if transitions:
            out += ["", "Segment starts: " + "; ".join(
                f"{t['segment']}@frame {t['frame'] if t['frame'] is not None else '?'} ({t['trigger']})"
                for t in transitions)]
        out += ["", f"### Top profiler scopes ({arm})", "",
                "Inclusive per-frame averages from `A3.6 frame-profile` windows (nested scopes overlap; "
                "a scope outside a window's top 16 counts as 0 for that window).", ""]
        any_profile = False
        for item in report["segments"]:
            profile = item["profile"]
            if not profile["top_scopes"]:
                continue
            any_profile = True
            scopes = ", ".join(f"{s['scope']} {s['avg_us_per_frame'] / 1000.0:.2f} ms ({s['calls_per_frame']}/f)"
                               for s in profile["top_scopes"])
            out.append(f"- **{item['segment']}** (profile frame {_fmt(profile['avg_frame_ms'])} ms, "
                       f"clock cost ~{_fmt(profile['est_profiler_clock_us_per_frame'])} µs/f): {scopes}")
        if not any_profile:
            out.append("- no `A3.6 frame-profile` windows (profiler off or not in this build)")
        out += ["", f"### Memory and pools high-water ({arm})", "",
                "| Segment | heap in_use MB | heap free min MB | static mesh MB | skin cache KB | PCM live high MB | "
                "vitaGL immediate peak/cap KB | circular peak/slice KB | pool overruns | audio failures | audio errors |",
                "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |"]
        table_start = len(out)
        for item in report["segments"]:
            mx, mn, ct = item["maxima"], item["minima"], item["counters"]
            overruns = (ct.get("vitagl_pools.immediate_overruns") or 0) + (ct.get("vitagl_pools.circular_overruns") or 0)
            failures = sum(ct.get(f"audio.{k}") or 0 for k in ("sample_file_failures", "sample_3d_failures",
                                                              "stream_open_failures", "output_write_failures"))
            cells = [_mb(mx.get("heap.in_use_bytes")), _mb(mn.get("heap.free_bytes")),
                     _mb(mx.get("static_mesh_cache.bytes")), _kb(mx.get("skin_cache.bytes")),
                     _mb(mx.get("audio.pcm_live_high_bytes")),
                     f"{_kb(mx.get('vitagl_pools.immediate_peak'))}/{_kb(mx.get('vitagl_pools.immediate_capacity'))}",
                     f"{_kb(mx.get('vitagl_pools.circular_peak'))}/{_kb(mx.get('vitagl_pools.circular_slice'))}",
                     str(int(overruns)), str(int(failures)),
                     "; ".join(e["error"] for e in item["audio_errors"][:3]) or "-"]
            _table_row(out, item["segment"], cells)
        if len(out) == table_start:
            out.append("| - | no heap/pool/cache/audio telemetry lines in this log (dev240 adds most) |"
                       + " |" * 9)
        out += ["", f"### Renderer and simulation counters ({arm})", "",
                "| Segment | static-mesh hits/f | builds+rebuilds | VA batches/f | GL shadow skip | sampler skip | "
                "FFP compiles (ms) | missed vblanks/1k f | combat µs/f | awake soldiers | casts/f | pacing drift ms |",
                "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
        table_start = len(out)
        for item in report["segments"]:
            ct, rf, casts = item["counters"], item["renderer_frames"], item["combat_casts"]
            smc_frames = rf.get("static-mesh-cache") or 0
            va_frames = rf.get("vertex-array") or 0
            hits = ct.get("static_mesh_cache.hits")
            builds = (ct.get("static_mesh_cache.builds") or 0) + (ct.get("static_mesh_cache.rebuilds") or 0)
            batches = ct.get("vertex_array.batches")
            vbl_windows = ct.get("vblank.windows") or 0
            casts_total = sum(v for k, v in casts.items() if k.startswith("per_frame.")) if casts else None
            compiles = ct.get("ffp_programs.compiles")
            cells = [_fmt(hits / smc_frames if hits is not None and smc_frames else None),
                     str(int(builds)) if builds else "-",
                     _fmt(batches / va_frames if batches is not None and va_frames else None),
                     _pct(ct.get("gl_state_shadow.raster_skips"), ct.get("gl_state_shadow.raster_calls")),
                     _pct(ct.get("texture_state.sampler_skips"), ct.get("texture_state.sampler_updates")),
                     f"{int(compiles)} ({_fmt(ct.get('ffp_programs.compile_ms'))})" if compiles else "-",
                     _fmt(ct.get("vblank.missed", 0) * 1000.0 / (vbl_windows * 120.0) if vbl_windows else None),
                     _fmt(casts.get("combat_avg_us")), _fmt(casts.get("soldiers_awake")), _fmt(casts_total),
                     _fmt(item["pacing_drift_ms"])]
            _table_row(out, item["segment"], cells)
        if len(out) == table_start:
            out.append("| - | no renderer/simulation counter lines in this log |" + " |" * 10)
        hitches = report["hitches"]
        out += ["", f"### Hitches over {report['hitch_threshold_ms']:.0f} ms ({arm})", "",
                f"{report['hitch_count_individual']} individual frame(s) known "
                "(`A4 slow frame` >=500 ms, `A3.6 frame-profile-worst` per window); "
                "`window` rows carry frames counted by the window's >50 ms counter that are not listed individually "
                "(value is the window max when that frame is otherwise unlisted, else `~` the window p99).", "",
                "| ms | Frame | Segment | Source | Nearest preceding breadcrumb | Detail |",
                "| ---: | ---: | --- | --- | --- | --- |"]
        for hitch in hitches:
            crumb = hitch.get("breadcrumb")
            crumb_text = "-"
            if crumb:
                crumb_text = f"{crumb['label']} (frame {crumb['frame'] if crumb['frame'] is not None else '?'}"
                if crumb.get("frames_before_hitch") is not None:
                    crumb_text += f", {crumb['frames_before_hitch']} f before"
                crumb_text += ")"
            if hitch["source"] == "window":
                detail = hitch["detail"]
            else:
                parts = []
                if hitch.get("stages_us"):
                    parts.append("sync/sim/render ms " + "/".join(
                        f"{hitch['stages_us'].get(k, 0) / 1000.0:.1f}" for k in ("sync_us", "simulation_us", "render_us")))
                if hitch.get("scopes_us"):
                    top = sorted(hitch["scopes_us"].items(), key=lambda kv: -kv[1])[:4]
                    parts.append(", ".join(f"{name} {value / 1000.0:.1f}" for name, value in top))
                detail = "; ".join(parts) or "-"
            frame = hitch.get("frame")
            frame_text = "-" if frame is None else (f"~{frame}" if hitch.get("frame_is_approximate") else str(frame))
            ms = _fmt(hitch["frame_ms"])
            if hitch["source"] == "window" and not hitch.get("exact"):
                ms = f"~{ms}"
            out.append(f"| {ms} | {frame_text} | {hitch['segment']} | {hitch['source']} | {_cell(crumb_text)} | "
                       f"{_cell(detail)} |")
        if not hitches:
            out.append("| - | - | - | - | - | none |")
        out += ["", f"### Level-load milestones ({arm})", ""]
        milestones = report["load_milestones"]
        if milestones:
            for item in milestones[:40]:
                elapsed = f" — {item['elapsed_ms']:.0f} ms" if item["elapsed_ms"] is not None else ""
                out.append(f"- line {item['line']} [{item['segment']}] {item['label']}{elapsed}")
        else:
            out.append("- none found")
        config = {k: v for k, v in report["configuration"].items() if not isinstance(v, dict)}
        out += ["", f"### Logged switches ({arm})", ""]
        out.append(", ".join(f"`{k}`={v}" for k, v in sorted(config.items())) if config else "none logged")
    out += ["", "## Method", "",
            "- Segments follow the original Mission00 breadcrumbs in `A3.5 mission progress` lines: "
            "`active=<conversation>` changes and objective status changes (objective 1 at Sydney, 2 Gunner, "
            "3 Hotwire, 4 Mobius, 5 Petrova, 6 officers down). Segments only move forward along the route; "
            "a 120-frame window is attributed to the segment active when it was logged (its end).",
            "- FPS = frames / time per window, with time recovered from the cumulative `avg_fps` and frame count "
            "(precision about 2e-5 relative per line).",
            "- p50/p95/p99: frame-weighted mixture of per-window piecewise-linear CDFs through the logged "
            "window p50/p95/p99/max; exact for a single window, an estimate for several.",
            "- Stage averages come from cumulative integer averages; error per segment <= `stage_avg_error_us`.",
            "- Hardware gains are not claimed by this tool; compare repeated runs of the same route."]
    return "\n".join(out) + "\n"


def build_report(paths: list[Path], *, labels: list[str] | None = None,
                 sessions: list[str] | None = None, hitch_ms: float = 50.0, top_scopes: int = 8,
                 top_hitches: int = 30) -> dict:
    """``sessions`` holds one selector per log (the last one repeats)."""
    reports = []
    for index, path in enumerate(paths):
        label = labels[index] if labels and index < len(labels) else ("A" if index == 0 else "B")
        session = (sessions[min(index, len(sessions) - 1)] if sessions else "auto")
        reports.append(analyze_log(path, session=session, hitch_ms=hitch_ms, top_scopes=top_scopes,
                                   top_hitches=top_hitches, label=label))
    comparison = compare(reports[0], reports[1]) if len(reports) == 2 else None
    return {"schema_version": SCHEMA_VERSION, "tool_version": TOOL_VERSION, "reports": reports,
            "comparison": comparison}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("logs", nargs="+", type=Path, help="runtime log (A) and optional second log (B)")
    parser.add_argument("--label", action="append", dest="labels", help="label per log (repeat)")
    parser.add_argument("--out-md", type=Path, help="write Markdown here (default: stdout)")
    parser.add_argument("--out-json", type=Path, help="write JSON here")
    parser.add_argument("--session", action="append", dest="sessions",
                        help="session per log when a log holds several launches (the runtime log is "
                             "opened for append): index, negative from the end, or auto (default); "
                             "repeat for B, e.g. one log twice with --session 0 --session 1")
    parser.add_argument("--hitch-ms", type=float, default=50.0, help="hitch threshold (default 50)")
    parser.add_argument("--top-scopes", type=int, default=8, help="profiler scopes per segment")
    parser.add_argument("--top-hitches", type=int, default=30, help="hitch rows to list")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if len(args.logs) > 2:
        parser.error("give one log, or two for A/B")
    for path in args.logs:
        if not path.is_file():
            print(f"error: {path} is not a readable file", file=sys.stderr)
            return 2
    try:
        report = build_report(args.logs, labels=args.labels, sessions=args.sessions, hitch_ms=args.hitch_ms,
                              top_scopes=args.top_scopes, top_hitches=args.top_hitches)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    markdown = render_markdown(report["reports"], report["comparison"])
    if args.out_json:
        args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.write_text(markdown, encoding="utf-8")
    if not args.out_md:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
