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
