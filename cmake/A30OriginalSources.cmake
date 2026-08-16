if(NOT DEFINED RENEGADE_STAGE)
  message(FATAL_ERROR "RENEGADE_STAGE must be defined before A30OriginalSources.cmake")
endif()

include("${CMAKE_CURRENT_LIST_DIR}/A22OriginalSources.cmake")

# Complete original EA/Westwood WWPhys runtime module. This is the exact 93-TU
# source list in the pinned revision's Code/wwphys/wwphys.dsp. The separately
# present PathfindSectorBuilder.cpp is a LevelEdit-only implementation and is
# deliberately not part of the original runtime project.
set(RENEGADE_A30_WWPHYS_SOURCES
  ${RENEGADE_STAGE}/wwphys/accessiblephys.cpp
  ${RENEGADE_STAGE}/wwphys/animcollisionmanager.cpp
  ${RENEGADE_STAGE}/wwphys/bpt.cpp
  ${RENEGADE_STAGE}/wwphys/camerashakesystem.cpp
  ${RENEGADE_STAGE}/wwphys/decophys.cpp
  ${RENEGADE_STAGE}/wwphys/dynamicaabtreecull.cpp
  ${RENEGADE_STAGE}/wwphys/dynamicanimphys.cpp
  ${RENEGADE_STAGE}/wwphys/dynamicphys.cpp
  ${RENEGADE_STAGE}/wwphys/dynamicshadowmanager.cpp
  ${RENEGADE_STAGE}/wwphys/dyntexproject.cpp
  ${RENEGADE_STAGE}/wwphys/floodfillbox.cpp
  ${RENEGADE_STAGE}/wwphys/floodfillgrid.cpp
  ${RENEGADE_STAGE}/wwphys/grideffect.cpp
  ${RENEGADE_STAGE}/wwphys/heightdb.cpp
  ${RENEGADE_STAGE}/wwphys/humanphys.cpp
  ${RENEGADE_STAGE}/wwphys/lightcull.cpp
  ${RENEGADE_STAGE}/wwphys/lightphys.cpp
  ${RENEGADE_STAGE}/wwphys/lightsolve.cpp
  ${RENEGADE_STAGE}/wwphys/lightsolvecontext.cpp
  ${RENEGADE_STAGE}/wwphys/materialeffect.cpp
  ${RENEGADE_STAGE}/wwphys/motorcycle.cpp
  ${RENEGADE_STAGE}/wwphys/motorvehicle.cpp
  ${RENEGADE_STAGE}/wwphys/movephys.cpp
  ${RENEGADE_STAGE}/wwphys/octbox.cpp
  ${RENEGADE_STAGE}/wwphys/Path.cpp
  ${RENEGADE_STAGE}/wwphys/PathDebugPlotter.cpp
  ${RENEGADE_STAGE}/wwphys/Pathfind.cpp
  ${RENEGADE_STAGE}/wwphys/pathfindbox.cpp
  ${RENEGADE_STAGE}/wwphys/PathfindPortal.cpp
  ${RENEGADE_STAGE}/wwphys/PathfindSector.cpp
  ${RENEGADE_STAGE}/wwphys/pathmgr.cpp
  ${RENEGADE_STAGE}/wwphys/pathnode.cpp
  ${RENEGADE_STAGE}/wwphys/PathObject.cpp
  ${RENEGADE_STAGE}/wwphys/pathsolve.cpp
  ${RENEGADE_STAGE}/wwphys/phys.cpp
  ${RENEGADE_STAGE}/wwphys/phys3.cpp
  ${RENEGADE_STAGE}/wwphys/physaabtreecull.cpp
  ${RENEGADE_STAGE}/wwphys/physcon.cpp
  ${RENEGADE_STAGE}/wwphys/physcontrol.cpp
  ${RENEGADE_STAGE}/wwphys/physdecalsys.cpp
  ${RENEGADE_STAGE}/wwphys/physdynamicsavesystem.cpp
  ${RENEGADE_STAGE}/wwphys/physgridcull.cpp
  ${RENEGADE_STAGE}/wwphys/physresourcemgr.cpp
  ${RENEGADE_STAGE}/wwphys/physstaticsavesystem.cpp
  ${RENEGADE_STAGE}/wwphys/phystexproject.cpp
  ${RENEGADE_STAGE}/wwphys/progcall.cpp
  ${RENEGADE_STAGE}/wwphys/projectile.cpp
  ${RENEGADE_STAGE}/wwphys/projectormanager.cpp
  ${RENEGADE_STAGE}/wwphys/pscene.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_collision.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_decal.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_lighting.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_projectors.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_saveload.cpp
  ${RENEGADE_STAGE}/wwphys/pscene_vis.cpp
  ${RENEGADE_STAGE}/wwphys/rbody.cpp
  ${RENEGADE_STAGE}/wwphys/rbody_obsolete.cpp
  ${RENEGADE_STAGE}/wwphys/renderobjphys.cpp
  ${RENEGADE_STAGE}/wwphys/renegadeterrainmaterialpass.cpp
  ${RENEGADE_STAGE}/wwphys/renegadeterrainpatch.cpp
  ${RENEGADE_STAGE}/wwphys/ridermanager.cpp
  ${RENEGADE_STAGE}/wwphys/shakeablestaticphys.cpp
  ${RENEGADE_STAGE}/wwphys/staticaabtreecull.cpp
  ${RENEGADE_STAGE}/wwphys/staticanimphys.cpp
  ${RENEGADE_STAGE}/wwphys/staticphys.cpp
  ${RENEGADE_STAGE}/wwphys/stealtheffect.cpp
  ${RENEGADE_STAGE}/wwphys/terrainmaterial.cpp
  ${RENEGADE_STAGE}/wwphys/timeddecophys.cpp
  ${RENEGADE_STAGE}/wwphys/trackedvehicle.cpp
  ${RENEGADE_STAGE}/wwphys/transitioneffect.cpp
  ${RENEGADE_STAGE}/wwphys/umbrasupport.cpp
  ${RENEGADE_STAGE}/wwphys/vehicledazzle.cpp
  ${RENEGADE_STAGE}/wwphys/vehiclephys.cpp
  ${RENEGADE_STAGE}/wwphys/visoptimizationcontext.cpp
  ${RENEGADE_STAGE}/wwphys/visoptprogress.cpp
  ${RENEGADE_STAGE}/wwphys/visrendercontext.cpp
  ${RENEGADE_STAGE}/wwphys/vissample.cpp
  ${RENEGADE_STAGE}/wwphys/vissectorstats.cpp
  ${RENEGADE_STAGE}/wwphys/vistable.cpp
  ${RENEGADE_STAGE}/wwphys/vistablemgr.cpp
  ${RENEGADE_STAGE}/wwphys/vtolvehicle.cpp
  ${RENEGADE_STAGE}/wwphys/waypath.cpp
  ${RENEGADE_STAGE}/wwphys/waypoint.cpp
  ${RENEGADE_STAGE}/wwphys/wheel.cpp
  ${RENEGADE_STAGE}/wwphys/wheelvehicle.cpp
  ${RENEGADE_STAGE}/wwphys/wwphys.cpp
  ${RENEGADE_STAGE}/wwphys/bin_aabox.cpp
  ${RENEGADE_STAGE}/wwphys/bin_axes.cpp
  ${RENEGADE_STAGE}/wwphys/bin_obbox.cpp
  ${RENEGADE_STAGE}/wwphys/bin_point.cpp
  ${RENEGADE_STAGE}/wwphys/bin_vector.cpp
  ${RENEGADE_STAGE}/wwphys/widgets.cpp
  ${RENEGADE_STAGE}/wwphys/widgetuser.cpp
)

list(LENGTH RENEGADE_A30_WWPHYS_SOURCES RENEGADE_A30_WWPHYS_SOURCE_COUNT)
if(NOT RENEGADE_A30_WWPHYS_SOURCE_COUNT EQUAL 93)
  message(FATAL_ERROR
    "A3.0 WWPhys source manifest changed unexpectedly: ${RENEGADE_A30_WWPHYS_SOURCE_COUNT}")
endif()

# Original release-mode WWSaveLoad definition/database closure. The first
# three translation units are already part of the A2.2 manifest; the eight
# additional units complete the real DefinitionMgr/factory/Twiddler lifecycle.
# parameter.cpp is intentionally excluded: PARAM_EDITING_ON is disabled in the
# retail runtime, so editable.h compiles all editor-parameter declarations out.
set(RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCES
  ${RENEGADE_STAGE}/wwsaveload/saveloadsubsystem.cpp
  ${RENEGADE_STAGE}/wwsaveload/saveloadstatus.cpp
  ${RENEGADE_STAGE}/wwsaveload/definition.cpp
  ${RENEGADE_STAGE}/wwsaveload/definitionmgr.cpp
  ${RENEGADE_STAGE}/wwsaveload/definitionfactory.cpp
  ${RENEGADE_STAGE}/wwsaveload/definitionfactorymgr.cpp
  ${RENEGADE_STAGE}/wwsaveload/twiddler.cpp
  ${RENEGADE_STAGE}/wwsaveload/wwsaveload.cpp
)
list(LENGTH
  RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCES
  RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCE_COUNT)
if(NOT RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCE_COUNT EQUAL 8)
  message(FATAL_ERROR
    "A3.0 additional WWSaveLoad definition source manifest changed unexpectedly: ${RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCE_COUNT}")
endif()

set(RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCES
  ${RENEGADE_STAGE}/wwsaveload/saveload.cpp
  ${RENEGADE_STAGE}/wwsaveload/persistfactory.cpp
  ${RENEGADE_STAGE}/wwsaveload/pointerremap.cpp
  ${RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCES}
)
list(LENGTH
  RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCES
  RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCE_COUNT)
if(NOT RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCE_COUNT EQUAL 11)
  message(FATAL_ERROR
    "A3.0 WWSaveLoad definition closure changed unexpectedly: ${RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCE_COUNT}")
endif()

set(RENEGADE_A30_ORIGINAL_SOURCES
  ${RENEGADE_A22_ORIGINAL_SOURCES}
  ${RENEGADE_A30_WWPHYS_SOURCES}
  ${RENEGADE_A30_WWSAVELOAD_DEFINITION_ADDITIONAL_SOURCES}
  ${RENEGADE_STAGE}/ww3d2/dx8fvf.cpp
  ${RENEGADE_STAGE}/ww3d2/dx8vertexbuffer.cpp
  ${RENEGADE_STAGE}/ww3d2/dx8indexbuffer.cpp
)
list(LENGTH RENEGADE_A30_ORIGINAL_SOURCES RENEGADE_A30_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A30_ORIGINAL_SOURCE_COUNT EQUAL 209)
  message(FATAL_ERROR
    "A3.0 original source manifest changed unexpectedly: ${RENEGADE_A30_ORIGINAL_SOURCE_COUNT}")
endif()

# First coherent Combat world-factory slice.  These are the original runtime
# implementations required to register and restore the M00 static object
# types, initialize the retail armor/warhead database, and preserve the
# original SaveGameManager level-load facade.  Keeping this list separate lets
# the 209-TU DefinitionMgr/WWPhys runtime proof stay independently linkable
# while the remaining Combat/Commando closure is discovered at the linker.
set(RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCES
  ${RENEGADE_STAGE}/combat/assets.cpp
  ${RENEGADE_STAGE}/combat/damage.cpp
  ${RENEGADE_STAGE}/combat/reflist.cpp
  ${RENEGADE_STAGE}/combat/buildingstate.cpp
  ${RENEGADE_STAGE}/combat/doors.cpp
  ${RENEGADE_STAGE}/combat/elevator.cpp
  ${RENEGADE_STAGE}/combat/damageablestaticphys.cpp
  ${RENEGADE_STAGE}/combat/buildingaggregate.cpp
  ${RENEGADE_STAGE}/combat/savegame.cpp
)
list(LENGTH RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCES
  RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCE_COUNT)
if(NOT RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCE_COUNT EQUAL 9)
  message(FATAL_ERROR
    "A3.0 Combat world-factory manifest changed unexpectedly: ${RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCE_COUNT}")
endif()

# Original DataSafe remains part of the game runtime.  Only its multiplayer
# chat/reporting side effect is redirected at the optional-services boundary;
# the original encryption, shuffling, handles, checksums, and random source are
# compiled unchanged apart from explicit ILP32-width portability patches.
set(RENEGADE_A30_DATASAFE_ORIGINAL_SOURCES
  ${RENEGADE_STAGE}/commando/datasafe.cpp
  ${RENEGADE_STAGE}/combat/crandom.cpp
)
list(LENGTH RENEGADE_A30_DATASAFE_ORIGINAL_SOURCES
  RENEGADE_A30_DATASAFE_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A30_DATASAFE_ORIGINAL_SOURCE_COUNT EQUAL 2)
  message(FATAL_ERROR
    "A3.0 DataSafe source manifest changed unexpectedly: ${RENEGADE_A30_DATASAFE_ORIGINAL_SOURCE_COUNT}")
endif()

set(RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCES
  ${RENEGADE_A30_ORIGINAL_SOURCES}
  ${RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCES}
  ${RENEGADE_A30_DATASAFE_ORIGINAL_SOURCES}
)
list(LENGTH RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCES
  RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCE_COUNT EQUAL 220)
  message(FATAL_ERROR
    "A3.0 aggregate compile-frontier manifest changed unexpectedly: ${RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCE_COUNT}")
endif()

# Exact original dependencies added by the live M00 static-world load and
# render target. These remain direct objects in each executable: SaveLoad and
# Phys factories register through translation-unit static initializers, so an
# ordinary archive could discard them before their registration executes.
set(RENEGADE_A30_WORLD_WWMATH_SOURCES
  ${RENEGADE_STAGE}/wwmath/aabtreecull.cpp
  ${RENEGADE_STAGE}/wwmath/cardinalspline.cpp
  ${RENEGADE_STAGE}/wwmath/catmullromspline.cpp
  ${RENEGADE_STAGE}/wwmath/cullsys.cpp
  ${RENEGADE_STAGE}/wwmath/curve.cpp
  ${RENEGADE_STAGE}/wwmath/euler.cpp
  ${RENEGADE_STAGE}/wwmath/gridcull.cpp
  ${RENEGADE_STAGE}/wwmath/hermitespline.cpp
  ${RENEGADE_STAGE}/wwmath/lookuptable.cpp
  ${RENEGADE_STAGE}/wwmath/ode.cpp
  ${RENEGADE_STAGE}/wwmath/pot.cpp
  ${RENEGADE_STAGE}/wwmath/tcbspline.cpp
  ${RENEGADE_STAGE}/wwmath/v3_rnd.cpp
  ${RENEGADE_STAGE}/wwmath/vehiclecurve.cpp
)

set(RENEGADE_A30_WORLD_LINK_SOURCES
  ${RENEGADE_STAGE}/wwlib/gcd_lcm.cpp
  ${RENEGADE_STAGE}/wwlib/lzo.cpp
  ${RENEGADE_STAGE}/wwlib/lzo1x_c.cpp
  ${RENEGADE_STAGE}/wwlib/lzo1x_d.cpp
  ${RENEGADE_STAGE}/ww3d2/dynamesh.cpp
  ${RENEGADE_STAGE}/ww3d2/light.cpp
  ${RENEGADE_STAGE}/ww3d2/lightenvironment.cpp
  ${RENEGADE_STAGE}/ww3d2/linegrp.cpp
  ${RENEGADE_STAGE}/ww3d2/part_buf.cpp
  ${RENEGADE_STAGE}/ww3d2/part_emt.cpp
  ${RENEGADE_STAGE}/ww3d2/part_ldr.cpp
  ${RENEGADE_STAGE}/ww3d2/pointgr.cpp
  ${RENEGADE_STAGE}/ww3d2/seglinerenderer.cpp
  ${RENEGADE_STAGE}/ww3d2/shattersystem.cpp
)

set(RENEGADE_A30_WORLD_ORIGINAL_SOURCES
  ${RENEGADE_A30_COMPILE_FRONTIER_ORIGINAL_SOURCES}
  ${RENEGADE_A30_WORLD_WWMATH_SOURCES}
  ${RENEGADE_A30_WORLD_LINK_SOURCES}
)
list(LENGTH RENEGADE_A30_WORLD_ORIGINAL_SOURCES
  RENEGADE_A30_WORLD_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A30_WORLD_ORIGINAL_SOURCE_COUNT EQUAL 248)
  message(FATAL_ERROR
    "A3.0 M00 world source closure changed unexpectedly: ${RENEGADE_A30_WORLD_ORIGINAL_SOURCE_COUNT}")
endif()
