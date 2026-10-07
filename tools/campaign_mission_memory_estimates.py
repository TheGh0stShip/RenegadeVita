#!/usr/bin/env python3
"""Read-only per-mission resident memory estimator (metadata only, no export).

Reads MIX1 indexes plus DDS/TGA/WAV headers and W3D chunk names from an
unchanged retail Data directory and prints a Markdown report of numbers. No
retail payload is written anywhere. Estimates follow the Vita texture upload
paths in port/renderer/vita/ww3d_dx8_boundary.cpp (static analysis, not
hardware measurement).
"""
from __future__ import annotations

import argparse
import re
import struct
from collections import Counter
from pathlib import Path

from renegade_cinematic_dependency_scan import MixArchive, level_asset_dependencies

MIB = 1024.0 * 1024.0
MISSIONS = ["M00_Tutorial", "M01", "M02", "M03", "M04", "M05", "M06",
            "M07", "M08", "M09", "M10", "M11", "M13"]
SHARED = ["Always2.dat", "always3.dat", "always.dat"]  # lookup priority after mission mix


def mip_chain_blocks(width, height, block_bytes):
    total, levels = 0, 0
    w, h = width, height
    while w >= 4 and h >= 4:
        total += (w // 4) * (h // 4) * block_bytes
        levels += 1
        if w == 4 and h == 4:
            break
        w = max(w // 2, 1)
        h = max(h // 2, 1)
    return total, levels


def rgba_chain(width, height, mips):
    total, w, h = 0, width, height
    for _ in range(max(mips, 1)):
        total += w * h * 4
        if w == 1 and h == 1:
            break
        w = max(w >> 1, 1)
        h = max(h >> 1, 1)
    return total


def full_mips(width, height):
    count, w, h = 1, width, height
    while w > 1 or h > 1:
        w, h = max(w >> 1, 1), max(h >> 1, 1)
        count += 1
    return count


def is_pot(v):
    return v > 0 and (v & (v - 1)) == 0


def classify_texture(kind, header, file_bytes):
    """Return dict(name-less): w,h,fmt,gpu,cpu (bytes), path."""
    if kind == "dds":
        if len(header) < 128 or header[:4] != b"DDS ":
            return None
        height, width = struct.unpack_from("<II", header, 12)
        mips = max(struct.unpack_from("<I", header, 28)[0], 1)
        flags = struct.unpack_from("<I", header, 80)[0]
        fourcc = header[84:88].decode("latin1") if flags & 4 else "RGB"
        bpp = struct.unpack_from("<I", header, 88)[0]
        fmt = fourcc if flags & 4 else "RAW%d" % bpp
        native = fourcc in ("DXT1", "DXT5") and is_pot(width) and is_pot(height) \
            and width <= 2048 and height <= 2048 and width >= 4 and height >= 4
        if native:
            gpu, _ = mip_chain_blocks(width, height, 8 if fourcc == "DXT1" else 16)
            # clamp to the stored mip count when the file carries fewer levels
            if mips < full_mips(width, height):
                gpu, w, h = 0, width, height
                for _ in range(mips):
                    if w < 4 or h < 4:
                        break
                    gpu += (w // 4) * (h // 4) * (8 if fourcc == "DXT1" else 16)
                    w, h = w >> 1, h >> 1
            return dict(w=width, h=height, fmt=fmt, mips=mips, gpu=gpu, cpu=0, path="native-dxt")
        rgba = rgba_chain(width, height, mips)
        return dict(w=width, h=height, fmt=fmt, mips=mips, gpu=rgba, cpu=rgba, path="decode-rgba")
    if kind == "tga":
        if len(header) < 18:
            return None
        id_len, cmap, itype = header[0], header[1], header[2]
        width, height = struct.unpack_from("<HH", header, 12)
        bpp = header[16]
        # Create_Texture_From_Surface uploads level 0 only as RGBA8888 and keeps
        # one copy of the source-format surface in the C heap.
        src_bytes = {8: 1, 15: 2, 16: 2, 24: 3, 32: 4}.get(bpp, 4)
        return dict(w=width, h=height, fmt="TGA%d%s" % (bpp, "rle" if itype >= 8 else ""),
                    mips=1, gpu=width * height * 4, cpu=width * height * src_bytes,
                    path="tga-rgba")
    return None


class Source:
    def __init__(self, path):
        self.path = path
        self.archive = MixArchive(path)
        self.fh = path.open("rb")

    def has(self, name):
        return name.lower() in self.archive.entries

    def size(self, name):
        return self.archive.entries[name.lower()][2]

    def read(self, name, limit=None):
        _, offset, size = self.archive.entries[name.lower()]
        self.fh.seek(offset)
        return self.fh.read(size if limit is None else min(limit, size))


def wav_info(blob):
    """Return (pcm16_bytes, data_bytes, tag, channels, rate) or None."""
    if len(blob) < 44 or blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        return None
    pos, fmt, data_bytes = 12, None, None
    while pos + 8 <= len(blob):
        cid, csize = blob[pos:pos + 4], struct.unpack_from("<I", blob, pos + 4)[0]
        body = pos + 8
        if cid == b"fmt " and body + 16 <= len(blob):
            tag, ch, rate, _, align, bits = struct.unpack_from("<HHIIHH", blob, body)
            spb = struct.unpack_from("<H", blob, body + 20)[0] if csize >= 22 and body + 22 <= len(blob) else 0
            fmt = (tag, ch, rate, align, bits, spb)
        elif cid == b"data":
            data_bytes = csize
            break
        pos = body + csize + (csize & 1)
    if fmt is None or data_bytes is None:
        return None
    tag, ch, rate, align, bits, spb = fmt
    if tag in (0x11, 0x02) and align:
        if tag == 0x11 and spb:
            samples = (data_bytes // align) * spb
        else:
            samples = (data_bytes // align) * max(2 * (align - 7 * ch) // ch + 2, 1) if tag == 0x02 else data_bytes * 2 // ch
        pcm = samples * ch * 2
    elif tag == 1 and bits:
        pcm = data_bytes if bits == 16 else data_bytes * (16 // bits)
    else:
        pcm = data_bytes * 4
    return pcm, data_bytes, tag, ch, rate


def w3d_references(blob):
    """Texture, HLOD sub-object and emitter texture names (lowercase)."""
    tex, subs = set(), set()
    pos, stack, end = 0, [], len(blob)
    # iterative walk so deep files do not recurse
    work = [(0, len(blob))]
    while work:
        start, stop = work.pop()
        p = start
        while p + 8 <= stop:
            kind, size = struct.unpack_from("<II", blob, p)
            body_end = p + 8 + (size & 0x7FFFFFFF)
            if body_end > stop:
                break
            if kind == 0x32:
                v = blob[p + 8:body_end].split(b"\0", 1)[0].decode("latin1").lower()
                if v:
                    tex.add(v)
            elif kind == 0x503 and body_end - p - 8 >= 260:
                v = blob[p + 8:p + 8 + 260].split(b"\0", 1)[0].decode("latin1").lower()
                if v:
                    tex.add(v)
            elif kind == 0x704 and body_end - p - 8 == 36:
                v = blob[p + 12:p + 44].split(b"\0", 1)[0].decode("latin1").lower()
                if v:
                    subs.add(v)
            if size & 0x80000000:
                work.append((p + 8, body_end))
            p = body_end
    return tex, subs


AUDIO_RE = re.compile(rb"[A-Za-z0-9_\-\. ]{1,60}\.(?:wav|mp3)", re.I)


def analyse_mission(name, data_dir, shared):
    src = Source(data_dir / (name + ".mix"))
    arch = src.archive
    suffix_n, suffix_b = Counter(), Counter()
    for entry, _, _, size in arch.entry_records:
        s = Path(entry).suffix.lower()
        suffix_n[s] += 1
        suffix_b[s] += size
    result = dict(name=name, mix_bytes=data_dir.joinpath(name + ".mix").stat().st_size,
                  entries=len(arch.entry_records), suffix_n=suffix_n, suffix_b=suffix_b)

    # --- local texture inventory (everything stored in the mission MIX) -------
    local_tex = []
    for entry, _, off, size in arch.entry_records:
        ext = Path(entry).suffix.lower()
        if ext not in (".dds", ".tga"):
            continue
        src.fh.seek(off)
        info = classify_texture(ext[1:], src.fh.read(128), size)
        if info:
            info.update(name=entry, file_bytes=size, ext=ext)
            local_tex.append(info)
    result["local_tex"] = local_tex

    # --- dependency closure (original .dep drives preload) -------------------
    sources = [src] + shared

    def find(entry):
        for s in sources:
            if s.has(entry):
                return s
        return None

    try:
        dep = level_asset_dependencies(arch)["files"]
    except Exception:
        dep = []
    queue = [d.lower() for d in dep if d]
    seen_w3d, w3d_bytes_local, w3d_bytes_shared = set(), 0, 0
    textures = set()
    missing_w3d = set()
    while queue:
        item = queue.pop()
        cands = [item] if item.endswith(".w3d") else [item, item + ".w3d"]
        s = None
        for cand in cands:
            s = find(cand)
            if s:
                item = cand
                break
        if s is None:
            missing_w3d.add(item)
            continue
        if item in seen_w3d:
            continue
        seen_w3d.add(item)
        size = s.size(item)
        if s is src:
            w3d_bytes_local += size
        else:
            w3d_bytes_shared += size
        blob = s.read(item)
        tex, subs = w3d_references(blob)
        textures |= tex
        for sub in subs:
            for part in {sub.split(".")[0], sub.split(".")[-1], sub}:
                if part and part + ".w3d" not in seen_w3d and find(part + ".w3d"):
                    queue.append(part + ".w3d")
    result.update(dep_count=len(dep), w3d_closure=len(seen_w3d), w3d_local=w3d_bytes_local,
                  w3d_shared=w3d_bytes_shared, w3d_missing=len(missing_w3d))

    resolved, unresolved = [], 0
    for t in sorted(textures):
        stem = t.rsplit(".", 1)[0]
        hit = None
        for ext in (".dds", ".tga"):
            s = find(stem + ext)
            if s:
                hit = (s, stem + ext, ext)
                break
        if hit is None:
            unresolved += 1
            continue
        s, entry, ext = hit
        _, off, size = s.archive.entries[entry]
        s.fh.seek(off)
        info = classify_texture(ext[1:], s.fh.read(128), size)
        if info:
            info.update(name=entry, file_bytes=size, ext=ext, local=(s is src))
            resolved.append(info)
    result["closure_tex"] = resolved
    result["tex_unresolved"] = unresolved

    # --- audio -----------------------------------------------------------------
    local_audio = dict(n=0, comp=0, pcm=0, mp3=0)
    for entry, _, off, size in arch.entry_records:
        ext = Path(entry).suffix.lower()
        if ext == ".wav":
            src.fh.seek(off)
            w = wav_info(src.fh.read(min(size, 4096)))
            local_audio["n"] += 1
            local_audio["comp"] += size
            local_audio["pcm"] += w[0] if w else size * 4
        elif ext == ".mp3":
            local_audio["mp3"] += size
    result["local_audio"] = local_audio

    # level-data string references to shared audio (lower bound)
    refs = set()
    for entry, _, off, size in arch.entry_records:
        if Path(entry).suffix.lower() in (".ldd", ".lsd", ".txt", ".dep"):
            src.fh.seek(off)
            for m in AUDIO_RE.finditer(src.fh.read(size)):
                refs.add(m.group(0).decode("latin1").strip().lower())
    ref_audio = dict(names=0, found_local=0, found_shared=0, wav_n=0, wav_comp=0, wav_pcm=0,
                     mp3_n=0, mp3_bytes=0, wav_max_pcm=0, wav_max_name="")
    for ref in sorted(refs):
        s = find(ref)
        if s is None:
            continue
        ref_audio["names"] += 1
        ref_audio["found_local" if s is src else "found_shared"] += 1
        if ref.endswith(".mp3"):
            ref_audio["mp3_n"] += 1
            ref_audio["mp3_bytes"] += s.size(ref)
        else:
            w = wav_info(s.read(ref, 4096))
            pcm = w[0] if w else s.size(ref) * 4
            ref_audio["wav_n"] += 1
            ref_audio["wav_comp"] += s.size(ref)
            ref_audio["wav_pcm"] += pcm
            if pcm > ref_audio["wav_max_pcm"]:
                ref_audio["wav_max_pcm"], ref_audio["wav_max_name"] = pcm, ref
    result["ref_audio"] = ref_audio
    src.fh.close()
    return result


def fmt_mib(value):
    return "%.2f" % (value / MIB)


def render(results, shared_info, data_dir_label):
    m13 = next(r for r in results if r["name"] == "M13")

    def tex_totals(r):
        t = r["closure_tex"]
        gpu = sum(x["gpu"] for x in t)
        cpu = sum(x["cpu"] for x in t)
        return gpu, cpu

    def heap_proxy(r):
        gpu, cpu = tex_totals(r)
        lvl = r["suffix_b"][".lsd"] + r["suffix_b"][".ldd"]
        w3d = r["w3d_local"] + r["w3d_shared"]
        return lvl + w3d + cpu + r["local_audio"]["pcm"]

    rows = []
    for r in results:
        gpu, cpu = tex_totals(r)
        rows.append(dict(r=r, gpu=gpu, cpu=cpu, heap=heap_proxy(r)))
    base_gpu = next(x for x in rows if x["r"]["name"] == "M13")["gpu"]
    base_heap = next(x for x in rows if x["r"]["name"] == "M13")["heap"]
    for x in rows:
        x["gpu_ratio"] = x["gpu"] / base_gpu if base_gpu else 0.0
        x["heap_ratio"] = x["heap"] / base_heap if base_heap else 0.0
        x["score"] = max(x["gpu_ratio"], x["heap_ratio"])
    ranked = sorted(rows, key=lambda x: -x["score"])

    out = []
    w = out.append
    w("# Campaign mission memory estimates")
    w("")
    w("Status: static, read-only estimate from MIX/DDS/TGA/WAV/W3D headers of an unchanged retail")
    w("Data directory (`%s`). Numbers only: no retail bytes, names beyond file names, or" % data_dir_label)
    w("thumbnails are stored. Host/static analysis; **not a hardware measurement**. M13 is the")
    w("only campaign level known to load on physical Vita and is the 1.00x baseline. M00 is shown")
    w("as a second reference. Regenerate with")
    w("`python3 tools/campaign_mission_memory_estimates.py --data-dir <Data> --output reports/campaign/MISSION_MEMORY_ESTIMATES.md`.")
    w("")
    w("## Method and assumptions")
    w("")
    w("- Texture residency follows `port/renderer/vita/ww3d_dx8_boundary.cpp`: power-of-two DXT1/DXT5")
    w("  DDS (4 <= side <= 2048) uploads DXT blocks unchanged (`native-dxt`; GPU bytes = block chain over")
    w("  the stored mips, no retained CPU copy). Uncompressed/DXT3/non-power-of-two DDS takes the RGBA8888")
    w("  decode path (`decode-rgba`): GPU bytes = `sum(w*h*4)` over the mip chain plus an equal retained")
    w("  CPU surface chain. TGA (`tga-rgba`, `Create_Texture_From_Surface`) uploads **level 0 only** as")
    w("  RGBA8888 (GPU bytes = `w*h*4`, no mips) and retains one source-format surface copy in the C heap")
    w("  (`w*h*{1,2,3,4}` for 8/16/24/32-bit TGA). Retained-surface sizes are from source reading, not measured.")
    w("- Closure set: the original per-level `.dep` W3D list, plus HLOD sub-object W3Ds found in")
    w("  the mission MIX or the shared archives, plus every texture name (`W3D_CHUNK_TEXTURE_NAME`,")
    w("  emitter texture) those W3Ds carry. `.tga` names resolve through the `.dds` alias first, then")
    w("  `.tga`, searching mission MIX, `Always2.dat`, `always3.dat`, `always.dat`. This approximates")
    w("  the texture hash the Vita loader walks in `Warm_Original_Campaign_Referenced_Textures`")
    w("  (48 MiB extra-prepare budget, 24 MiB vitaGL free floor). It excludes HUD/UI, characters spawned")
    w("  from definitions only in `always.dbs`, effects spawned by scripts, and cinematic-only assets.")
    w("- Heap proxy (main 192 MiB newlib heap): `.lsd + .ldd` bytes + W3D closure file bytes +")
    w("  retained CPU texture copies + decoded PCM of mission-local WAVs. W3D/LSD in-memory expansion")
    w("  factors are unknown and treated as 1.0x; this is a relative ranking input, not an absolute")
    w("  total. It omits the engine/physics baseline, vitaGL meshes, and streamed dialogue.")
    w("- Risk score = max(GPU texture ratio, heap-proxy ratio), each relative to M13.")
    w("- Audio: WAV PCM16 size derived from the fmt/fact fields (IMA/MS ADPCM about 4x). MP3 is")
    w("  streamed through the MPEG path and is not counted as resident PCM. Shared dialogue is referenced")
    w("  by name from level data (`.ldd/.lsd/.txt/.dep` strings); this is a lower bound because")
    w("  most sound/conversation definitions live in `always.dbs`.")
    w("")
    w("Vita budgets for context: newlib heap 192 MiB (`a30_main.cpp`), vitaGL extended init with 4 MiB")
    w("legacy pool and a 16 MiB RAM threshold (`ww3d_vita_renderer.cpp`), texture prepare 48 MiB,")
    w("static mesh cache 24 MiB.")
    w("")
    w("## Ranking against M13")
    w("")
    w("| Rank | Mission | Score vs M13 | GPU tex ratio | Heap ratio | Closure GPU tex MiB | Heap proxy MiB | Main driver |")
    w("|---:|---|---:|---:|---:|---:|---:|---|")
    for i, x in enumerate(ranked, 1):
        r = x["r"]
        tga = [t for t in r["closure_tex"] if t["path"] != "native-dxt"]
        drivers = []
        if x["gpu_ratio"] >= x["heap_ratio"]:
            drivers.append("GPU textures")
        else:
            drivers.append("heap proxy")
        if tga:
            drivers.append("%d non-native tex = %s MiB GPU + %s MiB CPU-retained" % (
                len(tga), fmt_mib(sum(t["gpu"] for t in tga)), fmt_mib(sum(t["cpu"] for t in tga))))
        w("| %d | %s | %.2fx | %.2fx | %.2fx | %s | %s | %s |" % (
            i, r["name"], x["score"], x["gpu_ratio"], x["heap_ratio"],
            fmt_mib(x["gpu"]), fmt_mib(x["heap"]), "; ".join(drivers)))
    w("")
    base = next(x for x in rows if x["r"]["name"] == "M13")
    by = {x["r"]["name"]: x for x in rows}

    def band(x):
        return "high" if x["score"] >= 5.0 else "medium" if x["score"] >= 2.0 else "low"

    w("## Findings (computed from the tables below)")
    w("")
    w("- M13 baseline: closure GPU textures %s MiB (%d resolved names), heap proxy %s MiB. M00 sits at %.2fx." % (
        fmt_mib(base["gpu"]), len(base["r"]["closure_tex"]), fmt_mib(base["heap"]), by["M00_Tutorial"]["score"]))
    w("- Risk bands (score >= 5.0x high, >= 2.0x medium, else low): " + "; ".join(
        "%s %s" % (b, ", ".join(x["r"]["name"] for x in ranked if band(x) == b and x["r"]["name"] != "M13"))
        for b in ("high", "medium", "low")) + ".")
    for name in ("M08", "M09"):
        x = by[name]
        non = [t for t in x["r"]["closure_tex"] if t["path"] != "native-dxt"]
        w("- %s: %d non-native (TGA) closure textures = %s MiB GPU RGBA8888 (level 0 only) + %s MiB retained"
          " CPU copies; closure GPU total %s MiB vs the 48 MiB prepare budget. The DXT share is only %s MiB." % (
              name, len(non), fmt_mib(sum(t["gpu"] for t in non)), fmt_mib(sum(t["cpu"] for t in non)),
              fmt_mib(x["gpu"]), fmt_mib(sum(t["gpu"] for t in x["r"]["closure_tex"] if t["path"] == "native-dxt"))))
    w("- The M08/M09 TGAs are 256x256 16-bit images expanded to 4 bytes per pixel on upload; a 16-bit")
    w("  GL upload format or skipping the retained surface copy would roughly halve GPU or heap cost")
    w("  (candidate mitigations only; not evaluated and not applied).")
    w("- Medium-band missions are driven by `.lsd/.ldd` bytes and W3D closure size (largest: M02 and M01),")
    w("  not textures; their closure textures are DXT-native and only %s-%s MiB." % (
        fmt_mib(min(by[n]["gpu"] for n in ("M01", "M02", "M03", "M07", "M10"))),
        fmt_mib(max(by[n]["gpu"] for n in ("M01", "M02", "M03", "M07", "M10")))))
    w("- Context pool sizes: a Vita3K dev148 log (128 MiB heap, not physical) reported vitaGL RAM 112 MiB,")
    w("  VRAM 110 MiB, phycont 26 MiB. Physical pool sizes with the current 192 MiB heap have not been")
    w("  measured here; the closure GPU numbers above should be compared to a physical")
    w("  `texture_bytes_resident` for M13 before treating any absolute threshold as safe.")
    w("")
    w("## Per-mission archive inventory")
    w("")
    w("| Mission | MIX MiB | Entries | .dds n / MiB | .tga n / MiB | .w3d n / MiB | .wav n / MiB | .lsd MiB | .ldd MiB | .txt n / KiB |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        sn, sb = r["suffix_n"], r["suffix_b"]
        w("| %s | %s | %d | %d / %s | %d / %s | %d / %s | %d / %s | %s | %s | %d / %.1f |" % (
            r["name"], fmt_mib(r["mix_bytes"]), r["entries"],
            sn[".dds"], fmt_mib(sb[".dds"]), sn[".tga"], fmt_mib(sb[".tga"]),
            sn[".w3d"], fmt_mib(sb[".w3d"]), sn[".wav"], fmt_mib(sb[".wav"]),
            fmt_mib(sb[".lsd"]), fmt_mib(sb[".ldd"]), sn[".txt"], sb[".txt"] / 1024.0))
    w("")
    w("Shared archives (always present, mounted for every level):")
    w("")
    w("| Archive | MiB | Entries | .dds n / MiB | .tga n / MiB | .w3d n / MiB | .wav n / MiB | .mp3 n / MiB |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in shared_info:
        sn, sb = s["suffix_n"], s["suffix_b"]
        w("| %s | %s | %d | %d / %s | %d / %s | %d / %s | %d / %s | %d / %s |" % (
            s["name"], fmt_mib(s["bytes"]), s["entries"], sn[".dds"], fmt_mib(sb[".dds"]),
            sn[".tga"], fmt_mib(sb[".tga"]), sn[".w3d"], fmt_mib(sb[".w3d"]),
            sn[".wav"], fmt_mib(sb[".wav"]), sn[".mp3"], fmt_mib(sb[".mp3"])))
    w("")
    w("## Mission-local textures (everything stored in the mission MIX)")
    w("")
    w("| Mission | Textures | Native DXT n | Native GPU MiB | Non-native n | Non-native GPU MiB | Non-native CPU-retained MiB | Largest dims (w x h, fmt) |")
    w("|---|---:|---:|---:|---:|---:|---:|---|")
    for r in results:
        lt = r["local_tex"]
        nat = [t for t in lt if t["path"] == "native-dxt"]
        non = [t for t in lt if t["path"] != "native-dxt"]
        biggest = max(lt, key=lambda t: t["w"] * t["h"]) if lt else None
        w("| %s | %d | %d | %s | %d | %s | %s | %s |" % (
            r["name"], len(lt), len(nat), fmt_mib(sum(t["gpu"] for t in nat)),
            len(non), fmt_mib(sum(t["gpu"] for t in non)), fmt_mib(sum(t["cpu"] for t in non)),
            "%dx%d %s" % (biggest["w"], biggest["h"], biggest["fmt"]) if biggest else "-"))
    w("")
    w("## Dependency-closure texture residency (resident-set estimate)")
    w("")
    w("| Mission | .dep names | W3D closure n | W3D local MiB | W3D shared MiB | Unresolved W3D | Textures resolved | Unresolved tex names | Native DXT GPU MiB | Non-native GPU MiB | Non-native CPU MiB | Total GPU MiB | Of which local-MIX MiB |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for x in rows:
        r = x["r"]
        t = r["closure_tex"]
        nat = sum(i["gpu"] for i in t if i["path"] == "native-dxt")
        non = sum(i["gpu"] for i in t if i["path"] != "native-dxt")
        noncpu = sum(i["cpu"] for i in t)
        loc = sum(i["gpu"] for i in t if i.get("local"))
        w("| %s | %d | %d | %s | %s | %d | %d | %d | %s | %s | %s | %s | %s |" % (
            r["name"], r["dep_count"], r["w3d_closure"], fmt_mib(r["w3d_local"]),
            fmt_mib(r["w3d_shared"]), r["w3d_missing"], len(t), r["tex_unresolved"],
            fmt_mib(nat), fmt_mib(non), fmt_mib(noncpu), fmt_mib(x["gpu"]), fmt_mib(loc)))
    w("")
    w("Total GPU above the 48 MiB prepare budget means the loader defers textures (lazy upload on")
    w("first draw); deferred textures still allocate GPU memory when first drawn, so the budget")
    w("only moves the cost into gameplay frames.")
    w("")
    w("## Largest closure textures per mission (top 5 by GPU bytes)")
    w("")
    for x in rows:
        r = x["r"]
        top = sorted(r["closure_tex"], key=lambda t: -t["gpu"])[:5]
        w("- **%s**: " % r["name"] + "; ".join(
            "%s %dx%d %s %s MiB%s" % (t["name"], t["w"], t["h"], t["fmt"],
                                      fmt_mib(t["gpu"]), "" if t["path"] == "native-dxt" else " (+CPU)")
            for t in top))
    w("")
    w("## Audio")
    w("")
    w("| Mission | Local WAV n | Local WAV MiB (file) | Local WAV decoded PCM16 MiB | Local MP3 MiB | Level-referenced shared WAV n | Shared WAV file MiB | Shared WAV PCM16 MiB | Largest referenced WAV PCM MiB | Referenced MP3 n / MiB |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in results:
        a, b = r["local_audio"], r["ref_audio"]
        w("| %s | %d | %s | %s | %s | %d | %s | %s | %s | %d / %s |" % (
            r["name"], a["n"], fmt_mib(a["comp"]), fmt_mib(a["pcm"]), fmt_mib(a["mp3"]),
            b["wav_n"], fmt_mib(b["wav_comp"]), fmt_mib(b["wav_pcm"]),
            fmt_mib(b["wav_max_pcm"]), b["mp3_n"], fmt_mib(b["mp3_bytes"])))
    w("")
    w("Per `reports/AUDIO_STREAM_MEMORY.md`, WAV streams currently decode fully to PCM16 on open")
    w("(sources over 1 MiB bypass the 4 MiB PCM cache), so concurrent-stream peak is the practical")
    w("audio risk, not the per-level file totals above.")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = args.data_dir

    shared, shared_info = [], []
    for name in ("always.dat", "Always2.dat", "always3.dat"):
        path = data / name
        if not path.exists():
            continue
        src = Source(path)
        sn, sb = Counter(), Counter()
        for entry, _, _, size in src.archive.entry_records:
            s = Path(entry).suffix.lower()
            sn[s] += 1
            sb[s] += size
        shared_info.append(dict(name=name, bytes=path.stat().st_size,
                                entries=len(src.archive.entry_records), suffix_n=sn, suffix_b=sb))
        shared.append(src)
    order = {"always2.dat": 0, "always3.dat": 1, "always.dat": 2}
    shared.sort(key=lambda s: order.get(s.path.name.lower(), 9))

    results = [analyse_mission(name, data, shared) for name in MISSIONS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(results, shared_info, "retail Data tree"), encoding="utf-8")
    print("wrote", args.output)


if __name__ == "__main__":
    main()
