cmake_minimum_required(VERSION 3.16)
project(RenegadeA22HostValidation LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

get_filename_component(RV_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include("${RV_ROOT}/cmake/RenegadeCcache.cmake")
set(RV_STAGE "${RV_ROOT}/staging")
set(RV_UPSTREAM "${RV_ROOT}/upstream/CnC_Renegade")
set(RV_COMPAT "${RV_ROOT}/port/compatibility/include")
set(RENEGADE_STAGE "${RV_STAGE}")

set(RV_ORIGINAL_SOURCES
  ${RV_STAGE}/wwbitpack/BitPacker.cpp
  ${RV_STAGE}/wwbitpack/bitstream.cpp
  ${RV_STAGE}/wwbitpack/encoderlist.cpp
  ${RV_STAGE}/wwbitpack/encodertypeentry.cpp
  ${RV_STAGE}/wwutil/mathutil.cpp

  ${RV_STAGE}/wwlib/buff.cpp
  ${RV_STAGE}/wwlib/bufffile.cpp
  ${RV_STAGE}/wwlib/chunkio.cpp
  ${RV_STAGE}/wwlib/crc.cpp
  ${RV_STAGE}/wwlib/cstraw.cpp
  ${RV_STAGE}/wwlib/ffactory.cpp
  ${RV_STAGE}/wwlib/hash.cpp
  ${RV_STAGE}/wwlib/ini.cpp
  ${RV_STAGE}/wwlib/mixfile.cpp
  ${RV_STAGE}/wwlib/multilist.cpp
  ${RV_STAGE}/wwlib/nstrdup.cpp
  ${RV_STAGE}/wwlib/random.cpp
  ${RV_STAGE}/wwlib/rawfile.cpp
  ${RV_STAGE}/wwlib/readline.cpp
  ${RV_STAGE}/wwlib/realcrc.cpp
  ${RV_STAGE}/wwlib/slnode.cpp
  ${RV_STAGE}/wwlib/straw.cpp
  ${RV_STAGE}/wwlib/systimer.cpp
  ${RV_STAGE}/wwlib/trim.cpp
  ${RV_STAGE}/wwlib/wwfile.cpp
  ${RV_STAGE}/wwlib/wwstring.cpp
  ${RV_STAGE}/wwlib/widestring.cpp
  ${RV_STAGE}/wwlib/xstraw.cpp

  ${RV_STAGE}/wwmath/aabox.cpp
  ${RV_STAGE}/wwmath/colmath.cpp
  ${RV_STAGE}/wwmath/colmathaabox.cpp
  ${RV_STAGE}/wwmath/colmathaabtri.cpp
  ${RV_STAGE}/wwmath/colmathfrustum.cpp
  ${RV_STAGE}/wwmath/colmathline.cpp
  ${RV_STAGE}/wwmath/colmathobbobb.cpp
  ${RV_STAGE}/wwmath/colmathobbox.cpp
  ${RV_STAGE}/wwmath/colmathobbtri.cpp
  ${RV_STAGE}/wwmath/colmathplane.cpp
  ${RV_STAGE}/wwmath/colmathsphere.cpp
  ${RV_STAGE}/wwmath/frustum.cpp
  ${RV_STAGE}/wwmath/lineseg.cpp
  ${RV_STAGE}/wwmath/matrix3.cpp
  ${RV_STAGE}/wwmath/matrix3d.cpp
  ${RV_STAGE}/wwmath/matrix4.cpp
  ${RV_STAGE}/wwmath/obbox.cpp
  ${RV_STAGE}/wwmath/quat.cpp
  ${RV_STAGE}/wwmath/tri.cpp
  ${RV_STAGE}/wwmath/vp.cpp
  ${RV_STAGE}/wwmath/wwmath.cpp

  ${RV_STAGE}/wwsaveload/persistfactory.cpp
  ${RV_STAGE}/wwsaveload/pointerremap.cpp
  ${RV_STAGE}/wwsaveload/saveload.cpp

  ${RV_STAGE}/combat/ffactorylist.cpp

  ${RV_STAGE}/ww3d2/aabtree.cpp
  ${RV_STAGE}/ww3d2/aabtreebuilder.cpp
  ${RV_STAGE}/ww3d2/agg_def.cpp
  ${RV_STAGE}/ww3d2/animobj.cpp
  ${RV_STAGE}/ww3d2/assetmgr.cpp
  ${RV_STAGE}/ww3d2/assetstatus.cpp
  ${RV_STAGE}/ww3d2/boxrobj.cpp
  ${RV_STAGE}/ww3d2/bwrender.cpp
  ${RV_STAGE}/ww3d2/camera.cpp
  ${RV_STAGE}/ww3d2/collect.cpp
  ${RV_STAGE}/ww3d2/coltest.cpp
  ${RV_STAGE}/ww3d2/composite.cpp
  ${RV_STAGE}/ww3d2/dazzle.cpp
  ${RV_STAGE}/ww3d2/decalmsh.cpp
  ${RV_STAGE}/ww3d2/decalsys.cpp
  ${RV_STAGE}/ww3d2/distlod.cpp
  ${RV_STAGE}/ww3d2/hanim.cpp
  ${RV_STAGE}/ww3d2/hanimmgr.cpp
  ${RV_STAGE}/ww3d2/hcanim.cpp
  ${RV_STAGE}/ww3d2/hlod.cpp
  ${RV_STAGE}/ww3d2/hmdldef.cpp
  ${RV_STAGE}/ww3d2/hmorphanim.cpp
  ${RV_STAGE}/ww3d2/hrawanim.cpp
  ${RV_STAGE}/ww3d2/htree.cpp
  ${RV_STAGE}/ww3d2/htreemgr.cpp
  ${RV_STAGE}/ww3d2/mapper.cpp
  ${RV_STAGE}/ww3d2/matpass.cpp
  ${RV_STAGE}/ww3d2/matinfo.cpp
  ${RV_STAGE}/ww3d2/matrixmapper.cpp
  ${RV_STAGE}/ww3d2/metalmap.cpp
  ${RV_STAGE}/ww3d2/mesh.cpp
  ${RV_STAGE}/ww3d2/meshgeometry.cpp
  ${RV_STAGE}/ww3d2/meshmatdesc.cpp
  ${RV_STAGE}/ww3d2/meshmdl.cpp
  ${RV_STAGE}/ww3d2/meshmdlio.cpp
  ${RV_STAGE}/ww3d2/motchan.cpp
  ${RV_STAGE}/ww3d2/nullrobj.cpp
  ${RV_STAGE}/ww3d2/pivot.cpp
  ${RV_STAGE}/ww3d2/predlod.cpp
  ${RV_STAGE}/ww3d2/projector.cpp
  ${RV_STAGE}/ww3d2/proto.cpp
  ${RV_STAGE}/ww3d2/rendobj.cpp
  ${RV_STAGE}/ww3d2/rinfo.cpp
  ${RV_STAGE}/ww3d2/scene.cpp
  ${RV_STAGE}/ww3d2/shader.cpp
  ${RV_STAGE}/ww3d2/snappts.cpp
  ${RV_STAGE}/ww3d2/texture.cpp
  ${RV_STAGE}/ww3d2/texproject.cpp
  ${RV_STAGE}/ww3d2/vertmaterial.cpp
  ${RV_STAGE}/ww3d2/visrasterizer.cpp
  ${RV_STAGE}/ww3d2/w3d_util.cpp
  ${RV_STAGE}/ww3d2/ww3d.cpp
)

include("${RV_ROOT}/cmake/A22OriginalSources.cmake")
if(NOT "${RV_ORIGINAL_SOURCES}" STREQUAL "${RENEGADE_A22_ORIGINAL_SOURCES}")
  message(FATAL_ERROR "Host source list diverged from the canonical A2.2 manifest")
endif()

add_executable(a22_asset_selftest
  ${RENEGADE_A22_ORIGINAL_SOURCES}
  # A3.1.5 makes the established TextureClass boundary execute the original
  # DDS loader.  Keep the accepted A2.2 manifest unchanged while adding this
  # direct texture dependency to the host asset-validation closure.  The
  # current AssetManager/WW3D sources also retain their original Font3D and
  # Render2D references even when this retained A2.2 test does not render
  # text; link their existing owners and the shared Vita font/surface boundary
  # so deterministic restaging cannot make the regression target incomplete.
  ${RV_STAGE}/ww3d2/ddsfile.cpp
  ${RV_STAGE}/ww3d2/formconv.cpp
  ${RV_STAGE}/ww3d2/font3d.cpp
  ${RV_STAGE}/ww3d2/render2d.cpp
  ${RV_STAGE}/ww3d2/render2dsentence.cpp
  ${RV_STAGE}/wwlib/TARGA.CPP
  ${RV_STAGE}/ww3d2/bitmaphandler.cpp
  ${RV_STAGE}/ww3d2/ww3dformat.cpp
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/renegade_freetype_font_provider.cpp
  ${RV_ROOT}/port/validation/wwbitpack_selftest.cpp
  ${RV_ROOT}/port/validation/a21_filesystem_selftest.cpp
  ${RV_ROOT}/port/validation/a22_w3d_selftest.cpp
  ${RV_ROOT}/port/validation/host_selftest_main.cpp
)

target_include_directories(a22_asset_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  /usr/local/vitasdk/arm-vita-eabi/include/freetype2
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/validation
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
)

target_compile_definitions(a22_asset_selftest PRIVATE
  NDEBUG=1
  _UNIX=1
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
)
target_compile_options(a22_asset_selftest PRIVATE
  -O1 -g
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_link_options(a22_asset_selftest PRIVATE -Wl,--gc-sections)
set(RV_A22_HOST_FREETYPE "/usr/lib/x86_64-linux-gnu/libfreetype.so.6")
if(NOT EXISTS "${RV_A22_HOST_FREETYPE}")
  message(FATAL_ERROR "Host FreeType runtime library is required for the A2.2 asset regression")
endif()
target_link_libraries(a22_asset_selftest PRIVATE m pthread "${RV_A22_HOST_FREETYPE}")
