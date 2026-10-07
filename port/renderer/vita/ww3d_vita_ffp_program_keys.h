#pragma once

// Persistent record of the vitaGL fixed-function (FFP) program keys this
// title has used, so later runs can load their cached GXPs on a loading
// screen instead of on first use during gameplay.
//
// The record only names programs; it never decides which program a draw
// uses. vitaGL still selects programs by its exact shader/combiner masks,
// and pre-warm only loads GXPs that its own first-use path would load.
//
// Text format (version 1), every line '\n'-terminated:
//   renegade-vgl-ffp-keys 1
//   tag <vitaGL revision/magic/WVP/patch-digest tag>
//   v <8 hex vertex mask>                        (0..kMaxVertexKeys lines)
//   f <8 hex mask> <8 hex combiner low> <8 hex combiner high>
//   end <vertex count> <fragment count>
// A file with another version or tag, a malformed line, a duplicate, too
// many keys, or a missing/mismatched trailer is rejected as a whole.
// Pure logic: no Vita or vitaGL dependencies (host-tested).

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace RenegadeVitaFfpProgramKeys {

enum {
	kFormatVersion = 1,
	// Below vitaGL's 256-entry RAM cache so pre-warm never wraps it and
	// leaves room for programs first seen in the current run.
	kMaxVertexKeys = 128,
	kMaxFragmentKeys = 192,
	kMaxTagLength = 63,
	kMaxFileBytes = 16384
};

struct FragmentKey {
	uint32_t mask;
	uint32_t combiner_low;
	uint32_t combiner_high;
};

struct KeySet {
	uint32_t vertex[kMaxVertexKeys];
	unsigned vertex_count;
	FragmentKey fragment[kMaxFragmentKeys];
	unsigned fragment_count;
};

inline void Clear(KeySet &set)
{
	set.vertex_count = 0U;
	set.fragment_count = 0U;
}

inline bool Has_Vertex(const KeySet &set, uint32_t key)
{
	for (unsigned i = 0U; i < set.vertex_count; ++i) {
		if (set.vertex[i] == key) return true;
	}
	return false;
}

inline bool Has_Fragment(const KeySet &set, const FragmentKey &key)
{
	for (unsigned i = 0U; i < set.fragment_count; ++i) {
		const FragmentKey &k = set.fragment[i];
		if (k.mask == key.mask && k.combiner_low == key.combiner_low &&
			k.combiner_high == key.combiner_high) return true;
	}
	return false;
}

// Appends a new key; returns false for a duplicate or when the set is full.
inline bool Add_Vertex(KeySet &set, uint32_t key)
{
	if (set.vertex_count >= kMaxVertexKeys || Has_Vertex(set, key)) return false;
	set.vertex[set.vertex_count++] = key;
	return true;
}

inline bool Add_Fragment(KeySet &set, const FragmentKey &key)
{
	if (set.fragment_count >= kMaxFragmentKeys || Has_Fragment(set, key)) return false;
	set.fragment[set.fragment_count++] = key;
	return true;
}

// Merges keys exported by vitaGL (fragment keys as {mask, low, high}
// triplets) after the existing ones, preserving order. Returns the number
// of keys added; keys beyond the bounds are dropped.
inline unsigned Merge(KeySet &set, const uint32_t *vertex, unsigned vertex_count,
	const uint32_t *fragment_triplets, unsigned fragment_count)
{
	unsigned added = 0U;
	for (unsigned i = 0U; i < vertex_count; ++i) {
		if (Add_Vertex(set, vertex[i])) ++added;
	}
	for (unsigned i = 0U; i < fragment_count; ++i) {
		FragmentKey key;
		key.mask = fragment_triplets[i * 3U + 0U];
		key.combiner_low = fragment_triplets[i * 3U + 1U];
		key.combiner_high = fragment_triplets[i * 3U + 2U];
		if (Add_Fragment(set, key)) ++added;
	}
	return added;
}

inline bool Valid_Tag(const char *tag)
{
	if (tag == NULL) return false;
	const size_t length = strlen(tag);
	if (length == 0U || length > kMaxTagLength) return false;
	for (size_t i = 0U; i < length; ++i) {
		const unsigned char c = static_cast<unsigned char>(tag[i]);
		if (c <= 0x20U || c >= 0x7FU) return false;
	}
	return true;
}

namespace Detail {

struct Writer {
	char *out;
	size_t capacity;
	size_t length;
	bool ok;
};

inline void Put(Writer &w, const char *text)
{
	const size_t n = strlen(text);
	if (!w.ok || w.length + n > w.capacity) {
		w.ok = false;
		return;
	}
	memcpy(w.out + w.length, text, n);
	w.length += n;
}

inline void Put_Hex(Writer &w, uint32_t value)
{
	static const char digits[] = "0123456789ABCDEF";
	char text[9];
	for (int i = 7; i >= 0; --i) {
		text[i] = digits[value & 0xFU];
		value >>= 4;
	}
	text[8] = '\0';
	Put(w, text);
}

inline void Put_Decimal(Writer &w, unsigned value)
{
	char text[12];
	int i = 11;
	text[i] = '\0';
	do {
		text[--i] = static_cast<char>('0' + value % 10U);
		value /= 10U;
	} while (value != 0U && i > 0);
	Put(w, text + i);
}

struct Reader {
	const char *data;
	size_t size;
	size_t pos;
};

// Returns the next '\n'-terminated line (without the terminator); false at
// end of data or for an unterminated final line.
inline bool Next_Line(Reader &r, const char *&line, size_t &length)
{
	if (r.pos >= r.size) return false;
	const char *start = r.data + r.pos;
	const void *newline = memchr(start, '\n', r.size - r.pos);
	if (newline == NULL) return false;
	length = static_cast<size_t>(static_cast<const char *>(newline) - start);
	line = start;
	r.pos += length + 1U;
	return true;
}

inline bool Starts_With(const char *line, size_t length, const char *prefix)
{
	const size_t n = strlen(prefix);
	return length >= n && memcmp(line, prefix, n) == 0;
}

// Exactly eight upper/lower-case hex digits.
inline bool Parse_Hex8(const char *text, uint32_t &value)
{
	uint32_t result = 0U;
	for (int i = 0; i < 8; ++i) {
		const char c = text[i];
		uint32_t digit;
		if (c >= '0' && c <= '9') digit = static_cast<uint32_t>(c - '0');
		else if (c >= 'A' && c <= 'F') digit = static_cast<uint32_t>(c - 'A' + 10);
		else if (c >= 'a' && c <= 'f') digit = static_cast<uint32_t>(c - 'a' + 10);
		else return false;
		result = (result << 4) | digit;
	}
	value = result;
	return true;
}

// One to five decimal digits, nothing else.
inline bool Parse_Count(const char *text, size_t length, unsigned &value)
{
	if (length == 0U || length > 5U) return false;
	unsigned result = 0U;
	for (size_t i = 0U; i < length; ++i) {
		if (text[i] < '0' || text[i] > '9') return false;
		result = result * 10U + static_cast<unsigned>(text[i] - '0');
	}
	value = result;
	return true;
}

} // namespace Detail

// Writes the record; returns its byte length, or 0 if the tag is invalid or
// the output buffer is too small.
inline size_t Serialize(const KeySet &set, const char *tag, char *out, size_t capacity)
{
	if (!Valid_Tag(tag) || out == NULL || set.vertex_count > kMaxVertexKeys ||
		set.fragment_count > kMaxFragmentKeys) return 0U;
	Detail::Writer w = { out, capacity, 0U, true };
	Detail::Put(w, "renegade-vgl-ffp-keys ");
	Detail::Put_Decimal(w, kFormatVersion);
	Detail::Put(w, "\ntag ");
	Detail::Put(w, tag);
	Detail::Put(w, "\n");
	for (unsigned i = 0U; i < set.vertex_count; ++i) {
		Detail::Put(w, "v ");
		Detail::Put_Hex(w, set.vertex[i]);
		Detail::Put(w, "\n");
	}
	for (unsigned i = 0U; i < set.fragment_count; ++i) {
		Detail::Put(w, "f ");
		Detail::Put_Hex(w, set.fragment[i].mask);
		Detail::Put(w, " ");
		Detail::Put_Hex(w, set.fragment[i].combiner_low);
		Detail::Put(w, " ");
		Detail::Put_Hex(w, set.fragment[i].combiner_high);
		Detail::Put(w, "\n");
	}
	Detail::Put(w, "end ");
	Detail::Put_Decimal(w, set.vertex_count);
	Detail::Put(w, " ");
	Detail::Put_Decimal(w, set.fragment_count);
	Detail::Put(w, "\n");
	return w.ok ? w.length : 0U;
}

// Parses a complete record written for expected_tag. On any failure the
// output set is left empty and false is returned.
inline bool Parse(const char *data, size_t size, const char *expected_tag, KeySet &set)
{
	Clear(set);
	if (data == NULL || size == 0U || size > kMaxFileBytes || !Valid_Tag(expected_tag)) return false;
	Detail::Reader r = { data, size, 0U };
	const char *line = NULL;
	size_t length = 0U;
	if (!Detail::Next_Line(r, line, length) ||
		length != strlen("renegade-vgl-ffp-keys 1") ||
		memcmp(line, "renegade-vgl-ffp-keys 1", length) != 0) return false;
	const size_t tag_length = strlen(expected_tag);
	if (!Detail::Next_Line(r, line, length) || length != 4U + tag_length ||
		!Detail::Starts_With(line, length, "tag ") ||
		memcmp(line + 4, expected_tag, tag_length) != 0) return false;
	bool ended = false;
	while (Detail::Next_Line(r, line, length)) {
		if (ended) {
			Clear(set);
			return false;
		}
		if (length == 10U && Detail::Starts_With(line, length, "v ")) {
			uint32_t key;
			if (!Detail::Parse_Hex8(line + 2, key) || !Add_Vertex(set, key)) {
				Clear(set);
				return false;
			}
		} else if (length == 28U && Detail::Starts_With(line, length, "f ") &&
			line[10] == ' ' && line[19] == ' ') {
			FragmentKey key;
			if (!Detail::Parse_Hex8(line + 2, key.mask) ||
				!Detail::Parse_Hex8(line + 11, key.combiner_low) ||
				!Detail::Parse_Hex8(line + 20, key.combiner_high) ||
				!Add_Fragment(set, key)) {
				Clear(set);
				return false;
			}
		} else if (Detail::Starts_With(line, length, "end ")) {
			const char *counts = line + 4;
			const size_t counts_length = length - 4U;
			const void *space = memchr(counts, ' ', counts_length);
			unsigned vertex_count = 0U;
			unsigned fragment_count = 0U;
			if (space == NULL) {
				Clear(set);
				return false;
			}
			const size_t first = static_cast<size_t>(static_cast<const char *>(space) - counts);
			if (!Detail::Parse_Count(counts, first, vertex_count) ||
				!Detail::Parse_Count(counts + first + 1U, counts_length - first - 1U, fragment_count) ||
				vertex_count != set.vertex_count || fragment_count != set.fragment_count) {
				Clear(set);
				return false;
			}
			ended = true;
		} else {
			Clear(set);
			return false;
		}
	}
	if (!ended || r.pos != r.size) {
		Clear(set);
		return false;
	}
	return true;
}

} // namespace RenegadeVitaFfpProgramKeys
