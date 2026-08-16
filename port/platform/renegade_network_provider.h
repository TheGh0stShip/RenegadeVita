#pragma once

// Native replacement boundary for the retired GameSpy service.  The original
// cNetwork/WWNet object graph remains the replication authority; this file
// owns only transport discovery and optional public-directory integration.
// A future W3D Hub/TT provider implements PublicDiscoveryProvider and is
// registered here without changing Combat or Commando network code.

#include <stddef.h>
#include <stdint.h>

class WideStringClass;

namespace RenegadeNetworkProvider {

typedef uint32_t IPv4Address;
typedef uint16_t Port;

struct Endpoint {
	IPv4Address Address; // host byte order
	Port PortNumber;
	Endpoint(IPv4Address address = 0, Port port = 0)
		: Address(address), PortNumber(port) {}
};

struct DiscoveryRecord {
	Endpoint Host;
	char ServerName[64];
	uint32_t ProtocolVersion;
};

// Datagram ownership is deliberately below cNetwork.  WWNet still controls
// connection state, reliability, packets, and replicated objects.
class DatagramTransport {
public:
	virtual ~DatagramTransport() {}
	virtual bool Open(Port local_port) = 0;
	virtual void Close() = 0;
	virtual bool Send(const Endpoint &destination, const void *data, size_t bytes) = 0;
	virtual int Receive(void *data, size_t capacity, Endpoint &sender) = 0;
	virtual Port Local_Port() const = 0;
};

DatagramTransport *Create_Datagram_Transport();
void Destroy_Datagram_Transport(DatagramTransport *transport);

// LAN discovery is a lightweight UDP broadcast capability.  It does not
// publish to, authenticate with, or depend on any Internet service.
class DiscoveryProvider {
public:
	virtual ~DiscoveryProvider() {}
	virtual bool Start_Lan(Port listen_port) = 0;
	virtual void Stop() = 0;
	virtual bool Announce(const char *server_name, Port game_port) = 0;
	virtual bool Poll(DiscoveryRecord &record) = 0;
};

DiscoveryProvider *Create_Lan_Discovery_Provider();
void Destroy_Discovery_Provider(DiscoveryProvider *provider);

// Optional public directories are explicitly capability-based.  The default
// provider is null; W3D Hub/TT can be added later without changing cNetwork.
class PublicDiscoveryProvider {
public:
	virtual ~PublicDiscoveryProvider() {}
	virtual bool Is_Available() const = 0;
	virtual bool Publish(const DiscoveryRecord &record) = 0;
	virtual bool Query(DiscoveryRecord *records, size_t capacity, size_t &count) = 0;
};

void Set_Public_Discovery_Provider(PublicDiscoveryProvider *provider);
PublicDiscoveryProvider *Get_Public_Discovery_Provider();
bool Public_Service_Active();

// Direct-IP remains a first-class baseline capability.  Parsing is kept at
// this boundary so menu/UI code need not own socket syntax.
bool Parse_Direct_IP(const char *text, Port default_port, Endpoint &endpoint);

} // namespace RenegadeNetworkProvider

// Transitional source-level bridge for original Commando files that already
// ask cGameSpyAdmin only about public-service state.  This is not GameSpy:
// all answers route to the provider boundary and default to no public service.
class cGameSpyAdmin {
public:
	static bool Is_Gamespy_Game(void);
	static bool Get_Is_Launched_From_Gamespy(void) { return false; }
	static bool Is_Nickname_Collision(WideStringClass &) { return false; }
	static bool Get_Is_Server_Gamespy_Listed(void);
	static void Set_Is_Server_Gamespy_Listed(bool flag);
	static void Set_Password_Attempt(WideStringClass &password);
	static WideStringClass &Get_Password_Attempt(void);
};
