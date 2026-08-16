// POSIX/Vita replacement for the original Win32 Registry boundary.
//
// Combat and Commando retain RegistryClass as their configuration API.  Vita
// has no registry, so this process-local store deliberately preserves the
// original API and keeps all writable state above the retail data tree.  The
// launcher/runtime owns durable user-config serialization; this boundary never
// touches retail files or invokes Win32 registry services.

#include "registry.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// This helper is originally owned by Commando/init.cpp.  Pulling that entire
// desktop process/bootstrap translation unit into the Vita runtime would also
// pull its Win32 command-line and window lifecycle.  Keep its small, original
// registry-key composition behaviour at the already-established registry
// platform boundary instead.
// Desktop Combat/debug.cpp owns this process-global setting alongside its
// Win32 log window.  The Vita build deliberately excludes that UI owner, so
// retain the exact storage contract with the registry boundary.
char DefaultRegistryModifier[1024] = {""};

char *Build_Registry_Location_String(char *base, char *modifier, char *sub)
{
	static char whole_registry_string[1024];

	if (base == NULL || sub == NULL) {
		return NULL;
	}
	if (modifier == NULL) {
		modifier = DefaultRegistryModifier;
	}

	whole_registry_string[0] = 0;
	if (*base != 0) {
		strncpy(whole_registry_string, base, sizeof(whole_registry_string) - 1U);
		whole_registry_string[sizeof(whole_registry_string) - 1U] = 0;
	}
	if (modifier != NULL && *modifier != 0) {
		strncat(whole_registry_string, "\\\\", sizeof(whole_registry_string) - strlen(whole_registry_string) - 1U);
		strncat(whole_registry_string, modifier, sizeof(whole_registry_string) - strlen(whole_registry_string) - 1U);
	}
	if (*sub != 0) {
		strncat(whole_registry_string, "\\\\", sizeof(whole_registry_string) - strlen(whole_registry_string) - 1U);
		strncat(whole_registry_string, sub, sizeof(whole_registry_string) - strlen(whole_registry_string) - 1U);
	}
	return whole_registry_string;
}

namespace {

enum {
	MAX_REGISTRY_KEYS = 64,
	MAX_REGISTRY_VALUES = 128,
	MAX_REGISTRY_NAME = 96,
	MAX_REGISTRY_VALUE = 512
};

struct RegistryValue {
	char name[MAX_REGISTRY_NAME];
	char value[MAX_REGISTRY_VALUE];
	int binary_size;
};

struct RegistryStore {
	char path[MAX_REGISTRY_NAME];
	RegistryValue values[MAX_REGISTRY_VALUES];
	int value_count;
};

RegistryStore g_registry[MAX_REGISTRY_KEYS] = {};
int g_registry_count = 0;

int Find_Key(const char *path, bool create)
{
	if (path == NULL || path[0] == 0) {
		return -1;
	}
	for (int index = 0; index < g_registry_count; ++index) {
		if (strcmp(g_registry[index].path, path) == 0) {
			return index;
		}
	}
	if (!create || g_registry_count == MAX_REGISTRY_KEYS) {
		return -1;
	}
	RegistryStore &store = g_registry[g_registry_count];
	strncpy(store.path, path, sizeof(store.path) - 1U);
	store.path[sizeof(store.path) - 1U] = 0;
	store.value_count = 0;
	return g_registry_count++;
}

RegistryValue *Find_Value(int key, const char *name, bool create)
{
	if (key < 0 || key >= g_registry_count || name == NULL || name[0] == 0) {
		return NULL;
	}
	RegistryStore &store = g_registry[key];
	for (int index = 0; index < store.value_count; ++index) {
		if (strcmp(store.values[index].name, name) == 0) {
			return &store.values[index];
		}
	}
	if (!create || store.value_count == MAX_REGISTRY_VALUES) {
		return NULL;
	}
	RegistryValue &value = store.values[store.value_count++];
	strncpy(value.name, name, sizeof(value.name) - 1U);
	value.name[sizeof(value.name) - 1U] = 0;
	value.value[0] = 0;
	value.binary_size = 0;
	return &value;
}

void Copy_Wide_To_Narrow(const WCHAR *source, char *destination, size_t capacity)
{
	if (destination == NULL || capacity == 0U) {
		return;
	}
	size_t index = 0;
	if (source != NULL) {
		for (; source[index] != 0 && index + 1U < capacity; ++index) {
			destination[index] = source[index] <= 0x7fU ? (char)source[index] : '?';
		}
	}
	destination[index] = 0;
}

void Copy_Narrow_To_Wide(const char *source, WCHAR *destination, size_t capacity)
{
	if (destination == NULL || capacity == 0U) {
		return;
	}
	size_t index = 0;
	if (source != NULL) {
		for (; source[index] != 0 && index + 1U < capacity; ++index) {
			destination[index] = (WCHAR)(unsigned char)source[index];
		}
	}
	destination[index] = 0;
}

} // namespace

bool RegistryClass::IsLocked = false;

bool RegistryClass::Exists(const char *sub_key)
{
	return Find_Key(sub_key, false) >= 0;
}

RegistryClass::RegistryClass(const char *sub_key, bool create) : Key(-1), IsValid(false)
{
	Key = Find_Key(sub_key, create && !IsLocked);
	IsValid = Key >= 0;
}

RegistryClass::~RegistryClass(void)
{
}

int RegistryClass::Get_Int(const char *name, int def_value)
{
	RegistryValue *value = Find_Value(Key, name, false);
	return value == NULL ? def_value : (int)strtol(value->value, NULL, 10);
}

void RegistryClass::Set_Int(const char *name, int value)
{
	if (!IsLocked) {
		RegistryValue *entry = Find_Value(Key, name, true);
		if (entry != NULL) snprintf(entry->value, sizeof(entry->value), "%d", value);
	}
}

bool RegistryClass::Get_Bool(const char *name, bool def_value)
{
	return Get_Int(name, def_value ? 1 : 0) != 0;
}

void RegistryClass::Set_Bool(const char *name, bool value)
{
	Set_Int(name, value ? 1 : 0);
}

float RegistryClass::Get_Float(const char *name, float def_value)
{
	RegistryValue *value = Find_Value(Key, name, false);
	return value == NULL ? def_value : (float)strtod(value->value, NULL);
}

void RegistryClass::Set_Float(const char *name, float value)
{
	if (!IsLocked) {
		RegistryValue *entry = Find_Value(Key, name, true);
		if (entry != NULL) snprintf(entry->value, sizeof(entry->value), "%.9g", value);
	}
}

char *RegistryClass::Get_String(const char *name, char *value, int value_size,
	const char *default_string)
{
	if (value == NULL || value_size <= 0) return value;
	RegistryValue *entry = Find_Value(Key, name, false);
	const char *selected = entry == NULL ? (default_string == NULL ? "" : default_string) : entry->value;
	strncpy(value, selected, (size_t)value_size - 1U);
	value[value_size - 1] = 0;
	return value;
}

void RegistryClass::Get_String(const char *name, StringClass &string, const char *default_string)
{
	char value[MAX_REGISTRY_VALUE];
	Get_String(name, value, sizeof(value), default_string);
	string = value;
}

void RegistryClass::Set_String(const char *name, const char *value)
{
	if (!IsLocked) {
		RegistryValue *entry = Find_Value(Key, name, true);
		if (entry != NULL) {
			strncpy(entry->value, value == NULL ? "" : value, sizeof(entry->value) - 1U);
			entry->value[sizeof(entry->value) - 1U] = 0;
		}
	}
}

void RegistryClass::Get_String(const WCHAR *name, WideStringClass &string,
	const WCHAR *default_string)
{
	char narrow_name[MAX_REGISTRY_NAME];
	char narrow_default[MAX_REGISTRY_VALUE];
	char narrow_value[MAX_REGISTRY_VALUE];
	Copy_Wide_To_Narrow(name, narrow_name, sizeof(narrow_name));
	Copy_Wide_To_Narrow(default_string, narrow_default, sizeof(narrow_default));
	Get_String(narrow_name, narrow_value, sizeof(narrow_value), narrow_default);
	WCHAR wide_value[MAX_REGISTRY_VALUE];
	Copy_Narrow_To_Wide(narrow_value, wide_value, sizeof(wide_value) / sizeof(wide_value[0]));
	string = wide_value;
}

void RegistryClass::Set_String(const WCHAR *name, const WCHAR *value)
{
	char narrow_name[MAX_REGISTRY_NAME];
	char narrow_value[MAX_REGISTRY_VALUE];
	Copy_Wide_To_Narrow(name, narrow_name, sizeof(narrow_name));
	Copy_Wide_To_Narrow(value, narrow_value, sizeof(narrow_value));
	Set_String(narrow_name, narrow_value);
}

void RegistryClass::Get_Bin(const char *name, void *buffer, int buffer_size)
{
	RegistryValue *entry = Find_Value(Key, name, false);
	if (buffer != NULL && buffer_size > 0) {
		memset(buffer, 0, (size_t)buffer_size);
		if (entry != NULL) memcpy(buffer, entry->value,
			(size_t)(entry->binary_size < buffer_size ? entry->binary_size : buffer_size));
	}
}

int RegistryClass::Get_Bin_Size(const char *name)
{
	RegistryValue *entry = Find_Value(Key, name, false);
	return entry == NULL ? 0 : entry->binary_size;
}

void RegistryClass::Set_Bin(const char *name, const void *buffer, int buffer_size)
{
	if (IsLocked || buffer == NULL || buffer_size < 0) return;
	RegistryValue *entry = Find_Value(Key, name, true);
	if (entry != NULL) {
		const int copy_size = buffer_size < (int)sizeof(entry->value) ? buffer_size : (int)sizeof(entry->value);
		memcpy(entry->value, buffer, (size_t)copy_size);
		entry->binary_size = copy_size;
	}
}

void RegistryClass::Get_Value_List(DynamicVectorClass<StringClass> &list)
{
	if (Key < 0 || Key >= g_registry_count) return;
	RegistryStore &store = g_registry[Key];
	for (int index = 0; index < store.value_count; ++index) {
		list.Add(StringClass(store.values[index].name));
	}
}

void RegistryClass::Delete_Value(const char *name)
{
	if (IsLocked || Key < 0 || Key >= g_registry_count || name == NULL) return;
	RegistryStore &store = g_registry[Key];
	for (int index = 0; index < store.value_count; ++index) {
		if (strcmp(store.values[index].name, name) == 0) {
			store.values[index] = store.values[--store.value_count];
			return;
		}
	}
}

void RegistryClass::Deleta_All_Values(void)
{
	if (!IsLocked && Key >= 0 && Key < g_registry_count) g_registry[Key].value_count = 0;
}

void RegistryClass::Delete_Registry_Tree(char *) {}
void RegistryClass::Load_Registry(const char *, char *, char *) {}
void RegistryClass::Save_Registry(const char *, char *) {}
void RegistryClass::Delete_Registry_Values(HKEY) {}
void RegistryClass::Save_Registry_Tree(char *, INIClass *) {}
void RegistryClass::Save_Registry_Values(HKEY, char *, INIClass *) {}
