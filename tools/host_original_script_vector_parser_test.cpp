// Retail-free original-owner regression, included in the host probe graph.
// Link original scripts.cpp, ScriptFactory and ScriptRegistrar plus the
// established compatibility/provider dependencies; do not substitute a parser.
#include "scripts.h"
#include "ScriptFactory.h"
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <initializer_list>

extern char *Renegade_Script_strtrim(char *);
extern char *strtrim(char *);
extern wchar_t *wcstrim(wchar_t *);

class VectorFixtureFactory : public ScriptFactory
{
public:
	VectorFixtureFactory(const char *description = "Value:vector3")
		: ScriptFactory("VectorFixture", description) {}
	ScriptImpClass *Create() override
	{
		ScriptImpClass *script = new ScriptImpClass;
		script->SetFactory(this);
		script->Register_Auto_Save_Variables();
		return script;
	}
};

static bool Check(VectorFixtureFactory &factory, const char *input,
	int index, float x, float y, float z)
{
	ScriptImpClass *script = factory.Create();
	script->Set_Parameters_String(input);
	const Vector3 result = script->Get_Vector3_Parameter(index);
	const bool passed = result.X == x && result.Y == y && result.Z == z;
	if (!passed) fprintf(stderr, "original vector parser failed for index%d\n", index);
	delete script;
	return passed;
}

int main()
{
	VectorFixtureFactory factory;
	bool passed = true;
	passed &= Check(factory, "1.25 -2 3", 0, 1.25F, -2.0F, 3.0F);
	passed &= Check(factory, " 1 2 3 trailing", 0, 1.0F, 2.0F, 3.0F);
	passed &= Check(factory, "1", 0, 1.0F, 0.0F, 0.0F);
	passed &= Check(factory, "1 2", 0, 1.0F, 2.0F, 0.0F);
	passed &= Check(factory, "1 bad 3", 0, 1.0F, 0.0F, 0.0F);
	passed &= Check(factory, "1 2 bad", 0, 1.0F, 2.0F, 0.0F);
	passed &= Check(factory, "bad", 0, 0.0F, 0.0F, 0.0F);
	passed &= Check(factory, "", 0, 0.0F, 0.0F, 0.0F);
	passed &= Check(factory, NULL, 0, 0.0F, 0.0F, 0.0F);
	passed &= Check(factory, "1 2 3", -1, 0.0F, 0.0F, 0.0F);
	passed &= Check(factory, "1 2 3", 1, 0.0F, 0.0F, 0.0F);
	ScriptImpClass *script = factory.Create();
	script->Set_Parameters_String("4 5 6");
	const Vector3 named = script->Get_Vector3_Parameter("vAlUe");
	const Vector3 absent = script->Get_Vector3_Parameter("Offset");
	passed &= named.X == 4.0F && named.Y == 5.0F && named.Z == 6.0F;
	passed &= absent.X == 0.0F && absent.Y == 0.0F && absent.Z == 0.0F;
	delete script;
	// Exercise original name lookup with the whitespace carried by real script
	// descriptions; keep case-insensitive matching and underscore quirks exact.
	VectorFixtureFactory parameters(" First :int,\tSecond:int, Killable_by_NotStar:int");
	script = parameters.Create();
	script->Set_Parameters_String("11,22,33");
	passed &= script->Get_Int_Parameter("fIrSt") == 11;
	passed &= script->Get_Int_Parameter("Second") == 22;
	passed &= script->Get_Int_Parameter("Killable_by_NotStar") == 33;
	passed &= script->Get_Parameter_Index("Killable_ByNotStar") == -1;
	delete script;
	for (const char *input : {"", "abc", " abc ", "\t\r\nabc\v\f ", "  x ", " \t\r\n"}) {
		char text[64];
		strcpy(text, input);
		passed &= Renegade_Script_strtrim(text) == text;
		const char *expected = *input == '\0' || strcmp(input, " \t\r\n") == 0 ? ""
			: strcmp(input, "  x ") == 0 ? "x" : "abc";
		passed &= strcmp(text, expected) == 0;
	}
	passed &= Renegade_Script_strtrim(NULL) == NULL;
	// WWLib's trailing predicate depends on the original source pointer. Keep
	// that existing short-string behavior instead of normalizing it away.
	char narrow[] = "  x ";
	wchar_t wide[] = L"  x ";
	passed &= strtrim(narrow) == narrow && strcmp(narrow, "x ") == 0;
	passed &= wcstrim(wide) == wide && wcscmp(wide, L"x ") == 0;
	wchar_t ordinary[] = L" abc ";
	passed &= wcstrim(ordinary) == ordinary && wcscmp(ordinary, L"abc") == 0;
	passed &= strtrim(NULL) == NULL && wcstrim(static_cast<wchar_t *>(NULL)) == NULL;
	return passed ? 0 : 1;
}
