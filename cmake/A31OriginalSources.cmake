if(NOT DEFINED RENEGADE_STAGE)
  message(FATAL_ERROR "RENEGADE_STAGE must be defined before A31OriginalSources.cmake")
endif()

# A3.0 remains an independently valid 248-TU static-world closure.  A3.1
# starts by replacing only the temporary scalar gameplay closures with their
# original owning translation units.  Keep this seed explicit and direct: the
# legacy factory registrations in these TUs must not be hidden in an archive.
include("${CMAKE_CURRENT_LIST_DIR}/A30OriginalSources.cmake")

set(RENEGADE_A31_GAMEPLAY_OWNER_SOURCES
  ${RENEGADE_STAGE}/combat/combat.cpp
  ${RENEGADE_STAGE}/combat/gameobjmanager.cpp
  ${RENEGADE_STAGE}/combat/smartgameobj.cpp
  ${RENEGADE_STAGE}/combat/vehicle.cpp
  ${RENEGADE_STAGE}/combat/diaglog.cpp
)
list(LENGTH RENEGADE_A31_GAMEPLAY_OWNER_SOURCES
  RENEGADE_A31_GAMEPLAY_OWNER_SOURCE_COUNT)
if(NOT RENEGADE_A31_GAMEPLAY_OWNER_SOURCE_COUNT EQUAL 5)
  message(FATAL_ERROR
    "A3.1 gameplay-owner source manifest changed unexpectedly: ${RENEGADE_A31_GAMEPLAY_OWNER_SOURCE_COUNT}")
endif()

# The owner TUs expose the complete original virtual GameObj hierarchy at
# link time.  Bring in its immediate serialized/control/timing and local
# object-identity closure as one source-backed cluster; do not replace these
# base classes or their network bookkeeping with Vita-specific stand-ins.
set(RENEGADE_A31_DYNAMIC_RUNTIME_SOURCES
  ${RENEGADE_STAGE}/combat/combatsaveload.cpp
  ${RENEGADE_STAGE}/combat/basegameobj.cpp
  ${RENEGADE_STAGE}/combat/scriptablegameobj.cpp
  ${RENEGADE_STAGE}/combat/damageablegameobj.cpp
  ${RENEGADE_STAGE}/combat/physicalgameobj.cpp
  ${RENEGADE_STAGE}/combat/armedgameobj.cpp
  ${RENEGADE_STAGE}/combat/soldier.cpp
  ${RENEGADE_STAGE}/combat/scriptzone.cpp
  ${RENEGADE_STAGE}/combat/powerup.cpp
  ${RENEGADE_STAGE}/combat/simplegameobj.cpp
  ${RENEGADE_STAGE}/combat/transitiongameobj.cpp
  ${RENEGADE_STAGE}/combat/building.cpp
  ${RENEGADE_STAGE}/combat/control.cpp
  ${RENEGADE_STAGE}/combat/action.cpp
  ${RENEGADE_STAGE}/combat/pathaction.cpp
  ${RENEGADE_STAGE}/combat/animcontrol.cpp
  ${RENEGADE_STAGE}/combat/humanstate.cpp
  ${RENEGADE_STAGE}/combat/weapons.cpp
  ${RENEGADE_STAGE}/combat/weaponbag.cpp
  ${RENEGADE_STAGE}/combat/weaponmanager.cpp
  ${RENEGADE_STAGE}/combat/explosion.cpp
  ${RENEGADE_STAGE}/combat/playerdata.cpp
  ${RENEGADE_STAGE}/combat/clientcontrol.cpp
  ${RENEGADE_STAGE}/combat/timemgr.cpp
  ${RENEGADE_STAGE}/combat/transition.cpp
  ${RENEGADE_STAGE}/wwnet/networkobject.cpp
  ${RENEGADE_STAGE}/wwnet/networkobjectmgr.cpp
  ${RENEGADE_STAGE}/wwnet/networkobjectfactory.cpp
  ${RENEGADE_STAGE}/wwnet/networkobjectfactorymgr.cpp
  ${RENEGADE_STAGE}/wwlib/thread.cpp
  ${RENEGADE_STAGE}/wwlib/FastAllocator.cpp
)
list(LENGTH RENEGADE_A31_DYNAMIC_RUNTIME_SOURCES
  RENEGADE_A31_DYNAMIC_RUNTIME_SOURCE_COUNT)
if(NOT RENEGADE_A31_DYNAMIC_RUNTIME_SOURCE_COUNT EQUAL 31)
  message(FATAL_ERROR
    "A3.1 dynamic-runtime source manifest changed unexpectedly: ${RENEGADE_A31_DYNAMIC_RUNTIME_SOURCE_COUNT}")
endif()

# CombatSaveLoad restores these managers directly from the retail level stream.
# Keep that original serialized graph together with the conversation, encyclopedia,
# map, and camera owners reached by the player hierarchy.  This is not a UI or
# script replacement: it is the next source-authentic dynamic-world closure.
set(RENEGADE_A31_DYNAMIC_LEVEL_SOURCES
  ${RENEGADE_STAGE}/combat/spawn.cpp
  ${RENEGADE_STAGE}/combat/scripts.cpp
	${RENEGADE_STAGE}/combat/scriptcommands.cpp
  ${RENEGADE_STAGE}/combat/persistentgameobjobserver.cpp
  ${RENEGADE_STAGE}/combat/cover.cpp
  ${RENEGADE_STAGE}/combat/objectives.cpp
  ${RENEGADE_STAGE}/combat/radar.cpp
  ${RENEGADE_STAGE}/combat/gameobjobserver.cpp
  ${RENEGADE_STAGE}/combat/bullet.cpp
  ${RENEGADE_STAGE}/combat/weaponview.cpp
  ${RENEGADE_STAGE}/combat/backgroundmgr.cpp
  ${RENEGADE_STAGE}/combat/WeatherMgr.cpp
  ${RENEGADE_STAGE}/combat/hud.cpp
  ${RENEGADE_STAGE}/combat/screenfademanager.cpp
  ${RENEGADE_STAGE}/combat/conversationmgr.cpp
  ${RENEGADE_STAGE}/combat/conversation.cpp
  ${RENEGADE_STAGE}/combat/conversationremark.cpp
  ${RENEGADE_STAGE}/combat/activeconversation.cpp
  ${RENEGADE_STAGE}/combat/orator.cpp
  ${RENEGADE_STAGE}/combat/oratortypes.cpp
  ${RENEGADE_STAGE}/combat/encyclopediamgr.cpp
  ${RENEGADE_STAGE}/combat/mapmgr.cpp
  ${RENEGADE_STAGE}/combat/ccamera.cpp
)
list(LENGTH RENEGADE_A31_DYNAMIC_LEVEL_SOURCES
  RENEGADE_A31_DYNAMIC_LEVEL_SOURCE_COUNT)
if(NOT RENEGADE_A31_DYNAMIC_LEVEL_SOURCE_COUNT EQUAL 23)
  message(FATAL_ERROR
    "A3.1 dynamic-level source manifest changed unexpectedly: ${RENEGADE_A31_DYNAMIC_LEVEL_SOURCE_COUNT}")
endif()

# The first direct gameplay/mission closure proves the dynamic hierarchy has
# reached its real owners.  Retain the original scalar managers, controller
# helpers, HUD sentence classes, and serialized combat events rather than
# replacing their behavior at the Vita boundary.  Audio output itself remains
# separately bounded, but AudioEvents is source-authentic bookkeeping shared by
# SmartGameObj and the original scriptable-object lifecycle.
set(RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCES
  ${RENEGADE_STAGE}/wwlib/jshell.cpp
  ${RENEGADE_STAGE}/wwlib/rndstrng.cpp
  ${RENEGADE_STAGE}/wwlib/vector.cpp
  ${RENEGADE_STAGE}/ww3d2/animatedsoundmgr.cpp
  ${RENEGADE_STAGE}/ww3d2/line3d.cpp
  ${RENEGADE_STAGE}/ww3d2/segline.cpp
  ${RENEGADE_STAGE}/ww3d2/render2d.cpp
  ${RENEGADE_STAGE}/ww3d2/render2dsentence.cpp
  ${RENEGADE_STAGE}/ww3d2/renderobjectrecycler.cpp
  ${RENEGADE_STAGE}/wwtranslatedb/tdbcategory.cpp
  ${RENEGADE_STAGE}/wwtranslatedb/translateobj.cpp
  ${RENEGADE_STAGE}/wwtranslatedb/translatedb.cpp
  ${RENEGADE_STAGE}/wwtranslatedb/stringtwiddler.cpp
  ${RENEGADE_STAGE}/wwaudio/AudioEvents.cpp
  ${RENEGADE_STAGE}/wwaudio/LogicalListener.cpp
  ${RENEGADE_STAGE}/wwaudio/LogicalSound.cpp
  ${RENEGADE_STAGE}/wwaudio/SoundSceneObj.cpp
  ${RENEGADE_STAGE}/combat/assetdep.cpp
  ${RENEGADE_STAGE}/combat/basecontroller.cpp
  ${RENEGADE_STAGE}/combat/beacongameobj.cpp
  ${RENEGADE_STAGE}/combat/bones.cpp
  ${RENEGADE_STAGE}/combat/buildingmonitor.cpp
  ${RENEGADE_STAGE}/combat/c4.cpp
  ${RENEGADE_STAGE}/combat/cheatmgr.cpp
  ${RENEGADE_STAGE}/combat/CNCModeSettings.cpp
  ${RENEGADE_STAGE}/combat/combatmaterialeffectmanager.cpp
  ${RENEGADE_STAGE}/combat/csdamageevent.cpp
  ${RENEGADE_STAGE}/combat/dialogue.cpp
  ${RENEGADE_STAGE}/combat/dynamicspeechanim.cpp
  ${RENEGADE_STAGE}/combat/effectrecycler.cpp
  ${RENEGADE_STAGE}/combat/evasettings.cpp
  ${RENEGADE_STAGE}/combat/gametype.cpp
  ${RENEGADE_STAGE}/combat/globalsettings.cpp
  ${RENEGADE_STAGE}/combat/hudinfo.cpp
  ${RENEGADE_STAGE}/combat/humanrecoil.cpp
  ${RENEGADE_STAGE}/combat/input.cpp
  ${RENEGADE_STAGE}/combat/messagewindow.cpp
  ${RENEGADE_STAGE}/combat/muzzlerecoil.cpp
  ${RENEGADE_STAGE}/combat/objlibrary.cpp
  ${RENEGADE_STAGE}/combat/objectivesviewer.cpp
  ${RENEGADE_STAGE}/combat/pilot.cpp
  ${RENEGADE_STAGE}/combat/playerterminal.cpp
  ${RENEGADE_STAGE}/combat/playertype.cpp
  ${RENEGADE_STAGE}/combat/scexplosionevent.cpp
  ${RENEGADE_STAGE}/combat/soldierobserver.cpp
  ${RENEGADE_STAGE}/combat/surfaceeffects.cpp
  ${RENEGADE_STAGE}/combat/systeminfolog.cpp
  ${RENEGADE_STAGE}/combat/textwindow.cpp
  ${RENEGADE_STAGE}/combat/unitcoordinationzonemgr.cpp
  ${RENEGADE_STAGE}/combat/vehicledriver.cpp
  ${RENEGADE_STAGE}/combat/viseme.cpp
)
list(LENGTH RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCES
  RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCE_COUNT)
if(NOT RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCE_COUNT EQUAL 51)
  message(FATAL_ERROR
    "A3.1 gameplay link-closure manifest changed unexpectedly: ${RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCE_COUNT}")
endif()

# Original WWAudio retains all game-facing sound definition, playlist,
# priority, loop, scene, and callback ownership. The Vita executable selects
# this coherent cluster together with the native provider below the Miles ABI;
# host world-load targets can continue selecting the established lite boundary.
set(RENEGADE_A35_ORIGINAL_AUDIO_SOURCES
  ${RENEGADE_STAGE}/wwaudio/AudibleSound.cpp
  ${RENEGADE_STAGE}/wwaudio/FilteredSound.cpp
  ${RENEGADE_STAGE}/wwaudio/Listener.cpp
  ${RENEGADE_STAGE}/wwaudio/Sound3D.cpp
  ${RENEGADE_STAGE}/wwaudio/SoundBuffer.cpp
  ${RENEGADE_STAGE}/wwaudio/SoundPseudo3D.cpp
  ${RENEGADE_STAGE}/wwaudio/SoundScene.cpp
  ${RENEGADE_STAGE}/wwaudio/Threads.cpp
  ${RENEGADE_STAGE}/wwaudio/Utils.cpp
  ${RENEGADE_STAGE}/wwaudio/WWAudio.cpp
  ${RENEGADE_STAGE}/wwaudio/listenerhandle.cpp
  ${RENEGADE_STAGE}/wwaudio/sound2dhandle.cpp
  ${RENEGADE_STAGE}/wwaudio/sound3dhandle.cpp
  ${RENEGADE_STAGE}/wwaudio/soundhandle.cpp
  ${RENEGADE_STAGE}/wwaudio/soundstreamhandle.cpp
)
list(LENGTH RENEGADE_A35_ORIGINAL_AUDIO_SOURCES
  RENEGADE_A35_ORIGINAL_AUDIO_SOURCE_COUNT)
if(NOT RENEGADE_A35_ORIGINAL_AUDIO_SOURCE_COUNT EQUAL 15)
  message(FATAL_ERROR
    "A3.5 original WWAudio source closure changed unexpectedly: ${RENEGADE_A35_ORIGINAL_AUDIO_SOURCE_COUNT}")
endif()

set(RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCES
  ${RENEGADE_A30_WORLD_ORIGINAL_SOURCES}
  ${RENEGADE_A31_GAMEPLAY_OWNER_SOURCES}
  ${RENEGADE_A31_DYNAMIC_RUNTIME_SOURCES}
  ${RENEGADE_A31_DYNAMIC_LEVEL_SOURCES}
  ${RENEGADE_A31_GAMEPLAY_LINK_CLOSURE_SOURCES}
)
list(LENGTH RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCES
  RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCE_COUNT)
if(NOT RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCE_COUNT EQUAL 358)
  message(FATAL_ERROR
    "A3.1 gameplay seed source closure changed unexpectedly: ${RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCE_COUNT}")
endif()
