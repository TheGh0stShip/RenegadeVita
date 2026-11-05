// Actual original subtitle manager/parser/caption ownership with a short-enum
// engine and an independently compiled int-enum movie caller. Only sentence
// rendering and display resolution are observed, not GPU pixels or gameplay.
#include "renegade_movie_subtitles.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(expression) do { if (!(expression)) { \
    fprintf(stderr, "subtitle contract failed at line %d: %s\n", __LINE__, #expression); \
    abort(); } } while (0)

enum EnumAbiProbe { EnumAbiZero, EnumAbiOne };
static_assert(sizeof(wchar_t) == 2, "Fixture must retain engine UTF-16 storage");

extern "C" {
void Fixture_Begin(const char *root, void *font);
void Fixture_End();
void Fixture_Enable_Factory(uint32_t enabled);
uint32_t Fixture_Alive_Renderers();
uint32_t Fixture_Constructed_Renderers();
uint32_t Fixture_Destroyed_Renderers();
uint32_t Fixture_Files_Requested();
uint32_t Fixture_Files_Returned();
uint32_t Fixture_Render_Count();
uint32_t Fixture_Caption_Is(const char *caption);
uint32_t Fixture_Visible();
uint32_t Fixture_Color();
int32_t Fixture_X();
int32_t Fixture_Y();
FontCharsClass *Fixture_Create_Font();
void Fixture_Release_Font(FontCharsClass *font);
uint32_t Fixture_Font_References(FontCharsClass *font);
uint32_t Fixture_Destroyed_Fonts();
void Fixture_Set_Render_Guard(void (*guard)());
}

#if defined(MOVIE_SUBTITLE_ENGINE_FIXTURE)

#include "subtitlemanager.h"
#include "subtitle.h"
#include "renegade_file_factory.h"
#include "ww3d.h"
#include <map>
#include <string>

static_assert(sizeof(EnumAbiProbe) == 1, "Engine fixture must use short enums");
static_assert(sizeof(SubTitleClass::Alignment) == 1, "Original caption enum ABI changed");

namespace {
struct DrawRecord {
    std::u16string caption;
    Vector2 location = Vector2(0.0F, 0.0F);
    uint32_t color = 0U;
    bool visible = false;
};

std::map<const Render2DSentenceClass *, DrawRecord> g_draw_records;
const Render2DSentenceClass *g_last_renderer = NULL;
uint32_t g_constructed = 0U;
uint32_t g_destroyed = 0U;
uint32_t g_renders = 0U;
uint32_t g_gets = 0U;
uint32_t g_returns = 0U;
uint32_t g_destroyed_fonts = 0U;
void *g_expected_font = NULL;
std::string g_retail, g_user, g_cache, g_mods;
FileFactoryClass *g_previous_factory = NULL;
void (*g_render_guard)() = NULL;

class ObservedRootedFactory : public RenegadeRootedFileFactoryClass {
public:
    explicit ObservedRootedFactory(const RenegadePathRoots &roots)
        : RenegadeRootedFileFactoryClass(roots) {}

    FileClass *Get_File(const char *name) override
    {
        ++g_gets;
        return RenegadeRootedFileFactoryClass::Get_File(name);
    }

    void Return_File(FileClass *file) override
    {
        // FileStraw must release its original open before file_auto_ptr
        // returns the file to the rooted owner.
        CHECK(file != NULL);
        CHECK(!file->Is_Open());
        ++g_returns;
        RenegadeRootedFileFactoryClass::Return_File(file);
    }
};

ObservedRootedFactory *g_factory = NULL;

const DrawRecord *Last_Draw()
{
    const auto found = g_draw_records.find(g_last_renderer);
    return found == g_draw_records.end() ? NULL : &found->second;
}
} // namespace

// Observe the original constructors/destructors without replacing their font
// retention. The generated include contains the actual production methods.
static void Fixture_Renderer_Created(Render2DSentenceClass *renderer)
{
    ++g_constructed;
    CHECK(g_draw_records.emplace(renderer, DrawRecord()).second);
}

static void Fixture_Renderer_Destroyed(Render2DSentenceClass *renderer)
{
    CHECK(g_draw_records.erase(renderer) == 1U);
    if (g_last_renderer == renderer) g_last_renderer = NULL;
    ++g_destroyed;
}

#include "subtitle-renderer-ownership.inc"

ShaderClass Render2DClass::Get_Default_Shader()
{
    return ShaderClass();
}

void FontCharsClass::Free_GDI_Font()
{
    // No glyph or platform font creation is requested in this fixture.
    CHECK(GDIFont == NULL && GDIBitmap == NULL && MemDC == NULL);
}

void FontCharsClass::Free_Character_Arrays()
{
    CHECK(UnicodeCharArray == NULL);
    for (auto *entry : ASCIICharArray) CHECK(entry == NULL);
}

void Render2DSentenceClass::Reset()
{
    DrawRecord &draw = g_draw_records.at(this);
    draw.caption.clear();
    draw.visible = false;
}

Vector2 Render2DSentenceClass::Get_Text_Extents(const WCHAR *text)
{
    size_t length = 0U;
    while (text[length] != 0) ++length;
    return Vector2(static_cast<float>(length * 8U), 18.0F);
}

void Render2DSentenceClass::Set_Location(const Vector2 &location)
{
    Location = location;
    g_draw_records.at(this).location = location;
}

void Render2DSentenceClass::Build_Sentence(const WCHAR *text)
{
    CHECK(Font != NULL);
    CHECK(static_cast<void *>(Font) == g_expected_font);
    CHECK(Font->Num_Refs() >= 1);
    std::u16string &caption = g_draw_records.at(this).caption;
    caption.clear();
    for (; *text != 0; ++text) caption.push_back(static_cast<char16_t>(*text));
}

void Render2DSentenceClass::Draw_Sentence(uint32 color)
{
    DrawRecord &draw = g_draw_records.at(this);
    draw.color = color;
    draw.visible = true;
}

void Render2DSentenceClass::Render()
{
    if (g_render_guard != NULL) g_render_guard();
    g_last_renderer = this;
    ++g_renders;
}

void WW3D::Get_Device_Resolution(int &width, int &height, int &bits, bool &windowed)
{
    width = 960;
    height = 544;
    bits = 32;
    windowed = false;
}

extern "C" void Fixture_Begin(const char *root, void *font)
{
    CHECK(g_factory == NULL);
    CHECK(g_draw_records.empty());
    g_retail = std::string(root) + "/retail";
    g_user = std::string(root) + "/user";
    g_cache = std::string(root) + "/cache";
    g_mods = std::string(root) + "/mods";
    RenegadePathRoots roots = {g_retail.c_str(), g_user.c_str(),
                             g_cache.c_str(), g_mods.c_str()};
    g_expected_font = font;
    g_previous_factory = _TheFileFactory;
    g_factory = new ObservedRootedFactory(roots);
    _TheFileFactory = g_factory;
    Renegade_File_Factory_Reset_Statistics();
}

extern "C" void Fixture_End()
{
    CHECK(g_draw_records.empty());
    CHECK(g_constructed == g_destroyed);
    CHECK(g_gets == g_returns);
    _TheFileFactory = g_previous_factory;
    delete g_factory;
    g_factory = NULL;
    Renegade_File_Factory_Reset_Statistics();
}

extern "C" void Fixture_Enable_Factory(uint32_t enabled)
{
    _TheFileFactory = enabled ? g_factory : NULL;
}

extern "C" uint32_t Fixture_Alive_Renderers() { return g_constructed - g_destroyed; }
extern "C" uint32_t Fixture_Constructed_Renderers() { return g_constructed; }
extern "C" uint32_t Fixture_Destroyed_Renderers() { return g_destroyed; }
extern "C" uint32_t Fixture_Files_Requested() { return g_gets; }
extern "C" uint32_t Fixture_Files_Returned() { return g_returns; }
extern "C" uint32_t Fixture_Render_Count() { return g_renders; }
extern "C" uint32_t Fixture_Visible() { return Last_Draw() && Last_Draw()->visible; }
extern "C" uint32_t Fixture_Color() { return Last_Draw() ? Last_Draw()->color : 0U; }
extern "C" int32_t Fixture_X() { return Last_Draw() ? static_cast<int32_t>(Last_Draw()->location.X) : 0; }
extern "C" int32_t Fixture_Y() { return Last_Draw() ? static_cast<int32_t>(Last_Draw()->location.Y) : 0; }
extern "C" FontCharsClass *Fixture_Create_Font() { return new FontCharsClass(); }
extern "C" void Fixture_Release_Font(FontCharsClass *font) { font->Release_Ref(); }
extern "C" uint32_t Fixture_Font_References(FontCharsClass *font) { return font->Num_Refs(); }
extern "C" uint32_t Fixture_Destroyed_Fonts() { return g_destroyed_fonts; }
extern "C" void Fixture_Set_Render_Guard(void (*guard)()) { g_render_guard = guard; }

extern "C" uint32_t Fixture_Caption_Is(const char *caption)
{
    const DrawRecord *draw = Last_Draw();
    if (draw == NULL || draw->caption.size() != strlen(caption)) return 0U;
    for (size_t index = 0; index < draw->caption.size(); ++index) {
        if (draw->caption[index] != static_cast<unsigned char>(caption[index])) return 0U;
    }
    return 1U;
}

#else

#include "renegade_paths.h"
#include <algorithm>
#include <atomic>
#include <deque>
#include <string>
#include <vector>

static_assert(sizeof(EnumAbiProbe) == 4, "Movie caller must use int-sized enums");

// The complete production movie entry/exit/render functions run against fake
// decoder and GPU APIs. They still call the real short-enum subtitle adapter,
// original manager/parser/caption owners, original font retention and rooted
// file factory. This is a non-play contract, not a decoder or GPU test.
namespace BinkFixture {
class BINKMovie {
public:
    static void Play(const char *, const char *, FontCharsClass *);
    static void Stop();
    static void Shutdown();
    static void Render();
};

using GLuint = unsigned;
using GLint = int;
using GLenum = unsigned;
using GLsizei = int;
using GLfloat = float;
using GLboolean = unsigned char;
enum {
    GL_FALSE = 0, GL_VIEWPORT, GL_MATRIX_MODE, GL_ACTIVE_TEXTURE,
    GL_CURRENT_COLOR, GL_DEPTH_TEST, GL_CULL_FACE, GL_BLEND, GL_TEXTURE_2D,
    GL_TEXTURE_BINDING_2D, GL_PROJECTION, GL_MODELVIEW, GL_TEXTURE0,
    GL_TEXTURE1, GL_TRIANGLE_STRIP,
};

struct GraphicsState {
    GLint viewport[4] = {7, 11, 640, 360};
    GLint matrix_mode = GL_MODELVIEW;
    GLint active_texture = GL_TEXTURE1;
    GLint texture = 99;
    GLfloat color[4] = {0.2F, 0.3F, 0.4F, 0.5F};
    bool enabled[32] = {};
    int projection_depth = 0;
    int modelview_depth = 0;
};
GraphicsState g_gl;
GraphicsState g_expected_gl;
uint32_t g_quad_draws = 0U;
uint32_t g_guard_calls = 0U;
uint32_t g_quad_vertices = 0U;

void glGetIntegerv(GLenum field, GLint *value)
{
    if (field == GL_VIEWPORT) memcpy(value, g_gl.viewport, sizeof(g_gl.viewport));
    else if (field == GL_MATRIX_MODE) *value = g_gl.matrix_mode;
    else if (field == GL_ACTIVE_TEXTURE) *value = g_gl.active_texture;
    else if (field == GL_TEXTURE_BINDING_2D) *value = g_gl.texture;
    else CHECK(false);
}
void glGetFloatv(GLenum field, GLfloat *value)
{
    CHECK(field == GL_CURRENT_COLOR);
    memcpy(value, g_gl.color, sizeof(g_gl.color));
}
GLboolean glIsEnabled(GLenum field) { return g_gl.enabled[field]; }
void glEnable(GLenum field) { g_gl.enabled[field] = true; }
void glDisable(GLenum field) { g_gl.enabled[field] = false; }
void glActiveTexture(GLenum texture) { g_gl.active_texture = texture; }
void glBindTexture(GLenum, GLuint texture) { g_gl.texture = texture; }
void glDeleteTextures(int, const GLuint *) {}
void glMatrixMode(GLenum mode) { g_gl.matrix_mode = mode; }
void glPushMatrix()
{
    if (g_gl.matrix_mode == GL_PROJECTION) ++g_gl.projection_depth;
    else ++g_gl.modelview_depth;
}
void glPopMatrix()
{
    if (g_gl.matrix_mode == GL_PROJECTION) CHECK(g_gl.projection_depth-- > 0);
    else CHECK(g_gl.modelview_depth-- > 0);
}
void glViewport(GLint x, GLint y, GLsizei width, GLsizei height)
{
    g_gl.viewport[0] = x; g_gl.viewport[1] = y;
    g_gl.viewport[2] = width; g_gl.viewport[3] = height;
}
void glLoadIdentity() {}
void glOrtho(double, double, double, double, double, double) {}
void glColor4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a)
{
    g_gl.color[0] = r; g_gl.color[1] = g;
    g_gl.color[2] = b; g_gl.color[3] = a;
}
void glColor4ub(unsigned char r, unsigned char g, unsigned char b, unsigned char a)
{
    glColor4f(r / 255.0F, g / 255.0F, b / 255.0F, a / 255.0F);
}
void glBegin(GLenum mode) { CHECK(mode == GL_TRIANGLE_STRIP); g_quad_vertices = 0U; }
void glTexCoord2f(float, float) {}
void glVertex3f(float, float, float) { ++g_quad_vertices; }
void glEnd() { CHECK(g_quad_vertices == 4U); ++g_quad_draws; }

namespace RenegadeVitaRenderer {
void Get_Physical_Display_Size(uint32_t &width, uint32_t &height)
{ width = 640U; height = 360U; }
void Invalidate_Texture_State_Cache() {}
}

void Check_Render_State()
{
    CHECK(g_quad_draws > g_guard_calls);
    ++g_guard_calls;
    CHECK(memcmp(g_gl.viewport, g_expected_gl.viewport, sizeof(g_gl.viewport)) == 0);
    CHECK(memcmp(g_gl.color, g_expected_gl.color, sizeof(g_gl.color)) == 0);
    CHECK(memcmp(g_gl.enabled, g_expected_gl.enabled, sizeof(g_gl.enabled)) == 0);
    CHECK(g_gl.matrix_mode == g_expected_gl.matrix_mode);
    CHECK(g_gl.active_texture == g_expected_gl.active_texture);
    CHECK(g_gl.texture == g_expected_gl.texture);
    CHECK(g_gl.projection_depth == 0 && g_gl.modelview_depth == 0);
}

struct AVPacket {};
struct AVFrame {};
struct AVStream {};
struct AVFormatContext { AVStream *streams[1]; };
struct AVCodecContext { int width = 640; int height = 480; };
struct SwrContext {};
struct SwsContext {};
struct AVRational { int num; int den; };
constexpr int64_t AV_NOPTS_VALUE = INT64_MIN;
enum { AVMEDIA_TYPE_VIDEO, AVMEDIA_TYPE_AUDIO };

bool g_initialized = true, g_active = false, g_complete = true;
bool g_open_failure = false;
bool g_audio_enabled = false, g_texture_allocated = false, g_pending_video = false;
bool g_video_prefetch_failed = false, g_packet_pending = false, g_decoders_flushed = false;
bool g_update_budget_logged = false, g_update_entry_logged = false, g_render_entry_logged = false;
bool g_demux_read_entry_logged = false, g_audio_thread_entry_logged = false;
bool g_audio_first_output_logged = false, g_audio_first_frame_logged = false;
bool g_video_first_frame_logged = false, g_video_first_upload_logged = false, g_video_drop_logged = false;
std::atomic<bool> g_demux_eof(false), g_audio_decode_eof(false), g_audio_drained(true);
std::atomic<int64_t> g_presentation_start_us(0);
char g_movie_name[160] = {};
RenegadeMovieSubtitles *g_subtitles = NULL;
RenegadePathRoots kVitaRoots = {};
AVStream g_stream;
AVFormatContext *g_format = NULL;
AVCodecContext *g_video_decoder = NULL, *g_audio_decoder = NULL;
AVFrame *g_video_frame = NULL, *g_audio_frame = NULL;
AVPacket *g_packet = NULL;
SwrContext *g_resampler = NULL;
SwsContext *g_scaler = NULL;
std::deque<AVPacket *> g_prefetched_video_packets;
size_t g_prefetched_video_bytes = 0U, g_prefetched_video_high_water = 0U;
std::vector<uint8_t> g_pending_video_pixels;
std::vector<int16_t> g_audio_ring, g_audio_conversion;
GLuint g_video_texture = 0U;
int g_texture_width = 0, g_texture_height = 0, g_video_stream = -1, g_audio_stream = -1;
int g_source_video_width = 0, g_source_video_height = 0, g_video_width = 0, g_video_height = 0;
int64_t g_first_video_pts_us = AV_NOPTS_VALUE, g_uploaded_video_pts_us = 0;
int64_t g_frame_duration_us = 33333;
uint64_t g_decoded_video_frames = 0U, g_uploaded_video_frames = 0U, g_dropped_video_frames = 0U;
uint32_t g_last_skip_buttons = 0U;
constexpr int kMaxMovieUploadWidth = 320, kMaxMovieUploadHeight = 240;
int g_video_render_timing = 0;
struct BinkStageTimer { explicit BinkStageTimer(int &) {} };

void av_packet_free(AVPacket **packet) { delete *packet; *packet = NULL; }
void av_packet_unref(AVPacket *) {}
void av_frame_free(AVFrame **frame) { delete *frame; *frame = NULL; }
void avcodec_free_context(AVCodecContext **codec) { delete *codec; *codec = NULL; }
void avformat_close_input(AVFormatContext **format) { delete *format; *format = NULL; }
void swr_free(SwrContext **context) { delete *context; *context = NULL; }
void sws_freeContext(SwsContext *context) { delete context; }
AVPacket *av_packet_alloc() { return new AVPacket(); }
AVFrame *av_frame_alloc() { return new AVFrame(); }
int avformat_open_input(AVFormatContext **format, const char *, void *, void *)
{
    if (g_open_failure) return -1;
    *format = new AVFormatContext();
    (*format)->streams[0] = &g_stream;
    return 0;
}
int avformat_find_stream_info(AVFormatContext *, void *) { return 0; }
int av_find_best_stream(AVFormatContext *, int type, int, int, void *, int)
{ return type == AVMEDIA_TYPE_VIDEO ? 0 : -1; }
AVRational av_guess_frame_rate(AVFormatContext *, AVStream *, void *) { return {30, 1}; }
AVRational av_inv_q(AVRational rate) { return {rate.den, rate.num}; }
int64_t av_rescale_q(int64_t value, AVRational from, AVRational to)
{ return value * from.num * to.den / (from.den * to.num); }
bool Open_Decoder(AVCodecContext **codec, AVStream *) { *codec = new AVCodecContext(); return true; }
bool Configure_Audio() { return false; }
void Stop_Audio_Output() {}
void Prime_Skip_Button_Latch() {}
void Reset_Playback_Statistics() {}
void Log_Playback_Statistics(const char *) {}
void Log_FFmpeg_Error(const char *, int) {}
void A30_Vita_Log(const char *, ...) {}
void A4_Frontend_Record_Bink_Init(bool) {}
void A4_Frontend_Record_Bink_Play(const char *) {}
void A4_Frontend_Record_Bink_Skip(const char *) {}
bool Start_Presentation_Clock(const char *) { CHECK(g_quad_draws != 0U); return true; }
void Copy_Movie_Name(const char *name)
{ snprintf(g_movie_name, sizeof(g_movie_name), "%s", name ? name : ""); }
const char *Build_FFmpeg_File_URL(const RenegadeResolvedPath &path, char *, size_t)
{ return path.physical; }
void Configure_Video_Upload_Dimensions(int width, int height)
{
    g_source_video_width = width; g_source_video_height = height;
    g_video_width = kMaxMovieUploadWidth; g_video_height = kMaxMovieUploadHeight;
}

#include "subtitle-bink-routing.inc"

void Run(const char *root, FontCharsClass *font)
{
    const std::string retail = std::string(root) + "/retail";
    const std::string user = std::string(root) + "/user";
    const std::string cache = std::string(root) + "/cache";
    const std::string mods = std::string(root) + "/mods";
    kVitaRoots = {retail.c_str(), user.c_str(), cache.c_str(), mods.c_str()};
    g_gl.enabled[GL_DEPTH_TEST] = g_gl.enabled[GL_CULL_FACE] = true;
    g_gl.enabled[GL_BLEND] = g_gl.enabled[GL_TEXTURE_2D] = true;
    g_expected_gl = g_gl;
    Fixture_Set_Render_Guard(Check_Render_State);

    BINKMovie::Play("Data/fixture.bik", "data\\subtitle.ini", font);
    CHECK(g_active && !g_complete && g_subtitles != NULL);
    CHECK(Fixture_Font_References(font) == 2U);
    BINKMovie::Render();
    CHECK(Fixture_Render_Count() == 0U); // No visible movie texture yet.
    g_video_texture = 1U;
    g_texture_allocated = true;
    g_texture_width = 512;
    g_texture_height = 256;
    g_uploaded_video_pts_us = 999999;
    g_decoded_video_frames = 60000U; // Decode-ahead must not select captions.
    BINKMovie::Render();
    CHECK(!Fixture_Visible());
    g_uploaded_video_pts_us = 1000000;
    BINKMovie::Render();
    CHECK(Fixture_Caption_Is("Alpha"));
    g_decoded_video_frames += 60000U;
    BINKMovie::Render();
    CHECK(Fixture_Caption_Is("Alpha"));
    g_uploaded_video_pts_us = 2000000;
    BINKMovie::Render();
    CHECK(Fixture_Caption_Is("Beta"));
    CHECK(g_guard_calls == 4U);

    // Replacement must release the old sentence/font before acquiring anew.
    BINKMovie::Play("Data/fixture.bik", "data\\subtitle.ini", font);
    CHECK(Fixture_Alive_Renderers() == 1U);
    CHECK(Fixture_Constructed_Renderers() == 2U);
    CHECK(Fixture_Destroyed_Renderers() == 1U);
    CHECK(Fixture_Font_References(font) == 2U);
    CHECK(g_uploaded_video_pts_us == 0);
    Mark_Failed("synthetic decode failure");
    CHECK(!g_active && g_complete && g_subtitles == NULL && g_format == NULL);
    CHECK(Fixture_Alive_Renderers() == 0U && Fixture_Font_References(font) == 1U);
    BINKMovie::Stop(); // A second cleanup must be harmless.
    CHECK(Fixture_Destroyed_Renderers() == 2U);

    BINKMovie::Play("Data/fixture.bik", "data\\subtitle.ini", font);
    g_open_failure = true;
    BINKMovie::Play("Data/fixture.bik", "data\\subtitle.ini", font);
    CHECK(!g_active && g_complete && g_subtitles == NULL);
    CHECK(Fixture_Alive_Renderers() == 0U && Fixture_Font_References(font) == 1U);
    g_open_failure = false;
    BINKMovie::Play("Data/fixture.bik", NULL, font);
    CHECK(g_active && g_subtitles == NULL);
    CHECK(Fixture_Font_References(font) == 1U);
    BINKMovie::Shutdown();
    CHECK(!g_initialized && !g_active && g_complete && g_format == NULL);
    Fixture_Set_Render_Guard(NULL);
}
} // namespace BinkFixture

namespace {
FontCharsClass *g_font = NULL;

RenegadeMovieSubtitles *Create(const char *movie = "movies\\FiXtUrE.bik")
{
    return Renegade_Movie_Subtitles_Create(movie, "data\\subtitle.ini", g_font);
}

void Present(RenegadeMovieSubtitles *owner, uint32_t tick)
{
    Renegade_Movie_Subtitles_Process(owner, tick);
    Renegade_Movie_Subtitles_Render(owner);
}

void Schedule()
{
    RenegadeMovieSubtitles *owner = Create();
    CHECK(owner != NULL);
    CHECK(Fixture_Alive_Renderers() == 1U);
    CHECK(Fixture_Files_Requested() == 1U);
    CHECK(Fixture_Files_Returned() == 1U);
    Present(owner, 0U);
    CHECK(!Fixture_Visible());
    Present(owner, 1U);
    CHECK(!Fixture_Visible());
    Present(owner, 59U);
    CHECK(!Fixture_Visible());
    Present(owner, 60U);
    CHECK(Fixture_Visible());
    CHECK(Fixture_Caption_Is("Alpha"));
    CHECK(Fixture_X() == 0 && Fixture_Y() == 14 * (544 / 16));
    CHECK(Fixture_Color() == UINT32_C(0xFF0C2238));
    Present(owner, 119U);
    CHECK(Fixture_Caption_Is("Alpha"));
    Present(owner, 120U);
    CHECK(Fixture_Caption_Is("Beta"));
    CHECK(Fixture_X() == 960 - 4 * 8 && Fixture_Y() == 13 * (544 / 16));
    Present(owner, 149U);
    CHECK(Fixture_Visible());
    Present(owner, 150U);
    CHECK(!Fixture_Visible());
    CHECK(Fixture_Render_Count() == 8U);
    Renegade_Movie_Subtitles_Destroy(owner);
    CHECK(Fixture_Alive_Renderers() == 0U);
}

void Admission()
{
    CHECK(Renegade_Movie_Subtitles_Create(NULL, "data\\subtitle.ini", g_font) == NULL);
    CHECK(Renegade_Movie_Subtitles_Create("fixture.bik", NULL, g_font) == NULL);
    CHECK(Renegade_Movie_Subtitles_Create("fixture.bik", "data\\subtitle.ini", NULL) == NULL);
    CHECK(Fixture_Constructed_Renderers() == 0U);
    Renegade_Movie_Subtitles_Process(NULL, UINT32_MAX);
    Renegade_Movie_Subtitles_Render(NULL);
    Renegade_Movie_Subtitles_Destroy(NULL);
    CHECK(Fixture_Render_Count() == 0U);

    CHECK(Renegade_Movie_Subtitles_Create("fixture.bik", "data\\missing.ini", g_font) == NULL);
    CHECK(Renegade_Movie_Subtitles_Create("fixture.bik", "../SubTitle.INI", g_font) == NULL);
    CHECK(Create("unknown.bik") == NULL);
    CHECK(Create("") == NULL);
    char too_long[300];
    memset(too_long, 'x', sizeof(too_long));
    too_long[sizeof(too_long) - 1] = '\0';
    CHECK(Create(too_long) == NULL);
    Fixture_Enable_Factory(0U);
    CHECK(Create() == NULL);
    Fixture_Enable_Factory(1U);
    CHECK(Fixture_Alive_Renderers() == 0U);
    CHECK(Fixture_Files_Requested() == Fixture_Files_Returned());

    // A rejected request must not poison the next valid original owner.
    RenegadeMovieSubtitles *owner = Create("ux0:movies\\FiXtUrE.bik");
    CHECK(owner != NULL);
    Present(owner, 60U);
    CHECK(Fixture_Caption_Is("Alpha"));
    Renegade_Movie_Subtitles_Destroy(owner);
}

void Lifecycle()
{
    for (uint32_t cycle = 0U; cycle < 32U; ++cycle) {
        RenegadeMovieSubtitles *owner = Create();
        CHECK(owner != NULL);
        Present(owner, 60U);
        CHECK(Fixture_Caption_Is("Alpha"));
        Renegade_Movie_Subtitles_Destroy(owner);
        CHECK(Fixture_Alive_Renderers() == 0U);
        CHECK(Fixture_Constructed_Renderers() == cycle + 1U);
        CHECK(Fixture_Destroyed_Renderers() == cycle + 1U);
        CHECK(Fixture_Files_Requested() == Fixture_Files_Returned());
        CHECK(Fixture_Font_References(g_font) == 1U);
    }
}

void Font_Retention()
{
    CHECK(Fixture_Font_References(g_font) == 1U);
    RenegadeMovieSubtitles *owner = Create();
    CHECK(owner != NULL);
    CHECK(Fixture_Font_References(g_font) == 2U);
    Fixture_Release_Font(g_font);
    CHECK(Fixture_Font_References(g_font) == 1U);
    CHECK(Fixture_Destroyed_Fonts() == 0U);
    Present(owner, 60U);
    CHECK(Fixture_Caption_Is("Alpha"));
    Renegade_Movie_Subtitles_Destroy(owner);
    CHECK(Fixture_Destroyed_Fonts() == 1U);
    g_font = NULL;
}

void High_Ticks()
{
    RenegadeMovieSubtitles *owner = Create("high.bik");
    CHECK(owner != NULL);
    Present(owner, UINT32_MAX - 16U);
    CHECK(!Fixture_Visible());
    Present(owner, UINT32_MAX - 15U);
    CHECK(Fixture_Caption_Is("High"));
    Present(owner, UINT32_MAX);
    CHECK(Fixture_Visible());
    CHECK(Fixture_Caption_Is("High"));
    Renegade_Movie_Subtitles_Destroy(owner);
}

uint32_t Tick_Oracle(uint64_t microseconds)
{
    const __uint128_t ticks = static_cast<__uint128_t>(microseconds) * 60U / 1000000U;
    return ticks > UINT32_MAX ? UINT32_MAX : static_cast<uint32_t>(ticks);
}

void Tick_Conversion()
{
    const uint64_t saturation = (static_cast<uint64_t>(UINT32_MAX) * 1000000U + 59U) / 60U;
    const uint64_t cases[] = {
        0U, 1U, 16666U, 16667U, 33333U, 33334U, 999999U, 1000000U,
        saturation - 1U, saturation, saturation + 1U,
        UINT64_MAX / 60U, UINT64_MAX / 60U + 1U, UINT64_MAX,
    };
    for (uint64_t microseconds : cases) {
        CHECK(Renegade_Movie_Subtitle_Ticks(microseconds) == Tick_Oracle(microseconds));
    }
    CHECK(Renegade_Movie_Subtitle_Ticks(999999U) == 59U);
    CHECK(Renegade_Movie_Subtitle_Ticks(1000000U) == 60U);
    uint64_t random = UINT64_C(0xC0FFEE193D);
    for (uint32_t index = 0U; index < 10000U; ++index) {
        random = random * UINT64_C(6364136223846793005) + UINT64_C(1442695040888963407);
        const uint64_t microseconds = index % 2U ? random : random % (saturation + 1000000U);
        CHECK(Renegade_Movie_Subtitle_Ticks(microseconds) == Tick_Oracle(microseconds));
    }
}
} // namespace

int main(int argc, char **argv)
{
    CHECK(argc == 3);
    g_font = Fixture_Create_Font();
    Fixture_Begin(argv[2], g_font);
    if (strcmp(argv[1], "schedule") == 0) Schedule();
    else if (strcmp(argv[1], "admission") == 0) Admission();
    else if (strcmp(argv[1], "lifecycle") == 0) Lifecycle();
    else if (strcmp(argv[1], "high-ticks") == 0) High_Ticks();
    else if (strcmp(argv[1], "font-retention") == 0) Font_Retention();
    else if (strcmp(argv[1], "bink-routing") == 0) BinkFixture::Run(argv[2], g_font);
    else if (strcmp(argv[1], "tick-conversion") == 0) Tick_Conversion();
    else CHECK(false);
    Fixture_End();
    if (g_font != NULL) {
        CHECK(Fixture_Font_References(g_font) == 1U);
        Fixture_Release_Font(g_font);
    }
    CHECK(Fixture_Destroyed_Fonts() == 1U);
    printf("movie_subtitle_abi=%s PASS\n", argv[1]);
    return 0;
}

#endif
