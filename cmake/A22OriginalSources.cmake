if(NOT DEFINED RENEGADE_STAGE)
  message(FATAL_ERROR "RENEGADE_STAGE must be defined before A22OriginalSources.cmake")
endif()

# Coherent original EA/Westwood WW3D asset, RenderObj, Scene, and Camera slice.
# Every entry is a staged copy of the pinned canonical source revision.
set(RENEGADE_A22_ORIGINAL_SOURCES
  ${RENEGADE_STAGE}/wwbitpack/BitPacker.cpp
  ${RENEGADE_STAGE}/wwbitpack/bitstream.cpp
  ${RENEGADE_STAGE}/wwbitpack/encoderlist.cpp
  ${RENEGADE_STAGE}/wwbitpack/encodertypeentry.cpp
  ${RENEGADE_STAGE}/wwutil/mathutil.cpp

  ${RENEGADE_STAGE}/wwlib/buff.cpp
  ${RENEGADE_STAGE}/wwlib/bufffile.cpp
  ${RENEGADE_STAGE}/wwlib/chunkio.cpp
  ${RENEGADE_STAGE}/wwlib/crc.cpp
  ${RENEGADE_STAGE}/wwlib/cstraw.cpp
  ${RENEGADE_STAGE}/wwlib/ffactory.cpp
  ${RENEGADE_STAGE}/wwlib/hash.cpp
  ${RENEGADE_STAGE}/wwlib/ini.cpp
  ${RENEGADE_STAGE}/wwlib/mixfile.cpp
  ${RENEGADE_STAGE}/wwlib/multilist.cpp
  ${RENEGADE_STAGE}/wwlib/nstrdup.cpp
  ${RENEGADE_STAGE}/wwlib/random.cpp
  ${RENEGADE_STAGE}/wwlib/rawfile.cpp
  ${RENEGADE_STAGE}/wwlib/readline.cpp
  ${RENEGADE_STAGE}/wwlib/realcrc.cpp
  ${RENEGADE_STAGE}/wwlib/slnode.cpp
  ${RENEGADE_STAGE}/wwlib/straw.cpp
  ${RENEGADE_STAGE}/wwlib/systimer.cpp
  ${RENEGADE_STAGE}/wwlib/trim.cpp
  ${RENEGADE_STAGE}/wwlib/wwfile.cpp
  ${RENEGADE_STAGE}/wwlib/wwstring.cpp
  ${RENEGADE_STAGE}/wwlib/widestring.cpp
  ${RENEGADE_STAGE}/wwlib/xstraw.cpp

  ${RENEGADE_STAGE}/wwmath/aabox.cpp
  ${RENEGADE_STAGE}/wwmath/colmath.cpp
  ${RENEGADE_STAGE}/wwmath/colmathaabox.cpp
  ${RENEGADE_STAGE}/wwmath/colmathaabtri.cpp
  ${RENEGADE_STAGE}/wwmath/colmathfrustum.cpp
  ${RENEGADE_STAGE}/wwmath/colmathline.cpp
  ${RENEGADE_STAGE}/wwmath/colmathobbobb.cpp
  ${RENEGADE_STAGE}/wwmath/colmathobbox.cpp
  ${RENEGADE_STAGE}/wwmath/colmathobbtri.cpp
  ${RENEGADE_STAGE}/wwmath/colmathplane.cpp
  ${RENEGADE_STAGE}/wwmath/colmathsphere.cpp
  ${RENEGADE_STAGE}/wwmath/frustum.cpp
  ${RENEGADE_STAGE}/wwmath/lineseg.cpp
  ${RENEGADE_STAGE}/wwmath/matrix3.cpp
  ${RENEGADE_STAGE}/wwmath/matrix3d.cpp
  ${RENEGADE_STAGE}/wwmath/matrix4.cpp
  ${RENEGADE_STAGE}/wwmath/obbox.cpp
  ${RENEGADE_STAGE}/wwmath/quat.cpp
  ${RENEGADE_STAGE}/wwmath/tri.cpp
  ${RENEGADE_STAGE}/wwmath/vp.cpp
  ${RENEGADE_STAGE}/wwmath/wwmath.cpp

  ${RENEGADE_STAGE}/wwsaveload/persistfactory.cpp
  ${RENEGADE_STAGE}/wwsaveload/pointerremap.cpp
  ${RENEGADE_STAGE}/wwsaveload/saveload.cpp

  ${RENEGADE_STAGE}/combat/ffactorylist.cpp

  ${RENEGADE_STAGE}/ww3d2/aabtree.cpp
  ${RENEGADE_STAGE}/ww3d2/aabtreebuilder.cpp
  ${RENEGADE_STAGE}/ww3d2/agg_def.cpp
  ${RENEGADE_STAGE}/ww3d2/animobj.cpp
  ${RENEGADE_STAGE}/ww3d2/assetmgr.cpp
  ${RENEGADE_STAGE}/ww3d2/assetstatus.cpp
  ${RENEGADE_STAGE}/ww3d2/boxrobj.cpp
  ${RENEGADE_STAGE}/ww3d2/bwrender.cpp
  ${RENEGADE_STAGE}/ww3d2/camera.cpp
  ${RENEGADE_STAGE}/ww3d2/collect.cpp
  ${RENEGADE_STAGE}/ww3d2/coltest.cpp
  ${RENEGADE_STAGE}/ww3d2/composite.cpp
  ${RENEGADE_STAGE}/ww3d2/dazzle.cpp
  ${RENEGADE_STAGE}/ww3d2/decalmsh.cpp
  ${RENEGADE_STAGE}/ww3d2/decalsys.cpp
  ${RENEGADE_STAGE}/ww3d2/distlod.cpp
  ${RENEGADE_STAGE}/ww3d2/hanim.cpp
  ${RENEGADE_STAGE}/ww3d2/hanimmgr.cpp
  ${RENEGADE_STAGE}/ww3d2/hcanim.cpp
  ${RENEGADE_STAGE}/ww3d2/hlod.cpp
  ${RENEGADE_STAGE}/ww3d2/hmdldef.cpp
  ${RENEGADE_STAGE}/ww3d2/hmorphanim.cpp
  ${RENEGADE_STAGE}/ww3d2/hrawanim.cpp
  ${RENEGADE_STAGE}/ww3d2/htree.cpp
  ${RENEGADE_STAGE}/ww3d2/htreemgr.cpp
  ${RENEGADE_STAGE}/ww3d2/mapper.cpp
  ${RENEGADE_STAGE}/ww3d2/matpass.cpp
  ${RENEGADE_STAGE}/ww3d2/matinfo.cpp
  ${RENEGADE_STAGE}/ww3d2/matrixmapper.cpp
  ${RENEGADE_STAGE}/ww3d2/metalmap.cpp
  ${RENEGADE_STAGE}/ww3d2/mesh.cpp
  ${RENEGADE_STAGE}/ww3d2/meshgeometry.cpp
  ${RENEGADE_STAGE}/ww3d2/meshmatdesc.cpp
  ${RENEGADE_STAGE}/ww3d2/meshmdl.cpp
  ${RENEGADE_STAGE}/ww3d2/meshmdlio.cpp
  ${RENEGADE_STAGE}/ww3d2/motchan.cpp
  ${RENEGADE_STAGE}/ww3d2/nullrobj.cpp
  ${RENEGADE_STAGE}/ww3d2/pivot.cpp
  ${RENEGADE_STAGE}/ww3d2/predlod.cpp
  ${RENEGADE_STAGE}/ww3d2/projector.cpp
  ${RENEGADE_STAGE}/ww3d2/proto.cpp
  ${RENEGADE_STAGE}/ww3d2/rendobj.cpp
  ${RENEGADE_STAGE}/ww3d2/rinfo.cpp
  ${RENEGADE_STAGE}/ww3d2/scene.cpp
  ${RENEGADE_STAGE}/ww3d2/shader.cpp
  ${RENEGADE_STAGE}/ww3d2/snappts.cpp
  ${RENEGADE_STAGE}/ww3d2/texture.cpp
  ${RENEGADE_STAGE}/ww3d2/texproject.cpp
  ${RENEGADE_STAGE}/ww3d2/vertmaterial.cpp
  ${RENEGADE_STAGE}/ww3d2/visrasterizer.cpp
  ${RENEGADE_STAGE}/ww3d2/w3d_util.cpp
  ${RENEGADE_STAGE}/ww3d2/ww3d.cpp
)

list(LENGTH RENEGADE_A22_ORIGINAL_SOURCES RENEGADE_A22_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A22_ORIGINAL_SOURCE_COUNT EQUAL 105)
  message(FATAL_ERROR
    "A2.2 original source manifest changed unexpectedly: ${RENEGADE_A22_ORIGINAL_SOURCE_COUNT}")
endif()
