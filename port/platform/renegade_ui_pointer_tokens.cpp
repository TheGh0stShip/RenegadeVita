#include "renegade_ui_pointer_tokens.h"

#if defined(RENEGADE_HOST_ABI_TEST)
#include <mutex>
#include <unordered_map>

namespace {

std::mutex TokenMutex;
std::unordered_map<uint32_t, void *> Tokens;
uint32_t NextToken = 1U;

uint32_t Allocate_Token(void *pointer)
{
	if (pointer == NULL) return 0U;
	std::lock_guard<std::mutex> lock(TokenMutex);
	for (;;) {
		const uint32_t token = NextToken++;
		if (token != 0U && Tokens.find(token) == Tokens.end()) {
			Tokens[token] = pointer;
			return token;
		}
	}
}

} // namespace
#endif

uint32_t Renegade_Ui_Pointer_To_Token(void *pointer)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	return Allocate_Token(pointer);
#else
	return static_cast<uint32_t>(reinterpret_cast<uintptr_t>(pointer));
#endif
}

void *Renegade_Ui_Pointer_From_Token(uint32_t token)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	if (token == 0U) return NULL;
	std::lock_guard<std::mutex> lock(TokenMutex);
	const std::unordered_map<uint32_t, void *>::const_iterator found = Tokens.find(token);
	return found == Tokens.end() ? NULL : found->second;
#else
	return reinterpret_cast<void *>(static_cast<uintptr_t>(token));
#endif
}

void *Renegade_Ui_Take_Pointer_Token(uint32_t token)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	if (token == 0U) return NULL;
	std::lock_guard<std::mutex> lock(TokenMutex);
	const std::unordered_map<uint32_t, void *>::iterator found = Tokens.find(token);
	if (found == Tokens.end()) return NULL;
	void *pointer = found->second;
	Tokens.erase(found);
	return pointer;
#else
	return reinterpret_cast<void *>(static_cast<uintptr_t>(token));
#endif
}
