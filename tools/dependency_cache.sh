# shellcheck shell=bash
# Opt-in content-addressed cache for the third-party dependency builds.
# Sourced by build_vitagl_demo.sh, build_ffmpeg_bink_vita.sh and
# build_ttfs_https_vita.sh after their own in-tree reuse checks.
#
# Disabled unless RENEGADE_DEPENDENCY_CACHE=1 or RENEGADE_DEPENDENCY_CACHE_DIR
# is set.  RENEGADE_DEPENDENCY_CACHE=0 always disables it.  While disabled,
# rv_depcache_compute_key and rv_depcache_restore return non-zero without
# running Python and rv_depcache_store does nothing, so every script takes its
# original build path unchanged.
#
# RENEGADE_DEPENDENCY_CACHE_DIR selects a shared location (for example one
# directory for every worktree); the default is build/dependency-cache inside
# this tree.  Any key, verification or copy failure falls back to the normal
# build.  See reports/tutorial/TUT_R1_DEPENDENCY_CACHE.md.

rv_depcache_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_depcache_tool="$rv_depcache_root/tools/dependency_cache.py"
rv_depcache_key=
rv_depcache_explain=

rv_depcache_enabled() {
	case "${RENEGADE_DEPENDENCY_CACHE:-}" in
	0) return 1 ;;
	1) return 0 ;;
	'') [[ -n "${RENEGADE_DEPENDENCY_CACHE_DIR:-}" ]] ;;
	*)
		echo "Dependency cache: invalid RENEGADE_DEPENDENCY_CACHE=${RENEGADE_DEPENDENCY_CACHE} (expected 0 or 1); cache disabled." >&2
		return 1
		;;
	esac
}

rv_depcache_dir() {
	printf '%s\n' "${RENEGADE_DEPENDENCY_CACHE_DIR:-$rv_depcache_root/build/dependency-cache}"
}

# rv_depcache_compute_key NAME KEY-ARGS...
# Sets rv_depcache_key on success.  KEY-ARGS are passed to
# 'dependency_cache.py key' (--source/--patch/--script/--file/--value/--flags/--tree).
rv_depcache_compute_key() {
	rv_depcache_key=
	rv_depcache_explain=
	rv_depcache_enabled || return 1
	local rv_name=$1
	shift
	local rv_dir rv_key
	rv_dir=$(rv_depcache_dir)
	mkdir -p "$rv_dir/.pending" || return 1
	rv_depcache_explain="$rv_dir/.pending/$rv_name.$$.json"
	if ! rv_key=$(python3 "$rv_depcache_tool" key --name "$rv_name" \
		--explain-out "$rv_depcache_explain" "$@"); then
		echo "Dependency cache: key for $rv_name unavailable; using the normal build path." >&2
		rm -f -- "$rv_depcache_explain"
		rv_depcache_explain=
		return 1
	fi
	rv_depcache_key=$rv_key
	echo "Dependency cache: $rv_name key $rv_key in $rv_dir"
}

# rv_depcache_restore NAME DEST [--replace-dest] OUTPUT...
# Returns 0 only for a verified hit restored into DEST.
rv_depcache_restore() {
	[[ -n "$rv_depcache_key" ]] || return 1
	local rv_name=$1 rv_dest=$2
	shift 2
	if python3 "$rv_depcache_tool" restore --cache-dir "$(rv_depcache_dir)" \
		--name "$rv_name" --key "$rv_depcache_key" --dest "$rv_dest" "$@"; then
		rm -f -- "$rv_depcache_explain"
		return 0
	fi
	return 1
}

# rv_depcache_store NAME SRC OUTPUT...
# Publishes outputs from a completed build.  Never fails the caller.
rv_depcache_store() {
	[[ -n "$rv_depcache_key" ]] || return 0
	local rv_name=$1 rv_src=$2
	shift 2
	python3 "$rv_depcache_tool" store --cache-dir "$(rv_depcache_dir)" \
		--name "$rv_name" --key "$rv_depcache_key" --key-json "$rv_depcache_explain" \
		--src "$rv_src" "$@" ||
		echo "Dependency cache: storing $rv_name failed; the completed build is unaffected." >&2
	rm -f -- "$rv_depcache_explain"
	rv_depcache_key=
	rv_depcache_explain=
	return 0
}
