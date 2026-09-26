#include "wwmath.h"

#include <limits>
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
	return 0;
}
