#pragma once

// Capacity policy only: original WW3D dynamic buffers still own allocation,
// locks, references, offsets, frame reset and all logical draw counts.
namespace RenegadeVitaBufferGrowth {

inline unsigned Capacity(unsigned current, unsigned required, unsigned minimum)
{
	const unsigned maximum = 65535U;
	// Leave invalid oversized requests to the original owner's range contract;
	// never disguise them as a successful but undersized capacity request.
	if (required > maximum || minimum > maximum) return required;
	unsigned capacity = current < minimum ? minimum : current;
	while (capacity < required) {
		const unsigned increment = capacity > 1U ? capacity / 2U : 1U;
		if (capacity > maximum - increment) {
			capacity = maximum;
			break;
		}
		capacity += increment;
	}
	return capacity;
}

} // namespace RenegadeVitaBufferGrowth
