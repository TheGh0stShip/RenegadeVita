#pragma once
// Minimal BufferedFileClass stand-in for the rooted file factory unit test:
// native availability probes are counted and performed with fopen.
#include <atomic>
#include <stdio.h>
#include <string.h>

extern std::atomic<unsigned> g_native_availability_probes;

class FileClass {
public:
	enum { READ = 1, WRITE = 2 };
	virtual ~FileClass() {}
};

class BufferedFileClass : public FileClass {
public:
	virtual ~BufferedFileClass() {}
	virtual char const *File_Name(void) const { return Name; }
	virtual char const *Set_Name(char const *filename)
	{
		snprintf(Name, sizeof(Name), "%s", filename);
		return Name;
	}
	virtual int Create(void) { return 1; }
	virtual int Delete(void) { return 1; }
	virtual bool Is_Available(int = false)
	{
		++g_native_availability_probes;
		FILE *file = fopen(Name, "rb");
		if (file == NULL) return false;
		fclose(file);
		return true;
	}
	virtual int Open(char const *filename, int rights = READ)
	{
		Set_Name(filename);
		return Open(rights);
	}
	virtual int Open(int = READ) { return 0; }
	virtual int Read(void *, int) { return 0; }
	virtual int Write(void const *, int size) { return size; }
	virtual bool Is_Open(void) const { return false; }
	virtual int Seek(int, int = 1) { return 0; }
	virtual int Size(void) { return 0; }
	virtual void Close(void) {}

private:
	char Name[1024] = {};
};
