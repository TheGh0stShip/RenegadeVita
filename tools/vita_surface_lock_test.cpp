// Exercise production SurfaceClass raster methods with a counted provider.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "surface-format.inc"

struct Vector2i {
	int I, J;
	Vector2i(int i, int j) : I(i), J(j) {}
};

class SurfaceClass {
public:
	struct SurfaceDescription { WW3DFormat Format; unsigned Width, Height; };
	SurfaceDescription description;
	std::vector<unsigned char> pixels;
	int pitch, locks = 0, unlocks = 0;
	bool fail_lock = false, locked = false;
	SurfaceClass(int row_pitch, WW3DFormat format = WW3D_FORMAT_A8,
		unsigned width = 3, unsigned height = 2)
		: description{format, width, height}, pixels(128, 0x77), pitch(row_pitch) {}
	void Get_Description(SurfaceDescription &out) { out = description; }
	void *Lock(int *out) {
		*out = pitch;
		if (fail_lock) return nullptr;
		assert(!locked);
		locked = true;
		++locks;
		return pixels.data();
	}
	void Unlock() { assert(locked); locked = false; ++unlocks; }
	void Clear();
	void Copy(const unsigned char *);
	void Copy(unsigned, unsigned, unsigned, unsigned, unsigned, unsigned,
		const SurfaceClass *);
	void FindBB(Vector2i *, Vector2i *);
};

#include "surface-raster-production.inc"

static void Balanced(const SurfaceClass &s) {
	assert(!s.locked && s.locks == s.unlocks);
}

int main() {
	unsigned cases = 0;
	const unsigned char input[] = {1, 2, 3, 4, 5, 6};
	for (int pitch : {-1, 0, 2}) {
		SurfaceClass clear(pitch);
		clear.Clear(); Balanced(clear);
		assert(clear.pixels == std::vector<unsigned char>(128, 0x77)); ++cases;
		SurfaceClass copy(pitch);
		copy.Copy(input); Balanced(copy);
		assert(copy.pixels == std::vector<unsigned char>(128, 0x77)); ++cases;
		SurfaceClass bb(pitch);
		Vector2i min(0, 0), max(3, 2);
		bb.FindBB(&min, &max); Balanced(bb);
		assert(min.I == 0 && min.J == 0 && max.I == 3 && max.J == 2); ++cases;
	}
	SurfaceClass clear(5);
	clear.Clear(); Balanced(clear);
	assert(clear.pixels[0] == 0 && clear.pixels[5] == 0);
	assert(clear.pixels[3] == 0x77 && clear.pixels[8] == 0x77); ++cases;
	SurfaceClass copy(5);
	copy.Copy(input); Balanced(copy);
	assert(copy.pixels[0] == 1 && copy.pixels[7] == 6);
	assert(copy.pixels[3] == 0x77 && copy.pixels[8] == 0x77); ++cases;
	for (bool bad_source : {false, true}) {
		SurfaceClass dst(bad_source ? 5 : -1), src(bad_source ? -1 : 5);
		dst.Copy(0, 0, 0, 0, 3, 2, &src);
		Balanced(dst); Balanced(src);
		assert(dst.pixels == std::vector<unsigned char>(128, 0x77)); ++cases;
	}
	for (bool source_failure : {false, true}) {
		SurfaceClass dst(5), src(5);
		(source_failure ? src : dst).fail_lock = true;
		dst.Copy(0, 0, 0, 0, 3, 2, &src);
		Balanced(dst); Balanced(src);
		assert(dst.pixels == std::vector<unsigned char>(128, 0x77)); ++cases;
	}
	SurfaceClass src(5), dst(5);
	src.Copy(input);
	dst.Copy(1, 0, 0, 0, 2, 2, &src);
	Balanced(src); Balanced(dst);
	assert(dst.pixels[1] == 1 && dst.pixels[2] == 2 && dst.pixels[7] == 5);
	assert(dst.pixels[0] == 0x77 && dst.pixels[3] == 0x77); ++cases;
	SurfaceClass argb(12, WW3D_FORMAT_A8R8G8B8, 2, 1);
	SurfaceClass rgba4(6, WW3D_FORMAT_A4R4G4B4, 2, 1);
	argb.pixels[0] = 0x12; argb.pixels[1] = 0x34;
	argb.pixels[2] = 0x56; argb.pixels[3] = 0x78;
	rgba4.Copy(0, 0, 0, 0, 1, 1, &argb);
	Balanced(argb); Balanced(rgba4);
	assert(rgba4.pixels[0] == 0x31 && rgba4.pixels[1] == 0x75);
	assert(rgba4.pixels[2] == 0x77); ++cases;
	SurfaceClass bb(5);
	bb.Clear(); bb.pixels[6] = 0xff;
	Vector2i min(0, 0), max(3, 2);
	bb.FindBB(&min, &max); Balanced(bb);
	assert(min.I == 1 && min.J == 1 && max.I == 1 && max.J == 1); ++cases;
	SurfaceClass failed(5); failed.fail_lock = true;
	failed.Clear(); failed.Copy(input); failed.FindBB(&min, &max);
	Balanced(failed); assert(failed.locks == 0); ++cases;
	std::printf("%u production surface raster cases passed\n", cases);
}
