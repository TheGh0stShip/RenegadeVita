#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>

// Exercise the original script directly; only the chunk transport is a fixture.
#include "../staging/scripts/Test_Cinematic.cpp"

struct SavedField {
	int id;
	std::vector<unsigned char> bytes;
};
struct SavedChunk {
	unsigned id;
	std::vector<SavedField> fields;
};
class ScriptSaver {
public:
	std::vector<SavedChunk> chunks;
	bool open = false;
};
class ScriptLoader {
public:
	const std::vector<SavedChunk> &chunks;
	size_t chunk = 0;
	size_t field = 0;
	explicit ScriptLoader(const ScriptSaver &saved) : chunks(saved.chunks) {}
};

static unsigned Clock = 1000;
static std::vector<std::string> PlayedCues;

static void Check_Command_Parameters()
{
	const std::vector<std::pair<std::string, std::vector<std::string>>> cases = {
		{"", {"", ""}},
		{" a , b ", {"a", "b", ""}},
		{"\"a,b\", c", {"a,b", "c", ""}},
		{",x,", {"", "x", "", ""}},
		{"\"unterminated", {"unterminated", ""}},
		{"one", {"one", "", ""}},
		{std::string(600, 'x') + ",end", {std::string(600, 'x'), "end", ""}},
	};
	for (const auto &item : cases) {
		Test_Cinematic script;
		assert(strcmp(script.Get_Next_Parameter(), "") == 0);
		std::string input = item.first;
		for (size_t i = 0; i < item.second.size(); ++i) {
			const char *value = i == 0 ? script.Get_First_Parameter(input.data()) : script.Get_Next_Parameter();
			assert(value != nullptr && item.second[i] == value);
		}
	}
	Test_Cinematic first, second;
	char first_input[] = "a,b";
	char second_input[] = "c,d";
	assert(strcmp(first.Get_First_Parameter(first_input), "a") == 0);
	assert(strcmp(second.Get_First_Parameter(second_input), "c") == 0);
	assert(strcmp(first.Get_Next_Parameter(), "b") == 0);
	assert(strcmp(second.Get_Next_Parameter(), "d") == 0);
	puts("Original cinematic command parameter parsing: 7 cases and independent cursors PASS");
}

int main()
{
	Check_Command_Parameters();
	ScriptCommands commands = {};
	commands.Get_Sync_Time = []() { return Clock; };
	commands.Get_ID = [](GameObject *) { return 1; };
	commands.Start_Timer = [](GameObject *, ScriptClass *, float duration, int) {
		assert(duration >= 0);
	};
	commands.Destroy_Object = [](GameObject *) {};
	commands.Create_2D_Sound = [](const char *name) {
		PlayedCues.emplace_back(name);
		return static_cast<int>(PlayedCues.size());
	};
	commands.Begin_Chunk = [](ScriptSaver &saved, unsigned id) {
		assert(!saved.open);
		saved.chunks.push_back({id, {}});
		saved.open = true;
	};
	commands.End_Chunk = [](ScriptSaver &saved) { assert(saved.open); saved.open = false; };
	commands.Save_Data = [](ScriptSaver &saved, int id, int size, void *data) {
		assert(saved.open && size >= 0);
		const auto *bytes = static_cast<unsigned char *>(data);
		saved.chunks.back().fields.push_back({id, {bytes, bytes + size}});
	};
	commands.Open_Chunk = [](ScriptLoader &loader, unsigned *id) {
		if (loader.chunk == loader.chunks.size()) return false;
		*id = loader.chunks[loader.chunk].id;
		loader.field = 0;
		return true;
	};
	commands.Close_Chunk = [](ScriptLoader &loader) { ++loader.chunk; };
	commands.Load_Begin = [](ScriptLoader &loader, int *id) {
		const auto &fields = loader.chunks[loader.chunk].fields;
		if (loader.field == fields.size()) return false;
		*id = fields[loader.field].id;
		return true;
	};
	commands.Load_Data = [](ScriptLoader &loader, int size, void *data) {
		const auto &bytes = loader.chunks[loader.chunk].fields[loader.field].bytes;
		assert(size >= 0 && static_cast<size_t>(size) == bytes.size());
		memcpy(data, bytes.data(), bytes.size());
	};
	commands.Load_End = [](ScriptLoader &loader) { ++loader.field; };
	Commands = &commands;

	for (bool camera : {false, true}) {
		Test_Cinematic original;
		original.IsCameraCinematic = camera;
		original.PrimaryKilled = false;
		original.Time = 12.25f;
		original.LastSyncTime = 975;
		original.ObjectSlots[3] = 123456;
		original.Add_Control_Line(13.0f, "Play_Animation,3,Example.Example,0");
		ScriptSaver saved;
		original.Save(saved);
		assert(!saved.open);
		Clock = 5000;
		ScriptLoader loader(saved);
		Test_Cinematic restored;
		restored.IsCameraCinematic = !camera;
		restored.Load(loader);
		assert(restored.IsCameraCinematic == camera);
		assert(restored.Time == original.Time && restored.LastSyncTime == 4975);
		assert(restored.ObjectSlots[3] == 123456 && restored.ObjectSlots[2] == 0);
		assert(restored.Controls && restored.Controls->Time == 13.0f);
		assert(strcmp(restored.Controls->Command, original.Controls->Command) == 0);
		assert(restored.Controls->Next == NULL);

		// Older saves have no camera-state microchunk; loading must be deterministic.
		for (auto &chunk : saved.chunks) {
			if (chunk.id != CHUNKID_VARIABLES) continue;
			chunk.fields.erase(std::remove_if(chunk.fields.begin(), chunk.fields.end(),
				[](const SavedField &field) { return field.id == 8; }), chunk.fields.end());
		}
		ScriptLoader legacy_loader(saved);
		Test_Cinematic legacy;
		legacy.IsCameraCinematic = true;
		legacy.Load(legacy_loader);
		assert(!legacy.IsCameraCinematic);
		Clock = 1000;
	}
	{
		Test_Cinematic original;
		original.IsCameraCinematic = false;
		original.PrimaryKilled = false;
		original.Time = 0;
		original.LastSyncTime = 1000;
		original.Add_Control_Line(0.5f, "Play_Audio,Cue_Before_Save");
		original.Add_Control_Line(1.5f, "Play_Audio,Cue_After_Save");
		Clock = 1600;
		original.Parse_Commands(NULL);
		assert((PlayedCues == std::vector<std::string>{"Cue_Before_Save"}));
		ScriptSaver saved;
		original.Save(saved);
		Clock = 5000;
		ScriptLoader loader(saved);
		Test_Cinematic restored;
		restored.Load(loader);
		restored.Parse_Commands(NULL);
		assert(PlayedCues.size() == 1);
		Clock = 5800;
		restored.Parse_Commands(NULL);
		assert(PlayedCues.size() == 1);
		Clock = 6000;
		restored.Parse_Commands(NULL);
		assert((PlayedCues == std::vector<std::string>{"Cue_Before_Save", "Cue_After_Save"}));
		assert(restored.Controls == NULL);
	}
	puts("Original cinematic pending audio executes once after save/load PASS");
	puts("Original cinematic save/load camera, clock, slots and commands PASS");
	Commands = NULL;
	return 0;
}
