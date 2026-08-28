#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	printf 'Usage: %s VITA_IP VPK_PATH [REMOTE_DIR]\n' "$0" >&2
	printf 'Upload one built VPK to a VitaShell FTP directory without installing it.\n' >&2
	printf 'Default REMOTE_DIR: ux0:/data/renegade/user\n' >&2
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
	usage
	exit 0
fi
if (($# < 2 || $# > 3)); then
	usage
	exit 2
fi

vita_ip=$1
vpk_path=$2
remote_dir=${3:-ux0:/data/renegade/user}
ftp_port=${RENEGADE_VITASHELL_FTP_PORT:-1337}

case "$vpk_path" in
	*.vpk) ;;
	*) printf 'Refusing to upload a non-VPK file: %s\n' "$vpk_path" >&2; exit 2 ;;
esac
test -f "$vpk_path" || {
	printf 'VPK does not exist: %s\n' "$vpk_path" >&2
	exit 2
}

for command in curl sha256sum; do
	command -v "$command" >/dev/null 2>&1 || {
		printf 'Required command is unavailable: %s\n' "$command" >&2
		exit 2
	}
done

file_name=$(basename "$vpk_path")
remote_url="ftp://$vita_ip:$ftp_port/$remote_dir/$file_name"
local_size=$(wc -c < "$vpk_path")
local_sha=$(sha256sum "$vpk_path" | awk '{print $1}')

printf 'Uploading %s (%s bytes)\n' "$vpk_path" "$local_size"
printf 'SHA-256: %s\n' "$local_sha"
printf 'Target: %s\n' "$remote_url"

curl --connect-timeout 10 --max-time 300 --ftp-create-dirs -T "$vpk_path" "$remote_url"

printf '\nUpload complete. Install the VPK manually from VitaShell.\n'
