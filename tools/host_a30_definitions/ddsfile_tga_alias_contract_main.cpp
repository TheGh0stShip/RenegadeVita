#include "ddsfile.h"
#include "ffactory.h"
#include "formconv.h"
#include "wwfile.h"

#include <algorithm>
#include <cstring>
#include <stdio.h>
#include <string>
#include <utility>
#include <vector>

class MemoryFileClass : public FileClass
{
public:
	MemoryFileClass(const char *filename, const std::vector<unsigned char> &bytes, bool available) :
		name_(filename != NULL ? filename : ""),
		bytes_(bytes),
		available_(available),
		open_(false),
		position_(0)
	{
	}

	char const *File_Name(void) const override { return name_.c_str(); }
	char const *Set_Name(char const *filename) override
	{
		name_ = filename != NULL ? filename : "";
		return name_.c_str();
	}
	int Create(void) override { return 0; }
	int Delete(void) override { return 0; }
	bool Is_Available(int forced = false) override
	{
		(void)forced;
		return available_;
	}
	bool Is_Open(void) const override { return open_; }
	int Open(char const *filename, int rights = READ) override
	{
		Set_Name(filename);
		return Open(rights);
	}
	int Open(int rights = READ) override
	{
		(void)rights;
		if (!available_) return 0;
		open_ = true;
		position_ = 0;
		return 1;
	}
	int Read(void *buffer, int size) override
	{
		if (!open_ || buffer == NULL || size <= 0) return 0;
		const int remaining = static_cast<int>(bytes_.size() - std::min(position_, bytes_.size()));
		const int count = std::min(size, remaining);
		if (count > 0) {
			std::memcpy(buffer, bytes_.data() + position_, static_cast<size_t>(count));
			position_ += static_cast<size_t>(count);
		}
		return count;
	}
	int Seek(int pos, int dir = SEEK_CUR) override
	{
		long long base = 0;
		if (dir == SEEK_CUR) {
			base = static_cast<long long>(position_);
		} else if (dir == SEEK_END) {
			base = static_cast<long long>(bytes_.size());
		}
		long long next = base + static_cast<long long>(pos);
		if (next < 0) next = 0;
		if (next > static_cast<long long>(bytes_.size())) next = static_cast<long long>(bytes_.size());
		position_ = static_cast<size_t>(next);
		return static_cast<int>(position_);
	}
	int Size(void) override { return static_cast<int>(bytes_.size()); }
	int Write(void const *buffer, int size) override
	{
		(void)buffer;
		(void)size;
		return 0;
	}
	void Close(void) override { open_ = false; }
	unsigned long Get_Date_Time(void) override { return 0x4a350049UL; }
	void Error(int error, int canretry = false, char const *filename = NULL) override
	{
		(void)error;
		(void)canretry;
		(void)filename;
	}
	void Bias(int start, int length = -1) override
	{
		(void)start;
		(void)length;
	}

private:
	std::string name_;
	std::vector<unsigned char> bytes_;
	bool available_;
	bool open_;
	size_t position_;
};

class CapturingDDSFactory : public FileFactoryClass
{
public:
	explicit CapturingDDSFactory(std::vector<unsigned char> dds_bytes) :
		dds_bytes_(std::move(dds_bytes)),
		request_count_(0)
	{
	}

	FileClass *Get_File(char const *filename) override
	{
		last_request_ = filename != NULL ? filename : "";
		++request_count_;
		return new MemoryFileClass(filename, dds_bytes_, last_request_ == "l02_mnt02.dds");
	}

	void Return_File(FileClass *file) override
	{
		delete file;
	}

	const std::string &Last_Request(void) const { return last_request_; }
	unsigned Request_Count(void) const { return request_count_; }

private:
	std::vector<unsigned char> dds_bytes_;
	std::string last_request_;
	unsigned request_count_;
};

static std::vector<unsigned char> Make_DXT1_DDS()
{
	std::vector<unsigned char> bytes;
	const char header[4] = {'D', 'D', 'S', ' '};
	bytes.insert(bytes.end(), header, header + sizeof(header));

	LegacyDDSURFACEDESC2 desc;
	std::memset(&desc, 0, sizeof(desc));
	desc.Size = sizeof(desc);
	desc.Height = 4;
	desc.Width = 4;
	desc.MipMapCount = 1;
	desc.PixelFormat.Size = sizeof(desc.PixelFormat);
	desc.PixelFormat.FourCC = D3DFMT_DXT1;

	const unsigned char *desc_bytes = reinterpret_cast<const unsigned char *>(&desc);
	bytes.insert(bytes.end(), desc_bytes, desc_bytes + sizeof(desc));

	const unsigned char block[8] = {0x00, 0xf8, 0xe0, 0x07, 0x44, 0x44, 0x44, 0x44};
	bytes.insert(bytes.end(), block, block + sizeof(block));
	return bytes;
}

static bool Check(bool value, const char *label, unsigned &checks)
{
	++checks;
	if (!value) fprintf(stderr, "FAIL: %s\n", label);
	return value;
}

int main()
{
	unsigned checks = 0;
	unsigned failures = 0;
	CapturingDDSFactory factory(Make_DXT1_DDS());
	FileFactoryClass *previous_factory = _TheFileFactory;
	_TheFileFactory = &factory;

	DDSFileClass dds("l02_mnt02.tga", 0);
	failures += !Check(factory.Last_Request() == "l02_mnt02.dds", "DDSFileClass maps tga request to dds factory lookup", checks);
	failures += !Check(factory.Request_Count() == 1, "constructor performs one factory lookup", checks);
	const bool available = dds.Is_Available();
	failures += !Check(available, "minimal DXT1 DDS header is accepted", checks);
	failures += !Check(dds.Get_Full_Width() == 4 && dds.Get_Full_Height() == 4, "DDS dimensions retained", checks);
	failures += !Check(dds.Get_Mip_Level_Count() == 1, "single mip level retained", checks);
	failures += !Check(dds.Get_Format() == WW3D_FORMAT_DXT1, "D3DFMT_DXT1 maps to WW3D_FORMAT_DXT1", checks);
	const D3DFORMAT dx8_format = WW3DFormat_To_D3DFormat(dds.Get_Format());
	failures += !Check(dx8_format == D3DFMT_DXT1, "DDS WW3D format maps back to D3DFMT_DXT1 metadata", checks);
	failures += !Check(D3DFormat_To_WW3DFormat(dx8_format) == dds.Get_Format(), "DDS DX8 metadata round-trips to WW3D format", checks);
	const bool loaded = available && dds.Load();
	failures += !Check(loaded, "DDS payload load succeeds through same dds filename", checks);
	failures += !Check(factory.Last_Request() == "l02_mnt02.dds" && factory.Request_Count() == 2, "Load reuses dds factory lookup", checks);
	failures += !Check(loaded && dds.Get_Memory_Pointer(0) != NULL && dds.Get_Level_Size(0) == 8, "DXT1 block payload is resident", checks);

	_TheFileFactory = previous_factory;
	printf("A3.5 DDSFileClass tga-alias contract: %u checks, %u failures\n", checks, failures);
	return failures == 0 ? 0 : 1;
}
