#pragma once

#include <sys/stat.h>
#include <unistd.h>

static inline int _mkdir(const char *path)
{
	return mkdir(path, 0777);
}
