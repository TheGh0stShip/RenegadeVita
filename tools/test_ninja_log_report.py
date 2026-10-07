#!/usr/bin/env python3
"""Pure-Python tests for tools/ninja_log_report.py (no Ninja, no compiler)."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools import ninja_log_report as report

# Two sessions. Session 0 is an older incremental build. Session 1 is a full
# build on two workers: gen.inc -> {a,b,c,big}.obj -> app -> app.vpk, plus a
# multi-output edge (two pngs, one command) logged twice. Ninja appends lines
# in completion order, so end times only decrease at a session boundary.
SYNTHETIC_LOG = """# ninja log v5
0\t900\t1\tCMakeFiles/app.dir/src/a.cpp.obj\taaaa
900\t1500\t2\tapp\tlink0
0\t100\t10\tgenerated/gen.inc\tgen1
100\t600\t12\tCMakeFiles/app.dir/port/b.cpp.obj\tccc2
100\t1100\t11\tCMakeFiles/app.dir/src/a.cpp.obj\tccc1
1100\t1300\t14\tCMakeFiles/app.dir/port/c.cpp.obj\tccc4
600\t2600\t13\tCMakeFiles/app.dir/src/big.cpp.obj\tccc3
2600\t3400\t15\tapp\tlink1
3400\t3500\t16\tlivearea/bg0.png\tpng1
3400\t3500\t16\tlivearea/startup.png\tpng1
3500\t3600\t17\tapp.vpk\tvpk1
"""

SYNTHETIC_BUILD_NINJA = """ninja_required_version = 1.5
include rules.ninja
build generated/gen.inc: GEN ../tools/gen.py
build cmake_object_order_depends_target_app: phony || generated/gen.inc
build CMakeFiles/app.dir/src/a.cpp.obj: CXX ../src/a.cpp || cmake_object_order_depends_target_app
build CMakeFiles/app.dir/port/b.cpp.obj: CXX ../port/b.cpp || cmake_object_order_depends_target_app
build CMakeFiles/app.dir/src/big.cpp.obj: CXX ../src/big.cpp || cmake_object_order_depends_target_app
build CMakeFiles/app.dir/port/c.cpp.obj: CXX ../port/c$ name.cpp || cmake_object_order_depends_target_app
build app: LINK CMakeFiles/app.dir/src/a.cpp.obj CMakeFiles/app.dir/port/b.cpp.obj $
    CMakeFiles/app.dir/src/big.cpp.obj CMakeFiles/app.dir/port/c.cpp.obj
build livearea/bg0.png livearea/startup.png: PNG ../assets/x.png
build app.vpk: VPK app | livearea/bg0.png livearea/startup.png |@ check.stamp
build all: phony app.vpk
"""

SYNTHETIC_RULES_NINJA = """rule CXX
  command = cc -c $in -o $out
build ignored-from-include: phony
"""

SYNTHETIC_DEPS = """CMakeFiles/app.dir/src/a.cpp.obj: #deps 2, deps mtime 1 (VALID)
    ../../src/a.h
    /usr/include/stdio.h

CMakeFiles/app.dir/src/big.cpp.obj: #deps 3, deps mtime 1 (VALID)
    /work/tree/port/compat/WWLib\\Notify.h
    /work/tree/src/big.h
    /usr/include/stdio.h

CMakeFiles/app.dir/port/b.cpp.obj: #deps 1, deps mtime 1 (VALID)
    ../../src/a.h

app: #deps 0, deps mtime 1 (VALID)
"""


class ParseTests(unittest.TestCase):
    def test_rejects_unknown_header(self):
        with self.assertRaises(ValueError):
            report.parse_log("# not a ninja log\n")

    def test_rejects_unsupported_version(self):
        with self.assertRaises(ValueError):
            report.parse_log("# ninja log v4\n")

    def test_splits_sessions_on_decreasing_end_time(self):
        builds = report.split_builds(report.parse_log(SYNTHETIC_LOG))
        self.assertEqual([2, 9], [len(build) for build in builds])

    def test_latest_entry_per_output_wins(self):
        latest = report.latest_per_output(report.parse_log(SYNTHETIC_LOG))
        by_output = {entry.output: entry for entry in latest}
        self.assertEqual("ccc1", by_output["CMakeFiles/app.dir/src/a.cpp.obj"].cmdhash)
        self.assertEqual("link1", by_output["app"].cmdhash)

    def test_multi_output_edge_is_counted_once(self):
        builds = report.split_builds(report.parse_log(SYNTHETIC_LOG))
        edges = report.merge_edges(builds[-1])
        self.assertEqual(8, len(edges))
        png = [edge for edge in edges if edge.cmdhash == "png1"]
        self.assertEqual(1, len(png))
        self.assertEqual("livearea/bg0.png", png[0].name)
        self.assertEqual(2, len(png[0].outputs))


class SummaryTests(unittest.TestCase):
    def setUp(self):
        builds = report.split_builds(report.parse_log(SYNTHETIC_LOG))
        self.edges = report.merge_edges(builds[-1])

    def test_serial_wall_and_concurrency(self):
        summary = report.summarize(self.edges, top=3, jobs=None, group_depth=1,
                                   hit_threshold_ms=300)
        self.assertEqual(8, summary["edges"])
        self.assertEqual(4, summary["compile_edges"])
        self.assertEqual(100 + 1000 + 500 + 2000 + 200 + 800 + 100 + 100, summary["serial_ms"])
        self.assertEqual(3700, summary["compile_serial_ms"])
        self.assertEqual(3600, summary["wall_ms"])
        self.assertEqual(2, summary["max_concurrency"])
        self.assertEqual(2, summary["jobs_assumed"])
        self.assertEqual(1, summary["likely_cache_hits"])  # c.cpp at 200 ms
        self.assertEqual("CMakeFiles/app.dir/src/big.cpp.obj", summary["slowest"][0]["output"])
        groups = {item["group"]: item for item in summary["groups"]}
        self.assertEqual({"src", "port"}, set(groups))
        self.assertEqual(3000, groups["src"]["ms"])
        self.assertEqual(2, groups["port"]["edges"])

    def test_lpt_estimate_and_lower_bound(self):
        self.assertEqual(2000, report.lpt_wall_ms([1000, 500, 2000, 200], 2))
        self.assertEqual(3700, report.lpt_wall_ms([1000, 500, 2000, 200], 1))
        self.assertEqual(0, report.lpt_wall_ms([], 4))
        with self.assertRaises(ValueError):
            report.lpt_wall_ms([1], 0)
        summary = report.summarize(self.edges, top=1, jobs=2, group_depth=2,
                                   hit_threshold_ms=1)
        self.assertEqual(2000, summary["compile_lower_bound_ms"])
        self.assertEqual(2000, summary["compile_lpt_estimate_ms"])

    def test_observed_chain_follows_waits_back_to_the_start(self):
        chain = [edge.name for edge in report.observed_critical_chain(self.edges)]
        self.assertEqual(
            ["generated/gen.inc", "CMakeFiles/app.dir/port/b.cpp.obj",
             "CMakeFiles/app.dir/src/big.cpp.obj", "app", "livearea/bg0.png", "app.vpk"],
            chain,
        )


class GraphTests(unittest.TestCase):
    def test_parses_escapes_continuations_and_includes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.ninja").write_text(SYNTHETIC_BUILD_NINJA, encoding="utf-8")
            (root / "rules.ninja").write_text(SYNTHETIC_RULES_NINJA, encoding="utf-8")
            graph = report.parse_build_ninja(root / "build.ninja")
        by_output = {output: edge for edge in graph for output in edge.outputs}
        self.assertIn("ignored-from-include", by_output)
        self.assertEqual(["../port/c name.cpp", "cmake_object_order_depends_target_app"],
                         by_output["CMakeFiles/app.dir/port/c.cpp.obj"].inputs)
        self.assertEqual(4, len(by_output["app"].inputs))
        # Validation inputs after |@ do not gate the edge.
        self.assertEqual(["app", "livearea/bg0.png", "livearea/startup.png"],
                         by_output["app.vpk"].inputs)
        self.assertEqual("PNG", by_output["livearea/startup.png"].rule)

    def test_dependency_critical_path_uses_logged_durations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.ninja").write_text(SYNTHETIC_BUILD_NINJA, encoding="utf-8")
            (root / "rules.ninja").write_text(SYNTHETIC_RULES_NINJA, encoding="utf-8")
            graph = report.parse_build_ninja(root / "build.ninja")
        builds = report.split_builds(report.parse_log(SYNTHETIC_LOG))
        durations = {}
        for edge in report.merge_edges(builds[-1]):
            for output in edge.outputs:
                durations[output] = edge.duration_ms
        total, chain = report.graph_critical_path(graph, durations)
        self.assertEqual(100 + 2000 + 800 + 100, total)
        self.assertEqual(["generated/gen.inc", "CMakeFiles/app.dir/src/big.cpp.obj", "app", "app.vpk"],
                         [name for name, _ in chain])
        deep = [report.GraphEdge([f"n{i}"], [f"n{i - 1}"] if i else [], "R") for i in range(5000)]
        deep_total, deep_chain = report.graph_critical_path(deep, {f"n{i}": 1 for i in range(5000)})
        self.assertEqual((5000, 5000), (deep_total, len(deep_chain)))
        cyclic = [report.GraphEdge(["a"], ["b"], "R"), report.GraphEdge(["b"], ["a"], "R")]
        self.assertEqual(5, report.graph_critical_path(cyclic, {"a": 2, "b": 3})[0])
        total_app, _ = report.graph_critical_path(graph, durations, root="app")
        self.assertEqual(2900, total_app)
        with self.assertRaises(ValueError):
            report.graph_critical_path(graph, durations, root="missing")


class DepsTests(unittest.TestCase):
    def test_absolute_depfiles_mark_ccache_bypass(self):
        deps = report.parse_deps_dump(SYNTHETIC_DEPS)
        self.assertEqual(["../../src/a.h", "/usr/include/stdio.h"],
                         deps["CMakeFiles/app.dir/src/a.cpp.obj"])
        targets = report.absolute_depfile_targets(deps, "/work/tree/")
        self.assertEqual(["CMakeFiles/app.dir/src/big.cpp.obj"], targets)
        others = ["CMakeFiles/app.dir/src/a.cpp.obj", "CMakeFiles/app.dir/port/b.cpp.obj"]
        ranked = report.shared_headers(deps, targets, others, limit=2)
        self.assertEqual(("WWLib\\Notify.h", 1, 0), ranked[0])


class CommandLineTests(unittest.TestCase):
    def run_main(self, *argv):
        stream = io.StringIO()
        with redirect_stdout(stream):
            status = report.main(list(argv))
        return status, stream.getvalue()

    def test_text_and_json_output_from_a_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ninja_log").write_text(SYNTHETIC_LOG, encoding="utf-8")
            (root / "build.ninja").write_text(SYNTHETIC_BUILD_NINJA, encoding="utf-8")
            (root / "rules.ninja").write_text(SYNTHETIC_RULES_NINJA, encoding="utf-8")
            deps = root / "deps.txt"
            deps.write_text(SYNTHETIC_DEPS, encoding="utf-8")
            status, text = self.run_main(str(root), "--top", "2", "--list-builds",
                                         "--min-build-edges", "1",
                                         "--build-ninja", str(root / "build.ninja"),
                                         "--deps-dump", str(deps), "--base-dir", "/work/tree")
            self.assertEqual(0, status)
            self.assertIn("build session 1 of 2", text)
            self.assertIn("2.0s  [0.6s -> 2.6s]  CMakeFiles/app.dir/src/big.cpp.obj", text)
            self.assertIn("dependency critical path (3.0s):", text)
            self.assertIn("absolute-path depfiles under /work/tree: 1 TUs, 2.0s", text)
            self.assertIn("header WWLib\\Notify.h: in 1 of these TUs, 0 other TUs", text)
            status, raw = self.run_main(str(root / ".ninja_log"), "--json", "--build", "0")
            self.assertEqual(0, status)
            data = json.loads(raw)
            self.assertEqual(2, data["summary"]["edges"])
            self.assertEqual(1500, data["summary"]["wall_ms"])
            status, raw = self.run_main(str(root), "--json", "--latest")
            self.assertEqual(0, status)
            self.assertEqual(8, json.loads(raw)["summary"]["edges"])

    def test_errors_return_status_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / ".ninja_log"
            bad.write_text("garbage\n", encoding="utf-8")
            stream = io.StringIO()
            with redirect_stdout(stream):
                import contextlib
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(2, report.main([str(bad)]))
                    self.assertEqual(2, report.main([str(Path(tmp) / "missing")]))


if __name__ == "__main__":
    unittest.main()
