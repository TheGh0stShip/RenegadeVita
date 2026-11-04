"""Compile-only ARM probe for FFmpeg transform wildcard representation."""
import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Pinned FFmpeg source directory')
    parser.add_argument('--cc', default='/usr/local/vitasdk/bin/arm-vita-eabi-gcc')
    args = parser.parse_args()
    code = '''#include <stdint.h>
#include "libavutil/tx.h"
_Static_assert(sizeof(enum AVTXType) == 4, "FFmpeg transform enum must retain INT32_MAX wildcard");
_Static_assert((enum AVTXType)INT32_MAX == INT32_MAX, "wildcard truncated");
int probe(void) { return sizeof(enum AVTXType); }
'''
    with tempfile.TemporaryDirectory(prefix='renegade-ffmpeg-enum-') as directory:
        source = Path(directory) / 'probe.c'
        source.write_text(code)
        for label, flags in [('installed default', []), ('explicit int enums', ['-fno-short-enums'])]:
            result = subprocess.run([args.cc, '-std=c11', '-mcpu=cortex-a9', '-mfpu=neon',
                                     '-mfloat-abi=hard', *flags, '-I', str(args.source),
                                     '-c', str(source), '-o', str(Path(directory) / 'probe.o')],
                                    capture_output=True, text=True)
            print(f'{label}: exit={result.returncode}')
            if result.returncode:
                print(result.stderr, end='')
            if label == 'explicit int enums' and result.returncode:
                return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
