#pragma once

// Narrow WinSock-to-native-socket boundary for original WWNet.  cConnection,
// packet scheduling, and replication retain their original implementations;
// only the obsolete WinSock spelling is translated here.

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#if defined(__vita__)
#include <psp2/net/net.h>
#else
#include <sys/ioctl.h>
#endif
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

typedef int SOCKET;
typedef struct sockaddr_in SOCKADDR_IN;
typedef struct sockaddr_in *LPSOCKADDR_IN;
typedef struct sockaddr *LPSOCKADDR;
typedef struct hostent *LPHOSTENT;
typedef struct in_addr IN_ADDR;

typedef struct _WSADATA { int unused; } WSADATA;

// Vita exposes socket nonblocking state as SO_NONBLOCK and queue state through
// SceNetSockInfo rather than the BSD ioctl request values.  These private
// compatibility tokens are only consumed by ioctlsocket below; no original
// packet or replication code observes their numeric values.
#if defined(__vita__)
#ifndef FIONBIO
#define FIONBIO 1L
#endif
#ifndef FIONREAD
#define FIONREAD 2L
#endif
#endif

static inline int WSAStartup(unsigned short, WSADATA *) { return 0; }
static inline int WSAGetLastError(void) { return errno; }
static inline void WSASetLastError(int error) { errno = error; }
static inline int closesocket(SOCKET socket)
{
#if defined(__vita__)
	return sceNetSocketClose(socket);
#else
	return close(socket);
#endif
}
static inline int ioctlsocket(SOCKET socket, long command, unsigned long *value)
{
#if defined(__vita__)
	if (value == NULL) {
		errno = EINVAL;
		return -1;
	}
	if (command == FIONBIO) {
		const int enabled = *value != 0 ? 1 : 0;
		const int result = sceNetSetsockopt(socket, SOL_SOCKET, SO_NONBLOCK,
			&enabled, sizeof(enabled));
		if (result < 0) errno = *sceNetErrnoLoc();
		return result;
	}
	if (command == FIONREAD) {
		SceNetSockInfo info;
		memset(&info, 0, sizeof(info));
		const int result = sceNetGetSockInfo(socket, &info, 1,
			SCE_NET_SOCKINFO_F_SELF);
		if (result < 0) {
			errno = *sceNetErrnoLoc();
			return -1;
		}
		*value = info.recv_queue_length > 0 ?
			(unsigned long)info.recv_queue_length : 0UL;
		return 0;
	}
	errno = EINVAL;
	return -1;
#else
	return ioctl(socket, command, value);
#endif
}

// The original sources use WinSock's int address-length pointers. Preserve
// that call shape while dispatching to the POSIX socklen_t ABI.
static inline int recvfrom(SOCKET socket, void *buffer, size_t length, int flags,
	LPSOCKADDR address, int *address_length)
{
	socklen_t native_length = address_length == NULL ? 0 : (socklen_t)*address_length;
	const ssize_t result = ::recvfrom(socket, buffer, length, flags, address,
		address_length == NULL ? NULL : &native_length);
	if (address_length != NULL) *address_length = (int)native_length;
	return (int)result;
}

static inline int getsockopt(SOCKET socket, int level, int option, void *value,
	int *value_length)
{
	socklen_t native_length = value_length == NULL ? 0 : (socklen_t)*value_length;
	const int result = ::getsockopt(socket, level, option, value,
		value_length == NULL ? NULL : &native_length);
	if (value_length != NULL) *value_length = (int)native_length;
	return result;
}

#ifndef MAKEWORD
#define MAKEWORD(low, high) ((unsigned short)(((unsigned char)(low)) | ((unsigned short)((unsigned char)(high)) << 8)))
#endif

#ifndef INVALID_SOCKET
#define INVALID_SOCKET ((SOCKET)-1)
#endif

#ifndef SOCKET_ERROR
#define SOCKET_ERROR (-1)
#endif

// Only the error values tested by the runtime are mapped to POSIX errno.
// The remainder preserve their distinct WinSock values for diagnostics, so
// the original error-name switch retains valid non-duplicate cases.
#define WSAEINTR EINTR
#define WSAEBADF EBADF
#define WSAEACCES EACCES
#define WSAEFAULT EFAULT
#define WSAEINVAL EINVAL
#define WSAEMFILE EMFILE
#define WSAEWOULDBLOCK EWOULDBLOCK
#define WSAEINPROGRESS EINPROGRESS
#define WSAEALREADY EALREADY
#define WSAENOTSOCK ENOTSOCK
#define WSAEDESTADDRREQ EDESTADDRREQ
#define WSAEMSGSIZE EMSGSIZE
#define WSAEPROTOTYPE EPROTOTYPE
#define WSAENOPROTOOPT ENOPROTOOPT
#define WSAEPROTONOSUPPORT EPROTONOSUPPORT
#define WSAESOCKTNOSUPPORT 10044
#define WSAEOPNOTSUPP EOPNOTSUPP
#define WSAEPFNOSUPPORT 10046
#define WSAEAFNOSUPPORT EAFNOSUPPORT
#define WSAEADDRINUSE EADDRINUSE
#define WSAEADDRNOTAVAIL EADDRNOTAVAIL
#define WSAENETDOWN ENETDOWN
#define WSAENETUNREACH ENETUNREACH
#define WSAENETRESET ENETRESET
#define WSAECONNABORTED ECONNABORTED
#define WSAECONNRESET ECONNRESET
#define WSAENOBUFS ENOBUFS
#define WSAEISCONN EISCONN
#define WSAENOTCONN ENOTCONN
#define WSAESHUTDOWN ESHUTDOWN
#define WSAETOOMANYREFS ETOOMANYREFS
#define WSAETIMEDOUT ETIMEDOUT
#define WSAECONNREFUSED ECONNREFUSED
#define WSAELOOP ELOOP
#define WSAENAMETOOLONG ENAMETOOLONG
#define WSAEHOSTDOWN EHOSTDOWN
#define WSAEHOSTUNREACH EHOSTUNREACH
#define WSAENOTEMPTY ENOTEMPTY
#define WSAEPROCLIM 10067
#define WSAEUSERS EUSERS
#define WSAEDQUOT EDQUOT
#define WSAESTALE ESTALE
#define WSAEREMOTE EREMOTE
#define WSASYSNOTREADY 10091
#define WSAVERNOTSUPPORTED 10092
#define WSANOTINITIALISED 10093
#define WSAEDISCON 10101
