"""Verify Vita TLS provider limits/failures and full-width monotonic time."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TLSPlatformTests(unittest.TestCase):
    def test_rng_chunks_failure_and_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'mbedtls').mkdir()
            (root / 'psp2/kernel').mkdir(parents=True)
            (root / 'mbedtls/entropy.h').write_text(
                '#include <stddef.h>\n#define MBEDTLS_ERR_ENTROPY_SOURCE_FAILED -60\n'
                'int mbedtls_hardware_poll(void*, unsigned char*, size_t, size_t*);\n')
            (root / 'mbedtls/platform_time.h').write_text(
                '#include <stdint.h>\ntypedef int64_t mbedtls_ms_time_t;\n'
                'mbedtls_ms_time_t mbedtls_ms_time(void);\n')
            (root / 'psp2/kernel/rng.h').write_text(
                'typedef unsigned int SceSize;\nint sceKernelGetRandomNumber(void*, SceSize);\n')
            (root / 'psp2/kernel/processmgr.h').write_text(
                '#include <stdint.h>\nuint64_t sceKernelGetProcessTimeWide(void);\n')
            (root / 'test.c').write_text(r'''
#include <mbedtls/entropy.h>
#include <mbedtls/platform_time.h>
#include <psp2/kernel/rng.h>
#include <assert.h>
#include <string.h>
static unsigned calls, fail;
int sceKernelGetRandomNumber(void *out, SceSize size) {
    assert(size && size <= 64);
    if (++calls == fail) return -1;
    memset(out, 0xa5, size);
    return 0;
}
uint64_t sceKernelGetProcessTimeWide(void) { return (UINT64_C(1) << 45) + 999; }
int main(void) {
    unsigned char bytes[1024];
    for (size_t n = 0; n <= sizeof(bytes); ++n) {
        size_t written = 123;
        calls = fail = 0;
        memset(bytes, 0xcc, sizeof(bytes));
        assert(mbedtls_hardware_poll(0, bytes, n, &written) == 0);
        assert(written == n && calls == (n + 63) / 64);
        for (size_t i = 0; i < sizeof(bytes); ++i) assert(bytes[i] == (i < n ? 0xa5 : 0xcc));
    }
    for (fail = 1; fail <= 3; ++fail) {
        calls = 0;
        size_t written = 123;
        memset(bytes, 0xcc, sizeof(bytes));
        assert(mbedtls_hardware_poll(0, bytes, 130, &written) == MBEDTLS_ERR_ENTROPY_SOURCE_FAILED);
        assert(written == 0 && calls == fail);
        for (size_t i = 0; i < sizeof(bytes); ++i) assert(bytes[i] == (i < 130 ? 0 : 0xcc));
    }
    assert(mbedtls_ms_time() == (int64_t)(((UINT64_C(1) << 45) + 999) / 1000));
}
''')
            binary = root / 'probe'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                            '-I' + str(root), str(root / 'test.c'),
                            str(ROOT / 'port/platform/vita/renegade_mbedtls_platform.c'),
                            '-o', str(binary)], check=True, timeout=30)
            subprocess.run([str(binary)], check=True, timeout=15)


if __name__ == '__main__':
    unittest.main()
