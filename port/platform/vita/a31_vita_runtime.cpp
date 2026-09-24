#include "a31_vita_runtime.h"

#include "a30_vita_runtime.h"
#include "a31_interactive_runtime_policy.h"
#include "a31_capture_telemetry.h"
#include "a31_demo_ending.h"
#include "a35_campaign_flight_recorder.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "a4_frontend_lifecycle_boundary.h"
#include "a31_development_checkpoint.h"
#endif
#include "renegade_cache_health.h"
#include "renegade_file_factory.h"
#include "renegade_find_files.h"
#include "renegade_vita_options.h"
#include "renegade_miles_runtime_stats.h"
#include "renegade_vita_input_telemetry.h"
#include "renegade_build_identity.h"
#include "ww3d_vita_renderer.h"

#include "assetmgr.h"
#include "assetdep.h"
#include "assets.h"
#include "campaign.h"
#include "ccamera.h"
#include "encyclopediamgr.h"
#include "chunkio.h"
#include "combat.h"
#include "combatgmode.h"
#include "consolemode.h"
#include "cnetwork.h"
#include "d3d8.h"
#include "datasafe.h"
#include "damage.h"
#include "debug.h"
#include "definition.h"
#include "definitionmgr.h"
#include "definitionfactorymgr.h"
#include "explosion.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "gamedata.h"
#include "gameinitmgr.h"
#include "gamemode.h"
#include "gameobjmanager.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "dialogmgr.h"
#include "dlgevaencyclopedia.h"
#include "gamemenu.h"
#include "movie.h"
#include "renegadedialogmgr.h"
#if !RENEGADE_VITA_M00_DEMO
#include "scorescreen.h"
#endif
#endif
#include "gdsingleplayer.h"
#include "gametype.h"
#include "god.h"
#include "hanim.h"
#include "htree.h"
#include "hud.h"
#include "input.h"
#include "mixfile.h"
#include "netinterface.h"
#include "networkobjectmgr.h"
#include "pathmgr.h"
#include "playermanager.h"
#include "playertype.h"
#include "radar.h"
#include "ramfile.h"
#include "renegadecheatmgr.h"
#include "render2d.h"
#include "render2dsentence.h"
#include "saveload.h"
#include "saveloadstatus.h"
#include "screenfademanager.h"
#include "serverfps.h"
#include "singlepl.h"
#include "scripts.h"
#include "scene.h"
#include "soldier.h"
#include "stylemgr.h"
#include "teammanager.h"
#include "textdisplay.h"
#include "textwindow.h"
#include "timemgr.h"
#include "textureloader.h"
#include "texture.h"
#include "timeddecophys.h"
#include "vehicle.h"
#include "hashtemplate.h"
#include "menubackdrop.h"
#include "translatedb.h"
#include "renegade_vita_tutorial_help.h"
#include "translateobj.h"
#include "ww3d.h"
#include "wwaudio.h"
#include "wwmath.h"
#include "wwphys.h"
#include "wwsaveload.h"

#include <psp2/ctrl.h>
#include <psp2/display.h>
#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <debugScreen.h>

#include <math.h>
#include <new>
#include <memory>
#include <algorithm>
#include <atomic>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

extern void _Force_Link_Soldier(void);
extern void *Commando_Create_Original_Loading_Screen(void);
extern void Commando_Render_Original_Loading_Screen(void *screen, bool update_network);
extern bool Commando_Original_Loading_Screen_Has_Backdrop_Model(void *screen);
extern void Commando_Destroy_Original_Loading_Screen(void *screen);
extern void Commando_Set_Original_Loading_Progress(void *screen, float progress);
extern GameObject *Find_Object(int obj_id);
extern void Set_Position(GameObject *obj, const Vector3 &position);
extern void Set_Facing(GameObject *obj, float degrees);
extern void Select_Weapon(GameObject *obj, const char *weapon_name);
extern void Send_Custom_Event(GameObject *from, GameObject *to, int type, int param, float delay);
extern void Attach_Script(GameObject *object, const char *script_name, const char *script_params);
extern GameObject *Create_Object(const char *type_name, const Vector3 &position);

struct A35PreparedRenderObjectSlot {
	const char *name;
	RenderObjClass *object;
};

static A35PreparedRenderObjectSlot g_A35PreparedRenderObjects[128];

void A35_Vita_Clear_Prepared_Render_Objs(void)
{
	for (unsigned i = 0; i < sizeof(g_A35PreparedRenderObjects) / sizeof(g_A35PreparedRenderObjects[0]); ++i) {
		if (g_A35PreparedRenderObjects[i].object != NULL) {
			A30_Vita_Log("A4 prepared render object: released stale=%s slot=%u object=%p\n",
				g_A35PreparedRenderObjects[i].name != NULL ? g_A35PreparedRenderObjects[i].name : "(null)",
				i,
				static_cast<void *>(g_A35PreparedRenderObjects[i].object));
			g_A35PreparedRenderObjects[i].object->Release_Ref();
			g_A35PreparedRenderObjects[i].object = NULL;
			g_A35PreparedRenderObjects[i].name = NULL;
		}
	}
}

bool A35_Vita_Retain_Prepared_Render_Obj(const char *name)
{
	if (name == NULL || WW3DAssetManager::Get_Instance() == NULL) {
		return false;
	}
	int slot = -1;
	for (unsigned i = 0; i < sizeof(g_A35PreparedRenderObjects) / sizeof(g_A35PreparedRenderObjects[0]); ++i) {
		if (g_A35PreparedRenderObjects[i].object == NULL) {
			slot = static_cast<int>(i);
			break;
		}
	}
	if (slot < 0) {
		A30_Vita_Log("A4 prepared render object: retain failed no slot model=%s\n", name);
		return false;
	}
	const uint64_t start_us = sceKernelGetProcessTimeWide();
	RenderObjClass *object = WW3DAssetManager::Get_Instance()->Create_Render_Obj(name);
	const uint64_t elapsed_us = sceKernelGetProcessTimeWide() - start_us;
	g_A35PreparedRenderObjects[slot].name = object != NULL ? name : NULL;
	g_A35PreparedRenderObjects[slot].object = object;
	A30_Vita_Log("A4 prepared render object: retained=%s created=%d slot=%d elapsed_us=%llu object=%p\n",
		name,
		object != NULL ? 1 : 0,
		slot,
		static_cast<unsigned long long>(elapsed_us),
		static_cast<void *>(object));
	return object != NULL;
}

bool A35_Vita_Warm_Render_Obj(const char *name)
{
	if (name == NULL || WW3DAssetManager::Get_Instance() == NULL) {
		return false;
	}
	const uint64_t start_us = sceKernelGetProcessTimeWide();
	RenderObjClass *object = WW3DAssetManager::Get_Instance()->Create_Render_Obj(name);
	const uint64_t elapsed_us = sceKernelGetProcessTimeWide() - start_us;
	if (object != NULL) {
		object->Release_Ref();
	}
	A30_Vita_Log("A4 prepared render object: warmed=%s created=%d elapsed_us=%llu object_released=1\n",
		name,
		object != NULL ? 1 : 0,
		static_cast<unsigned long long>(elapsed_us));
	return object != NULL;
}

bool A35_Vita_Prepare_Render_Obj(const char *name, bool retain, unsigned count)
{
	if (!retain) {
		return A35_Vita_Warm_Render_Obj(name);
	}
	bool prepared = false;
	const unsigned attempts = count > 0U ? count : 1U;
	for (unsigned i = 0; i < attempts; ++i) {
		prepared = A35_Vita_Retain_Prepared_Render_Obj(name) || prepared;
	}
	return prepared;
}

RenderObjClass *A35_Vita_Take_Prepared_Render_Obj(const char *name)
{
	if (name == NULL) {
		return NULL;
	}
	for (unsigned i = 0; i < sizeof(g_A35PreparedRenderObjects) / sizeof(g_A35PreparedRenderObjects[0]); ++i) {
		if (g_A35PreparedRenderObjects[i].object != NULL &&
			g_A35PreparedRenderObjects[i].name != NULL &&
			stricmp(g_A35PreparedRenderObjects[i].name, name) == 0) {
			RenderObjClass *object = g_A35PreparedRenderObjects[i].object;
			g_A35PreparedRenderObjects[i].object = NULL;
			g_A35PreparedRenderObjects[i].name = NULL;
			A30_Vita_Log("A4 prepared render object: consumed=%s slot=%u object=%p\n",
				name,
				i,
				static_cast<void *>(object));
			return object;
		}
	}
	return NULL;
}

namespace {

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
bool g_gameplay_pause_requested = false;
#endif

const RenegadePathRoots kVitaRoots = {
	"ux0:data/renegade/retail",
	"ux0:data/renegade/user",
	"ux0:data/renegade/cache",
	"ux0:data/renegade/mods"
};

const char *const kAlways2Archive = "Data\\Always2.dat";
const char *const kAlwaysDbsArchive = "Data\\always.dbs";
const char *const kAlwaysArchive = "Data\\Always.dat";
const char *const kM00Archive = "Data\\M00_Tutorial.mix";
const char *const kStringsDatabase = "STRINGS.TDB";
const char *const kStyleManagerIni = "stylemgr.ini";
const char *const kM00CacheIndex = "cache/m00-tutorial-mix-index-v1.txt";
const char *const kStartupPrecacheReceiptPath =
	RENEGADE_BUILD_STARTUP_PRECACHE_RECEIPT_PATH;
const uint32_t kTimingWindowFrames = 120U;
const uint32_t kCaptureWidth = RenegadeVitaRenderer::DISPLAY_WIDTH;
const uint32_t kCaptureHeight = RenegadeVitaRenderer::DISPLAY_HEIGHT;
const uint32_t kCaptureBytes = kCaptureWidth * kCaptureHeight * 4U;
const unsigned kStartupPrecacheVisibleSteps = 6U;
const uint64_t kStartupPrecacheMinimumVisibleUs = 1000000ULL;
const unsigned kLoadingProgressCatchupFrames = 3U;
const unsigned kStartupPrecacheRequiredReadBytes = 32768U;
const unsigned kStartupPrecacheOptionalReadBytes = 8192U;
const unsigned kStartupPrecacheMovieReadBytes = 65536U;
const unsigned kStartupStatusRepaintIntervalUs = 250000U;
const unsigned kLoadingPrewarmFrames = 1U;
const unsigned kM00ScenePrewarmFrames = 60U;
const int kCncMultiplayerLoadBackdropNumber = 94;
const float kOriginalLoadingLogicalWidth = 640.0f;
const float kOriginalLoadingLogicalHeight = 480.0f;
const float kOriginalFrontendLogicalWidth = 800.0f;
const float kOriginalFrontendLogicalHeight = 600.0f;
const float kGameplayHUDLogicalWidth =
	static_cast<float>(RenegadeVitaRenderer::DISPLAY_WIDTH);
const float kGameplayHUDLogicalHeight =
	static_cast<float>(RenegadeVitaRenderer::DISPLAY_HEIGHT);

#if RENEGADE_VITA_M00_DEMO
class A31DemoEndingPresenter;
A31DemoEndingPresenter *g_demo_ending_presenter = NULL;

class A31DemoEndingPresenter {
public:
	A31DemoEndingPresenter() : TextPhase(A31Demo::Ending::Playing), Backdrop(NULL) {
		g_demo_ending_presenter = this;
	}
	~A31DemoEndingPresenter() {
		delete Backdrop;
		g_demo_ending_presenter = NULL;
	}
	bool Render_Credit_Frame() {
		if (WW3D::Begin_Render(true, true, Vector3(0, 0, 0)) != WW3D_ERROR_OK)
			return false;
		Render();
		return WW3D::End_Render() == WW3D_ERROR_OK;
	}
	void Render() {
		if (!Timeline.Active()) return;
		const A31Demo::Ending::Phase phase = Timeline.GetPhase();
		const bool credit_scene = phase == A31Demo::Ending::Thanks ||
			phase == A31Demo::Ending::CreditScene;
		if (credit_scene) {
			if (Backdrop == NULL) {
				Backdrop = new MenuBackDropClass;
				Backdrop->Set_Model("IF_BACK01");
				Backdrop->Set_Animation("IF_BACK01.IF_BACK01");
				A30_Vita_Log("A3.5 demo ending: original animated menu imagery available=%d\n",
					Backdrop->Peek_Model() != NULL ? 1 : 0);
			}
			Backdrop->Render();
		}
		const RectClass screen(0.0f, 0.0f, kGameplayHUDLogicalWidth,
			kGameplayHUDLogicalHeight);
		Black.Reset();
		Black.Set_Coordinate_Range(screen);
		Black.Enable_Texturing(false);
		Black.Enable_Alpha(true);
		Black.Add_Quad(screen, credit_scene ? 0xA8000000U :
			static_cast<unsigned long>(Timeline.Alpha() * 255.0f) << 24);
		if (credit_scene) {
			Black.Add_Quad(RectClass(320.0f, 146.0f, 640.0f, 148.0f), 0xFFE6BC58U);
		}
		Black.Render();
		if (!credit_scene) return;
		if (TextPhase != phase) {
			Text.Reset();
			Title.Reset();
			FontCharsClass *font = StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT);
			FontCharsClass *title_font = StyleMgrClass::Peek_Font(StyleMgrClass::FONT_MENU);
			if (font == NULL || title_font == NULL) {
				A30_Vita_Log("A3.5 demo ending: original font unavailable phase=%d\n", phase);
				TextPhase = phase;
				return;
			}
			Text.Set_Font(font);
			Title.Set_Font(title_font);
			Add_Centered_Line(Title, "RENEGADE VITA", 88.0f, 0xFFE6BC58U);
			if (phase == A31Demo::Ending::Thanks) {
				Add_Centered_Line(Text, "Thank you for playing the Renegade Vita Demo!", 218.0f);
				Add_Centered_Line(Text, "There is still more work to be done", 266.0f);
				Add_Centered_Line(Text, "before this is a complete title. Stay tuned!", 298.0f);
				Add_Centered_Line(Text, "Built for PlayStation Vita", 410.0f, 0xFFE6BC58U);
			} else {
				const char *lines[] = {
					"Native port: Renegade Vita project",
					"Original game: Westwood Studios / Electronic Arts",
					"VitaSDK contributors",
					"vitaGL / vitaShaRK / SceShaccCgExt",
					"FFmpeg / mpg123 / FreeType / zlib / libpng",
					"bzip2 / minizip / taiHEN / math-neon",
					"With thanks to the PlayStation Vita homebrew community."
				};
				for (unsigned i = 0; i < sizeof(lines) / sizeof(lines[0]); ++i)
					Add_Centered_Line(Text, lines[i], 184.0f + 34.0f * i);
				Add_Centered_Line(Text, "Returning to main menu", 464.0f, 0xFFE6BC58U);
			}
			TextPhase = phase;
			A30_Vita_Log("A3.5 demo ending: presentation phase=%d original_sentence_owner=1\n", phase);
		}
		Title.Render();
		Text.Render();
	}
	A31Demo::Ending Timeline;
private:
	static void Add_Centered_Line(Render2DSentenceClass &renderer,
		const char *line, float y, uint32_t color = 0xFFFFFFFFU) {
		WideStringClass text;
		text.Convert_From(line);
		const Vector2 size = renderer.Get_Text_Extents(text);
		renderer.Build_Sentence(text);
		renderer.Set_Location(Vector2((kGameplayHUDLogicalWidth - size.X) * 0.5f, y));
		renderer.Draw_Sentence(color);
	}
	A31Demo::Ending::Phase TextPhase;
	MenuBackDropClass *Backdrop;
	Render2DClass Black;
	Render2DSentenceClass Text;
	Render2DSentenceClass Title;
};
#endif

struct A31NativePresentationRect
{
	uint32_t x;
	uint32_t y;
	uint32_t width;
	uint32_t height;
};

struct A31StartupPrecacheResult
{
	bool passed;
	unsigned archives_valid;
	unsigned archives_total;
	unsigned entries_indexed;
	unsigned files_touched;
	unsigned files_opened;
	unsigned required_files_touched;
	unsigned required_files_opened;
	unsigned optional_files_touched;
	unsigned optional_files_opened;
	unsigned movie_files_touched;
	unsigned movie_files_opened;
	unsigned cache_indexes_attempted;
	unsigned cache_indexes_written;
	unsigned cache_entries_written;
	uint64_t bytes_read;
	char first_missing_required[96];
	char first_missing_optional[96];
	char first_cache_failure[96];
};

struct A31StartupPrecacheFileSpec
{
	const char *name;
	bool required;
	unsigned read_limit;
};

std::atomic<int> g_debug_status_draw_lock(0);
std::atomic<int> g_startup_status_repaint_active(0);
std::atomic<const char *> g_startup_status_phase(NULL);
std::atomic<const char *> g_startup_status_detail(NULL);
int g_startup_status_screen_result = -1;

class A31ScopedDebugStatusDraw
{
public:
	A31ScopedDebugStatusDraw() : Locked(false)
	{
		int expected = 0;
		Locked = g_debug_status_draw_lock.compare_exchange_strong(expected, 1,
			std::memory_order_acq_rel, std::memory_order_acquire);
	}
	~A31ScopedDebugStatusDraw()
	{
		if (Locked) {
			g_debug_status_draw_lock.store(0, std::memory_order_release);
		}
	}
	bool Acquired() const { return Locked; }
private:
	bool Locked;
};

A31NativePresentationRect Build_Aspect_Preserved_Presentation_Rect(
	uint32_t logical_width, uint32_t logical_height)
{
	const uint32_t display_width = RenegadeVitaRenderer::DISPLAY_WIDTH;
	const uint32_t display_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
	uint32_t width = display_width;
	uint32_t height =
		static_cast<uint32_t>((static_cast<uint64_t>(display_width) *
			logical_height) / logical_width);
	if (height > display_height) {
		height = display_height;
		width = static_cast<uint32_t>((static_cast<uint64_t>(display_height) *
			logical_width) / logical_height);
	}
	A31NativePresentationRect rect = {
		(display_width - width) / 2U,
		(display_height - height) / 2U,
		width,
		height
	};
	return rect;
}

A31NativePresentationRect Build_Original_Loading_Presentation_Rect()
{
	return Build_Aspect_Preserved_Presentation_Rect(
		static_cast<uint32_t>(kOriginalLoadingLogicalWidth),
		static_cast<uint32_t>(kOriginalLoadingLogicalHeight));
}

A31NativePresentationRect Build_Original_Frontend_Presentation_Rect()
{
	return Build_Aspect_Preserved_Presentation_Rect(
		static_cast<uint32_t>(kOriginalFrontendLogicalWidth),
		static_cast<uint32_t>(kOriginalFrontendLogicalHeight));
}

bool Apply_Original_Loading_Presentation_Rect(const char *reason,
	bool log_state)
{
	const A31NativePresentationRect rect =
		Build_Original_Loading_Presentation_Rect();
	const bool applied = RenegadeVitaRenderer::Set_Native_Presentation_Rect(
		rect.x, rect.y, rect.width, rect.height);
	if (log_state) {
		A30_Vita_Log("A3.5 loading screen: original 640x480 presentation rect reason=%s native=%u,%u %ux%u display=%ux%u aspect_preserved=%d applied=%d\n",
			reason != NULL ? reason : "unknown",
			rect.x, rect.y, rect.width, rect.height,
			RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT,
			1, applied ? 1 : 0);
	}
	return applied;
}

bool Apply_Original_Frontend_Presentation_Rect(const char *reason,
	bool log_state)
{
	const A31NativePresentationRect rect =
		Build_Original_Frontend_Presentation_Rect();
	const bool applied = RenegadeVitaRenderer::Set_Native_Presentation_Rect(
		rect.x, rect.y, rect.width, rect.height);
	if (log_state) {
		A30_Vita_Log("A4 frontend: original 800x600 presentation rect reason=%s native=%u,%u %ux%u display=%ux%u aspect_preserved=%d applied=%d\n",
			reason != NULL ? reason : "unknown",
			rect.x, rect.y, rect.width, rect.height,
			RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT,
			1, applied ? 1 : 0);
	}
	return applied;
}

/* Original Commando gives WWAudio a path-stripping factory over the active
** retail/MIX chain. Keep the same semantic boundary here so authoring paths
** such as always\\sound\\... resolve to the basename stored in the archives.
** This adapter and WWAudio are declared after the chain, so audio teardown
** returns every file before the stack-local factories are destroyed. */
class A31AudioFileFactoryClass final : public SimpleFileFactoryClass
{
public:
	explicit A31AudioFileFactoryClass(FileFactoryClass *base_factory) :
		BaseFactory(base_factory)
	{
	}

	FileClass *Get_File(char const *filename) override
	{
		if (BaseFactory == NULL || filename == NULL) return NULL;
		StringClass stripped(true);
		Strip_Path_From_Filename(stripped, filename);
		return BaseFactory->Get_File(stripped);
	}

private:
	FileFactoryClass *BaseFactory;
};

bool Load_Strings_Database_For_Loading_Screen()
{
	TranslateDBClass::Initialize();
	FileClass *file = _TheFileFactory != NULL ? _TheFileFactory->Get_File(kStringsDatabase) : NULL;
	if (file == NULL) {
		A30_Vita_Log("A3.5 loading screen: FAIL strings database file unavailable name=%s\n",
			kStringsDatabase);
		return false;
	}

	bool loaded = false;
	if (file->Open(FileClass::READ)) {
		if (file->Is_Available()) {
			ChunkLoadClass cload(file);
			loaded = SaveLoadSystemClass::Load(cload);
		}
		file->Close();
	}
	_TheFileFactory->Return_File(file);
	if (loaded) {
		unsigned replaced = 0;
		for (int i = 0; i < TranslateDBClass::Get_Object_Count(); ++i) {
			TDBObjClass *entry = TranslateDBClass::Get_Object(i);
			if (entry == NULL) continue;
			const char *hint = Renegade_Vita_Tutorial_Help(entry->Get_ID(), 0U);
			if (hint == NULL) continue;
			WideStringClass native_text;
			native_text.Convert_From(hint);
			entry->Set_String(TranslateDBClass::LANGID_ENGLISH, native_text);
			++replaced;
		}
		A30_Vita_Log("A3.5 tutorial: in-memory English Vita control captions=%u retail_unchanged=1\n", replaced);
	}
	A30_Vita_Log("A3.5 loading screen: strings database load=%d name=%s version=%lu\n",
		loaded ? 1 : 0, kStringsDatabase,
		static_cast<unsigned long>(TranslateDBClass::Get_Version_Number()));
	return loaded;
}

unsigned Count_Visible_Glyph_Columns(const std::vector<uint16> &pixels,
	int width, int height)
{
	if (width <= 0 || height <= 0) return 0U;
	unsigned visible_columns = 0U;
	for (int x = 0; x < width; ++x) {
		bool column_visible = false;
		for (int y = 0; y < height; ++y) {
			const size_t index = static_cast<size_t>(y) *
				static_cast<size_t>(width) + static_cast<size_t>(x);
			if (pixels[index] != 0U) {
				column_visible = true;
				break;
			}
		}
		if (column_visible) ++visible_columns;
	}
	return visible_columns;
}

unsigned Minimum_Visible_Glyph_Columns(int width)
{
	return width >= 4 ? 2U : 1U;
}

bool Validate_StyleMgr_Font_Glyphs(const char *scope)
{
	struct FontProbe {
		StyleMgrClass::FONT_STYLE style;
		const char *name;
	};
	const FontProbe probes[] = {
		{ StyleMgrClass::FONT_TITLE, "FONT_TITLE" },
		{ StyleMgrClass::FONT_LG_CONTROLS, "FONT_LG_CONTROLS" },
		{ StyleMgrClass::FONT_CONTROLS, "FONT_CONTROLS" },
		{ StyleMgrClass::FONT_LISTS, "FONT_LISTS" },
		{ StyleMgrClass::FONT_TOOLTIPS, "FONT_TOOLTIPS" },
		{ StyleMgrClass::FONT_MENU, "FONT_MENU" },
		{ StyleMgrClass::FONT_SM_MENU, "FONT_SM_MENU" },
		{ StyleMgrClass::FONT_HEADER, "FONT_HEADER" },
		{ StyleMgrClass::FONT_BIG_HEADER, "FONT_BIG_HEADER" },
		{ StyleMgrClass::FONT_CREDITS, "FONT_CREDITS" },
		{ StyleMgrClass::FONT_CREDITS_BOLD, "FONT_CREDITS_BOLD" },
		{ StyleMgrClass::FONT_INGAME_TXT, "FONT_INGAME_TXT" },
		{ StyleMgrClass::FONT_INGAME_BIG_TXT, "FONT_INGAME_BIG_TXT" },
		{ StyleMgrClass::FONT_INGAME_SUBTITLE_TXT, "FONT_INGAME_SUBTITLE_TXT" },
		{ StyleMgrClass::FONT_INGAME_HEADER_TXT, "FONT_INGAME_HEADER_TXT" }
	};
	bool ok = true;
	for (unsigned index = 0U; index < sizeof(probes) / sizeof(probes[0]);
		++index) {
		FontCharsClass *font = StyleMgrClass::Peek_Font(probes[index].style);
		const int height = font != NULL ? font->Get_Char_Height() : 0;
		const int spacing_a = font != NULL ?
			font->Get_Char_Spacing(static_cast<WCHAR>('A')) : 0;
		const int spacing_0 = font != NULL ?
			font->Get_Char_Spacing(static_cast<WCHAR>('0')) : 0;
		const int width_a = font != NULL ?
			font->Get_Char_Width(static_cast<WCHAR>('A')) : 0;
		const int width_0 = font != NULL ?
			font->Get_Char_Width(static_cast<WCHAR>('0')) : 0;
		unsigned visible_pixels_a = 0U;
		unsigned visible_pixels_0 = 0U;
		unsigned visible_columns_a = 0U;
		unsigned visible_columns_0 = 0U;
		if (font != NULL && height > 0 && width_a > 0) {
			std::vector<uint16> pixels(static_cast<size_t>(width_a) *
				static_cast<size_t>(height), 0);
			font->Blit_Char(static_cast<WCHAR>('A'), pixels.data(),
				width_a * static_cast<int>(sizeof(uint16)), 0, 0);
			for (size_t pixel_index = 0U; pixel_index < pixels.size();
				++pixel_index) {
				if (pixels[pixel_index] != 0U) ++visible_pixels_a;
			}
			visible_columns_a =
				Count_Visible_Glyph_Columns(pixels, width_a, height);
		}
		if (font != NULL && height > 0 && width_0 > 0) {
			std::vector<uint16> pixels(static_cast<size_t>(width_0) *
				static_cast<size_t>(height), 0);
			font->Blit_Char(static_cast<WCHAR>('0'), pixels.data(),
				width_0 * static_cast<int>(sizeof(uint16)), 0, 0);
			for (size_t pixel_index = 0U; pixel_index < pixels.size();
				++pixel_index) {
				if (pixels[pixel_index] != 0U) ++visible_pixels_0;
			}
			visible_columns_0 =
				Count_Visible_Glyph_Columns(pixels, width_0, height);
		}
		const bool glyph_a_ok = visible_pixels_a > 0U &&
			visible_columns_a >= Minimum_Visible_Glyph_Columns(width_a);
		const bool glyph_0_ok = visible_pixels_0 > 0U &&
			visible_columns_0 >= Minimum_Visible_Glyph_Columns(width_0);
		const bool font_ok = height > 0 &&
			(spacing_a > 0 || spacing_0 > 0) &&
			(glyph_a_ok || glyph_0_ok);
		if (!font_ok) ok = false;
		A30_Vita_Log("A4 frontend/text: StyleMgr font probe scope=%s font=%s ptr=%p height=%d spacing_A=%d spacing_0=%d width_A=%d width_0=%d visible_A=%u columns_A=%u visible_0=%u columns_0=%u ok=%d\n",
			scope != NULL ? scope : "unknown", probes[index].name,
			static_cast<void *>(font), height, spacing_a, spacing_0,
			width_a, width_0, visible_pixels_a, visible_columns_a,
			visible_pixels_0, visible_columns_0, font_ok ? 1 : 0);
	}
	if (!ok) {
		A30_Vita_Log("A4 frontend/text: FAIL StyleMgr font glyph probe scope=%s; refusing to enter visually blank text state\n",
			scope != NULL ? scope : "unknown");
	}
	return ok;
}

void Flush_Debug_Status(unsigned frames)
{
	for (unsigned index = 0U; index < frames; ++index) {
		sceDisplayWaitVblankStart();
	}
}

void Set_Startup_Status_Repaint_Phase(const char *phase, const char *detail)
{
	g_startup_status_phase.store(phase != NULL ? phase : "unknown",
		std::memory_order_release);
	g_startup_status_detail.store(detail != NULL ? detail : "",
		std::memory_order_release);
}

void Draw_Engine_Setup_Screen(int startup_screen_result, const char *phase,
	const char *detail)
{
	if (startup_screen_result < 0) return;
	Set_Startup_Status_Repaint_Phase(phase, detail);
	A31ScopedDebugStatusDraw draw_lock;
	if (!draw_lock.Acquired()) return;
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\n", RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("Original engine setup / frontend handoff\n\n");
	psvDebugScreenPrintf("Now:  %s\n", phase != NULL ? phase : "unknown");
	if (detail != NULL && detail[0] != 0) {
		psvDebugScreenPrintf("Info: %s\n", detail);
	}
	psvDebugScreenPrintf("\nThis screen stays active until vitaGL owns display.\n");
	psvDebugScreenPrintf("Next: original intro movies, menu, then M00 tutorial.\n");
	psvDebugScreenPrintf("Log:  %s\n", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	Flush_Debug_Status(1U);
}

int Startup_Status_Repaint_Thread(SceSize, void *)
{
	unsigned tick = 0U;
	while (g_startup_status_repaint_active.load(std::memory_order_acquire) != 0) {
		const char *phase =
			g_startup_status_phase.load(std::memory_order_acquire);
		const char *detail =
			g_startup_status_detail.load(std::memory_order_acquire);
		Draw_Engine_Setup_Screen(g_startup_status_screen_result, phase, detail);
		if ((tick % 4U) == 0U) {
			A30_Vita_Log("A3.5 startup: verbose status repaint active tick=%u phase=%s before_vitagl=1\n",
				tick, phase != NULL ? phase : "unknown");
		}
		++tick;
		sceKernelDelayThread(kStartupStatusRepaintIntervalUs);
	}
	return 0;
}

class A31ScopedStartupStatusRepaint
{
public:
	explicit A31ScopedStartupStatusRepaint(int startup_screen_result) :
		Thread(-1)
	{
		if (startup_screen_result < 0) return;
		g_startup_status_screen_result = startup_screen_result;
		Set_Startup_Status_Repaint_Phase(
			"Opening original retail data factories",
			"verbose status repaints until visible pre-cache starts");
		g_startup_status_repaint_active.store(1, std::memory_order_release);
		Thread = sceKernelCreateThread("RenegadeStartupStatus",
			Startup_Status_Repaint_Thread, 0x10000100, 0x4000, 0, 0, NULL);
		if (Thread >= 0) {
			const int start_result = sceKernelStartThread(Thread, 0, NULL);
			if (start_result < 0) {
				g_startup_status_repaint_active.store(0,
					std::memory_order_release);
				A30_Vita_Log("A3.5 startup: verbose status repaint start failed rc=%08X\n",
					static_cast<unsigned>(start_result));
				(void)sceKernelDeleteThread(Thread);
				Thread = -1;
			} else {
				A30_Vita_Log("A3.5 startup: verbose status repaint started before_vitagl=1 interval_us=%u\n",
					kStartupStatusRepaintIntervalUs);
			}
		} else {
			g_startup_status_repaint_active.store(0, std::memory_order_release);
			A30_Vita_Log("A3.5 startup: verbose status repaint create failed rc=%08X\n",
				static_cast<unsigned>(Thread));
		}
	}

	~A31ScopedStartupStatusRepaint()
	{
		Stop("scope-exit");
	}

	void Stop(const char *reason)
	{
		if (Thread < 0) return;
		g_startup_status_repaint_active.store(0, std::memory_order_release);
		int exit_status = 0;
		(void)sceKernelWaitThreadEnd(Thread, &exit_status, NULL);
		(void)sceKernelDeleteThread(Thread);
		A30_Vita_Log("A3.5 startup: verbose status repaint stopped reason=%s status=%d before_vitagl=1\n",
			reason != NULL ? reason : "unknown", exit_status);
		Thread = -1;
	}

private:
	SceUID Thread;
};

void Draw_Startup_Precache_Screen(int startup_screen_result, const char *phase,
	unsigned step, unsigned percent, const A31StartupPrecacheResult &state,
	const char *detail)
{
	if (startup_screen_result < 0) return;
	if (percent > 100U) percent = 100U;
	A31ScopedDebugStatusDraw draw_lock;
	if (!draw_lock.Acquired()) return;
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("%s\n", RENEGADE_BUILD_DISPLAY_LABEL);
	psvDebugScreenPrintf("Pre-cache / pre-warm / pre-compute\n\n");
	psvDebugScreenPrintf("Phase %u/%u: %s\n", step,
		kStartupPrecacheVisibleSteps, phase != NULL ? phase : "unknown");
	psvDebugScreenPrintf("[");
	const unsigned filled = percent / 5U;
	for (unsigned index = 0U; index < 20U; ++index) {
		psvDebugScreenPrintf(index < filled ? "#" : ".");
	}
	psvDebugScreenPrintf("] %u%%\n\n", percent);
	psvDebugScreenPrintf("Original MIX archives: %u/%u\n",
		state.archives_valid, state.archives_total);
	psvDebugScreenPrintf("Indexed entries:       %u\n", state.entries_indexed);
	psvDebugScreenPrintf("Startup files:         %u/%u\n",
		state.files_opened, state.files_touched);
	psvDebugScreenPrintf("Required startup:      %u/%u\n",
		state.required_files_opened, state.required_files_touched);
	psvDebugScreenPrintf("Optional startup:      %u/%u\n",
		state.optional_files_opened, state.optional_files_touched);
	psvDebugScreenPrintf("Movie files:           %u/%u\n",
		state.movie_files_opened, state.movie_files_touched);
	psvDebugScreenPrintf("Cache indexes:         %u/%u (%u entries)\n",
		state.cache_indexes_written, state.cache_indexes_attempted,
		state.cache_entries_written);
	psvDebugScreenPrintf("Bytes touched:         %llu\n",
		static_cast<unsigned long long>(state.bytes_read));
	if (state.first_missing_required[0] != 0) {
		psvDebugScreenPrintf("Missing required:      %s\n",
			state.first_missing_required);
	} else if (state.first_cache_failure[0] != 0) {
		psvDebugScreenPrintf("Cache issue:           %s\n",
			state.first_cache_failure);
	} else if (state.first_missing_optional[0] != 0) {
		psvDebugScreenPrintf("Missing optional:      %s\n",
			state.first_missing_optional);
	}
	if (detail != NULL && detail[0] != 0) {
		psvDebugScreenPrintf("Now:                   %s\n", detail);
	}
	psvDebugScreenPrintf("\nThis runs before intro movies, menus, and M00 input.\n");
	psvDebugScreenPrintf("Log: %s\n", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	psvDebugScreenPrintf("Receipt: %s\n", kStartupPrecacheReceiptPath);
}

bool Startup_Index_Mix_Archive(const char *name, MixFileFactoryClass &factory,
	A31StartupPrecacheResult &state)
{
	++state.archives_total;
	DynamicVectorClass<StringClass> names;
	names.Set_Growth_Step(1000);
	const bool listed = factory.Is_Valid() && factory.Build_Filename_List(names);
	const unsigned count = listed && names.Count() > 0 ?
		static_cast<unsigned>(names.Count()) : 0U;
	if (count != 0U) {
		++state.archives_valid;
		state.entries_indexed += count;
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache archive=%s valid=%d listed=%d entries=%u retained_factory=1 original_mix_owner=1\n",
		name != NULL ? name : "unknown", factory.Is_Valid() ? 1 : 0,
		listed ? 1 : 0, count);
	return count != 0U;
}

bool Safe_Startup_Cache_Entry_Name(const char *name)
{
	if (name == NULL || name[0] == 0) return false;
	for (const char *cursor = name; *cursor != 0; ++cursor) {
		if (*cursor == '\r' || *cursor == '\n') return false;
	}
	return true;
}

bool Startup_Write_Mix_Index_Cache(const char *archive_label, bool required,
	const char *cache_logical, MixFileFactoryClass &factory,
	A31StartupPrecacheResult &state)
{
	++state.cache_indexes_attempted;
	DynamicVectorClass<StringClass> names;
	names.Set_Growth_Step(1000);
	std::vector<std::string> entries;
	bool ok = factory.Is_Valid() && factory.Build_Filename_List(names);
	for (int index = 0; ok && index < names.Count(); ++index) {
		const char *name = names[index];
		if (!Safe_Startup_Cache_Entry_Name(name)) {
			ok = false;
			break;
		}
		entries.push_back(name);
	}
	std::sort(entries.begin(), entries.end());
	const RenegadeResolvedPath resolved = Renegade_Resolve_Path(kVitaRoots,
		cache_logical, RENEGADE_PATH_WRITE);
	ok = ok && !entries.empty() && resolved.success &&
		resolved.writable_namespace &&
		strncasecmp(resolved.normalized_logical, "cache/", 6U) == 0;
	if (ok) {
		(void)sceIoMkdir(kVitaRoots.cache, 0777);
		FILE *output = fopen(resolved.physical, "wb");
		ok = output != NULL;
		if (ok) {
			ok = fprintf(output,
				"schema=renegade-vita-mix-index-v1\n"
				"archive=%s\n"
				"entry_count=%u\n",
				archive_label != NULL ? archive_label : "unknown",
				static_cast<unsigned>(entries.size())) > 0;
			for (std::vector<std::string>::const_iterator entry =
					entries.begin();
				ok && entry != entries.end(); ++entry) {
				ok = fprintf(output, "entry=%s\n", entry->c_str()) > 0;
			}
			const bool flushed = fflush(output) == 0;
			const bool closed = fclose(output) == 0;
			ok = ok && flushed && closed;
		}
	}
	if (ok) {
		++state.cache_indexes_written;
		state.cache_entries_written += static_cast<unsigned>(entries.size());
	} else if (required && state.first_cache_failure[0] == 0) {
		snprintf(state.first_cache_failure,
			sizeof(state.first_cache_failure), "%s",
			archive_label != NULL ? archive_label : "unknown");
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache cache-index archive=%s path=%s written=%d entries=%u original_mix_owner=1 cache_namespace=1\n",
		archive_label != NULL ? archive_label : "unknown",
		resolved.success ? resolved.physical : cache_logical,
		ok ? 1 : 0, static_cast<unsigned>(entries.size()));
	return ok;
}

bool Startup_Touch_File(FileFactoryClass &factory,
	const A31StartupPrecacheFileSpec &spec,
	A31StartupPrecacheResult &state)
{
	const char *name = spec.name;
	++state.files_touched;
	if (spec.required) {
		++state.required_files_touched;
	} else {
		++state.optional_files_touched;
	}
	const bool movie_file = name != NULL &&
		(::strstr(name, "MOVIES") != NULL ||
		 ::strstr(name, "Movies") != NULL ||
		 ::strstr(name, "movies") != NULL ||
		 ::strstr(name, ".BIK") != NULL ||
		 ::strstr(name, ".bik") != NULL);
	if (movie_file) {
		++state.movie_files_touched;
	}
	unsigned read_bytes = 0U;
	bool opened = false;
	FileClass *file = factory.Get_File(name);
	if (file != NULL && file->Open(FileClass::READ)) {
		opened = true;
		char buffer[2048];
		unsigned remaining = spec.read_limit;
		if (remaining == 0U) {
			remaining = spec.required ?
				kStartupPrecacheRequiredReadBytes :
				kStartupPrecacheOptionalReadBytes;
		}
		for (; remaining != 0U;) {
			const unsigned request = remaining < sizeof(buffer) ?
				remaining : static_cast<unsigned>(sizeof(buffer));
			const int received = file->Read(buffer, request);
			if (received <= 0) break;
			read_bytes += static_cast<unsigned>(received);
			remaining -= static_cast<unsigned>(received);
			if (static_cast<unsigned>(received) != request) break;
		}
		file->Close();
	}
	if (file != NULL) {
		factory.Return_File(file);
	}
	if (opened) {
		++state.files_opened;
		if (spec.required) {
			++state.required_files_opened;
		} else {
			++state.optional_files_opened;
		}
		state.bytes_read += read_bytes;
		if (movie_file) {
			++state.movie_files_opened;
		}
	} else if (spec.required && state.first_missing_required[0] == 0) {
		snprintf(state.first_missing_required,
			sizeof(state.first_missing_required), "%s",
			name != NULL ? name : "unknown");
	} else if (!spec.required && state.first_missing_optional[0] == 0) {
		snprintf(state.first_missing_optional,
			sizeof(state.first_missing_optional), "%s",
			name != NULL ? name : "unknown");
	}
	A30_Vita_Log("A3.5 prewarm: startup-precache touch kind=%s name=%s opened=%d read_bytes=%u limit=%u movie=%d original_file_factory=1\n",
		spec.required ? "required" : "optional",
		name != NULL ? name : "unknown", opened ? 1 : 0, read_bytes,
		spec.read_limit, movie_file ? 1 : 0);
	return opened;
}

void Write_Startup_Precache_Receipt(const A31StartupPrecacheResult &state,
	uint64_t elapsed_us)
{
	const SceUID file = sceIoOpen(kStartupPrecacheReceiptPath,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_TRUNC, 0666);
	if (file < 0) {
		A30_Vita_Log("A3.5 prewarm: startup-precache receipt write failed path=%s rc=%08X\n",
			kStartupPrecacheReceiptPath, static_cast<unsigned>(file));
		return;
	}
	char receipt[1024];
	const int count = snprintf(receipt, sizeof(receipt),
		"candidate=%s\n"
		"phase=startup-precache\n"
		"pass=%d\n"
		"archives=%u/%u\n"
		"entries=%u\n"
		"files=%u/%u\n"
		"required_files=%u/%u\n"
		"optional_files=%u/%u\n"
		"movie_files=%u/%u\n"
		"cache_indexes=%u/%u\n"
		"cache_entries=%u\n"
		"bytes=%llu\n"
		"elapsed_ms=%llu\n"
		"visible_minimum_ms=%llu\n"
		"before_frontend=1\n"
		"before_movies=1\n"
		"before_gameplay=1\n"
		"first_missing_required=%s\n"
		"first_missing_optional=%s\n"
		"cache_issue=%s\n",
		RENEGADE_BUILD_CANDIDATE_LABEL, state.passed ? 1 : 0,
		state.archives_valid, state.archives_total, state.entries_indexed,
		state.files_opened, state.files_touched,
		state.required_files_opened, state.required_files_touched,
		state.optional_files_opened, state.optional_files_touched,
		state.movie_files_opened, state.movie_files_touched,
		state.cache_indexes_written, state.cache_indexes_attempted,
		state.cache_entries_written,
		static_cast<unsigned long long>(state.bytes_read),
		static_cast<unsigned long long>(elapsed_us / 1000ULL),
		static_cast<unsigned long long>(
			kStartupPrecacheMinimumVisibleUs / 1000ULL),
		state.first_missing_required[0] != 0 ?
			state.first_missing_required : "none",
		state.first_missing_optional[0] != 0 ?
			state.first_missing_optional : "none",
		state.first_cache_failure[0] != 0 ?
			state.first_cache_failure : "none");
	unsigned written_total = 0U;
	if (count > 0) {
		const unsigned length = static_cast<unsigned>(
			count < static_cast<int>(sizeof(receipt)) ? count :
			static_cast<int>(sizeof(receipt) - 1));
		while (written_total < length) {
			const int written = sceIoWrite(file, receipt + written_total,
				length - written_total);
			if (written <= 0) break;
			written_total += static_cast<unsigned>(written);
		}
	}
	const int close_result = sceIoClose(file);
	A30_Vita_Log("A3.5 prewarm: startup-precache receipt path=%s bytes=%u close=%08X\n",
		kStartupPrecacheReceiptPath, written_total,
		static_cast<unsigned>(close_result));
}

bool Run_Visible_Startup_Precache_Phase(int startup_screen_result,
	FileFactoryClass &factory, MixFileFactoryClass &always2_factory,
	MixFileFactoryClass &always_dbs_factory, MixFileFactoryClass &always_factory,
	MixFileFactoryClass &m00_factory)
{
	A31StartupPrecacheResult state = {};
	const uint64_t started_us = sceKernelGetProcessTimeWide();
	A30_Vita_Log("A3.5 prewarm: startup-precache begin visible=%d before_frontend=1 before_movies=1 before_gameplay=1 input_enabled=0\n",
		startup_screen_result >= 0 ? 1 : 0);
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Indexing original retail MIX archives", 1U, 5U, state,
		"Always/Always2/always.dbs/M00");
	Flush_Debug_Status(1U);

	bool archives_ok = true;
	archives_ok = Startup_Index_Mix_Archive(kAlways2Archive, always2_factory,
		state) && archives_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Indexing original retail MIX archives", 2U, 25U, state,
		kAlways2Archive);
	Flush_Debug_Status(1U);
	archives_ok = Startup_Index_Mix_Archive(kAlwaysDbsArchive,
		always_dbs_factory, state) && archives_ok;
	archives_ok = Startup_Index_Mix_Archive(kAlwaysArchive, always_factory,
		state) && archives_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Precomputing archive name tables", 3U, 50U, state,
		kAlwaysArchive);
	Flush_Debug_Status(1U);
	archives_ok = Startup_Index_Mix_Archive(kM00Archive, m00_factory, state) &&
		archives_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Writing persistent cache indexes", 4U, 55U, state,
		"M00_Tutorial.mix");
	const bool m00_cache_ok = Startup_Write_Mix_Index_Cache(
		"M00_Tutorial.mix", true, kM00CacheIndex, m00_factory, state);
	Draw_Startup_Precache_Screen(startup_screen_result,
		"Persistent cache indexes ready", 4U, 60U, state,
		m00_cache_ok ? "M00 cache written" : "M00 cache unavailable");
	Flush_Debug_Status(1U);

	const A31StartupPrecacheFileSpec startup_files[] = {
		{ kAlways2Archive, true, kStartupPrecacheRequiredReadBytes },
		{ kAlwaysDbsArchive, true, kStartupPrecacheRequiredReadBytes },
		{ kAlwaysArchive, true, kStartupPrecacheRequiredReadBytes },
		{ kM00Archive, true, kStartupPrecacheRequiredReadBytes },
		{ kStringsDatabase, true, kStartupPrecacheRequiredReadBytes },
		{ kStyleManagerIni, true, kStartupPrecacheRequiredReadBytes },
		{ "DEFAULT_INPUT.CFG", true, kStartupPrecacheRequiredReadBytes },
		{ "if_lvl94load.w3d", true, kStartupPrecacheRequiredReadBytes },
		{ "IF_BACK01.W3D", true, kStartupPrecacheRequiredReadBytes },
		{ "IF_RENLOGO.W3D", true, kStartupPrecacheRequiredReadBytes },
		{ "IF_EVAGIZMO.W3D", true, kStartupPrecacheRequiredReadBytes },
		{ "M00_Tutorial.lsd", true, kStartupPrecacheRequiredReadBytes },
		{ "M00_Tutorial.ldd", true, kStartupPrecacheRequiredReadBytes },
		{ "m00_tutorial.dep", true, kStartupPrecacheRequiredReadBytes },
		{ "54251___.TTF", false, kStartupPrecacheRequiredReadBytes },
		{ "ARI_____.TTF", false, kStartupPrecacheRequiredReadBytes },
		{ "FONT12x16.TGA", false, kStartupPrecacheOptionalReadBytes },
		{ "FONT6x8.TGA", false, kStartupPrecacheOptionalReadBytes },
		{ "FONT8x8.TGA", false, kStartupPrecacheOptionalReadBytes },
		{ "HUD_MAIN.TGA", false, kStartupPrecacheOptionalReadBytes },
		{ "HUD_CHATPBOX.TGA", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_6x4_Messages.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_armor1.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_armor2.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_armor3.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_health1.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_health2.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_health3.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_armedal.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "hud_hemedal.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "shadowblob.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_01.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_02.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_03.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_04.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_05.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "POG_M00_1_06.tga", false, kStartupPrecacheOptionalReadBytes },
		{ "DATA\\MOVIES\\EA_WW.BIK", false, kStartupPrecacheMovieReadBytes },
		{ "DATA\\MOVIES\\R_INTRO.BIK", false, kStartupPrecacheMovieReadBytes },
		{ "Data\\Movies\\R_Intro.BIK", false, kStartupPrecacheMovieReadBytes },
		{ "data\\subtitle.ini", false, kStartupPrecacheOptionalReadBytes }
	};
	for (unsigned index = 0U;
		index < sizeof(startup_files) / sizeof(startup_files[0]); ++index) {
		Startup_Touch_File(factory, startup_files[index], state);
		if ((index % 3U) == 2U || index + 1U ==
			sizeof(startup_files) / sizeof(startup_files[0])) {
			char detail[96];
			snprintf(detail, sizeof(detail), "%s", startup_files[index].name);
			Draw_Startup_Precache_Screen(startup_screen_result,
				"Touching startup menu, movie, loading, and M00 files",
				5U, 62U + ((index + 1U) * 30U) /
					(sizeof(startup_files) / sizeof(startup_files[0])),
				state, detail);
			Flush_Debug_Status(1U);
		}
	}
	state.passed = archives_ok && state.archives_valid == state.archives_total &&
		state.required_files_opened == state.required_files_touched &&
		m00_cache_ok;
	Draw_Startup_Precache_Screen(startup_screen_result,
		state.passed ? "Startup pre-cache complete" :
			"Startup pre-cache incomplete", 6U, 100U, state,
		state.passed ? "starting original intro/menu" :
			"continuing only if required archives are present");
	const uint64_t after_work_us = sceKernelGetProcessTimeWide();
	if (startup_screen_result >= 0 &&
		after_work_us - started_us < kStartupPrecacheMinimumVisibleUs) {
		const uint64_t hold_us =
			kStartupPrecacheMinimumVisibleUs - (after_work_us - started_us);
		A30_Vita_Log("A3.5 prewarm: startup-precache visible hold remaining_ms=%llu minimum_ms=%llu\n",
			static_cast<unsigned long long>(hold_us / 1000ULL),
			static_cast<unsigned long long>(
				kStartupPrecacheMinimumVisibleUs / 1000ULL));
		sceKernelDelayThread(static_cast<unsigned int>(hold_us));
	} else {
		Flush_Debug_Status(3U);
	}
	Write_Startup_Precache_Receipt(state,
		sceKernelGetProcessTimeWide() - started_us);
	A30_Vita_Log("A3.5 prewarm: startup-precache complete pass=%d archives=%u/%u entries=%u files=%u/%u required_files=%u/%u optional_files=%u/%u movie_files=%u/%u cache_indexes=%u/%u cache_entries=%u bytes=%llu elapsed_ms=%llu visible_minimum_ms=%llu receipt=%s missing_required=%s missing_optional=%s cache_issue=%s before_frontend=1 before_movies=1 before_gameplay=1 original_mix_owner=1\n",
		state.passed ? 1 : 0, state.archives_valid, state.archives_total,
		state.entries_indexed, state.files_opened, state.files_touched,
		state.required_files_opened, state.required_files_touched,
		state.optional_files_opened, state.optional_files_touched,
		state.movie_files_opened, state.movie_files_touched,
		state.cache_indexes_written, state.cache_indexes_attempted,
		state.cache_entries_written,
		static_cast<unsigned long long>(state.bytes_read),
		static_cast<unsigned long long>(
			(sceKernelGetProcessTimeWide() - started_us) / 1000ULL),
		static_cast<unsigned long long>(
			kStartupPrecacheMinimumVisibleUs / 1000ULL),
		kStartupPrecacheReceiptPath,
		state.first_missing_required[0] != 0 ?
			state.first_missing_required : "none",
		state.first_missing_optional[0] != 0 ?
			state.first_missing_optional : "none",
		state.first_cache_failure[0] != 0 ?
			state.first_cache_failure : "none");
	return state.passed;
}

class A31VitaScopedLoadingRenderResolution
{
public:
	A31VitaScopedLoadingRenderResolution() :
		PreviousWidth(0),
		PreviousHeight(0),
		PreviousBits(0),
		PreviousWindowed(false),
		PresentationRectApplied(false),
		Applied(false)
	{
		WW3D::Get_Device_Resolution(PreviousWidth, PreviousHeight,
			PreviousBits, PreviousWindowed);
		PresentationRectApplied =
			Apply_Original_Loading_Presentation_Rect("loading_scope", true);
		Applied = WW3D::Set_Device_Resolution(
			static_cast<int>(kOriginalLoadingLogicalWidth),
			static_cast<int>(kOriginalLoadingLogicalHeight), -1, -1,
			false) == WW3D_ERROR_OK;
		const A31NativePresentationRect rect =
			Build_Original_Loading_Presentation_Rect();
		A30_Vita_Log("A3.5 loading screen: original logical WW3D/DX8/Render2D resolution %.0fx%.0f over Vita display %ux%u presentation=%u,%u %ux%u aspect_preserved=1 applied=%d rect_applied=%d previous=%dx%d\n",
			kOriginalLoadingLogicalWidth, kOriginalLoadingLogicalHeight,
			kCaptureWidth, kCaptureHeight, rect.x, rect.y, rect.width,
			rect.height, Applied ? 1 : 0,
			PresentationRectApplied ? 1 : 0, PreviousWidth,
			PreviousHeight);
	}

	~A31VitaScopedLoadingRenderResolution()
	{
		if (PresentationRectApplied) {
			RenegadeVitaRenderer::Reset_Native_Presentation_Rect();
		}
		if (Applied) {
			const int previous_windowed = PreviousWindowed ? 1 : 0;
			WW3D::Set_Device_Resolution(PreviousWidth, PreviousHeight,
				PreviousBits, previous_windowed, false);
		}
		A30_Vita_Log("A3.5 loading screen: restored Vita WW3D/DX8/Render2D resolution %dx%d applied=%d rect_reset=%d\n",
			PreviousWidth, PreviousHeight, Applied ? 1 : 0,
			PresentationRectApplied ? 1 : 0);
	}

	A31VitaScopedLoadingRenderResolution(const A31VitaScopedLoadingRenderResolution &) = delete;
	A31VitaScopedLoadingRenderResolution &operator=(const A31VitaScopedLoadingRenderResolution &) = delete;

private:
	int PreviousWidth;
	int PreviousHeight;
	int PreviousBits;
	bool PreviousWindowed;
	bool PresentationRectApplied;
	bool Applied;
};

class A31VitaScopedFrontendRenderResolution
{
public:
	A31VitaScopedFrontendRenderResolution() :
		PreviousWidth(0),
		PreviousHeight(0),
		PreviousBits(0),
		PreviousWindowed(false),
		PresentationRectApplied(false),
		Applied(false)
	{
		WW3D::Get_Device_Resolution(PreviousWidth, PreviousHeight,
			PreviousBits, PreviousWindowed);
		PresentationRectApplied =
			Apply_Original_Frontend_Presentation_Rect("frontend_scope", true);
		Applied = WW3D::Set_Device_Resolution(
			static_cast<int>(kOriginalFrontendLogicalWidth),
			static_cast<int>(kOriginalFrontendLogicalHeight), -1, -1,
			false) == WW3D_ERROR_OK;
		const A31NativePresentationRect rect =
			Build_Original_Frontend_Presentation_Rect();
		A30_Vita_Log("A4 frontend: original logical WW3D/DX8/Render2D resolution %.0fx%.0f over Vita display %ux%u presentation=%u,%u %ux%u aspect_preserved=1 applied=%d rect_applied=%d previous=%dx%d\n",
			kOriginalFrontendLogicalWidth, kOriginalFrontendLogicalHeight,
			kCaptureWidth, kCaptureHeight, rect.x, rect.y, rect.width,
			rect.height, Applied ? 1 : 0,
			PresentationRectApplied ? 1 : 0, PreviousWidth,
			PreviousHeight);
	}

	~A31VitaScopedFrontendRenderResolution()
	{
		if (PresentationRectApplied) {
			RenegadeVitaRenderer::Reset_Native_Presentation_Rect();
		}
		if (Applied) {
			const int previous_windowed = PreviousWindowed ? 1 : 0;
			WW3D::Set_Device_Resolution(PreviousWidth, PreviousHeight,
				PreviousBits, previous_windowed, false);
		}
		A30_Vita_Log("A4 frontend: restored Vita WW3D/DX8/Render2D resolution %dx%d applied=%d rect_reset=%d\n",
			PreviousWidth, PreviousHeight, Applied ? 1 : 0,
			PresentationRectApplied ? 1 : 0);
	}

	A31VitaScopedFrontendRenderResolution(
		const A31VitaScopedFrontendRenderResolution &) = delete;
	A31VitaScopedFrontendRenderResolution &operator=(
		const A31VitaScopedFrontendRenderResolution &) = delete;

private:
	int PreviousWidth;
	int PreviousHeight;
	int PreviousBits;
	bool PreviousWindowed;
	bool PresentationRectApplied;
	bool Applied;
};

class A31VitaScopedGameplayHUDRender2DResolution
{
public:
	explicit A31VitaScopedGameplayHUDRender2DResolution(const char *reason, bool log_transition = true) :
		Previous(Render2DClass::Get_Screen_Resolution()),
		Reason(reason != NULL ? reason : "unknown"), LogTransition(log_transition)
	{
		Render2DClass::Set_Screen_Resolution(RectClass(0, 0,
			kGameplayHUDLogicalWidth, kGameplayHUDLogicalHeight));
		if (LogTransition) A30_Vita_Log("A3.5 HUD: native gameplay Render2D resolution %.0fx%.0f reason=%s previous=%.0fx%.0f\n",
			kGameplayHUDLogicalWidth, kGameplayHUDLogicalHeight, Reason,
			Previous.Width(), Previous.Height());
	}

	~A31VitaScopedGameplayHUDRender2DResolution()
	{
		Render2DClass::Set_Screen_Resolution(Previous);
		if (LogTransition) A30_Vita_Log("A3.5 HUD: restored Render2D resolution %.0fx%.0f reason=%s\n",
			Previous.Width(), Previous.Height(), Reason);
	}

	A31VitaScopedGameplayHUDRender2DResolution(
		const A31VitaScopedGameplayHUDRender2DResolution &) = delete;
	A31VitaScopedGameplayHUDRender2DResolution &operator=(
		const A31VitaScopedGameplayHUDRender2DResolution &) = delete;

private:
	RectClass Previous;
	const char *Reason;
	bool LogTransition;
};

void Copy_Renderer_Statistics(A31RendererTelemetry &telemetry)
{
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	telemetry.draw_calls = static_cast<uint64_t>(statistics.mesh_submissions) +
		static_cast<uint64_t>(statistics.indexed_submissions);
	telemetry.mesh_submissions = statistics.mesh_submissions;
	telemetry.vertices = statistics.vertex_submissions;
	telemetry.triangles = statistics.triangle_submissions;
	telemetry.indexed_draw_calls = statistics.indexed_submissions;
	telemetry.indexed_vertex_references = statistics.indexed_vertex_references;
	telemetry.indexed_triangles = statistics.indexed_triangle_submissions;
	telemetry.material_passes = statistics.material_passes;
	telemetry.textures_resident = statistics.texture_resident;
	telemetry.texture_bytes_resident = statistics.texture_bytes_resident;
	telemetry.texture_uploads = statistics.texture_uploads;
	telemetry.texture_binds = statistics.texture_binds;
	telemetry.texture_bind_skips = statistics.texture_bind_skips;
	telemetry.texture_requests = statistics.texture_requests;
	telemetry.texture_decodes = statistics.texture_decodes;
	telemetry.texture_dds_loads = statistics.texture_dds_loads;
	telemetry.texture_tga_loads = statistics.texture_tga_loads;
	telemetry.texture_missing = statistics.texture_missing;
	telemetry.texture_source_missing = statistics.texture_source_missing;
	telemetry.texture_invalid_data = statistics.texture_invalid_data;
	telemetry.texture_unsupported_formats = statistics.texture_unsupported_formats;
	telemetry.texture_decode_failures = statistics.texture_decode_failures;
	telemetry.texture_upload_failures = statistics.texture_upload_failures;
	telemetry.texture_checkerboard_fallbacks = statistics.texture_checkerboard_fallbacks;
	telemetry.texture_checkerboard_binds = statistics.texture_checkerboard_binds;
	telemetry.texture_invalid_binds = statistics.texture_invalid_binds;
	telemetry.texture_sampler_updates = statistics.texture_sampler_updates;
	telemetry.texture_sampler_skips = statistics.texture_sampler_skips;
	telemetry.texture_stage_enable_skips = statistics.texture_stage_enable_skips;
	telemetry.texture_combiner_skips = statistics.texture_combiner_skips;
	telemetry.texture_unsupported_stages = statistics.texture_unsupported_stages;
	telemetry.state_changes = statistics.state_changes;
	telemetry.render_state_skips = statistics.render_state_skips;
	telemetry.rejected_submissions = statistics.rejected_indexed_submissions;
	telemetry.unsupported_submissions = statistics.unsupported_submissions;
	telemetry.backend_errors = statistics.backend_errors;
	telemetry.geometry_checksum = statistics.geometry_checksum;
	telemetry.indexed_geometry_checksum = statistics.indexed_geometry_checksum;
}

class A31VitaLoadingPresenter
{
public:
	A31VitaLoadingPresenter() :
		Screen(NULL),
		BackdropReady(false),
		LastMirroredLoadProgress(-1)
	{
	}

	~A31VitaLoadingPresenter()
	{
		Commando_Destroy_Original_Loading_Screen(Screen);
		Screen = NULL;
	}

	bool Initialize(const char *mission_archive)
	{
		int backdrop_number = kCncMultiplayerLoadBackdropNumber;
#if !RENEGADE_VITA_M00_DEMO
		if (mission_archive == NULL || mission_archive[0] == '\0') return false;
		backdrop_number = cGameData::Get_Mission_Number_From_Map_Name(mission_archive);
#else
		(void)mission_archive;
#endif
		CampaignManager::Select_Backdrop_Number(backdrop_number);
		const int description_count = CampaignManager::Get_Backdrop_Description_Count();
		StringClass selected_model(0, true);
		for (int index = 0; index < description_count; ++index) {
			StringClass desc = CampaignManager::Get_Backdrop_Description(index);
			while (desc.Get_Length() != 0 && desc[0] <= ' ') desc.Erase(0, 1);
			while (desc.Get_Length() != 0 && desc[desc.Get_Length() - 1] <= ' ') {
				desc.Erase(desc.Get_Length() - 1, 1);
			}
			if (::strnicmp("Model", desc, 5) == 0) {
				desc.Erase(0, 5);
				while (desc.Get_Length() != 0 && desc[0] <= ' ') desc.Erase(0, 1);
				selected_model = desc;
			}
		}
		Screen = Commando_Create_Original_Loading_Screen();
		BackdropReady =
			Commando_Original_Loading_Screen_Has_Backdrop_Model(Screen);
		A30_Vita_Log("A3.5 loading screen: original class state=%d descriptions=%d model=%s ready=%d direct_vitagl_tiles=0 progress_owner=original_LoadingScreenClass\n",
			backdrop_number, description_count,
			selected_model.Get_Length() != 0 ?
				static_cast<const char *>(selected_model) : "none",
			BackdropReady ? 1 : 0);
		return Screen != NULL && BackdropReady;
	}

	void *Peek_Screen() const
	{
		return Screen;
	}

	void Render_Original_Progress(const char *phase, bool update_network = true,
		int minimum_progress = -1)
	{
		StringClass load_status;
		StringClass load_sub_status;
		SaveLoadStatus::Get_Status_Text(load_status, 0);
		SaveLoadStatus::Get_Status_Text(load_sub_status, 1);
		const int status_count = SaveLoadStatus::Get_Status_Count();
		const int current_progress = CombatManager::Get_Load_Progress();
		int mirrored_progress = current_progress;
		// SaveLoadStatus counts chunks; Combat progress uses seven milestones.
		// Mixing the two makes a large archive jump straight to 100 percent.
		if (minimum_progress > mirrored_progress) mirrored_progress = minimum_progress;
		if (mirrored_progress > current_progress) {
			CombatManager::Set_Load_Progress(mirrored_progress);
		}
		const bool progress_changed =
			LastMirroredLoadProgress != mirrored_progress;
		Apply_Original_Loading_Presentation_Rect(
			"loading_presenter_render", false);
		Commando_Render_Original_Loading_Screen(Screen, update_network);
		unsigned catchup_frames = 0U;
		if (progress_changed) {
			for (unsigned frame = 0U;
				frame < kLoadingProgressCatchupFrames; ++frame) {
				sceDisplayWaitVblankStart();
				Commando_Render_Original_Loading_Screen(Screen, false);
				++catchup_frames;
			}
		}
		if (progress_changed ||
			phase == NULL ||
			::strstr(phase, "complete") != NULL ||
			::strstr(phase, "ready") != NULL ||
			::strstr(phase, "prewarm") != NULL) {
			LastMirroredLoadProgress = mirrored_progress;
		}
		A30_Vita_Log("A3.5 loading screen: phase=%s original_class=1 original_backdrop=%d progress=%d status_count=%d changed=%d catchup_frames=%u status=%s sub_status=%s\n",
			phase != NULL ? phase : "unknown", BackdropReady ? 1 : 0,
			CombatManager::Get_Load_Progress(), status_count,
			progress_changed ? 1 : 0, catchup_frames,
			static_cast<const char *>(load_status),
			static_cast<const char *>(load_sub_status));
	}

private:
	void *Screen;
	bool BackdropReady;
	int LastMirroredLoadProgress;
};

	A31VitaLoadingPresenter *g_active_loading_presenter = NULL;

	class A31VitaScopedLoadingPresenterCallback
	{
	public:
		explicit A31VitaScopedLoadingPresenterCallback(
			A31VitaLoadingPresenter &presenter) :
			Previous(g_active_loading_presenter)
		{
			g_active_loading_presenter = &presenter;
			A30_Vita_Log("A3.5 loading screen: Vita synchronous-load callback armed presenter=%p previous=%p\n",
				static_cast<void *>(&presenter), static_cast<void *>(Previous));
		}

		~A31VitaScopedLoadingPresenterCallback()
		{
			A30_Vita_Log("A3.5 loading screen: Vita synchronous-load callback disarmed presenter=%p restore=%p\n",
				static_cast<void *>(g_active_loading_presenter),
				static_cast<void *>(Previous));
			g_active_loading_presenter = Previous;
		}

	private:
		A31VitaLoadingPresenter *Previous;
	};

		A31StateSnapshot Make_Interactive_Capture_State(const A31InteractiveRenderTrace &trace,
			uint64_t frame, uint64_t monotonic_us, const char *reason)
		{
	A31StateSnapshot state = {};
	state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(state.milestone, sizeof(state.milestone), "%s", RENEGADE_BUILD_CANDIDATE_LABEL);
	snprintf(state.build_label, sizeof(state.build_label), "%s", RENEGADE_BUILD_DISPLAY_LABEL);
	snprintf(state.capture_overlay_label, sizeof(state.capture_overlay_label), "%s", RENEGADE_BUILD_CAPTURE_OVERLAY);
	snprintf(state.runtime_log_path, sizeof(state.runtime_log_path), "%s", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	snprintf(state.reason, sizeof(state.reason), "%s", reason);
	snprintf(state.phase, sizeof(state.phase), "%s", "interactive-player-owned");
	state.capture_monotonic_us = monotonic_us;
	state.capture_frame = frame;
	state.world.loaded = trace.scene_available;
	state.world.static_object_count = trace.static_object_count;
	state.world.dynamic_object_count = trace.dynamic_object_count;
	state.world.light_count = trace.static_light_count;
	state.world.vis_sector_count = trace.visibility_table_count;
	state.camera.present = trace.camera_available;
	state.camera.original_camera_class = trace.camera_available;
	state.camera.player_owned = trace.camera_available && trace.star_available;
	state.camera.position[0] = trace.camera_x;
	state.camera.position[1] = trace.camera_y;
	state.camera.position[2] = trace.camera_z;
	state.camera.near_clip = trace.near_clip;
	state.camera.far_clip = trace.far_clip;
	state.player.present = trace.star_available;
	state.player.object_id = trace.player_object_id;
	snprintf(state.player.definition, sizeof(state.player.definition), "%s",
		trace.player_definition);
	snprintf(state.player.type, sizeof(state.player.type), "%s", "SoldierGameObj");
	state.player.position[0] = trace.player_x;
	state.player.position[1] = trace.player_y;
	state.player.position[2] = trace.player_z;
	for (unsigned index = 0U; index < 4U; ++index) {
		state.player.orientation[index] = trace.player_orientation[index];
	}
	for (unsigned index = 0U; index < 3U; ++index) {
		state.player.velocity[index] = trace.player_velocity[index];
	}
	state.player.health = trace.player_health;
	state.player.physics_registered = trace.player_physics_registered;
	state.player.grounded = trace.player_grounded;
	Copy_Renderer_Statistics(state.renderer);
	if (state.renderer.draw_calls == 0U) {
		state.renderer.draw_calls = trace.mesh_submissions;
		state.renderer.mesh_submissions = trace.mesh_submissions;
		state.renderer.vertices = trace.vertex_submissions;
		state.renderer.triangles = trace.triangle_submissions;
		state.renderer.rejected_submissions = trace.rejected_submissions;
		state.renderer.unsupported_submissions = trace.unsupported_submissions;
	}
	state.game_update_count = frame;
	state.physics_update_count = frame;
	state.input_action_count = Renegade_Vita_Last_Input_Telemetry().sample_count;
	state.scripts_active = ScriptManager::Is_Provider_Active()
		&& ScriptManager::Get_Active_Script_Count() > 0;
	return state;
}

A31StateSnapshot Make_Loading_Capture_State(uint64_t monotonic_us, const char *reason)
{
	A31StateSnapshot state = {};
	state.schema_version = A31_CAPTURE_SCHEMA_VERSION;
	snprintf(state.milestone, sizeof(state.milestone), "%s", RENEGADE_BUILD_CANDIDATE_LABEL);
	snprintf(state.build_label, sizeof(state.build_label), "%s", RENEGADE_BUILD_DISPLAY_LABEL);
	snprintf(state.capture_overlay_label, sizeof(state.capture_overlay_label), "%s", RENEGADE_BUILD_CAPTURE_OVERLAY);
	snprintf(state.runtime_log_path, sizeof(state.runtime_log_path), "%s", RENEGADE_BUILD_RUNTIME_LOG_PATH);
	snprintf(state.reason, sizeof(state.reason), "%s", reason != NULL ? reason : "unknown");
	snprintf(state.phase, sizeof(state.phase), "%s", "original-loading-screen");
	state.capture_monotonic_us = monotonic_us;
	state.world.loaded = CombatManager::Get_Scene() != NULL;
	Copy_Renderer_Statistics(state.renderer);
	state.loading_visual_gate.active = true;
	state.loading_visual_gate.framebuffer_width = kCaptureWidth;
	state.loading_visual_gate.framebuffer_height = kCaptureHeight;
	state.loading_visual_gate.original_logical_width =
		static_cast<uint32_t>(kOriginalLoadingLogicalWidth);
	state.loading_visual_gate.original_logical_height =
		static_cast<uint32_t>(kOriginalLoadingLogicalHeight);
	state.loading_visual_gate.native_display_width = RenegadeVitaRenderer::DISPLAY_WIDTH;
	state.loading_visual_gate.native_display_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
	const A31NativePresentationRect rect =
		Build_Original_Loading_Presentation_Rect();
	state.loading_visual_gate.native_presentation_x = rect.x;
	state.loading_visual_gate.native_presentation_y = rect.y;
	state.loading_visual_gate.native_presentation_width = rect.width;
	state.loading_visual_gate.native_presentation_height = rect.height;
	state.loading_visual_gate.logical_to_native_fullscreen =
		rect.x == 0U && rect.y == 0U &&
		rect.width == RenegadeVitaRenderer::DISPLAY_WIDTH &&
		rect.height == RenegadeVitaRenderer::DISPLAY_HEIGHT;
	state.loading_visual_gate.aspect_preserved = true;
	state.loading_visual_gate.original_loading_screen_owner = true;
	state.loading_visual_gate.direct_vitagl_overlay_disabled = true;
	state.loading_visual_gate.loading_texture_v_flip_enabled = false;
	state.loading_visual_gate.gameplay_texture_v_unchanged = true;
	state.scripts_active = ScriptManager::Is_Provider_Active()
		&& ScriptManager::Get_Active_Script_Count() > 0;
	return state;
}

bool Apply_Original_Gameplay_Render_Resolution(const char *reason = "startup",
	bool log_state = true)
{
	RenegadeVitaRenderer::Reset_Native_Presentation_Rect();
	const bool applied = WW3D::Set_Device_Resolution(
		static_cast<int>(RenegadeVitaRenderer::DISPLAY_WIDTH),
		static_cast<int>(RenegadeVitaRenderer::DISPLAY_HEIGHT), -1, -1, false) == WW3D_ERROR_OK;
	int width = 0;
	int height = 0;
	int bits = 0;
	bool windowed = false;
	WW3D::Get_Device_Resolution(width, height, bits, windowed);
	if (log_state) {
		A30_Vita_Log("A3.5 HUD: native Vita gameplay/HUD render resolution reason=%s requested=%ux%u current=%dx%d bits=%d windowed=%d applied=%d\n",
			reason != NULL ? reason : "unknown",
			RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT, width, height, bits,
			windowed ? 1 : 0, applied ? 1 : 0);
	}
	return applied && width == static_cast<int>(RenegadeVitaRenderer::DISPLAY_WIDTH) &&
		height == static_cast<int>(RenegadeVitaRenderer::DISPLAY_HEIGHT);
}

bool Apply_Original_Loading_Render_Resolution_For_Prewarm(unsigned frame,
	bool log_state)
{
	const bool rect_applied = Apply_Original_Loading_Presentation_Rect(
		"prewarm_loading_overlay", log_state);
	const bool applied = WW3D::Set_Device_Resolution(
		static_cast<int>(kOriginalLoadingLogicalWidth),
		static_cast<int>(kOriginalLoadingLogicalHeight), -1, -1, false) == WW3D_ERROR_OK;
	int width = 0;
	int height = 0;
	int bits = 0;
	bool windowed = false;
	WW3D::Get_Device_Resolution(width, height, bits, windowed);
	if (log_state) {
		const A31NativePresentationRect rect =
			Build_Original_Loading_Presentation_Rect();
		A30_Vita_Log("A3.5 prewarm: loading presenter overlay resolution frame=%u requested=%.0fx%.0f current=%dx%d bits=%d windowed=%d native=%ux%u presentation=%u,%u %ux%u aspect_preserved=1 applied=%d rect_applied=%d\n",
			frame, kOriginalLoadingLogicalWidth,
			kOriginalLoadingLogicalHeight, width, height, bits,
			windowed ? 1 : 0, RenegadeVitaRenderer::DISPLAY_WIDTH,
			RenegadeVitaRenderer::DISPLAY_HEIGHT, rect.x, rect.y,
			rect.width, rect.height, applied ? 1 : 0,
			rect_applied ? 1 : 0);
	}
	return rect_applied && applied &&
		width == static_cast<int>(kOriginalLoadingLogicalWidth) &&
		height == static_cast<int>(kOriginalLoadingLogicalHeight);
}

void Warm_Original_M00_Presentation_Cache(A31VitaLoadingPresenter &loading_presenter)
{
	SaveLoadStatus::Set_Status_Text("Prewarming loading cache", 0);
	CombatManager::Set_Load_Progress(7);
	for (unsigned frame = 0U; frame < kLoadingPrewarmFrames; ++frame) {
		TextureLoader::Update(IS_SOLOPLAY ? NULL : &cNetwork::Update);
		A31_Interactive_Apply_Render_Capabilities();
		loading_presenter.Render_Original_Progress("prewarm_renderer_cache",
			true, 7);
		sceKernelDelayThread(16666);
	}
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	A30_Vita_Log("A3.5 prewarm: loading-screen-owned frames=%u textures=%llu uploads=%llu binds=%llu shader_cache=ux0:data/renegade/cache/vitagl-shader-cache state_changes=%llu backend_errors=%llu\n",
		kLoadingPrewarmFrames,
		static_cast<unsigned long long>(statistics.texture_resident),
		static_cast<unsigned long long>(statistics.texture_uploads),
		static_cast<unsigned long long>(statistics.texture_binds),
		static_cast<unsigned long long>(statistics.state_changes),
		static_cast<unsigned long long>(statistics.backend_errors));
}

bool Present_M00_Prewarm_Progress(A31VitaLoadingPresenter &presenter,
	float progress)
{
	if (!Apply_Original_Loading_Render_Resolution_For_Prewarm(0U, false)) return false;
	const RectClass previous = Render2DClass::Get_Screen_Resolution();
	Render2DClass::Set_Screen_Resolution(RectClass(0, 0,
		kOriginalLoadingLogicalWidth, kOriginalLoadingLogicalHeight));
	Commando_Set_Original_Loading_Progress(presenter.Peek_Screen(), progress);
	presenter.Render_Original_Progress("m00_prewarm", false, 7);
	Render2DClass::Set_Screen_Resolution(previous);
	return true;
}

bool Warm_Original_M00_Referenced_Textures(A31VitaLoadingPresenter &presenter)
{
	// Original DEP/model loading has populated this hash. Do not scan or retain
	// the entire retail archive. Snapshot references before any render callback
	// can create another font texture and mutate the manager's hash.
	const unsigned capacity = 2048U;
	TextureClass *pending[capacity];
	unsigned count = 0U;
	unsigned overflow = 0U;
	WW3DAssetManager *assets = WW3DAssetManager::Get_Instance();
	if (assets == NULL) return false;
	{
		HashTemplateIterator<StringClass, TextureClass *> it(assets->Texture_Hash());
		for (it.First(); !it.Is_Done(); it.Next()) {
			TextureClass *texture = it.Peek_Value();
			if (texture == NULL || texture->Is_Initialized() || texture->Num_Refs() <= 1) continue;
			if (count == capacity) { ++overflow; continue; }
			texture->Add_Ref();
			pending[count++] = texture;
		}
	}
	SaveLoadStatus::Set_Status_Text("Preparing M00 textures", 0);
	const uint64_t start_bytes = RenegadeVitaRenderer::Get_Statistics().texture_bytes_resident;
	const uint64_t additional_budget = 32ULL * 1024ULL * 1024ULL;
	unsigned prepared = 0U;
	bool presented = Present_M00_Prewarm_Progress(presenter, 0.90f);
	for (; presented && prepared < count; ++prepared) {
		const uint64_t resident = RenegadeVitaRenderer::Get_Statistics().texture_bytes_resident;
		// Soft incremental residency budget, checked between indivisible original
		// decodes. One texture can exceed it. Remaining textures stay lazy.
		if (resident >= start_bytes && resident - start_bytes >= additional_budget) break;
		pending[prepared]->Init();
		if ((prepared + 1U) % 8U == 0U || prepared + 1U == count) {
			presented = Present_M00_Prewarm_Progress(presenter,
				0.90f + 0.05f * float(prepared + 1U) / float(count));
		}
	}
	for (unsigned i = 0U; i < count; ++i) pending[i]->Release_Ref();
	A30_Vita_Log("A3.5 prewarm: original referenced textures attempted=%u deferred=%u soft_extra_budget_bytes=%llu whole_archive_scan=0 readiness_unassessed=1\n",
		prepared, count - prepared + overflow,
		static_cast<unsigned long long>(additional_budget));
	return presented;
}

bool Warm_Original_M00_Interactive_Presentation_Cache(WWAudioClass *audio,
	A31VitaLoadingPresenter &loading_presenter)
{
	if (!Warm_Original_M00_Referenced_Textures(loading_presenter)) return false;
	SaveLoadStatus::Set_Status_Text("Prewarming M00 scene cache", 0);
	CombatManager::Set_Load_Progress(7);
	const uint64_t prewarm_started_us = sceKernelGetProcessTimeWide();
	A30_Vita_Log("A3.5 prewarm: m00-scene start frames=%u input_enabled=0 simulation_frames=0 hidden_scene=1 status=%s\n",
		kM00ScenePrewarmFrames, "Prewarming M00 scene cache");

	A31InteractiveRenderTrace last_trace = {};
	bool rendered_scene = false;
	for (unsigned frame = 0U; frame < kM00ScenePrewarmFrames; ++frame) {
		TextureLoader::Update(IS_SOLOPLAY ? NULL : &cNetwork::Update);
		if (!Apply_Original_Gameplay_Render_Resolution("prewarm_m00_scene",
			frame == 0U)) {
			A30_Vita_Log("A3.5 prewarm: FAIL native gameplay resolution before scene frame=%u\n",
				frame);
			return false;
		}
		WW3D::Sync(static_cast<uint32_t>(
			(sceKernelGetProcessTimeWide() - prewarm_started_us) / 1000ULL));
		A31_Interactive_Apply_Render_Capabilities();
		// Finish original scene work without swapping an incomplete world/HUD.
		last_trace = A31_Interactive_Run_Render_Frame(false);
		rendered_scene =
			(last_trace.begin_render_completed &&
			 last_trace.combat_render_called &&
			 last_trace.end_render_completed &&
			 last_trace.post_render_completed);
		if (!rendered_scene || !Present_M00_Prewarm_Progress(loading_presenter,
			0.95f + 0.049f * float(frame + 1U) / float(kM00ScenePrewarmFrames))) {
			return false;
		}
		if (audio != NULL) audio->On_Frame_Update(0);
		if (frame == 0U || frame + 1U == kM00ScenePrewarmFrames ||
			((frame + 1U) % 15U) == 0U) {
			A30_Vita_Log("A3.5 prewarm: m00-scene frame=%u/%u scene=%d camera=%d star=%d begin/combat/end=%d/%d/%d meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
				frame + 1U, kM00ScenePrewarmFrames,
				last_trace.scene_available ? 1 : 0,
				last_trace.camera_available ? 1 : 0,
				last_trace.star_available ? 1 : 0,
				last_trace.begin_render_completed ? 1 : 0,
				last_trace.combat_render_called ? 1 : 0,
				last_trace.end_render_completed ? 1 : 0,
				static_cast<unsigned long long>(last_trace.mesh_submissions),
				static_cast<unsigned long long>(last_trace.vertex_submissions),
				static_cast<unsigned long long>(last_trace.triangle_submissions),
				static_cast<unsigned long long>(last_trace.rejected_submissions),
				static_cast<unsigned long long>(last_trace.unsupported_submissions));
		}
		sceKernelDelayThread(16667);
	}
	if (!Present_M00_Prewarm_Progress(loading_presenter, 1.0f)) return false;
	if (!Apply_Original_Gameplay_Render_Resolution("prewarm_m00_scene_complete",
		true)) {
		A30_Vita_Log("A3.5 prewarm: FAIL native gameplay resolution after scene prewarm\n");
		return false;
	}
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	A30_Vita_Log("A3.5 prewarm: m00-scene complete rendered=%d frames=%u elapsed_ms=%llu textures=%llu uploads=%llu binds=%llu state_changes=%llu shader_cache=ux0:data/renegade/cache/vitagl-shader-cache backend_errors=%llu hidden_scene=1 loading_presented=1\n",
		rendered_scene ? 1 : 0, kM00ScenePrewarmFrames,
		static_cast<unsigned long long>(
			(sceKernelGetProcessTimeWide() - prewarm_started_us) / 1000ULL),
		static_cast<unsigned long long>(statistics.texture_resident),
		static_cast<unsigned long long>(statistics.texture_uploads),
		static_cast<unsigned long long>(statistics.texture_binds),
		static_cast<unsigned long long>(statistics.state_changes),
		static_cast<unsigned long long>(statistics.backend_errors));
	return rendered_scene;
}

void Log_Interactive_Player_Effects(const A31InteractiveRenderTrace &trace,
	uint32_t frame, const char *reason)
{
	A30_Vita_Log("A3.5 effects: reason=%s frame=%u player=%u definition=%s state=%s position=(%.3f,%.3f,%.3f) velocity=(%.3f,%.3f,%.3f) health=%.3f physics=%d grounded=%d first_person=%d weapon=%s/%u rounds=%d/%d fired_total=%u weapon_state=%d triggered/fired=%d/%d action_count/active/busy=%u/%d/%d control action/reload=%d/%d input action/reload/use/camera/prev/next/zoom/objectives=%d/%d/%d/%d/%d/%d/%d/%d/%d physical square/triangle/select/circle/cross/l/r/front/dpad_udlr=%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d/%d key action/reload/camera/prev/next/zoom/objectives=%u/%u/%u/%u/%u/%u/%u/%u buttons=%08X\n",
		reason, frame, trace.player_object_id, trace.player_definition,
		trace.player_state, trace.player_x, trace.player_y, trace.player_z,
		trace.player_velocity[0], trace.player_velocity[1],
		trace.player_velocity[2], trace.player_health,
		trace.player_physics_registered ? 1 : 0,
		trace.player_grounded ? 1 : 0,
		trace.first_person_active ? 1 : 0,
		trace.weapon_present ? trace.weapon_definition : "none",
		trace.weapon_definition_id, trace.weapon_total_rounds,
		trace.weapon_clip_rounds, trace.weapon_total_rounds_fired,
		trace.weapon_state, trace.weapon_triggered ? 1 : 0,
		trace.weapon_fired_this_frame ? 1 : 0, trace.action_act_count,
		trace.action_active ? 1 : 0, trace.action_busy ? 1 : 0,
		trace.control_action_active ? 1 : 0,
		trace.control_reload_active ? 1 : 0,
		trace.input_action_active ? 1 : 0,
		trace.input_reload_active ? 1 : 0,
		trace.input_use_weapon_active ? 1 : 0,
			trace.input_first_person_toggle_active ? 1 : 0,
			trace.input_previous_weapon_active ? 1 : 0,
			trace.input_next_weapon_active ? 1 : 0,
			trace.input_zoom_in_active ? 1 : 0,
			trace.input_zoom_out_active ? 1 : 0,
			trace.input_objectives_toggle_active ? 1 : 0,
			trace.input_square_down ? 1 : 0,
		trace.input_triangle_down ? 1 : 0,
		trace.input_select_down ? 1 : 0,
		trace.input_circle_down ? 1 : 0,
		trace.input_cross_down ? 1 : 0,
		trace.input_left_shoulder_down ? 1 : 0,
		trace.input_right_shoulder_down ? 1 : 0,
		trace.input_front_touch_down ? 1 : 0,
		trace.input_dpad_up_down ? 1 : 0,
		trace.input_dpad_down_down ? 1 : 0,
		trace.input_dpad_left_down ? 1 : 0,
		trace.input_dpad_right_down ? 1 : 0,
		trace.input_action_key_state, trace.input_reload_key_state,
			trace.input_camera_toggle_key_state,
			trace.input_previous_weapon_key_state,
			trace.input_next_weapon_key_state,
			trace.input_zoom_in_key_state,
			trace.input_zoom_out_key_state,
			trace.input_objectives_toggle_key_state,
		trace.input_buttons);
}

#if !RENEGADE_VITA_M00_DEMO
struct A31NearbyActorSnapshot
{
	int id;
	char definition[64];
	char state[32];
	Vector3 position;
	Vector3 velocity;
	float distance2;
	float health;
	unsigned action_count;
	int action_active;
	int action_busy;
	bool vehicle;
	bool valid;
};

void Insert_Nearby_Actor(A31NearbyActorSnapshot *nearest, unsigned capacity,
	const A31NearbyActorSnapshot &candidate)
{
	if (!candidate.valid) return;
	for (unsigned index = 0U; index < capacity; ++index) {
		if (!nearest[index].valid || candidate.distance2 < nearest[index].distance2) {
			for (unsigned move = capacity - 1U; move > index; --move) {
				nearest[move] = nearest[move - 1U];
			}
			nearest[index] = candidate;
			return;
		}
	}
}

void Log_M13_Nearby_Actor_Snapshot(uint32_t frame)
{
	SoldierGameObj *star = CombatManager::Get_The_Star();
	if (star == NULL) return;
	Vector3 star_position;
	star->Get_Position(&star_position);
	A31NearbyActorSnapshot nearest[8] = {};
	unsigned soldier_count = 0U;
	unsigned vehicle_count = 0U;
	SList<SmartGameObj> *smart_objects = GameObjManager::Get_Smart_Game_Obj_List();
	for (SLNode<SmartGameObj> *node = smart_objects != NULL ? smart_objects->Head() : NULL;
		node != NULL; node = node->Next()) {
		SmartGameObj *smart = node->Data();
		if (smart == NULL || smart == star || smart->Is_Delete_Pending()) continue;
		SoldierGameObj *soldier = smart->As_SoldierGameObj();
		VehicleGameObj *vehicle = smart->As_VehicleGameObj();
		if (soldier == NULL && vehicle == NULL) continue;
		Vector3 position;
		Vector3 velocity;
		smart->Get_Position(&position);
		smart->Get_Velocity(velocity);
		const Vector3 delta = position - star_position;
		const float distance2 = delta.Length2();
		if (soldier != NULL) ++soldier_count;
		if (vehicle != NULL) ++vehicle_count;
		ActionClass *action = smart->Get_Action();
		DefenseObjectClass *defense = smart->Get_Defense_Object();
		A31NearbyActorSnapshot candidate = {};
		candidate.id = smart->Get_ID();
		candidate.position = position;
		candidate.velocity = velocity;
		candidate.distance2 = distance2;
		candidate.health = defense != NULL ? defense->Get_Health() : 0.0f;
		candidate.action_count = action != NULL ? action->Get_Act_Count() : 0U;
		candidate.action_active = action != NULL && action->Is_Active() ? 1 : 0;
		candidate.action_busy = action != NULL && action->Is_Busy() ? 1 : 0;
		candidate.vehicle = vehicle != NULL;
		candidate.valid = true;
		const char *definition = smart->Get_Definition().Get_Name();
		if (definition == NULL) definition = "unknown";
		snprintf(candidate.definition, sizeof(candidate.definition), "%s", definition);
		const char *state_name = soldier != NULL ? soldier->Get_State_Name() : "n/a";
		if (state_name == NULL) state_name = "unknown";
		snprintf(candidate.state, sizeof(candidate.state), "%s", state_name);
		Insert_Nearby_Actor(nearest, 8U, candidate);
	}
	A30_Vita_Log("A4 M13 actor snapshot: frame=%u star=(%.3f,%.3f,%.3f) soldiers=%u vehicles=%u cinematic_freeze=%d\n",
		frame, star_position.X, star_position.Y, star_position.Z,
		soldier_count, vehicle_count,
		GameObjManager::Is_Cinematic_Freeze_Active() ? 1 : 0);
	for (unsigned index = 0U; index < 8U; ++index) {
		if (!nearest[index].valid) continue;
		const char *kind = nearest[index].vehicle ? "vehicle" : "soldier";
		A30_Vita_Log("A4 M13 actor nearby: frame=%u rank=%u kind=%s id=%d def=%s pos=(%.3f,%.3f,%.3f) dist=%.3f vel=(%.3f,%.3f,%.3f) action=%u/%d/%d human_state=%s health=%.2f\n",
			frame, index, kind, nearest[index].id, nearest[index].definition,
			nearest[index].position.X, nearest[index].position.Y,
			nearest[index].position.Z,
			sqrtf(nearest[index].distance2), nearest[index].velocity.X,
			nearest[index].velocity.Y, nearest[index].velocity.Z,
			nearest[index].action_count, nearest[index].action_active,
			nearest[index].action_busy, nearest[index].state,
			nearest[index].health);
		}
	}
#endif

bool Mission_Progress_Changed(const A31MissionProgressState &left,
	const A31MissionProgressState &right)
{
	if (left.star_available != right.star_available ||
		left.player_control_enabled != right.player_control_enabled ||
		left.objective_count != right.objective_count ||
		left.active_conversation_count != right.active_conversation_count ||
		left.active_conversation_id != right.active_conversation_id ||
		left.active_conversation_state != right.active_conversation_state ||
		left.active_conversation_action_id != right.active_conversation_action_id ||
		left.active_conversation_current_remark !=
			right.active_conversation_current_remark ||
		left.active_conversation_remark_count !=
			right.active_conversation_remark_count ||
		left.active_conversation_text_id !=
			right.active_conversation_text_id ||
		left.active_conversation_sound_id !=
			right.active_conversation_sound_id ||
		left.active_conversation_string_available !=
			right.active_conversation_string_available ||
		left.active_conversation_sound_definition_available !=
			right.active_conversation_sound_definition_available ||
		left.active_conversation_speech_source !=
			right.active_conversation_speech_source ||
		left.active_conversation_speech_class_id !=
			right.active_conversation_speech_class_id ||
		left.active_conversation_speech_type !=
			right.active_conversation_speech_type ||
		left.active_conversation_speech_state !=
			right.active_conversation_speech_state ||
		left.active_conversation_speech_duration_ms !=
			right.active_conversation_speech_duration_ms ||
		left.active_conversation_speaker_available !=
			right.active_conversation_speaker_available ||
		left.active_conversation_speech_available !=
			right.active_conversation_speech_available ||
		left.active_conversation_speech_in_scene !=
			right.active_conversation_speech_in_scene ||
		left.active_conversation_speech_culled !=
			right.active_conversation_speech_culled ||
		left.active_conversation_speech_playing !=
			right.active_conversation_speech_playing ||
		strcmp(left.active_conversation_name,
			right.active_conversation_name) != 0) {
		return true;
	}
	for (unsigned index = 0U; index < 6U; ++index) {
		if (left.objective_status[index] != right.objective_status[index]) {
			return true;
		}
	}
	return false;
}

void Log_Mission_Progress(const A31MissionProgressState &progress,
	const A31InteractiveRenderTrace &trace, uint32_t frame)
{
	A30_Vita_Log("A3.5 mission progress: frame=%u star/control=%d/%d objectives=%u status_1_6=%d/%d/%d/%d/%d/%d active_conversations=%u active=%s id/state/action/remark/count=%d/%d/%d/%d/%d text/sound/str/def=%d/%d/%d/%d next_seconds=%.3f speech=speaker:%d src:%d present/scene/culled/playing=%d/%d/%d/%d class/type/state=%d/%d/%d dur/dropoff/dist=%u/%.3f/%.3f player=(%.3f,%.3f,%.3f)\n",
		frame, progress.star_available ? 1 : 0,
		progress.player_control_enabled ? 1 : 0, progress.objective_count,
		progress.objective_status[0], progress.objective_status[1],
		progress.objective_status[2], progress.objective_status[3],
		progress.objective_status[4], progress.objective_status[5],
		progress.active_conversation_count,
		progress.active_conversation_name[0] != '\0' ?
			progress.active_conversation_name : "none",
		progress.active_conversation_id, progress.active_conversation_state,
		progress.active_conversation_action_id,
		progress.active_conversation_current_remark,
		progress.active_conversation_remark_count,
		progress.active_conversation_text_id,
		progress.active_conversation_sound_id,
		progress.active_conversation_string_available ? 1 : 0,
		progress.active_conversation_sound_definition_available ? 1 : 0,
		progress.active_conversation_next_remark_seconds,
		progress.active_conversation_speaker_available ? 1 : 0,
		progress.active_conversation_speech_source,
		progress.active_conversation_speech_available ? 1 : 0,
		progress.active_conversation_speech_in_scene ? 1 : 0,
		progress.active_conversation_speech_culled ? 1 : 0,
		progress.active_conversation_speech_playing ? 1 : 0,
		progress.active_conversation_speech_class_id,
		progress.active_conversation_speech_type,
		progress.active_conversation_speech_state,
		progress.active_conversation_speech_duration_ms,
		progress.active_conversation_speech_dropoff_radius,
		progress.active_conversation_speech_listener_distance,
		trace.player_x, trace.player_y, trace.player_z);
}

A35CampaignFlightMissionState Make_Flight_Mission_State(
	const A31MissionProgressState &progress,
	const A31InteractiveRenderTrace &trace, uint32_t frame,
	const char *archive, const char *load_source)
{
	A35CampaignFlightMissionState state = {};
	state.frame = frame;
	state.archive = archive;
	state.load_source = load_source;
	state.star_available = progress.star_available;
	state.player_control_enabled = progress.player_control_enabled;
	state.objective_count = progress.objective_count;
	for (unsigned index = 0U; index < 6U; ++index) {
		state.objective_status[index] = progress.objective_status[index];
	}
	state.active_conversation_count = progress.active_conversation_count;
	state.active_conversation_name = progress.active_conversation_name;
	state.active_conversation_id = progress.active_conversation_id;
	state.active_conversation_state = progress.active_conversation_state;
	state.active_conversation_action_id =
		progress.active_conversation_action_id;
	state.active_conversation_current_remark =
		progress.active_conversation_current_remark;
	state.active_conversation_remark_count =
		progress.active_conversation_remark_count;
	state.active_conversation_text_id = progress.active_conversation_text_id;
	state.active_conversation_sound_id = progress.active_conversation_sound_id;
	state.active_conversation_string_available =
		progress.active_conversation_string_available;
	state.active_conversation_sound_definition_available =
		progress.active_conversation_sound_definition_available;
	state.active_conversation_next_remark_seconds =
		progress.active_conversation_next_remark_seconds;
	state.active_conversation_speaker_available =
		progress.active_conversation_speaker_available;
	state.active_conversation_speech_source =
		progress.active_conversation_speech_source;
	state.active_conversation_speech_available =
		progress.active_conversation_speech_available;
	state.active_conversation_speech_in_scene =
		progress.active_conversation_speech_in_scene;
	state.active_conversation_speech_culled =
		progress.active_conversation_speech_culled;
	state.active_conversation_speech_playing =
		progress.active_conversation_speech_playing;
	state.active_conversation_speech_class_id =
		progress.active_conversation_speech_class_id;
	state.active_conversation_speech_type =
		progress.active_conversation_speech_type;
	state.active_conversation_speech_state =
		progress.active_conversation_speech_state;
	state.active_conversation_speech_duration_ms =
		progress.active_conversation_speech_duration_ms;
	state.active_conversation_speech_dropoff_radius =
		progress.active_conversation_speech_dropoff_radius;
	state.active_conversation_speech_listener_distance =
		progress.active_conversation_speech_listener_distance;
	state.player_x = trace.player_x;
	state.player_y = trace.player_y;
	state.player_z = trace.player_z;
	return state;
}

A35CampaignFlightRenderState Make_Flight_Render_State(
	const A31InteractiveRenderTrace &trace)
{
	A35CampaignFlightRenderState state = {};
	state.scene_available = trace.scene_available;
	state.camera_available = trace.camera_available;
	state.star_available = trace.star_available;
	state.pre_render_completed = trace.pre_render_completed;
	state.begin_render_completed = trace.begin_render_completed;
	state.combat_render_called = trace.combat_render_called;
	state.message_window_render_called = trace.message_window_render_called;
	state.end_render_completed = trace.end_render_completed;
	state.post_render_completed = trace.post_render_completed;
	state.mesh_submissions = trace.mesh_submissions;
	state.vertex_submissions = trace.vertex_submissions;
	state.triangle_submissions = trace.triangle_submissions;
	state.rejected_submissions = trace.rejected_submissions;
	state.unsupported_submissions = trace.unsupported_submissions;
	state.camera_x = trace.camera_x;
	state.camera_y = trace.camera_y;
	state.camera_z = trace.camera_z;
	state.player_x = trace.player_x;
	state.player_y = trace.player_y;
	state.player_z = trace.player_z;
	return state;
}

A35CampaignFlightAudioState Make_Flight_Audio_State()
{
	RenegadeMilesRuntimeStats stats = {};
	Renegade_Miles_Get_Runtime_Stats(&stats);
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	A35CampaignFlightAudioState state = {};
	state.active_samples = stats.active_samples;
	state.active_streams = stats.active_streams;
	state.active_stream_position_ms = stats.active_stream_position_ms;
	state.active_stream_length_ms = stats.active_stream_length_ms;
	state.active_stream_cursor_frame = stats.active_stream_cursor_frame;
	state.active_stream_total_frames = stats.active_stream_total_frames;
	state.output_write_failures = stats.output_write_failures;
	state.stream_open_failures = stats.stream_open_failures;
	state.stream_start_silent = stats.stream_start_silent;
	state.mixed_peak_abs = stats.mixed_peak_abs;
	state.last_stream_name = stats.last_stream_name[0] != '\0' ?
		stats.last_stream_name : "none";
	state.last_error = stats.last_error[0] != '\0' ? stats.last_error : "none";
	state.dialog_volume = audio != NULL ? audio->Get_Dialog_Volume() : -1.0F;
	state.cinematic_volume =
		audio != NULL ? audio->Get_Cinematic_Volume() : -1.0F;
	return state;
}

void Copy_Flight_Memory(A31MemoryTelemetry &output)
{
	RenegadeVitaRenderer::BackendMemoryStatistics memory = {};
	if (!RenegadeVitaRenderer::Query_Backend_Memory(memory)) return;
	output.available = true;
	output.system_user_free = memory.system_user_free;
	output.system_cdram_free = memory.system_cdram_free;
	output.system_phycont_free = memory.system_phycont_free;
	output.vitagl_ram_total = memory.ram_total;
	output.vitagl_ram_free = memory.ram_free;
	output.vitagl_vram_total = memory.vram_total;
	output.vitagl_vram_free = memory.vram_free;
	output.vitagl_slow_total = memory.slow_total;
	output.vitagl_slow_free = memory.slow_free;
	output.vitagl_all_total = memory.all_total;
	output.vitagl_all_free = memory.all_free;
}

	A31CaptureBundleResult Capture_Interactive_Frame(const A31StateSnapshot &state,
		const A31FrameHistory &history, const uint8_t *pixels, const char *label)
	{
	A31CaptureBundleInput input = {};
	input.base_directory = RENEGADE_BUILD_CAPTURE_ROOT;
	input.bundle_label = label;
	input.resolved_rgba_bottom_up = pixels;
	input.framebuffer_width = kCaptureWidth;
	input.framebuffer_height = kCaptureHeight;
	input.write_annotated_screenshot = pixels != NULL;
	input.state = state;
	input.history = &history;
	return A31_Write_Capture_Bundle(input);
}

// Fixed-capacity timing aggregation keeps the physical candidate decisive
// without adding allocator churn or per-object logging to a release frame.
// All values are process-clock microseconds and therefore are available on a
// retail Vita without a development-only profiler.
struct InteractiveTiming
{
	uint32_t frame_us[kTimingWindowFrames];
	uint32_t sample_count;
	uint32_t sample_cursor;
	uint64_t total_frame_us;
	uint64_t total_sync_us;
	uint64_t total_simulation_us;
	uint64_t total_render_us;
	uint32_t total_frames;
	uint32_t minimum_frame_us;
	uint32_t slow_over_16_7ms_count;
	uint32_t slow_over_20_0ms_count;
	uint32_t slow_over_33_3ms_count;
	uint32_t slow_over_50_0ms_count;
	uint32_t worst_frame_us;
	uint32_t worst_sync_us;
	uint32_t worst_simulation_us;
	uint32_t worst_render_us;

	void Add(uint32_t sync_us, uint32_t simulation_us, uint32_t render_us,
		uint32_t frame_duration_us)
	{
		frame_us[sample_cursor] = frame_duration_us;
		sample_cursor = (sample_cursor + 1U) % kTimingWindowFrames;
		if (sample_count < kTimingWindowFrames) ++sample_count;
		total_sync_us += sync_us;
		total_simulation_us += simulation_us;
		total_render_us += render_us;
		total_frame_us += frame_duration_us;
		++total_frames;
		if (minimum_frame_us == 0U || frame_duration_us < minimum_frame_us) {
			minimum_frame_us = frame_duration_us;
		}
		if (frame_duration_us > 16667U) ++slow_over_16_7ms_count;
		if (frame_duration_us > 20000U) ++slow_over_20_0ms_count;
		if (frame_duration_us > 33333U) ++slow_over_33_3ms_count;
		if (frame_duration_us > 50000U) ++slow_over_50_0ms_count;
		if (frame_duration_us > worst_frame_us) worst_frame_us = frame_duration_us;
		if (sync_us > worst_sync_us) worst_sync_us = sync_us;
		if (simulation_us > worst_simulation_us) worst_simulation_us = simulation_us;
		if (render_us > worst_render_us) worst_render_us = render_us;
		#if !RENEGADE_VITA_M00_DEMO
		if (frame_duration_us >= 500000U) {
			A30_Vita_Log("A4 slow frame: frame=%u total_us=%u sync_us=%u simulation_us=%u render_us=%u\n",
				total_frames, frame_duration_us, sync_us, simulation_us, render_us);
		}
		#endif
	}

	uint32_t Percentile(unsigned percentile) const
	{
		if (sample_count == 0U) return 0U;
		uint32_t ordered[kTimingWindowFrames];
		for (uint32_t index = 0U; index < sample_count; ++index) {
			ordered[index] = frame_us[index];
		}
		for (uint32_t index = 1U; index < sample_count; ++index) {
			const uint32_t value = ordered[index];
			uint32_t cursor = index;
			while (cursor > 0U && ordered[cursor - 1U] > value) {
				ordered[cursor] = ordered[cursor - 1U];
				--cursor;
			}
			ordered[cursor] = value;
		}
		const uint32_t rank = (sample_count - 1U) * percentile / 100U;
		return ordered[rank];
	}

	uint32_t Average(uint64_t total) const
	{
		return total_frames == 0U ? 0U : static_cast<uint32_t>(total / total_frames);
	}

	uint32_t Average_FPS_Milli() const
	{
		return total_frame_us == 0U ? 0U : static_cast<uint32_t>(
			static_cast<uint64_t>(total_frames) * 1000000000ULL / total_frame_us);
	}
};

void Copy_Timing_Statistics(A31VitaInteractiveResult &result,
	const InteractiveTiming &timing)
{
	result.average_fps_milli = timing.Average_FPS_Milli();
	result.median_frame_us = timing.Percentile(50U);
	result.p95_frame_us = timing.Percentile(95U);
	result.worst_frame_us = timing.worst_frame_us;
	result.average_sync_us = timing.Average(timing.total_sync_us);
	result.average_simulation_us = timing.Average(timing.total_simulation_us);
	result.average_render_us = timing.Average(timing.total_render_us);
}

void Log_Campaign_Simulation_Stages()
{
#if !RENEGADE_VITA_M00_DEMO
	const A31SimulationStageTotals stages = A31_Interactive_Get_Simulation_Stage_Totals();
	if (stages.frames == 0U) return;
	const uint64_t drift_us = stages.real_us > stages.simulated_us ?
		stages.real_us - stages.simulated_us : 0U;
	A30_Vita_Log("A4 campaign pacing: frames=%u avg_us time/input/path/control/network/combat/other=%llu/%llu/%llu/%llu/%llu/%llu/%llu clock_real/sim/drift_ms=%llu/%llu/%llu\n",
		stages.frames,
		static_cast<unsigned long long>(stages.time_manager_us / stages.frames),
		static_cast<unsigned long long>(stages.input_us / stages.frames),
		static_cast<unsigned long long>(stages.path_us / stages.frames),
		static_cast<unsigned long long>(stages.control_us / stages.frames),
		static_cast<unsigned long long>(stages.network_us / stages.frames),
		static_cast<unsigned long long>(stages.combat_us / stages.frames),
		static_cast<unsigned long long>(stages.other_us / stages.frames),
		static_cast<unsigned long long>(stages.real_us / 1000U),
		static_cast<unsigned long long>(stages.simulated_us / 1000U),
		static_cast<unsigned long long>(drift_us / 1000U));
#endif
}

void Log_Timing_Statistics(const InteractiveTiming &timing,
	const RenegadeVitaRenderer::Statistics &renderer)
{
	if (timing.sample_count == 0U) return;
	A30_Vita_Log("A3.5 perf: frames=%u rolling_samples=%u avg_fps=%.3f frame_us min/p50/p95/p99/max=%u/%u/%u/%u/%u slow_over_16_7ms=%u slow_over_20ms=%u slow_over_33ms=%u slow_over_50ms=%u stage_us sync/sim/render=%u/%u/%u draws meshes=%u triangles=%u textures req/decode/upload/bind/missing=%llu/%llu/%llu/%llu/%llu loaded_dds/tga=%llu/%llu source/invalid/unsupported/decode/upload_fail/checker/checker_bind/invalid_bind=%llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu texture_sampler_updates=%llu texture_bind_skips=%llu texture_sampler_skips=%llu texture_stage_enable_skips=%llu texture_combiner_skips=%llu texture_unsupported_stages=%llu state_changes=%llu render_state_skips=%llu backend_errors=%llu\n",
		timing.total_frames, timing.sample_count,
		static_cast<double>(timing.Average_FPS_Milli()) / 1000.0,
		timing.minimum_frame_us, timing.Percentile(50U), timing.Percentile(95U),
		timing.Percentile(99U), timing.worst_frame_us,
		timing.slow_over_16_7ms_count, timing.slow_over_20_0ms_count,
		timing.slow_over_33_3ms_count, timing.slow_over_50_0ms_count,
		timing.Average(timing.total_sync_us), timing.Average(timing.total_simulation_us),
		timing.Average(timing.total_render_us), renderer.mesh_submissions,
		renderer.triangle_submissions,
		static_cast<unsigned long long>(renderer.texture_requests),
		static_cast<unsigned long long>(renderer.texture_decodes),
		static_cast<unsigned long long>(renderer.texture_uploads),
		static_cast<unsigned long long>(renderer.texture_binds),
		static_cast<unsigned long long>(renderer.texture_missing),
		static_cast<unsigned long long>(renderer.texture_dds_loads),
		static_cast<unsigned long long>(renderer.texture_tga_loads),
		static_cast<unsigned long long>(renderer.texture_source_missing),
		static_cast<unsigned long long>(renderer.texture_invalid_data),
		static_cast<unsigned long long>(renderer.texture_unsupported_formats),
		static_cast<unsigned long long>(renderer.texture_decode_failures),
		static_cast<unsigned long long>(renderer.texture_upload_failures),
		static_cast<unsigned long long>(renderer.texture_checkerboard_fallbacks),
		static_cast<unsigned long long>(renderer.texture_checkerboard_binds),
		static_cast<unsigned long long>(renderer.texture_invalid_binds),
		static_cast<unsigned long long>(renderer.texture_sampler_updates),
		static_cast<unsigned long long>(renderer.texture_bind_skips),
		static_cast<unsigned long long>(renderer.texture_sampler_skips),
		static_cast<unsigned long long>(renderer.texture_stage_enable_skips),
		static_cast<unsigned long long>(renderer.texture_combiner_skips),
		static_cast<unsigned long long>(renderer.texture_unsupported_stages),
		static_cast<unsigned long long>(renderer.state_changes),
		static_cast<unsigned long long>(renderer.render_state_skips),
		static_cast<unsigned long long>(renderer.backend_errors));
	A30_Vita_Log("A3.5 skin: submissions=%u deformed_vertices=%u deformation_failures=%u\n",
		renderer.skinned_mesh_submissions, renderer.deformed_skin_vertices,
		renderer.skin_deformation_failures);
	A30_Vita_Log("A3.5 indexed: submissions=%u triangles=%u state_applications=%llu rejected=%u\n",
		renderer.indexed_submissions, renderer.indexed_triangle_submissions,
		static_cast<unsigned long long>(renderer.indexed_state_applications),
		renderer.rejected_indexed_submissions);
}

void Log_Input_Telemetry()
{
	const RenegadeVitaInputTelemetry &input = Renegade_Vita_Last_Input_Telemetry();
	A30_Vita_Log("A3.5 input: samples=%llu raw lx/ly/rx/ry=%u/%u/%u/%u normalized=%.3f/%.3f/%.3f/%.3f logical=%ld/%ld/%ld/%ld mouse_delta=%ld/%ld dt=%.4f buttons=%08X physical square/triangle/select/circle/cross/l/r/front/dpad_udlr=%u/%u/%u/%u/%u/%u/%u/%u/%u/%u/%u/%u key action/reload/camera/prev/next/zoom/objectives=%u/%u/%u/%u/%u/%u/%u/%u route_mode/active/index/count/truncated=%u/%u/%u/%u/%u\n",
		static_cast<unsigned long long>(input.sample_count),
		static_cast<unsigned>(input.lx), static_cast<unsigned>(input.ly),
		static_cast<unsigned>(input.rx), static_cast<unsigned>(input.ry),
		static_cast<double>(input.normalized_lx),
		static_cast<double>(input.normalized_ly),
		static_cast<double>(input.normalized_rx),
		static_cast<double>(input.normalized_ry),
		static_cast<long>(input.logical_lx), static_cast<long>(input.logical_ly),
		static_cast<long>(input.logical_rx), static_cast<long>(input.logical_ry),
		static_cast<long>(input.mouse_dx), static_cast<long>(input.mouse_dy),
		static_cast<double>(input.frame_seconds), input.buttons,
		input.square_down, input.triangle_down, input.select_down,
		input.circle_down, input.cross_down, input.left_shoulder_down,
		input.right_shoulder_down, input.front_touch_down,
		input.dpad_up_down, input.dpad_down_down,
		input.dpad_left_down, input.dpad_right_down,
		input.action_key_state, input.reload_key_state,
		input.camera_toggle_key_state, input.previous_weapon_key_state,
		input.next_weapon_key_state, input.zoom_in_key_state,
		input.zoom_out_key_state, input.objectives_toggle_key_state,
		input.route_mode, input.route_gameplay_active,
		input.route_sample_index, input.route_sample_count,
		input.route_truncated);
	}

void Log_Audio_Runtime_Statistics(const char *reason, uint32_t frame)
{
	RenegadeMilesRuntimeStats stats = {};
	Renegade_Miles_Get_Runtime_Stats(&stats);
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	const float dialog_volume = audio != NULL ? audio->Get_Dialog_Volume() : -1.0F;
	const float cinematic_volume = audio != NULL ? audio->Get_Cinematic_Volume() : -1.0F;
	A30_Vita_Log("A3.5 audio: reason=%s frame=%u output_start=%u/%u/%u output_written/fail=%u/%u output_stream=buffers:%llu frames:%llu nonzero:%llu peak:%u last_output_stream=active/frames/nonzero/peak:%u/%u/%u/%u sample_file=%u/%u/%u sample_3d=%u/%u/%u stream=%u/%u/%u stream_start=%u/%u/%u/%u stream_bytes/frames=%llu/%llu stream_mix=buffers:%llu frames:%llu nonzero:%llu peak:%u last_stream_mix=active/frames/nonzero/peak:%u/%u/%u/%u last_stream=%s frames/fact/estimate/untrimmed/trimmed/rate/vol/pan=%u/%u/%u/%u/%u/%u/%u/%u starts=%u/%u/%u mix=buffers:%llu frames:%llu nonzero:%llu peak:%u allocated/active/streams=%u/%u/%u active_stream=pos/len/cursor/frames/loops/vol/pan=%u/%u/%u/%u/%u/%u/%u volumes_dialog/cinematic=%.3f/%.3f last_error=%s\n",
		reason != NULL ? reason : "unknown", frame,
		stats.output_start_attempts, stats.output_start_successes,
		stats.output_start_failures, stats.output_buffers_written,
		stats.output_write_failures,
		static_cast<unsigned long long>(stats.output_stream_buffers_written),
		static_cast<unsigned long long>(stats.output_stream_frames_written),
		static_cast<unsigned long long>(stats.output_stream_nonzero_buffers_written),
		stats.output_stream_peak_abs,
		stats.last_output_stream_active, stats.last_output_stream_frames,
		stats.last_output_stream_nonzero, stats.last_output_stream_peak_abs,
		stats.sample_file_load_attempts, stats.sample_file_load_successes,
		stats.sample_file_load_failures,
		stats.sample_3d_file_load_attempts,
		stats.sample_3d_file_load_successes,
		stats.sample_3d_file_load_failures,
		stats.stream_open_attempts, stats.stream_open_successes,
		stats.stream_open_failures,
		stats.stream_start_attempts, stats.stream_start_successes,
		stats.stream_start_silent, stats.stream_start_zero_volume,
		static_cast<unsigned long long>(stats.stream_bytes_read),
		static_cast<unsigned long long>(stats.stream_decoded_frames),
		static_cast<unsigned long long>(stats.stream_mixed_buffers),
		static_cast<unsigned long long>(stats.stream_mixed_frames),
		static_cast<unsigned long long>(stats.stream_mixed_nonzero_buffers),
		stats.stream_mixed_peak_abs,
		stats.last_stream_mix_active, stats.last_stream_mix_frames,
		stats.last_stream_mix_nonzero, stats.last_stream_mix_peak_abs,
		stats.last_stream_name[0] != '\0' ? stats.last_stream_name : "none",
		stats.last_stream_frames, stats.last_stream_fact_frames,
		stats.last_stream_estimated_frames,
		stats.last_stream_untrimmed_frames,
		stats.last_stream_trimmed_frames, stats.last_stream_rate,
		stats.last_stream_volume, stats.last_stream_pan,
		stats.sample_start_attempts, stats.sample_start_successes,
		stats.sample_start_silent,
		static_cast<unsigned long long>(stats.mixed_buffers),
		static_cast<unsigned long long>(stats.mixed_frames),
		static_cast<unsigned long long>(stats.mixed_nonzero_buffers),
		stats.mixed_peak_abs,
		stats.allocated_samples, stats.active_samples, stats.active_streams,
		stats.active_stream_position_ms, stats.active_stream_length_ms,
		stats.active_stream_cursor_frame, stats.active_stream_total_frames,
		stats.active_stream_loop_count, stats.active_stream_volume,
		stats.active_stream_pan,
		static_cast<double>(dialog_volume),
		static_cast<double>(cinematic_volume),
		stats.last_error[0] != '\0' ? stats.last_error : "none");
}

void Log_File_Factory_Statistics(uint32_t frame = 0U)
{
	const RenegadeFileFactoryStatistics statistics =
		Renegade_File_Factory_Get_Statistics();
	A30_Vita_Log("A3.6 resources: factory get/return=%u/%u resolve read/write/total/fail/cache_hit=%u/%u/%u/%u/%u open=%u fail=%u available=%u fail=%u create=%u fail=%u delete=%u fail=%u io read=%u/%uB write=%u/%uB; original MIX route unchanged\n",
		statistics.get_file_calls, statistics.return_file_calls,
		statistics.read_resolution_attempts, statistics.write_resolution_attempts,
		statistics.resolution_attempts, statistics.resolution_failures,
		statistics.resolution_cache_hits, statistics.open_attempts,
		statistics.open_failures, statistics.availability_attempts,
		statistics.availability_failures, statistics.create_attempts,
		statistics.create_failures, statistics.delete_attempts,
		statistics.delete_failures, statistics.read_calls, statistics.read_bytes,
		statistics.write_calls, statistics.write_bytes);
	A30_Vita_Log("A3.6 resources: confirmed-readonly-miss native probes skipped available/open=%u/%u logical_failures_retained=1 writable_and_forced_native=1\n",
		statistics.readonly_availability_skips, statistics.readonly_open_skips);
	A35_Campaign_Flight_Record_Resource_Snapshot(frame,
		statistics.open_attempts, statistics.open_failures,
		statistics.availability_attempts, statistics.availability_failures,
		statistics.read_calls, statistics.read_bytes, statistics.write_calls,
		statistics.write_bytes);
}

void Copy_Render_Statistics(A31VitaInteractiveResult &result)
{
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	result.mesh_submissions = statistics.mesh_submissions;
	result.vertex_submissions = statistics.vertex_submissions;
	result.triangle_submissions = statistics.triangle_submissions;
}

bool Is_Start_Pressed()
{
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
	// Start now reaches original menu-toggle input. Replay abort stays distinct.
	return Renegade_Vita_Input_Route_Replay_Exit_Requested();
#else
	SceCtrlData controller = {};
	return (sceCtrlPeekBufferPositive(0, &controller, 1) > 0 &&
			(controller.buttons & SCE_CTRL_START) != 0U) ||
		Renegade_Vita_Input_Route_Replay_Exit_Requested();
#endif
}

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
bool Run_Original_Gameplay_Pause_Menu(MenuGameModeClass2 &menu_mode,
	WWAudioClass *audio, uint64_t sync_origin, bool &pause_observed,
	bool &resume_observed, bool death_dialog = false)
{
	GameModeClass *combat_mode = GameModeManager::Find("Combat");
	if (combat_mode == NULL ||
		(death_dialog ? !combat_mode->Is_Suspended() : !combat_mode->Is_Active())) return true;
	A31VitaScopedFrontendRenderResolution frontend_render_resolution;
	if (!death_dialog) combat_mode->Suspend();
	pause_observed = true;
	A4_Frontend_Begin_Pause_Loop();
	Input::Menu_Enable(true);
	Input::Update();
	A4_Frontend_Prime_WWUI_Key_Transitions();
	menu_mode.Activate();
	if (!death_dialog) EVAEncyclopediaMenuClass::Display();
	A30_Vita_Log("A4 pause: original %s entered; Combat suspended; retained WWUI owner\n",
		death_dialog ? "death dialog" : "EVA");
	while (combat_mode->Is_Suspended() && !A4_Frontend_Exit_Requested() &&
		!A4_Frontend_Get_Trace().reload_requested &&
		!Renegade_Vita_Input_Route_Replay_Exit_Requested() &&
		(!death_dialog || DialogMgrClass::Get_Dialog_Count() > 0)) {
		WW3D::Sync(static_cast<uint32_t>(
			sceKernelGetProcessTimeWide() / 1000ULL - sync_origin));
		TimeManager::Update();
		Input::Update();
		A4_Frontend_Pump_WWUI_Key_Transitions();
		if (!combat_mode->Is_Suspended() || A4_Frontend_Exit_Requested() ||
			A4_Frontend_Get_Trace().reload_requested) break;
		// Do not run desktop Combat::Think or its focus-loss keyboard handler.
		cNetwork::Update();
		menu_mode.Think();
		GameModeManager::Safely_Deactivate();
		if (!menu_mode.Is_Active()) break;
		DialogMgrClass::On_Frame_Update();
		GameModeManager::Render();
		if (audio != NULL) audio->On_Frame_Update(0);
		sceKernelDelayThread(16667);
	}
	const bool exit_requested = A4_Frontend_Exit_Requested() ||
		Renegade_Vita_Input_Route_Replay_Exit_Requested();
	const bool reload_requested = A4_Frontend_Get_Trace().reload_requested;
	if (combat_mode->Is_Suspended() && !exit_requested && !reload_requested) {
		GameInitMgrClass::Continue_Game();
	}
	if (!menu_mode.Is_Inactive()) menu_mode.Deactivate();
	GameModeManager::Safely_Deactivate();
	Input::Menu_Enable(false);
	A4_Frontend_End_Menu_Loop();
	// Consume the menu button's gameplay edge before control generation resumes.
	Input::Update();
	A30_Vita_Log("A4 pause: original EVA left; resumed=%d exit=%d\n",
		combat_mode->Is_Active() ? 1 : 0, exit_requested ? 1 : 0);
	resume_observed = resume_observed || combat_mode->Is_Active();
	return !exit_requested && !reload_requested;
}

bool Try_Latch_Development_M00_Checkpoint()
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	const char *const request_path =
		"ux0:data/renegade/user/config/dev-checkpoint-launch-v1.txt";
	FILE *file = fopen(request_path, "rb");
	if (file == NULL) return false;
	char request[77];
	const size_t bytes = fread(request, 1U, sizeof(request), file);
	const bool read_failed = ferror(file) != 0;
	const bool close_failed = fclose(file) != 0;
	char source[96];
	if (read_failed || close_failed ||
		!A31DevelopmentCheckpoint::Parse(request, bytes, source, sizeof(source)) ||
		!A4_Frontend_Is_Tutorial_Source(source)) {
		A30_Vita_Log("A4 checkpoint: developer request rejected; original M00 save required\n");
		return false;
	}
	// Consume only validated one-shot launch metadata, never the original save.
	if (remove(request_path) != 0) {
		A30_Vita_Log("A4 checkpoint: developer request could not be consumed; launch refused\n");
		return false;
	}
	A4_Frontend_Latch_Start_Game(source, 0, 0UL);
	const bool latched = A4_Frontend_Get_Trace().tutorial_start_latched;
	A30_Vita_Log("A4 checkpoint: developer handoff latched=%d source=%s; original reload unassessed\n",
		latched ? 1 : 0, source);
	return latched;
#else
	return false;
#endif
}

#if !RENEGADE_VITA_M00_DEMO
bool Try_Latch_Development_Campaign_Mission()
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	const char *const request_path =
		"ux0:data/renegade/user/config/dev-mission-launch-v1.txt";
	FILE *file = fopen(request_path, "rb");
	if (file == NULL) return false;
	char request[32];
	const size_t bytes = fread(request, 1U, sizeof(request), file);
	const bool read_failed = ferror(file) != 0;
	const bool close_failed = fclose(file) != 0;
	char source[32];
	char archive[96];
	bool is_save = false;
	if (read_failed || close_failed ||
		!A31DevelopmentCheckpoint::Parse_Mission(request, bytes, source,
			sizeof(source)) ||
		!A4_Frontend_Resolve_Single_Player_Archive(source, archive,
			sizeof(archive), &is_save) || is_save) {
		A30_Vita_Log("A4 campaign diagnostic: invalid mission launch request\n");
		return false;
	}
	if (remove(request_path) != 0) {
		A30_Vita_Log("A4 campaign diagnostic: request could not be consumed\n");
		return false;
	}
	A4_Frontend_Latch_Start_Game(source, -1, 0UL);
	const bool latched = A4_Frontend_Get_Trace().tutorial_start_latched;
	A30_Vita_Log("A4 campaign diagnostic: standalone mission latched=%d source=%s; normal campaign state/transition not exercised\n",
		latched ? 1 : 0, source);
	return latched;
#else
	return false;
#endif
}

bool Try_Arm_Development_M13_Completion(const char *load_source)
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	if (load_source == NULL || stricmp(load_source, "M13.mix") != 0) return false;
	const char *const request_path =
		"ux0:data/renegade/user/config/dev-m13-completion-v1.txt";
	FILE *file = fopen(request_path, "rb");
	if (file == NULL) return false;
	char request[32];
	const size_t bytes = fread(request, 1U, sizeof(request), file);
	const bool read_failed = ferror(file) != 0;
	const bool close_failed = fclose(file) != 0;
	if (read_failed || close_failed ||
		!A31DevelopmentCheckpoint::Parse_M13_Completion(request, bytes)) {
		A30_Vita_Log("A4 campaign diagnostic: invalid M13 completion request\n");
		return false;
	}
	if (remove(request_path) != 0) {
		A30_Vita_Log("A4 campaign diagnostic: M13 completion request could not be consumed\n");
		return false;
	}
	A30_Vita_Log("A4 campaign diagnostic: M13 completion event armed for frame 120; objectives not exercised\n");
	return true;
#else
	(void)load_source;
	return false;
#endif
}

bool Try_Arm_Development_M13_Death(const char *load_source)
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	if (load_source == NULL || stricmp(load_source, "M13.mix") != 0) return false;
	const char *const request_path =
		"ux0:data/renegade/user/config/dev-m13-death-v1.txt";
	FILE *file = fopen(request_path, "rb");
	if (file == NULL) return false;
	char request[32];
	const size_t bytes = fread(request, 1U, sizeof(request), file);
	const bool read_failed = ferror(file) != 0;
	const bool close_failed = fclose(file) != 0;
	if (read_failed || close_failed ||
		!A31DevelopmentCheckpoint::Parse_M13_Death(request, bytes)) {
		A30_Vita_Log("A4 campaign diagnostic: invalid M13 death request\n");
		return false;
	}
	if (remove(request_path) != 0) {
		A30_Vita_Log("A4 campaign diagnostic: M13 death request could not be consumed\n");
		return false;
	}
	A30_Vita_Log("A4 campaign diagnostic: original lethal-damage event armed after intro camera release\n");
	return true;
#else
	(void)load_source;
	return false;
#endif
}

bool Try_Arm_Development_M13_A03_Field(const char *load_source)
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	if (load_source == NULL || stricmp(load_source, "M13.mix") != 0) return false;
	const char *const request_path =
		"ux0:data/renegade/user/config/dev-m13-a03-field-v1.txt";
	FILE *file = fopen(request_path, "rb");
	if (file == NULL) return false;
	char request[32];
	const size_t bytes = fread(request, 1U, sizeof(request), file);
	const bool read_failed = ferror(file) != 0;
	const bool close_failed = fclose(file) != 0;
	if (read_failed || close_failed ||
		!A31DevelopmentCheckpoint::Parse_M13_A03_Field(request, bytes)) {
		A30_Vita_Log("A4 campaign diagnostic: invalid M13 A03 field request\n");
		return false;
	}
	if (remove(request_path) != 0) {
		A30_Vita_Log("A4 campaign diagnostic: M13 A03 field request could not be consumed\n");
		return false;
	}
	A30_Vita_Log("A4 campaign diagnostic: M13 A03 field event setup armed; normal objectives not completed\n");
	return true;
#else
	(void)load_source;
	return false;
#endif
}

bool Apply_Development_M13_A03_Field_Setup(uint32_t frame)
{
#if RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
	SoldierGameObj *star = CombatManager::Get_The_Star();
	CCameraClass *camera = CombatManager::Get_Camera();
	if (star == NULL || camera == NULL) {
		A30_Vita_Log("A4 campaign diagnostic: M13 A03 field setup skipped; star/camera unavailable frame=%u star=%p camera=%p\n",
			frame, static_cast<void *>(star), static_cast<void *>(camera));
		return false;
	}

	enum {
		kControllerId = 1400041,
		kHumveeDropId = 1400042,
		kTroopDropId = 1400053,
		kTankDropId = 1400057,
		kHarvesterId = 1400001,
		kMinigunnerOneId = 1400150,
		kMinigunnerTwoId = 1400149,
		kStartZone = 401,
		kHarvesterDamageSelf = 413,
		kPlacedMinigunnerInnateEnable = 417
	};

	GameObject *controller = Find_Object(kControllerId);
	GameObject *humvee_drop = Find_Object(kHumveeDropId);
	GameObject *troop_drop = Find_Object(kTroopDropId);
	GameObject *tank_drop = Find_Object(kTankDropId);
	GameObject *harvester = Find_Object(kHarvesterId);
	GameObject *minigunner_one = Find_Object(kMinigunnerOneId);
	GameObject *minigunner_two = Find_Object(kMinigunnerTwoId);

	camera->Set_Host_Model(NULL);
	GameObjManager::Activate_Cinematic_Freeze(false);
	ScreenFadeManager::Enable_Letterbox(false, 0.0f);
	ScreenFadeManager::Set_Screen_Overlay_Opacity(0.0f, 0.0f);
	HUDClass::Enable(true);
	star->Control_Enable(true);
	CombatManager::Set_First_Person_Default(true);
	CombatManager::Set_First_Person(true);
	Set_Position(star, Vector3(-38.0f, -6.0f, 1.0f));
	Set_Facing(star, 25.0f);
	Select_Weapon(star, "Weapon_AutoRifle_Player");

	if (controller != NULL) {
		Send_Custom_Event(star, controller, kStartZone, 0, 0.0f);
	}
	if (humvee_drop != NULL) {
		Attach_Script(humvee_drop, "Test_Cinematic", "XG_A03_HumveeDrop_B.txt");
	}
	if (troop_drop != NULL) {
		Attach_Script(troop_drop, "Test_Cinematic", "MX0_A03_GDI_TroopDrop.txt");
	}
	if (tank_drop != NULL) {
		Attach_Script(tank_drop, "Test_Cinematic", "XG_A03_Tank_Drop.txt");
	}
	GameObject *orca = Create_Object("Invisible_Object", Vector3(0.0f, 0.0f, 0.0f));
	if (orca != NULL) {
		Attach_Script(orca, "Test_Cinematic", "X0F_Harvester.txt");
	}
	if (harvester != NULL) {
		Send_Custom_Event(star, harvester, kHarvesterDamageSelf, 4, 7.6f);
		Send_Custom_Event(star, harvester, kHarvesterDamageSelf, 3, 9.6f);
		Send_Custom_Event(star, harvester, kHarvesterDamageSelf, 3, 10.1f);
	}
	if (minigunner_one != NULL) {
		Send_Custom_Event(star, minigunner_one, kPlacedMinigunnerInnateEnable, 0, 0.0f);
	}
	if (minigunner_two != NULL) {
		Send_Custom_Event(star, minigunner_two, kPlacedMinigunnerInnateEnable, 0, 0.0f);
	}

	A30_Vita_Log("A4 campaign diagnostic: M13 A03 field setup applied frame=%u controller=%p humvee=%p troop=%p tank=%p harvester=%p minigunners=%p/%p orca=%p star=(%.3f,%.3f,%.3f)\n",
		frame, static_cast<void *>(controller), static_cast<void *>(humvee_drop),
		static_cast<void *>(troop_drop), static_cast<void *>(tank_drop),
		static_cast<void *>(harvester), static_cast<void *>(minigunner_one),
		static_cast<void *>(minigunner_two), static_cast<void *>(orca),
		-38.0f, -6.0f, 1.0f);
	return true;
#else
	(void)frame;
	return false;
#endif
}
#endif

bool Prepare_Timed_Decoration_Phys(int phys_def_id, bool animated,
	const char *label, const char *owner)
{
	if (phys_def_id == 0) return false;
	PhysDefClass *phys_def =
		(PhysDefClass *)DefinitionMgrClass::Find_Definition(phys_def_id);
	if (phys_def == NULL || !phys_def->Is_Type("TimedDecorationPhysDef")) {
		A30_Vita_Log("A4 M13 retained preparation: %s=%s phys_def=%p id=%d timed=0\n",
			owner, label != NULL ? label : "(id)",
			static_cast<void *>(phys_def), phys_def_id);
		return false;
	}
	TimedDecorationPhysClass *phys =
		(TimedDecorationPhysClass *)phys_def->Create();
	if (phys == NULL) {
		A30_Vita_Log("A4 M13 retained preparation: %s=%s phys_create=0 id=%d\n",
			owner, label != NULL ? label : "(id)", phys_def_id);
		return false;
	}
	bool model_ready = false;
	bool animation_ready = false;
	RenderObjClass *model = phys->Peek_Model();
	if (model != NULL) {
		model_ready = true;
		if (animated && model->Get_HTree() != NULL) {
			StringClass animation_name;
			animation_name.Format("%s.%s",
				model->Get_HTree()->Get_Name(),
				model->Get_HTree()->Get_Name());
			HAnimClass *animation =
				WW3DAssetManager::Get_Instance()->Get_HAnim(animation_name);
			if (animation != NULL) {
				animation_ready = true;
				animation->Release_Ref();
			}
		}
	}
	phys->Release_Ref();
	A30_Vita_Log("A4 M13 retained preparation: %s=%s phys_id=%d model=%d animation=%d\n",
		owner, label != NULL ? label : "(id)", phys_def_id,
		model_ready ? 1 : 0, animation_ready ? 1 : 0);
	return model_ready;
}

bool Prepare_Explosion_Definition(const char *name)
{
	ExplosionDefinitionClass *explosion =
		(ExplosionDefinitionClass *)DefinitionMgrClass::Find_Typed_Definition(
			name, CLASSID_DEF_EXPLOSION);
	if (explosion == NULL) {
		A30_Vita_Log("A4 M13 retained preparation: explosion=%s definition=0\n",
			name != NULL ? name : "(null)");
		return false;
	}
	const bool model_ready = Prepare_Timed_Decoration_Phys(explosion->PhysDefID,
		explosion->AnimatedExplosion, name, "explosion");
	A30_Vita_Log("A4 campaign effect preparation: explosion=%s model_ready=%d original_spawn_path=1\n",
		name != NULL ? name : "(null)", model_ready ? 1 : 0);
	return model_ready;
}

bool Run_Original_Frontend_Intro_And_Menu(MenuGameModeClass2 &menu_mode,
	MovieGameModeClass &movie_mode, WWAudioClass *audio, bool start_at_main_menu,
	const char *reload_source, const char *campaign_source)
{
	A31VitaScopedFrontendRenderResolution frontend_render_resolution;
	A4_Frontend_Reset_Trace();
	g_gameplay_pause_requested = false;
	A4_Frontend_Begin_Menu_Loop();
	RenegadeDialogMgrClass::Initialize();
	A30_Vita_Log("A4 frontend: original WWUI StyleMgr initialized under 800x600 frontend logical resolution menu_font=%p small_menu_font=%p\n",
		static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_MENU)),
		static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_SM_MENU)));
	if (!Validate_StyleMgr_Font_Glyphs("frontend-menu-stylemgr")) {
		RenegadeDialogMgrClass::Shutdown();
		A4_Frontend_End_Menu_Loop();
		return false;
	}
	Input::Menu_Enable(true);
	GameModeManager::Add(&menu_mode);
	GameModeManager::Add(&movie_mode);
	bool reload_valid = false;
	if (reload_source != NULL && reload_source[0] != '\0') {
#if RENEGADE_VITA_M00_DEMO
		reload_valid = A4_Frontend_Is_Tutorial_Source(reload_source);
#else
		char reload_archive[96];
		bool reload_is_save = false;
		reload_valid = A4_Frontend_Resolve_Single_Player_Archive(reload_source,
			reload_archive, sizeof(reload_archive), &reload_is_save) && reload_is_save;
		A30_Vita_Log("A4 campaign reload: source=%s archive=%s valid=%d\n",
			reload_source, reload_valid ? reload_archive : "none", reload_valid ? 1 : 0);
#endif
	}
	if (campaign_source != NULL && campaign_source[0] != '\0') {
		A4_Frontend_Latch_Start_Game(campaign_source, PLAYERTYPE_RENEGADE, 0);
		A30_Vita_Log("A4 campaign: restored original campaign next source=%s\n", campaign_source);
	} else if (reload_valid) {
		A4_Frontend_Latch_Start_Game(reload_source, -1, 0);
		A30_Vita_Log("A4 load: original save handoff after completed session teardown source=%s\n", reload_source);
	} else if (start_at_main_menu) {
		RenegadeDialogMgrClass::Goto_Location(RenegadeDialogMgrClass::LOC_MAIN_MENU);
		A30_Vita_Log("A3.5 demo ending: returned to original main menu; startup movies and developer checkpoint bypassed\n");
	}
#if !RENEGADE_VITA_M00_DEMO
	else if (Try_Latch_Development_Campaign_Mission()) {
		A30_Vita_Log("A4 campaign diagnostic: original frontend selected standalone mission\n");
	}
#endif
	else if (!Try_Latch_Development_M00_Checkpoint()) {
		movie_mode.Activate();
		movie_mode.Startup_Movies();
		A30_Vita_Log("A4 frontend: original MovieGameMode startup sequence entered; Bink provider owns decode or per-movie fail-closed skip\n");
	}
	// A valid developer save follows the same original frontend handoff below.

	unsigned frontend_frame = 0U;
	while (!A4_Frontend_Exit_Requested() &&
		!A4_Frontend_Get_Trace().tutorial_start_latched) {
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop frame entry\n");
		TimeManager::Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after TimeManager::Update\n");
		Input::Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after Input::Update\n");
		A4_Frontend_Pump_WWUI_Key_Transitions();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after WWUI key pump\n");
		GameModeManager::Think();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameModeManager::Think\n");
		GameInitMgrClass::Think();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameInitMgrClass::Think\n");
		DialogMgrClass::On_Frame_Update();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after DialogMgrClass::On_Frame_Update\n");
		GameModeManager::Render();
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after GameModeManager::Render\n");
		if (audio != NULL) audio->On_Frame_Update(0);
		if (frontend_frame == 0U) A30_Vita_Log("A4 frontend: first menu loop after WWAudio On_Frame_Update\n");
		++frontend_frame;
		sceKernelDelayThread(16667);
	}

	const A4FrontendTrace trace = A4_Frontend_Get_Trace();
#if RENEGADE_VITA_M00_DEMO
	const bool tutorial_selected = trace.tutorial_start_latched &&
		A4_Frontend_Is_Tutorial_Source(trace.tutorial_map);
#else
	char selected_archive[96];
	bool selected_save = false;
	const bool tutorial_selected = trace.tutorial_start_latched &&
		A4_Frontend_Resolve_Single_Player_Archive(trace.tutorial_map,
			selected_archive, sizeof(selected_archive), &selected_save);
#endif
	A30_Vita_Log("A4 frontend: menu loop exit latched=%d map=%s movie_play/skip=%u/%u last_movie=%s exit=%d code=%d\n",
		trace.tutorial_start_latched ? 1 : 0,
		trace.tutorial_map[0] != '\0' ? trace.tutorial_map : "none",
		trace.movie_play_requests, trace.movie_skip_requests,
		trace.last_movie[0] != '\0' ? trace.last_movie : "none",
		trace.exit_requested ? 1 : 0, trace.exit_code);

	if (!movie_mode.Is_Inactive()) {
		movie_mode.Deactivate();
	}
	if (!menu_mode.Is_Inactive()) {
		menu_mode.Deactivate();
	}
	GameModeManager::Safely_Deactivate();
#if RENEGADE_VITA_M00_DEMO
	GameModeManager::Remove(&movie_mode);
#else
	if (!tutorial_selected) GameModeManager::Remove(&movie_mode);
#endif
	if (tutorial_selected) {
		A30_Vita_Log("A4 frontend: retained original Menu mode through Combat handoff\n");
#if !RENEGADE_VITA_M00_DEMO
		A30_Vita_Log("A4 campaign: retained original Movie mode for campaign intermissions\n");
#endif
	} else {
		GameModeManager::Remove(&menu_mode);
	}
	if (!tutorial_selected) RenegadeDialogMgrClass::Shutdown();
	Input::Menu_Enable(false);
	A4_Frontend_End_Menu_Loop();
	return tutorial_selected;
}

#if !RENEGADE_VITA_M00_DEMO
bool Run_Original_Campaign_Intermission(WWAudioClass *audio,
	A31VitaInteractiveResult &result)
{
	A31VitaScopedFrontendRenderResolution presentation_resolution;
	A4_Frontend_Begin_Menu_Loop();
	Input::Menu_Enable(true);
	A30_Vita_Log("A4 campaign: dispatching observed mission success to original CampaignManager\n");
	CampaignManager::Continue();
	GameModeClass *combat = GameModeManager::Find("Combat");
	const bool original_end_game_consumed = combat != NULL && combat->Is_Inactive();
	A30_Vita_Log("A4 campaign: original Continue returned combat_inactive=%d score_active=%d\n",
		original_end_game_consumed ? 1 : 0,
		GameModeManager::Find("ScoreScreen") != NULL &&
			GameModeManager::Find("ScoreScreen")->Is_Active() ? 1 : 0);
	if (original_end_game_consumed) {
		unsigned intermission_frames = 0U;
		while (!A4_Frontend_Exit_Requested() &&
			!A4_Frontend_Get_Trace().tutorial_start_latched) {
			TimeManager::Update();
			Input::Update();
			A4_Frontend_Pump_WWUI_Key_Transitions();
			GameModeManager::Think();
			GameInitMgrClass::Think();
			DialogMgrClass::On_Frame_Update();
			GameModeManager::Render();
			if (audio != NULL) audio->On_Frame_Update(0);
			++intermission_frames;
			if (intermission_frames == 1U || intermission_frames % 600U == 0U) {
				A30_Vita_Log("A4 campaign: original intermission frame=%u score/movie=%d/%d\n",
					intermission_frames,
					GameModeManager::Find("ScoreScreen") != NULL &&
						GameModeManager::Find("ScoreScreen")->Is_Active() ? 1 : 0,
					GameModeManager::Find("Movie") != NULL &&
						GameModeManager::Find("Movie")->Is_Active() ? 1 : 0);
			}
			sceKernelDelayThread(16667);
		}
		const A4FrontendTrace trace = A4_Frontend_Get_Trace();
		if (trace.tutorial_start_latched) {
			char archive[96];
			bool is_save = false;
			if (A4_Frontend_Resolve_Single_Player_Archive(trace.tutorial_map,
				archive, sizeof(archive), &is_save) && !is_save) {
				RAMFileClass state_file(result.campaign_state,
					sizeof(result.campaign_state));
				if (state_file.Open(FileClass::WRITE)) {
					ChunkSaveClass state_writer(&state_file);
					const bool saved = CampaignManager::Save(state_writer);
					const int bytes = state_file.Size();
					state_file.Close();
					if (saved && bytes > 0 && bytes <=
						static_cast<int>(sizeof(result.campaign_state))) {
						memcpy(result.campaign_next_source, trace.tutorial_map,
							sizeof(result.campaign_next_source));
						result.campaign_state_size = static_cast<uint32_t>(bytes);
						result.campaign_handoff_completed = true;
						A30_Vita_Log("A4 campaign: original intermission latched next source=%s state_bytes=%u frames=%u\n",
							result.campaign_next_source, result.campaign_state_size,
							intermission_frames);
					}
				}
			}
		}
		result.frontend_exit_requested = A4_Frontend_Exit_Requested();
	}
	Input::Menu_Enable(false);
	A4_Frontend_End_Menu_Loop();
	return original_end_game_consumed;
}
#endif
#endif

} // namespace

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
void A31_Vita_Request_Gameplay_Pause(void)
{
	g_gameplay_pause_requested = true;
}
#endif

void A31_Vita_Render_Demo_Ending_Overlay(void)
{
#if RENEGADE_VITA_M00_DEMO
	if (g_demo_ending_presenter != NULL) g_demo_ending_presenter->Render();
#endif
}

void A31_Vita_Render_Original_Loading_Callback(const char *phase,
	int minimum_progress)
{
	static bool rendering = false;
	static uint64_t last_render_us = 0U;
	const uint64_t now_us = sceKernelGetProcessTimeWide();
	// Status callbacks may fire during asset creation inside a loading draw.
	// Keep the original renderer on this thread and never recurse into it.
	if (rendering) return;
	if (minimum_progress < 0 && now_us - last_render_us < 50000U) return;
	if (g_active_loading_presenter == NULL) {
		A30_Vita_Log("A3.5 loading screen: synchronous-load callback ignored phase=%s minimum=%d active=0\n",
			phase != NULL ? phase : "unknown", minimum_progress);
		return;
	}
	rendering = true;
	last_render_us = now_us;
	g_active_loading_presenter->Render_Original_Progress(phase, true,
		minimum_progress);
	rendering = false;
}

A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(
	int startup_screen_result, bool start_at_main_menu, const char *reload_source,
	const char *campaign_source, const uint8_t *campaign_state,
	uint32_t campaign_state_size)
{
	A31VitaInteractiveResult result = {};
	result.attempted = true;
	Renegade_File_Factory_Reset_Statistics();
	A31ScopedStartupStatusRepaint startup_status_repaint(startup_screen_result);

	Draw_Engine_Setup_Screen(startup_screen_result,
		"Opening original retail data factories",
		"pre-cache screen follows after MIX constructors are available");
	A30_Vita_Log("A3.5 startup: pre-cache visibility before MIX factory construction display=%d\n",
		startup_screen_result >= 0 ? 1 : 0);
	Renegade_Set_Find_Roots(kVitaRoots);
	RenegadeRootedFileFactoryClass root_factory(kVitaRoots);
	// Original Game_Init searches loose DATA_SUBDIRECTORY files before MIX
	// fallback. Keep explicit Data/user/cache paths at the root factory, and
	// add the missing loose Data read route without changing writable roots.
	RenegadePathRoots data_roots = kVitaRoots;
	data_roots.retail = "ux0:data/renegade/retail/Data";
	RenegadeRootedFileFactoryClass data_factory(data_roots);
	Draw_Engine_Setup_Screen(startup_screen_result,
		"Opening original Always2.dat archive",
		"large MIX constructor work is visible before pre-cache");
	MixFileFactoryClass always2_factory(kAlways2Archive, &root_factory);
	Draw_Engine_Setup_Screen(startup_screen_result,
		"Opening original always.dbs archive",
		"large MIX constructor work is visible before pre-cache");
	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	Draw_Engine_Setup_Screen(startup_screen_result,
		"Opening original Always.dat archive",
		"large MIX constructor work is visible before pre-cache");
	MixFileFactoryClass always_factory(kAlwaysArchive, &root_factory);
	Draw_Engine_Setup_Screen(startup_screen_result,
		"Opening original M00_Tutorial.mix archive",
		"large MIX constructor work is visible before pre-cache");
	MixFileFactoryClass m00_factory(kM00Archive, &root_factory);
#if !RENEGADE_VITA_M00_DEMO
	std::unique_ptr<MixFileFactoryClass> selected_mission_factory;
#endif
	Draw_Engine_Setup_Screen(startup_screen_result,
		"Preparing original FileFactoryList route",
		"visible pre-cache/pre-warm/pre-compute starts next");
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&data_factory, "Data");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	factory_list.Add_FileFactory(&m00_factory, "M00_Tutorial.mix");

	FileFactoryClass *previous_read_factory = _TheFileFactory;
	FileFactoryClass *previous_write_factory = _TheWritingFileFactory;
	_TheFileFactory = &factory_list;
	_TheWritingFileFactory = &root_factory;
	bool retail_probes_ok = true;
	const char *const retail_probe_names[] = {
		"stylemgr.ini", "WWAudio.ini", "hd_reticle.dds"
	};
	for (unsigned probe_index = 0U; probe_index < 3U; ++probe_index) {
		const char *name = retail_probe_names[probe_index];
		FileClass *file = factory_list.Get_File(name);
		const bool opened = file != NULL && file->Open(FileClass::READ);
		unsigned char header[4] = {};
		const int bytes = opened ? file->Read(header, sizeof(header)) : 0;
		const bool readable = bytes == 4 &&
			(probe_index != 2U || memcmp(header, "DDS ", 4) == 0);
		A30_Vita_Log("A3.5 retail lookup: logical=%s opened=%d bytes=%d readable=%d backing=%s original_file_factory=1\n",
			name, opened ? 1 : 0, bytes, readable ? 1 : 0,
			file != NULL ? file->File_Name() : "(none)");
		if (file != NULL) {
			if (opened) file->Close();
			factory_list.Return_File(file);
		}
		retail_probes_ok = retail_probes_ok && readable;
	}
	startup_status_repaint.Stop("visible-startup-precache-begin");
	const bool startup_precache_ok = retail_probes_ok && Run_Visible_Startup_Precache_Phase(
		startup_screen_result, factory_list, always2_factory,
		always_dbs_factory, always_factory, m00_factory);
	if (!startup_precache_ok) {
		Draw_Engine_Setup_Screen(startup_screen_result,
			"Startup pre-cache/pre-compute failed",
			"required retail archives or cache receipts were not ready");
		A30_Vita_Log("A3.5 prewarm: FAIL startup precache/precompute phase before frontend\n");
		result.render_error = true;
		Log_File_Factory_Statistics();
		_TheFileFactory = previous_read_factory;
		_TheWritingFileFactory = previous_write_factory;
		return result;
	}
	/* The Vita boundary has no Win32 console to own the screen.  The original
	** GameModeManager deliberately omits all presentation while that console is
	** exclusive, which otherwise leaves both the original WWUI main menu and
	** BINKMovie::Render() black despite their input/update owners running. */
	ConsoleBox.Set_Exclusive(false);
	A30_Vita_Log("A4 frontend: native presentation console_exclusive=%d; original WWUI and Bink rendering enabled\n",
		ConsoleBox.Is_Exclusive() ? 1 : 0);

	bool math_initialized = false;
	// Historical load evidence survives teardown; this flag owns pending cleanup.
	bool level_unload_pending = false;
	bool path_manager_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool translatedb_initialized = false;
	bool stylemgr_initialized = false;
		bool input_initialized = false;
			bool combat_initialized = false;
			bool campaign_initialized = false;
			bool mission_completion_observer_installed = false;
			bool text_display_initialized = false;
			bool text_window_scene_initialized = false;
		bool radar_initialized = false;
		bool session_initialized = false;
		bool original_end_game_consumed = false;
		bool single_player_transport_initialized = false;
		bool audio_teardown_completed = false;
			WW3DAssetManager *asset_manager = NULL;
			TextDebugDisplayHandlerClass text_display_handler;
			TextDisplayGameModeClass text_display_mode;
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
			CombatGameModeClass frontend_combat_mode;
			bool frontend_combat_mode_registered = false;
			MenuGameModeClass2 frontend_menu_mode;
			MovieGameModeClass frontend_movie_mode;
#if !RENEGADE_VITA_M00_DEMO
			ScoreScreenGameModeClass frontend_score_mode;
			bool frontend_score_mode_registered = false;
#endif
			bool frontend_menu_mode_registered_for_handoff = false;
			bool frontend_dialog_manager_retained = false;
#endif

	{
		/* Match original Commando ownership.  WWAudio must see the installed
		** retail/MIX chain and must be destroyed after the Combat session but
		** before asset, renderer, physics, and factory teardown. */
		A31AudioFileFactoryClass audio_file_factory(&factory_list);
		Draw_Engine_Setup_Screen(startup_screen_result,
			"Starting original audio provider",
			"WWAudio sees the installed retail/MIX file factory");
		A30_Vita_Log("A3.1 breadcrumb: application audio construction entry singleton=%p\n",
			static_cast<void *>(WWAudioClass::Get_Instance()));
		Renegade_Miles_Reset_Runtime_Stats();
		WWAudioClass application_audio(false);
		application_audio.Initialize();
		const bool options_loaded = RenegadeVitaUserSettings::Configure(
			"ux0:data/renegade/user/config/options-v1.cfg");
		RenegadeVitaOptions::Apply_Audio(application_audio);
		A30_Vita_Log("A3.5 options: user preferences load=%d sections=%u native_fixed_provider=1\n",
			options_loaded ? 1 : 0, RenegadeVitaUserSettings::State().record.value[0]);
		application_audio.Set_File_Factory(&audio_file_factory);
		WWAudioClass *audio = &application_audio;
		A30_Vita_Log("Alpha direct M00: original audio initialized over path-stripped Vita retail provider; entering original tutorial runtime\n");

		A30_Vita_Log("A3.1 interactive: begin original Commando/Combat session\n");
		A30_Vita_Log("A3.5 build profile: %s demo_only=%d durable_goal=complete_native_port\n",
			RENEGADE_BUILD_PROFILE, RENEGADE_VITA_M00_DEMO);
		const RenegadeCacheHealth m00_cache_health =
			Renegade_Inspect_Mix_Index_Cache(
				kVitaRoots, "M00_Tutorial.mix", kM00CacheIndex);
		A30_Vita_Log("A3.6 cache health: state=%s archive=%s entries=%u detail=%s path=%s; original MIX route unchanged\n",
			Renegade_Cache_Health_Name(m00_cache_health.state),
			m00_cache_health.archive, m00_cache_health.entry_count,
			m00_cache_health.detail, m00_cache_health.physical_path);
		if (WWAudioClass::Get_Instance() != audio || audio->Get_Sound_Scene() == NULL ||
			audio->Get_2D_Driver() == NULL || audio->Get_3D_Driver() == 0U) {
			A30_Vita_Log("A3.5 interactive: FAIL original WWAudio/Vita provider unavailable singleton=%p sound_scene=%p driver2d=%p driver3d=%lu\n",
				static_cast<void *>(audio),
				audio != NULL ? static_cast<void *>(audio->Get_Sound_Scene()) : NULL,
				audio != NULL ? static_cast<void *>(audio->Get_2D_Driver()) : NULL,
				audio != NULL ? static_cast<unsigned long>(audio->Get_3D_Driver()) : 0UL);
			Log_File_Factory_Statistics();
			_TheFileFactory = previous_read_factory;
			_TheWritingFileFactory = previous_write_factory;
			return result;
		}
		A30_Vita_Log("A3.1 breadcrumb: audio/session construction singleton=%p sound_scene=%p\n",
			static_cast<void *>(audio), static_cast<void *>(audio->Get_Sound_Scene()));
		Log_Audio_Runtime_Statistics("post-initialize", 0U);
		Draw_Engine_Setup_Screen(startup_screen_result,
			"Checking startup cache health",
			"M00/M01 index receipts and original archive route");
		{
		RenegadeCheatMgrClass cheat_manager;
		A31FrameHistory *capture_history = new (std::nothrow) A31FrameHistory;
		uint8_t *capture_pixels = NULL;
		uint32_t current_pause_input_frames = 0U;
		bool select_was_pressed = false;
		bool capture_policy_armed_logged = false;
		A31InteractiveRenderTrace last_render_trace = {};
		A31MissionProgressState last_mission_progress = {};
		bool mission_progress_recorded = false;
		bool tutorial_control_ready_observed = false;
		do {
			if (capture_history == NULL) {
				A30_Vita_Log("A3.5 capture: FAIL frame history heap allocation unavailable\n");
				break;
			}
			if (!always2_factory.Is_Valid() || !always_dbs_factory.Is_Valid() ||
				!always_factory.Is_Valid() || !m00_factory.Is_Valid()) {
				A30_Vita_Log("A3.1 interactive: retail factory chain FAIL\n");
				break;
			}

				Draw_Engine_Setup_Screen(startup_screen_result,
					"Initializing original math/path systems",
					"WWMath and PathMgr before original asset manager");
				WWMath::Init();
				math_initialized = true;
				/* Preserve original Commando ordering: the process-wide path-solver
				 * pool begins after WWMath and is destroyed after the asset manager. */
				PathMgrClass::Initialize();
				path_manager_initialized = true;
				Draw_Engine_Setup_Screen(startup_screen_result,
					"Constructing original WW3D asset manager",
					"load-on-demand and fog activation remain original-owned");
				asset_manager = new WW3DAssetManager;
				asset_manager->Set_WW3D_Load_On_Demand(true);
				asset_manager->Set_Activate_Fog_On_Load(true);
				Draw_Engine_Setup_Screen(startup_screen_result,
					"Starting vitaGL renderer",
					"visible status remains until vitaGL replaces the framebuffer");
				A30_Vita_Log("A3.5 startup: retaining bootstrap framebuffer through WW3D::Init to avoid black display handoff\n");
				ww3d_initialized = WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK;
				if (!ww3d_initialized) {
					A30_Vita_Log("A3.1 interactive: WW3D init FAIL\n");
					break;
				}
			if (!Apply_Original_Gameplay_Render_Resolution()) {
				A30_Vita_Log("A3.5 HUD: FAIL native gameplay/HUD render resolution unavailable\n");
				break;
			}
			A30_Vita_Log("A3.1 breadcrumb: WW3D asset manager ready\n");
			/* Font3D now follows the original FileFactory/Targa/Surface/texture
			 * chain. HUD promotion remains a separately tested A4 decision, so log
			 * the selected original Combat mode rather than claiming a capability
			 * is absent. */
			WWPhys::Init();
			wwphys_initialized = true;
			WWSaveLoad::Init();
			wwsaveload_initialized = true;
			if (!Load_Strings_Database_For_Loading_Screen()) {
				A30_Vita_Log("A3.5 loading screen: FAIL original strings database initialization\n");
				break;
			}
			translatedb_initialized = true;
			StyleMgrClass::Initialize_From_INI(kStyleManagerIni);
			stylemgr_initialized = true;
			if (StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT) == NULL ||
				StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT) == NULL) {
				A30_Vita_Log("A3.5 loading screen: FAIL original StyleMgr in-game fonts unavailable ini=%s normal=%p big=%p\n",
					kStyleManagerIni,
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
				break;
			}
			if (!Validate_StyleMgr_Font_Glyphs("initial-loading-stylemgr")) {
				break;
			}
				A30_Vita_Log("A3.5 loading screen: original StyleMgr initialized ini=%s normal_font=%p big_font=%p\n",
					kStyleManagerIni,
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
					static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
				Input::Init(true);
				Input::Load_Configuration("DEFAULT_INPUT.CFG");
				A31_Interactive_Configure_Vita_Controls();
				input_initialized = true;
					CampaignManager::Init();
					campaign_initialized = true;
					#if !RENEGADE_VITA_M00_DEMO
					if (campaign_source != NULL) {
						char archive[96];
						bool is_save = false;
						if (campaign_state == NULL || campaign_state_size == 0U ||
							campaign_state_size > 64U ||
							!A4_Frontend_Resolve_Single_Player_Archive(campaign_source,
								archive, sizeof(archive), &is_save) || is_save) {
							A30_Vita_Log("A4 campaign: rejected invalid session handoff source=%s bytes=%u\n",
								campaign_source, campaign_state_size);
							break;
						}
						uint8_t state_bytes[64];
						memcpy(state_bytes, campaign_state, campaign_state_size);
						RAMFileClass state_file(state_bytes, campaign_state_size);
						if (!state_file.Open(FileClass::READ)) break;
						ChunkLoadClass state_reader(&state_file);
						const bool loaded = CampaignManager::Load(state_reader);
						state_file.Close();
						if (!loaded) break;
						A30_Vita_Log("A4 campaign: restored original CampaignManager chunk bytes=%u source=%s\n",
							campaign_state_size, campaign_source);
					}
					#endif
					EncyclopediaMgrClass::Initialize();
					A30_Vita_Log("A3.5 EVA: original encyclopedia discovery tables initialized\n");
					A30_Vita_Log("A3.5 loading screen: original CampaignManager catalog initialized\n");
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
					if (GameModeManager::Find("Combat") == NULL) {
						GameModeManager::Add(&frontend_combat_mode);
						frontend_combat_mode_registered = true;
						A30_Vita_Log("A4 frontend: registered original CombatGameMode owner for menu/direct M00 route\n");
					}
#if !RENEGADE_VITA_M00_DEMO
					if (GameModeManager::Find("ScoreScreen") == NULL) {
						GameModeManager::Add(&frontend_score_mode);
						frontend_score_mode_registered = true;
					}
#endif
					{
						const bool frontend_tutorial_selected =
							Run_Original_Frontend_Intro_And_Menu(frontend_menu_mode,
								frontend_movie_mode, audio, start_at_main_menu, reload_source,
								campaign_source);
						frontend_menu_mode_registered_for_handoff =
							frontend_tutorial_selected &&
							GameModeManager::Find("Menu") == &frontend_menu_mode;
						frontend_dialog_manager_retained = frontend_tutorial_selected;
						stylemgr_initialized = frontend_tutorial_selected;
						if (!frontend_tutorial_selected) {
							result.clean_exit_requested = A4_Frontend_Exit_Requested();
							result.frontend_exit_requested = result.clean_exit_requested;
							A30_Vita_Log("A4 frontend: menu exited without supported tutorial selection; direct M00 route not entered\n");
							break;
						}
						A30_Vita_Log("A4 frontend: original WWUI/input/factories retained for M00 pause; StyleMgr remains live\n");
						if (StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT) == NULL ||
							StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT) == NULL) {
							A30_Vita_Log("A4 frontend: FAIL StyleMgr fonts unavailable after menu handoff normal=%p big=%p\n",
								static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_TXT)),
								static_cast<void *>(StyleMgrClass::Peek_Font(StyleMgrClass::FONT_INGAME_BIG_TXT)));
							break;
						}
						if (!Validate_StyleMgr_Font_Glyphs("post-menu-stylemgr")) {
							break;
						}
					}
#endif
				{
					A31VitaScopedGameplayHUDRender2DResolution text_display_resolution(
						"TextDisplayGameModeClass::Init");
					text_display_mode.Init();
				}
				text_display_initialized =
					TextDisplayGameModeClass::Get_Instance() == &text_display_mode;
				if (text_display_initialized) {
					DebugManager::Set_Display_Handler(&text_display_handler);
				}
				A30_Vita_Log("A3.5 text display: original TextDisplayGameMode init after final StyleMgr=%d handler=%d\n",
					text_display_initialized ? 1 : 0,
					text_display_initialized ? 1 : 0);
					cServerFps::Create_Instance();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP initialization entry\n");
			GameInitMgrClass::Initialize_SP();
			single_player_transport_initialized = cSinglePlayerData::Is_Single_Player();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP initialized=%d data=%p\n",
				single_player_transport_initialized ? 1 : 0,
				static_cast<void *>(PTheGameData));
			GameModeClass *combat_mode = GameModeManager::Find("Combat");
			if (!single_player_transport_initialized || PTheGameData == NULL || combat_mode == NULL) {
				A30_Vita_Log("A3.1 interactive: game-data/mode FAIL\n");
				break;
			}
			const A4FrontendTrace selected_source = A4_Frontend_Get_Trace();
			const char *load_source = selected_source.tutorial_start_latched
				? selected_source.tutorial_map : "M00_Tutorial.mix";
#if !RENEGADE_VITA_M00_DEMO
			char selected_archive[96];
			bool loading_checkpoint = false;
			if (!selected_source.tutorial_start_latched ||
				!A4_Frontend_Resolve_Single_Player_Archive(load_source,
					selected_archive, sizeof(selected_archive), &loading_checkpoint)) {
				A30_Vita_Log("A4 campaign: unsupported original single-player source=%s\n",
					load_source);
				break;
			}
			if (stricmp(selected_archive, "M00_Tutorial.mix") != 0) {
				char archive_path[112];
				snprintf(archive_path, sizeof(archive_path), "Data\\%s", selected_archive);
				selected_mission_factory.reset(new MixFileFactoryClass(archive_path,
					&root_factory));
				if (!selected_mission_factory->Is_Valid()) {
					A30_Vita_Log("A4 campaign: original mission MIX unavailable archive=%s\n",
						archive_path);
					break;
				}
				factory_list.Add_FileFactory(selected_mission_factory.get(),
					selected_archive);
			}
			A30_Vita_Log("A4 campaign: original selection source=%s archive=%s save=%d mix_valid=1\n",
				load_source, selected_archive, loading_checkpoint ? 1 : 0);
#endif
			combat_mode->Activate();
#if RENEGADE_VITA_M00_DEMO
			StringClass map_name("M00_Tutorial.mix", true);
#else
			StringClass map_name(load_source, true);
#endif
			The_Game()->Set_Map_Name(map_name);
			_Force_Link_Soldier();
			cNetwork::Onetime_Init();
			cNetwork::Init_Server();
			cNetwork::Init_Client();
			/*
			 * The original local single-player lane owns this connection.  Keep
			 * the invariant explicit at the platform boundary: a failure here is
			 * an initialization failure, not a reason to dereference a missing
			 * client connection while polling the original handshake.
			 */
			if (cNetwork::PClientConnection == NULL) {
				A30_Vita_Log("A3.1 interactive: original client connection unavailable\n");
				break;
			}
			session_initialized = true;
			CombatManager::Scene_Init();
			const bool render_hud = A31_Interactive_Render_HUD_Available();
			A30_Vita_Log("A3.1 breadcrumb: CombatManager::Init entry render_hud=%d\n",
				render_hud ? 1 : 0);
				{
					A31VitaScopedGameplayHUDRender2DResolution hud_init_resolution(
						"CombatManager::Init");
					CombatManager::Init(render_hud);
				}
			combat_initialized = true;
			A30_Vita_Log("A3.1 breadcrumb: Combat initialized render_hud=%d\n",
				render_hud ? 1 : 0);

			for (unsigned updates = 0U; updates < 120U &&
				!cNetwork::PClientConnection->Is_Established(); ++updates) {
				cNetwork::Update();
			}
			result.transport_established =
				cNetwork::PClientConnection->Is_Established();
			if (!result.transport_established) {
				A30_Vita_Log("A3.1 interactive: original local transport FAIL\n");
				break;
			}
			A30_Vita_Log("A3.1 breadcrumb: original local transport established\n");

			/* Match CombatGameModeClass::Load_Level at the existing misc-handler
			** seam. The adapter observes only callbacks generated by original
				** Combat/Mission00 code. */
				A31_Interactive_Begin_Mission_Completion_Observation();
				mission_completion_observer_installed = true;
				CombatManager::Set_Load_Progress(0);
				A31VitaScopedLoadingRenderResolution loading_render_resolution;
				A31VitaLoadingPresenter loading_presenter;
				if (!loading_presenter.Initialize(
#if RENEGADE_VITA_M00_DEMO
					load_source
#else
					selected_archive
#endif
				)) {
					result.render_error = true;
					A30_Vita_Log("A3.5 loading screen: FAIL original MenuBackDrop model unavailable\n");
					break;
				}
				A31VitaScopedLoadingPresenterCallback loading_callback(
					loading_presenter);
				loading_presenter.Render_Original_Progress("before_pre_load");
			CombatGameModeClass::Vita_Begin_Level_Load(
				loading_presenter.Peek_Screen(), true);
			loading_presenter.Render_Original_Progress("after_combatgmode_begin_load");
			/* The direct Vita runtime has a real WW3D presentation backend even
			** while the full HUD remains independently gated.  Passing false here
			** prevented the original BackgroundMgr from constructing SkyClass and
			** its Haze/Starfield/CloudLayer/SkyObject children, so no indexed sky
			** draw could ever reach the platform boundary.  Match the original
			** non-exclusive CombatGameMode load contract for world rendering. */
			CombatManager::Pre_Load_Level(true);
			loading_presenter.Render_Original_Progress("after_pre_load");
			A30_Vita_Log("A3.5 background: original render_available=1\n");
			NetworkObjectMgrClass::Set_Is_Level_Loading(true);
			TextureLoader::Suspend_Texture_Load();
			A30_Vita_Log("A3.5 texture loader: suspended during threaded M00 load\n");
#if !RENEGADE_VITA_M00_DEMO
			const uint64_t mission_preload_started_us = sceKernelGetProcessTimeWide();
			A30_Vita_Log("A4 campaign preload: original mission dependency list begin archive=%s\n",
				selected_archive);
			AssetDependencyManager::Load_Level_Assets(selected_archive);
			A30_Vita_Log("A4 campaign preload: original mission dependency list return archive=%s elapsed_ms=%llu\n",
				selected_archive,
				static_cast<unsigned long long>((sceKernelGetProcessTimeWide() -
					mission_preload_started_us) / 1000ULL));
			loading_presenter.Render_Original_Progress("mission_dependency_preload");
#endif
#if RENEGADE_VITA_M00_DEMO
			const bool tutorial_source_validated = A4_Frontend_Is_Tutorial_Source(load_source);
			if (!tutorial_source_validated) {
				A30_Vita_Log("A3.5 M00 load: rejected incompatible tutorial source\n");
				result.render_error = true;
				break;
			}
			const bool loading_checkpoint =
				stricmp(load_source, "M00_Tutorial.mix") != 0;
#endif
			A30_Vita_Log("A3.5 level load: original source=%s checkpoint=%d preload_always=0 campaign_mission_dep=%d\n",
				load_source, loading_checkpoint ? 1 : 0, !RENEGADE_VITA_M00_DEMO);
			CombatManager::Load_Level_Threaded(load_source, false);
			int last_load_progress = -1;
			int last_load_status_count = -1;
			StringClass last_load_sub_status;
			const uint64_t load_started_us = sceKernelGetProcessTimeWide();
			uint64_t last_load_log_us = load_started_us;
			while (!CombatManager::Is_Load_Level_Complete()) {
				/* Original ThreadClass performs the level work; this preserves the
				** established CombatManager polling contract. Report only progress
				** changes or one heartbeat per ten seconds. */
				const int load_progress = CombatManager::Get_Load_Progress();
				const uint64_t now_us = sceKernelGetProcessTimeWide();
				StringClass load_sub_status;
				SaveLoadStatus::Get_Status_Text(load_sub_status, 1);
				const int load_status_count = SaveLoadStatus::Get_Status_Count();
				loading_presenter.Render_Original_Progress("threaded_load");
				if (load_progress != last_load_progress ||
					load_status_count != last_load_status_count ||
					load_sub_status != static_cast<const char *>(last_load_sub_status) ||
					now_us - last_load_log_us >= 10000000ULL) {
					StringClass load_status;
					SaveLoadStatus::Get_Status_Text(load_status, 0);
					A30_Vita_Log("A3.1 M00 load: progress=%d status=%s sub_status=%s chunks=%d elapsed_ms=%llu\n",
						load_progress, static_cast<const char *>(load_status),
						static_cast<const char *>(load_sub_status), load_status_count,
						static_cast<unsigned long long>((now_us - load_started_us) / 1000ULL));
					last_load_progress = load_progress;
					last_load_status_count = load_status_count;
					last_load_sub_status = load_sub_status;
					last_load_log_us = now_us;
				}
				sceKernelDelayThread(50000);
			}
			loading_presenter.Render_Original_Progress("threaded_load_complete");
			A30_Vita_Log("A3.1 M00 load: threaded load complete progress=%d elapsed_ms=%llu\n",
				CombatManager::Get_Load_Progress(),
				static_cast<unsigned long long>(
					(sceKernelGetProcessTimeWide() - load_started_us) / 1000ULL));
			GenericDataSafeClass::Set_Preferred_Thread(GetCurrentThreadId());
			TextureLoader::Continue_Texture_Load();
			loading_presenter.Render_Original_Progress("texture_load_continued");
			A30_Vita_Log("A3.5 texture loader: continued before post-load processing\n");
			loading_presenter.Render_Original_Progress("post_load_processing");
			SaveLoadSystemClass::Post_Load_Processing(NULL);
				NetworkObjectMgrClass::Set_Is_Level_Loading(false);
				loading_presenter.Render_Original_Progress("post_load_level");
				CombatManager::Post_Load_Level();
				{
					A31VitaScopedGameplayHUDRender2DResolution hud_finalize_resolution(
						"CombatGameModeClass::Vita_Finalize_Loaded_Level");
					CombatGameModeClass::Vita_Finalize_Loaded_Level(
						loading_presenter.Peek_Screen(), true);
				}
				radar_initialized = true;
				A30_Vita_Log("A3.5 CombatGameMode: original post-load finalization complete radar_initialized=1\n");
				Warm_Original_M00_Presentation_Cache(loading_presenter);
				loading_presenter.Render_Original_Progress("level_ready", true, 7);
				if (capture_pixels == NULL) {
					capture_pixels = static_cast<uint8_t *>(malloc(kCaptureBytes));
				}
				const uint64_t loading_capture_us = sceKernelGetProcessTimeWide();
				const bool loading_readback = capture_pixels != NULL &&
					RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes, true);
				A31FrameTelemetry loading_capture_frame = {};
				loading_capture_frame.frame_index = 0U;
				loading_capture_frame.monotonic_us = loading_capture_us;
				Copy_Renderer_Statistics(loading_capture_frame.renderer);
				capture_history->Reset();
				capture_history->Push(loading_capture_frame);
				char loading_capture_label[96];
				snprintf(loading_capture_label, sizeof(loading_capture_label),
					"original-loading-screen-level-ready-t%llu",
					static_cast<unsigned long long>(loading_capture_us));
				const A31StateSnapshot loading_capture_state =
					Make_Loading_Capture_State(loading_capture_us, "level-ready");
				const A31CaptureBundleResult loading_capture = Capture_Interactive_Frame(
					loading_capture_state, *capture_history,
					loading_readback ? capture_pixels : NULL, loading_capture_label);
				A30_Vita_Log("Capture: %s candidate=%s phase=original-loading-screen reason=level-ready path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
					loading_capture.passed ? "PASS" : "FAIL",
					RENEGADE_BUILD_CANDIDATE_LABEL, loading_capture.bundle_path,
					loading_capture.screenshot_written ? 1 : 0,
					loading_capture.state_written ? 1 : 0,
					loading_capture.history_written ? 1 : 0,
					loading_capture.summary_written ? 1 : 0,
					loading_capture.first_error_code);
				capture_history->Reset();
				if (!Apply_Original_Gameplay_Render_Resolution(
					"post-loading-capture", true)) {
					result.render_error = true;
					A30_Vita_Log("A3.5 HUD: FAIL native gameplay/HUD resolution after loading capture\n");
					break;
				}
				A31_Interactive_Apply_Render_Capabilities();
				if (render_hud && CombatManager::Get_Background_Scene() != NULL) {
					TextWindowClass::Initialize(CombatManager::Get_Background_Scene());
					text_window_scene_initialized = true;
					A30_Vita_Log("A3.5 text window: original scene binding initialized for message/objective HUD scene=%p\n",
						static_cast<void *>(CombatManager::Get_Background_Scene()));
				}
				A30_Vita_Log("A3.5 scripts: provider_active=%d registered=%d active=%d\n",
					ScriptManager::Is_Provider_Active() ? 1 : 0,
					Get_Script_Count(), ScriptManager::Get_Active_Script_Count());
#if !RENEGADE_VITA_M00_DEMO
				if (stricmp(selected_archive, "M13.mix") == 0) {
					DefinitionClass *cinematic_definition =
						DefinitionMgrClass::Find_Named_Definition("Generic_Cinematic");
					StringClass cinematic_error;
					A30_Vita_Log("A4 M13 intro preset: named=%p class_id=%u valid=%d error=%s\n",
						static_cast<void *>(cinematic_definition),
						cinematic_definition != NULL ? cinematic_definition->Get_Class_ID() : 0U,
						cinematic_definition != NULL &&
							cinematic_definition->Is_Valid_Config(cinematic_error) ? 1 : 0,
						cinematic_error.Peek_Buffer());
				}
#endif
			A30_Vita_Log("A4 breadcrumb: original RadarManager initialized by CombatGameMode finalization for HUD=%d\n",
				render_hud ? 1 : 0);
			const A31InteractiveHUDState post_load_hud =
				A31_Interactive_Get_HUD_State();
			A30_Vita_Log("A3.1 breadcrumb: post-load HUD serialized=%d resources=%d effective=%d\n",
				post_load_hud.serialized_enabled ? 1 : 0,
				post_load_hud.render_resources_available ? 1 : 0,
				post_load_hud.effectively_displayable ? 1 : 0);
			result.level_loaded = CombatManager::Get_Scene() != NULL;
			level_unload_pending = result.level_loaded;
			if (!result.level_loaded) {
				A30_Vita_Log("A3.1 interactive: original level load FAIL\n");
				break;
			}
#if !RENEGADE_VITA_M00_DEMO
			if (stricmp(selected_archive, "M13.mix") == 0) {
				A35_Vita_Clear_Prepared_Render_Objs();
				struct A35PreparedMissionModel {
					const char *name;
					bool retain;
					unsigned count;
				};
				const A35PreparedMissionModel prepare_models[] = {
					{ "X00_AG_Explode", true, 2U },
					{ "X0F_AG_EFFECTS", true, 2U },
					{ "X0D_AG_Explode", true, 2U },
					{ "ag_rocketl", true, 4U },
					{ "ag_fiery_ex06", true, 2U },
					{ "ag_tank_exp01", false, 0U },
					{ "ag_tank_expld02", false, 0U },
					{ "ag_humvee_exp1", false, 0U },
					{ "ag_gdi_apc_exp1", false, 0U },
					{ "ag_nod_apc_exp1", false, 0U },
					{ "ag_ob_exp1", false, 0U },
					{ "V_NOD_LTANK", false, 0U },
					{ "V_NOD_MGUN", false, 0U },
					{ "V_NOD_ART", false, 0U },
					{ "B_SAMSITE", false, 0U },
					{ "BX_SAMSITE", false, 0U },
					{ "v_GDI_trnspt", false, 0U },
					{ "V_GDI_ORCA", false, 0U },
					{ "v_Nod_cplane", false, 0U },
					{ "V_GDI_A10", false, 0U },
					{ "X0Z_Effects", true, 2U },
					{ "X0Z_Orca01_Traj", true, 2U },
					{ "X0Z_Orca02_Traj", true, 2U },
					{ "X0D_A10_Traj", true, 1U },
					{ "L00.HND^FRONT", false, 0U },
					{ "L00.HND^ROOF", false, 0U },
					{ "L00.AR_04_03", false, 0U }
				};
				for (unsigned i = 0; i < sizeof(prepare_models) / sizeof(prepare_models[0]); ++i) {
					const uint64_t prepare_started_us = sceKernelGetProcessTimeWide();
					const bool prepared = A35_Vita_Prepare_Render_Obj(
						prepare_models[i].name,
						prepare_models[i].retain,
						prepare_models[i].count);
					A30_Vita_Log("A4 M13 %s preparation: model=%s created=%d retained=%d count=%u elapsed_us=%llu\n",
						prepare_models[i].retain ? "retained" : "warmed",
						prepare_models[i].name,
						prepared ? 1 : 0,
						prepare_models[i].retain ? 1 : 0,
						prepare_models[i].retain ? prepare_models[i].count : 0U,
						static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - prepare_started_us));
					loading_presenter.Render_Original_Progress("after_m13_model_prepare");
				}
				const char *const prepare_explosions[] = {
					"Vehicle Explosion 01",
					"Vehicle Explosion 02",
					"Vehicle Explosion Twiddler",
					"Explosion_Large_01",
					"Explosion_Large_02",
					"Explosion_Large_07",
					"Explosion_Small_04",
					"Explosion_SAM_Site",
					"Rocket Launcher Explosion Twiddler",
					"Ground Explosions Twiddler",
					"Air Explosions Twiddler",
					"Generic Ground 01"
				};
				for (unsigned i = 0; i < sizeof(prepare_explosions) / sizeof(prepare_explosions[0]); ++i) {
					const uint64_t prepare_started_us = sceKernelGetProcessTimeWide();
					const bool prepared = Prepare_Explosion_Definition(prepare_explosions[i]);
					A30_Vita_Log("A4 M13 retained preparation: explosion_result=%s prepared=%d elapsed_us=%llu\n",
						prepare_explosions[i], prepared ? 1 : 0,
						static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - prepare_started_us));
					loading_presenter.Render_Original_Progress("after_m13_explosion_prepare");
				}
			}
			if (stricmp(selected_archive, "M01.mix") == 0) {
				A35_Vita_Clear_Prepared_Render_Objs();
				struct A35PreparedMissionModel {
					const char *name;
					bool retain;
					unsigned count;
				};
				const A35PreparedMissionModel prepare_models[] = {
					{ "v_Nod_cplane", true, 1U },
					{ "v_GDI_trnspt", true, 1U },
					{ "v_Nod_trnspt", true, 1U },
					{ "v_nod_Apache", true, 1U },
					{ "Vxag_Nod_apache", true, 2U },
					{ "vxag_nod_heli", false, 2U },
					{ "V_GDI_ORCA", true, 1U },
					{ "V_GDI_A10", true, 1U },
					{ "V_AG_X1bGBoat", true, 1U },
					{ "V_AG_X1Borca", true, 1U },
					{ "VxAG_X1Borca", false, 2U },
					{ "X1B_AG_Missiles", true, 2U },
					{ "X1B_AG_xplosion", true, 2U },
					{ "X1C_AG_Missile", false, 2U },
					{ "X1c_AG_xplosion", false, 2U },
					{ "X1D_AG_Missile", true, 2U },
					{ "X1D_AG_xplosion", true, 2U },
					{ "X1D_Apache", true, 1U },
					{ "X1D_MTank", true, 1U },
					{ "X1d_Trajectory", true, 1U },
					{ "X1G_A-10_Traj", true, 1U },
					{ "X1G_AG_Effects", true, 2U },
					{ "XG_AG_AT_Misl", true, 2U },
					{ "XG_AG_AT_Xplsn", true, 2U },
					{ "XG_At_ApTraj", true, 1U },
					{ "XG_At_TrnTraj", true, 1U },
					{ "XG_EV5_Path", true, 1U },
					{ "XG_EV5_rope", true, 1U },
					{ "XG_EV5_troopBN", true, 1U },
					{ "XG_HD_Harness", true, 1U },
					{ "XG_HD_HTraj", true, 1U },
					{ "XG_TransprtBone", true, 1U }
				};
				for (unsigned i = 0; i < sizeof(prepare_models) / sizeof(prepare_models[0]); ++i) {
					const uint64_t prepare_started_us = sceKernelGetProcessTimeWide();
					const bool prepared = A35_Vita_Prepare_Render_Obj(
						prepare_models[i].name,
						prepare_models[i].retain,
						prepare_models[i].count);
					A30_Vita_Log("A4 M01 %s preparation: model=%s created=%d retained=%d count=%u elapsed_us=%llu\n",
						prepare_models[i].retain ? "retained" : "warmed",
						prepare_models[i].name,
						prepared ? 1 : 0,
						prepare_models[i].retain ? 1 : 0,
						prepare_models[i].retain ? prepare_models[i].count : 0U,
						static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - prepare_started_us));
					loading_presenter.Render_Original_Progress("after_m01_model_prepare");
				}
			}
#endif
			A30_Vita_Log("A3.1 breadcrumb: original M00 level loaded\n");

			WideStringClass local_player_name;
			local_player_name.Convert_From("Renegade");
			cPlayer *local_player = NULL;
			SoldierGameObj *restored_star = NULL;
			if (loading_checkpoint) {
				// WWSaveLoad restores the player/star links, but cPlayer::Save
				// does not persist IsActive. Admit only the original inactive
				// reuse path, never Create_Player's active-player rejoin branch.
				local_player = cPlayerManager::Find_Player(cNetwork::Get_My_Id());
				restored_star = CombatManager::Get_The_Star();
				A30_Vita_Log("A3.5 checkpoint: restored identity local_id=%d player=%p active_players=%d star=%p control_owner=%d\n",
					cNetwork::Get_My_Id(), static_cast<void *>(local_player),
					cPlayerManager::Count(), static_cast<void *>(restored_star),
					restored_star != NULL ? restored_star->Get_Control_Owner() : -1);
				if (local_player == NULL && cPlayerManager::Count() == 0 &&
					restored_star != NULL &&
					restored_star->Get_Control_Owner() == cNetwork::Get_My_Id()) {
					SLNode<cPlayer> *saved_node =
						cPlayerManager::Get_Player_Object_List()->Head();
					cPlayer *saved_player = saved_node != NULL &&
						saved_node->Next() == NULL ? saved_node->Data() : NULL;
					if (saved_player == NULL || saved_player->Is_Active() ||
						saved_player->Get_Id() != cNetwork::Get_My_Id() ||
						saved_player->Get_GameObj() != restored_star ||
						restored_star->Get_Player_Data() != saved_player ||
						cPlayerManager::Find_Inactive_Player(saved_player->Get_Name()) != saved_player) {
						A30_Vita_Log("A3.5 checkpoint: FAIL unique inactive saved-player binding; no session activation attempted\n");
						break;
					}
					local_player = cGod::Create_Player(cNetwork::Get_My_Id(),
						saved_player->Get_Name(), -1, 0);
					if (local_player != saved_player || cPlayerManager::Count() != 1 ||
						CombatManager::Get_The_Star() != restored_star ||
						saved_player->Get_GameObj() != restored_star ||
						restored_star->Get_Player_Data() != saved_player) {
						A30_Vita_Log("A3.5 checkpoint: FAIL original inactive-player reuse changed saved identity\n");
						break;
					}
					A30_Vita_Log("A3.5 checkpoint: original inactive player reactivated player=%p star=%p; saved objects preserved\n",
						static_cast<void *>(local_player), static_cast<void *>(restored_star));
				}
				if (local_player == NULL || cPlayerManager::Count() != 1 ||
					restored_star == NULL ||
					restored_star->Get_Control_Owner() != cNetwork::Get_My_Id()) {
					A30_Vita_Log("A3.5 checkpoint: FAIL restored local player/star identity; no respawn or rejoin attempted\n");
					break;
				}
			} else {
				local_player = cGod::Create_Player(cNetwork::Get_My_Id(),
					local_player_name, -1, 0);
			}
			result.player_created = local_player != NULL;
			result.player_registered = cPlayerManager::Count() == 1;
			A30_Vita_Log("A3.1 breadcrumb: original player created=%d registered=%d\n",
				result.player_created ? 1 : 0, result.player_registered ? 1 : 0);
			cGod::Think();
			if (loading_checkpoint &&
				(CombatManager::Get_The_Star() != restored_star ||
				 local_player->Get_GameObj() != restored_star)) {
				A30_Vita_Log("A3.5 checkpoint: FAIL original saved-player relink; refusing replacement state\n");
				break;
			}
			result.commando_created = CombatManager::Get_The_Star() != NULL;
			if (!result.player_created || !result.player_registered ||
				!result.commando_created) {
				A30_Vita_Log("A3.1 interactive: original player creation FAIL player=%d registered=%d commando=%d\n",
					result.player_created ? 1 : 0, result.player_registered ? 1 : 0,
					result.commando_created ? 1 : 0);
				break;
			}
			if (!loading_checkpoint) {
				CombatManager::Set_First_Person_Default(true);
				CombatManager::Set_First_Person(true);
				A30_Vita_Log("A3.5 camera: original first-person default restored for direct M00 route first_person=%d\n",
					CombatManager::Is_First_Person() ? 1 : 0);
			} else {
				A30_Vita_Log("A3.5 checkpoint: original player/star reused; saved camera preserved first_person=%d\n",
					CombatManager::Is_First_Person() ? 1 : 0);
			}
			bool presentation_ready = true;
#if !RENEGADE_VITA_M00_DEMO
			if (stricmp(selected_archive, "M00_Tutorial.mix") != 0) {
				A30_Vita_Log("A4 campaign: skip M00 eager presentation prewarm archive=%s; original textures remain lazy\n",
					selected_archive);
			} else
#endif
			{
				presentation_ready = Warm_Original_M00_Interactive_Presentation_Cache(
					audio, loading_presenter);
			}
			if (!presentation_ready) {
				result.render_error = true;
				A30_Vita_Log("A3.5 prewarm: FAIL M00 interactive scene warmup before first input\n");
				break;
			}

				result.initialized = true;
				A30_Vita_Log("A3.1 breadcrumb: original player/session ready; original mission completion or START exits\n");
				RenegadeVitaRenderer::Reset_Statistics();
				InteractiveTiming timing = {};
				if (capture_pixels == NULL) {
					capture_pixels = static_cast<uint8_t *>(malloc(kCaptureBytes));
				}
				const uint64_t sync_origin = sceKernelGetProcessTimeWide() / 1000ULL;
				A35_Campaign_Flight_Reset(RENEGADE_BUILD_CANDIDATE_LABEL,
					RENEGADE_BUILD_CAPTURE_ROOT, RENEGADE_BUILD_RUNTIME_LOG_PATH,
					selected_archive, load_source);
				A35_Campaign_Flight_Record_Event("lifecycle",
					"interactive_session_ready", result.frames, sync_origin,
					"original player/session ready; entering campaign frame loop");
#if !RENEGADE_VITA_M00_DEMO && RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
				bool diagnostic_m13_completion_pending =
					Try_Arm_Development_M13_Completion(load_source);
				bool diagnostic_m13_death_pending =
					Try_Arm_Development_M13_Death(load_source);
				bool diagnostic_m13_a03_field_pending =
					Try_Arm_Development_M13_A03_Field(load_source);
#endif
#if RENEGADE_VITA_M00_DEMO
				A31DemoEndingPresenter demo_ending;
#endif
			while (true) {
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
				if (g_gameplay_pause_requested) {
					g_gameplay_pause_requested = false;
#if RENEGADE_VITA_M00_DEMO
					if (!demo_ending.Timeline.Active())
#endif
					{
						if (!Run_Original_Gameplay_Pause_Menu(frontend_menu_mode, audio, sync_origin,
							result.pause_observed, result.resume_observed)) {
							const A4FrontendTrace request = A4_Frontend_Get_Trace();
							if (request.reload_requested) {
								memcpy(result.reload_source, request.tutorial_map, sizeof(result.reload_source));
								A30_Vita_Log("A4 load: pause request queued; original session cleanup required source=%s\n", result.reload_source);
							}
							result.start_exit_requested = true;
							break;
						}
					}
				}
#endif
				if (Is_Start_Pressed()) {
					result.start_exit_requested = true;
					break;
				}
				const uint64_t frame_begin = sceKernelGetProcessTimeWide();
				WW3D::Sync(static_cast<uint32_t>(
					sceKernelGetProcessTimeWide() / 1000ULL - sync_origin));
#if RENEGADE_VITA_M00_DEMO
				if (demo_ending.Timeline.Active()) {
					demo_ending.Timeline.Update(frame_begin);
					if (demo_ending.Timeline.GetPhase() == A31Demo::Ending::Done) {
						result.return_to_menu_requested = true;
						A30_Vita_Log("A3.5 demo ending: credits complete; original teardown then main menu\n");
						break;
					}
					bool ending_rendered;
					if (demo_ending.Timeline.GetPhase() == A31Demo::Ending::Fade) {
						const A31InteractiveRenderTrace ending_frame = A31_Interactive_Run_Render_Frame();
						ending_rendered = ending_frame.end_render_completed && ending_frame.post_render_completed;
					} else {
						A31VitaScopedGameplayHUDRender2DResolution ending_resolution("demo-credits", false);
						ending_rendered = demo_ending.Render_Credit_Frame();
					}
					if (!ending_rendered) {
						result.render_error = true;
						break;
					}
					audio->On_Frame_Update(0);
					sceKernelDelayThread(16667);
					continue;
				}
#endif
				const uint64_t simulation_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original input frame\n");
				}
				const bool was_suspended = combat_mode->Is_Suspended();
				A31_Interactive_Run_Simulation_Frame();
#if !RENEGADE_VITA_M00_DEMO && RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
				if (diagnostic_m13_a03_field_pending && result.frames >= 180U) {
					diagnostic_m13_a03_field_pending = false;
					if (!Apply_Development_M13_A03_Field_Setup(result.frames)) {
						A30_Vita_Log("A4 campaign diagnostic: M13 A03 field setup failed frame=%u\n",
							result.frames);
					}
				}
				if (diagnostic_m13_death_pending && result.frames >= 120U &&
					CombatManager::Get_Camera() != NULL &&
					!CombatManager::Get_Camera()->Is_Using_Host_Model()) {
					diagnostic_m13_death_pending = false;
					SoldierGameObj *star = CombatManager::Get_The_Star();
					if (star != NULL && !star->Is_Dead() && !star->Is_Destroyed()) {
						const float health_before = star->Get_Defense_Object()->Get_Health();
						star->Apply_Damage_Extended(OffenseObjectClass(100000.0f),
							1.0f, Vector3(0.0f, 0.0f, 1.0f), NULL);
						A30_Vita_Log("A4 campaign diagnostic: original lethal damage applied frame=%u health_before=%.2f health_after=%.2f dead=%d\n",
							result.frames, health_before,
							star->Get_Defense_Object()->Get_Health(), star->Is_Dead() ? 1 : 0);
					} else {
						A30_Vita_Log("A4 campaign diagnostic: lethal damage skipped; original star unavailable\n");
					}
				}
#endif
#if !RENEGADE_VITA_M00_DEMO
				if (stricmp(selected_archive, "M13.mix") == 0 &&
					(result.frames == 0U || result.frames == 120U ||
					 result.frames == 1800U || result.frames == 4200U)) {
					const A31InteractiveHUDState intro_hud =
						A31_Interactive_Get_HUD_State();
					CCameraClass *intro_camera = CombatManager::Get_Camera();
					A30_Vita_Log("A4 M13 intro: frame=%u camera_host=%d hud_enabled=%d hud_effective=%d star=%p\n",
						result.frames,
						intro_camera != NULL && intro_camera->Is_Using_Host_Model() ? 1 : 0,
						intro_hud.serialized_enabled ? 1 : 0,
						intro_hud.effectively_displayable ? 1 : 0,
						static_cast<void *>(CombatManager::Get_The_Star()));
				}
#endif
#if !RENEGADE_VITA_M00_DEMO && RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
				if (diagnostic_m13_completion_pending && result.frames >= 120U) {
					diagnostic_m13_completion_pending = false;
					A30_Vita_Log("A4 campaign diagnostic: dispatch original CombatManager mission success at frame=%u; objectives bypassed only in diagnostic build\n",
						result.frames);
					CombatManager::Mission_Complete(true);
				}
#endif
				const A31MissionCompletionState mission_state =
					A31_Interactive_Get_Mission_Completion_State();
				const bool first_star_death = mission_state.star_killed_observed &&
					!result.star_killed_observed;
				result.star_killed_observed = mission_state.star_killed_observed;
				if (mission_state.completion_observed &&
					!result.mission_completion_observed) {
					result.mission_completion_observed = true;
					result.mission_succeeded = mission_state.mission_succeeded;
					A30_Vita_Log("A3.5 mission completion: original Combat event observed success=%d frame=%u\n",
						result.mission_succeeded ? 1 : 0, result.frames);
#if RENEGADE_VITA_M00_DEMO
					if (result.mission_succeeded && tutorial_source_validated) {
						Renegade_Vita_Input_Route_Set_Gameplay_Active(false, result.frames);
						demo_ending.Timeline.Start(sceKernelGetProcessTimeWide());
						A30_Vita_Log("A3.5 demo ending: original M00 success; fade begin; campaign advance disabled\n");
						continue;
					}
					if (result.mission_succeeded) {
						A30_Vita_Log("A3.5 demo ending: rejected non-M00 completion source=%s\n", load_source);
					}
#else
					if (result.mission_succeeded) {
						original_end_game_consumed =
							Run_Original_Campaign_Intermission(audio, result);
						if (original_end_game_consumed) {
							level_unload_pending = false;
							radar_initialized = false;
						}
						break;
					}
#endif
#if RENEGADE_VITA_M00_DEMO
					break;
#endif
				}
				if (first_star_death) {
					A30_Vita_Log("A3.5 mission completion: original Combat star-killed event observed frame=%u\n",
						result.frames);
#if RENEGADE_VITA_M00_DEMO
					break;
#endif
				}
				const bool is_suspended = combat_mode->Is_Suspended();
				if (!was_suspended && is_suspended) {
					result.pause_observed = true;
					current_pause_input_frames = 0U;
					A30_Vita_Log("A3.5 pause: original Combat suspended frame=%u player=(%.3f,%.3f,%.3f)\n",
						result.frames, last_render_trace.player_x,
						last_render_trace.player_y, last_render_trace.player_z);
				}
				if (was_suspended && !is_suspended) {
					result.resume_observed = true;
					A30_Vita_Log("A3.5 pause: original Combat resumed frame=%u paused_input_frames=%u player=(%.3f,%.3f,%.3f)\n",
						result.frames, current_pause_input_frames,
						last_render_trace.player_x, last_render_trace.player_y,
						last_render_trace.player_z);
					current_pause_input_frames = 0U;
				}
				if (is_suspended) {
#if !RENEGADE_VITA_M00_DEMO && defined(RENEGADE_A4_ORIGINAL_FRONTEND)
					if ((result.star_killed_observed ||
						(result.mission_completion_observed && !result.mission_succeeded)) &&
						DialogMgrClass::Get_Dialog_Count() > 0) {
						A30_Vita_Log("A4 death: original popup active dialogs=%d; entering WWUI pump\n",
							DialogMgrClass::Get_Dialog_Count());
						if (!Run_Original_Gameplay_Pause_Menu(frontend_menu_mode, audio,
							sync_origin, result.pause_observed, result.resume_observed, true)) {
							A30_Vita_Log("A4 death: original popup requested exit/reload\n");
							result.start_exit_requested = true;
							break;
						}
						if (!combat_mode->Is_Active()) {
							A30_Vita_Log("A4 death: original popup closed without active Combat; ending session\n");
							break;
						}
						A31_Interactive_Begin_Mission_Completion_Observation();
						result.mission_completion_observed = false;
						result.mission_succeeded = false;
						result.star_killed_observed = false;
						A30_Vita_Log("A4 death: original restart resumed Combat; mission callback observation reset\n");
						continue;
					}
#endif
					++current_pause_input_frames;
					++result.paused_input_frames;
					/* Preserve the last original Combat frame while the absent desktop
					** menu presenter is deferred. Input, TimeManager, and the local
					** network lane were serviced above, so resume has no accumulated
					** simulation delta. */
					audio->On_Frame_Update(0);
					sceKernelDelayThread(16667);
					continue;
				}
				const uint64_t render_begin = sceKernelGetProcessTimeWide();
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: first original Combat update\n");
				}

				const A31InteractiveRenderTrace render_trace =
					A31_Interactive_Run_Render_Frame();
				/* Preserve original mainloop ownership and ordering: WWAudio advances
				** once after the game render. This services playback completion,
				** looping, and original sound-ended events; conversation remark timing
				** remains owned by ActiveConversationClass and TimeManager. */
				audio->On_Frame_Update(0);
				last_render_trace = render_trace;
				const A31MissionProgressState mission_progress =
					A31_Interactive_Get_Mission_Progress_State();
				if (!mission_progress_recorded ||
					Mission_Progress_Changed(last_mission_progress, mission_progress)) {
					Log_Mission_Progress(mission_progress, render_trace, result.frames);
					A35_Campaign_Flight_Record_Mission(Make_Flight_Mission_State(
						mission_progress, render_trace, result.frames,
						selected_archive, load_source));
					A35_Campaign_Flight_Flush("mission-progress-change");
					last_mission_progress = mission_progress;
					mission_progress_recorded = true;
				}
					/* Do not begin record/replay merely because the first frame rendered:
					** Mission00 owns the dialogue/control handoff. Physical M00 evidence
					** can report pre-completed objective status while original player
					** control is already valid, so the route gate follows the original
					** control flag rather than one objective slot. */
					if (!tutorial_control_ready_observed &&
						mission_progress.player_control_enabled) {
						tutorial_control_ready_observed = true;
						Renegade_Vita_Input_Route_Set_Gameplay_Active(true,
							result.frames);
						A30_Vita_Log("A3.5 mission progress: original player control available for route activation frame=%u objectives=%u status_1=%d\n",
							result.frames, mission_progress.objective_count,
							mission_progress.objective_status[0]);
					}
				const uint64_t frame_end = sceKernelGetProcessTimeWide();
				timing.Add(static_cast<uint32_t>(simulation_begin - frame_begin),
					static_cast<uint32_t>(render_begin - simulation_begin),
					static_cast<uint32_t>(frame_end - render_begin),
					static_cast<uint32_t>(frame_end - frame_begin));
				if (result.frames == 0U) {
					A30_Vita_Log("A3.1 breadcrumb: interactive render state scene=%p camera=%p star=%p static/dynamic/lights=%u/%u/%u vis=%u/%u camera=(%.3f,%.3f,%.3f) player=(%.3f,%.3f,%.3f) clip=%.3f..%.3f\n",
						reinterpret_cast<void *>(render_trace.scene_pointer),
						reinterpret_cast<void *>(render_trace.camera_pointer),
						reinterpret_cast<void *>(render_trace.star_pointer),
						render_trace.static_object_count,
						render_trace.dynamic_object_count,
						render_trace.static_light_count,
						render_trace.visibility_table_size,
						render_trace.visibility_table_count,
						render_trace.camera_x, render_trace.camera_y, render_trace.camera_z,
						render_trace.player_x, render_trace.player_y, render_trace.player_z,
						render_trace.near_clip, render_trace.far_clip);
					A30_Vita_Log("A3.1 breadcrumb: first render closure scene/camera/star/pre/begin/combat/message/end/post=%d/%d/%d/%d/%d/%d/%d/%d/%d meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
						render_trace.scene_available ? 1 : 0,
						render_trace.camera_available ? 1 : 0,
						render_trace.star_available ? 1 : 0,
						render_trace.pre_render_completed ? 1 : 0,
						render_trace.begin_render_completed ? 1 : 0,
						render_trace.combat_render_called ? 1 : 0,
						render_trace.message_window_render_called ? 1 : 0,
						render_trace.end_render_completed ? 1 : 0,
						render_trace.post_render_completed ? 1 : 0,
						static_cast<unsigned long long>(render_trace.mesh_submissions),
						static_cast<unsigned long long>(render_trace.vertex_submissions),
						static_cast<unsigned long long>(render_trace.triangle_submissions),
						static_cast<unsigned long long>(render_trace.rejected_submissions),
						static_cast<unsigned long long>(render_trace.unsupported_submissions));
					Log_Interactive_Player_Effects(render_trace, result.frames,
						"first-visible-frame");
				}
				if (!render_trace.end_render_completed ||
					!render_trace.post_render_completed) {
					result.render_error = true;
					A30_Vita_Log("A3.1 interactive: render closure FAIL frame=%u scene/camera/pre/begin/combat/end/post=%d/%d/%d/%d/%d/%d/%d\n",
						result.frames, render_trace.scene_available ? 1 : 0,
						render_trace.camera_available ? 1 : 0,
						render_trace.pre_render_completed ? 1 : 0,
						render_trace.begin_render_completed ? 1 : 0,
						render_trace.combat_render_called ? 1 : 0,
						render_trace.end_render_completed ? 1 : 0,
						render_trace.post_render_completed ? 1 : 0);
					break;
				}
				if (result.frames == 0U &&
					(render_trace.mesh_submissions == 0U ||
						render_trace.vertex_submissions == 0U ||
						render_trace.triangle_submissions == 0U ||
						render_trace.rejected_submissions != 0U ||
						render_trace.unsupported_submissions != 0U)) {
					result.render_error = true;
					A30_Vita_Log("A3.1 interactive: first visible-frame gate FAIL meshes=%llu vertices=%llu triangles=%llu rejected=%llu unsupported=%llu\n",
						static_cast<unsigned long long>(render_trace.mesh_submissions),
						static_cast<unsigned long long>(render_trace.vertex_submissions),
						static_cast<unsigned long long>(render_trace.triangle_submissions),
						static_cast<unsigned long long>(render_trace.rejected_submissions),
						static_cast<unsigned long long>(render_trace.unsupported_submissions));
					break;
				}
				++result.frames;
				Copy_Render_Statistics(result);
				A31FrameTelemetry capture_frame = {};
				capture_frame.frame_index = result.frames;
				capture_frame.monotonic_us = frame_end;
				capture_frame.frame_time_us = frame_end - frame_begin;
				capture_frame.ordinary_frame_time_us = capture_frame.frame_time_us;
				capture_frame.stages.input_us = simulation_begin - frame_begin;
				capture_frame.stages.game_update_us = render_begin - simulation_begin;
				capture_frame.stages.render_us = frame_end - render_begin;
				Copy_Renderer_Statistics(capture_frame.renderer);
				Copy_Flight_Memory(capture_frame.memory);
				if (capture_frame.renderer.draw_calls == 0U) {
					capture_frame.renderer.draw_calls = render_trace.mesh_submissions;
					capture_frame.renderer.mesh_submissions = render_trace.mesh_submissions;
					capture_frame.renderer.vertices = render_trace.vertex_submissions;
					capture_frame.renderer.triangles = render_trace.triangle_submissions;
					capture_frame.renderer.rejected_submissions =
						render_trace.rejected_submissions;
					capture_frame.renderer.unsupported_submissions =
						render_trace.unsupported_submissions;
				}
				capture_frame.game_update_count = result.frames;
				capture_frame.physics_update_count = result.frames;
				const RenegadeVitaInputTelemetry &input_telemetry =
					Renegade_Vita_Last_Input_Telemetry();
				capture_frame.input_action_count = input_telemetry.sample_count;
				capture_history->Push(capture_frame);
				A35_Campaign_Flight_Record_Frame(capture_frame,
					Make_Flight_Render_State(render_trace), Make_Flight_Audio_State());
				if (capture_frame.frame_time_us >= 250000ULL) {
					A35_Campaign_Flight_Flush("slow-frame-over-250ms");
				}
				/* A player/camera at frame one is an engine-ownership signal, not
				** proof that the physical panel has reached a settled gameplay
				** presentation. Dev82 retained a stale loading image and a black/HUD
				** image from that old automatic branch. Do not replace that error with
				** another guessed frame delay: the human observer, or a recorded input
				** route, must explicitly request the capture at the chosen checkpoint. */
				const bool requested_capture_ready = tutorial_control_ready_observed &&
					mission_progress.player_control_enabled && render_trace.scene_available &&
					render_trace.star_available && render_trace.camera_available &&
					render_trace.pre_render_completed && render_trace.begin_render_completed &&
					render_trace.combat_render_called && render_trace.end_render_completed &&
					render_trace.post_render_completed && render_trace.mesh_submissions != 0U &&
					render_trace.vertex_submissions != 0U && render_trace.triangle_submissions != 0U &&
					render_trace.rejected_submissions == 0U &&
					render_trace.unsupported_submissions == 0U;
				if (requested_capture_ready && !capture_policy_armed_logged) {
					capture_policy_armed_logged = true;
					A30_Vita_Log("A3.5 capture policy: automatic first-frame screenshot disabled; SELECT diagnostic enabled=%d by input-capture-select.flag; default SELECT cycles objectives. For opted-in capture, encode that SELECT edge at the fixed checkpoint in a recorded input route frame=%u\n",
						Renegade_Vita_Select_Capture_Enabled() ? 1 : 0, result.frames);
				}
				const bool select_pressed =
					(input_telemetry.buttons & SCE_CTRL_SELECT) != 0U;
				if (Renegade_Vita_Select_Capture_Enabled() && select_pressed &&
					!select_was_pressed && requested_capture_ready) {
					const bool readback = capture_pixels != NULL &&
						RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels, kCaptureBytes, true);
					char label[96];
					snprintf(label, sizeof(label), "manual-select-visible-gameplay-f%u-t%llu",
						result.frames, static_cast<unsigned long long>(frame_end));
					const A31StateSnapshot state = Make_Interactive_Capture_State(render_trace,
						result.frames, frame_end, "manual-select-visible-gameplay");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, readback ? capture_pixels : NULL, label);
					A30_Vita_Log("Capture: %s candidate=%s phase=interactive-player-owned reason=manual-select-visible-gameplay path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.screenshot_written ? 1 : 0,
						capture.state_written ? 1 : 0, capture.history_written ? 1 : 0,
						capture.summary_written ? 1 : 0, capture.first_error_code);
				}
				select_was_pressed = select_pressed;
				if (!result.first_frame_completed) {
					result.first_frame_completed = true;
					result.first_frame_geometry = true;
					A30_Vita_Log("A3.1 breadcrumb: first original render frame PASS meshes=%u vertices=%u triangles=%u\n",
						result.mesh_submissions, result.vertex_submissions,
						result.triangle_submissions);
				}
		if ((result.frames % kTimingWindowFrames) == 0U) {
			Log_File_Factory_Statistics(result.frames);
					A30_Vita_Log("A3.5 breadcrumb: %u-frame checkpoint PASS\n",
						result.frames);
					Log_Interactive_Player_Effects(render_trace, result.frames,
						"checkpoint");
#if !RENEGADE_VITA_M00_DEMO
					if (stricmp(selected_archive, "M13.mix") == 0) {
						Log_M13_Nearby_Actor_Snapshot(result.frames);
					}
#endif
					Log_Timing_Statistics(timing,
						RenegadeVitaRenderer::Get_Statistics());
					Log_Campaign_Simulation_Stages();
					Log_Input_Telemetry();
					Log_Audio_Runtime_Statistics("checkpoint", result.frames);
					A35_Campaign_Flight_Flush("checkpoint");
					A30_Vita_Log_Flush();
				}
			}
				result.clean_exit_requested = !result.render_error &&
					(result.start_exit_requested ||
#if RENEGADE_VITA_M00_DEMO
						(result.mission_completion_observed && result.mission_succeeded));
#else
						result.campaign_handoff_completed || result.frontend_exit_requested);
#endif
				if (result.clean_exit_requested && capture_history->Count() != 0U &&
					last_render_trace.star_available && last_render_trace.camera_available) {
					char label[96];
					const uint64_t exit_us = sceKernelGetProcessTimeWide();
					snprintf(label, sizeof(label), "pre-clean-exit-f%u-t%llu", result.frames,
						static_cast<unsigned long long>(exit_us));
					const A31StateSnapshot state = Make_Interactive_Capture_State(last_render_trace,
						result.frames, exit_us, "pre-clean-exit");
					const bool readback = capture_pixels != NULL &&
						RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(capture_pixels,
							kCaptureBytes, true);
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, readback ? capture_pixels : NULL, label);
					A30_Vita_Log("Capture flush: %s candidate=%s phase=interactive-player-owned reason=pre-clean-exit path=%s screenshot/state/csv/summary=%d/%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.screenshot_written ? 1 : 0,
						capture.state_written ? 1 : 0,
						capture.history_written ? 1 : 0, capture.summary_written ? 1 : 0,
						capture.first_error_code);
					A35_Campaign_Flight_Record_Event("lifecycle", "pre_clean_exit",
						result.frames, exit_us, "interactive capture flushed");
					A35_Campaign_Flight_Flush("pre-clean-exit");
				} else if (result.render_error && capture_history->Count() != 0U) {
					char label[96];
					const uint64_t fatal_us = sceKernelGetProcessTimeWide();
					snprintf(label, sizeof(label), "fatal-snapshot-f%u-t%llu", result.frames,
						static_cast<unsigned long long>(fatal_us));
					const A31StateSnapshot state = Make_Interactive_Capture_State(last_render_trace,
						result.frames, fatal_us, "best-effort-fatal-snapshot");
					const A31CaptureBundleResult capture = Capture_Interactive_Frame(state,
						*capture_history, NULL, label);
					A30_Vita_Log("Capture flush: %s candidate=%s phase=interactive-player-owned reason=best-effort-fatal-snapshot path=%s state/csv/summary=%d/%d/%d error_code=%d\n",
						capture.passed ? "PASS" : "FAIL", RENEGADE_BUILD_CANDIDATE_LABEL,
						capture.bundle_path, capture.state_written ? 1 : 0,
						capture.history_written ? 1 : 0, capture.summary_written ? 1 : 0,
						capture.first_error_code);
					A35_Campaign_Flight_Record_Event("lifecycle",
						"fatal_render_error", result.frames, fatal_us,
						"best-effort fatal capture flushed");
					A35_Campaign_Flight_Flush("best-effort-fatal-snapshot");
					A30_Vita_Log_Flush();
				}
				Copy_Timing_Statistics(result, timing);
				Log_Timing_Statistics(timing, RenegadeVitaRenderer::Get_Statistics());
				Log_Campaign_Simulation_Stages();
				Log_Audio_Runtime_Statistics("final", result.frames);
				A35_Campaign_Flight_Flush("final");
				A30_Vita_Log_Flush();
			if (result.start_exit_requested && result.clean_exit_requested) {
				A30_Vita_Log("A3.1 breadcrumb: native orderly exit request detected\n");
			} else if (result.mission_completion_observed && result.mission_succeeded &&
				result.clean_exit_requested) {
				A30_Vita_Log("A3.5 breadcrumb: original mission success transition detected\n");
			} else if (result.mission_completion_observed || result.star_killed_observed) {
				A30_Vita_Log("A3.5 breadcrumb: original mission failure transition detected\n");
			}
			} while (false);
			A35_Campaign_Flight_Shutdown();
			free(capture_pixels);
			delete capture_history;
			capture_history = NULL;
				if (mission_completion_observer_installed) {
					A31_Interactive_End_Mission_Completion_Observation();
					mission_completion_observer_installed = false;
				}

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
				// EVA tabs can retain live world/model pointers. Release them first.
				if (frontend_dialog_manager_retained) DialogMgrClass::Flush_Dialogs();
				if (frontend_combat_mode_registered) {
					if (!frontend_combat_mode.Is_Inactive()) {
						frontend_combat_mode.Deactivate();
						GameModeManager::Safely_Deactivate();
						level_unload_pending = false;
						radar_initialized = false;
						A30_Vita_Log("A4 frontend: original CombatGameMode shutdown consumed level/radar teardown\n");
					}
					/* Keep the inactive original owner registered until original player
					 * destruction has completed. cPlayer::On_Destroy() looks up Combat
					 * unconditionally, even when it is inactive. */
					A30_Vita_Log("A4 frontend: retained inactive Combat mode through player/session teardown\n");
				}
				if (frontend_menu_mode_registered_for_handoff) {
					if (!frontend_menu_mode.Is_Inactive()) {
						frontend_menu_mode.Deactivate();
					}
					GameModeManager::Safely_Deactivate();
					GameModeManager::Remove(&frontend_menu_mode);
					frontend_menu_mode_registered_for_handoff = false;
					A30_Vita_Log("A4 frontend: removed retained Menu mode after Combat handoff\n");
				}
#if !RENEGADE_VITA_M00_DEMO
				if (GameModeManager::Find("Movie") == &frontend_movie_mode) {
					if (!frontend_movie_mode.Is_Inactive()) {
						frontend_movie_mode.Deactivate();
					}
					GameModeManager::Safely_Deactivate();
					GameModeManager::Remove(&frontend_movie_mode);
					A30_Vita_Log("A4 campaign: removed retained Movie mode during session teardown\n");
				}
#endif
#endif

				/* Match CombatGameModeClass::Core_Shutdown for the direct M00 route:
				 * cGod leaves before the level frees static network wrappers, game
			 * objects, and load-on-demand assets. This precedes Radar/Combat
			 * shutdown and keeps the original ownership hierarchy intact. */
			if (level_unload_pending) {
				A30_Vita_Log("A4 breadcrumb: original Combat level unload entry\n");
				cGod::Exit();
				CombatManager::Unload_Level();
				level_unload_pending = false;
				A30_Vita_Log("A4 breadcrumb: original Combat level unload complete\n");
			}
			if (radar_initialized) {
				RadarManager::Shutdown();
				A30_Vita_Log("A4 breadcrumb: original RadarManager shutdown complete\n");
			}
		if (session_initialized && !original_end_game_consumed) {
			/* Preserve GameInitMgrClass's original session shutdown ordering:
			 * client-goodbye events are drained by NetworkObjectMgr, then the
			 * original server teams and player objects leave before a reload. */
			A30_Vita_Log("A4 breadcrumb: original session teardown entry\n");
			cNetwork::Flush();
			cNetwork::Cleanup_Client();
			cNetwork::Cleanup_Server();
			cPlayerManager::Remove_All();
			cTeamManager::Remove_All();
			NetworkObjectMgrClass::Set_All_Delete_Pending();
			NetworkObjectMgrClass::Delete_Pending();
			cGod::Reset();
			A30_Vita_Log("A4 breadcrumb: original session teardown complete\n");
		}
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
		if (frontend_combat_mode_registered) {
			GameModeManager::Remove(&frontend_combat_mode);
			frontend_combat_mode_registered = false;
			A30_Vita_Log("A4 frontend: removed original Combat mode after player/session teardown\n");
		}
#if !RENEGADE_VITA_M00_DEMO
		if (frontend_score_mode_registered) {
			if (!frontend_score_mode.Is_Inactive()) {
				frontend_score_mode.Deactivate();
			}
			GameModeManager::Safely_Deactivate();
			GameModeManager::Remove(&frontend_score_mode);
			frontend_score_mode_registered = false;
		}
#endif
#endif
			if (campaign_initialized) {
				EncyclopediaMgrClass::Shutdown();
				CampaignManager::Shutdown();
				campaign_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original CampaignManager catalog shutdown complete\n");
			}
				if (combat_initialized) {
					A30_Vita_Log("A3.1 breadcrumb: Combat shutdown entry\n");
					if (text_window_scene_initialized) {
						TextWindowClass::Shutdown();
						text_window_scene_initialized = false;
						A30_Vita_Log("A3.5 text window: original scene binding shutdown complete\n");
					}
					CombatManager::Shutdown();
					A30_Vita_Log("A3.1 breadcrumb: Combat shutdown complete\n");
				}
				if (text_display_initialized) {
					DebugManager::Set_Display_Handler(NULL);
					TextDisplayGameModeClass::Get_Instance()->Shutdown();
					text_display_initialized = false;
					A30_Vita_Log("A3.5 text display: original TextDisplayGameMode shutdown complete\n");
				}
				if (stylemgr_initialized) {
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
				if (frontend_dialog_manager_retained) {
					RenegadeDialogMgrClass::Shutdown();
					frontend_dialog_manager_retained = false;
				} else
#endif
				StyleMgrClass::Shutdown();
				stylemgr_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original StyleMgr shutdown complete\n");
			}
			if (translatedb_initialized) {
				TranslateDBClass::Shutdown();
				translatedb_initialized = false;
				A30_Vita_Log("A3.5 loading screen: original TranslateDB shutdown complete\n");
			}
			if (session_initialized) {
			GameInitMgrClass::Shutdown();
			A30_Vita_Log("A4 breadcrumb: original GameInitMgr SP shutdown complete\n");
			cNetwork::Onetime_Shutdown();
			A30_Vita_Log("A3.1 breadcrumb: network shutdown complete\n");
		}
		if (session_initialized) cServerFps::Destroy_Instance();
		if (input_initialized) Input::Shutdown();
		}
		A30_Vita_Log("A3.1 breadcrumb: application audio teardown entry singleton=%p\n",
			static_cast<void *>(WWAudioClass::Get_Instance()));
	}
	audio_teardown_completed = WWAudioClass::Get_Instance() == NULL;
	A30_Vita_Log("A3.1 breadcrumb: application audio teardown complete singleton=%p\n",
		static_cast<void *>(WWAudioClass::Get_Instance()));

	A35_Vita_Clear_Prepared_Render_Objs();
	if (asset_manager != NULL) WW3DAssetManager::Delete_This();
	if (path_manager_initialized) PathMgrClass::Shutdown();
	if (math_initialized) WWMath::Shutdown();
	if (wwsaveload_initialized) WWSaveLoad::Shutdown();
	if (ww3d_initialized) {
		WW3D::Shutdown();
		A30_Vita_Log("A3.1 breadcrumb: renderer shutdown complete\n");
	}
	if (wwphys_initialized) WWPhys::Shutdown();
	Log_File_Factory_Statistics();
	_TheFileFactory = previous_read_factory;
	_TheWritingFileFactory = previous_write_factory;
	result.teardown_completed = !result.render_error && audio_teardown_completed &&
		WW3DAssetManager::Get_Instance() == NULL && !WW3D::Is_Initted();
	A30_Vita_Log("A3.1 interactive: complete ready=%d transport=%d level=%d player=%d commando=%d frames=%u exit=%d render_error=%d teardown=%d pause/resume=%d/%d paused_input_frames=%u start_exit=%d mission_complete/success/star=%d/%d/%d perf_fps=%.3f p50/p95/worst_us=%u/%u/%u\n",
		result.initialized ? 1 : 0, result.transport_established ? 1 : 0,
		result.level_loaded ? 1 : 0, result.player_created ? 1 : 0,
		result.commando_created ? 1 : 0, result.frames,
		result.clean_exit_requested ? 1 : 0, result.render_error ? 1 : 0,
		result.teardown_completed ? 1 : 0, result.pause_observed ? 1 : 0,
		result.resume_observed ? 1 : 0, result.paused_input_frames,
		result.start_exit_requested ? 1 : 0,
		result.mission_completion_observed ? 1 : 0,
		result.mission_succeeded ? 1 : 0,
		result.star_killed_observed ? 1 : 0,
		static_cast<double>(result.average_fps_milli) / 1000.0,
		result.median_frame_us, result.p95_frame_us, result.worst_frame_us);
	return result;
}
