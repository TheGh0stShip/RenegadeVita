#!/usr/bin/env python3
"""Summarize compile time from a Ninja ``.ninja_log`` (read-only).

Reports, for one build session (default: the most recent one in the log):

* edge count, serial time (sum of edge durations), wall time and observed
  maximum concurrency;
* the slowest edges and per-directory totals;
* the observed critical chain: walking back from the last edge to finish, the
  edge whose completion each step most plausibly waited for (a heuristic that
  needs no dependency graph);
* with ``--build-ninja``, the dependency critical path: the longest chain of
  edges through the real build graph weighted by the logged durations;
* an LPT (longest-first) list-scheduling estimate of the wall time that the
  same durations would need on the same number of jobs;
* with ``--deps-dump`` (the saved output of ``ninja -t deps``), translation
  units whose recorded dependencies use absolute paths below ``--base-dir``.
  With ccache ``base_dir`` set, ccache passes rewritten relative paths to the
  compiler; an absolute depfile therefore means ccache bypassed caching and ran
  the original command (for example "Could not read or parse input file").

The tool never runs Ninja, a compiler or ccache. It only reads files.
Durations in a log come from whatever load the host had at the time; treat
the derived numbers as estimates and compare like with like.
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SUPPORTED_VERSIONS = (5, 6, 7)
OBJECT_SUFFIXES = (".o", ".obj")


@dataclass
class Edge:
    """One executed Ninja edge; multi-output edges are merged."""

    start_ms: int
    end_ms: int
    cmdhash: str
    outputs: list[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    @property
    def name(self) -> str:
        # Prefer the shortest (usually relative) spelling of the output.
        return min(self.outputs, key=lambda item: (len(item), item))

    @property
    def is_compile(self) -> bool:
        return any(output.endswith(OBJECT_SUFFIXES) for output in self.outputs)


@dataclass
class LogEntry:
    start_ms: int
    end_ms: int
    mtime: str
    output: str
    cmdhash: str


def parse_log(text: str) -> list[LogEntry]:
    lines = text.splitlines()
    if not lines:
        raise ValueError("empty .ninja_log")
    match = re.match(r"^# ninja log v(\d+)\s*$", lines[0])
    if not match:
        raise ValueError(f"not a ninja log header: {lines[0]!r}")
    version = int(match.group(1))
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"unsupported ninja log version {version}")
    entries: list[LogEntry] = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError(f"line {number}: expected 5 tab-separated fields")
        start, end, mtime, output, cmdhash = fields
        entries.append(LogEntry(int(start), int(end), mtime, output, cmdhash))
    return entries


def split_builds(entries: list[LogEntry]) -> list[list[LogEntry]]:
    """Split log entries into build sessions.

    Ninja appends one line per finished edge, so end times are non-decreasing
    within a session; a smaller end time starts a new session (the same rule
    ninjatracing uses). A recompacted log prefix is written in hash order and
    therefore appears as many tiny sessions.
    """

    builds: list[list[LogEntry]] = []
    last_end = None
    for entry in entries:
        if last_end is None or entry.end_ms < last_end:
            builds.append([])
        builds[-1].append(entry)
        last_end = entry.end_ms
    return builds


def latest_per_output(entries: list[LogEntry]) -> list[LogEntry]:
    """Ninja's own view: the last recorded entry for each output wins."""

    latest: dict[str, LogEntry] = {}
    for entry in entries:
        latest[entry.output] = entry
    return list(latest.values())


def merge_edges(entries: Iterable[LogEntry]) -> list[Edge]:
    edges: dict[tuple[int, int, str], Edge] = {}
    for entry in entries:
        key = (entry.start_ms, entry.end_ms, entry.cmdhash)
        edge = edges.get(key)
        if edge is None:
            edge = edges[key] = Edge(entry.start_ms, entry.end_ms, entry.cmdhash)
        edge.outputs.append(entry.output)
    return sorted(edges.values(), key=lambda item: (item.end_ms, item.start_ms, item.name))


def max_concurrency(edges: list[Edge]) -> int:
    events: list[tuple[int, int]] = []
    for edge in edges:
        if edge.duration_ms <= 0:
            continue
        events.append((edge.start_ms, 1))
        events.append((edge.end_ms, -1))
    # Ends sort before starts at the same timestamp.
    events.sort(key=lambda item: (item[0], item[1]))
    running = peak = 0
    for _, delta in events:
        running += delta
        peak = max(peak, running)
    return peak


def lpt_wall_ms(durations: Iterable[int], jobs: int) -> int:
    """Longest-processing-time-first list scheduling on ``jobs`` workers.

    Ignores dependencies, so it is only meaningful for a flat set of compile
    edges that all become ready at once (the usual CMake object phase).
    """

    if jobs < 1:
        raise ValueError("jobs must be at least 1")
    workers = [0] * jobs
    for duration in sorted(durations, reverse=True):
        finish = heapq.heappop(workers) + duration
        heapq.heappush(workers, finish)
    return max(workers) if workers else 0


def observed_critical_chain(edges: list[Edge], slack_ms: int = 50) -> list[Edge]:
    """Walk back from the last edge to finish.

    Each step picks the edge that finished last no later than ``slack_ms``
    after the current edge started: the dependency it most plausibly waited
    for. Without the build graph this is a heuristic.
    """

    if not edges:
        return []
    by_end = sorted(edges, key=lambda item: (item.end_ms, item.duration_ms))
    current = by_end[-1]
    chain = [current]
    seen = {id(current)}
    while True:
        candidates = [
            edge for edge in by_end
            if id(edge) not in seen and edge.end_ms <= current.start_ms + slack_ms
            and edge.end_ms < current.end_ms
        ]
        if not candidates:
            break
        current = max(candidates, key=lambda item: (item.end_ms, item.duration_ms))
        if current.end_ms <= 0:
            break
        chain.append(current)
        seen.add(id(current))
    chain.reverse()
    return chain


# --- build.ninja dependency graph --------------------------------------------

def _logical_lines(text: str) -> Iterable[str]:
    pending = ""
    for raw in text.splitlines():
        line = pending + raw
        # An odd number of trailing '$' characters continues the line.
        stripped = line.rstrip("$")
        if (len(line) - len(stripped)) % 2 == 1:
            pending = line[:-1]
            continue
        pending = ""
        yield line
    if pending:
        yield pending


def _split_ninja_paths(text: str) -> list[str]:
    paths: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "$" and index + 1 < len(text):
            current.append(text[index + 1])
            index += 2
            continue
        if char in " \t":
            if current:
                paths.append("".join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        paths.append("".join(current))
    return paths


def _find_unescaped(text: str, needle: str) -> int:
    index = 0
    while index < len(text):
        if text[index] == "$":
            index += 2
            continue
        if text[index] == needle:
            return index
        index += 1
    return -1


@dataclass
class GraphEdge:
    outputs: list[str]
    inputs: list[str]
    rule: str


def parse_build_ninja(path: Path, _seen: set[Path] | None = None) -> list[GraphEdge]:
    """Parse ``build`` statements (and ``include``/``subninja`` files)."""

    seen = _seen if _seen is not None else set()
    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)
    edges: list[GraphEdge] = []
    base = path.parent
    for line in _logical_lines(path.read_text(encoding="utf-8", errors="replace")):
        if line.startswith(("include ", "subninja ")):
            target = _split_ninja_paths(line.split(None, 1)[1])[0]
            child = (base / target) if not os.path.isabs(target) else Path(target)
            if child.is_file():
                edges.extend(parse_build_ninja(child, seen))
            continue
        if not line.startswith("build "):
            continue
        body = line[len("build "):]
        colon = _find_unescaped(body, ":")
        if colon < 0:
            continue
        outputs = [item for item in _split_ninja_paths(body[:colon]) if item != "|"]
        rest = _split_ninja_paths(body[colon + 1:])
        if not rest:
            continue
        rule, inputs = rest[0], []
        for item in rest[1:]:
            if item == "|@":  # Validations do not gate the edge.
                break
            if item not in ("|", "||"):
                inputs.append(item)
        edges.append(GraphEdge(outputs, inputs, rule))
    return edges


def graph_critical_path(graph: list[GraphEdge], durations: dict[str, int],
                        root: str | None = None) -> tuple[int, list[tuple[str, int]]]:
    """Longest duration-weighted chain through the dependency graph.

    ``durations`` maps output paths to milliseconds; edges that did not run in
    the selected build weigh zero. Returns (total_ms, [(output, ms), ...]).
    """

    producer: dict[str, int] = {}
    for index, edge in enumerate(graph):
        for output in edge.outputs:
            producer[output] = index

    def weight(index: int) -> int:
        return max((durations.get(output, 0) for output in graph[index].outputs), default=0)

    deps = [[producer[name] for name in edge.inputs if name in producer] for edge in graph]
    memo: dict[int, tuple[int, int | None]] = {}

    def longest(start: int) -> tuple[int, int | None]:
        # Iterative post-order DFS; deep manifests must not hit Python's
        # recursion limit. Cycles are invalid in Ninja and are cut here.
        stack = [start]
        visiting: set[int] = set()
        while stack:
            node = stack[-1]
            if node in memo:
                stack.pop()
                continue
            if node not in visiting:
                visiting.add(node)
                stack.extend(dep for dep in deps[node] if dep not in memo and dep not in visiting)
                continue
            best_total, best_dep = 0, None
            for dep in deps[node]:
                total = memo.get(dep, (0, None))[0]
                if total > best_total:
                    best_total, best_dep = total, dep
            memo[node] = (best_total + weight(node), best_dep)
            visiting.discard(node)
            stack.pop()
        return memo[start]

    if root is not None:
        if root not in producer:
            raise ValueError(f"target {root!r} is not produced by the build graph")
        start_candidates = [producer[root]]
    else:
        start_candidates = list(range(len(graph)))
    best_total, best_start = 0, None
    for index in start_candidates:
        total, _ = longest(index)
        if total > best_total or best_start is None:
            best_total, best_start = total, index
    chain: list[tuple[str, int]] = []
    cursor = best_start
    while cursor is not None:
        names = graph[cursor].outputs
        name = min(names, key=lambda item: (len(item), item)) if names else "?"
        chain.append((name, weight(cursor)))
        cursor = memo.get(cursor, (0, None))[1]
    chain.reverse()
    return best_total, [(name, ms) for name, ms in chain if ms > 0]


# --- ninja -t deps ------------------------------------------------------------

def parse_deps_dump(text: str) -> dict[str, list[str]]:
    """Parse the text printed by ``ninja -t deps``."""

    deps: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            current = line.split(":", 1)[0]
            deps[current] = []
        elif current is not None:
            deps[current].append(line.strip())
    return deps


def absolute_depfile_targets(deps: dict[str, list[str]], base_dir: str) -> list[str]:
    prefix = base_dir.rstrip("/") + "/"
    return sorted(
        target for target, headers in deps.items()
        if target.endswith(OBJECT_SUFFIXES) and any(header.startswith(prefix) for header in headers)
    )


def shared_headers(deps: dict[str, list[str]], targets: list[str], others: list[str],
                   limit: int = 5) -> list[tuple[str, int, int]]:
    """Headers present in most ``targets`` and fewest ``others``."""

    def names(target: str) -> set[str]:
        return {os.path.normpath(header).split("/")[-1] for header in deps.get(target, [])}

    selected = [names(target) for target in targets]
    rest = [names(target) for target in others]
    counts: dict[str, list[int]] = {}
    for group, slot in ((selected, 0), (rest, 1)):
        for headers in group:
            for header in headers:
                counts.setdefault(header, [0, 0])[slot] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1][0], item[1][1], item[0]))
    return [(name, hit, miss) for name, (hit, miss) in ranked[:limit]]


# --- reporting ---------------------------------------------------------------

def group_key(edge: Edge, depth: int) -> str:
    name = edge.name
    if ".dir/" in name:
        name = name.split(".dir/", 1)[1]
    parts = name.split("/")[:-1]
    return "/".join(parts[:depth]) if parts else "."


def summarize(edges: list[Edge], *, top: int, jobs: int | None, group_depth: int,
              hit_threshold_ms: int) -> dict:
    compiles = [edge for edge in edges if edge.is_compile]
    serial = sum(edge.duration_ms for edge in edges)
    compile_serial = sum(edge.duration_ms for edge in compiles)
    wall = (max(edge.end_ms for edge in edges) - min(edge.start_ms for edge in edges)) if edges else 0
    peak = max_concurrency(edges)
    worker_count = jobs or peak or 1
    groups: dict[str, list[int]] = {}
    for edge in compiles:
        bucket = groups.setdefault(group_key(edge, group_depth), [0, 0])
        bucket[0] += 1
        bucket[1] += edge.duration_ms
    chain = observed_critical_chain(edges)
    fast = [edge for edge in compiles if edge.duration_ms < hit_threshold_ms]
    lpt = lpt_wall_ms((edge.duration_ms for edge in compiles), worker_count)
    slowest = sorted(edges, key=lambda item: (-item.duration_ms, item.name))[:top]
    return {
        "edges": len(edges),
        "compile_edges": len(compiles),
        "serial_ms": serial,
        "compile_serial_ms": compile_serial,
        "wall_ms": wall,
        "max_concurrency": peak,
        "jobs_assumed": worker_count,
        "parallel_efficiency": round(serial / (wall * worker_count), 3) if wall and worker_count else None,
        "compile_lower_bound_ms": max(
            compile_serial // worker_count if worker_count else 0,
            max((edge.duration_ms for edge in compiles), default=0),
        ),
        "compile_lpt_estimate_ms": lpt,
        "likely_cache_hits": len(fast),
        "likely_cache_hit_threshold_ms": hit_threshold_ms,
        "slowest": [
            {"output": edge.name, "ms": edge.duration_ms, "start_ms": edge.start_ms,
             "end_ms": edge.end_ms}
            for edge in slowest
        ],
        "groups": [
            {"group": name, "edges": count, "ms": total}
            for name, (count, total) in sorted(groups.items(), key=lambda item: -item[1][1])
        ],
        "observed_critical_chain": [
            {"output": edge.name, "ms": edge.duration_ms, "start_ms": edge.start_ms,
             "end_ms": edge.end_ms}
            for edge in chain
        ],
    }


def seconds(ms: int | None) -> str:
    return "-" if ms is None else f"{ms / 1000:.1f}s"


def render_text(report: dict) -> str:
    out: list[str] = []
    out.append(f"log: {report['log']}")
    out.append(f"selection: {report['selection']}")
    s = report["summary"]
    out.append(
        f"edges={s['edges']} compile_edges={s['compile_edges']} serial={seconds(s['serial_ms'])} "
        f"compile_serial={seconds(s['compile_serial_ms'])} wall={seconds(s['wall_ms'])} "
        f"max_concurrency={s['max_concurrency']}"
    )
    out.append(
        f"jobs={s['jobs_assumed']} parallel_efficiency={s['parallel_efficiency']} "
        f"compile_lower_bound={seconds(s['compile_lower_bound_ms'])} "
        f"compile_lpt_estimate={seconds(s['compile_lpt_estimate_ms'])} "
        f"likely_cache_hits(<{s['likely_cache_hit_threshold_ms']}ms)={s['likely_cache_hits']}"
    )
    out.append("")
    out.append("slowest edges:")
    for item in s["slowest"]:
        out.append(f"  {seconds(item['ms']):>8}  [{seconds(item['start_ms'])} -> {seconds(item['end_ms'])}]  {item['output']}")
    out.append("")
    out.append("compile time by directory:")
    for item in s["groups"][: report.get("top_groups", 15)]:
        out.append(f"  {seconds(item['ms']):>9}  {item['edges']:>4} TUs  {item['group']}")
    out.append("")
    chain = s["observed_critical_chain"]
    limit = report.get("chain_limit", 12)
    out.append(
        f"observed critical chain (heuristic, from timestamps; {len(chain)} steps, "
        f"showing the last {min(limit, len(chain))}; a long chain of unrelated compiles "
        "means the build was throughput-bound, not dependency-bound):"
    )
    for item in chain[-limit:] if limit > 0 else []:
        out.append(f"  {seconds(item['ms']):>8}  [{seconds(item['start_ms'])} -> {seconds(item['end_ms'])}]  {item['output']}")
    if "graph_critical_path" in report:
        gcp = report["graph_critical_path"]
        out.append("")
        out.append(f"dependency critical path ({seconds(gcp['total_ms'])}):")
        for item in gcp["chain"]:
            out.append(f"  {seconds(item['ms']):>8}  {item['output']}")
    if "deps" in report:
        deps = report["deps"]
        out.append("")
        out.append(
            f"absolute-path depfiles under {deps['base_dir']}: {len(deps['targets'])} TUs, "
            f"{seconds(deps['logged_ms'])} logged compile time in this selection"
        )
        for name, hit, miss in deps["shared_headers"]:
            out.append(f"  header {name}: in {hit} of these TUs, {miss} other TUs")
        for target in deps["targets"][: report.get("top", 20)]:
            out.append(f"  {target}")
    if "builds" in report:
        out.append("")
        out.append("build sessions (index, edges, compile edges, serial, wall):")
        for item in report["builds"]:
            out.append(
                f"  {item['index']:>4}  {item['edges']:>5}  {item['compile_edges']:>5}  "
                f"{seconds(item['serial_ms']):>9}  {seconds(item['wall_ms']):>8}"
            )
    return "\n".join(out) + "\n"


def build_report(args: argparse.Namespace) -> dict:
    log_path = Path(args.log)
    entries = parse_log(log_path.read_text(encoding="utf-8", errors="replace"))
    builds = split_builds(entries)
    if args.latest:
        selected = latest_per_output(entries)
        selection = "latest entry per output across the whole log (wall time is not meaningful)"
    else:
        try:
            chosen = builds[args.build]
        except IndexError:
            raise ValueError(f"build index {args.build} out of range (log has {len(builds)} sessions)")
        selected = chosen
        index = args.build if args.build >= 0 else len(builds) + args.build
        selection = f"build session {index} of {len(builds)} (0-based; -1 = most recent)"
    edges = merge_edges(selected)
    report: dict = {
        "log": str(log_path),
        "selection": selection,
        "top": args.top,
        "chain_limit": args.chain_limit,
        "summary": summarize(edges, top=args.top, jobs=args.jobs, group_depth=args.group_depth,
                             hit_threshold_ms=args.hit_threshold_ms),
    }
    durations = {}
    for edge in edges:
        for output in edge.outputs:
            durations[output] = edge.duration_ms
    if args.build_ninja:
        graph = parse_build_ninja(Path(args.build_ninja))
        total, chain = graph_critical_path(graph, durations, args.target)
        report["graph_critical_path"] = {
            "total_ms": total,
            "chain": [{"output": name, "ms": ms} for name, ms in chain],
        }
    if args.deps_dump:
        if not args.base_dir:
            raise ValueError("--deps-dump requires --base-dir (the ccache base_dir)")
        deps = parse_deps_dump(Path(args.deps_dump).read_text(encoding="utf-8", errors="replace"))
        targets = absolute_depfile_targets(deps, args.base_dir)
        others = [target for target in deps if target.endswith(OBJECT_SUFFIXES) and target not in targets]
        report["deps"] = {
            "base_dir": args.base_dir,
            "targets": targets,
            "logged_ms": sum(durations.get(target, 0) for target in targets),
            "shared_headers": shared_headers(deps, targets, others),
        }
    if args.list_builds:
        rows = []
        for index, build in enumerate(builds):
            build_edges = merge_edges(build)
            if len(build_edges) < args.min_build_edges:
                continue
            rows.append({
                "index": index,
                "edges": len(build_edges),
                "compile_edges": sum(1 for edge in build_edges if edge.is_compile),
                "serial_ms": sum(edge.duration_ms for edge in build_edges),
                "wall_ms": (max(edge.end_ms for edge in build_edges)
                            - min(edge.start_ms for edge in build_edges)),
            })
        report["builds"] = rows
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("log", help="path to a .ninja_log (or a build directory containing one)")
    parser.add_argument("--top", type=int, default=20, help="slowest edges to list (default 20)")
    parser.add_argument("--build", type=int, default=-1,
                        help="0-based build session index; negative counts from the end (default -1)")
    parser.add_argument("--latest", action="store_true",
                        help="use the latest entry per output across the whole log instead of one session")
    parser.add_argument("--list-builds", action="store_true", help="also list build sessions")
    parser.add_argument("--min-build-edges", type=int, default=10,
                        help="hide sessions with fewer edges in --list-builds (default 10)")
    parser.add_argument("--jobs", type=int, default=None,
                        help="worker count for estimates (default: observed max concurrency)")
    parser.add_argument("--group-depth", type=int, default=2,
                        help="directory components used to group compile edges (default 2)")
    parser.add_argument("--hit-threshold-ms", type=int, default=1000,
                        help="compile edges faster than this count as likely ccache hits (default 1000)")
    parser.add_argument("--chain-limit", type=int, default=12,
                        help="observed-chain steps to print in text mode (default 12)")
    parser.add_argument("--build-ninja", help="build.ninja for the dependency critical path")
    parser.add_argument("--target", help="restrict the dependency critical path to this output")
    parser.add_argument("--deps-dump", help="saved output of 'ninja -t deps' for the same build directory")
    parser.add_argument("--base-dir", help="ccache base_dir used by the build (for --deps-dump)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)
    log = Path(args.log)
    if log.is_dir():
        args.log = str(log / ".ninja_log")
    try:
        report = build_report(args)
    except (OSError, ValueError) as error:
        print(f"ninja_log_report: {error}", file=sys.stderr)
        return 2
    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
