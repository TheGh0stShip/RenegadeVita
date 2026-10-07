#!/usr/bin/env python3
"""Pure-Python contract for the RVAU1 audio cost switches (audio-cost-v1.flag).

No compiler, game, device or retail write. The source checks pin that every
RVAU1 path is flag gated, keeps the default stream path and the mixer
unchanged, bounds the image pool and falls back to the heap. The arithmetic
model mirrors renegade_wave_decoder.cpp's ADPCM frame counts, its reserve and
libstdc++ vector growth, and proves the bit 0 reserve never regrows, keeps
every non-regrowing image's capacity identical and never exceeds the old
capacity or peak. Set RENEGADE_RETAIL_DATA to a retail Data directory (or keep
retail-pc/Data beside the checkout) to also sweep every always.dat ADPCM header.
"""
from __future__ import annotations

import functools
import os
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / 'port/audio/vita'
PROVIDER = AUDIO / 'renegade_miles_provider.cpp'
DECODER = AUDIO / 'renegade_wave_decoder.cpp'
COST = AUDIO / 'renegade_audio_cost.h'
STATS = AUDIO / 'renegade_miles_runtime_stats.h'
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'

IMA, MS = 0x11, 0x02
KMAX = 16 * 1024 * 1024
U32_MAX = 0xFFFFFFFF


def body(text: str, signature: str) -> str:
    """Brace-matched body of the first definition starting with signature."""
    start = text.index(signature)
    open_brace = text.index('{', start)
    depth, index = 0, open_brace
    while True:
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
        index += 1


# ---------------------------------------------------------------------------
# Model of renegade_wave_decoder.cpp (ADPCM only).
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=4096)
def block_frames(encoding, channels, spb, block_bytes):
    """Frames Decode_Ima_Block / Decode_Ms_Block emit, or None on failure."""
    limit = spb if spb else float('inf')
    if encoding == IMA:
        header = 4 * channels
        if block_bytes < header:
            return None
        payload = block_bytes - header
        frames = 1
        if channels == 1:
            index = 0
            while index < payload and frames < limit:
                frames += 1
                if frames >= limit:
                    break
                frames += 1
                index += 1
            return frames
        group = 0
        while group < payload and frames < limit:
            counts = [0, 0]
            for channel in (0, 1):
                available = min(4, payload - group)
                counts[channel] += 2 * available
                group += available
                if group >= payload and channel == 0:
                    break
            for _ in range(min(counts)):
                if frames >= limit:
                    break
                frames += 1
        return frames
    header = 7 * channels
    if block_bytes < header:
        return None
    payload = block_bytes - header
    frames = 2
    index = 0
    while index < payload and frames < limit:
        frames += 1
        if channels == 1:
            if frames >= limit:
                break
            frames += 1
        index += 1
    return frames


def estimate_frames(encoding, channels, align, spb, data_bytes):
    """Estimate_Frame_Count / Estimate_Partial_Adpcm_Frames."""
    if align == 0 or spb == 0:
        return 0
    full, remainder = divmod(data_bytes, align)
    header = (7 if encoding == MS else 4) * channels
    partial = 0
    if remainder > header:
        payload = remainder - header
        partial = 2 if encoding == MS else 1
        if encoding == MS:
            partial += payload * (2 if channels == 1 else 1)
        else:
            partial += (payload * 2) // channels
        partial = min(partial, spb)
    return min(full * spb + partial, U32_MAX)


def old_reserve(encoding, channels, align, spb, data_bytes):
    estimated = estimate_frames(encoding, channels, align, spb, data_bytes) * channels
    return min(KMAX, min(estimated, data_bytes * 2))


def exact_reserve(encoding, channels, align, data_bytes, fact, reserve):
    """Exact_Adpcm_Reserve."""
    header = (7 if encoding == MS else 4) * channels
    remainder = data_bytes % align if align else 0
    samples = reserve
    if remainder != 0 and remainder <= header:
        samples += (2 if encoding == MS else 1) * channels
    if encoding == IMA and channels == 1:
        samples = max(samples, fact)
    return min(KMAX, samples)


class Vector:
    """libstdc++ std::vector<int16_t> capacity growth."""

    def __init__(self):
        self.size = self.capacity = 0
        self.peak = 0
        self.regrowths = 0

    def _grow(self, new_capacity):
        self.peak = max(self.peak, self.capacity + new_capacity)
        self.capacity = new_capacity
        self.regrowths += 1

    def reserve(self, samples):
        if samples > self.capacity:
            self.peak = max(self.peak, self.capacity + samples)
            self.capacity = samples

    def insert(self, count):          # insert(end, first, first + count)
        if self.size + count > self.capacity:
            self._grow(self.size + max(self.size, count))
        self.size += count

    def push_back(self):
        if self.size == self.capacity:
            self._grow(self.size + max(self.size, 1))
        self.size += 1

    def resize(self, samples):
        if samples > self.capacity:
            self._grow(self.size + max(self.size, samples - self.size))
        self.size = samples


def decode(encoding, channels, align, spb, data_bytes, fact, exact):
    """Decode_Wave_With_Info's allocation sequence; None when decoding fails."""
    if encoding == IMA and channels == 1 and fact > KMAX:
        return None
    reserve = old_reserve(encoding, channels, align, spb, data_bytes)
    if exact:
        reserve = max(reserve, exact_reserve(encoding, channels, align, data_bytes,
                                             fact, reserve))
    output = Vector()
    output.reserve(reserve)
    offset = 0
    while offset < data_bytes:
        block_bytes = min(align, data_bytes - offset)
        if (encoding == IMA and channels == 1 and block_bytes < 4 and
                offset >= align and fact != 0):
            output.push_back()        # Append_Frame, one channel
            offset += block_bytes
            continue
        frames = block_frames(encoding, channels, spb, block_bytes)
        if frames is None:
            return None
        output.insert(frames * channels)
        offset += block_bytes
    if output.size == 0:
        return None
    untrimmed = output.size // channels
    if encoding == IMA and channels == 1 and fact > untrimmed:
        output.resize(fact)
    sample_frames = fact if fact else estimate_frames(encoding, channels, align, spb,
                                                      data_bytes)
    if sample_frames and output.size // channels > sample_frames:
        output.resize(sample_frames * channels)
    return {'samples': output.size, 'capacity': output.capacity,
            'peak': max(output.peak, output.capacity), 'regrowths': output.regrowths,
            'reserve': reserve}


def natural_spb(encoding, channels, align):
    if encoding == IMA:
        return (align - 4 * channels) * 2 // channels + 1
    return (align - 7 * channels) * 2 // channels + 2


def check_case(test, case, overstated_spb=False):
    old = decode(*case, exact=False)
    new = decode(*case, exact=True)
    test.assertEqual(old is None, new is None, case)
    if old is None:
        return None
    channels = case[1]
    test.assertEqual(old['samples'], new['samples'], case)
    test.assertEqual(new['regrowths'], 0, case)
    if old['regrowths'] == 0:
        if overstated_spb:
            # An estimate inflated by an oversized samples-per-block field
            # already covers the header-only block; the slack then costs at
            # most two frames of capacity.
            test.assertLessEqual(new['capacity'] - old['capacity'], 2 * channels, case)
        else:
            # Unaffected images keep the identical capacity (PCM cache cost).
            test.assertEqual(new['capacity'], old['capacity'], case)
    else:
        test.assertLessEqual(new['capacity'], old['capacity'], case)
        test.assertLessEqual(new['peak'], old['peak'], case)
    return old, new


class ExactDecodeReserveModelTest(unittest.TestCase):
    def test_block_model_matches_natural_block_sizes(self):
        for encoding, channels, align in ((IMA, 1, 512), (IMA, 2, 512), (IMA, 1, 1024),
                                          (MS, 1, 512), (MS, 2, 1024)):
            spb = natural_spb(encoding, channels, align)
            self.assertEqual(block_frames(encoding, channels, spb, align), spb)
            # Estimate of one full block equals what decoding emits.
            self.assertEqual(estimate_frames(encoding, channels, align, spb, align), spb)

    def test_reserve_never_regrows_and_never_costs_more(self):
        regrowing = 0
        cases = 0
        for encoding, channels, align in ((IMA, 1, 256), (IMA, 1, 512), (IMA, 2, 512),
                                          (IMA, 2, 1024), (MS, 1, 512), (MS, 2, 512),
                                          (MS, 1, 1024)):
            natural = natural_spb(encoding, channels, align)
            for spb in (natural, natural - 3, natural + 9):
                for blocks in (0, 1, 3):
                    for remainder in (0, 1, 2, 3, 4, 5, 7, 8, 9, 13, 14, 15, 29, align - 1):
                        data_bytes = blocks * align + remainder
                        if data_bytes == 0:
                            continue
                        estimate = estimate_frames(encoding, channels, align, spb, data_bytes)
                        for fact in {0, max(estimate - 5, 1), estimate, estimate + 1,
                                     estimate + 700}:
                            result = check_case(self, (encoding, channels, align, spb,
                                                       data_bytes, fact), spb > natural)
                            if result is None:
                                continue
                            cases += 1
                            regrowing += result[0]['regrowths'] != 0
        self.assertGreater(cases, 500)
        # The matrix exercises the defect the switch removes.
        self.assertGreater(regrowing, 20)

    def test_fact_padding_old_path_doubles_capacity(self):
        # Header values of retail m00gnod_kill0007r2nomg_snd.wav (generic
        # soldier chatter): mono IMA, 512-byte blocks, 1017 frames per block,
        # 36332 data bytes, fact 72664 above the 72167 encoded frames. The old
        # reserve is regrown to about twice the decoded size and kept.
        data_bytes, fact = 36332, 72664
        estimate = estimate_frames(IMA, 1, 512, 1017, data_bytes)
        self.assertEqual(estimate, 72167)
        old, new = check_case(self, (IMA, 1, 512, 1017, data_bytes, fact))
        self.assertGreater(old['regrowths'], 0)
        self.assertGreaterEqual(old['capacity'], 2 * estimate)
        self.assertEqual(new['capacity'], fact)
        self.assertLess(new['peak'] * 2, old['peak'])

    def test_header_only_final_block_old_path_regrows(self):
        # A final block holding only its header still emits header frames.
        old, new = check_case(self, (MS, 2, 512, natural_spb(MS, 2, 512), 3 * 512 + 14, 0))
        self.assertGreater(old['regrowths'], 0)
        self.assertEqual(new['regrowths'], 0)

    def test_retail_always_dat_headers_if_available(self):
        candidates = [os.environ.get('RENEGADE_RETAIL_DATA', ''), str(ROOT / 'retail-pc/Data'),
                      str(ROOT.parents[2] / 'retail-pc/Data')]
        data = next((Path(c) for c in candidates if c and (Path(c) / 'always.dat').is_file()),
                    None)
        if data is None:
            self.skipTest('retail Data not available')
        from tools.renegade_cinematic_dependency_scan import MixArchive
        archive = MixArchive(data / 'always.dat')
        checked = regrowing = 0
        with (data / 'always.dat').open('rb') as stream:
            for name, _crc, offset, size in archive.entry_records:
                if not name.lower().endswith('.wav') or size < 12:
                    continue
                stream.seek(offset)
                head = stream.read(min(size, 512))
                if head[:4] != b'RIFF' or head[8:12] != b'WAVE':
                    continue
                fmt = fact = data_bytes = None
                position = 12
                while position + 8 <= len(head):
                    kind, length = struct.unpack_from('<4sI', head, position)
                    if kind == b'fmt ' and position + 28 <= len(head):
                        fmt = struct.unpack_from('<HHIIHHHH', head, position + 8)
                    elif kind == b'fact' and position + 12 <= len(head):
                        fact = struct.unpack_from('<I', head, position + 8)[0]
                    elif kind == b'data':
                        data_bytes = min(length, size - position - 8)
                        break
                    position += 8 + length + (length & 1)
                if fmt is None or data_bytes is None or fmt[0] not in (IMA, MS):
                    continue
                tag, channels, _rate, _rate_bytes, align, _bits, _extra, spb = fmt
                if channels not in (1, 2) or align == 0:
                    continue
                result = check_case(self, (tag, channels, align, spb, data_bytes, fact or 0))
                if result is None:
                    continue
                checked += 1
                regrowing += result[0]['regrowths'] != 0
        self.assertGreater(checked, 1000)
        print(f'always.dat ADPCM headers checked={checked} old_regrowth={regrowing}')


# ---------------------------------------------------------------------------
# Source contract.
# ---------------------------------------------------------------------------

class AudioCostSourceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = PROVIDER.read_text()
        cls.decoder = DECODER.read_text()
        cls.cost = COST.read_text()
        cls.stats = STATS.read_text()
        cls.runtime = RUNTIME.read_text()

    def test_flag_file_prefix_and_default_off(self):
        self.assertIn('#define RENEGADE_VITA_AUDIO_COST_DEFAULT 0U', self.cost)
        parse = body(self.cost, 'inline bool Renegade_Parse_Audio_Cost_Flag(')
        for token in ('size != 8U', 'std::memcmp(value, "RVAU1 ", 6U) != 0',
                      "value[7] != '\\n'"):
            self.assertIn(token, parse)
        for name, value in (('EXACT_DECODE_RESERVE', 1), ('STREAM_CACHE_PROBE', 2),
                            ('STREAM_SECOND_OPEN_ADMISSION', 4), ('STREAM_IMAGE_POOL', 8),
                            ('ALL', 15)):
            self.assertIn(f'RENEGADE_AUDIO_COST_{name} = {value}U', self.cost)
        read = body(self.provider, 'static void Read_Audio_Cost_Flag(')
        self.assertIn('"ux0:data/renegade/user/config/audio-cost-v1.flag"', read)
        self.assertIn('unsigned mode = RENEGADE_VITA_AUDIO_COST_DEFAULT;', read)
        startup = body(self.provider, 'void AIL_startup(void)')
        self.assertIn('#if defined(__vita__)\n\tRead_Audio_Cost_Flag();', startup)
        self.assertIn('std::atomic<unsigned> g_audio_cost_mode{RENEGADE_VITA_AUDIO_COST_DEFAULT};',
                      self.provider)
        self.assertIn('RENEGADE_VITA_AUDIO_COST_DEFAULT & RENEGADE_AUDIO_COST_EXACT_DECODE_RESERVE',
                      self.decoder)

    def test_parser_contract_model(self):
        def parse(raw: bytes):
            if len(raw) != 8 or raw[:6] != b'RVAU1 ' or raw[7:8] != b'\n':
                return None
            digit = chr(raw[6])
            return int(digit, 16) if digit in '0123456789ABCDEFabcdef' else None
        self.assertEqual(parse(b'RVAU1 F\n'), 15)
        self.assertEqual(parse(b'RVAU1 0\n'), 0)
        self.assertIsNone(parse(b'RVAU1 F'))
        self.assertIsNone(parse(b'RVAU1 FF\n'))
        self.assertIsNone(parse(b'RVAU2 1\n'))
        # The C++ accepts exactly the digit ranges the model accepts.
        parse_cpp = body(self.cost, 'inline bool Renegade_Parse_Audio_Cost_Flag(')
        for token in ("digit >= '0' && digit <= '9'", "digit >= 'A' && digit <= 'F'",
                      "digit >= 'a' && digit <= 'f'"):
            self.assertIn(token, parse_cpp)

    def test_default_stream_path_is_the_original_sequence(self):
        open_body = body(self.provider, 'HSTREAM AIL_open_stream_by_sample(')
        default = open_body[open_body.index('if (cost_mode == 0U) {'):
                            open_body.index('} else if (sample != nullptr) {')]
        self.assertIn('image_loaded = sample != nullptr && Read_Stream_Image(name,\n'
                      '\t\t\tfile_open, file_close, file_seek, file_read, &image, &image_bytes,\n'
                      '\t\t\t&read_error);', default)
        self.assertIn('source_prepared = image_loaded && Prepare_Stream_Source(\n'
                      '\t\t\timage, image_bytes, &prepared);', default)
        self.assertNotIn('lease', default)
        read = body(self.provider, 'bool Read_Stream_Image(')
        self.assertIn('RenegadeAudioImageLease *lease = nullptr)',
                      self.provider[self.provider.index('bool Read_Stream_Image('):])
        self.assertIn('new (std::nothrow) uint8_t[static_cast<size_t>(file_size)]', read)
        self.assertIn('"stream image allocation failed"', read)
        # Admission is a no-op unless bit 2 marked the prepared source.
        admit = body(self.provider, 'bool Admit_Stream_Pcm_Locked(')
        self.assertTrue(admit.lstrip('{\n\t').startswith(
            'if (!prepared->second_open_admission) return true;'))
        self.assertIn('prepared->second_open_admission =\n\t\t(mode & '
                      'RENEGADE_AUDIO_COST_STREAM_SECOND_OPEN_ADMISSION) != 0U;', self.provider)
        # Sample-file and prewarm paths are untouched by RVAU1.
        for signature in ('bool Decode_Into_Sample(', 'int Renegade_Miles_Prewarm_Pcm('):
            text = body(self.provider, signature)
            for token in ('cost', 'pinned', 'lease', 'Admit_'):
                self.assertNotIn(token, text, signature)

    def test_mixer_is_not_touched(self):
        for signature in ('void Mix_Locked(', 'void Mix_Pcm_Voice(', 'void Mix_Mpeg_Voice(',
                          'void Advance_Silent_Voice(', 'bool Wrap_Voice(',
                          'void *Output_Thread('):
            text = body(self.provider, signature)
            for token in ('cost', 'pinned', 'lease', 'pool', 'RVAU1'):
                self.assertNotIn(token, text, signature)

    def test_image_pool_is_bounded_and_falls_back_to_heap(self):
        self.assertIn('RenegadeAudioImagePool<128U * 1024U, 2U> g_stream_image_pool;',
                      self.provider)
        acquire = body(self.cost, 'bool Acquire(size_t bytes, RenegadeAudioImageLease *lease)')
        for token in ('bytes > SlabBytes', 'compare_exchange_strong',
                      'new (std::nothrow) uint8_t[SlabBytes]',
                      'allocation_failures.fetch_add', 'busy.fetch_add'):
            self.assertIn(token, acquire)
        self.assertEqual(acquire.count('return false;'), 4)
        read = body(self.provider, 'bool Read_Stream_Image(')
        self.assertIn('const bool slab = lease != nullptr &&\n'
                      '\t\tg_stream_image_pool.Acquire(static_cast<size_t>(file_size), lease);',
                      read)
        self.assertIn('std::unique_ptr<uint8_t[]> pending(slab ? nullptr :', read)
        self.assertIn('if (slab) g_stream_image_pool.Release(lease);', read)
        costed = body(self.provider, 'bool Load_Stream_Source_Costed(')
        # MPEG adoption needs a heap image: copy out, release, then the
        # original preparation.
        mpeg = costed[costed.index('RenegadeVitaAudio::Is_Mpeg_Media(data, bytes)'):]
        self.assertLess(mpeg.index('std::memcpy(image.get(), lease.data, bytes);'),
                        mpeg.index('g_stream_image_pool.Release(&lease);'))
        self.assertLess(mpeg.index('g_stream_image_pool.Release(&lease);'),
                        mpeg.index('Prepare_Stream_Source(image, bytes, prepared)'))
        # The slab is returned before the open publishes.
        self.assertTrue(costed.rstrip('}\n\t ').endswith(
            'g_stream_image_pool.Release(&lease);\n\timage.reset();\n\treturn true;'))
        shutdown = body(self.provider, 'void AIL_shutdown(void)')
        self.assertIn('g_stream_image_pool.Free_Idle();', shutdown)

    def test_cache_probe_pins_before_skipping_the_decode(self):
        costed = body(self.provider, 'bool Load_Stream_Source_Costed(')
        order = ['Hash_Image(data, bytes)', 'AIL_lock();',
                 'Find_Cached_Pcm(prepared->source_hash, bytes)', '++pcm->references;',
                 'prepared->pinned = pcm;', 'AIL_unlock();',
                 'prepared->pinned != nullptr ||\n\t\tRenegadeVitaAudio::Decode_Wave_With_Info(']
        positions = [costed.index(token) for token in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('RENEGADE_AUDIO_COST_STREAM_CACHE_PROBE', costed)
        publish = body(self.provider, 'bool Publish_Stream_Source_Locked(')
        pinned = publish[publish.index('} else if (prepared->pinned != nullptr) {'):
                         publish.index('} else {\n\t\t// Preparation already performed')]
        self.assertNotIn('pcm_decodes', pinned)
        self.assertLess(pinned.index('Set_Sample_Pcm(sample, pcm);'),
                        pinned.index('Release_Pinned_Pcm_Locked(prepared);'))
        for token in ('++g_stats.pcm_cache_hits;', 'pcm->last_use = ++g_pcm_cache_clock;',
                      'sample->wave = Wave_Metadata(pcm->wave);', 'sample->mpeg.reset();',
                      'sample->encoded_data_bytes = pcm->encoded_data_bytes;'):
            self.assertIn(token, pinned)
        # A pinned entry (references >= 2) is never an eviction victim.
        room = body(self.provider, 'bool Make_Pcm_Cache_Room(')
        self.assertIn('pcm->references == 1U', room)
        open_body = body(self.provider, 'HSTREAM AIL_open_stream_by_sample(')
        tail = open_body[open_body.rindex('Release_Pinned_Pcm_Locked(&prepared);'):]
        self.assertIn('AIL_unlock();', tail)
        self.assertIn('if (prepared->cacheable && Admit_Stream_Pcm_Locked(prepared)) '
                      'Cache_Pcm(pcm);', publish)

    def test_admission_ring_is_bounded(self):
        self.assertIn('constexpr size_t kStreamSeenSlots = 64U;', self.provider)
        admit = body(self.provider, 'bool Admit_Stream_Pcm_Locked(')
        self.assertIn('(g_stream_seen_next + 1U) % kStreamSeenSlots', admit)

    def test_exact_reserve_is_flag_gated_in_decoder(self):
        decode = body(self.decoder, 'bool Decode_Wave_With_Info(')
        gated = decode[decode.index('if (g_exact_decode_reserve.load(std::memory_order_relaxed)) {'):]
        gated = gated[:gated.index('output.samples.reserve(reserve_samples);')]
        self.assertIn('Exact_Adpcm_Reserve(info, reserve_samples)', gated)
        # The fact ceiling check runs before any reserve.
        self.assertLess(decode.index('"IMA fact sample ceiling exceeded"'),
                        decode.index('output.samples.reserve(reserve_samples);'))
        exact = body(self.decoder, 'size_t Exact_Adpcm_Reserve(')
        for token in ('(microsoft ? 7U : 4U)', '(microsoft ? 2U : 1U)',
                      'remainder != 0U && remainder <= header',
                      'info.encoding == WaveEncoding::ImaAdpcm && info.channels == 1U',
                      'info.fact_sample_frames', 'kMaximumDecodedSamples'):
            self.assertIn(token, exact)
        setter = body(self.provider, 'void Renegade_Miles_Set_Audio_Cost_Mode(')
        self.assertIn('RenegadeVitaAudio::Set_Exact_Decode_Reserve(', setter)

    def test_telemetry_line(self):
        for field in ('stream_probe_hits', 'stream_pcm_deferred', 'image_pool_hits',
                      'image_pool_resident_bytes', 'exact_reserve_raises'):
            self.assertIn(field, self.stats)
        log = body(self.runtime, 'void Log_Audio_Runtime_Statistics(')
        self.assertIn('A3.5 audio-cost: reason=%s frame=%u mode=%X', log)
        self.assertIn('Renegade_Miles_Get_Audio_Cost_Stats(&cost);', log)
        # The existing audio line keeps its single sample_start_silent field.
        self.assertEqual(log.count('stats.sample_start_silent'), 1)
        self.assertIsNotNone(re.search(r'A3\.5 heap: reason=%s', log))


if __name__ == '__main__':
    unittest.main()
