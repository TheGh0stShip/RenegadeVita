#pragma once

#include "packetmgr.h"
#include "crc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

inline bool Validate_Bounded_Bit_Reads()
{
	bool passed = true;
	unsigned cases = 0;
	for (unsigned offset = 0; offset < 8; ++offset) {
		for (unsigned width = 1; width <= 32; ++width) {
			for (unsigned tail = 0; tail <= 32; ++tail) {
				BitStreamClass bits;
				unsigned char *bytes = reinterpret_cast<unsigned char *>(bits.Get_Data());
				for (unsigned i = 0; i < bits.Get_Buffer_Size(); ++i) bytes[i] = i * 157 + 91;
				const unsigned end = bits.Get_Buffer_Size() * 8 - offset;
				bits.Set_Bit_Write_Position(end);
				const unsigned start = end - tail;
				ULONG value = 0;
				while (bits.Get_Bit_Read_Position() < start) {
					unsigned left = start - bits.Get_Bit_Read_Position();
					bits.Get_Bits(value, left < 32 ? left : 32);
				}
				ULONG expected = 0;
				if (width <= tail) {
					for (unsigned i = 0; i < width; ++i)
						expected = (expected << 1) | ((bytes[(start + i) / 8] >> (7 - (start + i) % 8)) & 1);
				}
				bits.Get_Bits(value, width);
				passed = value == expected && bits.Has_Read_Error() == (width > tail) && passed;
				if (width > tail) {
					BitStreamClass copy;
					copy = bits;
					passed = copy.Has_Read_Error() && copy.Is_Flushed() && passed;
					copy.Set_Bit_Write_Position(0);
					passed = !copy.Has_Read_Error() && copy.Is_Flushed() && passed;
				}
				++cases;
			}
		}
	}
	for (bool wide : {false, true}) {
		for (unsigned length : {0u, 1u, 255u, 256u, 65535u}) {
			BitStreamClass bits;
			bits.Add(static_cast<USHORT>(length));
			char narrow[256] = {};
			WCHAR utf16[256] = {};
			if (wide) bits.Get_Wide_Terminated_String(utf16, 256, true);
			else bits.Get_Terminated_String(narrow, 256, true);
			passed = bits.Has_Read_Error() == (length != 0) && bits.Is_Flushed() && passed;
		}
	}
	printf("wwnet.bounded_bit_read_cases=%u result=%s\n", cases, passed ? "PASS" : "FAIL");
	return passed;
}

inline int Validate_Original_WWNet_Packets()
{
	if (!Validate_Bounded_Bit_Reads()) return 1;
	static_assert(sizeof(PacketPackHeaderStruct) == 2, "retail packet header width");
	static_assert(sizeof(PacketDeltaHeaderStruct) == 1, "retail delta header width");
	const int tx = socket(AF_INET, SOCK_DGRAM, 0);
	const int rx = socket(AF_INET, SOCK_DGRAM, 0);
	bool passed = tx >= 0 && rx >= 0;
	sockaddr_in local = {};
	local.sin_family = AF_INET;
	local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	socklen_t size = sizeof(local);
	passed = passed && bind(rx, reinterpret_cast<sockaddr *>(&local), size) == 0 &&
		getsockname(rx, reinterpret_cast<sockaddr *>(&local), &size) == 0;
	unsigned long nonblocking = 1;
	passed = passed && ioctlsocket(rx, FIONBIO, &nonblocking) == 0;
	PacketManagerClass sender, receiver;
	sender.Set_Flush_Frequency(1000000);
	unsigned cases = 0;
	// Deliberately unaligned buffers exercise the ARM-safe word loads too.
	for (int length : {8, 17, 64, 127, 256, 500}) {
		if (!passed) break;
		unsigned char source[3][544] = {};
		for (int packet = 0; packet < 3; ++packet) {
			for (int i = 0; i < length; ++i) source[packet][i + 1] = i * 13;
			source[packet][2] ^= packet;
			passed = passed && sender.Take_Packet(source[packet] + 1, length,
				reinterpret_cast<unsigned char *>(&local.sin_addr.s_addr), local.sin_port, tx);
		}
		sender.Flush(true);
		for (int packet = 0; packet < 3 && passed; ++packet) {
			unsigned char decoded[2048], ip[4];
			unsigned short port = 0;
			int bytes = 0;
			for (int attempt = 0; attempt < 200 && bytes == 0; ++attempt) {
				bytes = receiver.Get_Packet(rx, decoded + 1, sizeof(decoded) - 1, ip, port);
				if (!bytes) usleep(1000);
			}
			passed = bytes == length && memcmp(decoded + 1, source[packet] + 1, length) == 0;
			++cases;
		}
	}
	// Inspect an actual wire packet, independently of the matching decoder.
	unsigned char payload[32] = {};
	if (passed) {
		sender.Take_Packet(payload, sizeof(payload),
			reinterpret_cast<unsigned char *>(&local.sin_addr.s_addr), local.sin_port, tx);
		sender.Flush(true);
		unsigned char wire[2048];
		int bytes = -1;
		for (int attempt = 0; attempt < 200 && bytes < 0; ++attempt) {
			bytes = recv(rx, wire, sizeof(wire), 0);
			if (bytes < 0) usleep(1000);
		}
		uint32_t crc = 0;
		if (bytes >= 4) memcpy(&crc, wire, sizeof(crc));
		passed = bytes == 4 + 2 + sizeof(payload) &&
			crc == __builtin_bswap32(static_cast<uint32_t>(CRC::Memory(wire + 4, bytes - 4))) &&
			wire[4] == 1 && wire[5] == 4 && memcmp(wire + 6, payload, sizeof(payload)) == 0;
	}
	unsigned rejected = 0;
	auto rejects = [&](const unsigned char *body, unsigned count) {
		unsigned char wire[2048] = {};
		memcpy(wire + 4, body, count);
		const uint32_t crc = __builtin_bswap32(static_cast<uint32_t>(CRC::Memory(wire + 4, count)));
		memcpy(wire, &crc, sizeof(crc));
		if (sendto(tx, reinterpret_cast<const char *>(wire), count + 4, 0,
			reinterpret_cast<sockaddr *>(&local), sizeof(local)) != count + 4) return false;
		unsigned long available = 0;
		for (int attempt = 0; attempt < 200 && !available; ++attempt) {
			if (ioctlsocket(rx, FIONREAD, &available)) return false;
			if (!available) usleep(1000);
		}
		unsigned char decoded[2048], ip[4];
		unsigned short port = 0;
		const bool rejected_packet = available &&
			receiver.Get_Packet(rx, decoded, sizeof(decoded), ip, port) == 0;
		if (rejected_packet) ++rejected;
		return rejected_packet;
	};
	// Valid CRCs must not turn truncated base packets into valid game data.
	for (unsigned count = 0; count < 32 && passed; ++count) {
		unsigned char body[34] = {1, 4}; // one 32-byte base packet
		passed = rejects(body, count);
	}
	for (unsigned size_claim = 1; size_claim <= 540 && passed; ++size_claim) {
		const uint16_t header = static_cast<uint16_t>((size_claim << 5) | 1);
		unsigned char body[2];
		memcpy(body, &header, sizeof(header));
		passed = rejects(body, sizeof(body));
	}
	// Missing delta payload, byte/chunk masks, and chained metapacket header.
	for (unsigned delta_flags = 0; delta_flags < 4 && passed; ++delta_flags) {
		unsigned char body[11] = {2, 1}; // two 8-byte packets, only base present
		body[10] = delta_flags;
		passed = rejects(body, sizeof(body));
	}
	if (passed) {
		unsigned char body[10] = {1, 129}; // more-packets bit, missing next header
		passed = rejects(body, sizeof(body));
	}
	if (tx >= 0) closesocket(tx);
	if (rx >= 0) closesocket(rx);
	printf("wwnet.original_udp_roundtrip_cases=%u\nwwnet.retail_wire_layout=%s\n",
		cases, passed ? "PASS" : "FAIL");
	printf("wwnet.malformed_packets_rejected=%u\n", rejected);
	return passed ? 0 : 1;
}
