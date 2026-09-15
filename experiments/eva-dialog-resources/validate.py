#!/usr/bin/env python3
"""Exercise the isolated resource correction without changing build inputs."""
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "upstream/CnC_Renegade/Code/Commando"


def field(data, offset):
    value = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    if value == 0xffff:
        return struct.unpack_from("<H", data, offset)[0], offset + 2
    words = []
    while value:
        words.append(value)
        value = struct.unpack_from("<H", data, offset)[0]
        offset += 2
    return "".join(map(chr, words)), offset


def decode(data):
    style, _, count, _, _, _, _ = struct.unpack_from("<IIHhhhh", data)
    offset = 18
    _, offset = field(data, offset)
    _, offset = field(data, offset)
    caption, offset = field(data, offset)
    if style & 0x40:
        offset += 2
        _, offset = field(data, offset)
    controls = []
    for _ in range(count):
        offset = (offset + 3) & ~3
        flags, _, x, y, w, h, ident = struct.unpack_from("<IIhhhhH", data, offset)
        offset += 18
        cls, offset = field(data, offset)
        title, offset = field(data, offset)
        extra = struct.unpack_from("<H", data, offset)[0]
        assert extra == 0, "Unexpected creation data"
        offset += 2
        controls.append((ident, cls, (x, y, w, h), flags, title))
    assert (offset + 3) & ~3 == len(data), "Incorrect template length/alignment"
    return caption, controls


def main():
    with tempfile.TemporaryDirectory(prefix="renegade-eva-resource-") as directory:
        work = Path(directory)
        script = work / "tools/generate_wwui_dialog_templates.py"
        script.parent.mkdir()
        shutil.copyfile(ROOT / "tools/generate_wwui_dialog_templates.py", script)
        subprocess.run(
            ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i",
             str(Path(__file__).with_name("generator.patch"))],
            cwd=work, check=True,
        )
        spec = importlib.util.spec_from_file_location("eva_generator", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        macros = module.macros((SOURCE / "resource.h", SOURCE / "dialogresource.h"))
        templates = module.parse(SOURCE / "chat.rc", macros)
        assert set(templates) == {128, 130, 131, 255, 256} | set(range(146, 154))
        decoded = {ident: decode(data) for ident, data in templates.items()}
        for ident in range(146, 154):
            caption, controls = decoded[ident]
            assert controls, f"Empty original dialog {ident}"
            if ident != 153:
                assert caption.startswith("IDS_MENU_TEXT"), (ident, caption)
            print(f"dialog={ident} controls={len(controls)} template_bytes={len(templates[ident])}")
        controls = decoded[153][1]
        assert len(controls) == 10
        tab = next(c for c in controls if c[0] == macros["IDC_GENERIC_TABCTRL"])
        assert tab[1:3] == ("SysTabControl32", (8, 59, 384, 202)), tab
        back = next(c for c in controls if c[0] == macros["IDC_MENU_BACK_BUTTON"])
        assert back[1:3] == (0x80, (8, 274, 61, 19)), back
        assert back[4] == "IDS_MENU_TEXT184", back
        edit = next(c for c in decoded[146][1] if c[0] == macros["IDC_DESCRIPTION_EDIT"])
        assert edit[1:] == (0x81, (40, 161, 225, 43), 0x84, ""), edit
        for ident in range(149, 153):
            edit = next(c for c in decoded[ident][1] if c[0] == macros["IDC_DESCRIPTION_STATIC"])
            assert edit[1:] == (0x81, (76, 160, 189, 44), 0x84, ""), (ident, edit)
        print("PASS: zero-fuzz application; all templates decoded; EVA shell and five captionless edit controls match original resources")


if __name__ == "__main__":
    main()
