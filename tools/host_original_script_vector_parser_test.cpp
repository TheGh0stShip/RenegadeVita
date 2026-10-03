// Prepared original-owner regression. Not compiled under the build hold.
// Link original scripts.cpp, ScriptFactory and ScriptRegistrar plus the
// established compatibility/provider dependencies; do not substitute a parser.
#include "scripts.h"
#include "ScriptFactory.h"
#include <stdio.h>

class VectorFixtureFactory : public ScriptFactory
{
public:
	VectorFixtureFactory() : ScriptFactory("VectorFixture", "Value:vector3") {}
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
	return passed ? 0 : 1;
}
