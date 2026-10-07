#pragma once

// RENEGADE_VITA_PORT also enables compatibility code in host probes. Only the
// compiler's native Vita define selects the actual device ABI contract.
#if defined(__vita__)
#if !defined(__arm__) || !defined(__ARM_ARCH) || __ARM_ARCH != 7
#error "PS Vita requires 32-bit ARMv7, not a host or AArch64 compiler"
#endif
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "PS Vita requires little-endian data layout"
#endif
#if __SIZEOF_INT__ != 4 || __SIZEOF_LONG__ != 4 || __SIZEOF_POINTER__ != 4 || __SIZEOF_SIZE_T__ != 4
#error "PS Vita requires ILP32: int, long, pointers and size_t must be 32-bit"
#endif
#endif

// Short-enum ABI (see reports/SHORT_ENUM_NETWORK_AUDIT.md). arm-vita-eabi
// defaults to -fshort-enums (AAPCS "small enum" variant): an enum whose
// values fit in a byte occupies 1 byte, unlike MSVC where every enum is 4.
// Original code that writes a raw enum to a BitStream, save chunk or packet
// via sizeof(enum)/memcpy would therefore change wire/save layout versus PC.
// Raw enum serialization must go through int (write (int)value, read an int
// and cast back) so the encoded width is independent of enum storage size.
// This assert makes any future -fno-short-enums (or toolchain default)
// change visible so the audit and dependent struct layouts are re-reviewed.
#if defined(__vita__) && defined(__cplusplus)
namespace renegade_abi_detail { enum ShortEnumProbe { SHORT_ENUM_PROBE_A, SHORT_ENUM_PROBE_B }; }
static_assert(sizeof(renegade_abi_detail::ShortEnumProbe) == 1,
              "Vita short-enum ABI changed: re-audit enum serialization (reports/SHORT_ENUM_NETWORK_AUDIT.md)");
#endif
