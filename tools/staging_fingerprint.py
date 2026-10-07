#!/usr/bin/env python3
"""Input/output fingerprint for the deterministic tools/stage_sources.sh run.

Staging output is a pure function of: the staging script, the ordered
registered patches, the upstream paths the script names, the repository helper
files it names, and the GNU patch version.  ``begin`` (start of
staging) and ``record`` (after the receipt is written) store those inputs plus a
content manifest of every staged file under ``build/staging-stamp.json``.
``check`` proves that a full restage would rewrite byte-identical files: it
passes only when the inputs AND the staged tree still match the stamp.

The script is also split into per-module fingerprints: each managed staging
directory owns its ordered patch applications (root-level patches by their
---/+++ paths) and the script units that name only that directory (copies,
sha256 anchors and the ``if [[ ]]`` blocks that read their variables, helper
calls).  Literal echo/comment lines are inert; every other unit is global.  A
copy between modules adds a src->dst edge; any other multi-module unit couples
its modules.  ``check``/``plan`` report the resulting dirty-module closure.
Execution stays whole-tree: a stale stamp means a full restage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if __package__:
    from .renegade_patch_inventory import parse_applications
else:
    from renegade_patch_inventory import parse_applications

SCHEMA = 1
SCRIPT = "tools/stage_sources.sh"
STAMP = "build/staging-stamp.json"
PENDING = "build/staging-stamp.pending.json"
GLOBAL = "<global>"

_END = r"(?![A-Za-z0-9_])"
STAGE_REF = re.compile(r"\$(?:\{rv_stage\}|rv_stage" + _END + r")(?:/([A-Za-z0-9_]+))?")
ROOT_REF = re.compile(r"\$(?:\{rv_root\}|rv_root" + _END + r")/([A-Za-z0-9_./-]+)")
UPSTREAM_REF = re.compile(r"\$(?:\{rv_upstream\}|rv_upstream" + _END + r")((?:/[A-Za-z0-9_.-]+)*)")
VAR_REF = re.compile(r"\$\{?(rv_[A-Za-z0-9_]+)")
ASSIGN = re.compile(r"^\s*(rv_[A-Za-z0-9_]+)=")
LOCAL = re.compile(r"\bfor\s+(rv_[A-Za-z0-9_]+)\s+in\b|\bread\b[^;\n]*?\b(rv_[A-Za-z0-9_]+)\s*(?:;|$)"
                   r"|(?:^|[\s;])(rv_[A-Za-z0-9_]+)=", re.M)
OPEN = re.compile(r"(?:^|[;&|(]|\bthen|\bdo|\belse)\s*(?:if|for|while|until|case)\b")
CLOSE = re.compile(r"(?:^|[;&|]|\bthen|\bdo|\belse)\s*(?:fi|done|esac)\b")
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
ECHO_LITERAL = re.compile(r"""^\s*echo\s+(?:"[^"$`\\]*"|'[^']*')\s*(?:>&2)?\s*;?\s*$""")
PATCH_COMMAND = re.compile(r"\s*patch(?:\s|$)")
# The registered form; anything else goes through the inventory's own parser.
CANONICAL_PATCH = re.compile(
    r'\s*patch[ \t]+--batch[ \t]+--forward[ \t]+--fuzz=0[ \t]+--no-backup-if-mismatch[ \t]+'
    r'-d[ \t]+"\$rv_stage(?:/([A-Za-z0-9_]+))?"[ \t]+-p1[ \t]+<[ \t]+'
    r'"\$rv_root/(port/patches/[A-Za-z0-9_.-]+\.patch)"[ \t]*')
MANAGED = re.compile(r"^rv_managed_stage_dirs=\((.*?)\)", re.S | re.M)
DIFF_PATH = re.compile(r"^(?:---|\+\+\+) (\S+)", re.M)
NOT_ROOT_INPUTS = ("port/patches/", "staging", "build", "upstream/")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_json(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _read(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def digest_path(path: Path) -> str:
    """Content digest of a file, or of every file below a directory (no .git)."""
    if path.is_file():
        return sha256(path.read_bytes())
    if not path.is_dir():
        return "missing"
    rows, base = [], str(path)
    for directory, subdirs, files in os.walk(base):
        subdirs[:] = sorted(name for name in subdirs if name != ".git")
        for name in sorted(files):
            item = os.path.join(directory, name)
            if os.path.isfile(item):
                rows.append([item[len(base) + 1:].replace(os.sep, "/"), sha256(_read(item))])
    return digest_json(rows)


def managed_dirs(text: str) -> list[str]:
    match = MANAGED.search(text)
    if match is None:
        raise ValueError("rv_managed_stage_dirs=( ... ) not found in the staging script")
    names = match.group(1).split()
    if not names or len(set(names)) != len(names):
        raise ValueError("managed staging directory list is empty or repeated")
    return names


def split_units(text: str) -> list[str]:
    """Group logical lines into units: one command, one if/for/while/case block,
    or one command with its here-document.  Mis-grouping only merges units,
    which widens attribution (more modules or global), never narrows it."""
    units, current, depth, heredoc = [], [], 0, None
    for line in text.replace("\r\n", "\n").replace("\\\n", "").split("\n"):
        current.append(line)
        if heredoc is not None:
            if (line.lstrip("\t") if heredoc[0] else line) == heredoc[1]:
                heredoc = None
        elif not line.lstrip().startswith("#"):
            depth += len(OPEN.findall(line)) - len(CLOSE.findall(line))
            match = HEREDOC.search(line)
            if match:
                heredoc = (match.group(1) == "-", match.group(3))
        if heredoc is None and depth <= 0:
            units.append("\n".join(current))
            current, depth = [], 0
    if current:
        units.append("\n".join(current))
    return units


def patch_modules(payload: str, managed: list[str]) -> list[str]:
    """Managed directories named by a root-level (-d "$rv_stage") patch."""
    found = []
    for raw in DIFF_PATH.findall(payload):
        parts = raw.split("/")
        if raw == "/dev/null" or len(parts) < 3:
            continue
        if parts[1] in managed and parts[1] not in found:
            found.append(parts[1])
    return found


def line_applications(line: str) -> list[dict]:
    """parse_applications() for one logical line, with a fast exact path."""
    match = CANONICAL_PATCH.fullmatch(line)
    if match:
        return [{"path": match.group(2), "directory": match.group(1) or ""}]
    return parse_applications(line)


def analyse(text: str, managed: list[str], root_patch_modules, applied=None) -> tuple[dict, set]:
    """Attribute every script unit; pure function of the script text.

    Returns ({scope: [entry, ...]}, edges).  Entries keep script order and are
    ("patch", path), ("unit", text), ("file", repo path) or ("upstream", path).
    ``applied`` (a list) receives every registered application in script order.
    """
    scopes = {GLOBAL: [], **{name: [] for name in managed}}
    edges: set[tuple[str, str]] = set()
    var_modules: dict[str, list[str]] = {}
    applied = [] if applied is None else applied

    def applications(line: str) -> list[dict]:
        found = line_applications(line)
        applied.extend(found)
        return found

    for unit in split_units(text):
        lines = [line for line in unit.split("\n") if line.strip() and not line.lstrip().startswith("#")]
        if not lines or (len(lines) == 1 and ECHO_LITERAL.match(lines[0])):
            continue
        if len(lines) == 1 and PATCH_COMMAND.match(lines[0]):
            for application in applications(lines[0]):
                directory = application["directory"]
                targets = [directory] if directory in managed else (
                    root_patch_modules(application["path"]) if not directory else [])
                for target in targets or [GLOBAL]:
                    scopes[target].append(("patch", application["path"]))
            continue
        modules, whole_stage = [], False
        for match in STAGE_REF.finditer(unit):
            if match.group(1) in managed:
                modules.append(match.group(1))
            else:
                whole_stage = True
        direct = list(dict.fromkeys(modules))
        local = {name for group in LOCAL.findall(unit) for name in group if name}
        for name in VAR_REF.findall(unit):
            if name in var_modules and name not in local:
                modules.extend(var_modules[name])
        modules = list(dict.fromkeys(modules))
        assignment = ASSIGN.match(lines[0]) if len(lines) == 1 else None
        if assignment:
            if modules and not whole_stage:
                var_modules[assignment.group(1)] = modules
            else:
                var_modules.pop(assignment.group(1), None)
        command = lines[0].split()[0]
        if not modules or whole_stage:
            targets = [GLOBAL]
        elif (command == "cp" and len(lines) == 1 and len(direct) > 1 and modules == direct
              and not re.search(r"\s(?:-t|--target-directory)\b", lines[0])):
            destination = [m.group(1) for m in STAGE_REF.finditer(unit)][-1]
            targets = [destination]
            edges.update((source, destination) for source in direct if source != destination)
        elif command == "touch" and len(lines) == 1:
            targets = modules
        else:
            targets = modules
            edges.update((a, b) for a in modules for b in modules if a != b)
        entries = [("unit", unit)]
        entries += [("patch", app["path"]) for line in lines if PATCH_COMMAND.match(line)
                    for app in applications(line)]
        entries += [("file", path) for path in ROOT_REF.findall(unit) if not path.startswith(NOT_ROOT_INPUTS)]
        entries += [("upstream", path.strip("/")) for path in UPSTREAM_REF.findall(unit)]
        for target in targets:
            scopes[target].extend(entries)
    return scopes, edges


def tool_versions() -> dict:
    """GNU patch defines the staged bytes.  The Python steps (blank-line trim,
    sampler restore) are version-independent, and recording the interpreter
    would thrash the stamp between login and non-login shells."""
    try:
        result = subprocess.run(["patch", "--version"], capture_output=True, text=True, check=False)
        patch_version = (result.stdout.splitlines() or ["unknown"])[0]
    except OSError:
        patch_version = "unavailable"
    return {"patch": patch_version}


def compute_inputs(root, upstream=None, tools=None) -> dict:
    root = Path(root)
    text = (root / SCRIPT).read_text(encoding="utf-8")
    managed = managed_dirs(text)
    upstream = Path(upstream) if upstream else root / "upstream/CnC_Renegade"
    payloads: dict[str, bytes] = {}

    def payload(relative: str) -> bytes:
        if relative not in payloads:
            payloads[relative] = (root / relative).read_bytes()
        return payloads[relative]

    applied: list[dict] = []
    scopes, edges = analyse(
        text, managed, lambda path: patch_modules(payload(path).decode("utf-8", "replace"), managed), applied)
    cache: dict[tuple[str, str], str] = {}

    def entry_row(kind: str, value: str) -> list[str]:
        if kind == "unit":
            return [kind, value.strip().split("\n")[0][:96], sha256(value.encode("utf-8"))]
        if (kind, value) not in cache:
            if kind == "patch":
                cache[(kind, value)] = sha256(payload(value))
            else:
                cache[(kind, value)] = digest_path((upstream if kind == "upstream" else root) / value)
        return [kind, value, cache[(kind, value)]]

    tools = dict(tools) if tools is not None else tool_versions()
    rows = {scope: [entry_row(*entry) for entry in entries] for scope, entries in scopes.items()}
    rows[GLOBAL].append(["tools", "versions", digest_json(tools)])
    modules = {name: {"sha256": digest_json(rows[name]), "entries": rows[name]} for name in managed}
    patches = [[app["path"], app["directory"], sha256(payload(app["path"]))] for app in applied]
    inputs = {
        "schema": SCHEMA,
        "managed": managed,
        "script_sha256": sha256(text.encode("utf-8")),
        "patch_order_sha256": digest_json(patches),
        "global_sha256": digest_json(rows[GLOBAL]),
        "global_entries": rows[GLOBAL],
        "modules": modules,
        "edges": sorted([list(edge) for edge in edges]),
        "tools": tools,
    }
    inputs["input_sha256"] = digest_json({key: inputs[key] for key in (
        "schema", "managed", "script_sha256", "patch_order_sha256", "global_sha256", "edges")}
        | {"modules": {name: modules[name]["sha256"] for name in managed}})
    return inputs


def compute_outputs(root, managed) -> dict:
    stage = Path(root) / "staging"
    files, prefix = {}, len(str(stage)) + 1
    for name in managed:
        base = stage / name
        if not base.is_dir():
            files[name + "/"] = "missing"
            continue
        for directory, subdirs, names in os.walk(str(base)):
            subdirs.sort()
            for item_name in names:
                item = os.path.join(directory, item_name)
                relative = item[prefix:].replace(os.sep, "/")
                if os.path.islink(item):
                    files[relative] = "symlink:" + os.readlink(item)
                else:
                    files[relative] = f"{os.stat(item).st_mode & 0o777:o}:{sha256(_read(item))}"
    receipt = stage / "PATCH_INVENTORY.json"
    files["PATCH_INVENTORY.json"] = sha256(receipt.read_bytes()) if receipt.is_file() else "missing"
    return {"sha256": digest_json(files), "count": len(files), "files": files}


def describe(old: dict | None, new: dict | None) -> str:
    if old is None or new is None:
        return "module added" if old is None else "module removed"
    old_inputs = {(row[0], row[1]): row[2] for row in old["entries"] if row[0] != "unit"}
    new_inputs = {(row[0], row[1]): row[2] for row in new["entries"] if row[0] != "unit"}
    notes = [f"{key[0]} added {key[1]}" for key in new_inputs if key not in old_inputs]
    notes += [f"{key[0]} removed {key[1]}" for key in old_inputs if key not in new_inputs]
    notes += [f"{key[0]} changed {key[1]}" for key in new_inputs
              if key in old_inputs and old_inputs[key] != new_inputs[key]]
    if not notes:
        same_set = sorted(map(tuple, old["entries"])) == sorted(map(tuple, new["entries"]))
        notes.append("patch/unit order changed" if same_set else "script unit changed")
    return "; ".join(notes[:6]) + (f" (+{len(notes) - 6} more)" if len(notes) > 6 else "")


def plan(old: dict, new: dict) -> dict:
    """Dirty-module closure between a stamped and a current input fingerprint."""
    managed = new["managed"]
    if old.get("managed") != managed:
        return {"dirty": list(managed), "reasons": {GLOBAL: "managed staging directory list changed"}}
    if old.get("global_sha256") != new["global_sha256"]:
        why = describe({"entries": old.get("global_entries", [])}, {"entries": new["global_entries"]})
        return {"dirty": list(managed), "reasons": {GLOBAL: why}}
    reasons = {}
    for name in managed:
        before, after = old["modules"].get(name), new["modules"].get(name)
        if before is None or before["sha256"] != after["sha256"]:
            reasons[name] = describe(before, after)
    edges = {tuple(edge) for edge in old.get("edges", [])} | {tuple(edge) for edge in new["edges"]}
    dirty, frontier = set(reasons), list(reasons)
    while frontier:
        source = frontier.pop()
        for edge_source, destination in sorted(edges):
            if edge_source == source and destination not in dirty:
                dirty.add(destination)
                reasons[destination] = f"reads {source}"
                frontier.append(destination)
    return {"dirty": [name for name in managed if name in dirty], "reasons": reasons}


def _load(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == SCHEMA else None


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def check(root, upstream=None, tools=None, stamp_path=None) -> tuple[int, dict]:
    """0 = fresh (skip is byte-identical), 1 = stale, 2 = no usable stamp."""
    root = Path(root)
    stamp = _load(Path(stamp_path) if stamp_path else root / STAMP)
    if stamp is None:
        return 2, {"status": "ABSENT", "detail": f"no usable {STAMP}; a full staging run records one"}
    current = compute_inputs(root, upstream, tools)
    if current["input_sha256"] != stamp["inputs"]["input_sha256"]:
        result = plan(stamp["inputs"], current)
        return 1, {"status": "STALE_INPUTS", **result}
    outputs = compute_outputs(root, current["managed"])
    if outputs["sha256"] != stamp["outputs"]["sha256"]:
        old, new = stamp["outputs"]["files"], outputs["files"]
        changed = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
        modules = sorted({key.split("/", 1)[0] for key in changed if "/" in key})
        return 1, {"status": "STALE_OUTPUTS", "changed_count": len(changed),
                   "changed": changed[:20], "dirty": modules}
    return 0, {"status": "FRESH", "input_sha256": current["input_sha256"], "files": outputs["count"]}


def begin(root, upstream=None, tools=None) -> dict:
    root = Path(root)
    (root / STAMP).unlink(missing_ok=True)
    inputs = compute_inputs(root, upstream, tools)
    _write(root / PENDING, {"schema": SCHEMA, "inputs": inputs})
    return inputs


def record(root, upstream=None, tools=None) -> tuple[int, dict]:
    root = Path(root)
    pending = _load(root / PENDING)
    current = compute_inputs(root, upstream, tools)
    if pending is None:
        return 1, {"status": "NOT_RECORDED", "detail": "no pending fingerprint; staging did not run begin"}
    if pending["inputs"]["input_sha256"] != current["input_sha256"]:
        return 1, {"status": "NOT_RECORDED", "detail": "staging inputs changed while staging ran",
                   **plan(pending["inputs"], current)}
    outputs = compute_outputs(root, current["managed"])
    _write(root / STAMP, {"schema": SCHEMA, "inputs": current, "outputs": outputs})
    (root / PENDING).unlink(missing_ok=True)
    return 0, {"status": "RECORDED", "input_sha256": current["input_sha256"], "files": outputs["count"]}


def summary(result: dict) -> str:
    text = f"Staging fingerprint {result['status']}"
    if result.get("dirty") is not None:
        text += ": dirty modules " + (", ".join(result["dirty"]) or "none (registry order/inert text only)")
    if result.get("reasons"):
        text += " | " + "; ".join(f"{name}: {why}" for name, why in result["reasons"].items())
    if result.get("changed"):
        text += f" | {result['changed_count']} staged file(s) differ, e.g. {', '.join(result['changed'][:3])}"
    for key in ("files", "detail"):
        if result.get(key) is not None:
            text += f" | {key}: {result[key]}"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--upstream", type=Path, help="default: <root>/upstream/CnC_Renegade")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("command", choices=("check", "begin", "record", "invalidate", "plan"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "check":
        code, result = check(root, args.upstream)
    elif args.command == "begin":
        begin(root, args.upstream)
        code, result = 0, {"status": "BEGUN"}
    elif args.command == "record":
        code, result = record(root, args.upstream)
    elif args.command == "invalidate":
        (root / STAMP).unlink(missing_ok=True)
        code, result = 0, {"status": "INVALIDATED"}
    else:
        inputs = compute_inputs(root, args.upstream)
        stamp = _load(root / STAMP)
        result = {"status": "PLAN", "input_sha256": inputs["input_sha256"],
                  "modules": {name: {"sha256": value["sha256"],
                                     "patches": sum(row[0] == "patch" for row in value["entries"]),
                                     "units": sum(row[0] == "unit" for row in value["entries"])}
                              for name, value in inputs["modules"].items()},
                  "global_units": sum(row[0] == "unit" for row in inputs["global_entries"]),
                  "edges": inputs["edges"]}
        if stamp is not None:
            result.update(plan(stamp["inputs"], inputs))
        code = 0
    print(json.dumps(result, indent=1, sort_keys=True) if args.json or args.command == "plan" else summary(result))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Staging fingerprint ERROR: {error}", file=sys.stderr)
        sys.exit(2)
