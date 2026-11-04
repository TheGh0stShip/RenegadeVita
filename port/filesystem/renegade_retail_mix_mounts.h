#pragma once

#include "ffactorylist.h"
#include "mixfile.h"
#include "renegade_find_files.h"
#include <memory>
#include <stdio.h>
#include <string>
#include <strings.h>
#include <vector>

// Session-scoped counterpart of original Game_Init's data\\*.mix enumeration.
// Declare after the list: remove borrowed/owned entries before either dies.
// The original list remains the lookup/priority owner, including its temp
// factory and SaveGameManager's M09 search start. No payload cache is added.
class RenegadeRetailMixMounts
{
public:
	RenegadeRetailMixMounts(FileFactoryListClass &list, FileFactoryClass &root,
		MixFileFactoryClass &tutorial) : List(list), Root(root), Tutorial(tutorial) {}
	~RenegadeRetailMixMounts()
	{
		Unmount();
	}

	bool Mount()
	{
		if (!Mounted.empty()) return false;
		FailedArchive.clear();
		WIN32_FIND_DATA entry = {};
		HANDLE find = Renegade_Find_First("Data\\*.mix", &entry);
		if (find == INVALID_HANDLE_VALUE) {
			FailedArchive = "Data\\*.mix enumeration";
			return false;
		}
		bool ok = true, tutorial_seen = false;
		do {
			if (entry.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) continue;
			char logical[sizeof(entry.cFileName) + 6];
			snprintf(logical, sizeof(logical), "Data\\%s", entry.cFileName);
			MixFileFactoryClass *factory = NULL;
			if (strcasecmp(entry.cFileName, "M00_Tutorial.mix") == 0) {
				factory = &Tutorial;
				tutorial_seen = true;
			} else {
				Owned.emplace_back(new MixFileFactoryClass(logical, &Root));
				factory = Owned.back().get();
			}
			if (!factory->Is_Valid()) {
				FailedArchive = entry.cFileName;
				ok = false;
				break;
			}
			List.Add_FileFactory(factory, entry.cFileName);
			Mounted.push_back(factory);
		} while (Renegade_Find_Next(find, &entry));
		const bool closed = Renegade_Find_Close(find) != 0;
		if (ok && closed && tutorial_seen) return true;
		if (FailedArchive.empty()) FailedArchive = tutorial_seen
			? "Data\\*.mix close" : "M00_Tutorial.mix";
		// A failed startup must not leave a usable-looking partial archive set.
		Unmount();
		return false;
	}

	size_t Count() const { return Mounted.size(); }
	const char *Failed_Archive() const { return FailedArchive.c_str(); }

private:
	void Unmount()
	{
		for (size_t i = 0; i < Mounted.size(); ++i) List.Remove_FileFactory(Mounted[i]);
		Mounted.clear();
		Owned.clear();
	}
	RenegadeRetailMixMounts(const RenegadeRetailMixMounts &) = delete;
	RenegadeRetailMixMounts &operator=(const RenegadeRetailMixMounts &) = delete;
	FileFactoryListClass &List;
	FileFactoryClass &Root;
	MixFileFactoryClass &Tutorial;
	std::vector<std::unique_ptr<MixFileFactoryClass> > Owned;
	std::vector<MixFileFactoryClass *> Mounted;
	std::string FailedArchive;
};
