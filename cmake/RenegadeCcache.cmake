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

if(RENEGADE_USE_CCACHE)
  find_program(RENEGADE_CCACHE_EXECUTABLE NAMES ccache)
  if(RENEGADE_CCACHE_EXECUTABLE)
    file(MAKE_DIRECTORY "${RENEGADE_CCACHE_DIR}")
    set(RENEGADE_CCACHE_LAUNCHER
      "${CMAKE_COMMAND};-E;env;CCACHE_DIR=${RENEGADE_CCACHE_DIR};CCACHE_BASEDIR=${RENEGADE_CCACHE_ROOT};${RENEGADE_CCACHE_EXECUTABLE}")
    set(CMAKE_C_COMPILER_LAUNCHER "${RENEGADE_CCACHE_LAUNCHER}")
    set(CMAKE_CXX_COMPILER_LAUNCHER "${RENEGADE_CCACHE_LAUNCHER}")
    message(STATUS "Renegade Vita: ccache launcher enabled: ${RENEGADE_CCACHE_EXECUTABLE}")
    message(STATUS "Renegade Vita: ccache directory: ${RENEGADE_CCACHE_DIR}")
  else()
    message(STATUS "Renegade Vita: ccache unavailable; compiling without a launcher")
  endif()
else()
  message(STATUS "Renegade Vita: ccache disabled by RENEGADE_USE_CCACHE=OFF")
endif()
