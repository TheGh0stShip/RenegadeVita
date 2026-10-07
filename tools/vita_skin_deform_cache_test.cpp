// Host proof for the deformed-skin cache (ww3d_vita_skin_deform_cache.h).
// Every simulated submission is checked bitwise against a fresh deformation
// computed from the live model/HTree state, so any stale reuse fails.
#include "ww3d_vita_skin_deform_cache.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <vector>

using RenegadeVitaRenderer::SkinDeformCache;

namespace {

struct V3 {
	float X, Y, Z;
};

// Same 3x4 row layout as Matrix3D.
struct Mat {
	float m[3][4];
};
static_assert(sizeof(Mat) == 48, "fake Matrix3D layout");

struct Model {
	std::vector<V3> vertices;
	std::vector<V3> normals;
	std::vector<uint16_t> links;
	int Count() const { return static_cast<int>(vertices.size()); }
};

struct HTree {
	std::vector<Mat> pivots;
	int Num_Pivots() const { return static_cast<int>(pivots.size()); }
};

struct Mesh {
	Model *model;
	HTree *htree;
};

typedef SkinDeformCache<V3> Cache;

int g_failures = 0;
#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #condition); \
	++g_failures; } } while (0)

V3 Transform(const Mat &a, const V3 &v, bool translate)
{
	V3 out;
	out.X = a.m[0][0] * v.X + a.m[0][1] * v.Y + a.m[0][2] * v.Z + (translate ? a.m[0][3] : 0.0f);
	out.Y = a.m[1][0] * v.X + a.m[1][1] * v.Y + a.m[1][2] * v.Z + (translate ? a.m[1][3] : 0.0f);
	out.Z = a.m[2][0] * v.X + a.m[2][1] * v.Y + a.m[2][2] * v.Z + (translate ? a.m[2][3] : 0.0f);
	return out;
}

// Mirrors MeshModelClass::get_deformed_vertices(dst_vert, dst_norm, htree):
// walks runs of equal bone links and reads only those pivots.
void Deform(const Mesh &mesh, V3 *dst_vertices, V3 *dst_normals)
{
	const Model &model = *mesh.model;
	for (int vi = 0; vi < model.Count();) {
		const Mat &tm = mesh.htree->pivots[model.links[vi]];
		int cnt = vi;
		while (cnt < model.Count() && model.links[cnt] == model.links[vi]) ++cnt;
		for (int i = vi; i < cnt; ++i) {
			dst_vertices[i] = Transform(tm, model.vertices[i], true);
			dst_normals[i] = Transform(tm, model.normals[i], false);
		}
		vi = cnt;
	}
}

struct Outcome {
	bool from_cache;   // submission reused stored bytes
	bool stored;       // submission deformed into the cache
};

// Mirrors Fetch_Cached_Deformed_Skin plus the original scratch fallback in
// Submit_Mesh_Internal, then proves the bytes the draw would consume equal a
// fresh deformation of the current inputs.
Outcome Submit(Cache &cache, const Mesh &mesh, bool material_pass, bool pass_follows,
	uint32_t frame, std::vector<V3> &scratch_v, std::vector<V3> &scratch_n)
{
	Outcome outcome = { false, false };
	const int count = mesh.model->Count();
	const V3 *vertices = NULL;
	const V3 *normals = NULL;
	const HTree *htree = mesh.htree;
	const auto transform_at = [htree](int pivot) -> const void * {
		return &htree->pivots[static_cast<size_t>(pivot)];
	};
	cache.Begin_Frame(frame);
	outcome.from_cache = cache.Find(&mesh, mesh.model, count, htree->Num_Pivots(),
		transform_at, &vertices, &normals);
	if (!outcome.from_cache && (material_pass || pass_follows)) {
		V3 *dv = NULL;
		V3 *dn = NULL;
		if (cache.Reserve(&mesh, mesh.model, count, &dv, &dn)) {
			Deform(mesh, dv, dn);
			outcome.stored = cache.Commit(mesh.model->links.data(), count,
				htree->Num_Pivots(), transform_at);
			vertices = dv;
			normals = dn;
		}
	}
	if (vertices == NULL) {
		scratch_v.resize(static_cast<size_t>(count));
		scratch_n.resize(static_cast<size_t>(count));
		Deform(mesh, scratch_v.data(), scratch_n.data());
		vertices = scratch_v.data();
		normals = scratch_n.data();
	}
	std::vector<V3> fresh_v(static_cast<size_t>(count));
	std::vector<V3> fresh_n(static_cast<size_t>(count));
	Deform(mesh, fresh_v.data(), fresh_n.data());
	CHECK(std::memcmp(vertices, fresh_v.data(), sizeof(V3) * count) == 0);
	CHECK(std::memcmp(normals, fresh_n.data(), sizeof(V3) * count) == 0);
	return outcome;
}

Mat Random_Mat(std::mt19937 &rng)
{
	std::uniform_real_distribution<float> dist(-2.0f, 2.0f);
	Mat mat;
	for (int r = 0; r < 3; ++r)
		for (int c = 0; c < 4; ++c) mat.m[r][c] = dist(rng);
	return mat;
}

Model Make_Model(std::mt19937 &rng, int vertex_count, int pivots, int run_length)
{
	std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
	Model model;
	for (int i = 0; i < vertex_count; ++i) {
		model.vertices.push_back({ dist(rng), dist(rng), dist(rng) });
		model.normals.push_back({ dist(rng), dist(rng), dist(rng) });
		model.links.push_back(static_cast<uint16_t>((i / run_length) % pivots));
	}
	return model;
}

HTree Make_HTree(std::mt19937 &rng, int pivots)
{
	HTree tree;
	for (int i = 0; i < pivots; ++i) tree.pivots.push_back(Random_Mat(rng));
	return tree;
}

void Targeted_Cases()
{
	std::mt19937 rng(1234U);
	std::vector<V3> sv, sn;
	Model model = Make_Model(rng, 200, 12, 20);   // references pivots 0..9
	HTree tree = Make_HTree(rng, 12);
	Mesh mesh = { &model, &tree };
	Cache cache;

	// Base pass followed by material passes in the same render: reuse.
	CHECK(Submit(cache, mesh, false, true, 1U, sv, sn).stored);
	CHECK(Submit(cache, mesh, true, false, 1U, sv, sn).from_cache);
	CHECK(Submit(cache, mesh, true, false, 1U, sv, sn).from_cache);
	CHECK(cache.Counters().hits == 2U);
	// Another camera renders the same pose: its base pass reuses it too.
	CHECK(Submit(cache, mesh, false, false, 1U, sv, sn).from_cache);

	// A plain skin (no material pass, nothing stored this frame) keeps the
	// original scratch path and never allocates the cache.
	Cache plain;
	{
		const Outcome outcome = Submit(plain, mesh, false, false, 1U, sv, sn);
		CHECK(!outcome.stored && !outcome.from_cache);
	}
	CHECK(plain.Counters().stores == 0U && plain.Bytes() == 0U);
	// A material-pass-only render (shadow, projector or stealth) stores, and
	// the main render's base pass of the same pose reuses it.
	{
		const Outcome outcome = Submit(plain, mesh, true, false, 1U, sv, sn);
		CHECK(outcome.stored && !outcome.from_cache);
	}
	CHECK(Submit(plain, mesh, false, false, 1U, sv, sn).from_cache);
	plain.Release();

	// Bones change between two renders in one frame (animation, cinematic or
	// Control_Bone update after the first render).
	CHECK(Submit(cache, mesh, false, true, 2U, sv, sn).stored);
	CHECK(Submit(cache, mesh, true, false, 2U, sv, sn).from_cache);
	const Mat saved = tree.pivots[3];
	tree.pivots[3].m[1][3] += 0.25f;
	{
		// Second render without material passes: stale, original path.
		const uint64_t stale = cache.Counters().stale;
		const Outcome outcome = Submit(cache, mesh, false, false, 2U, sv, sn);
		CHECK(!outcome.from_cache && !outcome.stored);
		CHECK(cache.Counters().stale == stale + 1U);
	}
	// Second render with a material pass: the base pass re-deforms and
	// replaces the entry; its material pass reuses the new pose.
	CHECK(Submit(cache, mesh, false, true, 2U, sv, sn).stored);
	CHECK(Submit(cache, mesh, true, false, 2U, sv, sn).from_cache);
	CHECK(cache.Entry_Count() == 1);
	// Going back to the first pose misses against the second pose's entry.
	tree.pivots[3] = saved;
	CHECK(!Submit(cache, mesh, false, false, 2U, sv, sn).from_cache);

	// A bone change between a base pass and its queued material pass misses;
	// that material pass re-deforms and stores, the next one reuses it.
	CHECK(Submit(cache, mesh, false, true, 3U, sv, sn).stored);
	tree.pivots[0] = Random_Mat(rng);
	{
		const Outcome outcome = Submit(cache, mesh, true, false, 3U, sv, sn);
		CHECK(!outcome.from_cache && outcome.stored);
	}
	CHECK(Submit(cache, mesh, true, false, 3U, sv, sn).from_cache);
	CHECK(cache.Entry_Count() == 1);

	// Bitwise comparison: +0.0 -> -0.0 is numerically equal but still misses.
	tree.pivots[2].m[0][3] = 0.0f;
	CHECK(Submit(cache, mesh, false, true, 4U, sv, sn).stored);
	tree.pivots[2].m[0][3] = -0.0f;
	CHECK(!Submit(cache, mesh, false, false, 4U, sv, sn).from_cache);

	// Unreferenced pivots are not deformation inputs.
	CHECK(Submit(cache, mesh, false, true, 5U, sv, sn).stored);
	tree.pivots[11] = Random_Mat(rng);
	CHECK(Submit(cache, mesh, true, false, 5U, sv, sn).from_cache);

	// Model reset/destruction hook drops the entry before the model changes.
	CHECK(Submit(cache, mesh, false, true, 6U, sv, sn).stored);
	cache.Forget_Model(&model);
	model.vertices[7].X += 1.0f;
	CHECK(!Submit(cache, mesh, false, false, 6U, sv, sn).from_cache);
	CHECK(cache.Counters().forgets == 1U);

	// Negative control: the hook is load-bearing. A model mutated in place
	// without Forget_Model would be reused (the original hooks guarantee
	// Forget_Model precedes every such mutation).
	{
		Cache control;
		std::vector<V3> v(200), n(200);
		const V3 *cv = NULL, *cn = NULL;
		V3 *dv = NULL, *dn = NULL;
		HTree *t = &tree;
		const auto at = [t](int p) -> const void * { return &t->pivots[static_cast<size_t>(p)]; };
		control.Begin_Frame(1U);
		CHECK(control.Reserve(&mesh, &model, 200, &dv, &dn));
		Deform(mesh, dv, dn);
		CHECK(control.Commit(model.links.data(), 200, 12, at));
		model.vertices[9].Y += 1.0f;
		CHECK(control.Find(&mesh, &model, 200, 12, at, &cv, &cn));
		Deform(mesh, v.data(), n.data());
		CHECK(std::memcmp(cv, v.data(), sizeof(V3) * 200) != 0);
		control.Release();
	}

	// Mesh model reassignment (MeshClass::Make_Unique) misses.
	Model other = model;
	CHECK(Submit(cache, mesh, false, true, 7U, sv, sn).stored);
	mesh.model = &other;
	CHECK(!Submit(cache, mesh, true, false, 7U, sv, sn).from_cache);
	mesh.model = &model;

	// Container HTree replaced by a tree with a different pivot count misses.
	HTree bigger = tree;
	bigger.pivots.push_back(Random_Mat(rng));
	CHECK(Submit(cache, mesh, false, true, 8U, sv, sn).stored);
	mesh.htree = &bigger;
	CHECK(!Submit(cache, mesh, true, false, 8U, sv, sn).from_cache);
	// A replacement HTree (Set_HTree) with identical transforms is the same input.
	HTree copy = tree;
	mesh.htree = &tree;
	CHECK(Submit(cache, mesh, false, true, 9U, sv, sn).stored);
	mesh.htree = &copy;
	CHECK(Submit(cache, mesh, true, false, 9U, sv, sn).from_cache);
	mesh.htree = &tree;

	// New frame drops every entry.
	CHECK(Submit(cache, mesh, false, true, 10U, sv, sn).stored);
	CHECK(!Submit(cache, mesh, false, false, 11U, sv, sn).from_cache);
	CHECK(cache.Entry_Count() == 0);

	// A destroyed mesh whose address is reused by a different skin: the key
	// matches but the inputs do not, so it misses; identical inputs reuse
	// identical bytes, which the bitwise check above proves.
	{
		Model model_b = Make_Model(rng, 200, 12, 10);
		HTree tree_b = Make_HTree(rng, 12);
		Mesh reused = { &model, &tree };
		CHECK(Submit(cache, reused, false, true, 12U, sv, sn).stored);
		reused.model = &model_b;
		reused.htree = &tree_b;
		CHECK(!Submit(cache, reused, true, false, 12U, sv, sn).from_cache);
		reused.model = &model;
		CHECK(!Submit(cache, reused, true, false, 12U, sv, sn).from_cache);
	}

	// Reserve without Commit is rolled back by the next Reserve.
	{
		Cache pending;
		V3 *dv = NULL, *dn = NULL;
		const V3 *cv = NULL, *cn = NULL;
		HTree *t = &tree;
		const auto at = [t](int p) -> const void * { return &t->pivots[static_cast<size_t>(p)]; };
		pending.Begin_Frame(1U);
		CHECK(pending.Reserve(&mesh, &model, 200, &dv, &dn));
		V3 *first = dv;
		CHECK(pending.Reserve(&mesh, &model, 200, &dv, &dn));
		CHECK(dv == first);
		Deform(mesh, dv, dn);
		CHECK(pending.Commit(model.links.data(), 200, 12, at));
		CHECK(!pending.Commit(model.links.data(), 200, 12, at));
		CHECK(pending.Find(&mesh, &model, 200, 12, at, &cv, &cn));
		// Out-of-range bone links are never stored.
		Model broken = model;
		broken.links[5] = 40;
		Mesh broken_mesh = { &broken, &tree };
		CHECK(pending.Reserve(&broken_mesh, &broken, 200, &dv, &dn));
		CHECK(!pending.Commit(broken.links.data(), 200, 12, at));
		CHECK(!pending.Find(&broken_mesh, &broken, 200, 12, at, &cv, &cn));
		// Forget during a pending reservation cancels it.
		CHECK(pending.Reserve(&broken_mesh, &model, 200, &dv, &dn));
		pending.Forget_Model(&model);
		CHECK(!pending.Commit(model.links.data(), 200, 12, at));
		CHECK(pending.Entry_Count() == 0);
		pending.Release();
		CHECK(pending.Bytes() == 0U);
		// Storage is reacquired after Release.
		pending.Begin_Frame(2U);
		CHECK(pending.Reserve(&mesh, &model, 200, &dv, &dn));
		pending.Release();
	}
	cache.Release();
}

void Capacity_Cases()
{
	std::mt19937 rng(99U);
	std::vector<V3> sv, sn;
	Cache cache;
	HTree tree = Make_HTree(rng, 64);

	// Entry table exhaustion falls back to the original scratch path.
	std::vector<Model> models;
	models.reserve(Cache::MAX_ENTRIES + 4);
	std::vector<Mesh> meshes;
	meshes.reserve(Cache::MAX_ENTRIES + 4);
	for (int i = 0; i < Cache::MAX_ENTRIES + 4; ++i) {
		models.push_back(Make_Model(rng, 16, 64, 4));
		meshes.push_back({ &models.back(), &tree });
	}
	int stored = 0;
	for (const Mesh &mesh : meshes) stored += Submit(cache, mesh, false, true, 1U, sv, sn).stored;
	CHECK(stored == Cache::MAX_ENTRIES);
	int hits = 0;
	for (const Mesh &mesh : meshes) hits += Submit(cache, mesh, true, false, 1U, sv, sn).from_cache;
	CHECK(hits == Cache::MAX_ENTRIES);
	// The four unstored material passes retried the full table as well.
	CHECK(cache.Counters().overflows == 8U);

	// Vertex arena exhaustion.
	Model huge = Make_Model(rng, Cache::MAX_VERTICES + 1, 64, 50);
	Mesh huge_mesh = { &huge, &tree };
	CHECK(!Submit(cache, huge_mesh, false, true, 2U, sv, sn).stored);
	CHECK(!Submit(cache, huge_mesh, true, false, 2U, sv, sn).from_cache);

	// Bone snapshot exhaustion: alternating links create one run per vertex.
	Model choppy = Make_Model(rng, Cache::MAX_BONES + 8, 64, 1);
	Mesh choppy_mesh = { &choppy, &tree };
	CHECK(!Submit(cache, choppy_mesh, false, true, 3U, sv, sn).stored);
	CHECK(!Submit(cache, choppy_mesh, true, false, 3U, sv, sn).from_cache);
	// The rollback left room for an ordinary skin in the same frame.
	Mesh normal_mesh = { &models[0], &tree };
	CHECK(Submit(cache, normal_mesh, false, true, 3U, sv, sn).stored);
	CHECK(Submit(cache, normal_mesh, true, false, 3U, sv, sn).from_cache);
	cache.Release();
}

// Random interleavings of renders, bone updates, model hooks, mesh reuse and
// frame changes. Every submission is checked against a fresh deformation.
void Randomized_Cases()
{
	std::mt19937 rng(20261006U);
	std::vector<V3> sv, sn;
	Cache cache;
	std::vector<Model> models;
	std::vector<HTree> trees;
	for (int i = 0; i < 4; ++i) models.push_back(Make_Model(rng, 40 + 30 * i, 16, 3 + i));
	for (int i = 0; i < 3; ++i) trees.push_back(Make_HTree(rng, 16));
	std::vector<Mesh> meshes;
	for (int i = 0; i < 6; ++i) meshes.push_back({ &models[i % 4], &trees[i % 3] });
	uint32_t frame = 1U;
	uint64_t hits = 0U;
	uint64_t stale = 0U;
	for (int step = 0; step < 30000; ++step) {
		const unsigned op = rng() % 100U;
		Mesh &mesh = meshes[rng() % meshes.size()];
		if (op < 30U) {
			Submit(cache, mesh, false, (rng() & 3U) != 0U, frame, sv, sn);
		} else if (op < 70U) {
			hits += Submit(cache, mesh, true, false, frame, sv, sn).from_cache ? 1U : 0U;
		} else if (op < 80U) {
			HTree &tree = trees[rng() % trees.size()];
			Mat &mat = tree.pivots[rng() % tree.pivots.size()];
			const unsigned kind = rng() % 4U;
			if (kind == 0U) mat = Random_Mat(rng);
			else if (kind == 1U) mat.m[rng() % 3U][rng() % 4U] *= -1.0f;
			else if (kind == 2U) mat.m[rng() % 3U][3] = (rng() & 1U) ? 0.0f : -0.0f;
			// kind 3: rewrite identical bits (animation re-evaluated, same pose).
			else mat = Mat(mat);
		} else if (op < 84U) {
			Model &model = models[rng() % models.size()];
			cache.Forget_Model(&model);
			model.vertices[rng() % model.vertices.size()].Z += 0.5f;
		} else if (op < 88U) {
			mesh.model = &models[rng() % models.size()];
		} else if (op < 92U) {
			mesh.htree = &trees[rng() % trees.size()];
		} else if (op < 95U) {
			++frame;
		} else {
			// Interleave unrelated skins to churn the arena.
			for (int i = 0; i < 4; ++i) {
				Submit(cache, meshes[rng() % meshes.size()], false, true, frame, sv, sn);
			}
		}
		stale = cache.Counters().stale;
	}
	CHECK(hits > 500U);
	CHECK(stale > 50U);
	std::printf("randomized: hits=%llu stale=%llu misses=%llu stores=%llu forgets=%llu\n",
		static_cast<unsigned long long>(cache.Counters().hits),
		static_cast<unsigned long long>(cache.Counters().stale),
		static_cast<unsigned long long>(cache.Counters().misses),
		static_cast<unsigned long long>(cache.Counters().stores),
		static_cast<unsigned long long>(cache.Counters().forgets));
	cache.Release();
}

} // namespace

int main()
{
	Targeted_Cases();
	Capacity_Cases();
	Randomized_Cases();
	if (g_failures != 0) {
		std::fprintf(stderr, "skin deform cache: %d failure(s)\n", g_failures);
		return 1;
	}
	std::printf("skin deform cache: all checks passed\n");
	return 0;
}
