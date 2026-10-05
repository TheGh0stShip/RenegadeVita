#include "renegade_vita_direct_ip_dialog.h"

#include "a4_frontend_lifecycle_boundary.h"
#include "renegade_network_provider.h"
#include "resource.h"
#include "popupdialog.h"
#include "editctrl.h"

namespace {
bool cancel_requested = false;
class DirectIPPopup;
DirectIPPopup *active_popup = NULL;

bool Narrow_Endpoint(const WCHAR *source, char *destination, unsigned capacity)
{
	if (source == NULL || destination == NULL || capacity == 0U) return false;
	unsigned index = 0U;
	for (; source[index] != 0; ++index) {
		if (index + 1U >= capacity || source[index] > 0x7fU) return false;
		destination[index] = static_cast<char>(source[index]);
	}
	destination[index] = '\0';
	return index != 0U;
}

bool Is_Valid_Endpoint(const WCHAR *text, char *endpoint, unsigned capacity)
{
	if (!Narrow_Endpoint(text, endpoint, capacity)) return false;
	RenegadeNetworkProvider::Endpoint parsed;
	bool tt_client = false;
	return RenegadeNetworkProvider::Parse_Client_Request(endpoint, 4848, parsed, tt_client);
}

class DirectIPPopup final : public PopupDialogClass {
public:
	DirectIPPopup() : PopupDialogClass(IDD_MP_CHANGE_LAN_NICKNAME), Waiting(false)
	{
		active_popup = this;
	}
	~DirectIPPopup() override
	{
		if (active_popup == this) active_popup = NULL;
	}

	void On_Init_Dialog() override
	{
		Set_Title(L"Direct IP");
		Enable_Dlg_Item(IDOK, false);
		EditCtrlClass *edit = static_cast<EditCtrlClass *>(Get_Dlg_Item(IDC_NICKNAME_EDIT));
		if (edit != NULL) {
			edit->Set_Text_Limit(63);
			edit->Set_Text(L"");
			edit->Set_Focus();
		}
		PopupDialogClass::On_Init_Dialog();
	}

	void On_Command(int control, int message, DWORD parameter) override
	{
		if (control == IDOK) {
			char endpoint[64];
			if (Is_Valid_Endpoint(Get_Dlg_Item_Text(IDC_NICKNAME_EDIT), endpoint,
				sizeof(endpoint)) && A4_Frontend_Latch_Direct_IP(endpoint)) {
				Waiting = true;
				Set_Title(L"Connecting");
				Enable_Dlg_Item(IDOK, false);
				Enable_Dlg_Item(IDC_NICKNAME_EDIT, false);
			}
		} else if (control == IDCANCEL && Waiting) {
			Waiting = false;
			cancel_requested = true;
		}
		PopupDialogClass::On_Command(control, message, parameter);
	}

	void On_EditCtrl_Change(EditCtrlClass *edit, int id) override
	{
		if (Waiting) return;
		char endpoint[64];
		Enable_Dlg_Item(IDOK, id == IDC_NICKNAME_EDIT && edit != NULL &&
			Is_Valid_Endpoint(edit->Get_Text(), endpoint, sizeof(endpoint)));
	}

	void On_EditCtrl_Enter_Pressed(EditCtrlClass *, int id) override
	{
		if (id == IDC_NICKNAME_EDIT && Is_Dlg_Item_Enabled(IDOK)) On_Command(IDOK, 0, 0);
	}

	bool Is_Waiting() const { return Waiting; }
	void Finish()
	{
		if (!Waiting) return;
		Waiting = false;
		End_Dialog();
	}

private:
	bool Waiting;
};
}

bool RenegadeVitaDirectIPDialog::DoDialog()
{
	cancel_requested = false;
	DirectIPPopup *dialog = new DirectIPPopup;
	if (dialog == NULL) return false;
	dialog->Start_Dialog();
	dialog->Release_Ref();
	return true;
}

bool RenegadeVitaDirectIPDialog::Take_Cancel_Request()
{
	const bool requested = cancel_requested;
	cancel_requested = false;
	return requested;
}

void RenegadeVitaDirectIPDialog::Finish_Connection()
{
	if (active_popup != NULL && active_popup->Is_Waiting()) active_popup->Finish();
}
