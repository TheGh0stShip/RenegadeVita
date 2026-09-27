#include <cassert>
#include <cmath>
#include <vector>

// Translation-only transform fixture: exercise the production Render method's
// state updates, not a replacement physics or texture implementation.
struct Vector2 { float X, Y; Vector2(float x, float y) : X(x), Y(y) {} };
struct Vector3 {
	float X, Y, Z;
	Vector3(float x=0, float y=0, float z=0) : X(x), Y(y), Z(z) {}
	static void Subtract(const Vector3 &a, const Vector3 &b, Vector3 *v) {
		*v = Vector3(a.X-b.X, a.Y-b.Y, a.Z-b.Z);
	}
	static float Dot_Product(const Vector3 &a, const Vector3 &b) { return a.X*b.X+a.Y*b.Y+a.Z*b.Z; }
};
struct Matrix3D {
	Vector3 position;
	Vector3 operator*(const Vector3 &v) const { return Vector3(v.X+position.X,v.Y+position.Y,v.Z+position.Z); }
	void Get_X_Vector(Vector3 *v) const { *v=Vector3(1,0,0); }
};
namespace WW3D { unsigned time=0; unsigned Get_Sync_Time() { return time; } }
struct RenderInfoClass {};
struct VehiclePhysClass { unsigned draws=0; void Render(RenderInfoClass &) { ++draws; } };
struct Mapper { Vector2 rate{0,0}; unsigned updates=0; void Set_UV_Offset_Delta(Vector2 v) { rate=v; ++updates; } };
struct TrackedVehicleDefClass { float TrackUScaleFactor=1, TrackVScaleFactor=2; };
struct Contact { struct { Vector3 Extent{1,1,1}; } InnerBox; };
struct TrackedVehicleClass : VehiclePhysClass {
	enum { LEFT_TRACK, RIGHT_TRACK };
	struct Entry { int TrackType; struct Mapper *Mapper; };
	struct Entries : std::vector<Entry> { int Count() const { return size(); } } TrackMappers;
	Contact contact; Contact *ContactBox=&contact;
	Matrix3D transform;
	TrackedVehicleDefClass definition;
	float LeftTrackMovement=0, RightTrackMovement=0;
	Vector3 LeftTrackLastPosition, RightTrackLastPosition;
	unsigned LastTrackSyncTime=0;
	bool TrackPositionsInitialized=false;
	const Matrix3D &Get_Transform() const { return transform; }
	const TrackedVehicleDefClass *Get_TrackedVehicleDef() const { return &definition; }
	void Render(RenderInfoClass &);
};

// ORIGINAL_RENDER_METHOD

int main() {
	TrackedVehicleClass tank; Mapper left, right; RenderInfoClass info;
	tank.TrackMappers.push_back({tank.LEFT_TRACK,&left});
	tank.TrackMappers.push_back({tank.RIGHT_TRACK,&right});
	tank.transform.position.X=100;
	WW3D::time=1000; tank.Render(info);
	assert(left.rate.X==0 && right.rate.X==0);
	tank.transform.position.X=101;
	WW3D::time=1100; tank.Render(info);
	assert(std::fabs(left.rate.X-10)<0.001 && std::fabs(right.rate.Y-20)<0.001);
	const unsigned updates=left.updates;
	tank.Render(info);
	assert(left.updates==updates && std::fabs(left.rate.X-10)<0.001);
	assert(tank.draws==3);
	tank.transform.position.X=100;
	WW3D::time=1200; tank.Render(info);
	assert(std::fabs(left.rate.X+10)<0.001);
	WW3D::time=1300; tank.Render(info);
	assert(left.rate.X==0 && right.rate.X==0);
	tank.TrackPositionsInitialized=false;
	tank.transform.position.X=500;
	tank.Render(info);
	assert(left.rate.X==0 && right.rate.X==0);
}
