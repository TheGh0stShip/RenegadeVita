#!/usr/bin/env python3
import argparse
import collections
import json
import pathlib
import re
import subprocess


MODULES = [
    "WWMath", "wwbitpack", "wwdebug", "wwlib", "wwsaveload",
    "wwtranslatedb", "wwutil", "wwphys", "ww3d2", "Combat",
    "Commando", "Scripts", "WWAudio", "WWOnline", "wolapi",
]

EXPECTED_ORIGINAL_SOURCE_COUNT = 447
EXPECTED_VITA_PORT_SOURCE_COUNT = 26
EXPECTED_PATCH_COUNT = 113

STAGED_TO_UPSTREAM_MODULE = {
    "combat": "Combat",
    "commando": "Commando",
    "wwaudio": "WWAudio",
    "wwmath": "WWMath",
}

VITA_PORT_SOURCES = [
    "port/developer/a31_capture_telemetry.cpp",
	"port/audio/vita/renegade_miles_provider.cpp",
	"port/audio/vita/renegade_wave_decoder.cpp",
	"port/filesystem/renegade_cache_health.cpp",
    "port/filesystem/renegade_paths.cpp",
    "port/filesystem/renegade_file_factory.cpp",
    "port/filesystem/renegade_registry.cpp",
    "port/platform/renegade_directinput.cpp",
    "port/platform/renegade_optional_services.cpp",
	"port/platform/renegade_network_provider.cpp",
    "port/renderer/vita/ww3d_vita_renderer.cpp",
    "port/renderer/vita/ww3d_dx8_boundary.cpp",
    "port/renderer/vita/surface_boundary.cpp",
	"port/renderer/vita/renegade_freetype_font_provider.cpp",
    "port/validation/wwbitpack_selftest.cpp",
    "port/validation/a21_filesystem_selftest.cpp",
    "port/validation/a22_w3d_selftest.cpp",
    "port/validation/a30_world_runtime.cpp",
    "port/platform/vita/vita_platform.cpp",
    "port/platform/vita/a30_vita_runtime.cpp",
    "port/platform/a31_gameplay_boundary.cpp",
	"port/platform/a31_miscutil_boundary.cpp",
	"port/platform/a31_network_options_boundary.cpp",
	"port/platform/renegade_script_static_provider.cpp",
    "port/platform/vita/a30_main.cpp",
	"port/platform/vita/a31_vita_runtime.cpp",
]


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
        r"\$\{RENEGADE_STAGE\}/([A-Za-z0-9_]+)/([^\s)#]+\.cpp)"
    )
    entries: list[str] = []
    for manifest in manifests:
        for staged_module, filename in pattern.findall(
                manifest.read_text(encoding="utf-8")):
            upstream_module = STAGED_TO_UPSTREAM_MODULE.get(
                staged_module, staged_module
            )
            entries.append(f"Code/{upstream_module}/{filename}")
        for filename in re.findall(
                r"\$\{RENEGADE_SCRIPT_SOURCE\}/([^\s\)#]+\.cpp)",
                manifest.read_text(encoding="utf-8")):
            entries.append(f"Code/Scripts/{filename}")
    entries = sorted(set(entries))
    if len(entries) != EXPECTED_ORIGINAL_SOURCE_COUNT:
        raise RuntimeError(
            "A3.1 gameplay seed source manifests contain "
            f"{len(entries)} unique entries; expected "
            f"{EXPECTED_ORIGINAL_SOURCE_COUNT}"
        )
    return entries


def read_patched_sources(root: pathlib.Path, upstream: pathlib.Path):
    # This historical NAT-traversal experiment is retained as evidence but is
    # deliberately not in deterministic staging: A3.2 preserves the accepted
    # local transport and does not reopen public-service/network work.
    retired_patches = {"wwnet-a31-network-posix.patch"}
    patches = sorted(
        patch for patch in (root / "port" / "patches").glob("*.patch")
        if patch.name not in retired_patches
    )
    if len(patches) != EXPECTED_PATCH_COUNT:
        raise RuntimeError(
            f"A3.1 patch set has {len(patches)} entries; expected "
            f"{EXPECTED_PATCH_COUNT}"
        )

    patched_sources: set[str] = set()
    patch_report = []
    for patch in patches:
        targets = []
        for line in patch.read_text(encoding="utf-8").splitlines():
            if not line.startswith("--- a/"):
                continue
            relative = line[len("--- a/"):]
            if relative not in targets:
                targets.append(relative)
        patch_report.append({
            "path": patch.relative_to(root).as_posix(),
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
    if len(VITA_PORT_SOURCES) != EXPECTED_VITA_PORT_SOURCE_COUNT:
        raise RuntimeError("Internal A3.1 native port source count is inconsistent")
    for relative_path in VITA_PORT_SOURCES:
        if not (root / relative_path).is_file():
            raise RuntimeError(
                f"Native A3.1 manifest references missing file: {relative_path}"
            )

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
            "Mission00 provider and its direct dependencies, and retains "
            "original WWAudio ownership over a Vita-native output boundary"
        ),
        "canonical_upstream": "https://github.com/electronicarts/CnC_Renegade",
        "upstream_revision": revision,
        "original_source_manifest": "cmake/A31OriginalSources.cmake",
        "original_source_files_discovered": len(all_sources),
        "original_source_files_compiled": len(original_translation_units),
        "original_translation_units": original_translation_units,
        "vita_platform_renderer_validation_files": len(VITA_PORT_SOURCES),
        "vita_translation_units": VITA_PORT_SOURCES,
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
        "automatic_vita_deployment": False,
    }
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
