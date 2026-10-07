// Bit-identity proof for the A3.6 ARM float helper patches:
//   port/patches/wwmath-a36-arm-int-floor-helpers.patch
//   port/patches/wwmath-a36-quat-matrix-single-precision.patch
// Every float bit pattern is checked for WWMath::Floor/Ceil (against the
// newlib sf_floor.c/sf_ceil.c algorithm that VitaSDK links) and for
// Float_To_Int_Chop/Floor (against the previous a35 implementation). The
// quaternion-to-matrix routines are compared bitwise with the original
// (float)(double) expressions over special and random quaternions. Both
// passes run with IEEE denormals and again with flush-to-zero/denormals-are-
// zero (the x86 analogue of the ARM FPSCR.FZ mode) when available.
#include "wwmath.h"
#include "quat.h"
#include "matrix3.h"
#include "matrix3d.h"
#include "matrix4.h"

#include <atomic>
#include <limits>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <thread>
#include <vector>
#if defined(__SSE__)
#include <xmmintrin.h>
#endif

namespace {

uint32_t Bits(float value) { uint32_t b; memcpy(&b, &value, sizeof(b)); return b; }
float From_Bits(uint32_t b) { float value; memcpy(&value, &b, sizeof(value)); return value; }

// newlib libm/common/sf_floor.c and sf_ceil.c, verbatim algorithm
// (GET/SET_FLOAT_WORD spelled with memcpy).
volatile float newlib_huge = 1.0e30f;
__attribute__((noinline)) float Newlib_Floorf(float x)
{
	int32_t i0, j0; uint32_t i, ix;
	memcpy(&i0, &x, sizeof(i0));
	ix = (i0 & 0x7fffffff);
	j0 = (ix >> 23) - 0x7f;
	if (j0 < 23) {
		if (j0 < 0) {
			if (newlib_huge + x > 0.0f) {
				if (i0 >= 0) { i0 = 0; }
				else if (ix != 0) { i0 = (int32_t)0xbf800000; }
			}
		} else {
			i = (0x007fffff) >> j0;
			if ((i0 & i) == 0) return x;
			if (newlib_huge + x > 0.0f) {
				if (i0 < 0) i0 += (0x00800000) >> j0;
				i0 &= (~i);
			}
		}
	} else {
		if (!(ix < 0x7f800000)) return x + x;
		else return x;
	}
	memcpy(&x, &i0, sizeof(x));
	return x;
}

__attribute__((noinline)) float Newlib_Ceilf(float x)
{
	int32_t i0, j0; uint32_t i, ix;
	memcpy(&i0, &x, sizeof(i0));
	ix = (i0 & 0x7fffffff);
	j0 = (ix >> 23) - 0x7f;
	if (j0 < 23) {
		if (j0 < 0) {
			if (newlib_huge + x > 0.0f) {
				if (i0 < 0) { i0 = (int32_t)0x80000000; }
				else if (ix != 0) { i0 = 0x3f800000; }
			}
		} else {
			i = (0x007fffff) >> j0;
			if ((i0 & i) == 0) return x;
			if (newlib_huge + x > 0.0f) {
				if (i0 > 0) i0 += (0x00800000) >> j0;
				i0 &= (~i);
			}
		}
	} else {
		if (!(ix < 0x7f800000)) return x + x;
		else return x;
	}
	memcpy(&x, &i0, sizeof(x));
	return x;
}

// Previous staged (a35) conversions.
__attribute__((noinline)) int Old_Chop(const float& f)
{
	if (!(f >= -2147483648.0f && f < 2147483648.0f)) return INT32_MIN;
	return static_cast<int>(f);
}
__attribute__((noinline)) int Old_Floor(const float& f)
{
	if (!(f >= -2147483648.0f && f < 2147483648.0f)) return INT32_MIN;
	const int truncated = static_cast<int>(f);
	return truncated - (f < static_cast<float>(truncated) ? 1 : 0);
}
__attribute__((noinline)) int New_Chop(const float& f) { return WWMath::Float_To_Int_Chop(f); }
__attribute__((noinline)) int New_Floor(const float& f) { return WWMath::Float_To_Int_Floor(f); }
__attribute__((noinline)) float New_Floorf(float f) { return WWMath::Floor(f); }
__attribute__((noinline)) float New_Ceilf(float f) { return WWMath::Ceil(f); }

std::atomic<unsigned long long> scalar_failures(0);

uint64_t scalar_stride = 1;
int random_quaternions = 2000000;

void Scalar_Range(uint64_t begin, uint64_t end, bool flush)
{
#if defined(__SSE__)
	if (flush) _mm_setcsr(_mm_getcsr() | 0x8040U);	// FTZ | DAZ
#endif
	unsigned long long failures = 0;
	for (uint64_t b = begin; b < end; b += scalar_stride) {
		const float f = From_Bits(static_cast<uint32_t>(b));
		if (Bits(New_Floorf(f)) != Bits(Newlib_Floorf(f)) ||
			Bits(New_Ceilf(f)) != Bits(Newlib_Ceilf(f)) ||
			New_Chop(f) != Old_Chop(f) || New_Floor(f) != Old_Floor(f)) {
			if (failures++ < 4) {
				fprintf(stderr, "scalar mismatch flush=%d bits=%08X floor %08X/%08X ceil %08X/%08X chop %d/%d ifloor %d/%d\n",
					flush, static_cast<unsigned>(b), Bits(New_Floorf(f)), Bits(Newlib_Floorf(f)),
					Bits(New_Ceilf(f)), Bits(Newlib_Ceilf(f)), New_Chop(f), Old_Chop(f),
					New_Floor(f), Old_Floor(f));
			}
		}
	}
	scalar_failures += failures;
}

bool Scalar_Pass(bool flush, unsigned threads)
{
	std::vector<std::thread> pool;
	const uint64_t total = 1ULL << 32;
	for (unsigned t = 0; t < threads; ++t) {
		pool.emplace_back(Scalar_Range, total * t / threads, total * (t + 1) / threads, flush);
	}
	for (std::thread& thread : pool) thread.join();
	return scalar_failures.load() == 0;
}

// Original (float)(double) quaternion -> rotation expressions.
template <class M> __attribute__((noinline)) void Original_Rotation(const Quaternion& q, M& m)
{
	m[0][0] = (float)(1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2]));
	m[0][1] = (float)(2.0 * (q[0] * q[1] - q[2] * q[3]));
	m[0][2] = (float)(2.0 * (q[2] * q[0] + q[1] * q[3]));
	m[1][0] = (float)(2.0 * (q[0] * q[1] + q[2] * q[3]));
	m[1][1] = (float)(1.0 - 2.0f * (q[2] * q[2] + q[0] * q[0]));
	m[1][2] = (float)(2.0 * (q[1] * q[2] - q[0] * q[3]));
	m[2][0] = (float)(2.0 * (q[2] * q[0] - q[1] * q[3]));
	m[2][1] = (float)(2.0 * (q[1] * q[2] + q[0] * q[3]));
	m[2][2] = (float)(1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0]));
}

template <class M> bool Same_Rotation(const M& a, const M& b)
{
	for (int r = 0; r < 3; ++r) for (int c = 0; c < 3; ++c) {
		if (Bits(a[r][c]) != Bits(b[r][c])) return false;
	}
	return true;
}

uint32_t rng_state = 0x12345678U;
uint32_t Next() { rng_state ^= rng_state << 13; rng_state ^= rng_state >> 17; rng_state ^= rng_state << 5; return rng_state; }

bool Quaternion_Pass(bool flush, unsigned long long& checked)
{
#if defined(__SSE__)
	const unsigned saved = _mm_getcsr();
	if (flush) _mm_setcsr(saved | 0x8040U);
#endif
	const float specials[] = {0.0f, -0.0f, 1.0f, -1.0f, 0.5f, -0.5f, 0.70710678f, -0.70710678f,
		std::numeric_limits<float>::denorm_min(), -std::numeric_limits<float>::denorm_min(),
		From_Bits(0x00400000U), From_Bits(0x807FFFFFU), std::numeric_limits<float>::min(),
		-std::numeric_limits<float>::min(), 1.0e-20f, -1.0e-20f, 1.0e19f, -1.0e19f,
		std::numeric_limits<float>::max(), -std::numeric_limits<float>::max(),
		From_Bits(0x7EFFFFFFU), From_Bits(0x7F000000U), 3.0e38f,
		std::numeric_limits<float>::infinity(), -std::numeric_limits<float>::infinity(),
		std::numeric_limits<float>::quiet_NaN(), From_Bits(0xFFC12345U), From_Bits(0x7FA00001U),
		0.99999994f, 1.00000012f, 0.49999997f, 0.25f};
	const int count = sizeof(specials) / sizeof(specials[0]);
	bool ok = true;
	auto check = [&](const Quaternion& q) {
		Matrix3D ref3d(true), new3d(true), set3d(true);
		Matrix3 ref3(true), set3(true);
		Matrix4 ref4(true);
		Original_Rotation(q, ref3d);
		Original_Rotation(q, ref3);
		Original_Rotation(q, ref4);
		new3d = Build_Matrix3D(q);
		set3d.Set_Rotation(q);
		set3.Set(q);
		const Matrix3 new3 = Build_Matrix3(q);
		const Matrix4 new4 = Build_Matrix4(q);
		++checked;
		if (!Same_Rotation(ref3d, new3d) || !Same_Rotation(ref3d, set3d) ||
			!Same_Rotation(ref3, set3) || !Same_Rotation(ref3, new3) || !Same_Rotation(ref4, new4)) {
			if (ok) fprintf(stderr, "quaternion mismatch flush=%d q=%08X %08X %08X %08X\n", flush,
				Bits(q[0]), Bits(q[1]), Bits(q[2]), Bits(q[3]));
			ok = false;
		}
	};
	// Every combination of special values in pairs of lanes, others from a fixed set.
	for (int a = 0; a < count; ++a) for (int b = 0; b < count; ++b) for (int c = 0; c < count; c += 3) {
		check(Quaternion(specials[a], specials[b], specials[c], specials[(a + b + c) % count]));
		check(Quaternion(specials[c], specials[a], specials[b], specials[(a * 7 + b) % count]));
	}
	// Random bit patterns (all exponents, NaNs, denormals) and random unit quaternions.
	for (int i = 0; i < random_quaternions; ++i) {
		check(Quaternion(From_Bits(Next()), From_Bits(Next()), From_Bits(Next()), From_Bits(Next())));
		const float x = (static_cast<int>(Next() & 0xFFFFFF) - 0x800000) / 8388608.0f;
		const float y = (static_cast<int>(Next() & 0xFFFFFF) - 0x800000) / 8388608.0f;
		const float z = (static_cast<int>(Next() & 0xFFFFFF) - 0x800000) / 8388608.0f;
		const float w = (static_cast<int>(Next() & 0xFFFFFF) - 0x800000) / 8388608.0f;
		Quaternion unit(x, y, z, w);
		unit.Normalize();
		check(unit);
		// Exponent-near-one inputs make 1-2s cancel to tiny normals.
		check(Quaternion(From_Bits(0x3F000000U | (Next() & 0x807FFFFFU)), From_Bits(0x3F000000U | (Next() & 0x807FFFFFU)),
			From_Bits(Next() & 0x9FFFFFFFU), From_Bits(Next())));
	}
#if defined(__SSE__)
	_mm_setcsr(saved);
#endif
	return ok;
}

}	// namespace

int main(int argc, char** argv)
{
	unsigned threads = std::thread::hardware_concurrency();
	if (threads == 0) threads = 2;
	if (threads > 4) threads = 4;
	// Optional stride (sanitizer builds): checks every Nth bit pattern.
	if (argc > 1) {
		scalar_stride = strtoull(argv[1], NULL, 10);
		if (scalar_stride == 0) scalar_stride = 1;
		random_quaternions = static_cast<int>(2000000 / scalar_stride) + 1000;
	}
	for (int flush = 0; flush <= 1; ++flush) {
#if !defined(__SSE__)
		if (flush) { puts("SKIP flush-to-zero pass (no SSE control register)"); break; }
#endif
		if (!Scalar_Pass(flush != 0, threads)) {
			fprintf(stderr, "FAIL scalar helpers flush=%d failures=%llu\n", flush, scalar_failures.load());
			return 1;
		}
		printf("PASS scalar helpers 2^32/stride=%llu flush=%d (Floor/Ceil vs newlib, Float_To_Int_Chop/Floor vs a35)\n",
			static_cast<unsigned long long>(scalar_stride), flush);
		unsigned long long checked = 0;
		if (!Quaternion_Pass(flush != 0, checked)) {
			fprintf(stderr, "FAIL quaternion matrices flush=%d\n", flush);
			return 1;
		}
		printf("PASS quaternion matrices bit-identical flush=%d quaternions=%llu\n", flush, checked);
	}
	return 0;
}
