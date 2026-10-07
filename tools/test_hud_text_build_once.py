"""HUD help/objective text keeps an identical build instead of re-uploading it.

The production HUD_Help_Text_* and Objective_* code is extracted from the
staged hud.cpp and compiled twice against one model of the original
Render2DSentenceClass/Render2DClass semantics (fresh atlas surface per build
after Reset, one renderer per atlas surface, one texture per pending surface
at Render): once as the original (#else branches) and once as the Vita port.
Both run the same frame script; every rendered quad (screen position after
coordinate conversion and UV bias, UV, colour, alpha) and the content of the
texture it samples must be identical frame by frame, while the port creates
fewer text textures.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HUD = ROOT / 'staging/combat/hud.cpp'
PATCH = 'combat-a36-hud-text-build-once.patch'


def section(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


MOCK = r'''
#include <cassert>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cwchar>
#include <string>
#include <vector>
#include <algorithm>

typedef wchar_t WCHAR;
#define WWASSERT(x) assert(x)
#define DEG_TO_RAD(x) ((x) * 3.14159265358979323846 / 180.0)
#define RGB_TO_INT32(r,g,b) (unsigned(r)<<16)|(unsigned(g)<<8)|(unsigned(b))|0xFF000000
#define VRGB_TO_INT32(rgb) (unsigned(rgb[0]*255.0f)<<16)|(unsigned(rgb[1]*255.0f)<<8)|(unsigned(rgb[2]*255.0f))|0xFF000000
#define RETICLE_HEIGHT (64.0f/480.0f)

struct Vector2 {
	float X, Y;
	Vector2() : X(0), Y(0) {}
	Vector2(float x, float y) : X(x), Y(y) {}
	void Set(float x, float y) { X = x; Y = y; }
	Vector2 &operator+=(const Vector2 &o) { X += o.X; Y += o.Y; return *this; }
	Vector2 &operator-=(const Vector2 &o) { X -= o.X; Y -= o.Y; return *this; }
	Vector2 &operator*=(float s) { X *= s; Y *= s; return *this; }
};
inline Vector2 operator+(Vector2 a, const Vector2 &b) { return a += b; }
inline Vector2 operator-(Vector2 a, const Vector2 &b) { return a -= b; }
inline Vector2 operator-(const Vector2 &a) { return Vector2(-a.X, -a.Y); }
inline Vector2 operator*(Vector2 a, float s) { return a *= s; }
inline Vector2 operator*(float s, Vector2 a) { return a *= s; }
inline Vector2 operator/(Vector2 a, float s) { return Vector2(a.X / s, a.Y / s); }
inline bool operator==(const Vector2 &a, const Vector2 &b) { return a.X == b.X && a.Y == b.Y; }
inline bool operator!=(const Vector2 &a, const Vector2 &b) { return !(a == b); }

struct Vector3 {
	float X, Y, Z;
	Vector3(float x = 0, float y = 0, float z = 0) : X(x), Y(y), Z(z) {}
	float operator[](int i) const { return i == 0 ? X : (i == 1 ? Y : Z); }
	float Length() const { return std::sqrt(X*X + Y*Y + Z*Z); }
	unsigned Convert_To_ARGB() const { return 0xFF000000u | (unsigned(X*255) << 16) | (unsigned(Y*255) << 8) | unsigned(Z*255); }
};

struct RectClass {
	float Left, Top, Right, Bottom;
	RectClass() : Left(0), Top(0), Right(0), Bottom(0) {}
	RectClass(float l, float t, float r, float b) : Left(l), Top(t), Right(r), Bottom(b) {}
	RectClass(const Vector2 &a, const Vector2 &b) : Left(a.X), Top(a.Y), Right(b.X), Bottom(b.Y) {}
	float Width() const { return Right - Left; }
	float Height() const { return Bottom - Top; }
	Vector2 Center() const { return Vector2((Left + Right) / 2, (Top + Bottom) / 2); }
	Vector2 Upper_Left() const { return Vector2(Left, Top); }
	Vector2 Upper_Right() const { return Vector2(Right, Top); }
	Vector2 Lower_Left() const { return Vector2(Left, Bottom); }
	Vector2 Lower_Right() const { return Vector2(Right, Bottom); }
	RectClass &operator+=(const Vector2 &o) { Left += o.X; Right += o.X; Top += o.Y; Bottom += o.Y; return *this; }
	RectClass &operator-=(const Vector2 &o) { Left -= o.X; Right -= o.X; Top -= o.Y; Bottom -= o.Y; return *this; }
	void Scale(float s) { Left *= s; Top *= s; Right *= s; Bottom *= s; }
	bool operator==(const RectClass &o) const { return Left == o.Left && Top == o.Top && Right == o.Right && Bottom == o.Bottom; }
};

struct Matrix3D {
	Vector3 Position;
	static void Inverse_Transform_Vector(const Matrix3D &tm, const Vector3 &in, Vector3 *out) {
		*out = Vector3(in[0] - tm.Position[0], in[1] - tm.Position[1], in[2] - tm.Position[2]);
	}
};

struct WWMath {
	static float Clamp(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
	static float Fast_Sin(float v) { return std::sin(v); }
	static float Fast_Cos(float v) { return std::cos(v); }
};

class WideStringClass {
public:
	WideStringClass() {}
	WideStringClass(const WCHAR *s, bool = false) : S(s ? s : L"") {}
	WideStringClass(int, bool) {}
	operator const WCHAR *() const { return S.c_str(); }
	bool Is_Empty() const { return S.empty(); }
	bool operator==(const WCHAR *o) const { return S == o; }
	bool operator!=(const WCHAR *o) const { return S != o; }
	WideStringClass &operator=(const WCHAR *o) { S = o ? o : L""; return *this; }
	void Format(const WCHAR *f, ...) {
		WCHAR buffer[256]; va_list args; va_start(args, f);
		vswprintf(buffer, 256, f, args); va_end(args); S = buffer;
	}
	std::wstring S;
};

template <class T> struct DynamicVectorClass {
	std::vector<T> V;
	int Count() const { return int(V.size()); }
	T &operator[](int i) { return V[i]; }
	void Add(const T &t) { V.push_back(t); }
	void Delete_All() { V.clear(); }
};

struct DX8Wrapper { static bool Ready; static bool Is_Initted() { return Ready; } };
bool DX8Wrapper::Ready = true;
struct WW3D { static bool Bias; static bool Is_Screen_UV_Biased() { return Bias; } };
bool WW3D::Bias = true;

static std::string Trace;
static int TextureCreations = 0;
static int LiveTextures = 0;

struct TextureMock {
	std::wstring Content;
	int Refs = 1;
	void Add_Ref() { ++Refs; }
	void Release() { if (--Refs == 0) { --LiveTextures; delete this; } }
};

static std::string Narrow(const std::wstring &w) { return std::string(w.begin(), w.end()); }

class Render2DClass {
public:
	static RectClass Resolution;
	static const RectClass &Get_Screen_Resolution() { return Resolution; }
	Render2DClass() { Set_Coordinate_Range(RectClass(-1, -1, 1, 1)); }
	~Render2DClass() { if (Texture) Texture->Release(); }
	void Set_Coordinate_Range(const RectClass &r) {
		ScaleX = 2 / r.Width(); ScaleY = -2 / r.Height();
		OffsetX = -(ScaleX * r.Left) - 1; OffsetY = -(ScaleY * r.Top) + 1;
		Update_Bias();
	}
	void Update_Bias() {
		BiasX = OffsetX; BiasY = OffsetY;
		if (WW3D::Is_Screen_UV_Biased()) {
			BiasX += -0.5f / (Resolution.Width() * 0.5f);
			BiasY += -0.5f / (Resolution.Height() * -0.5f);
		}
	}
	void Reset() { Quads.clear(); Update_Bias(); }
	void Set_Texture(TextureMock *t) { if (t) t->Add_Ref(); if (Texture) Texture->Release(); Texture = t; Name.clear(); }
	void Set_Texture(const char *name) { if (Texture) Texture->Release(); Texture = NULL; Name = name; }
	void Add_Quad(const RectClass &s, const RectClass &uv, unsigned color = 0xFFFFFFFF) {
		char b[256];
		snprintf(b, sizeof(b), "[%.6f,%.6f,%.6f,%.6f uv %g,%g,%g,%g ",
			s.Left * ScaleX + BiasX, s.Top * ScaleY + BiasY, s.Right * ScaleX + BiasX,
			s.Bottom * ScaleY + BiasY, uv.Left, uv.Top, uv.Right, uv.Bottom);
		Quads.push_back(std::make_pair(std::string(b), color));
	}
	void Add_Quad(const RectClass &s, unsigned color = 0xFFFFFFFF) { Add_Quad(s, RectClass(0, 0, 1, 1), color); }
	void Add_Quad(const Vector2 &a, const Vector2 &b, const Vector2 &c, const Vector2 &d, unsigned color = 0xFFFFFFFF) {
		Add_Quad(RectClass(a.X, a.Y, d.X, d.Y), RectClass(b.X, b.Y, c.X, c.Y), color);
	}
	void Force_Alpha(float alpha) {
		unsigned a = unsigned(WWMath::Clamp(alpha, 0, 1) * 255.0f) << 24;
		for (auto &q : Quads) q.second = (q.second & 0x00FFFFFF) | a;
	}
	void Render() {
		if (Quads.empty()) return;
		Trace += " R(" + (Texture ? "text:" + Narrow(Texture->Content) : Name) + ")";
		for (auto &q : Quads) { char c[16]; snprintf(c, sizeof(c), "%08X]", q.second); Trace += q.first + c; }
	}
private:
	float ScaleX, ScaleY, OffsetX, OffsetY, BiasX, BiasY;
	TextureMock *Texture = NULL;
	std::string Name;
	std::vector<std::pair<std::string, unsigned> > Quads;
};
RectClass Render2DClass::Resolution(0, 0, 640, 480);

struct FontCharsClass {};
struct StyleMgrClass {
	enum { FONT_INGAME_TXT, FONT_INGAME_BIG_TXT };
	static FontCharsClass *Peek_Font(int) { static FontCharsClass font; return &font; }
};

/*
** Model of the original Render2DSentenceClass: Build_Sentence appends to the
** current atlas surface (a fresh one after Reset or Render), Draw_Sentence adds
** quads to one renderer per surface, Render turns every pending surface into a
** new texture, Reset frees renderers and surfaces.
*/
struct SurfaceMock { std::wstring Content; int Refs = 1; };
class Render2DSentenceClass {
public:
	~Render2DSentenceClass() { Reset(); }
	void Set_Font(FontCharsClass *) { Reset(); }
	void Reset() {
		for (auto &r : Renderers) delete r.first;
		Renderers.clear();
		Release(CurSurface); CurSurface = NULL;
		for (auto &p : Pending) Release(p.first);
		Pending.clear();
		Reset_Sentence_Data();
	}
	void Reset_Polys() { for (auto &r : Renderers) r.first->Reset(); }
	void Set_Location(const Vector2 &l) { Location = l; }
	Vector2 Get_Text_Extents(const WCHAR *text) {
		if (!DX8Wrapper::Is_Initted()) return Vector2(0, 0);
		return Vector2(float(7 * wcslen(text)), 16);
	}
	void Build_Sentence(const WCHAR *text) {
		if (text == NULL || !DX8Wrapper::Is_Initted()) return;
		Reset_Sentence_Data();
		if (CurSurface == NULL) {
			CurSurface = new SurfaceMock;
			++CurSurface->Refs;
			Pending.push_back(std::make_pair(CurSurface, std::vector<Render2DClass *>()));
		}
		Chunk c; c.Surface = CurSurface; ++CurSurface->Refs;
		c.UStart = float(CurSurface->Content.size()); c.Width = float(7 * wcslen(text));
		CurSurface->Content += text; CurSurface->Content += L'|';
		Chunks.push_back(c);
	}
	void Draw_Sentence(unsigned color = 0xFFFFFFFF) {
		for (auto &c : Chunks) {
			Render2DClass *renderer = NULL;
			for (auto &r : Renderers) if (r.second == c.Surface) renderer = r.first;
			if (renderer == NULL) {
				renderer = new Render2DClass;
				renderer->Set_Coordinate_Range(Render2DClass::Get_Screen_Resolution());
				Renderers.push_back(std::make_pair(renderer, c.Surface));
				for (auto &p : Pending) if (p.first == c.Surface) p.second.push_back(renderer);
			}
			RectClass screen(Location.X, Location.Y, Location.X + c.Width, Location.Y + 16);
			renderer->Add_Quad(screen, RectClass(c.UStart, 0, c.UStart + c.Width / 7, 1), color);
		}
	}
	void Force_Alpha(float a) { for (auto &r : Renderers) r.first->Force_Alpha(a); }
	void Render() {
		if (!DX8Wrapper::Is_Initted()) return;
		Release(CurSurface); CurSurface = NULL;
		for (auto &p : Pending) {
			TextureMock *texture = new TextureMock;
			texture->Content = p.first->Content;
			++TextureCreations; ++LiveTextures;
			for (auto *r : p.second) r->Set_Texture(texture);
			texture->Release();
			Release(p.first);
		}
		Pending.clear();
		for (auto &r : Renderers) r.first->Render();
	}
private:
	struct Chunk { SurfaceMock *Surface; float UStart, Width; };
	static void Release(SurfaceMock *s) { if (s && --s->Refs == 0) delete s; }
	void Reset_Sentence_Data() { for (auto &c : Chunks) Release(c.Surface); Chunks.clear(); }
	Vector2 Location;
	SurfaceMock *CurSurface = NULL;
	std::vector<std::pair<SurfaceMock *, std::vector<Render2DClass *> > > Pending;
	std::vector<std::pair<Render2DClass *, SurfaceMock *> > Renderers;
	std::vector<Chunk> Chunks;
};

struct TimeManager { static float Seconds; static float Get_Frame_Seconds() { return Seconds; } };
float TimeManager::Seconds = 1.0f / 30.0f;

struct HUDInfo {
	static WideStringClass Text; static Vector3 Color; static bool Dirty;
	static void Set_HUD_Help_Text(const WCHAR *s, const Vector3 &c = Vector3(1, 1, 1)) { Text = s; Color = c; Dirty = true; }
	static void Set_Is_HUD_Help_Text_Dirty(bool d) { Dirty = d; }
	static bool Is_HUD_Help_Text_Dirty() { return Dirty; }
	static const WideStringClass &Get_HUD_Help_Text() { return Text; }
	static const Vector3 &Get_HUD_Help_Text_Color() { return Color; }
};
WideStringClass HUDInfo::Text; Vector3 HUDInfo::Color; bool HUDInfo::Dirty = false;

struct CameraMock { Vector2 Get_Camera_Target_2D_Offset() { return Vector2(0, 0); } };
static CameraMock CameraInstance;
#define COMBAT_CAMERA (&CameraInstance)
struct StarMock { Matrix3D TM; const Matrix3D &Get_Transform() { return TM; } };
static StarMock StarInstance;
#define COMBAT_STAR (&StarInstance)

struct ObjectiveMock {
	std::wstring Message; Vector3 Location; float Age; std::string Pog; int Type;
	Vector3 Type_To_Color() { return Type ? Vector3(0, 0, 1) : Vector3(0, 1, 0); }
};
struct ObjectiveManager {
	static std::vector<ObjectiveMock> List; static bool Update;
	static int Get_Num_HUD_Objectives() { return int(List.size()); }
	static ObjectiveMock *Get_Objective(int i) { return i < int(List.size()) ? &List[i] : NULL; }
	static const char *Get_HUD_Objectives_Pog_Texture_Name(int i) { return List[i].Pog.c_str(); }
	static float Get_HUD_Objectives_Age(int i) { return List[i].Age; }
	static Vector3 Get_HUD_Objectives_Location(int i) { return List[i].Location; }
	static const WCHAR *Get_HUD_Objectives_Message(int i) { return List[i].Message.c_str(); }
	static bool Are_HUD_Objectives_Changed() { return Update; }
	static void Clear_HUD_Objectives_Changed() { Update = false; }
};
std::vector<ObjectiveMock> ObjectiveManager::List; bool ObjectiveManager::Update = false;

enum { INPUT_FUNCTION_CYCLE_POG };
struct Input { static bool Cycle; static bool Get_State(int) { return Cycle; } };
bool Input::Cycle = false;
#define IS_MISSION true
enum { IDS_HUD_RANGE };
#define TRANSLATE(id) L"Range: %dm"

enum { HUD_HELP_TEXT_DISPLAYING = 0, HUD_HELP_TEXT_FADING, HUD_HELP_TEXT_DONE };
static const WCHAR HUD_EMPTY_TEXT[] = { 0 };
Render2DSentenceClass *HUDHelpTextRenderer;
Vector2 HUDHelpTextExtents(0, 0);
float HUDHelpTextTimer = 0;
int HUDHelpTextState = HUD_HELP_TEXT_DISPLAYING;
'''

SCRIPT = r'''
static void Frame(int f)
{
	Trace += "\nF" + std::to_string(f) + ":";
	HUD_Help_Text_Render();
	Objective_Update();
	Objective_Render();
	for (auto &o : ObjectiveManager::List) o.Age += TimeManager::Get_Frame_Seconds();
}

int main()
{
	HUD_Help_Text_Init();
	Objective_Init();
	ObjectiveMock a = { L"Destroy the SAM Site", Vector3(200, 0, 0), 0.0f, "POG_A.TGA", 0 };
	ObjectiveManager::List.push_back(a);
	ObjectiveManager::Update = true;
	for (int f = 0; f < 400; ++f) {
		// Standing on a powerup that cannot be taken: same text every frame.
		if (f < 40 || (f >= 150 && f < 170) || (f >= 300 && f < 320)) {
			HUDInfo::Set_HUD_Help_Text(L"Health full", Vector3(0, 1, 0));
		}
		if (f == 60) HUDInfo::Set_HUD_Help_Text(L"Quick Saved", Vector3(0, 1, 0));
		if (f >= 155 && f < 158) HUDInfo::Set_HUD_Help_Text(L"Armor full", Vector3(0, 1, 0));
		if (f == 45) {
			ObjectiveMock b = { L"Escort the convoy", Vector3(-80, 40, 0), 0.0f, "POG_B.TGA", 1 };
			ObjectiveManager::List.push_back(b);
			ObjectiveManager::Update = true;
		}
		if (f == 30 || f == 160) Render2DClass::Resolution = RectClass(0, 0, 960, 544);
		if (f == 35 || f == 165 || f == 295) Render2DClass::Resolution = RectClass(0, 0, 640, 480);
		// Same upper-right corner during a pog fly-in: the objective text keeps
		// its positions but its renderers' coordinate range changes.
		if (f == 285) Render2DClass::Resolution = RectClass(0, 0, 640, 400);
		if (f == 50 || f == 52 || f == 310) WW3D::Bias = !WW3D::Bias;
		if (f >= 20 && f < 23) DX8Wrapper::Ready = false; else DX8Wrapper::Ready = true;
		Input::Cycle = (f == 90 || f == 210);
		if (f == 120) { ObjectiveManager::List[1].Age = 0; ObjectiveManager::Update = true; }
		// Shown objective changes to a message of the same width.
		if (f == 230) { ObjectiveManager::List[0].Message = L"Destroy the SAM Base"; ObjectiveManager::List[0].Age = 0; ObjectiveManager::Update = true; }
		if (f == 250) { ObjectiveManager::List.clear(); ObjectiveManager::Update = true; }
		if (f == 270) { ObjectiveMock c = { L"Reach the extraction point", Vector3(0, -300, 0), 0.0f, "POG_C.TGA", 0 }; ObjectiveManager::List.push_back(c); ObjectiveManager::Update = true; }
		StarInstance.TM.Position = Vector3(float(f) * 0.9f, 0, 0);
		Frame(f);
	}
	HUD_Help_Text_Shutdown();
	Objective_Shutdown();
	assert(LiveTextures == 0);
	printf("TEXTURES %d\n", TextureCreations);
	fputs(Trace.c_str(), stdout);
	return 0;
}
'''


class HudTextBuildOnceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = HUD.read_text(errors='replace')
        cls.source = source
        help_text = section(source, '#if defined(RENEGADE_VITA_PORT)\n// The help text HUDHelpTextRenderer',
                            'static\tvoid\tWeapon_Init( void )')
        objective = section(source, 'DynamicVectorClass<Render2DClass *>\tObjectivePogRenderers;',
                            '/*\n** Info Display')
        program = MOCK + help_text + objective + SCRIPT
        cls.results = {}
        with tempfile.TemporaryDirectory(prefix='renegade-hud-text-') as folder:
            cpp = Path(folder) / 'hud_text.cpp'
            cpp.write_text(program)
            for name, defines in (('original', []), ('port', ['-DRENEGADE_VITA_PORT'])):
                exe = Path(folder) / name
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wno-unused-variable',
                                '-Wno-unused-but-set-variable', '-fsanitize=address,undefined',
                                '-fno-sanitize-recover=all', *defines, str(cpp), '-o', str(exe)],
                               check=True)
                run = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
                first, _, trace = run.stdout.partition('\n')
                cls.results[name] = (int(first.split()[1]), trace)

    def test_rendered_frames_identical(self):
        original = self.results['original'][1].splitlines()
        port = self.results['port'][1].splitlines()
        self.assertEqual(len(original), len(port))
        self.assertGreater(len(original), 300)
        for index, (left, right) in enumerate(zip(original, port)):
            self.assertEqual(left, right, f'frame line {index} differs')
        # The script must actually show help text and objective text.
        joined = '\n'.join(port)
        self.assertIn('text:Health full|', joined)
        # Same length as the first message, so only the string differs.
        self.assertIn('text:Destroy the SAM Base|Range: ', joined)
        self.assertIn('text:Reach the extraction point|Range: ', joined)

    def test_port_creates_fewer_text_textures(self):
        original = self.results['original'][0]
        port = self.results['port'][0]
        self.assertLess(port, original)
        self.assertLess(port * 3, original)

    def test_patch_registered_once_after_hud_load_admission(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        self.assertEqual(stage.count(PATCH), 1)
        self.assertLess(stage.index('combat-a36-hud-load-admission.patch'), stage.index(PATCH))
        self.assertTrue((ROOT / 'port/patches' / PATCH).is_file())


if __name__ == '__main__':
    unittest.main()
