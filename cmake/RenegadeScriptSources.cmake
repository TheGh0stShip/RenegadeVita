# Reuse the original Scripts.dsp inventory, replacing the DLL entry points with
# the platform's ScriptRegistrar provider at the target boundary.
function(renegade_collect_script_dsp_sources upstream_script_dir staged_script_dir output_var)
  set(dsp_file "${upstream_script_dir}/Scripts.dsp")
  if(NOT EXISTS "${dsp_file}")
    message(FATAL_ERROR "Original Scripts.dsp is missing: ${dsp_file}")
  endif()
  file(STRINGS "${dsp_file}" dsp_source_lines REGEX "^SOURCE=.*[.]cpp$")
  set(script_sources)
  set(script_source_names)
  set(project_source_names)
  foreach(dsp_line IN LISTS dsp_source_lines)
    string(SUBSTRING "${dsp_line}" 8 -1 source_name)
    string(REPLACE "\\" "" source_name "${source_name}")
    if(NOT source_name MATCHES "^[A-Za-z0-9_]+[.]cpp$" OR
       NOT EXISTS "${upstream_script_dir}/${source_name}")
      message(FATAL_ERROR "Invalid original script source: ${source_name}")
    endif()
    list(FIND project_source_names "${source_name}" source_name_index)
    if(NOT source_name_index EQUAL -1)
      message(FATAL_ERROR "Duplicate original script source: ${source_name}")
    endif()
    list(APPEND project_source_names "${source_name}")
    if(source_name STREQUAL "DLLmain.cpp")
      continue()
    endif()
    list(APPEND script_source_names "${source_name}")
    list(APPEND script_sources "${staged_script_dir}/${source_name}")
  endforeach()
  list(LENGTH dsp_source_lines dsp_count)
  list(LENGTH script_sources static_count)
  if(NOT dsp_count EQUAL 45 OR NOT static_count EQUAL 44)
    message(FATAL_ERROR
      "Original Scripts.dsp inventory changed: total=${dsp_count} static=${static_count}; review source closure")
  endif()
  set(${output_var} "${script_sources}" PARENT_SCOPE)
  set(${output_var}_NAMES "${script_source_names}" PARENT_SCOPE)
endfunction()

# scripts.dll and the desktop executable each exported their own strtrim.
# Keep both original implementations: their whitespace predicates differ.
# Isolate only the Scripts caller/definition when joining them into one image.
function(renegade_configure_script_static_helpers staged_script_dir)
  set_property(SOURCE
    "${staged_script_dir}/scripts.cpp"
    "${staged_script_dir}/strtrim.cpp"
    APPEND PROPERTY COMPILE_DEFINITIONS "strtrim=Renegade_Script_strtrim")
endfunction()
