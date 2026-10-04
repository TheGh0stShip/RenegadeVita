// Background flight-recorder flushing must persist exactly what synchronous
// flushing persists, while recording continues concurrently.
#include "a35_campaign_flight_recorder.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <map>
#include <string>

namespace {

std::string Read(const std::string &path)
{
	std::string contents;
	FILE *file = fopen(path.c_str(), "rb");
	if (file == NULL) return contents;
	char buffer[4096];
	size_t count = 0U;
	while ((count = fread(buffer, 1U, sizeof(buffer), file)) != 0U) contents.append(buffer, count);
	fclose(file);
	return contents;
}

unsigned Lines(const std::string &text)
{
	unsigned count = 0U;
	for (char c : text) count += c == '\n' ? 1U : 0U;
	return count;
}

// Maps each CSV data row to its frame number (fifth column).
std::map<unsigned, std::string> Rows(const std::string &csv)
{
	std::map<unsigned, std::string> rows;
	size_t offset = csv.find('\n');
	while (offset != std::string::npos && offset + 1U < csv.size()) {
		const size_t end = csv.find('\n', offset + 1U);
		const std::string row = csv.substr(offset + 1U, end - offset - 1U);
		size_t column = 0U;
		for (unsigned comma = 0U; comma < 4U && column != std::string::npos; ++comma)
			column = row.find(',', column + (comma != 0U ? 1U : 0U));
		if (column != std::string::npos)
			rows[static_cast<unsigned>(strtoul(row.c_str() + column + 1U, NULL, 10))] = row;
		offset = end;
	}
	return rows;
}

bool Check(bool condition, const char *step)
{
	if (!condition) fprintf(stderr, "background flight flush test failed: %s\n", step);
	return condition;
}

void Record_Session(const char *directory, bool background, unsigned frames)
{
	A35_Campaign_Flight_Set_Background_Flush(background);
	A35_Campaign_Flight_Reset("candidate-B", directory, "", "M01.mix", "M01.mix", false);
	for (unsigned index = 1U; index <= frames; ++index) {
		A31FrameTelemetry frame = {};
		frame.frame_index = index;
		frame.monotonic_us = index * 16667ULL;
		frame.frame_time_us = 16667U + (index % 7U) * 1000U;
		A35CampaignFlightRenderState render = {};
		render.mesh_submissions = index % 13U;
		A35CampaignFlightAudioState audio = {};
		audio.active_samples = index % 5U;
		A35_Campaign_Flight_Record_Frame(frame, render, audio);
		char line[64];
		const int count = snprintf(line, sizeof(line), "log line %u\n", index);
		A35_Campaign_Flight_Record_Log_Line(line, static_cast<unsigned>(count));
		if (index % 17U == 0U) {
			A35_Campaign_Flight_Record_Event("test", "tick", index, index * 16667ULL, "detail");
		}
		// Checkpoints arrive while the previous background flush may still run.
		if (index % 120U == 0U) A35_Campaign_Flight_Flush("checkpoint");
		if (index % 333U == 0U) A35_Campaign_Flight_Flush("slow-frame-over-250ms");
	}
	A35_Campaign_Flight_Flush("final");
	A35_Campaign_Flight_Shutdown();
}

} // namespace

int main()
{
	char background_dir[] = "/tmp/renegade-flight-background-XXXXXX";
	char sync_dir[] = "/tmp/renegade-flight-sync-XXXXXX";
	if (!Check(mkdtemp(background_dir) != NULL && mkdtemp(sync_dir) != NULL, "directories"))
		return 1;
	// More frames than the ring holds forces full-ring replacement passes.
	const unsigned frames = 9000U;
	Record_Session(background_dir, true, frames);
	Record_Session(sync_dir, false, frames);
	// Coalesced background snapshots may cross the 4096-frame ring boundary at
	// a different checkpoint, so the retained window can start elsewhere. Every
	// retained row must still match the synchronous row for that frame, rows
	// must be contiguous, end at the last frame and cover the whole ring.
	const std::map<unsigned, std::string> background_rows =
		Rows(Read(std::string(background_dir) + "/campaign-flight-frames.csv"));
	const std::map<unsigned, std::string> sync_rows =
		Rows(Read(std::string(sync_dir) + "/campaign-flight-frames.csv"));
	if (!Check(!background_rows.empty() && background_rows.rbegin()->first == frames &&
		sync_rows.rbegin()->first == frames, "rows end at the last frame")) return 1;
	if (!Check(background_rows.size() >= 4096U, "ring coverage")) return 1;
	unsigned expected = background_rows.begin()->first;
	for (const auto &row : background_rows) {
		if (!Check(row.first == expected++, "contiguous rows")) return 1;
		const auto match = sync_rows.find(row.first);
		if (match != sync_rows.end() &&
			!Check(match->second == row.second, "row content")) return 1;
	}
	const std::string tail_background = Read(std::string(background_dir) +
		"/campaign-flight-log-tail.txt");
	const std::string tail_sync = Read(std::string(sync_dir) + "/campaign-flight-log-tail.txt");
	if (!Check(!tail_background.empty() &&
		tail_background.substr(tail_background.size() - 15U) ==
			tail_sync.substr(tail_sync.size() - 15U), "log tail ends identically")) return 1;
	const std::string events_background = Read(std::string(background_dir) +
		"/campaign-flight-events.jsonl");
	const std::string events_sync = Read(std::string(sync_dir) + "/campaign-flight-events.jsonl");
	if (!Check(Lines(events_background) == Lines(events_sync) &&
		Lines(events_background) != 0U, "event line count")) return 1;
	const std::string summary = Read(std::string(background_dir) + "/campaign-flight-summary.json");
	if (!Check(summary.find("\"reason\":\"shutdown\"") != std::string::npos &&
		summary.find("\"frames_recorded\":4096") != std::string::npos, "final summary")) return 1;
	// A frames CSV holds the 4096-frame ring plus its header.
	if (!Check(Lines(Read(std::string(background_dir) + "/campaign-flight-frames.csv")) >= 4097U,
		"frame rows")) return 1;
	puts("Background flight recorder flush host contract PASS");
	return 0;
}
