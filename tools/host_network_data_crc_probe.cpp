// Synthetic FileClass/factory surface for the unchanged extracted cNetwork
// method. Compile the actual staged method, not a second checksum algorithm.
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "realcrc.h"

static bool NetworkDataCRCValid = false;
static int mode, max_read, acquired, returned, open_count, read_count;
struct StringClass {
    std::string value;
    StringClass(const char *text) : value(text) {}
    char &operator[](int index) { return value[index]; }
    const char *Peek_Buffer() const { return value.c_str(); }
};
struct FileClass {
    enum { READ = 1 };
    std::vector<unsigned char> data;
    bool available, opened = false;
    size_t position = 0;
    bool Is_Available() { return available; }
    int Size() { std::abort(); }
    int Open(int rights) {
        if (rights != READ || opened) std::abort();
        if (mode == 1) return 0;
        opened = true;
        ++open_count;
        return 1;
    }
    int Read(void *buffer, int size) {
        if (!opened || size != 16384) std::abort();
        ++read_count;
        if (position && mode == 2) return -1;
        if (mode == 3) return size + 1;
        if (mode == 4) return 0;
        int amount = std::min(size, std::min(max_read, int(data.size() - position)));
        if (amount) std::memcpy(buffer, data.data() + position, amount);
        position += amount;
        return amount;
    }
    void Close() { if (!opened) std::abort(); opened = false; --open_count; }
};
struct Factory {
    FileClass *Get_File(const StringClass &name) {
        if (name.value != "objects.ddb" && name.value != "armor.ini" &&
            name.value != "c_gdi_syd_l0.w3d") return nullptr;
        ++acquired;
        FileClass *file = new FileClass;
        file->available = name.value != "armor.ini";
        if (name.value == "objects.ddb") {
            file->data.resize(256 * 131);
            for (size_t i = 0; i < file->data.size(); ++i) file->data[i] = i & 255;
        } else {
            const char value[] = "repeated-entry";
            file->data.assign(value, value + sizeof(value) - 1);
        }
        return file;
    }
    void Return_File(FileClass *file) {
        if (!file || file->opened) std::abort();
        delete file;
        ++returned;
    }
};
static Factory factory;
static Factory *_TheFileFactory = &factory;
struct cNetwork { static int Get_Data_Files_CRC(); };
#include "network_data_crc.inc"

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    mode = std::atoi(argv[1]);
    max_read = std::atoi(argv[2]);
    if (max_read <= 0) return 2;
    const unsigned first = cNetwork::Get_Data_Files_CRC();
    const bool first_valid = NetworkDataCRCValid;
    const int first_reads = read_count;
    mode = 0;
    const unsigned second = cNetwork::Get_Data_Files_CRC();
    std::printf("%u %d %u %d %d %d %d %d %d\n", first, first_valid, second,
        NetworkDataCRCValid, acquired, returned, open_count, first_reads, read_count);
    return acquired == returned && open_count == 0 ? 0 : 1;
}
