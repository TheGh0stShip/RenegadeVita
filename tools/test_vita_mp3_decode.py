"""Exercise production MPEG decoding on generated audio, without retail fixtures."""
from pathlib import Path
import shutil
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MpegDecodeTests(unittest.TestCase):
    def test_generated_music_and_invalid_input(self):
        with tempfile.TemporaryDirectory(prefix="renegade-mpeg-") as folder:
            work = Path(folder)
            sdk = Path.home() / ".local/vitasdk/arm-vita-eabi/include"
            for header in ("mpg123.h", "fmt123.h"):
                shutil.copy2(sdk / header, work / header)
            source = work / "probe.cpp"
            source.write_text(r'''
#include "renegade_wave_decoder.h"
#include "mss.h"
#include "renegade_miles_test.h"
#include <cassert>
#include <fstream>
#include <iterator>
#include <cstdio>
#include <cstdlib>
int main(int argc, char **argv) {
    assert(argc == 4);
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(input)), {});
    RenegadeVitaAudio::DecodedWave wave;
    RenegadeVitaAudio::WaveInfo info, inspected;
    const char *error = nullptr;
    assert(RenegadeVitaAudio::Decode_Wave_With_Info(bytes.data(), bytes.size(), &wave, &info, &error));
    assert(RenegadeVitaAudio::Inspect_Wave(bytes.data(), bytes.size(), &inspected, &error));
    assert(wave.channels == std::atoi(argv[2]) && wave.sample_rate == unsigned(std::atoi(argv[3])));
    assert(wave.Frame_Count() > 20000 && info.sample_frames == wave.Frame_Count());
    assert(inspected.sample_frames == info.sample_frames);
    bool nonzero = false;
    for (int16_t sample : wave.samples) if (sample != 0) nonzero = true;
    assert(nonzero);
    auto playback = RenegadeVitaAudio::Open_Mpeg_Playback(bytes.data(), bytes.size(), &error);
    assert(playback && playback->Frame_Count() == wave.Frame_Count());
    assert(playback->PCM_Storage_Bytes() <= 16400);
    assert(playback->Channels() == wave.channels && playback->Sample_Rate() == wave.sample_rate);
    unsigned quantized_differences = 0;
    auto check_sample = [&](size_t frame, unsigned channel) {
        const int got = playback->Sample(frame, channel);
        const int expected = wave.samples[frame * wave.channels + channel];
        // mpg123 may choose different aligned synthesis paths for feeder and
        // reader buffers. Bound their signed-16 quantization difference to one
        // LSB; a missing/shifted/cache-corrupted sample still fails this check.
        if (got != expected) ++quantized_differences;
        if (std::abs(got - expected) > 1) std::fprintf(stderr,
            "MPEG mismatch frame=%zu channel=%u got=%d expected=%d\n", frame,channel,got,expected);
        assert(std::abs(got - expected) <= 1);
    };
    // Match each sample, including mixer lookahead across cache boundaries.
    for (size_t f = 0; f + 1 < wave.Frame_Count(); ++f) {
        for (unsigned c = 0; c < wave.channels; ++c) {
            check_sample(f, c);
            check_sample(f + 1, c);
        }
    }
    for (size_t f : {size_t(0), size_t(21000), size_t(4100), wave.Frame_Count() - 1})
        for (unsigned c = 0; c < wave.channels; ++c)
            check_sample(f, c);
    std::printf("MPEG quantized differences=%u max_allowed_lsb=1\n", quantized_differences);
    AIL_startup();
    HSAMPLE sample = AIL_allocate_sample_handle(nullptr);
    assert(sample && AIL_set_named_sample_file(sample, nullptr, bytes.data(), bytes.size(), 0));
    S32 length_ms = 0, position_ms = -1;
    AIL_sample_ms_position(sample, &length_ms, &position_ms);
    assert(length_ms == static_cast<S32>(static_cast<uint64_t>(wave.Frame_Count()) * 1000U / wave.sample_rate));
    assert(position_ms == 0);
    AIL_set_sample_volume(sample, 127);
    AIL_set_sample_pan(sample, 64);
    AIL_set_sample_loop_count(sample, 0);
    AIL_start_sample(sample);
    int16_t mixed[2048];
    for (unsigned i = 0; i < 100; ++i) {
        assert(Renegade_Miles_Mix_For_Test(mixed, 1024));
        bool audible = false;
        for (int16_t value : mixed) audible |= value != 0;
        assert(audible);
    }
    AIL_stop_sample(sample);
    assert(Renegade_Miles_Mix_For_Test(mixed, 1024));
    for (int16_t value : mixed) assert(value == 0);
    AIL_release_sample_handle(sample);
    AIL_shutdown();
    std::printf("frames=%zu channels=%u rate=%u decoded_bytes=%zu nonzero=1\n",
        wave.Frame_Count(), wave.channels, wave.sample_rate, wave.samples.size() * 2);
    const uint8_t invalid[16] = {'I', 'D', '3', 0xff};
    assert(!RenegadeVitaAudio::Open_Mpeg_Playback(invalid, sizeof(invalid), &error));
    assert(!RenegadeVitaAudio::Decode_Wave(invalid, sizeof(invalid), &wave, &error));
    assert(!RenegadeVitaAudio::Decode_Wave(bytes.data(), 3, &wave, &error));
}
''')
            built = subprocess.run(["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror",
                *(["-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                  if os.environ.get("RENEGADE_MPEG_SANITIZE") == "1" else []),
                "-DRENEGADE_AUDIO_MPG123=1", "-DRENEGADE_MILES_MANUAL_MIX=1", "-D_UNIX=1", "-pthread", "-I", str(work),
                "-I", str(ROOT / "port/audio/miles"), "-I", str(ROOT / "port/compatibility/include"),
                "-I", str(ROOT / "port/audio/vita"), str(source),
                str(ROOT / "port/audio/vita/renegade_wave_decoder.cpp"),
                str(ROOT / "port/audio/vita/renegade_miles_provider.cpp"),
                "-l:libmpg123.so.0", "-o", str(work / "probe")], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for channels, rate, duration in [(2, 44100, 1), (1, 22050, 1), (2, 48000, 120)]:
                fixture = work / f"generated-{channels}-{rate}.mp3"
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=440:duration={duration}:sample_rate={rate}", "-ac", str(channels),
                    "-codec:a", "libmp3lame", str(fixture)], check=True)
                subprocess.run([str(work / "probe"), str(fixture), str(channels), str(rate)], check=True)


if __name__ == "__main__":
    unittest.main()
