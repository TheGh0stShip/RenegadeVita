#!/usr/bin/env python3
"""Execute the pinned user's TT routine in isolated x86 emulation, synthetic inputs only.

No DLL entry point, registry, filesystem, sockets or user credentials are exposed.
Requires pefile and unicorn in a research-only environment. No TT code is copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

PIN = "d520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db"


def reference(image, seed, challenge, nonce):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x40000)
    cpu.mem_map(0x200000, 0x10000)
    cpu.mem_map(0x300000, 0x10000)
    hooks = {}
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for symbol in entry.imports:
            address = 0x300000 + 16 * len(hooks)
            hooks[address] = symbol.name.decode() if symbol.name else "ordinal"
            cpu.mem_write(symbol.address, struct.pack("<I", address))
    randoms = iter((nonce >> 16, nonce & 65535))

    def word(address):
        return struct.unpack("<I", cpu.mem_read(address, 4))[0]

    def string(address):
        value = bytearray()
        for index in range(1024):
            byte = cpu.mem_read(address + index, 1)[0]
            if not byte:
                return bytes(value)
            value.append(byte)
        raise RuntimeError("Unterminated oracle string")

    def imported(machine, address, size, unused):
        if address not in hooks:
            return
        stack = machine.reg_read(UC_X86_REG_ESP)
        arg = lambda index: word(stack + 4 + index * 4)
        name = hooks[address]
        if name == "rand":
            result = next(randoms)
        elif name == "sprintf":
            fmt = string(arg(1))
            if fmt == b"%s%u%s":
                value = string(arg(2)) + str(arg(3)).encode() + string(arg(4))
            elif fmt in (b"%.8x", b"%02x", b"%02X"):
                value = (("%08x" if fmt == b"%.8x" else fmt.decode()) % arg(2)).encode()
            else:
                raise RuntimeError("Unmodeled format: %r" % fmt)
            machine.mem_write(arg(0), value + b"\0")
            result = len(value)
        elif name in ("memcpy", "memmove"):
            machine.mem_write(arg(0), bytes(machine.mem_read(arg(1), arg(2))))
            result = arg(0)
        elif name == "memset":
            machine.mem_write(arg(0), bytes((arg(1) & 255,)) * arg(2))
            result = arg(0)
        else:
            raise RuntimeError("Unmodeled import: " + name)
        machine.reg_write(UC_X86_REG_EAX, result)
        machine.reg_write(UC_X86_REG_EIP, word(stack))
        machine.reg_write(UC_X86_REG_ESP, stack + 4)

    cpu.hook_add(UC_HOOK_CODE, imported)
    cpu.mem_write(0x200000, seed.encode() + b"\0")
    cpu.mem_write(0x201000, challenge.encode() + b"\0")
    stack = 0x13f000
    cpu.mem_write(stack, struct.pack("<II", 0x20f000, 0x202000))
    cpu.reg_write(UC_X86_REG_ESP, stack)
    cpu.reg_write(UC_X86_REG_ECX, 0x200000)
    cpu.reg_write(UC_X86_REG_EDX, 0x201000)
    cpu.emu_start(0x12138040, 0x20f000, timeout=5_000_000, count=1_000_000)
    if cpu.reg_read(UC_X86_REG_EIP) != 0x20f000:
        raise RuntimeError("Oracle instruction/time budget exhausted")
    return string(0x202000).decode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    args = parser.parse_args()
    data = args.dll.read_bytes()
    if hashlib.sha256(data).hexdigest() != PIN:
        parser.error("Reference DLL differs from the inspected b9000 revision")
    seed = hashlib.md5(b"synthetic-protocol-fixture-not-a-key").hexdigest()
    count = 0
    for challenge in ("", "test-challenge", "A" * 128):
        for nonce in (0, 1, 0x12345678, 0x7fff7fff):
            got = reference(data, seed, challenge, nonce)
            expected = (hashlib.md5(seed.encode()).hexdigest() + "%08x" % nonce +
                        hashlib.md5((seed + str(nonce % 65535) + challenge).encode()).hexdigest())
            if got != expected:
                raise RuntimeError("Synthetic reference mismatch")
            count += 1
    print(json.dumps({"reference_sha256": PIN, "synthetic_vectors_passed": count,
                      "real_credentials_used": False, "evidence_class": "isolated_x86_function"}))
