get_file_sha256() {
	local FILE_PATH="$1"
	sha256sum "$FILE_PATH" | awk '{print $1}'
}
