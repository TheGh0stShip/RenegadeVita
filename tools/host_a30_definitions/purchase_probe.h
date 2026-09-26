#pragma once

#include "vendor.h"
#include "purchasesettings.h"
#include "teampurchasesettings.h"
#include "purchaserequestevent.h"
#include "networkobjectfactorymgr.h"
#include "playerdata.h"
#include "soldier.h"
#include "weaponbag.h"
#include "weapons.h"
#include "playertype.h"
#include "playerterminal.h"
#include "vehiclefactorygameobj.h"
#include "dlgcncpurchasemainmenu.h"
#include "dlgcncpurchasemenu.h"
#include "dialogmgr.h"
#include "dialogcontrol.h"
#include "resource.h"
#include "playermanager.h"
#include "player.h"
#include "renegadedialogmgr.h"
#include "gamemenu.h"
#include "a31_console_stub.h"
#include "tt_purchase_probe.h"

inline bool Validate_TT_Purchase_Availability(SoldierGameObj *star,
    PurchaseSettingsDefClass *characters, TeamPurchaseSettingsDefClass *enlisted)
{
    TTPurchaseProfileScope profile;
    BitStreamClass page_backup, team_backup;
    characters->Export_Occasional(page_backup);
    enlisted->Export_Occasional(team_backup);
    BitStreamClass page_flags, team_flags;
    TT_Purchase_Write_Flags(page_flags, 33, 1);
    TT_Purchase_Write_Flags(team_flags, 12, 1);
    characters->Import_Occasional(page_flags);
    enlisted->Import_Occasional(team_flags);
    const float balance = star->Get_Player_Data()->Get_Money();
    bool passed = !page_flags.Has_Read_Error() && !team_flags.Has_Read_Error() &&
        VendorClass::Purchase_Item(star, VendorClass::TYPE_CHARACTER, 0, -1, false) == VendorClass::PERR_NOT_IN_STOCK &&
        VendorClass::Purchase_Item(star, VendorClass::TYPE_ENLISTED_CHARACTER, 0, -1, false) == VendorClass::PERR_NOT_IN_STOCK &&
        star->Get_Player_Data()->Get_Money() == balance;
    auto *terminal = PlayerTerminalClass::Get_Instance();
    if (terminal) terminal->Display_Default_Terminal_For_Player(star);
    auto *menu = static_cast<CNCPurchaseMainMenuClass *>(DialogMgrClass::Find_Dialog(IDD_CNC_PURCHASE_MAIN_SCREEN));
    if (menu) {
        menu->On_Frame_Update();
        auto *enlisted_ctrl = menu->Get_Dlg_Item(IDC_ENLISTED_PURCHASE_01);
        passed = enlisted_ctrl && !enlisted_ctrl->Is_Enabled() && !enlisted_ctrl->Is_Visible() && passed;
        menu->On_Command(IDC_CHARACTERS_BUTTON, 0, 0);
        auto *page = static_cast<CNCPurchaseMenuClass *>(DialogMgrClass::Find_Dialog(IDD_CNC_PURCHASE_SCREEN));
        if (page) {
            page->On_Frame_Update();
            auto *item = page->Get_Dlg_Item(IDC_ITEM_1);
            passed = item && !item->Is_Enabled() && !item->Is_Visible() && passed;
            page->End_Dialog();
        } else passed = false;
        menu->End_Dialog();
    } else passed = false;
    characters->Import_Occasional(page_backup);
    enlisted->Import_Occasional(team_backup);
    passed = !page_backup.Has_Read_Error() && !team_backup.Has_Read_Error() &&
        characters->Is_Available(0) && enlisted->Is_Available(0) && passed;
    printf("multiplayer.tt_purchase_availability=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}

class PurchaseUIFixture {
public:
    PurchaseUIFixture() {
        ConsoleBox.Set_Exclusive(false);
        A4_Frontend_Begin_Pause_Loop();
        RenegadeDialogMgrClass::Initialize();
        GameModeManager::Add(&Menu);
    }
    ~PurchaseUIFixture() {
        RenegadeDialogMgrClass::Shutdown();
        Menu.Deactivate();
        GameModeManager::Remove(&Menu);
        A4_Frontend_End_Menu_Loop();
        ConsoleBox.Set_Exclusive(true);
    }
private:
    MenuGameModeClass2 Menu;
};

class RemotePurchaseProbe {
public:
    void Tick(bool server) {
        cPlayer *player = server ? cPlayerManager::Find_Player(L"PS Vita") : cNetwork::Get_My_Player_Object();
        SoldierGameObj *star = player && player->Get_GameObj() ? player->Get_GameObj()->As_SoldierGameObj() : nullptr;
        if (!star) return;
        if (!ExpectedDefinition) {
            auto team = star->Get_Player_Type() == PLAYERTYPE_NOD ?
                TeamPurchaseSettingsDefClass::TEAM_NOD : TeamPurchaseSettingsDefClass::TEAM_GDI;
            auto *catalog = TeamPurchaseSettingsDefClass::Get_Definition(team);
            if (!catalog) return;
            for (int i = 0; i < 4; ++i) {
                if (catalog->Get_Enlisted_Definition(i) &&
                    catalog->Get_Enlisted_Definition(i) != star->Get_Definition().Get_ID()) {
                    ExpectedDefinition = catalog->Get_Enlisted_Definition(i);
                    if (!server) {
                        Requested = VendorClass::Purchase_Item(star, VendorClass::TYPE_ENLISTED_CHARACTER,
                            i) == VendorClass::PERR_OPERATION_PENDING;
                    }
                    break;
                }
            }
        }
        if (!Complete && ExpectedDefinition && star->Get_Definition().Get_ID() == ExpectedDefinition) {
            Complete = server || Requested;
            printf("multiplayer.remote_purchase_%s=%s definition=%d\n",
                server ? "server" : "client", Complete ? "PASS" : "FAIL", ExpectedDefinition);
        }
    }
    bool Passed() const { return Complete; }
private:
    int ExpectedDefinition = 0;
    bool Requested = false;
    bool Complete = false;
};

inline bool Validate_Original_Purchases()
{
    SoldierGameObj *star = COMBAT_STAR;
    if (!star || !star->Get_Player_Data() || !cNetwork::I_Am_Server()) return false;
    // Let original startup harvester production finish before testing orders.
    for (int frame = 0; frame < 1800; ++frame) {
        bool busy = false;
        for (int team : {PLAYERTYPE_GDI, PLAYERTYPE_NOD}) {
            auto *base = BaseControllerClass::Find_Base(team);
            auto *building = base ? base->Find_Building(BuildingConstants::TYPE_VEHICLE_FACTORY) : nullptr;
            auto *factory = building ? building->As_VehicleFactoryGameObj() : nullptr;
            if (frame == 0)
                printf("multiplayer.purchase_factory team=%d present=%d busy=%d available=%d\n",
                    team, factory != nullptr, factory && factory->Is_Busy(), factory && factory->Is_Available());
            busy = (factory && factory->Is_Busy()) || busy;
        }
        if (!busy) break;
        A31_Interactive_Run_Simulation_Frame();
        usleep(16000);
    }
    star = COMBAT_STAR;
    if (!star || !star->Get_Player_Data()) return false;
    PurchaseUIFixture ui;
    bool passed = NetworkObjectFactoryMgrClass::Find_Factory(NETCLASSID_PURCHASEREQUESTEVENT) &&
        NetworkObjectFactoryMgrClass::Find_Factory(NETCLASSID_PURCHASERESPONSEEVENT);
    PlayerDataClass *account = star->Get_Player_Data();
    const float old_money = account->Get_Money();
    const int old_team = star->Get_Player_Type();
    for (int team = 0; team < 2; ++team) {
        star->Set_Player_Type(team == 0 ? PLAYERTYPE_GDI : PLAYERTYPE_NOD);
        auto catalog_team = static_cast<PurchaseSettingsDefClass::TEAM>(team);
        auto *characters = PurchaseSettingsDefClass::Find_Definition(
            PurchaseSettingsDefClass::TYPE_CLASSES, catalog_team);
        auto *vehicles = PurchaseSettingsDefClass::Find_Definition(
            PurchaseSettingsDefClass::TYPE_VEHICLES, catalog_team);
        auto *enlisted = TeamPurchaseSettingsDefClass::Get_Definition(
            static_cast<TeamPurchaseSettingsDefClass::TEAM>(team));
        if (!characters || !vehicles || !enlisted) return false;
        passed = Validate_TT_Purchase_Availability(star, characters, enlisted) && passed;
        BaseControllerClass *base = BaseControllerClass::Find_Base(star->Get_Player_Type());
        if (!base) return false;
        account->Set_Money(10000);
        for (const auto type : {VendorClass::TYPE_CHARACTER, VendorClass::TYPE_VEHICLE,
                VendorClass::TYPE_ENLISTED_CHARACTER, VendorClass::TYPE_SECRET_CHARACTER,
                VendorClass::TYPE_SECRET_VEHICLE, VendorClass::TYPE_SUPPLY, VendorClass::TYPE_BEACON}) {
            for (int index : {-2147483647, -1, 10, 2147483647})
                passed = VendorClass::Purchase_Item(star, type, index, -1, false) ==
                    VendorClass::PERR_NOT_IN_STOCK && passed;
            for (int alternate : {-2147483647, -2, 3, 2147483647})
                passed = VendorClass::Purchase_Item(star, type, 0, alternate, false) ==
                    VendorClass::PERR_NOT_IN_STOCK && passed;
        }
        const auto free_result = VendorClass::Purchase_Item(star,
            VendorClass::TYPE_ENLISTED_CHARACTER, 0, -1, false);
        const bool free_ok = free_result == VendorClass::PERR_SUCCESS &&
            star->Get_Definition().Get_ID() == enlisted->Get_Enlisted_Definition(0) &&
            account->Get_Money() == 10000;
        passed = free_ok && passed;

        int paid_index = -1;
        for (int i = 0; i < 10 && paid_index == -1; ++i)
            if (characters->Get_Cost(i) > 0 && characters->Get_Definition(i)) paid_index = i;
        if (paid_index == -1) return false;
        account->Set_Money(0);
        const int initial_id = star->Get_Definition().Get_ID();
        const auto denied = VendorClass::Purchase_Item(star,
            VendorClass::TYPE_CHARACTER, paid_index, -1, false);
        const bool no_funds_ok = denied == VendorClass::PERR_NO_FUNDS &&
            account->Get_Money() == 0 && star->Get_Definition().Get_ID() == initial_id;
        passed = no_funds_ok && passed;
        account->Set_Money(10000);
        const int cost = characters->Get_Cost(paid_index) * (base->Is_Base_Powered() ? 1 : 2);
        const auto bought = VendorClass::Purchase_Item(star,
            VendorClass::TYPE_CHARACTER, paid_index, -1, false);
        const bool paid_ok = bought == VendorClass::PERR_SUCCESS &&
            star->Get_Definition().Get_ID() == characters->Get_Definition(paid_index) &&
            account->Get_Money() == 10000 - cost;
        printf("multiplayer.purchase_paid team=%d result=%d expected_definition=%d actual_definition=%d cost=%d balance=%.0f soldier_factory=%d\n",
            team, bought, characters->Get_Definition(paid_index), star->Get_Definition().Get_ID(),
            cost, account->Get_Money(), base->Find_Building(BuildingConstants::TYPE_SOLDIER_FACTORY) != nullptr);
        passed = paid_ok && passed;

        auto *defense = star->Get_Defense_Object();
        defense->Set_Health(1);
        defense->Set_Shield_Strength(0);
        auto *bag = star->Get_Weapon_Bag();
        for (int i = 0; i < bag->Get_Count(); ++i) {
            auto *weapon = bag->Peek_Weapon(i);
            if (weapon && weapon->Get_Definition()->CanReceiveGenericCnCAmmo) {
                weapon->Set_Clip_Rounds(0);
                weapon->Set_Inventory_Rounds(0);
            }
        }
        const float before_refill = account->Get_Money();
        cPacket packet;
        packet.Add(cNetwork::Get_My_Id());
        packet.Add(static_cast<int>(VendorClass::TYPE_SUPPLY));
        packet.Add(0);
        packet.Add(-1);
        auto *request = new cPurchaseRequestEvent;
        request->Import_Creation(packet);
        bool refill_ok = packet.Is_Flushed() && packet.Get_Bit_Write_Position() == 128 &&
            defense->Get_Health() == defense->Get_Health_Max() &&
            defense->Get_Shield_Strength() == defense->Get_Shield_Strength_Max() &&
            account->Get_Money() == before_refill;
        for (int i = 0; i < bag->Get_Count(); ++i) {
            auto *weapon = bag->Peek_Weapon(i);
            if (weapon && weapon->Get_Definition()->CanReceiveGenericCnCAmmo)
                refill_ok = weapon->Get_Clip_Rounds() == static_cast<int>(weapon->Get_Definition()->ClipSize) &&
                    weapon->Get_Inventory_Rounds() == static_cast<int>(weapon->Get_Definition()->MaxInventoryRounds) && refill_ok;
        }
        NetworkObjectMgrClass::Delete_Pending();
        passed = refill_ok && passed;

        auto *terminal = PlayerTerminalClass::Get_Instance();
        bool menus_ok = terminal != nullptr;
        if (terminal) {
            terminal->Display_Default_Terminal_For_Player(star);
            auto *menu = static_cast<CNCPurchaseMainMenuClass *>(
                DialogMgrClass::Find_Dialog(IDD_CNC_PURCHASE_MAIN_SCREEN));
            menus_ok = menu && menu->Get_Dlg_Item(IDC_SUPPLY_PURCHASE) &&
                menu->Get_Dlg_Item(IDC_CHARACTERS_BUTTON) && menu->Get_Dlg_Item(IDC_VEHICLES_BUTTON);
            if (menu) {
                menu->On_Frame_Update();
                menu->On_Command(IDC_CHARACTERS_BUTTON, 0, 0);
                auto *catalog = static_cast<CNCPurchaseMenuClass *>(
                    DialogMgrClass::Find_Dialog(IDD_CNC_PURCHASE_SCREEN));
                menus_ok = catalog && catalog->Get_Dlg_Item(IDC_ITEM_1) && menus_ok;
                if (catalog) { catalog->On_Frame_Update(); catalog->End_Dialog(); }
                menu->End_Dialog();
            }
        }
        passed = menus_ok && passed;

        auto *building = base->Find_Building(BuildingConstants::TYPE_VEHICLE_FACTORY);
        auto *factory = building ? building->As_VehicleFactoryGameObj() : nullptr;
        int vehicle_index = -1;
        for (int i = 0; i < 10 && vehicle_index == -1; ++i)
            if (vehicles->Get_Cost(i) > 0 && vehicles->Get_Definition(i)) vehicle_index = i;
        bool vehicle_ok = factory && factory->Is_Available() && vehicle_index >= 0;
        if (vehicle_ok) {
            account->Set_Money(10000);
            const int vehicle_cost = vehicles->Get_Cost(vehicle_index) * (base->Is_Base_Powered() ? 1 : 2);
            vehicle_ok = VendorClass::Purchase_Item(star, VendorClass::TYPE_VEHICLE,
                vehicle_index, -1, false) == VendorClass::PERR_SUCCESS && factory->Is_Busy() &&
                account->Get_Money() == 10000 - vehicle_cost;
        }
        passed = vehicle_ok && passed;
        printf("multiplayer.purchase team=%d enlisted=%d insufficient_funds=%d paid_character=%d request_refill=%d menus=%d vehicle_order=%d\n",
            team, free_ok, no_funds_ok, paid_ok, refill_ok, menus_ok, vehicle_ok);
    }
    star->Set_Player_Type(old_team);
    account->Set_Money(old_money);
    printf("multiplayer.original_purchases=%s\n", passed ? "PASS" : "FAIL");
    return passed;
}
