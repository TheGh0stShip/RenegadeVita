#pragma once

namespace RenegadeVitaRenderer {

// Column-vector 3x3 linear transform, stored in row order. Translation is
// deliberately excluded. Normal covectors transform by its inverse transpose.
struct PreparedNormalTransform {
	float c[9] = {};
	float determinant = 0.0f;
	void Prepare(const float m[9]) {
	const float cofactors[9] = {
		m[4]*m[8]-m[5]*m[7], m[5]*m[6]-m[3]*m[8], m[3]*m[7]-m[4]*m[6],
		m[2]*m[7]-m[1]*m[8], m[0]*m[8]-m[2]*m[6], m[1]*m[6]-m[0]*m[7],
		m[1]*m[5]-m[2]*m[4], m[2]*m[3]-m[0]*m[5], m[0]*m[4]-m[1]*m[3]
	};
	for (unsigned i = 0; i < 9U; ++i) c[i] = cofactors[i];
	determinant = m[0]*c[0] + m[1]*c[1] + m[2]*c[2];
	}
	bool Apply(const float n[3], float output[3]) const {
	if (determinant == 0.0f) return false;
	for (unsigned row = 0; row < 3U; ++row)
		output[row] = (c[row*3]*n[0] + c[row*3+1]*n[1] + c[row*3+2]*n[2]) / determinant;
	return true;
	}
};

inline bool Transform_Normal_Inverse_Transpose(const float m[9],
	const float n[3], float output[3])
{
	PreparedNormalTransform transform;
	transform.Prepare(m);
	return transform.Apply(n, output);
}

} // namespace RenegadeVitaRenderer
