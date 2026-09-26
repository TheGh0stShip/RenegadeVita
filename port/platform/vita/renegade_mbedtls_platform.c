#include <mbedtls/entropy.h>
#include <mbedtls/platform_time.h>
#include <psp2/kernel/rng.h>
#include <psp2/kernel/processmgr.h>
#include <string.h>

int mbedtls_hardware_poll(void *context, unsigned char *output, size_t length, size_t *written)
{
    (void)context;
    *written = 0;
    for (size_t offset = 0; offset < length;) {
        // SceKernel's documented RNG call limit is 64 bytes.
        size_t chunk = length - offset;
        if (chunk > 64) chunk = 64;
        if (sceKernelGetRandomNumber(output + offset, (SceSize)chunk) < 0) {
            memset(output, 0, length);
            return MBEDTLS_ERR_ENTROPY_SOURCE_FAILED;
        }
        offset += chunk;
    }
    *written = length;
    return 0;
}

mbedtls_ms_time_t mbedtls_ms_time(void)
{
    return (mbedtls_ms_time_t)(sceKernelGetProcessTimeWide() / 1000U);
}
