# Shared compiler-cache policy for every native-ext4 CMake build tree.  Keep
# this in project configuration rather than relying on PATH wrappers so host
# validation and the cross-compiled Vita target are both observable and
# reproducible from their respective CMakeCache.txt files.
option(RENEGADE_USE_CCACHE "Use ccache for native-ext4 build trees when available" ON)

# The managed environment can mount the host user's default ccache location
# read-only. Keep the cache next to native build output instead. This also
# avoids WSL /mnt/c metadata and clock-skew penalties.
get_filename_component(RENEGADE_CCACHE_ROOT "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(RENEGADE_CCACHE_DIR "${RENEGADE_CCACHE_ROOT}/build/ccache" CACHE PATH
  "Native-ext4 ccache directory shared by Renegade CMake build trees")

# Opt-in build-time knobs (docs: reports/tutorial/TUT_R1_BUILD_COMPILE_TIME.md).
# Each is read from the environment at configure time and wins over the cache
# value, so tools/build.sh and tools/build_fast_candidate.sh need no extra -D.
# Unset (the default) keeps the historical per-tree behaviour byte-for-byte.
#
# RENEGADE_CCACHE_DIR=<absolute path>
#   Store results in one cache shared by several worktrees. Only the storage
#   location changes; compile commands and objects do not.
set(RENEGADE_CCACHE_EFFECTIVE_DIR "${RENEGADE_CCACHE_DIR}")
set(RENEGADE_CCACHE_SHARED OFF)
if(NOT "$ENV{RENEGADE_CCACHE_DIR}" STREQUAL "")
  if(NOT IS_ABSOLUTE "$ENV{RENEGADE_CCACHE_DIR}")
    message(FATAL_ERROR "RENEGADE_CCACHE_DIR must be an absolute path: $ENV{RENEGADE_CCACHE_DIR}")
  endif()
  set(RENEGADE_CCACHE_EFFECTIVE_DIR "$ENV{RENEGADE_CCACHE_DIR}")
  set(RENEGADE_CCACHE_SHARED ON)
endif()

# RENEGADE_CCACHE_RELOCATABLE_DEBUG=1
#   RelWithDebInfo compiles with -g, and ccache then hashes the build directory
#   because GCC writes it to DW_AT_comp_dir. Every canonical build uses a new
#   timestamped directory and every worktree has its own path, so ARM objects
#   never hit. This maps the build directory to a fixed pseudo path (same
#   depth, so ../../staging/... still resolves below /renegade-vita) and lets
#   ccache reuse results across build directories and worktrees. It changes
#   DW_AT_comp_dir in debug sections only; instruction bytes are unchanged
#   (experiments/canonical-cache-identity). Use gdb
#   "set substitute-path /renegade-vita <worktree>" to resolve sources.
option(RENEGADE_CCACHE_RELOCATABLE_DEBUG
  "Map the build directory in DWARF to a fixed pseudo path so ccache can share results" OFF)
set(RENEGADE_CCACHE_RELOCATABLE_DEBUG_ACTIVE "${RENEGADE_CCACHE_RELOCATABLE_DEBUG}")
if(NOT "$ENV{RENEGADE_CCACHE_RELOCATABLE_DEBUG}" STREQUAL "")
  if("$ENV{RENEGADE_CCACHE_RELOCATABLE_DEBUG}" MATCHES "^(1|ON|on|TRUE|true|YES|yes)$")
    set(RENEGADE_CCACHE_RELOCATABLE_DEBUG_ACTIVE ON)
  elseif("$ENV{RENEGADE_CCACHE_RELOCATABLE_DEBUG}" MATCHES "^(0|OFF|off|FALSE|false|NO|no)$")
    set(RENEGADE_CCACHE_RELOCATABLE_DEBUG_ACTIVE OFF)
  else()
    message(FATAL_ERROR "RENEGADE_CCACHE_RELOCATABLE_DEBUG must be 0 or 1")
  endif()
endif()
if(RENEGADE_CCACHE_RELOCATABLE_DEBUG_ACTIVE)
  file(RELATIVE_PATH rv_ccache_binary_rel "${RENEGADE_CCACHE_ROOT}" "${CMAKE_BINARY_DIR}")
  set(rv_ccache_binary_parent "")
  if(NOT rv_ccache_binary_rel STREQUAL "" AND NOT rv_ccache_binary_rel MATCHES "^\\.\\.(/|$)"
     AND NOT IS_ABSOLUTE "${rv_ccache_binary_rel}")
    get_filename_component(rv_ccache_binary_parent "${rv_ccache_binary_rel}" DIRECTORY)
  endif()
  if(rv_ccache_binary_parent STREQUAL "")
    set(RENEGADE_DEBUG_PREFIX_MAP_TARGET "/renegade-vita/obj")
  else()
    set(RENEGADE_DEBUG_PREFIX_MAP_TARGET "/renegade-vita/${rv_ccache_binary_parent}/obj")
  endif()
  # GCC and ccache see the physical working directory; map that spelling and,
  # if different, the logical one CMake was given.
  get_filename_component(rv_ccache_binary_real "${CMAKE_BINARY_DIR}" REALPATH)
  add_compile_options("-fdebug-prefix-map=${rv_ccache_binary_real}=${RENEGADE_DEBUG_PREFIX_MAP_TARGET}")
  if(NOT rv_ccache_binary_real STREQUAL CMAKE_BINARY_DIR)
    add_compile_options("-fdebug-prefix-map=${CMAKE_BINARY_DIR}=${RENEGADE_DEBUG_PREFIX_MAP_TARGET}")
  endif()
  message(STATUS "Renegade Vita: relocatable debug paths: ${CMAKE_BINARY_DIR} -> ${RENEGADE_DEBUG_PREFIX_MAP_TARGET}")
endif()

if(RENEGADE_USE_CCACHE)
  find_program(RENEGADE_CCACHE_EXECUTABLE NAMES ccache)
  if(RENEGADE_CCACHE_EXECUTABLE)
    file(MAKE_DIRECTORY "${RENEGADE_CCACHE_EFFECTIVE_DIR}")
    set(RENEGADE_CCACHE_LAUNCHER
      "${CMAKE_COMMAND};-E;env;CCACHE_DIR=${RENEGADE_CCACHE_EFFECTIVE_DIR};CCACHE_BASEDIR=${RENEGADE_CCACHE_ROOT}")
    if(RENEGADE_CCACHE_SHARED)
      # Output-neutral for a shared cache: LANG/LC_* only localize diagnostic
      # text, so different shells or agents can still share object results.
      list(APPEND RENEGADE_CCACHE_LAUNCHER "CCACHE_SLOPPINESS=locale")
    endif()
    list(APPEND RENEGADE_CCACHE_LAUNCHER "${RENEGADE_CCACHE_EXECUTABLE}")
    set(CMAKE_C_COMPILER_LAUNCHER "${RENEGADE_CCACHE_LAUNCHER}")
    set(CMAKE_CXX_COMPILER_LAUNCHER "${RENEGADE_CCACHE_LAUNCHER}")
    message(STATUS "Renegade Vita: ccache launcher enabled: ${RENEGADE_CCACHE_EXECUTABLE}")
    message(STATUS "Renegade Vita: ccache directory: ${RENEGADE_CCACHE_EFFECTIVE_DIR}")
  else()
    message(STATUS "Renegade Vita: ccache unavailable; compiling without a launcher")
  endif()
else()
  message(STATUS "Renegade Vita: ccache disabled by RENEGADE_USE_CCACHE=OFF")
endif()
