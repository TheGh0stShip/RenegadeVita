#pragma once

#include "bitpacker.h"
#include <stdint.h>
#include <string>
#include <vector>
#include <utility>

// TT b9000 resource-group messages after original WWNet reliable ordering.
// Parsing alone never downloads, mounts files, or declares a world ready.
class RenegadeTTResources {
public:
    static_assert(sizeof(ULONG) == 4 && sizeof(UINT) == 4,
        "Original bitpacker requires 32-bit words; host probes must select their ABI boundary");
    struct Group {
        uint32_t Id = 0;
        std::string Name;
        std::vector<uint32_t> Packages;
    };
    static constexpr size_t MaxGroups = 64;
    static constexpr uint32_t MaxPackages = 4096;

    bool Receive(cBitPacker &packet) {
        if (Error) return false;
        const unsigned end = packet.Get_Bit_Write_Position();
        auto read = [&](unsigned bits, uint32_t &value) {
            const unsigned start = packet.Get_Bit_Read_Position();
            if (start > end || end > packet.Get_Buffer_Size() * 8U || bits > end - start) return false;
            ULONG word = 0;
            packet.Get_Bits(word, bits);
            value = static_cast<uint32_t>(word);
            return true;
        };
        uint32_t type = 0, id = 0;
        if (!read(32, type) || type > 1) return Fail("resource subtype");
        if (type == 1) {
            if (!read(32, id) || !packet.Is_Flushed()) return Fail("resource removal");
            for (auto it = Groups.begin(); it != Groups.end(); ++it) {
                if (it->Id == id) { Groups.erase(it); break; }
            }
            ++Generation;
            return true;
        }
        if (Remaining) {
            if (!read(32, id) || !packet.Is_Flushed()) return Fail("resource package");
            Pending.Packages.push_back(id);
            if (--Remaining == 0) Commit();
            return true;
        }
        Group next;
        uint32_t length = 0, count = 0;
        if (!read(32, next.Id) || !read(16, length) || length > 255)
            return Fail("resource group header");
        for (uint32_t index = 0; index < length; ++index) {
            uint32_t byte = 0;
            if (!read(8, byte) || byte < 32 || byte > 126) return Fail("resource group name");
            next.Name.push_back(static_cast<char>(byte));
        }
        if (!read(32, count) || !packet.Is_Flushed()) return Fail("resource group count");
        size_t total = count;
        bool replacing = false;
        for (const auto &group : Groups) {
            if (group.Id == next.Id) replacing = true;
            else total += group.Packages.size();
        }
        if (total > MaxPackages || (!replacing && Groups.size() >= MaxGroups))
            return Fail("resource group limit");
        next.Packages.reserve(count);
        Pending = std::move(next);
        Remaining = count;
        if (!Remaining) Commit();
        return true;
    }
    void Reset() { Groups.clear(); Pending = Group(); Remaining = Generation = 0; Error = nullptr; }
    const std::vector<Group> &Get_Groups() const { return Groups; }
    uint32_t Get_Remaining() const { return Remaining; }
    uint32_t Get_Generation() const { return Generation; }
    const char *Get_Error() const { return Error; }
private:
    bool Fail(const char *error) { Error = error; Pending = Group(); Remaining = 0; return false; }
    void Commit() {
        for (auto &group : Groups) {
            if (group.Id == Pending.Id) {
                group = std::move(Pending);
                Pending = Group();
                ++Generation;
                return;
            }
        }
        Groups.push_back(std::move(Pending));
        Pending = Group();
        ++Generation;
    }
    std::vector<Group> Groups;
    Group Pending;
    uint32_t Remaining = 0, Generation = 0;
    const char *Error = nullptr;
};
