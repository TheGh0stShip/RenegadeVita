#pragma once

#if defined(RENEGADE_HOST_ABI_TEST)
#include "../../platform/renegade_ui_pointer_tokens.h"
#include <cstring>

// Only for synchronous, process-local original script out-parameter events.
// Do not serialize a token or retain it in a delayed custom event.
class RenegadeHostScriptPointerExchange {
public:
	explicit RenegadeHostScriptPointerExchange(int *pointer)
		: token_(Renegade_Ui_Pointer_To_Token(pointer)) {}
	~RenegadeHostScriptPointerExchange() { Renegade_Ui_Take_Pointer_Token(token_); }
	RenegadeHostScriptPointerExchange(const RenegadeHostScriptPointerExchange &) = delete;
	RenegadeHostScriptPointerExchange &operator=(const RenegadeHostScriptPointerExchange &) = delete;
	int Parameter() const {
		static_assert(sizeof(int) == sizeof(token_), "Custom event parameter stays 32-bit");
		int parameter;
		std::memcpy(&parameter, &token_, sizeof(parameter));
		return parameter;
	}
	static int *Resolve(int parameter) {
		uint32_t token;
		std::memcpy(&token, &parameter, sizeof(token));
		return static_cast<int *>(Renegade_Ui_Pointer_From_Token(token));
	}
private:
	uint32_t token_;
};
#endif
