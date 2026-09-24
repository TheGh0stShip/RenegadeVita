#!/usr/bin/env python3
"""Restore sampled Post_Think instrumentation after legacy preservation staging."""

import sys
from pathlib import Path


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise SystemExit("Post_Think sampler restore refused: expected source fragment is not unique")
    return text.replace(before, after, 1)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: restore_postthink_sampler.py <staged gameobjmanager.cpp>")
    path = Path(sys.argv[1])
    source = path.read_text(encoding="utf-8")
    start = source.index("int\tGameObjManager::Post_Think()")
    end = source.index("\n}", start)
    body = source[start:end]

    body = replace_once(
        body,
        '\tunsigned vita_object_count = 0U;\n',
        '\tunsigned vita_object_count = 0U;\n'
        '\tunsigned vita_sampled_object_count = 0U;\n'
        '\tstatic unsigned vita_sample_phase = 0U;\n'
        '\tconst unsigned vita_sample_offset = vita_sample_phase++ & 15U;\n',
    )
    body = replace_once(
        body,
        '\t\t\tconst uint64_t vita_object_start_us = sceKernelGetProcessTimeWide();\n'
        '\t\t\tconst int vita_object_id = objnode->Data()->Get_ID();\n'
        '\t\t\tconst char *vita_object_name = objnode->Data()->Get_Definition().Get_Name();',
        '\t\t\tconst bool vita_sample_object = (vita_object_count++ & 15U) == vita_sample_offset;\n'
        '\t\t\tconst uint64_t vita_object_start_us = vita_sample_object ? sceKernelGetProcessTimeWide() : 0U;\n'
        '\t\t\tconst int vita_object_id = vita_sample_object ? objnode->Data()->Get_ID() : 0;\n'
        '\t\t\tconst char *vita_object_name = vita_sample_object ? objnode->Data()->Get_Definition().Get_Name() : "";',
    )
    body = replace_once(
        body,
        '\t\t\tobjnode->Data()->Post_Think();\n'
        '#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO\n'
        '\t\t\tconst uint64_t vita_object_us = sceKernelGetProcessTimeWide() - vita_object_start_us;',
        '\t\t\tobjnode->Data()->Post_Think();\n'
        '#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO\n'
        '\t\t\tif (vita_sample_object) {\n'
        '\t\t\tconst uint64_t vita_object_us = sceKernelGetProcessTimeWide() - vita_object_start_us;',
    )
    body = replace_once(
        body,
        '\t\t\t}\n'
        '#endif\n'
        '\t\t}',
        '\t\t\t}\n'
        '\t\t\t}\n'
        '#endif\n'
        '\t\t}',
    )
    body = replace_once(
        body,
        '\t\t\t++vita_object_count;\n',
        '\t\t\t++vita_sampled_object_count;\n',
    )
    body = replace_once(
        body,
        'count=%u top0=%llu/%d/%s',
        'count=%u sampled=%u stride=16 top0=%llu/%d/%s',
    )
    body = replace_once(
        body,
        '\t\t\tvita_object_count,\n',
        '\t\t\tvita_object_count,\n'
        '\t\t\tvita_sampled_object_count,\n',
    )
    source = source[:start] + body + source[end:]
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
