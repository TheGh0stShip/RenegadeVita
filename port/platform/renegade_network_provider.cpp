#include "renegade_network_provider.h"

#include "widestring.h"

#include <arpa/inet.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

namespace RenegadeNetworkProvider {
namespace {

const uint32_t LAN_MAGIC = 0x52564C31; // "RVL1"
const uint32_t LAN_PROTOCOL = 1;
const Port LAN_DISCOVERY_PORT = 25300;

class UdpDatagramTransport : public DatagramTransport {
public:
	UdpDatagramTransport() : Socket(-1), BoundPort(0) {}
	virtual ~UdpDatagramTransport() { Close(); }

	bool Open(Port local_port) {
		Close();
		Socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
		if (Socket < 0) return false;
		int enabled = 1;
		setsockopt(Socket, SOL_SOCKET, SO_BROADCAST, &enabled, sizeof(enabled));
		int flags = fcntl(Socket, F_GETFL, 0);
		if (flags >= 0) fcntl(Socket, F_SETFL, flags | O_NONBLOCK);
		struct sockaddr_in address;
		memset(&address, 0, sizeof(address));
		address.sin_family = AF_INET;
		address.sin_addr.s_addr = htonl(INADDR_ANY);
		address.sin_port = htons(local_port);
		if (bind(Socket, (struct sockaddr *)&address, sizeof(address)) != 0) {
			Close();
			return false;
		}
		socklen_t size = sizeof(address);
		if (getsockname(Socket, (struct sockaddr *)&address, &size) != 0) {
			Close();
			return false;
		}
		BoundPort = ntohs(address.sin_port);
		return true;
	}

	void Close() {
		if (Socket >= 0) close(Socket);
		Socket = -1;
		BoundPort = 0;
	}

	bool Send(const Endpoint &destination, const void *data, size_t bytes) {
		if (Socket < 0 || data == NULL || bytes == 0) return false;
		struct sockaddr_in address;
		memset(&address, 0, sizeof(address));
		address.sin_family = AF_INET;
		address.sin_addr.s_addr = htonl(destination.Address);
		address.sin_port = htons(destination.PortNumber);
		return sendto(Socket, data, bytes, 0, (struct sockaddr *)&address, sizeof(address)) == (ssize_t)bytes;
	}

	int Receive(void *data, size_t capacity, Endpoint &sender) {
		if (Socket < 0 || data == NULL || capacity == 0) return 0;
		struct sockaddr_in address;
		socklen_t size = sizeof(address);
		const int received = recvfrom(Socket, data, capacity, 0, (struct sockaddr *)&address, &size);
		if (received <= 0) return 0;
		sender.Address = ntohl(address.sin_addr.s_addr);
		sender.PortNumber = ntohs(address.sin_port);
		return received;
	}

	Port Local_Port() const { return BoundPort; }

private:
	int Socket;
	Port BoundPort;
};

struct LanBeacon {
	uint32_t Magic;
	uint32_t Version;
	uint16_t GamePort;
	char ServerName[64];
};

class LanDiscovery : public DiscoveryProvider {
public:
	LanDiscovery() : Transport(NULL), GamePort(0) {}
	virtual ~LanDiscovery() { Stop(); }

	bool Start_Lan(Port listen_port) {
		Stop();
		Transport = Create_Datagram_Transport();
		if (Transport == NULL || !Transport->Open(listen_port ? listen_port : LAN_DISCOVERY_PORT)) {
			Stop();
			return false;
		}
		return true;
	}

	void Stop() {
		if (Transport != NULL) Destroy_Datagram_Transport(Transport);
		Transport = NULL;
		GamePort = 0;
	}

	bool Announce(const char *server_name, Port game_port) {
		if (Transport == NULL) return false;
		LanBeacon beacon;
		memset(&beacon, 0, sizeof(beacon));
		beacon.Magic = htonl(LAN_MAGIC);
		beacon.Version = htonl(LAN_PROTOCOL);
		beacon.GamePort = htons(game_port);
		if (server_name != NULL) strncpy(beacon.ServerName, server_name, sizeof(beacon.ServerName) - 1);
		GamePort = game_port;
		return Transport->Send(Endpoint(0xffffffffU, LAN_DISCOVERY_PORT), &beacon, sizeof(beacon));
	}

	bool Poll(DiscoveryRecord &record) {
		if (Transport == NULL) return false;
		LanBeacon beacon;
		Endpoint sender;
		if (Transport->Receive(&beacon, sizeof(beacon), sender) != (int)sizeof(beacon)) return false;
		if (ntohl(beacon.Magic) != LAN_MAGIC || ntohl(beacon.Version) != LAN_PROTOCOL) return false;
		record.Host = sender;
		record.Host.PortNumber = ntohs(beacon.GamePort);
		record.ProtocolVersion = LAN_PROTOCOL;
		memcpy(record.ServerName, beacon.ServerName, sizeof(record.ServerName));
		record.ServerName[sizeof(record.ServerName) - 1] = '\0';
		return true;
	}

private:
	DatagramTransport *Transport;
	Port GamePort;
};

PublicDiscoveryProvider *PublicProvider = NULL;

} // namespace

DatagramTransport *Create_Datagram_Transport() { return new UdpDatagramTransport; }
void Destroy_Datagram_Transport(DatagramTransport *transport) { delete transport; }
DiscoveryProvider *Create_Lan_Discovery_Provider() { return new LanDiscovery; }
void Destroy_Discovery_Provider(DiscoveryProvider *provider) { delete provider; }
void Set_Public_Discovery_Provider(PublicDiscoveryProvider *provider) { PublicProvider = provider; }
PublicDiscoveryProvider *Get_Public_Discovery_Provider() { return PublicProvider; }
bool Public_Service_Active() { return PublicProvider != NULL && PublicProvider->Is_Available(); }

bool Parse_Direct_IP(const char *text, Port default_port, Endpoint &endpoint) {
	if (text == NULL || *text == '\0') return false;
	char copy[64];
	strncpy(copy, text, sizeof(copy) - 1);
	copy[sizeof(copy) - 1] = '\0';
	char *port_text = strrchr(copy, ':');
	Port port = default_port;
	if (port_text != NULL) {
		*port_text++ = '\0';
		char *end = NULL;
		unsigned long parsed = strtoul(port_text, &end, 10);
		if (end == port_text || *end != '\0' || parsed == 0 || parsed > 65535) return false;
		port = (Port)parsed;
	}
	struct in_addr address;
	if (inet_pton(AF_INET, copy, &address) != 1 || port == 0) return false;
	endpoint.Address = ntohl(address.s_addr);
	endpoint.PortNumber = port;
	return true;
}

} // namespace RenegadeNetworkProvider

namespace {
WideStringClass GameSpyCompatibilityPassword;
bool GameSpyCompatibilityListed = false;
}

bool cGameSpyAdmin::Is_Gamespy_Game(void) { return RenegadeNetworkProvider::Public_Service_Active(); }
bool cGameSpyAdmin::Get_Is_Server_Gamespy_Listed(void) { return GameSpyCompatibilityListed && Is_Gamespy_Game(); }
void cGameSpyAdmin::Set_Is_Server_Gamespy_Listed(bool flag) { GameSpyCompatibilityListed = flag; }
void cGameSpyAdmin::Set_Password_Attempt(WideStringClass &password) { GameSpyCompatibilityPassword = password; }
WideStringClass &cGameSpyAdmin::Get_Password_Attempt(void) { return GameSpyCompatibilityPassword; }
