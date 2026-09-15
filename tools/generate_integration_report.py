#!/usr/bin/env python3
import argparse
import collections
import json
import pathlib
import re
import shlex
import subprocess

if __package__:
    from .renegade_patch_inventory import load_inventory, require_staging_receipt
else:
    from renegade_patch_inventory import load_inventory, require_staging_receipt

MODULES = [
    "WWMath", "wwbitpack", "wwdebug", "wwlib", "wwsaveload",
    "wwtranslatedb", "wwutil", "wwphys", "ww3d2", "Combat",
    "Commando", "Scripts", "WWAudio", "WWOnline", "wolapi",
]

STAGED_ORIGINAL_OWNER_SOURCES = {
    "Code/Commando/loadingscreen.cpp": "staging/commando/loadingscreen.cpp",
}

STAGED_TO_UPSTREAM_MODULE = {
    "combat": "Combat",
    "commando": "Commando",
    "wwaudio": "WWAudio",
    "wwmath": "WWMath",
}

def read_native_source_sets(root: pathlib.Path) -> dict[str, list[str]]:
    """Read the literal native source sets, not a second maintained inventory."""
    text = re.sub(r"(?m)#.*$", "", (root / "CMakeLists.txt").read_text(encoding="utf-8"))
    result = {}
    for name in ("RENEGADE_A30_PORT_SOURCES", "RENEGADE_A4_FRONTEND_PORT_SOURCES"):
        definitions = [body for body in re.findall(
            r"\bset\s*\(\s*" + name + r"\b([^)]*)\)", text, re.IGNORECASE
        ) if body.strip()]
        if len(definitions) != 1:
            raise RuntimeError(f"Expected one nonempty literal CMake definition for {name}")
        sources = []
        for token in shlex.split(definitions[0], comments=True):
            match = re.fullmatch(r"\$\{RENEGADE_ROOT\}/(port/[A-Za-z0-9_./-]+\.(?:c|cpp))", token, re.IGNORECASE)
            if match is None or ".." in pathlib.PurePosixPath(match[1]).parts:
                raise RuntimeError(f"Unsupported native source token in {name}: {token}")
            source = match[1]
            if source in sources:
                raise RuntimeError(f"Duplicate native source in {name}: {source}")
            sources.append(source)
        if not sources:
            raise RuntimeError(f"Empty native source inventory: {name}")
        result[name] = sources
    return result


def source_count(directory: pathlib.Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(
        1 for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".c", ".cpp"}
    )


def read_world_manifest(root: pathlib.Path) -> list[str]:
    manifests = [
        root / "cmake" / "A22OriginalSources.cmake",
        root / "cmake" / "A30OriginalSources.cmake",
        root / "cmake" / "A31OriginalSources.cmake",
        root / "CMakeLists.txt",
    ]
    pattern = re.compile(
        r"\$\{RENEGADE_STAGE\}/([A-Za-z0-9_]+)/([^\s)\"#]+\.cpp)", re.IGNORECASE
    )
    entries: list[str] = []
    for manifest in manifests:
        text = re.sub(r"(?m)#.*$", "", manifest.read_text(encoding="utf-8"))
        for staged_module, filename in pattern.findall(
                text):
            upstream_module = STAGED_TO_UPSTREAM_MODULE.get(
                staged_module, staged_module
            )
            entries.append(f"Code/{upstream_module}/{filename}")
        for filename in re.findall(
                r"\$\{RENEGADE_SCRIPT_SOURCE\}/([^\s\)\"#]+\.cpp)",
                text, re.IGNORECASE):
            entries.append(f"Code/Scripts/{filename}")
    entries = sorted(set(entries) - set(STAGED_ORIGINAL_OWNER_SOURCES))
    if not entries:
        raise RuntimeError("Original source manifests contain no translation units")
    return entries


def read_patched_sources(root: pathlib.Path, upstream: pathlib.Path):
    inventory = load_inventory(root)
    require_staging_receipt(root, inventory)
    patches = [root / entry["path"] for entry in inventory["patches"]]

    patched_sources: set[str] = set()
    patch_report = []
    for patch, identity in zip(patches, inventory["patches"]):
        targets = []
        for line in patch.read_text(encoding="utf-8").splitlines():
            if not line.startswith("--- a/"):
                continue
            relative = line[len("--- a/"):]
            if relative not in targets:
                targets.append(relative)
        patch_report.append({
            "path": patch.relative_to(root).as_posix(),
            "stage_directory": identity["stage_directory"],
            "sha256": identity["sha256"],
            "application": (
                "generated staging only; patch --batch --forward --fuzz=0 "
                "--no-backup-if-mismatch"
            ),
            "upstream_targets": targets,
        })
        # Patch paths are relative to their staged module roots. Preserve the
        # exact upstream filenames when they can be uniquely located; the
        # report's aggregate intentionally counts unique files, not hunks.
        stem_module = patch.name.split("-", 1)[0]
        upstream_module = STAGED_TO_UPSTREAM_MODULE.get(stem_module, stem_module)
        for relative in targets:
            candidate = upstream / "Code" / upstream_module / relative
            if candidate.is_file():
                patched_sources.add(candidate.relative_to(upstream).as_posix())
            else:
                patched_sources.add(f"patch-target/{patch.name}/{relative}")
    return patches, patched_sources, patch_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--milestone", default="A3.5-dev5")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    upstream = root / "upstream" / "CnC_Renegade"
    code = upstream / "Code"
    all_sources = sorted(
        path for path in code.rglob("*")
        if path.is_file() and path.suffix.lower() in {".c", ".cpp"}
    )
    revision = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()

    original_translation_units = read_world_manifest(root)
    for relative_path in original_translation_units:
        if not (upstream / relative_path).is_file():
            raise RuntimeError(
                f"Manifest references missing upstream source: {relative_path}"
            )
    native_sets = read_native_source_sets(root)
    vita_port_sources = native_sets["RENEGADE_A30_PORT_SOURCES"]
    frontend_port_sources = native_sets["RENEGADE_A4_FRONTEND_PORT_SOURCES"]
    for relative_path in vita_port_sources:
        if not (root / relative_path).is_file():
            raise RuntimeError(
                f"Native A3.1 manifest references missing file: {relative_path}"
            )
    for relative_path in frontend_port_sources:
        if not (root / relative_path).is_file():
            raise RuntimeError(
                f"Native A4 frontend manifest references missing file: {relative_path}"
            )
    staged_original_owner_sources = []
    for staged_path in STAGED_ORIGINAL_OWNER_SOURCES.values():
        if not (root / staged_path).is_file():
            raise RuntimeError(
                f"Staged original owner source is missing: {staged_path}"
            )
        staged_original_owner_sources.append(staged_path)

    patches, patched_sources, patch_report = read_patched_sources(root, upstream)
    module_compiled = collections.Counter(
        pathlib.PurePosixPath(path).parts[1]
        for path in original_translation_units
    )
    module_totals = {name: source_count(code / name) for name in MODULES}
    module_status = {
        name: {
            "status": "integrated-a3-world-runtime" if module_compiled[name]
            else "deferred-or-external-boundary",
            "compiled": module_compiled[name],
            "total": module_totals[name],
        }
        for name in MODULES
    }
    module_status["WWAudio"]["status"] = (
        "original-runtime-over-vita-native-miles-compatible-provider"
    )
    module_status["Scripts"]["status"] = "native-static-m00-provider-with-direct-dependencies"
    module_status["WWOnline"]["status"] = "excluded-initially"
    module_status["wolapi"]["status"] = "excluded-initially"

    compatibility_headers = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "port" / "compatibility" / "include").glob("*.h")
    )
    report = {
        "milestone": args.milestone,
        "objective": (
            "First authentic M00 tutorial runtime; current source seed "
            "preserves accepted A3.0/Combat ownership, links the original "
            "Mission00 provider and its direct dependencies, promotes the "
            "original CombatGameMode post-load finalization owner, and retains "
            "original WWAudio ownership over a Vita-native output boundary"
        ),
        "canonical_upstream": "https://github.com/electronicarts/CnC_Renegade",
        "upstream_revision": revision,
        "original_source_manifest": "cmake/A31OriginalSources.cmake",
        "original_source_files_discovered": len(all_sources),
        "original_source_files_compiled": len(original_translation_units),
        "original_translation_units": original_translation_units,
        "staged_original_owner_files": len(staged_original_owner_sources),
        "staged_original_owner_paths": sorted(staged_original_owner_sources),
        "vita_platform_renderer_validation_files": len(vita_port_sources),
        "vita_translation_units": vita_port_sources,
        "a4_frontend_boundary_files": len(frontend_port_sources),
        "a4_frontend_boundary_paths": frontend_port_sources,
        "sdk_framebuffer_helper_files": 1,
        "compatibility_headers": len(compatibility_headers),
        "compatibility_header_paths": compatibility_headers,
        "patch_count": len(patches),
        "mechanically_patched_upstream_files": len(patched_sources),
        "mechanically_patched_upstream_paths": sorted(patched_sources),
        "patches": patch_report,
        "upstream_files_modified_in_place": 0,
        "custom_asset_formats": 0,
        "custom_runtime_mix_parser": False,
        "original_archive_runtime": "FileFactoryListClass/MixFileFactoryClass",
        "original_world_runtime": (
            "SaveLoadSystem/DefinitionMgr/WWPhys/PhysicsScene/M00_Tutorial.lsd"
        ),
        "renderer_boundary": {
            "backend": "vitaGL beneath original DX8Wrapper/WW3D",
            "render_to_texture": "explicit unsupported boundary; projectors disabled",
            "original_entry_path": (
                "PhysicsScene -> Camera -> WW3D -> Scene/RenderObj/Mesh"
            ),
            "custom_replacement_scene_graph": False,
        },
        "module_status": module_status,
        "runtime_filesystem_contract": {
            "retail_root": "ux0:data/renegade/retail/",
            "writable_root": "ux0:data/renegade/user/",
            "retail_tree_packaged_in_vpk": False,
        },
        "frontend_runtime_contract": {
            "owner": "original Commando MovieGameMode/MenuGameMode/RenegadeDialogMgr/WWUI",
            "menu_to_tutorial": "A4 menu selection latches original GameInitMgrClass::Start_Game and re-enters the existing direct M00 route until full menu-to-combat equivalence is proven",
            "movie_provider": "BINKMovie uses a pinned Vita FFmpeg software provider for unchanged retail Bink video/audio; no proprietary RAD code or packaged movies",
            "custom_game_loop": False,
            "custom_frontend_renderer": False,
        },
        "automatic_vita_deployment": False,
    }
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
