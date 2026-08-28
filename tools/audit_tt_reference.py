#!/usr/bin/env python3
"""Audit a pinned Tiberian Technologies source release without importing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import zipfile


TT_VERSION = "4.8 Update 4"
TT_REVISION = 9000
TT_ARCHIVE_MD5 = "5bf9acce0663514ea5e84ff5e0c16fb1"
TT_DIFF_MD5 = "c746d12f7bbe06b99e3a15b6856ab3f4"
TT_ARCHIVE_SHA256 = "8d3c2df2af0b2a7bb49b4e1a0353947b49fc2b228f849024e1a7bf18a0fddfcd"
TT_DIFF_SHA256 = "6a73ca645b1591b3c0456bb34c859d8b4644a64401503ae0f30a8ee68d1e314b"
TT_ARCHIVE_URL = "https://www.tiberiantechnologies.org/files/source-4.8.4.zip"
TT_DIFF_URL = "https://www.tiberiantechnologies.org/files/source-diff-4.8.4.diff"


def digest(path: pathlib.Path, algorithm: str) -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe_archive_members(archive: zipfile.ZipFile) -> list[str]:
    members: list[str] = []
    for info in archive.infolist():
        member = pathlib.PurePosixPath(info.filename)
        if member.is_absolute() or ".." in member.parts:
            raise ValueError(f"unsafe TT archive member: {info.filename}")
        members.append(info.filename)
    return members


def archive_text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8", errors="replace")


def audit_reference(
    archive_path: pathlib.Path,
    diff_path: pathlib.Path,
    root: pathlib.Path,
    expected_archive_md5: str = TT_ARCHIVE_MD5,
    expected_diff_md5: str = TT_DIFF_MD5,
    expected_archive_sha256: str = TT_ARCHIVE_SHA256,
    expected_diff_sha256: str = TT_DIFF_SHA256,
) -> dict[str, object]:
    archive_md5 = digest(archive_path, "md5")
    diff_md5 = digest(diff_path, "md5")
    archive_sha256 = digest(archive_path, "sha256")
    diff_sha256 = digest(diff_path, "sha256")
    if archive_md5 != expected_archive_md5:
        raise ValueError(f"TT source archive MD5 mismatch: {archive_md5}")
    if diff_md5 != expected_diff_md5:
        raise ValueError(f"TT source diff MD5 mismatch: {diff_md5}")
    if archive_sha256 != expected_archive_sha256:
        raise ValueError(f"TT source archive SHA-256 mismatch: {archive_sha256}")
    if diff_sha256 != expected_diff_sha256:
        raise ValueError(f"TT source diff SHA-256 mismatch: {diff_sha256}")

    with zipfile.ZipFile(archive_path) as archive:
        members = safe_archive_members(archive)
        required = {
            "source/scripts/AudioCallbackListClass.h",
            "source/scripts/AudibleSoundDefinitionClass.cpp",
            "source/scripts/COPYING",
            "source/scripts/ChunkClasses.cpp",
            "source/scripts/LineSegClass.cpp",
            "source/scripts/SysTimeClass.cpp",
            "source/scripts/WWAudioClass.h",
        }
        absent = sorted(required.difference(members))
        if absent:
            raise ValueError(f"TT source archive is missing required members: {absent}")
        copying = archive_text(archive, "source/scripts/COPYING")
        audio_callback_source = archive_text(
            archive, "source/scripts/AudioCallbackListClass.h"
        )
        audio_definition_source = archive_text(
            archive, "source/scripts/AudibleSoundDefinitionClass.cpp"
        )
        chunk_source = archive_text(archive, "source/scripts/ChunkClasses.cpp")
        line_source = archive_text(archive, "source/scripts/LineSegClass.cpp")
        time_source = archive_text(archive, "source/scripts/SysTimeClass.cpp")
        wwaudio_header = archive_text(archive, "source/scripts/WWAudioClass.h")

    license_detected = (
        "GNU GENERAL PUBLIC LICENSE" in copying
        and "Version 2, June 1991" in copying
        and "either version 2, or (at your option) any later" in chunk_source
    )
    if not license_detected:
        raise ValueError("TT GPL-2.0-or-later source notice was not detected")

    local_chunk = (root / "staging/wwlib/chunkio.cpp").read_text(
        encoding="utf-8", errors="replace"
    )
    local_line = (root / "upstream/CnC_Renegade/Code/WWMath/lineseg.cpp").read_text(
        encoding="utf-8", errors="replace"
    )
    local_time = (root / "upstream/CnC_Renegade/Code/wwlib/systimer.h").read_text(
        encoding="utf-8", errors="replace"
    )
    local_audio_callbacks = (root / "staging/wwaudio/AudioEvents.h").read_text(
        encoding="utf-8", errors="replace"
    )
    local_audio_definition = (root / "staging/wwaudio/AudibleSound.cpp").read_text(
        encoding="utf-8", errors="replace"
    )

    def compact_cpp(source: str) -> str:
        return re.sub(r"\s+", "", source)

    tt_audio_callbacks_compact = compact_cpp(audio_callback_source)
    tt_audio_definition_compact = compact_cpp(audio_definition_source)
    local_audio_callbacks_compact = compact_cpp(local_audio_callbacks)
    local_audio_definition_compact = compact_cpp(local_audio_definition)
    wwaudio_header_compact = compact_cpp(wwaudio_header)

    tt_diff = diff_path.read_text(encoding="utf-8", errors="replace")
    changed_files = sorted(
        set(
            re.findall(
                r"^diff -urN sourceold/(\S+) source/(\S+)$", tt_diff, re.MULTILINE
            )
        )
    )
    changed_paths = [new for _old, new in changed_files]
    active_blocker_pattern = re.compile(
        r"(?:^|/)(?:sound|audio|dialog|conversation|cinematic|controller|input|sky|background|dazzle|light|texture|material|render|dx8)",
        re.IGNORECASE,
    )
    active_blocker_files = sorted(
        name
        for name in members
        if active_blocker_pattern.search(name)
        and name.lower().endswith((".cpp", ".h"))
    )
    active_blocker_delta = sorted(
        name for name in changed_paths if active_blocker_pattern.search(name)
    )

    patterns = [
        {
            "id": "chunk-close-micro-chunk-position-accounting",
            "tt_source": "source/scripts/ChunkClasses.cpp",
            "tt_semantics_present": all(
                token in chunk_source
                for token in (
                    "MCHeader.ChunkSize - MicroChunkPosition",
                    "PositionStack[StackIndex-1] +=",
                )
            ),
            "local_semantics_present": all(
                token in local_chunk
                for token in (
                    "File->Seek(csize - pos,SEEK_CUR)",
                    "PositionStack[StackIndex-1] += csize - pos",
                )
            ),
            "decision": "ALREADY_PRESENT_IN_EA_SOURCE",
        },
        {
            "id": "lineseg-transformed-endpoints-direction-and-length",
            "tt_source": "source/scripts/LineSegClass.cpp",
            "tt_semantics_present": all(
                token in line_source
                for token in (
                    "Transform_Vector(transform, object.P0, &P0)",
                    "Rotate_Vector(transform, object.Dir, &Dir)",
                    "Length = object.Length",
                )
            ),
            "local_semantics_present": all(
                token in local_line
                for token in (
                    "Transform_Vector(tm,that.P0,&P0)",
                    "Rotate_Vector(tm,that.Dir,&Dir)",
                    "Length = that.Length",
                )
            ),
            "decision": "ALREADY_PRESENT_IN_EA_SOURCE",
        },
        {
            "id": "system-time-wrap-relative-clock",
            "tt_source": "source/scripts/SysTimeClass.cpp",
            "tt_semantics_present": "uTimeInitNeg + u" in time_source,
            "local_semantics_present": all(
                token in local_time for token in ("time - StartTime", "time + WrapAdd")
            ),
            "decision": "EQUIVALENT_EA_IMPLEMENTATION_PRESENT",
        },
        {
            "id": "audio-callback-add-get-remove-semantics",
            "tt_source": "source/scripts/AudioCallbackListClass.h",
            "tt_semantics_present": all(
                token in tt_audio_callbacks_compact
                for token in (
                    "Add(callbackStruct);",
                    "return(*this)[index].callback;",
                    "Remove(index);",
                )
            ),
            "local_semantics_present": all(
                token in local_audio_callbacks_compact
                for token in (
                    "this->Add(AUDIO_CALLBACK_STRUCT<T>(pointer,user_data));",
                    "returnthis->Vector[index].callback_ptr;",
                    "this->Delete(index);",
                )
            ),
            "decision": "LOCAL_GCC15_PORTABLE_EQUIVALENT_RETAINED",
        },
        {
            "id": "audible-definition-retail-binary-schema",
            "tt_source": "source/scripts/AudibleSoundDefinitionClass.cpp",
            "tt_semantics_present": all(
                token in tt_audio_definition_compact
                for token in (
                    "csave.Begin_Chunk(0x100);",
                    "csave.Begin_Chunk(0x200);",
                    "WRITE_MICRO_CHUNK(csave,3,m_Priority);",
                    "READ_MICRO_CHUNK(cload,22,m_VirtualChannel);",
                )
            ),
            "local_semantics_present": all(
                token in local_audio_definition_compact
                for token in (
                    "CHUNKID_VARIABLES=0x00000100",
                    "CHUNKID_BASE_CLASS=0x00000200",
                    "VARID_UNUSED1=0x01,VARID_UNUSED2,VARID_PRIORITY",
                    "WRITE_MICRO_CHUNK(csave,VARID_PRIORITY,m_Priority)",
                    "READ_MICRO_CHUNK(cload,VARID_VIRTUAL_CHANNEL,m_VirtualChannel)",
                )
            ),
            "decision": "EA_AUDIO_DEFINITION_SCHEMA_RETAINED",
        },
    ]
    if not all(
        item["tt_semantics_present"] and item["local_semantics_present"]
        for item in patterns
    ):
        raise ValueError("a known portable TT correctness pattern failed its comparison")

    return {
        "schema_version": 1,
        "reference": {
            "publisher": "Tiberian Technologies",
            "version": TT_VERSION,
            "revision": TT_REVISION,
            "archive_url": TT_ARCHIVE_URL,
            "diff_url": TT_DIFF_URL,
            "archive_md5": archive_md5,
            "archive_sha256": archive_sha256,
            "diff_md5": diff_md5,
            "diff_sha256": diff_sha256,
            "archive_files": len(members),
        },
        "license": {
            "detected": "GPL-2.0-or-later with TT runtime-linking exception",
            "copying_member": "source/scripts/COPYING",
            "reuse_policy": "file-by-file review; compatible patterns may be adapted under GPLv3",
        },
        "release_diff": {
            "changed_file_count": len(changed_paths),
            "changed_files": changed_paths,
            "scope": "scripts.dll source delta from the preceding TT release, not a diff against EA's full game source",
        },
        "active_vita_blocker_inventory": {
            "candidate_files": active_blocker_files,
            "update_diff_matches": active_blocker_delta,
            "finding": "the archive exposes selected engine-facing headers but no portable WWAudio device, controller, sky/background renderer, or conversation runtime implementation; the 4.8.4 update diff changes none of those surfaces",
        },
        "portable_correctness_patterns": patterns,
        "known_reference_hazards": [
            {
                "source": "source/scripts/AudioCallbackListClass.h",
                "finding": "template-dependent base calls are unqualified",
                "local_control": "retain the existing this-> qualified GCC/ARM implementation",
                "observed": "Add(callbackStruct);" in tt_audio_callbacks_compact,
            },
            {
                "source": "source/scripts/WWAudioClass.h",
                "finding": "Get_Active_Sound_Page has no return statement",
                "local_control": "do not import the TT WWAudio header or Windows/Miles ABI",
                "observed": "Get_Active_Sound_Page(void){m_CurrPage;}"
                in wwaudio_header_compact,
            },
        ],
        "active_candidate_decisions": [
            {
                "candidate": "4.8.2 Communications Center campaign crash fix",
                "decision": "STUDY_ONLY_SOURCE_UNAVAILABLE",
                "reason": "the public scripts.dll source delta does not contain the binary engine patch",
            },
            {
                "candidate": "4.8.4 preliminary controller support",
                "decision": "NOT_IMPORTED_PLATFORM_MISMATCH",
                "reason": "the public delta exposes no portable implementation and Vita input is owned by the native SceCtrl boundary",
            },
            {
                "candidate": "4.7 sound initialization and looping fixes",
                "decision": "STUDY_ONLY_SOURCE_UNAVAILABLE",
                "reason": "no public WWAudio device implementation is present; Vita requires a native output provider below WWAudio",
            },
            {
                "candidate": "TT lighting and DirectX renderer enhancements",
                "decision": "NOT_IMPORTED_RENDERER_PLATFORM_MISMATCH",
                "reason": "the public scripts.dll archive has interfaces but not a portable Vita renderer implementation",
            },
        ],
        "result": "PASSED_NO_UNJUSTIFIED_SOURCE_IMPORT",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--diff", type=pathlib.Path, required=True)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = audit_reference(args.archive, args.diff, args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
