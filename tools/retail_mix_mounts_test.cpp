// Non-play fixture: real original MIX/list owners with rooted synthetic data.
#include "renegade_retail_mix_mounts.h"
#include "renegade_file_factory.h"
#include "wwfile.h"
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); abort(); } } while (0)

static void Expect(FileFactoryListClass &list, const char *name, const char *expected)
{
	FileClass *file = list.Get_File(name);
	CHECK(file != NULL && file->Open(FileClass::READ));
	char bytes[64] = {};
	const int count = file->Read(bytes, sizeof(bytes) - 1);
	CHECK(count == static_cast<int>(strlen(expected)) && strcmp(bytes, expected) == 0);
	file->Close();
	list.Return_File(file);
}

int main(int argc, char **argv)
{
	CHECK(argc == 3);
	RenegadePathRoots roots = {argv[1], argv[1], argv[1], argv[1]};
	Renegade_Set_Find_Roots(roots);
	RenegadeRootedFileFactoryClass root(roots);
	MixFileFactoryClass tutorial("Data\\M00_Tutorial.mix", &root);
	MixFileFactoryClass global("Data\\Always.dat", &root);
	MixFileFactoryClass temp("Data\\network.dat", &root);
	FileFactoryListClass list;
	list.Add_FileFactory(&root, "");
	list.Add_FileFactory(&global, "Always.dat");
	{
		RenegadeRetailMixMounts mounts(list, root, tutorial);
		if (strcmp(argv[2], "reference") == 0) {
			CHECK(mounts.Mount());
			CHECK(mounts.Count() > 4);
			FileClass *file = list.Get_File("lv8_hbag.dds");
			CHECK(file != NULL && file->Open(FileClass::READ));
			char magic[4] = {};
			CHECK(file->Read(magic, 4) == 4 && memcmp(magic, "DDS ", 4) == 0);
			file->Close();
			list.Return_File(file);
			printf("read-only reference: %u MIX archives; cross-mission DDS header PASS\n",
				static_cast<unsigned>(mounts.Count()));
			return 0;
		}
		if (strcmp(argv[2], "valid") != 0) {
			CHECK(!mounts.Mount());
			CHECK(mounts.Count() == 0);
			CHECK(mounts.Failed_Archive()[0] != '\0');
			if (strcmp(argv[2], "invalid") == 0)
				CHECK(strcmp(mounts.Failed_Archive(), "broken.mix") == 0);
			Expect(list, "shared.txt", "global");
			FileClass *absent = list.Get_File("cross_mission.txt");
			CHECK(absent != NULL && !absent->Is_Available());
			list.Return_File(absent);
			CHECK(!mounts.Mount()); // retry fails cleanly without a partial list
			CHECK(mounts.Count() == 0);
		} else {
			CHECK(mounts.Mount());
			CHECK(mounts.Count() == 4); // directory and nested MIX are excluded
			CHECK(!mounts.Mount());
			Expect(list, "tutorial.txt", "tutorial");
			Expect(list, "cross_mission.txt", "other mission");
			Expect(list, "shared.txt", "global");
			list.Set_Search_Start("m09.MIX");
			Expect(list, "shared.txt", "m09");
			list.Add_Temp_FileFactory(&temp);
			Expect(list, "shared.txt", "network");
			CHECK(list.Remove_Temp_FileFactory() == &temp);
			Expect(list, "shared.txt", "m09");
			list.Reset_Search_Start();
			Expect(list, "shared.txt", "global");
			// Existing selected-map/round ownership is a separate original index.
			MixFileFactoryClass selected("Data\\M09.mix", &root);
			list.Add_FileFactory(&selected, "M09.mix");
			list.Set_Search_Start("M09.mix");
			Expect(list, "shared.txt", "m09");
			list.Remove_FileFactory(&selected);
			list.Set_Search_Start("M09.mix");
			Expect(list, "shared.txt", "m09");
		}
	}
	// Mounts must detach before their original factories are destroyed.
	Expect(list, "shared.txt", "global");
	FileClass *missing = list.Get_File("cross_mission.txt");
	CHECK(missing != NULL && !missing->Is_Available());
	list.Return_File(missing);
	puts("retail MIX mounts PASS");
}
