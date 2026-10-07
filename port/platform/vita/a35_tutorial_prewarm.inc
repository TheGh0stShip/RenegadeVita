// RVTP1 tutorial first-use preparation (M00_Tutorial.mix only, default off).
// Included by a31_vita_runtime.cpp inside its anonymous namespace, after the
// RVPL1 helpers it reuses (Level_Preload_Memory_Floor_Reached,
// Add_Level_Preload_Reference, Prewarm_Level_Sound_Definition,
// Prepare_Explosion_Choice, A35_Vita_Warm_Render_Obj); not a standalone
// translation unit. Called from Prepare_Original_Level_Loading_Resources.
//
// A user config file containing exactly "RVTP1 <hex>\n" selects a mask:
// bit 0 tutorial weapons (third-person, back and first-person models,
// first-person weapon/hands animations, clip, projectile, muzzle-flash and
// shell models, HUD weapon icons), bit 1 preset models and killed or
// projectile explosions, bit 2 decoded-PCM sounds (weapon, explosion,
// pick-up, HUD help text, EVA objectives), bit 3 the tutorial weapons' hold
// styles added to the RVPL1 soldier animation set (needs RVPL1 bit 0).
// "RVTP1 F\n" enables all. Roots: a35_tutorial_prewarm.h. Like RVPL1 this
// only loads original assets through their original owners; it creates no
// game object and changes no script, spawn, timing or RNG state.
enum {
	TUTORIAL_PREWARM_WEAPONS = 1U,
	TUTORIAL_PREWARM_PRESETS = 2U,
	TUTORIAL_PREWARM_SOUNDS = 4U,
	TUTORIAL_PREWARM_HOLD_STYLES = 8U,
	TUTORIAL_PREWARM_DEFAULT = 0U
};

static unsigned Read_Tutorial_Prewarm_Mode()
{
	unsigned mode = TUTORIAL_PREWARM_DEFAULT;
	FILE *file = fopen("ux0:data/renegade/user/config/tutorial-prewarm-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok && size == 8U && memcmp(value, "RVTP1 ", 6U) == 0 && value[7] == '\n') {
			const char digit = value[6];
			if (digit >= '0' && digit <= '9') mode = static_cast<unsigned>(digit - '0');
			else if (digit >= 'A' && digit <= 'F') mode = static_cast<unsigned>(digit - 'A' + 10);
			else if (digit >= 'a' && digit <= 'f') mode = static_cast<unsigned>(digit - 'a' + 10);
		}
	}
	return mode;
}

struct TutorialPrewarmWeapon {
	const WeaponDefinitionClass *definition;
	bool first_person;
};

struct TutorialPrewarmPlan {
	std::vector<TutorialPrewarmWeapon> weapons;
	std::vector<std::string> weapon_models;	// third-person, back, projectile, flash, shell
	std::vector<std::string> preset_models;	// soldier, vehicle and power-up physics models
	std::vector<int> explosions;			// explosion or explosion twiddler IDs
	std::vector<std::pair<int, unsigned> > sounds;
	unsigned roots;
	unsigned resolved;
	unsigned style_mask;
};

static void Add_Tutorial_Prewarm_Name(std::vector<std::string> &names, const char *name)
{
	if (name == NULL || name[0] == '\0' || stricmp(name, "NULL") == 0) return;
	for (const std::string &existing : names) {
		if (strcasecmp(existing.c_str(), name) == 0) return;
	}
	names.push_back(name);
}

// Preset model fields are file names ("vehicles\nod buggy\v_nod_buggy.w3d").
// The original owners strip the path and extension before Create_Render_Obj
// (Create_Render_Obj_From_Filename, assets.cpp:100; PhysClass::Init with
// create_render_obj_from_filename for dotted names, phys.cpp:162-170).
static void Add_Tutorial_Prewarm_Model_File(std::vector<std::string> &names, const char *filename)
{
	if (filename == NULL || filename[0] == '\0') return;
	if (strchr(filename, '.') == NULL) {
		Add_Tutorial_Prewarm_Name(names, filename);
		return;
	}
	StringClass name(true);
	Get_Render_Obj_Name_From_Filename(name, filename);
	Add_Tutorial_Prewarm_Name(names, name.Peek_Buffer());
}

static void Add_Tutorial_Prewarm_Phys_Model(std::vector<std::string> &names, int phys_def_id)
{
	if (phys_def_id == 0) return;
	DefinitionClass *definition = DefinitionMgrClass::Find_Definition(phys_def_id, false);
	if (definition == NULL ||
		SuperClassID_From_ClassID(definition->Get_Class_ID()) != CLASSID_PHYSICS) {
		return;
	}
	const StringClass &model = static_cast<PhysDefClass *>(definition)->Get_Model_Name();
	if (!model.Is_Empty()) Add_Tutorial_Prewarm_Model_File(names, model.Peek_Buffer());
}

// Sound twiddlers pick a choice at play time, so every choice is collected.
static void Add_Tutorial_Prewarm_Sound(TutorialPrewarmPlan &plan, int id, unsigned weight,
	unsigned depth = 0U)
{
	if (id <= 0 || depth >= 4U) return;
	DefinitionClass *definition = DefinitionMgrClass::Find_Definition(id, false);
	if (definition == NULL) return;
	if (definition->Get_Class_ID() == CLASSID_TWIDDLERS) {
		const TwiddlerClass *twiddler = static_cast<const TwiddlerClass *>(definition);
		for (int index = 0; index < twiddler->Get_Referenced_Definition_Count(); ++index) {
			Add_Tutorial_Prewarm_Sound(plan, twiddler->Get_Referenced_Definition_ID(index),
				weight, depth + 1U);
		}
	} else if (definition->Get_Class_ID() == CLASSID_SOUND) {
		Add_Level_Preload_Reference(plan.sounds, id, weight);
	}
}

static void Add_Tutorial_Prewarm_Explosion_Sounds(TutorialPrewarmPlan &plan, int id,
	unsigned weight, unsigned depth)
{
	if (id <= 0 || depth >= 4U) return;
	DefinitionClass *definition = DefinitionMgrClass::Find_Definition(id, false);
	if (definition == NULL) return;
	if (definition->Get_Class_ID() == CLASSID_TWIDDLERS) {
		const TwiddlerClass *twiddler = static_cast<const TwiddlerClass *>(definition);
		for (int index = 0; index < twiddler->Get_Referenced_Definition_Count(); ++index) {
			Add_Tutorial_Prewarm_Explosion_Sounds(plan,
				twiddler->Get_Referenced_Definition_ID(index), weight, depth + 1U);
		}
	} else if (definition->Get_Class_ID() == CLASSID_DEF_EXPLOSION) {
		Add_Tutorial_Prewarm_Sound(plan,
			static_cast<ExplosionDefinitionClass *>(definition)->SoundDefID, weight);
	}
}

// Prepare_Explosion_Choice expands explosion twiddlers itself.
static void Add_Tutorial_Prewarm_Explosion(TutorialPrewarmPlan &plan, int id, unsigned weight)
{
	if (id <= 0) return;
	bool seen = false;
	for (int existing : plan.explosions) {
		if (existing == id) { seen = true; break; }
	}
	if (!seen) plan.explosions.push_back(id);
	Add_Tutorial_Prewarm_Explosion_Sounds(plan, id, weight, 0U);
}

static void Add_Tutorial_Prewarm_Weapon(TutorialPrewarmPlan &plan,
	const WeaponDefinitionClass *weapon, bool first_person)
{
	if (weapon == NULL) return;
	for (TutorialPrewarmWeapon &existing : plan.weapons) {
		if (existing.definition == weapon) {
			existing.first_person = existing.first_person || first_person;
			return;
		}
	}
	const TutorialPrewarmWeapon entry = { weapon, first_person };
	plan.weapons.push_back(entry);
	if (weapon->Style >= 0 && weapon->Style < NUM_WEAPON_HOLD_STYLES) {
		plan.style_mask |= 1U << weapon->Style;
	}
	// SoldierGameObj::Set_Weapon_Model / Set_Back_Weapon_Model (soldier.cpp:3170,
	// 3226); WeaponClass muzzle flash and shell eject (weapons.cpp:1039, 1238).
	if (!weapon->Model.Is_Empty()) {
		Add_Tutorial_Prewarm_Model_File(plan.weapon_models, weapon->Model.Peek_Buffer());
	}
	if (!weapon->BackModel.Is_Empty()) {
		Add_Tutorial_Prewarm_Model_File(plan.weapon_models, weapon->BackModel.Peek_Buffer());
	}
	Add_Tutorial_Prewarm_Phys_Model(plan.weapon_models, weapon->MuzzleFlashPhysDefID);
	Add_Tutorial_Prewarm_Phys_Model(plan.weapon_models, weapon->EjectPhysDefID);
	Add_Tutorial_Prewarm_Sound(plan, weapon->ReloadSoundDefID, 1U);
	Add_Tutorial_Prewarm_Sound(plan, weapon->EmptySoundDefID, 1U);
	const int ammo_ids[2] = { weapon->PrimaryAmmoDefID, weapon->SecondaryAmmoDefID };
	for (int ammo_id : ammo_ids) {
		const AmmoDefinitionClass *ammo = WeaponManager::Find_Ammo_Definition(ammo_id);
		if (ammo == NULL) continue;
		// BulletClass creates ModelName (bullet.cpp:550); the continuous
		// emitter is a file name (weapons.cpp:1309).
		Add_Tutorial_Prewarm_Name(plan.weapon_models, ammo->ModelName.Peek_Buffer());
		if (!ammo->ContinuousEmitterName.Is_Empty()) {
			Add_Tutorial_Prewarm_Model_File(plan.weapon_models,
				ammo->ContinuousEmitterName.Peek_Buffer());
		}
		// Fire sounds play on every shot; weight them first, as RVPL1 does.
		Add_Tutorial_Prewarm_Sound(plan, ammo->FireSoundDefID, 4U);
		Add_Tutorial_Prewarm_Sound(plan, ammo->ContinuousSoundDefID, 4U);
		Add_Tutorial_Prewarm_Explosion(plan, ammo->ExplosionDefID, 2U);
	}
}

static void Add_Tutorial_Prewarm_Preset(TutorialPrewarmPlan &plan, DefinitionClass *definition,
	bool player, unsigned depth)
{
	if (definition == NULL || depth >= 4U) return;
	const uint32 class_id = definition->Get_Class_ID();
	if (class_id == CLASSID_TWIDDLERS) {
		const TwiddlerClass *twiddler = static_cast<const TwiddlerClass *>(definition);
		for (int index = 0; index < twiddler->Get_Referenced_Definition_Count(); ++index) {
			Add_Tutorial_Prewarm_Preset(plan, DefinitionMgrClass::Find_Definition(
				twiddler->Get_Referenced_Definition_ID(index), false), player, depth + 1U);
		}
		return;
	}
	if (class_id != CLASSID_GAME_OBJECT_DEF_SOLDIER && class_id != CLASSID_GAME_OBJECT_DEF_VEHICLE &&
		class_id != CLASSID_GAME_OBJECT_DEF_POWERUP && class_id != CLASSID_GAME_OBJECT_DEF_SIMPLE) {
		return;
	}
	const PhysicalGameObjDef *object = static_cast<const PhysicalGameObjDef *>(definition);
	Add_Tutorial_Prewarm_Phys_Model(plan.preset_models, object->Get_Phys_Def_ID());
	Add_Tutorial_Prewarm_Explosion(plan, object->Get_Killed_Explosion_ID(), 1U);
	if (class_id == CLASSID_GAME_OBJECT_DEF_POWERUP) {
		const PowerUpGameObjDef *powerup = static_cast<const PowerUpGameObjDef *>(definition);
		Add_Tutorial_Prewarm_Weapon(plan,
			WeaponManager::Find_Weapon_Definition(powerup->Get_Grant_Weapon_ID()), player);
	} else if (class_id != CLASSID_GAME_OBJECT_DEF_SIMPLE) {
		const ArmedGameObjDef *armed = static_cast<const ArmedGameObjDef *>(definition);
		Add_Tutorial_Prewarm_Weapon(plan,
			WeaponManager::Find_Weapon_Definition(armed->Get_Weapon_Def_ID()), false);
		Add_Tutorial_Prewarm_Weapon(plan,
			WeaponManager::Find_Weapon_Definition(armed->Get_Secondary_Weapon_Def_ID()), false);
	}
}

// Definition walk only: nothing is loaded here.
static void Build_Tutorial_Prewarm_Plan(TutorialPrewarmPlan &plan)
{
	for (const char *name : kTutorialPrewarmPlayerWeapons) {
		++plan.roots;
		const WeaponDefinitionClass *weapon = WeaponManager::Find_Weapon_Definition(name);
		if (weapon == NULL) {
			A30_Vita_Log("A4 M00 tutorial first-use plan: weapon=%s resolved=0\n", name);
			continue;
		}
		++plan.resolved;
		Add_Tutorial_Prewarm_Weapon(plan, weapon, true);
	}
	const auto add_presets = [&plan](const char *const *names, size_t count, bool player) {
		for (size_t index = 0U; index < count; ++index) {
			++plan.roots;
			DefinitionClass *definition =
				DefinitionMgrClass::Find_Named_Definition(names[index], false);
			if (definition == NULL) {
				A30_Vita_Log("A4 M00 tutorial first-use plan: preset=%s resolved=0\n",
					names[index]);
				continue;
			}
			++plan.resolved;
			Add_Tutorial_Prewarm_Preset(plan, definition, player, 0U);
		}
	};
	add_presets(kTutorialPrewarmPlayerPresets,
		sizeof(kTutorialPrewarmPlayerPresets) / sizeof(kTutorialPrewarmPlayerPresets[0]), true);
	add_presets(kTutorialPrewarmWorldPresets,
		sizeof(kTutorialPrewarmWorldPresets) / sizeof(kTutorialPrewarmWorldPresets[0]), false);
	for (const char *name : kTutorialPrewarmSounds) {
		++plan.roots;
		DefinitionClass *definition = DefinitionMgrClass::Find_Named_Definition(name, false);
		if (definition == NULL) {
			A30_Vita_Log("A4 M00 tutorial first-use plan: sound=%s resolved=0\n", name);
			continue;
		}
		++plan.resolved;
		Add_Tutorial_Prewarm_Sound(plan, static_cast<int>(definition->Get_ID()), 2U);
	}
	// Played on every Set_HUD_Help_Text (scriptcommands.cpp:3380) and
	// objectives update (objectivesviewer.cpp:245) during the tutorial.
	const GlobalSettingsDef *settings = GlobalSettingsDef::Get_Global_Settings();
	if (settings != NULL) {
		Add_Tutorial_Prewarm_Sound(plan, settings->Get_HUD_Help_Text_Sound_ID(), 8U);
		Add_Tutorial_Prewarm_Sound(plan, settings->Get_EVA_Objectives_Sound_ID(), 8U);
	}
	std::stable_sort(plan.sounds.begin(), plan.sounds.end(),
		[](const std::pair<int, unsigned> &a, const std::pair<int, unsigned> &b) {
			return a.second > b.second;
		});
}

// WeaponView first-person assets (weaponview.cpp:786-860): the F_GM_ model,
// its F_CM_ clip model, "<weapon htree>.F_GA_<name>_<IDLE|FIRE|RELOD>" and
// "F_SKELETON.F_HA_<name>_<IDLE|FIRE|RELOD|ENTER|EXIT>", all loaded when the
// star first selects the weapon. Same names and asset-manager calls;
// HAnimManager keeps hits and records misses exactly as first use would.
static void Warm_Tutorial_First_Person_Weapon(const char *filename, unsigned &models,
	unsigned &animations, unsigned &animation_misses)
{
	WW3DAssetManager *assets = WW3DAssetManager::Get_Instance();
	if (assets == NULL || filename == NULL || filename[0] == '\0') return;
	StringClass name(true);
	Get_Render_Obj_Name_From_Filename(name, filename);
	RenderObjClass *model = assets->Create_Render_Obj(name.Peek_Buffer());
	if (model == NULL) {
		A30_Vita_Log("A4 M00 tutorial first-person preparation: model=%s created=0\n",
			name.Peek_Buffer());
		return;
	}
	++models;
	const char *model_name = model->Get_Name();
	if (model_name != NULL && strlen(model_name) > 5U) {
		char clip_name[64];
		snprintf(clip_name, sizeof(clip_name), "%s", model_name);
		clip_name[2] = 'C';
		clip_name[3] = 'M';
		if (A35_Vita_Warm_Render_Obj(clip_name)) ++models;
		const char *weapon_name = model_name + 5;
		const HTreeClass *htree = model->Get_HTree();
		const char *htree_name = htree != NULL ? htree->Get_Name() : "";
		static const char *const weapon_states[] = { "IDLE", "FIRE", "RELOD" };
		static const char *const hands_states[] = { "IDLE", "FIRE", "RELOD", "ENTER", "EXIT" };
		char animation_name[128];
		for (const char *state : weapon_states) {
			snprintf(animation_name, sizeof(animation_name), "%s.F_GA_%s_%s",
				htree_name, weapon_name, state);
			HAnimClass *animation = assets->Get_HAnim(animation_name);
			if (animation != NULL) { ++animations; animation->Release_Ref(); }
			else ++animation_misses;
		}
		for (const char *state : hands_states) {
			snprintf(animation_name, sizeof(animation_name), "F_SKELETON.F_HA_%s_%s",
				weapon_name, state);
			HAnimClass *animation = assets->Get_HAnim(animation_name);
			if (animation != NULL) { ++animations; animation->Release_Ref(); }
			else ++animation_misses;
		}
	}
	model->Release_Ref();
}

// Loads the plan on the loading screen, most valuable first: first-person
// weapon sets, weapon models, explosions, sounds, then preset models (most
// are already in m00_tutorial.dep). Each indivisible original load is
// preceded by the 3 s budget check and, for vitaGL-backed work, the shared
// 24 MiB free-memory floor; the original loading screen is redrawn as the
// other preparation steps do.
static void Warm_Tutorial_First_Use_Resources(A31VitaLoadingPresenter &presenter,
	const char *label, unsigned mode, const TutorialPrewarmPlan &plan)
{
	const uint64_t started_us = sceKernelGetProcessTimeWide();
	const uint64_t time_limit_us = 3000000ULL;
	unsigned steps = 0U;
	bool memory_floor = false, time_limit = false;
	const auto may_continue = [&](bool check_memory) -> bool {
		if (time_limit || (check_memory && memory_floor)) return false;
		if (check_memory && steps % 4U == 0U && Level_Preload_Memory_Floor_Reached()) {
			memory_floor = true;
			return false;
		}
		if (sceKernelGetProcessTimeWide() - started_us > time_limit_us) {
			time_limit = true;
			return false;
		}
		if (steps != 0U && steps % 8U == 0U) {
			presenter.Render_Original_Progress("after_tutorial_first_use_prepare");
		}
		++steps;
		return true;
	};
	WW3DAssetManager *assets = WW3DAssetManager::Get_Instance();
	unsigned first_person_models = 0U, animations = 0U, animation_misses = 0U, icons = 0U;
	unsigned weapon_models = 0U, weapon_attempts = 0U;
	if ((mode & TUTORIAL_PREWARM_WEAPONS) != 0U && assets != NULL) {
		std::vector<std::string> icon_names;
		for (const TutorialPrewarmWeapon &weapon : plan.weapons) {
			if (!weapon.first_person) continue;
			if (!may_continue(true)) break;
			Warm_Tutorial_First_Person_Weapon(weapon.definition->FirstPersonModel.Peek_Buffer(),
				first_person_models, animations, animation_misses);
			// HUD weapon icons: Render2DClass::Set_Texture(const char *)
			// (render2d.cpp:133) creates them with MIP_LEVELS_1 and Inits them.
			if (weapon.definition->IconTextureName.Is_Empty()) continue;
			StringClass icon(true);
			Strip_Path_From_Filename(icon, weapon.definition->IconTextureName.Peek_Buffer());
			const size_t known = icon_names.size();
			Add_Tutorial_Prewarm_Name(icon_names, icon.Peek_Buffer());
			if (icon_names.size() == known) continue;
			TextureClass *texture = assets->Get_Texture(icon.Peek_Buffer(), TextureClass::MIP_LEVELS_1);
			if (texture != NULL) {
				texture->Init();
				texture->Release_Ref();
				++icons;
			}
		}
		for (const std::string &name : plan.weapon_models) {
			if (!may_continue(true)) break;
			++weapon_attempts;
			if (A35_Vita_Warm_Render_Obj(name.c_str())) ++weapon_models;
		}
	}
	unsigned explosions = 0U, explosion_attempts = 0U, preset_models = 0U, preset_attempts = 0U;
	if ((mode & TUTORIAL_PREWARM_PRESETS) != 0U) {
		for (int id : plan.explosions) {
			if (!may_continue(true)) break;
			DefinitionClass *definition = DefinitionMgrClass::Find_Definition(id, false);
			++explosion_attempts;
			if (Prepare_Explosion_Choice(definition,
				definition != NULL ? definition->Get_Name() : "(missing)", 0U)) ++explosions;
		}
	}
	unsigned sound_attempts = 0U, cached = 0U, present = 0U, skipped = 0U, missing = 0U;
	bool cache_full = false;
	uint64_t read_bytes = 0U, retained_bytes = 0U;
	if ((mode & TUTORIAL_PREWARM_SOUNDS) != 0U) {
		for (const std::pair<int, unsigned> &sound : plan.sounds) {
			if (sound_attempts >= 96U || !may_continue(false)) break;
			const LevelSoundPrewarmOutcome outcome =
				Prewarm_Level_Sound_Definition(sound.first, read_bytes, retained_bytes);
			if (outcome == LEVEL_SOUND_NOT_ATTEMPTED) continue;
			++sound_attempts;
			if (outcome == LEVEL_SOUND_MISSING) ++missing;
			else if (outcome == LEVEL_SOUND_CACHED) ++cached;
			else if (outcome == LEVEL_SOUND_PRESENT) ++present;
			else if (outcome == LEVEL_SOUND_FULL) { cache_full = true; break; }
			else ++skipped;
		}
	}
	if ((mode & TUTORIAL_PREWARM_PRESETS) != 0U) {
		for (const std::string &name : plan.preset_models) {
			if (!may_continue(true)) break;
			++preset_attempts;
			if (A35_Vita_Warm_Render_Obj(name.c_str())) ++preset_models;
		}
	}
	A30_Vita_Log("A4 %s tutorial first-use preparation: mode=%u roots=%u resolved=%u weapons=%u style_mask=%03X first_person_models=%u animations=%u animation_misses=%u icons=%u weapon_models=%u/%u/%u explosions=%u/%u/%u sounds=%u attempted=%u cached=%u present=%u skipped=%u missing=%u read_bytes=%llu retained_bytes=%llu cache_full=%u preset_models=%u/%u/%u memory_floor=%u time_limit=%u elapsed_us=%llu\n",
		label, mode, plan.roots, plan.resolved, static_cast<unsigned>(plan.weapons.size()),
		plan.style_mask, first_person_models, animations, animation_misses, icons,
		weapon_models, weapon_attempts, static_cast<unsigned>(plan.weapon_models.size()),
		explosions, explosion_attempts, static_cast<unsigned>(plan.explosions.size()),
		static_cast<unsigned>(plan.sounds.size()), sound_attempts, cached, present, skipped,
		missing, static_cast<unsigned long long>(read_bytes),
		static_cast<unsigned long long>(retained_bytes), cache_full ? 1U : 0U,
		preset_models, preset_attempts, static_cast<unsigned>(plan.preset_models.size()),
		memory_floor ? 1U : 0U, time_limit ? 1U : 0U,
		static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - started_us));
}
