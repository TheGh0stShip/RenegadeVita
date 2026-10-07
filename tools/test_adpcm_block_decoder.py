"""Per-block ADPCM decode must concatenate to the full decode, byte-for-byte,
and the full decode must match the pre-refactor (git HEAD~) implementation."""
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DECODER = ROOT / "port/audio/vita/renegade_wave_decoder.cpp"
HEADER = ROOT / "port/audio/vita/renegade_wave_decoder.h"
MS_COEFS = [256, 0, 512, -256, 0, 0, 192, 64, 240, 0, 460, -208, 392, -232]

PROBE = r'''
#include "renegade_wave_decoder.h"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
using namespace RenegadeVitaAudio;
int main(int argc, char **argv) {
    std::ifstream in(argv[1], std::ios::binary);
    std::vector<uint8_t> b((std::istreambuf_iterator<char>(in)), {});
    DecodedWave wave; WaveInfo info; const char *error = nullptr;
    if (!Decode_Wave_With_Info(b.data(), b.size(), &wave, &info, &error)) {
        std::fprintf(stderr, "decode failed: %s\n", error); return 2; }
    std::fwrite(wave.samples.data(), 2, wave.samples.size(), stdout);
#ifdef PER_BLOCK
    std::vector<int16_t> blocks;
    const uint8_t *src = b.data() + info.data_offset;
    for (size_t off = 0; off < info.data_bytes;) {
        size_t n = std::min<size_t>(info.block_align, info.data_bytes - off);
        size_t cap = Adpcm_Block_Max_Frames(info, n), got = 0;
        std::vector<int16_t> out(cap * info.channels);
        bool ok = info.encoding == WaveEncoding::ImaAdpcm
            ? Decode_Ima_Block(src + off, n, info, out.data(), cap, &got, &error)
            : Decode_Ms_Block(src + off, n, info, out.data(), cap, &got, &error);
        if (!ok) { std::fprintf(stderr, "block failed: %s\n", error); return 3; }
        // Pure: decoding again into a fresh buffer yields identical output.
        std::vector<int16_t> again(cap * info.channels); size_t got2 = 0;
        if (info.encoding == WaveEncoding::ImaAdpcm)
            Decode_Ima_Block(src + off, n, info, again.data(), cap, &got2, &error);
        else Decode_Ms_Block(src + off, n, info, again.data(), cap, &got2, &error);
        if (got2 != got || !std::equal(out.begin(), out.begin() + got * info.channels, again.begin())) return 4;
        if (got > 0) {
            size_t small = 0;
            bool fits = info.encoding == WaveEncoding::ImaAdpcm
                ? Decode_Ima_Block(src + off, n, info, again.data(), got - 1, &small, &error)
                : Decode_Ms_Block(src + off, n, info, again.data(), got - 1, &small, &error);
            if (fits) return 5;
        }
        blocks.insert(blocks.end(), out.begin(), out.begin() + got * info.channels);
        off += n;
    }
    if (blocks != wave.samples) { std::fprintf(stderr, "concat mismatch\n"); return 6; }
#endif
    return 0;
}
'''


def wav(fmt_tag, channels, block_align, spb, extra, data, frames):
    fmt = struct.pack("<HHIIHH", fmt_tag, channels, 22050,
                      22050 * block_align // spb, block_align, 4)
    fmt += struct.pack("<H", len(extra)) + extra
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"fact" + struct.pack("<II", 4, frames)
    body += b"data" + struct.pack("<I", len(data)) + data
    if len(data) & 1:
        body += b"\0"
    return b"RIFF" + struct.pack("<I", len(body)) + body


def ima(rng, channels, blocks, tail):
    align = 256 * channels
    spb = (align - 4 * channels) * 8 // (4 * channels) + 1
    data = bytearray()
    for i in range(blocks + (1 if tail else 0)):
        size = tail if i == blocks else align
        blk = bytearray()
        for _ in range(channels):
            blk += struct.pack("<hBB", rng.randint(-32768, 32767), rng.randint(0, 88), 0)
        blk += bytes(rng.randrange(256) for _ in range(size - len(blk)))
        data += blk[:size]
    frames = blocks * spb + (1 + (tail - 4 * channels) * 2 // channels if tail else 0)
    return wav(0x11, channels, align, spb, struct.pack("<H", spb), bytes(data), frames)


def ms(rng, channels, blocks, tail):
    align = 256 * channels
    spb = (align - 7 * channels) * 2 // channels + 2
    data = bytearray()
    for i in range(blocks + (1 if tail else 0)):
        size = tail if i == blocks else align
        blk = bytearray(rng.randrange(7) for _ in range(channels))
        for _ in range(channels):
            blk += struct.pack("<H", rng.randint(16, 2000))
        for _ in range(2 * channels):
            blk += struct.pack("<h", rng.randint(-32768, 32767))
        blk += bytes(rng.randrange(256) for _ in range(size - len(blk)))
        data += blk[:size]
    frames = blocks * spb + (2 + (tail - 7 * channels) * 2 // channels if tail else 0)
    extra = struct.pack("<HH", spb, 7) + struct.pack("<14h", *MS_COEFS)
    return wav(0x02, channels, align, spb, extra, bytes(data), frames)


class AdpcmBlockDecoderTests(unittest.TestCase):
    def test_per_block_matches_full_and_baseline(self):
        with tempfile.TemporaryDirectory(prefix="renegade-adpcm-") as folder:
            work = Path(folder)
            (work / "probe.cpp").write_text(PROBE)
            new = work / "new"
            subprocess.run(["g++", "-std=c++17", "-O1", "-DPER_BLOCK", f"-I{HEADER.parent}",
                            str(work / "probe.cpp"), str(DECODER), "-o", str(new)], check=True)
            base_dir = work / "base"
            base_dir.mkdir()
            baseline = None
            rev = subprocess.run(["git", "-C", str(ROOT), "log", "-n1", "--format=%H",
                                  "--grep=Phase 1 per-block ADPCM", "--invert-grep", "--",
                                  str(DECODER.relative_to(ROOT))],
                                 capture_output=True, text=True).stdout.strip()
            if rev:
                for src, dst in ((DECODER, "d.cpp"), (HEADER, HEADER.name)):
                    out = subprocess.run(["git", "-C", str(ROOT), "show",
                                          f"{rev}:{src.relative_to(ROOT)}"], capture_output=True)
                    (base_dir / dst).write_bytes(out.stdout)
                baseline = work / "baseline"
                # Headers the baseline revision includes but does not copy resolve
                # from the current tree, after the baseline copies.
                subprocess.run(["g++", "-std=c++17", "-O1", f"-I{base_dir}", f"-I{HEADER.parent}",
                                str(work / "probe.cpp"),
                                str(base_dir / "d.cpp"), "-o", str(baseline)], check=True)
            rng = random.Random(1234)
            cases = []
            for channels in (1, 2):
                for tail in (0, 40 * channels + 1, 7 * channels + 3):
                    cases.append(("ima", channels, ima(rng, channels, 5, tail)))
                    cases.append(("ms", channels, ms(rng, channels, 5, tail)))
            for name, channels, image in cases:
                with self.subTest(codec=name, channels=channels, size=len(image)):
                    path = work / "in.wav"
                    path.write_bytes(image)
                    got = subprocess.run([str(new), str(path)], capture_output=True)
                    self.assertEqual(got.returncode, 0, got.stderr.decode())
                    self.assertGreater(len(got.stdout), 1000)
                    if baseline:
                        ref = subprocess.run([str(baseline), str(path)], capture_output=True)
                        self.assertEqual(ref.returncode, 0, ref.stderr.decode())
                        self.assertEqual(got.stdout, ref.stdout)


if __name__ == "__main__":
    unittest.main()
