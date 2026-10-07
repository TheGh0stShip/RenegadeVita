"""RVIO1 load-io-v1.flag: pure-Python model and source-contract checks.

No compiler, game build or device is involved. The model in
tools/model_vita_load_io.py mirrors the VitaSDK newlib stdio paths (as
disassembled from libc.a), wwlib RawFileClass/BufferedFileClass and the
ChunkLoadClass/DDS read sequences.
"""
import random
import re
import struct
import unittest
from pathlib import Path

from tools.model_vita_load_io import (
    DEFAULT_RETAIL, BufferedFile, RawFile, Syscalls, archive_opens, chunk_traversal,
    compare_modes, presenter_renders, replay_member, tutorial_members)

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / 'port/filesystem/renegade_load_io.h'
FACTORY = ROOT / 'port/filesystem/renegade_file_factory.cpp'
FACTORY_HEADER = ROOT / 'port/filesystem/renegade_file_factory.h'
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'
STUB = ROOT / 'tools/file_factory_stub/bufffile.h'


def parse_flag(value):
    """Mirror of Renegade_Load_Io_Parse_Flag."""
    if len(value) != 8 or value[:6] != b'RVIO1 ' or value[7:8] != b'\n':
        return 0
    digit = value[6:7]
    if not b'0' <= digit <= b'7':
        return 0
    return digit[0] - ord('0')


def body(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin + len(start))]


class _FakeArchive:
    def __init__(self, data):
        self.data = data
        self.path = Path('synthetic.mix')


def chunk(chunk_type, payload=b'', children=None):
    if children is not None:
        inner = b''.join(children)
        return struct.pack('<II', chunk_type, len(inner) | 0x80000000) + inner
    return struct.pack('<II', chunk_type, len(payload)) + payload


def synthetic_archive(seed=7):
    """Members with leaf sizes around the 1 KiB stdio and 16 KiB BufferedFile
    boundaries, nested containers, unaligned member offsets and a DDS."""
    rng = random.Random(seed)
    members = []
    blob = bytearray(b'MIX1' + bytes(8) + bytes(rng.randrange(256) for _ in range(333)))
    leaf_sizes = [0, 1, 7, 1023, 1024, 1025, 4000, 16383, 16384, 16385, 40000, 70001]
    for index in range(10):
        leaves = []
        for leaf in range(rng.randrange(3, 9)):
            size = rng.choice(leaf_sizes)
            leaves.append(chunk(0x100 + leaf * 3 + index,
                                bytes(rng.randrange(256) for _ in range(size))))
        nested = chunk(0x200 + index, children=leaves[:2])
        payload = b''.join([chunk(0x300 + index, children=[nested] + leaves[2:]),
                            chunk(0x10 + index, b'tail' * rng.randrange(1, 300))])
        offset = len(blob)
        blob += payload + bytes(rng.randrange(256) for _ in range(rng.randrange(1, 900)))
        members.append((offset, len(payload), 'chunk', 'synthetic%d.w3d' % index))
    dds = b'DDS ' + bytes(124) + bytes(rng.randrange(256) for _ in range(87360))
    members.append((len(blob), len(dds), 'dds', 'synthetic.dds'))
    blob += dds + b'end'
    archive = _FakeArchive(bytes(blob))
    return archive, [(archive, offset, size, pattern, name)
                     for offset, size, pattern, name in members]


class LoadIoFlagTests(unittest.TestCase):
    def test_flag_parser_and_header_agree(self):
        header = HEADER.read_text()
        self.assertIn('#define RENEGADE_LOAD_IO_FLAG_PATH '
                      '"ux0:data/renegade/user/config/load-io-v1.flag"', header)
        self.assertIn('RENEGADE_LOAD_IO_DEFAULT = 0U', header)
        self.assertIn('RENEGADE_LOAD_IO_DIRECT_READS = 1U', header)
        self.assertIn('RENEGADE_LOAD_IO_ARCHIVE_SIZE_REUSE = 2U', header)
        self.assertIn('RENEGADE_LOAD_IO_REPAINT_CADENCE = 4U', header)
        parser = body(header, 'inline unsigned Renegade_Load_Io_Parse_Flag',
                      'inline unsigned Renegade_Load_Io_Read_Flag_File')
        self.assertIn('size != 8U', parser)
        self.assertIn('memcmp(value, "RVIO1 ", 6U) != 0', parser)
        self.assertIn("value[7] != '\\n'", parser)
        self.assertIn("value[6] < '0' || value[6] > '7'", parser)
        self.assertIn('kRenegadeLoadIoDefaultRepaintUs = 50000U', header)
        self.assertIn('kRenegadeLoadIoCadenceRepaintUs = 250000U', header)
        cases = {b'RVIO1 0\n': 0, b'RVIO1 3\n': 3, b'RVIO1 7\n': 7, b'RVIO1 8\n': 0,
                 b'RVIO1 3': 0, b'RVIO1 3\r\n': 0, b'RVPL1 3\n': 0, b'': 0,
                 b'rvio1 3\n': 0}
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_flag(value), expected)

    def test_runtime_reads_flag_before_mix_factories_and_logs_timeline(self):
        runtime = RUNTIME.read_text()
        start = runtime.index('A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(')
        configure = runtime.index('Renegade_Load_Io_Read_Flag_File(RENEGADE_LOAD_IO_FLAG_PATH)', start)
        self.assertLess(configure, runtime.index('MixFileFactoryClass always2_factory(', start))
        self.assertIn('A3.6 load-io: version=1 mask=%u', runtime)
        self.assertIn('A3.6 load-io: level load sync_ms=%llu', runtime)
        self.assertIn('A3.6 load-io: level load begin_to_first_frame_ms=%llu', runtime)
        self.assertIn('A3.6 load-io: frame=%u mask=%u direct_read_streams=%u', runtime)
        callback = body(runtime, 'void A31_Vita_Render_Original_Loading_Callback(',
                        'rendering = true;')
        self.assertIn('minimum_progress < 0 && now_us - last_render_us <', callback)
        self.assertIn('Renegade_Load_Io_Substatus_Repaint_Interval_Us(', callback)
        self.assertNotIn('50000U', callback)
        presenter = body(runtime, 'void Render_Original_Progress(', 'private:')
        self.assertIn('kLoadingProgressCatchupFrames', presenter)


class DirectReadTests(unittest.TestCase):
    def test_source_gates_unbuffered_streams_to_retail_reads(self):
        factory = FACTORY.read_text()
        apply = body(factory, 'void RenegadeRootedFileClass::Apply_Direct_Reads(void)', '\n}\n')
        self.assertIn('setvbuf(handle, NULL, _IONBF, 0) == 0', apply)
        self.assertIn('#if defined(_UNIX)', apply)
        open_body = body(factory, 'int RenegadeRootedFileClass::Open(int rights)',
                         'bool RenegadeRootedFileClass::Stage_Write(')
        self.assertIn('DirectReadPending = rights == FileClass::READ && Is_Immutable_Retail_Read() &&',
                      open_body)
        self.assertIn('RENEGADE_LOAD_IO_DIRECT_READS) != 0U;', open_body)
        self.assertLess(open_body.index('DirectReadPending = rights'),
                        open_body.index('const int opened = BufferedFileClass::Open(rights);'))
        self.assertIn('if (opened && DirectReadPending) Apply_Direct_Reads();', open_body)
        seek = body(factory, 'int RenegadeRootedFileClass::Seek(int pos, int dir)', '\n}\n')
        self.assertLess(seek.index('if (DirectReadPending) Apply_Direct_Reads();'),
                        seek.index('return BufferedFileClass::Seek(pos, dir);'))
        retail = body(factory, 'bool RenegadeRootedFileClass::Is_Immutable_Retail_Read(void) const',
                      '\n}\n')
        self.assertIn('!LastResolution.writable_namespace', retail)
        self.assertIn('PreparedAccess == RENEGADE_PATH_READ', retail)
        self.assertIn('g_load_io_mode(RENEGADE_LOAD_IO_DEFAULT)', factory)
        self.assertIn('mode & RENEGADE_LOAD_IO_ALL', factory)

    def test_unbuffered_stdio_delivers_identical_bytes_synthetic(self):
        _, members = synthetic_archive()
        original, direct, mismatches = compare_modes(members)
        self.assertEqual(mismatches, [])
        self.assertEqual(original.opens, direct.opens)
        self.assertLess(direct.reads * 8, original.reads)
        self.assertLessEqual(direct.lseeks, original.lseeks)

    def test_unbuffered_large_read_is_one_kernel_read(self):
        archive, members = synthetic_archive()
        _, offset, size, _, _ = members[-1]
        traces = {}
        counts = {}
        for direct in (False, True):
            trace, syscalls = replay_member(archive.data, offset, size, 'dds', direct)
            traces[direct], counts[direct] = trace, syscalls
        self.assertEqual(traces[False], traces[True])
        self.assertEqual(traces[True][-1][1], archive.data[offset + 128:offset + size])
        # 128-byte header refill + one 87 KiB data read, versus 1 KiB pieces.
        self.assertEqual(counts[True].reads, 2)
        self.assertGreater(counts[False].reads, 85)

    def test_seek_patterns_match_reference_positions(self):
        archive, members = synthetic_archive(seed=11)
        for _, offset, size, _, name in members[:4]:
            for direct in (False, True):
                with self.subTest(member=name, direct=direct):
                    raw = RawFile(archive.data, Syscalls(), direct_reads=direct)
                    raw.bias(offset, size)
                    file = BufferedFile(raw)
                    file.open()
                    expected = archive.data[offset:offset + size]
                    rng = random.Random(size)
                    position = 0
                    for _ in range(200):
                        operation = rng.randrange(4)
                        if operation == 0:
                            count = rng.choice([1, 8, 900, 1500, 17000, 33000])
                            data = file.read(count)
                            self.assertEqual(data, expected[position:position + count])
                            position += len(data)
                        elif operation == 1:
                            target = rng.randrange(0, size + 1)
                            self.assertEqual(file.seek(target, 0), target)
                            position = target
                        elif operation == 2:
                            delta = rng.randrange(-min(position, 5000), min(size - position, 5000) + 1)
                            self.assertEqual(file.seek(delta, 1), position + delta)
                            position += delta
                        else:
                            self.assertEqual(file.tell(), position)
                    file.close()

    @unittest.skipUnless((DEFAULT_RETAIL / 'M00_Tutorial.mix').is_file(),
                         'retail Data not present')
    def test_tutorial_dependency_members_identical_and_fewer_reads(self):
        names, members = tutorial_members(DEFAULT_RETAIL)
        self.assertGreater(len(names), 200)
        self.assertGreater(len(members), 200)
        original, direct, mismatches = compare_modes(members)
        self.assertEqual(mismatches, [])
        self.assertLess(direct.reads * 10, original.reads)
        self.assertLess(direct.total(), original.total())


class ArchiveSizeReuseTests(unittest.TestCase):
    def test_source_matches_original_bias_arithmetic(self):
        factory = FACTORY.read_text()
        bias = body(factory, 'void RenegadeRootedFileClass::Bias(int start, int length)', '\n}\n')
        for anchor in ('start != 0 && BiasStart == 0 && BiasLength == -1',
                       '!Is_Open() && Is_Immutable_Retail_Read() && !LastResolution.confirmed_missing',
                       'RENEGADE_LOAD_IO_ARCHIVE_SIZE_REUSE) != 0U;',
                       'BiasStart = start;',
                       'if (length != -1) bias_length = bias_length < length ? bias_length : length;',
                       'BiasLength = bias_length > 0 ? bias_length : 0;',
                       'ArchiveSizeProbe = eligible;',
                       'BufferedFileClass::Bias(start, length);'):
            self.assertIn(anchor, bias)
        size = body(factory, 'int RenegadeRootedFileClass::Size(void)', '\n}\n')
        self.assertIn('if (ArchiveSizeProbe && size > 0 && BiasStart == 0 && Is_Open())', size)
        rawfile = (ROOT / 'staging/wwlib/rawfile.cpp').read_text(errors='replace')
        original = body(rawfile, 'void RawFileClass::Bias(int start, int length)', '\n}\n')
        for anchor in ('BiasLength = RawFileClass::Size();', 'BiasStart += start;',
                       'BiasLength = BiasLength < length ? BiasLength : length;',
                       'BiasLength = BiasLength > 0 ? BiasLength : 0;'):
            self.assertIn(anchor, original)
        self.assertIn('virtual void Bias(int start, int length=-1);',
                      (ROOT / 'staging/wwlib/rawfile.h').read_text(errors='replace'))
        self.assertIn('virtual void Bias(int start, int length = -1);', FACTORY_HEADER.read_text())
        self.assertIn('virtual void Bias(int start, int length = -1)', STUB.read_text())

    def test_size_reuse_matches_original_bias_and_halves_opens(self):
        archive, members = synthetic_archive()
        extra = [(archive, start, length, 'chunk', 'edge')
                 for start, length in ((1, -1), (5, 10 ** 9), (len(archive.data) - 4, 64),
                                       (len(archive.data) + 10, 3), (77, 0))]
        original, reuse = archive_opens(members + extra)
        self.assertEqual(original.opens, 2 * len(members + extra))
        self.assertEqual(reuse.opens, len(members + extra) + 1)

    @unittest.skipUnless((DEFAULT_RETAIL / 'M00_Tutorial.mix').is_file(),
                         'retail Data not present')
    def test_tutorial_members_reuse_one_probe_per_archive(self):
        _, members = tutorial_members(DEFAULT_RETAIL)
        original, reuse = archive_opens(members)
        archives = {member[0].path for member in members}
        self.assertEqual(original.opens, 2 * len(members))
        self.assertEqual(reuse.opens, len(members) + len(archives))


class PresenterCadenceTests(unittest.TestCase):
    def test_cadence_keeps_every_milestone_and_bounds_gaps(self):
        rng = random.Random(3)
        events = [(0, 0)]
        for index in range(220):
            events.append((rng.randrange(5000, 140000), -1))
            if index % 40 == 39:
                events.append((rng.randrange(1000, 20000), index // 40 + 1))
        milestones = sum(1 for _, progress in events if progress >= 0)
        longest_work = max(work for work, _ in events)
        for render_us in (5000, 17000, 33000):
            with self.subTest(render_us=render_us):
                base = presenter_renders(events, 50000, render_us)
                cadence = presenter_renders(events, 250000, render_us)
                self.assertEqual(base[1], milestones)
                self.assertEqual(cadence[1], milestones)
                self.assertLess(cadence[0], base[0])
                self.assertLess(cadence[2], base[2])
                self.assertLessEqual(cadence[3], 250000 + longest_work)


if __name__ == '__main__':
    unittest.main()
