#pragma once

#include "gamemode.h"

// LAN transport and replication remain cNetwork/WWNet owned.  This is the
// desktop LAN-lobby callback seam; Vita's discovery UI will call the provider
// directly rather than importing the PC chat dialog stack.
class cLanChat {
public:
	void Accept_Actions(void) {}
	void Refusal_Actions(void) {}
};
class LanGameModeClass : public GameModeClass {
public:
	static cLanChat *Get_Lan_Interface(void) { return &Interface; }
	virtual const char *Name(void) { return "LAN"; }
	virtual void Init(void) {}
	virtual void Shutdown(void) {}
	virtual void Think(void) {}
	virtual void Render(void) {}
private:
	inline static cLanChat Interface;
};
#define PLC LanGameModeClass::Get_Lan_Interface()
