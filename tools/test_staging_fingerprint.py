import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import staging_fingerprint as fp  # noqa: E402
from renegade_patch_inventory import parse_applications  # noqa: E402

TOOLS = {"patch": "GNU patch test", "python": "test"}
PATCH = 'patch --batch --forward --fuzz=0 --no-backup-if-mismatch -d "$rv_stage{target}" -p1 < "$rv_root/port/patches/{name}"'
SCRIPT = """#!/usr/bin/env bash
set -Eeuo pipefail
rv_root=$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)
rv_upstream="$rv_root/upstream/CnC_Renegade"
rv_stage="$rv_root/staging"
python3 "$rv_root/tools/renegade_patch_inventory.py" --root "$rv_root" --count > /dev/null
rv_managed_stage_dirs=(
	alpha beta gamma
)
for rv_dir in "${{rv_managed_stage_dirs[@]}}"; do
	rm -rf -- "$rv_stage/$rv_dir"
	mkdir -p "$rv_stage/$rv_dir"
done
find "$rv_upstream/Code/Alpha" -maxdepth 1 -type f -exec cp -t "$rv_stage/alpha/" -- {{}} +
find "$rv_upstream/Code/Beta" -maxdepth 1 -type f -exec cp -t "$rv_stage/beta/" -- {{}} +
find "$rv_upstream/Code/Gamma" -maxdepth 1 -type f -exec cp -t "$rv_stage/gamma/" -- {{}} +
{patches}
echo "Applied: port/patches/alpha-two.patch"
# Anchor the beta source before the gamma copy.
rv_beta_sha=$(sha256sum "$rv_stage/beta/b.cpp" | cut -d' ' -f1)
if [[ "$rv_beta_sha" != "{beta_anchor}" ]]; then
	echo "Refusing unanchored beta patch: b.cpp changed ($rv_beta_sha)" >&2
	exit 1
fi
cp -- "$rv_stage/alpha/a.h" "$rv_stage/gamma/A.H"
python3 "$rv_root/tools/gamma_fix.py" "$rv_stage/gamma/g.cpp"
touch "$rv_stage/alpha"/* "$rv_stage/beta"/* "$rv_stage/gamma"/*
python3 "$rv_root/tools/renegade_patch_inventory.py" --root "$rv_root" --write-staging-receipt
"""
DEFAULT_PATCHES = [
    ("/alpha", "alpha-one.patch"),
    ("/beta", "beta-one.patch"),
    ("/alpha", "alpha-two.patch"),
    ("", "root-both.patch"),
]


def diff(path, old, new):
    return f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"


class Tree:
    """A synthetic repository root with a staging script, patches, upstream and staging."""

    def __init__(self, base, patches=None, beta_anchor="0" * 64):
        self.root = pathlib.Path(base)
        self.patches = list(patches or DEFAULT_PATCHES)
        self.beta_anchor = beta_anchor
        for relative, text in {
            "port/patches/alpha-one.patch": diff("a.cpp", "a", "a1"),
            "port/patches/alpha-two.patch": diff("a.h", "h", "h2"),
            "port/patches/beta-one.patch": diff("b.cpp", "b", "b1"),
            "port/patches/root-both.patch": diff("alpha/a.cpp", "a1", "a2") + diff("beta/b.cpp", "b1", "b2"),
            "upstream/CnC_Renegade/Code/Alpha/a.cpp": "a\n",
            "upstream/CnC_Renegade/Code/Alpha/a.h": "h\n",
            "upstream/CnC_Renegade/Code/Beta/b.cpp": "b\n",
            "upstream/CnC_Renegade/Code/Gamma/g.cpp": "g\n",
            "tools/gamma_fix.py": "print('gamma')\n",
            "tools/renegade_patch_inventory.py": "# stand-in\n",
            "staging/alpha/a.cpp": "a2\n",
            "staging/alpha/a.h": "h2\n",
            "staging/beta/b.cpp": "b2\n",
            "staging/gamma/g.cpp": "g!\n",
            "staging/gamma/A.H": "h2\n",
            "staging/PATCH_INVENTORY.json": "{}\n",
        }.items():
            self.write(relative, text)
        self.write_script()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def append(self, relative, text):
        with (self.root / relative).open("a", encoding="utf-8") as handle:
            handle.write(text)

    def write_script(self, transform=None):
        body = SCRIPT.format(
            patches="\n".join(PATCH.format(target=target, name=name) for target, name in self.patches),
            beta_anchor=self.beta_anchor)
        self.write(fp.SCRIPT, transform(body) if transform else body)

    def record(self, tools=TOOLS):
        fp.begin(self.root, tools=tools)
        code, result = fp.record(self.root, tools=tools)
        assert code == 0, result
        return result

    def check(self, tools=TOOLS):
        return fp.check(self.root, tools=tools)


class StagingFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tree = Tree(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def assertStaleInputs(self, dirty):
        code, result = self.tree.check()
        self.assertEqual((code, result["status"]), (1, "STALE_INPUTS"), result)
        self.assertEqual(result["dirty"], dirty, result)
        return result

    def test_no_stamp_is_absent_and_record_then_check_is_fresh(self):
        self.assertEqual(self.tree.check()[0], 2)
        self.tree.record()
        code, result = self.tree.check()
        self.assertEqual((code, result["status"]), (0, "FRESH"))
        self.assertFalse((self.tree.root / fp.PENDING).exists())

    def test_patch_change_restages_its_module_and_modules_that_copy_from_it(self):
        self.tree.record()
        self.tree.append("port/patches/beta-one.patch", "\n")
        result = self.assertStaleInputs(["beta"])
        self.assertIn("patch changed port/patches/beta-one.patch", result["reasons"]["beta"])
        self.tree.write("port/patches/beta-one.patch", diff("b.cpp", "b", "b1"))
        self.assertEqual(self.tree.check()[0], 0)
        # gamma copies alpha/a.h, so an alpha patch also dirties gamma, never beta.
        self.tree.append("port/patches/alpha-two.patch", "\n")
        result = self.assertStaleInputs(["alpha", "gamma"])
        self.assertEqual(result["reasons"]["gamma"], "reads alpha")

    def test_upstream_change_restages_only_the_module_that_copies_it(self):
        self.tree.record()
        self.tree.write("upstream/CnC_Renegade/Code/Beta/b.cpp", "B\n")
        self.assertStaleInputs(["beta"])

    def test_appended_patch_line_restages_only_its_module(self):
        self.tree.record()
        self.tree.write("port/patches/beta-two.patch", diff("b.cpp", "b2", "b3"))
        self.tree.patches.append(("/beta", "beta-two.patch"))
        self.tree.write_script()
        result = self.assertStaleInputs(["beta"])
        self.assertIn("patch added port/patches/beta-two.patch", result["reasons"]["beta"])

    def test_module_scoped_anchor_block_dirties_only_its_module(self):
        self.tree.record()
        self.tree.beta_anchor = "1" * 64
        self.tree.write_script()
        self.assertStaleInputs(["beta"])

    def test_global_script_logic_change_restages_every_module(self):
        self.tree.record()
        self.tree.write_script(lambda body: body.replace('mkdir -p "$rv_stage/$rv_dir"',
                                                          'mkdir -p -- "$rv_stage/$rv_dir"'))
        self.assertStaleInputs(["alpha", "beta", "gamma"])

    def test_global_helper_and_tool_version_changes_restage_every_module(self):
        self.tree.record()
        self.tree.append("tools/renegade_patch_inventory.py", "# changed\n")
        self.assertStaleInputs(["alpha", "beta", "gamma"])
        self.tree.record()
        code, result = self.tree.check(tools={"patch": "GNU patch other", "python": "test"})
        self.assertEqual((code, result["dirty"]), (1, ["alpha", "beta", "gamma"]))

    def test_module_helper_change_restages_only_that_module(self):
        self.tree.record()
        self.tree.append("tools/gamma_fix.py", "print('changed')\n")
        self.assertStaleInputs(["gamma"])

    def test_order_within_a_module_is_part_of_its_fingerprint(self):
        inputs = fp.compute_inputs(self.tree.root, tools=TOOLS)
        alpha = [row[1] for row in inputs["modules"]["alpha"]["entries"] if row[0] == "patch"]
        self.assertEqual(alpha, ["port/patches/alpha-one.patch", "port/patches/alpha-two.patch",
                                 "port/patches/root-both.patch"])
        self.tree.record()
        self.tree.patches[0], self.tree.patches[2] = self.tree.patches[2], self.tree.patches[0]
        self.tree.write_script()
        result = self.assertStaleInputs(["alpha", "gamma"])
        self.assertEqual(result["reasons"]["alpha"], "patch/unit order changed")

    def test_cross_module_reorder_is_stale_but_dirties_no_module(self):
        self.tree.record()
        self.tree.patches[0], self.tree.patches[1] = self.tree.patches[1], self.tree.patches[0]
        self.tree.write_script()
        # The registry order (and receipt) changed, so no skip; module outputs cannot change.
        self.assertStaleInputs([])

    def test_inert_comment_and_echo_lines_dirty_no_module(self):
        self.tree.record()
        self.tree.write_script(lambda body: body + '# note\necho "Applied: port/patches/beta-one.patch"\n')
        self.assertStaleInputs([])

    def test_root_level_patch_is_attributed_by_its_diff_paths(self):
        inputs = fp.compute_inputs(self.tree.root, tools=TOOLS)
        for module in ("alpha", "beta"):
            self.assertIn(["patch", "port/patches/root-both.patch"],
                          [row[:2] for row in inputs["modules"][module]["entries"]])
        self.assertNotIn("port/patches/root-both.patch",
                         [row[1] for row in inputs["modules"]["gamma"]["entries"]])
        self.tree.record()
        self.tree.append("port/patches/root-both.patch", "\n")
        self.assertStaleInputs(["alpha", "beta", "gamma"])

    def test_staged_output_changes_are_detected_with_the_module(self):
        self.tree.record()
        for mutate in (lambda: self.tree.append("staging/beta/b.cpp", "x"),
                       lambda: self.tree.write("staging/beta/extra.h", "x"),
                       lambda: (self.tree.root / "staging/beta/b.cpp").unlink(),
                       lambda: self.tree.append("staging/PATCH_INVENTORY.json", " ")):
            mutate()
            code, result = self.tree.check()
            self.assertEqual((code, result["status"]), (1, "STALE_OUTPUTS"), result)
            self.tree.record()
        self.tree.append("staging/beta/b.cpp", "y")
        self.assertEqual(self.tree.check()[1]["dirty"], ["beta"])

    def test_record_refuses_when_inputs_change_during_staging(self):
        fp.begin(self.tree.root, tools=TOOLS)
        self.tree.append("port/patches/alpha-one.patch", "\n")
        code, result = fp.record(self.tree.root, tools=TOOLS)
        self.assertEqual((code, result["status"]), (1, "NOT_RECORDED"))
        self.assertEqual(result["dirty"], ["alpha", "gamma"])
        self.assertFalse((self.tree.root / fp.STAMP).exists())
        self.assertEqual(self.tree.check()[0], 2)

    def test_begin_removes_a_previous_stamp(self):
        self.tree.record()
        fp.begin(self.tree.root, tools=TOOLS)
        self.assertEqual(self.tree.check()[0], 2)

    def test_command_line_exit_codes(self):
        command = [sys.executable, str(ROOT / "tools/staging_fingerprint.py"), "--root", str(self.tree.root)]
        self.assertEqual(subprocess.run(command + ["check"], capture_output=True).returncode, 2)
        for step in ("begin", "record"):
            subprocess.run(command + [step], check=True, capture_output=True)
        result = subprocess.run(command + ["check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Staging fingerprint FRESH", result.stdout)
        self.tree.append("upstream/CnC_Renegade/Code/Gamma/g.cpp", "!")
        result = subprocess.run(command + ["check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("dirty modules gamma", result.stdout)
        plan = json.loads(subprocess.run(command + ["plan"], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(plan["dirty"], ["gamma"])


class RealStagingScriptTests(unittest.TestCase):
    """Attribution of the real tools/stage_sources.sh (no upstream checkout needed)."""

    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / fp.SCRIPT).read_text(encoding="utf-8")
        cls.managed = fp.managed_dirs(cls.text)
        cls.applied = []
        cls.scopes, cls.edges = fp.analyse(
            cls.text, cls.managed,
            lambda path: fp.patch_modules((ROOT / path).read_text(encoding="utf-8", errors="replace"),
                                          cls.managed),
            cls.applied)

    def test_fast_patch_parse_matches_the_inventory_parser_in_order(self):
        self.assertEqual(self.applied, parse_applications(self.text))

    def test_every_registered_patch_belongs_to_a_managed_module(self):
        self.assertEqual(len(self.managed), 15)
        self.assertNotIn("patch", [entry[0] for entry in self.scopes[fp.GLOBAL]])
        attributed = {entry[1] for name in self.managed for entry in self.scopes[name] if entry[0] == "patch"}
        self.assertEqual(attributed, {application["path"] for application in self.applied})

    def test_anchor_blocks_are_module_scoped_and_copies_add_edges(self):
        global_units = [entry[1] for entry in self.scopes[fp.GLOBAL] if entry[0] == "unit"]
        self.assertFalse([unit for unit in global_units if "sha256sum" in unit or "Refusing unanchored" in unit])
        for edge in (("wwmath", "wwaudio"), ("wwlib", "wwaudio"), ("wwmath", "combat")):
            self.assertIn(edge, self.edges)
        self.assertIn(("file", "tools/restore_postthink_sampler.py"), self.scopes["combat"])
        self.assertIn(("file", "port/compatibility/include/bittype.h"), self.scopes["wwaudio"])
        self.assertIn(("file", "tools/staging_fingerprint.py"), self.scopes[fp.GLOBAL])


if __name__ == "__main__":
    unittest.main()
