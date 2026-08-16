#include "renegade_file_factory.h"
#include "mixfile.h"
#include "wwstring.h"

#include <stdio.h>

namespace {
const char *const kM01Archive = "Data\\M01.mix";

bool Has_Extension(const DynamicVectorClass<StringClass> &names, const char *extension)
{
	for (int index = 0; index < names.Count(); ++index) {
		const char *name = names[index];
		const char *dot = name;
		for (; *dot != 0; ++dot) {}
		for (; dot != name && dot[-1] != '.'; --dot) {}
		if (dot != name && StringClass(dot - 1).Compare_No_Case(extension) == 0) return true;
	}
	return false;
}
}

int main(int argc, char **argv)
{
	if (argc != 5) {
		fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT\n", argv[0]);
		return 2;
	}
	const RenegadePathRoots roots = {argv[1], argv[2], argv[3], argv[4]};
	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass m01_factory(kM01Archive, &root_factory);
	DynamicVectorClass<StringClass> names;
	const bool valid = m01_factory.Is_Valid();
	const bool enumerated = valid && m01_factory.Build_Filename_List(names);
	const bool ldd = enumerated && Has_Extension(names, ".ldd");
	const bool lsd = enumerated && Has_Extension(names, ".lsd");
	const bool dep = enumerated && Has_Extension(names, ".dep");
	printf("a36.m01_mix_valid=%s\n", valid ? "true" : "false");
	printf("a36.m01_mix_enumerated=%s\n", enumerated ? "true" : "false");
	printf("a36.m01_mix_entries=%d\n", names.Count());
	printf("a36.m01_has_ldd=%s\n", ldd ? "true" : "false");
	printf("a36.m01_has_lsd=%s\n", lsd ? "true" : "false");
	printf("a36.m01_has_dep=%s\n", dep ? "true" : "false");
	const bool passed = valid && enumerated && names.Count() > 0 && ldd && lsd && dep;
	printf("A3.6 original M01 MIX preflight: %s\n", passed ? "PASS" : "FAIL");
	return passed ? 0 : 1;
}
