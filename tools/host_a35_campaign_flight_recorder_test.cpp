#include "a35_campaign_flight_recorder.h"
#include "a35_script_lookup_telemetry.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <string>
#include <thread>

namespace {

bool Read_File(const std::string &path, std::string &contents)
{
	FILE *file = fopen(path.c_str(), "rb");
	if (file == NULL) return false;
	contents.clear();
	char buffer[4096];
	size_t count = 0U;
	while ((count = fread(buffer, 1U, sizeof(buffer), file)) != 0U) {
		contents.append(buffer, count);
	}
	const bool read_ok = ferror(file) == 0;
	const bool close_ok = fclose(file) == 0;
	return read_ok && close_ok;
}

unsigned Line_Count(const std::string &contents)
{
	unsigned count = 0U;
	for (size_t i = 0U; i < contents.size(); ++i) {
		if (contents[i] == '\n') ++count;
	}
	return count;
}

bool Check(bool condition, const char *step)
{
	if (!condition) fprintf(stderr, "flight recorder test failed: %s\n", step);
	return condition;
}

} // namespace

int main()
{
	char directory[] = "/tmp/renegade-flight-recorder-XXXXXX";
	if (!Check(mkdtemp(directory) != NULL, "temporary directory")) return 1;
	const std::string root(directory);
	const std::string events = root + "/campaign-flight-events.jsonl";
	const std::string frames = root + "/campaign-flight-frames.csv";
	const std::string log_tail = root + "/campaign-flight-log-tail.txt";
	const std::string summary = root + "/campaign-flight-summary.json";
	std::string contents;

	A35_Campaign_Flight_Reset("candidate-A", directory, "", "M13.mix", "M13.mix", true);
	std::thread loader([]() {
		A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, 100389, false);
	});
	loader.join();
	if (!Check(A35_Campaign_Flight_Flush("checkpoint"), "first checkpoint")) return 1;
	if (!Check(Read_File(summary, contents) &&
		contents.find("\"frames_recorded\":0") != std::string::npos &&
		contents.find("\"object_id\":100389") != std::string::npos &&
		contents.find("\"phase\":\"level_load\"") != std::string::npos,
		"load-only worker observation serialized")) return 1;
	if (!Check(Read_File(events, contents) && Line_Count(contents) == 1U &&
		contents.find("candidate-A") != std::string::npos, "first event")) return 1;
	A31FrameTelemetry frame = {};
	A35CampaignFlightRenderState render = {};
	A35CampaignFlightAudioState audio = {};
	for (uint64_t index = 1U; index <= 2U; ++index) {
		frame.frame_index = index;
		A35_Campaign_Flight_Record_Frame(frame, render, audio);
	}
	A35_Campaign_Flight_Record_Event("mission", "sam", 2U, 2U, "alive");
	if (!Check(A35_Campaign_Flight_Flush("checkpoint"), "append checkpoint")) return 1;
	if (!Check(Read_File(events, contents) && Line_Count(contents) == 2U,
		"event append")) return 1;
	if (!Check(Read_File(frames, contents) && Line_Count(contents) == 3U,
		"frame append")) return 1;
	if (!Check(A35_Campaign_Flight_Flush("checkpoint") &&
		Read_File(frames, contents) && Line_Count(contents) == 3U,
		"empty checkpoint")) return 1;
	A35_Campaign_Flight_Record_Log_Line("owner line\n", 11U);
	std::thread worker([]() {
		A35_Campaign_Flight_Record_Log_Line("worker line\n", 12U);
	});
	worker.join();
	if (!Check(A35_Campaign_Flight_Flush("checkpoint") &&
		Read_File(log_tail, contents) &&
		contents.find("owner line") != std::string::npos &&
		contents.find("worker line") == std::string::npos,
		"owner-only flight log")) return 1;

	A35_Campaign_Flight_Reset("candidate-B", directory, "", "M13.mix", "M13.mix");
	if (!Check(A35_Campaign_Flight_Flush("checkpoint"), "candidate replacement")) return 1;
	if (!Check(Read_File(events, contents) && Line_Count(contents) == 1U &&
		contents.find("candidate-B") != std::string::npos &&
		contents.find("candidate-A") == std::string::npos,
		"stale event removal")) return 1;
	if (!Check(Read_File(frames, contents) && Line_Count(contents) == 1U,
		"stale frame removal")) return 1;
	if (!Check(Read_File(summary, contents) &&
		contents.find("candidate-B") != std::string::npos &&
		contents.find("candidate-A") == std::string::npos &&
		contents.find("\"object_id\":100389") == std::string::npos &&
		contents.find("\"enabled\":false") != std::string::npos,
		"stale summary removal")) return 1;

	for (unsigned index = 0U; index < 769U; ++index) {
		A35_Campaign_Flight_Record_Event("mission", "sam", index, index, "event");
	}
	if (!Check(A35_Campaign_Flight_Flush("checkpoint"), "event ring rollover")) return 1;
	if (!Check(Read_File(events, contents) && Line_Count(contents) == 768U &&
		contents.find("candidate-B") != std::string::npos,
		"bounded event snapshot")) return 1;
	A35_Campaign_Flight_Shutdown();
	remove(events.c_str());
	remove(frames.c_str());
	remove(log_tail.c_str());
	remove(summary.c_str());
	rmdir(directory);
	puts("flight recorder append, replacement, ring rollover and owner thread PASS");
	return 0;
}
