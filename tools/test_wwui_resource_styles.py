"""Compare every generated frontend control with an independent RC compiler."""
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

from tools import generate_wwui_dialog_templates as generator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream/CnC_Renegade/Code/Commando'


def controls(data):
    def field(at):
        first = struct.unpack_from('<H', data, at)[0]
        if first == 0xffff:
            return at + 4
        while struct.unpack_from('<H', data, at)[0]:
            at += 2
        return at + 2
    at = 18
    for _ in range(3):
        at = field(at)
    if struct.unpack_from('<I', data)[0] & 0x40:
        at = field(at + 2)
    items = []
    for _ in range(struct.unpack_from('<H', data, 8)[0]):
        at = (at + 3) & ~3
        start = at
        class_start = at + 18
        class_end = field(class_start)
        control_class = data[class_start:class_end]
        if struct.unpack_from('<H', control_class)[0] != 0xffff:
            name = control_class[:-2].decode('utf-16le').upper()
            builtin = {'BUTTON':0x80, 'STATIC':0x82, 'EDIT':0x81, 'COMBOBOX':0x85}.get(name)
            if builtin:
                control_class = struct.pack('<HH', 0xffff, builtin)
        at = field(class_end)
        at += 2 + struct.unpack_from('<H', data, at)[0]
        items.append((data[start:class_start], control_class, data[class_end:at]))
    return items


class ResourceStyleTests(unittest.TestCase):
    def test_all_pause_action_and_confirmation_resources_present(self):
        definitions = generator.macros((SOURCE/'resource.h', SOURCE/'dialogresource.h'))
        generated = generator.parse(SOURCE/'chat.rc', definitions)
        # Independent inventory of the original owners invoked by EVA.
        for name in ('IDD_MENU_LOAD_SP_GAME', 'IDD_MESSAGEBOX_YESNO', 'IDD_MESSAGEBOX_OK',
                     'IDD_MENU_SAVE_GAME', 'IDD_CONFIG_AUDIO', 'IDD_CONFIG_VIDEO',
                     'IDD_CONFIG_PERFORMANCE'):
            self.assertIn(definitions[name], generated, name)

    def test_original_frontend_controls_match_llvm_rc(self):
        definitions = generator.macros((SOURCE/'resource.h', SOURCE/'dialogresource.h'))
        generated = generator.parse(SOURCE/'chat.rc', definitions)
        source = (SOURCE/'chat.rc').read_text(encoding='latin1')
        blocks = re.findall(r'^\w+ DIALOG(?:EX)? DISCARDABLE .*?^END',
                            source, re.MULTILINE | re.DOTALL)
        selected = [b for b in blocks if definitions.get(b.split()[0]) in generator.IDS]
        self.assertEqual(len(selected), len(generator.IDS))
        rc = '\n'.join(f'#define {key} {value}' for key, value in definitions.items())
        rc += '\n' + '\n'.join(selected) + '\n'
        with tempfile.TemporaryDirectory(prefix='renegade-rc-') as folder:
            path = Path(folder)
            (path/'source.rc').write_text(rc)
            result = subprocess.run(['llvm-rc', '/C', '65001', '/FO', str(path/'source.res'), str(path/'source.rc')],
                                    capture_output=True, text=True, errors='replace')
            self.assertEqual(result.returncode, 0, result.stderr)
            res = (path/'source.res').read_bytes()
        at = 0
        compared = 0
        while at < len(res):
            size, header = struct.unpack_from('<II', res, at)
            if size:
                ordinal, kind, named, ident = struct.unpack_from('<4H', res, at + 8)
                self.assertEqual((ordinal, kind, named), (0xffff, 5, 0xffff))
                reference = controls(res[at+header:at+header+size])
                actual = controls(generated[ident])
                self.assertEqual(len(actual), len(reference), f'dialog {ident}')
                for index, (a, b) in enumerate(zip(actual, reference)):
                    self.assertEqual(a, b, f'dialog {ident} control {index}')
                    compared += 1
            at = (at + header + size + 3) & ~3
        print(f'Original frontend RC control equivalence PASS dialogs={len(selected)} controls={compared}')

    def test_explicit_not_can_remove_implicit_visibility(self):
        data = generator.control(generator.split('LTEXT "hidden", 10, 1, 2, 3, 4, NOT WS_VISIBLE'), generator.FLAGS)
        self.assertEqual(struct.unpack_from('<I', data)[0], 0x40020000)


if __name__ == '__main__':
    unittest.main()
