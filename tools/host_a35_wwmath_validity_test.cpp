#include "wwmath.h"

#include <limits>
#include <initializer_list>
#include <stdio.h>

int main()
{
	const float finite_float[] = {0.0f, -0.0f, 1.0f,
		std::numeric_limits<float>::max(),
		std::numeric_limits<float>::denorm_min()};
	const double finite_double[] = {0.0, -0.0, 1.0,
		std::numeric_limits<double>::max(),
		std::numeric_limits<double>::denorm_min()};
	for (float value : finite_float) {
		if (!WWMath::Is_Valid_Float(value)) return 1;
	}
	for (double value : finite_double) {
		if (!WWMath::Is_Valid_Double(value)) return 1;
	}
	const float invalid_float[] = {
		std::numeric_limits<float>::infinity(),
		-std::numeric_limits<float>::infinity(),
		std::numeric_limits<float>::quiet_NaN()};
	const double invalid_double[] = {
		std::numeric_limits<double>::infinity(),
		-std::numeric_limits<double>::infinity(),
		std::numeric_limits<double>::quiet_NaN()};
	for (float value : invalid_float) {
		if (WWMath::Is_Valid_Float(value)) return 1;
	}
	for (double value : invalid_double) {
		if (WWMath::Is_Valid_Double(value)) return 1;
	}
	puts("WWMath 32/64-bit validity storage PASS");
	// Raw animation interpolation requires the lower key and a weight in [0, 1).
	// Half-frame-biased x87 conversion selects the wrong key when truncated on ARM.
	for (int key = 0; key < 4096; ++key) {
		for (float fraction : {0.0f, 0.125f, 0.25f, 0.5f, 0.75f, 0.875f}) {
			const float frame = key + fraction;
			const int lower = static_cast<int>(WWMath::Floor(frame));
			const float weight = frame - lower;
			if (lower != key || weight != fraction || weight < 0.0f || weight >= 1.0f) {
				fprintf(stderr, "Raw animation key selection failed at %.3f\n", frame);
				return 1;
			}
		}
	}
	puts("Raw animation fractional key selection PASS (24576 samples)");
	const float conversions[] = {0.0f, -0.0f, 0.125f, -0.125f, 0.75f, -0.75f,
		1.0f, -1.0f, 1.25f, -1.25f, 2.75f, -2.75f, 1024.125f, -1024.125f,
		std::numeric_limits<float>::denorm_min(),
		-std::numeric_limits<float>::denorm_min()};
	for (volatile float input : conversions) {
		const float value = input;
		if (WWMath::Float_To_Int_Chop(value) != static_cast<int>(value) ||
			WWMath::Float_To_Int_Floor(value) != static_cast<int>(floorf(value))) {
			fprintf(stderr, "WWMath integer conversion failed at %.9g\n", value);
			return 1;
		}
	}
	puts("WWMath fractional integer conversion PASS");
	uint32_t bits = 0;
	for (unsigned sample = 0; sample < 1000000U; ++sample) {
		bits += 0x9e3779b9U;
		float value;
		memcpy(&value, &bits, sizeof(value));
		const double reference = value;
		const bool representable = reference >= -2147483648.0 && reference < 2147483648.0;
		const int expected_chop = representable ? static_cast<int>(reference) : INT32_MIN;
		const int expected_floor = representable ? static_cast<int>(floor(reference)) : INT32_MIN;
		if (WWMath::Float_To_Int_Chop(value) != expected_chop ||
			WWMath::Float_To_Int_Floor(value) != expected_floor) {
			fprintf(stderr, "WWMath conversion mismatch for bits %08x\n", bits);
			return 1;
		}
	}
	puts("WWMath integer conversion bit-pattern sweep PASS (1000000 samples)");
	return 0;
}
