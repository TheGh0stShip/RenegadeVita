#include "renegade_cache_health.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/stat.h>
#include <unistd.h>

namespace {

struct Contract
{
	unsigned checks;
	unsigned failures;

	void Expect(bool condition, const char *name)
	{
		++checks;
		if (!condition) {
			++failures;
			printf("FAIL: %s\n", name);
		}
	}
};

bool Write_Text(const char *path, const char *text)
{
	FILE *output = fopen(path, "wb");
	if (output == NULL) return false;
	const bool written = fputs(text, output) >= 0;
	return fclose(output) == 0 && written;
}

} // namespace

int main()
{
	char temporary[] = "/tmp/renegade-cache-health-XXXXXX";
	char *root = mkdtemp(temporary);
	if (root == NULL) return 2;
	char cache[512] = {};
	snprintf(cache, sizeof(cache), "%s/cache", root);
	if (mkdir(cache, 0700) != 0) return 2;
	const RenegadePathRoots roots = {root, root, cache, root};
	char index_path[640] = {};
	snprintf(index_path, sizeof(index_path), "%s/m01-mix-index-v1.txt", cache);
	Contract contract = {};

	RenegadeCacheHealth health = Renegade_Inspect_Mix_Index_Cache(roots, "M01.mix",
		"cache/m01-mix-index-v1.txt");
	contract.Expect(health.state == RENEGADE_CACHE_HEALTH_MISSING,
		"missing cache remains optional");
	contract.Expect(Write_Text(index_path,
		"schema=renegade-vita-mix-index-v1\narchive=M01.mix\nentry_count=2\n"
		"entry=alpha.w3d\nentry=beta.w3d\n"), "write valid cache fixture");
	health = Renegade_Inspect_Mix_Index_Cache(roots, "M01.mix",
		"cache/m01-mix-index-v1.txt");
	contract.Expect(health.state == RENEGADE_CACHE_HEALTH_VALID,
		"valid index accepted");
	contract.Expect(health.entry_count == 2U, "entry count preserved");
	contract.Expect(strcmp(health.archive, "M01.mix") == 0, "archive preserved");
	contract.Expect(Write_Text(index_path,
		"schema=renegade-vita-mix-index-v1\narchive=M01.mix\nentry_count=2\n"
		"entry=beta.w3d\nentry=alpha.w3d\n"), "write unordered cache fixture");
	health = Renegade_Inspect_Mix_Index_Cache(roots, "M01.mix",
		"cache/m01-mix-index-v1.txt");
	contract.Expect(health.state == RENEGADE_CACHE_HEALTH_CORRUPT,
		"unordered index rejected");
	health = Renegade_Inspect_Mix_Index_Cache(roots, "M01.mix", "retail/M01.mix");
	contract.Expect(health.state == RENEGADE_CACHE_HEALTH_UNSAFE_PATH,
		"retail cache path rejected");
	health = Renegade_Inspect_Mix_Index_Cache(roots, "M01.mix", "cache/../M01.mix");
	contract.Expect(health.state == RENEGADE_CACHE_HEALTH_UNSAFE_PATH,
		"traversing cache path rejected");
	printf("A3.6 native cache-health contract: %u checks, %u failures\n",
		contract.checks, contract.failures);
	return contract.failures == 0U ? 0 : 1;
}
