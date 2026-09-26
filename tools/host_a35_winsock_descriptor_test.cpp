#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include <cassert>
#include <cstdio>

// Model Vita libc's SO_NONBLOCK extension using real host descriptors. Any
// accidental raw SceNet call fails to link; descriptor/close behavior is real.
#define SO_NONBLOCK 0x1100
static int last_descriptor = -1;
static int Native_Setsockopt(int descriptor, int level, int option,
    const void *value, socklen_t size)
{
    assert(level == SOL_SOCKET && option == SO_NONBLOCK && size == sizeof(int));
    last_descriptor = descriptor;
    const int flags = fcntl(descriptor, F_GETFL, 0);
    if (flags < 0) return -1;
    return fcntl(descriptor, F_SETFL,
        *static_cast<const int *>(value) ? flags | O_NONBLOCK : flags & ~O_NONBLOCK);
}
#define __vita__ 1
#define setsockopt Native_Setsockopt
#include "winsock.h"
#undef setsockopt

int main()
{
    const int descriptor = socket(AF_INET, SOCK_DGRAM, 0);
    assert(descriptor >= 0);
    unsigned long enabled = 1;
    assert(ioctlsocket(descriptor, FIONBIO, &enabled) == 0);
    assert(last_descriptor == descriptor && (fcntl(descriptor, F_GETFL) & O_NONBLOCK));
    char byte;
    assert(recv(descriptor, &byte, 1, MSG_DONTWAIT) == -1 && errno == EAGAIN);
    enabled = 0;
    assert(ioctlsocket(descriptor, FIONBIO, &enabled) == 0);
    assert(!(fcntl(descriptor, F_GETFL) & O_NONBLOCK));
    assert(ioctlsocket(descriptor, FIONBIO, nullptr) == -1 && errno == EINVAL);
    assert(ioctlsocket(descriptor, FIONREAD, &enabled) == -1 && errno == ENOSYS);
    assert(closesocket(descriptor) == 0);
    assert(fcntl(descriptor, F_GETFD) == -1 && errno == EBADF);
    assert(closesocket(descriptor) == -1 && errno == EBADF);
    puts("Vita libc descriptor boundary model: PASS");
}
