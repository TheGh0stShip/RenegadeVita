/*
** Native binding for the original EA/Westwood script provider.
**
** The retail game loaded these entry points from SCRIPTS.DLL.  Vita links the
** same GPL-released registrar, ScriptImpClass implementation, and original
** Scripts.dsp code units (with this provider replacing DLLmain)
** into the application and binds them below the original ScriptManager
** boundary.  Mission logic and object ownership remain unchanged.
*/
#include "../../upstream/CnC_Renegade/Code/Scripts/scripts.h"
#include "../../upstream/CnC_Renegade/Code/Scripts/ScriptRegistrar.h"
#include "../developer/a35_script_lookup_telemetry.h"

ScriptClass *Create_Script(const char *name)
{
	ScriptClass *script = ScriptRegistrar::CreateScript(name);
	A35_Script_Lookup_Record(A35_LOOKUP_SCRIPT_FACTORY, name, 0, script != NULL);
	return script;
}

void Destroy_Script(ScriptClass *script)
{
	assert(script != NULL);
	delete script;
}

int Get_Script_Count(void)
{
	return ScriptRegistrar::Count();
}

const char *Get_Script_Name(int index)
{
	ScriptFactory *factory = ScriptRegistrar::GetScriptFactory(index);
	return factory != NULL ? factory->GetName() : NULL;
}

const char *Get_Script_Param_Description(int index)
{
	ScriptFactory *factory = ScriptRegistrar::GetScriptFactory(index);
	return factory != NULL ? factory->GetParamDescription() : NULL;
}

bool Set_Script_Commands(ScriptCommandsClass *commands)
{
	assert(commands != NULL);
	Commands = commands->Commands;
	return Commands != NULL
		&& Commands->Size == sizeof(ScriptCommands)
		&& Commands->Version == SCRIPT_COMMANDS_VERSION;
}

void Set_Request_Destroy_Func(void (*function)(ScriptClass *))
{
	assert(function != NULL);
	ScriptImpClass::Set_Request_Destroy_Func(function);
}
