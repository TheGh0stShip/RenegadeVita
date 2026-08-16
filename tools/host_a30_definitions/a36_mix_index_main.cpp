// Deterministic host-side MIX index writer.  It deliberately uses the original
// MixFileFactoryClass; it does not parse, extract, transcode, or redistribute
// retail content and is not part of the Vita runtime resource path.

#include "renegade_file_factory.h"
#include "mixfile.h"
#include "wwstring.h"

#include <algorithm>
#include <stdio.h>
#include <string>
#include <vector>

namespace {

const char *const kIndexSchema = "renegade-vita-mix-index-v1";

bool Safe_Entry_Name(const char *name)
{
	if (name == NULL || name[0] == 0) return false;
	for (const char *cursor = name; *cursor != 0; ++cursor) {
		if (*cursor == '\r' || *cursor == '\n') return false;
	}
	return true;
}

bool Build_Index(MixFileFactoryClass &factory, std::vector<std::string> &entries)
{
	DynamicVectorClass<StringClass> names;
	if (!factory.Is_Valid() || !factory.Build_Filename_List(names)) return false;
	for (int index = 0; index < names.Count(); ++index) {
		const char *name = names[index];
		if (!Safe_Entry_Name(name)) return false;
		entries.push_back(name);
	}
	std::sort(entries.begin(), entries.end());
	return !entries.empty();
}

bool Write_Index(const char *output_path, const char *archive_name,
	const std::vector<std::string> &entries)
{
	FILE *output = fopen(output_path, "wb");
	if (output == NULL) return false;
	bool valid = fprintf(output, "schema=%s\narchive=%s\nentry_count=%u\n",
		kIndexSchema, archive_name, static_cast<unsigned>(entries.size())) > 0;
	for (std::vector<std::string>::const_iterator entry = entries.begin();
		valid && entry != entries.end(); ++entry) {
		valid = fprintf(output, "entry=%s\n", entry->c_str()) > 0;
	}
	const bool flushed = fflush(output) == 0;
	const bool closed = fclose(output) == 0;
	return valid && flushed && closed;
}

} // namespace

int main(int argc, char **argv)
{
	if (argc != 7) {
		fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT MIX_NAME OUTPUT\n",
			argv[0]);
		return 2;
	}
	char archive_path[128] = {};
	const int archive_length = snprintf(archive_path, sizeof(archive_path),
		"Data\\%s", argv[5]);
	if (archive_length <= 0 ||
		static_cast<size_t>(archive_length) >= sizeof(archive_path)) {
		fprintf(stderr, "MIX name is too long\n");
		return 2;
	}
	const RenegadePathRoots roots = {argv[1], argv[2], argv[3], argv[4]};
	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass mix_factory(archive_path, &root_factory);
	std::vector<std::string> entries;
	const bool indexed = Build_Index(mix_factory, entries);
	const bool written = indexed && Write_Index(argv[6], argv[5], entries);
	printf("a36.mix_index_archive=%s\n", argv[5]);
	printf("a36.mix_index_entries=%u\n", static_cast<unsigned>(entries.size()));
	printf("a36.mix_index_schema=%s\n", kIndexSchema);
	printf("A3.6 original MIX index: %s\n", written ? "PASS" : "FAIL");
	return written ? 0 : 1;
}
