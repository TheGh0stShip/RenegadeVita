"""Asset-free source-contract checks for letterbox/fade presentation.

These checks pin the facts established by reports/campaign/CINEMATIC_PRESENTATION.md.
They read staged/port sources only; they do not build, launch, or prove visual
correctness.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding='utf-8', errors='replace')


def body(text, signature):
    """Return the brace-balanced body that follows `signature`."""
    start = text.index(signature)
    open_brace = text.index('{', start)
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
    raise AssertionError('unbalanced body for ' + signature)


class CinematicPresentationContractTest(unittest.TestCase):
    def test_fade_renders_last_inside_gameplay_hud_scope(self):
        render = body(source('staging/combat/combat.cpp'),
                      'void CombatManager::Render()')
        begin = render.index('A31_Vita_Begin_Original_HUD_Render')
        hud = render.index('HUDClass::Render()')
        fade = render.index('ScreenFadeManager::Render()')
        end = render.index('A31_Vita_End_Original_HUD_Render')
        self.assertLess(begin, hud)
        self.assertLess(hud, fade)
        self.assertLess(fade, end)

    def test_hud_scope_uses_full_native_display_rect(self):
        text = source('port/platform/a31_gameplay_boundary.cpp')
        rect = body(text, 'A31NativeHUDPresentationRect Build_A31_Gameplay_HUD_Presentation_Rect()')
        self.assertIsNotNone(re.search(
            r'0U,\s*0U,\s*RenegadeVitaRenderer::DISPLAY_WIDTH,\s*RenegadeVitaRenderer::DISPLAY_HEIGHT',
            rect))

    def test_fade_quads_are_resolution_independent_and_cover_ndc(self):
        text = source('staging/combat/screenfademanager.cpp')
        init = body(text, 'void\tScreenFadeManager::Init()')
        # The final range wins: fade geometry is authored in normalized 0..1 space.
        self.assertTrue(init.rstrip().endswith('}'))
        self.assertLess(init.index('Get_Screen_Resolution'),
                        init.index('RectClass(0,0,1,1)'))
        think = body(text, 'void ScreenFadeManager::Think()')
        self.assertIn('RectClass(-1.0f,-1.0f,1.0f,1.0f)', think)
        self.assertIn('RectClass(0.0f,0.0f,1.0f,lsize)', think)
        self.assertIn('RectClass(0.0f,1.0f - lsize,1.0f,1.0f)', think)

    def test_level_load_resets_letterbox_and_overlay_opacity(self):
        pre_load = body(source('staging/combat/combat.cpp'),
                        'void\tCombatManager::Pre_Load_Level( bool render_available )')
        self.assertIn('ScreenFadeManager::Enable_Letterbox( 0, 0 )', pre_load)
        self.assertIn('ScreenFadeManager::Set_Screen_Overlay_Opacity( 0, 0 )', pre_load)
        self.assertIn('HUDClass::Enable( true )', pre_load)

    def test_unload_level_releases_cinematic_camera_state(self):
        unload = body(source('staging/combat/combat.cpp'),
                      'void\tCombatManager::Unload_Level( void )')
        self.assertIn('MainCamera->Set_Host_Model(NULL)', unload)
        self.assertIn('GameObjManager::Activate_Cinematic_Freeze(false)', unload)

    def test_screen_uv_bias_is_not_enabled_on_vita(self):
        # Half-pixel bias is a D3D8 pixel-center convention; with GL pixel
        # centers it would leave a sliver along the right/bottom letterbox edge.
        ww3d = source('staging/ww3d2/ww3d.cpp')
        self.assertIsNotNone(re.search(r'WW3D::IsScreenUVBiased\s*=\s*false;', ww3d))
        for cmake_path in ('CMakeLists.txt', 'cmake/A22OriginalSources.cmake',
                           'cmake/A30OriginalSources.cmake', 'cmake/A31OriginalSources.cmake',
                           'cmake/A35MultiplayerBuildingSources.cmake'):
            self.assertNotRegex(source(cmake_path), r'commando/console\.cpp')
        for path in ('port/platform/a31_gameplay_boundary.cpp',
                     'port/platform/vita/a31_vita_runtime.cpp',
                     'port/renderer/vita/ww3d_dx8_boundary.cpp'):
            self.assertNotIn('Set_Screen_UV_Bias', source(path))

    def test_render2d_uses_full_device_viewport_without_scissor(self):
        render2d = body(source('staging/ww3d2/render2d.cpp'), 'void Render2DClass::Render(void)')
        self.assertIn('WW3D::Get_Device_Resolution', render2d)
        self.assertIn('vp.Width\t\t= width', render2d)
        renderer = source('port/renderer/vita/ww3d_vita_renderer.cpp')
        self.assertNotIn('glScissor', renderer)
        self.assertNotIn('GL_SCISSOR_TEST', renderer)

    def test_script_commands_route_to_screen_fade_manager(self):
        text = source('staging/combat/scriptcommands.cpp')
        self.assertIn('ScreenFadeManager::Enable_Letterbox(onoff,seconds)', text)
        self.assertIn('ScreenFadeManager::Set_Screen_Overlay_Color(r,g,b,seconds)', text)
        self.assertIn('ScreenFadeManager::Set_Screen_Overlay_Opacity(opacity,seconds)', text)


if __name__ == '__main__':
    unittest.main()
