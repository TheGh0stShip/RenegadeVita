// Vita boundary for the desktop IMM candidate-control ABI.
//
// WWUIInput is patched to disable IME creation on Vita because there is no
// Win32 IMM context.  The original candidate control remains part of the UI
// graph, however, and retains calls to this small value object.  Keep that
// object inert and deterministic rather than importing desktop composition
// APIs or fabricating text input.

#include "IMECandidate.h"

#include <string.h>

namespace IME {

IMECandidate::IMECandidate()
	: mIndex(-1),
	  mHWND(NULL),
	  mCodePage(CP_ACP),
	  mUseUnicode(true),
	  mStartFrom1(true),
	  mCandidateSize(0),
	  mCandidates(NULL)
{
	mTempString[0] = 0;
}

IMECandidate::~IMECandidate() = default;

void IMECandidate::Open(int index, HWND hwnd, UINT codepage, bool unicode,
	bool start_from_1)
{
	mIndex = index;
	mHWND = hwnd;
	mCodePage = codepage;
	mUseUnicode = unicode;
	mStartFrom1 = start_from_1;
}

void IMECandidate::Read(void) {}

void IMECandidate::Close(void)
{
	mIndex = -1;
	mHWND = NULL;
	mCandidates = NULL;
	mCandidateSize = 0;
	mTempString[0] = 0;
}

bool IMECandidate::IsValid(void) const { return false; }
int IMECandidate::GetIndex(void) const { return mIndex; }
unsigned long IMECandidate::GetStyle(void) const { return 0; }
unsigned long IMECandidate::GetPageStart(void) const { return 0; }
void IMECandidate::SetPageStart(unsigned long) {}
unsigned long IMECandidate::GetPageSize(void) const { return 0; }
unsigned long IMECandidate::GetCount(void) const { return 0; }
unsigned long IMECandidate::GetSelection(void) const { return 0; }
const wchar_t *IMECandidate::GetCandidate(unsigned long)
{
	mTempString[0] = 0;
	return mTempString;
}
void IMECandidate::SelectCandidate(unsigned long) {}
void IMECandidate::SetView(unsigned long, unsigned long) {}
bool IMECandidate::IsStartFrom1(void) const { return mStartFrom1; }

} // namespace IME
