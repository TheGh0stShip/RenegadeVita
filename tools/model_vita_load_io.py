#!/usr/bin/env python3
"""Pure-Python model of the Vita retail read stack for RVIO1 (load-io-v1.flag).

Models, without compiling or running game code:

* VitaSDK newlib stdio as disassembled from /usr/local/vitasdk libc.a
  (__smakebuf_r: 1024-byte buffer and __SNPT, because HAVE_BLKSIZE is unset
  and scestat_to_stat leaves st_blksize 0; _fseeko_r: SEEK_CUR flushes first,
  __SNPT/__SNBF force a plain lseek, the optimised SEEK_SET path seeks to
  target & ~1023 and refills one KiB; __sflush_r on a read stream seeks back
  to the logical position and drops the buffer; buffered fread refills one
  _bf._size block per sceIoRead, unbuffered fread reads the request at once).
* wwlib RawFileClass (biased Seek/Read, Bias via Size()) and the staged
  BufferedFileClass (16 KiB, including wwlib-a35-buffered-relative-seek).
* ChunkLoadClass header/skip traffic and a DDS-style header/seek/read.
* The synchronous loading-presenter sub-status rate limit.

The model proves byte identity between the two stdio modes for the modelled
call sequences and counts sceIo calls; it is not a timing measurement.
"""

import argparse
import mmap
import struct
import sys
from pathlib import Path

SEEK_SET, SEEK_CUR, SEEK_END = 0, 1, 2
NEWLIB_BUFSIZ = 1024
NEWLIB_BLKSIZE = 1024
BUFFERED_FILE_SIZE = 16 * 1024

DEFAULT_RETAIL = Path('/home/steve/projects/RenegadeVitaBuilder/workspace/active/retail-pc/Data')


class Syscalls:
    def __init__(self):
        self.opens = 0
        self.closes = 0
        self.reads = 0
        self.read_bytes = 0
        self.lseeks = 0
        self.fstats = 0

    def total(self):
        return self.opens + self.closes + self.reads + self.lseeks + self.fstats

    def as_dict(self):
        return dict(opens=self.opens, closes=self.closes, reads=self.reads,
                    read_bytes=self.read_bytes, lseeks=self.lseeks, fstats=self.fstats,
                    total=self.total())


class NewlibStream:
    """Read-only FILE as implemented by the VitaSDK newlib build."""

    def __init__(self, data, sys_):
        self.data = data
        self.sys = sys_
        self.phys = 0          # kernel file offset
        self.offset_known = False  # __SOFF
        self.buf = None        # None until __smakebuf_r
        self.p = 0             # consumed bytes in buf
        self.r = 0             # unread bytes in buf
        self.snpt = False
        self.sopt = False
        self.nbf = False
        self.eof = False
        self.sys.opens += 1

    # kernel primitives ---------------------------------------------------
    def _sce_read(self, n):
        self.sys.reads += 1
        chunk = self.data[self.phys:self.phys + n]
        self.phys += len(chunk)
        self.sys.read_bytes += len(chunk)
        return chunk

    def _sce_lseek(self, pos, whence):
        self.sys.lseeks += 1
        if whence == SEEK_SET:
            target = pos
        elif whence == SEEK_CUR:
            target = self.phys + pos
        else:
            target = len(self.data) + pos
        if target < 0:
            return -1
        self.phys = target
        self.offset_known = True
        return target

    def _makebuf(self):
        self.sys.fstats += 1
        self.buf = b''
        self.p = 0
        self.r = 0
        self.snpt = True

    def setvbuf_unbuffered(self):
        self._fflush()
        self.r = 0
        self.p = 0
        self.buf = b''
        self.snpt = self.sopt = self.eof = False
        self.nbf = True

    # stdio ------------------------------------------------------------
    def _refill(self):
        self.r = 0
        if self.eof:
            return False
        if self.buf is None:
            self._makebuf()
        chunk = self._sce_read(NEWLIB_BUFSIZ)
        self.buf = chunk
        self.p = 0
        self.r = len(chunk)
        if not chunk:
            self.eof = True
            return False
        return True

    def fread(self, n):
        if n <= 0:
            return b''
        out = bytearray()
        if self.nbf:
            resid = n
            while resid > 0:
                if self.eof:
                    break
                chunk = self._sce_read(resid)
                if not chunk:
                    self.eof = True
                    break
                out += chunk
                resid -= len(chunk)
            self.r = 0
            return bytes(out)
        if self.buf is None:
            self._makebuf()
        resid = n
        while resid > self.r:
            out += self.buf[self.p:self.p + self.r]
            resid -= self.r
            self.p += self.r
            self.r = 0
            if not self._refill():
                return bytes(out)
        out += self.buf[self.p:self.p + resid]
        self.p += resid
        self.r -= resid
        return bytes(out)

    def _current_physical(self):
        if self.offset_known:
            return self.phys
        return self._sce_lseek(0, SEEK_CUR)

    def _fflush(self):
        if self.nbf:
            return
        self.snpt = True
        if self.r > 0:
            logical = self._current_physical() - self.r
            self._sce_lseek(logical, SEEK_SET)
            self.snpt = False
            self.r = 0
            self.p = 0
            self.buf = b'' if self.buf is not None else None

    def _dumb(self, target):
        self._fflush()
        if self._sce_lseek(target, SEEK_SET) < 0:
            return -1
        self.p = 0
        self.r = 0
        if self.buf is not None:
            self.buf = b''
        self.eof = False
        self.snpt = False
        return 0

    def fseek(self, offset, whence):
        havepos = False
        if whence == SEEK_CUR:
            self._fflush()
            curoff = self._current_physical() - self.r
            offset += curoff
            whence = SEEK_SET
            havepos = True
        if self.buf is None and not self.nbf:
            self._makebuf()
        if self.nbf or self.snpt:
            return self._dumb(offset if whence == SEEK_SET else len(self.data) + offset)
        if not self.sopt:
            self.sys.fstats += 1
            self.sopt = True
        target = offset if whence == SEEK_SET else len(self.data) + offset
        if not havepos:
            curoff = self._current_physical() - self.r
        buffer_start = curoff - self.p
        n = self.p + self.r
        if buffer_start <= target < buffer_start + n:
            o = target - buffer_start
            self.p = o
            self.r = n - o
            self.eof = False
            return 0
        aligned = target & ~(NEWLIB_BLKSIZE - 1)
        self._sce_lseek(aligned, SEEK_SET)
        self.r = 0
        self.p = 0
        self.buf = b''
        self.eof = False
        skip = target - aligned
        if skip:
            if not self._refill() or self.r < skip:
                return self._dumb(target)
            self.p += skip
            self.r -= skip
        return 0

    def ftell(self):
        return self._current_physical() - self.r

    def fclose(self):
        self.sys.closes += 1


class RawFile:
    """wwlib RawFileClass over a newlib stream (_UNIX branch)."""

    def __init__(self, data, sys_, direct_reads=False, size_cache=None):
        self.data = data
        self.sys = sys_
        self.direct_reads = direct_reads
        self.size_cache = size_cache
        self.stream = None
        self.bias_start = 0
        self.bias_length = -1

    def is_open(self):
        return self.stream is not None

    def open(self):
        self.close()
        self.stream = NewlibStream(self.data, self.sys)
        if self.direct_reads:
            # RVIO1 bit 0: before the biased positioning seek in Open.
            self.stream.setvbuf_unbuffered()
        if self.bias_start != 0 or self.bias_length != -1:
            self.seek(0, SEEK_SET)
        return True

    def close(self):
        if self.stream is not None:
            self.stream.fclose()
            self.stream = None

    def raw_seek(self, pos, whence):
        if self.stream.fseek(pos, whence) != 0:
            return -1
        return self.stream.ftell()

    def seek(self, pos, whence=SEEK_CUR):
        if self.bias_length != -1:
            if whence == SEEK_SET:
                pos = min(pos, self.bias_length) + self.bias_start
            elif whence == SEEK_END:
                whence = SEEK_SET
                pos += self.bias_start + self.bias_length
            newpos = self.raw_seek(pos, whence) - self.bias_start
            if newpos < 0:
                newpos = self.raw_seek(self.bias_start, SEEK_SET) - self.bias_start
            if newpos > self.bias_length:
                newpos = self.raw_seek(self.bias_start + self.bias_length, SEEK_SET) - self.bias_start
            return newpos
        return self.raw_seek(pos, whence)

    def size(self):
        if self.bias_length != -1:
            return self.bias_length
        if self.is_open():
            cur = self.stream.ftell()
            self.stream.fseek(0, SEEK_END)
            end = self.stream.ftell()
            self.stream.fseek(cur, SEEK_SET)
            size = end
        else:
            self.open()
            size = self.size()
            self.close()
        self.bias_length = size - self.bias_start
        return self.bias_length

    def bias(self, start, length=-1):
        """Original RawFileClass::Bias, or the RVIO1 bit 1 shortcut."""
        if start == 0:
            self.bias_start, self.bias_length = 0, -1
            return
        if (self.size_cache is not None and self.bias_start == 0 and
                self.bias_length == -1 and not self.is_open() and 'size' in self.size_cache):
            self.bias_start = start
            bias_length = self.size_cache['size']
            if length != -1:
                bias_length = min(bias_length, length)
            self.bias_length = max(bias_length, 0)
            return
        probing = (self.size_cache is not None and self.bias_start == 0 and
                   self.bias_length == -1 and not self.is_open())
        self.bias_length = self.size()
        if probing and self.bias_length > 0:
            self.size_cache['size'] = self.bias_length
        self.bias_start += start
        if length != -1:
            self.bias_length = min(self.bias_length, length)
        self.bias_length = max(self.bias_length, 0)
        if self.is_open():
            self.seek(0, SEEK_SET)

    def read(self, size):
        if self.bias_length != -1:
            remainder = self.bias_length - self.seek(0)
            size = min(size, remainder)
        out = bytearray()
        while size > 0:
            chunk = self.stream.fread(size)
            out += chunk
            size -= len(chunk)
            if not chunk:
                break
        return bytes(out)


class BufferedFile:
    """Staged wwlib BufferedFileClass (16 KiB) over RawFile."""

    def __init__(self, raw, buffer_size=BUFFERED_FILE_SIZE):
        self.raw = raw
        self.desired = buffer_size
        self.buffer = None
        self.buffer_size = 0
        self.available = 0
        self.offset = 0

    def reset_buffer(self):
        if self.buffer is not None:
            self.buffer = None
            self.buffer_size = self.available = self.offset = 0

    def open(self):
        self.reset_buffer()
        return self.raw.open()

    def close(self):
        self.raw.close()
        self.reset_buffer()

    def read(self, size):
        out = bytearray()
        if self.available > 0:
            amount = min(size, self.available)
            out += self.buffer[self.offset:self.offset + amount]
            self.available -= amount
            self.offset += amount
            size -= amount
        if size == 0:
            return bytes(out)
        amount = self.buffer_size or self.desired
        if size > amount:
            return bytes(out) + self.raw.read(size)
        if self.buffer_size == 0:
            self.buffer_size = self.desired
            self.buffer = b''
            self.available = self.offset = 0
        if self.available == 0:
            self.buffer = self.raw.read(self.buffer_size)
            self.available = len(self.buffer)
            self.offset = 0
        if self.available > 0:
            amount = min(size, self.available)
            out += self.buffer[self.offset:self.offset + amount]
            self.available -= amount
            self.offset += amount
        return bytes(out)

    def seek(self, pos, whence=SEEK_CUR):
        if whence == SEEK_CUR and pos < 0 and self.available > 0:
            if self.raw.seek(-self.available, SEEK_CUR) < 0:
                return -1
        if whence != SEEK_CUR or pos < 0:
            self.reset_buffer()
        if self.available == 0:
            return self.raw.seek(pos, whence)
        amount = min(pos, self.available)
        pos -= amount
        self.available -= amount
        self.offset += amount
        return self.raw.seek(pos, whence) - self.available

    def tell(self):
        return self.seek(0, SEEK_CUR)

    def size(self):
        return self.raw.size()


def chunk_traversal(file, skip_type=lambda chunk_type: False, trace=None):
    """ChunkLoadClass-style walk: top-level Tell/Size, 8-byte headers, full
    leaf reads, Close_Chunk skips through Tell + Seek(SEEK_CUR)."""
    trace = trace if trace is not None else []

    def walk(limit):
        consumed = 0
        while limit is None or consumed < limit:
            if limit is None:
                position, size = file.tell(), file.size()
                trace.append(('tell', position))
                if size - position < 8:
                    return consumed
            header = file.read(8)
            trace.append(('header', header))
            if len(header) != 8:
                return consumed
            chunk_type, raw_size = struct.unpack('<II', header)
            chunk_size = raw_size & 0x7FFFFFFF
            remaining = None if limit is None else limit - consumed - 8
            if remaining is not None and chunk_size > remaining:
                return consumed
            position_in_chunk = 0
            if raw_size & 0x80000000:
                position_in_chunk = walk(chunk_size)
            elif not skip_type(chunk_type):
                payload = file.read(chunk_size)
                trace.append(('payload', payload))
                position_in_chunk = len(payload)
            if position_in_chunk < chunk_size:
                before = file.tell()
                after = file.seek(chunk_size - position_in_chunk, SEEK_CUR)
                trace.append(('skip', before, after))
            consumed += 8 + chunk_size
        return consumed

    walk(None)
    return trace


def dds_pattern(file, trace=None):
    """ddsfile.cpp: 4 + 124 header bytes, skip to data, one large read."""
    trace = trace if trace is not None else []
    head = file.read(4 + 124)
    trace.append(('dds-header', head))
    data_size = max(file.size() - 128, 0)
    trace.append(('dds-seek', file.seek(0, SEEK_CUR)))
    trace.append(('dds-data', file.read(data_size)))
    return trace


def replay_member(archive, start, length, pattern, direct_reads, size_cache=None,
                  syscalls=None, skip_type=lambda chunk_type: False):
    syscalls = syscalls if syscalls is not None else Syscalls()
    raw = RawFile(archive, syscalls, direct_reads=direct_reads, size_cache=size_cache)
    raw.bias(start, length)
    file = BufferedFile(raw)
    file.open()
    trace = chunk_traversal(file, skip_type) if pattern == 'chunk' else dds_pattern(file)
    file.close()
    return trace, syscalls


class MixArchive:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path, 'rb') as handle:
            # always.dat is ~578 MB; map it instead of reading it.
            self.data = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        signature, header_offset, names_offset = struct.unpack_from('<4sii', self.data, 0)
        if signature != b'MIX1':
            raise ValueError('not a MIX1 archive: %s' % path)
        count, = struct.unpack_from('<i', self.data, header_offset)
        infos = [struct.unpack_from('<III', self.data, header_offset + 4 + 12 * i)
                 for i in range(count)]
        name_count, = struct.unpack_from('<i', self.data, names_offset)
        cursor = names_offset + 4
        names = []
        for _ in range(name_count):
            length = self.data[cursor]
            names.append(self.data[cursor + 1:cursor + 1 + length].rstrip(b'\0').decode('latin1'))
            cursor += 1 + length
        self.entries = {name.lower(): (offset, size)
                        for (crc, offset, size), name in zip(infos, names)}

    def member(self, name):
        return self.entries.get(name.lower())


def dependency_names(dep_bytes):
    """Filenames in a .dep CHUNKID_FILE_LIST (micro chunk id 1)."""
    chunk_type, raw_size = struct.unpack_from('<II', dep_bytes, 0)
    if chunk_type != 0x04020527:
        raise ValueError('unexpected dependency chunk %08X' % chunk_type)
    end = 8 + (raw_size & 0x7FFFFFFF)
    cursor = 8
    names = []
    while cursor + 2 <= end:
        micro_id, micro_size = dep_bytes[cursor], dep_bytes[cursor + 1]
        payload = dep_bytes[cursor + 2:cursor + 2 + micro_size]
        if micro_id == 1:
            names.append(payload.rstrip(b'\0').decode('latin1'))
        cursor += 2 + micro_size
    return names


def tutorial_members(retail):
    """(archive, offset, size, pattern) for the M00 dependency list (in the
    Vita factory-list order Always2.dat, always.dbs, Always.dat, M00) plus the
    tutorial MIX's own lightmap DDS members."""
    retail = Path(retail)
    order = [MixArchive(retail / name) for name in
             ('Always2.dat', 'always.dbs', 'always.dat', 'M00_Tutorial.mix')]
    m00 = order[-1]
    dep_offset, dep_size = m00.member('m00_tutorial.dep')
    names = dependency_names(m00.data[dep_offset:dep_offset + dep_size])
    members = []
    seen = set()
    for name in names:
        base = name.replace('\\', '/').split('/')[-1]
        # Load_Assets skips render objects that already exist.
        if base.lower() in seen:
            continue
        seen.add(base.lower())
        for archive in order:
            entry = archive.member(base)
            if entry is not None:
                members.append((archive, entry[0], entry[1], 'chunk', base))
                break
    for name, (offset, size) in sorted(m00.entries.items()):
        if name.endswith('.dds'):
            members.append((m00, offset, size, 'dds', name))
    return names, members


def compare_modes(members, skip_type=lambda chunk_type: (chunk_type % 7) == 0):
    original, direct = Syscalls(), Syscalls()
    mismatches = []
    for archive, offset, size, pattern, name in members:
        a, _ = replay_member(archive.data, offset, size, pattern, False,
                             syscalls=original, skip_type=skip_type)
        b, _ = replay_member(archive.data, offset, size, pattern, True,
                             syscalls=direct, skip_type=skip_type)
        if a != b:
            mismatches.append(name)
    return original, direct, mismatches


def archive_opens(members):
    """Native opens for Bias + Open of every member: original vs size reuse."""
    original, reuse = Syscalls(), Syscalls()
    caches = {}
    for archive, offset, size, pattern, name in members:
        raw = RawFile(archive.data, original)
        raw.bias(offset, size)
        cache = caches.setdefault(archive.path, {})
        shortcut = RawFile(archive.data, reuse, size_cache=cache)
        shortcut.bias(offset, size)
        if (raw.bias_start, raw.bias_length) != (shortcut.bias_start, shortcut.bias_length):
            raise AssertionError('bias mismatch for %s' % name)
        for item in (raw, shortcut):
            item.open()
            item.close()
    return original, reuse


def presenter_renders(events, interval_us, render_us):
    """Replay loading callbacks. events: (work_us_before, minimum_progress).
    Returns (renders, milestone_renders, total_us, max_gap_us)."""
    now = 0
    last_render = None
    renders = milestones = 0
    max_gap = 0
    previous_render_end = 0
    for work_us, minimum_progress in events:
        now += work_us
        if minimum_progress < 0 and last_render is not None and now - last_render < interval_us:
            continue
        max_gap = max(max_gap, now - previous_render_end)
        last_render = now
        now += render_us
        previous_render_end = now
        renders += 1
        if minimum_progress >= 0:
            milestones += 1
    return renders, milestones, now, max_gap


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--retail', default=str(DEFAULT_RETAIL))
    args = parser.parse_args(argv)
    retail = Path(args.retail)
    if not (retail / 'M00_Tutorial.mix').is_file():
        print('retail data not found: %s' % retail)
        return 1
    names, members = tutorial_members(retail)
    chunk_bytes = sum(size for _, _, size, pattern, _ in members if pattern == 'chunk')
    dds_bytes = sum(size for _, _, size, pattern, _ in members if pattern == 'dds')
    print('M00 dependency list: %d names, %d resolved W3D members (%d bytes), '
          '%d tutorial DDS members (%d bytes)' % (
              len(names), sum(1 for m in members if m[3] == 'chunk'), chunk_bytes,
              sum(1 for m in members if m[3] == 'dds'), dds_bytes))
    original, direct, mismatches = compare_modes(members)
    print('stdio buffered (original): %s' % original.as_dict())
    print('stdio unbuffered (RVIO1 1): %s' % direct.as_dict())
    print('byte-identical traces: %s' % ('yes' if not mismatches else 'NO: %s' % mismatches))
    opens_original, opens_reuse = archive_opens(members)
    print('Bias+Open native opens original=%d size-reuse=%d' % (
        opens_original.opens, opens_reuse.opens))
    return 0 if not mismatches else 2


if __name__ == '__main__':
    sys.exit(main())
