#pragma once
class FileClass;
class FileFactoryClass {
public:
	virtual ~FileFactoryClass() {}
	virtual FileClass *Get_File(char const *filename) = 0;
	virtual void Return_File(FileClass *file) = 0;
};
