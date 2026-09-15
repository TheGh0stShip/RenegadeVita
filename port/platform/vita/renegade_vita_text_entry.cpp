#include "renegade_vita_text_entry.h"
#include "renegade_text_entry_session.h"
#include "vita_runtime_log.h"
#include <psp2/apputil.h>
#include <psp2/ime_dialog.h>
#include <psp2/sysmodule.h>

namespace {
bool app_util_ready = false;
bool config_ready = false;
bool close_error_logged = false;
bool ime_module_owned = false;

struct NativeKeyboard {
    static bool Open(uint16_t *initial, uint16_t *output, size_t limit) {
        if (sceSysmoduleIsLoaded(SCE_SYSMODULE_IME) < 0) {
            const int result = sceSysmoduleLoadModule(SCE_SYSMODULE_IME);
            if (result < 0) {
                Vita_Append_A22_Runtime_Breadcrumb("text-entry", "IME module load failed code=%08X", result);
                return false;
            }
            ime_module_owned = true;
        }
        if (!app_util_ready) {
            SceAppUtilInitParam init = {};
            SceAppUtilBootParam boot = {};
            const int result = sceAppUtilInit(&init, &boot);
            if (result < 0) {
                Vita_Append_A22_Runtime_Breadcrumb("text-entry", "AppUtil init failed code=%08X", result);
                return false;
            }
            app_util_ready = true;
        }
        if (!config_ready) {
            int language = SCE_SYSTEM_PARAM_LANG_ENGLISH_US;
            int enter = SCE_SYSTEM_PARAM_ENTER_BUTTON_CROSS;
            sceAppUtilSystemParamGetInt(SCE_SYSTEM_PARAM_ID_LANG, &language);
            sceAppUtilSystemParamGetInt(SCE_SYSTEM_PARAM_ID_ENTER_BUTTON, &enter);
            SceCommonDialogConfigParam config = {};
            config.sdkVersion = PSP2_SDK_VERSION;
            config.language = static_cast<SceSystemParamLang>(language);
            config.enterButtonAssign = static_cast<SceSystemParamEnterButtonAssign>(enter);
            const int result = sceCommonDialogSetConfigParam(&config);
            if (result < 0) {
                Vita_Append_A22_Runtime_Breadcrumb("text-entry", "common dialog config failed code=%08X", result);
                return false;
            }
            config_ready = true;
        }
        static const uint16_t title[] = {'S','a','v','e',' ','d','e','s','c','r','i','p','t','i','o','n',0};
        SceImeDialogParam param;
        sceImeDialogParamInit(&param);
        // Standard firmware keyboard languages; leave the user's selection
        // unforced. This mask is also used by VitaShell's native IME provider.
        param.supportedLanguages = 0x0001FFFFULL;
        param.languagesForced = SCE_FALSE;
        param.type = SCE_IME_TYPE_DEFAULT;
        param.dialogMode = SCE_IME_DIALOG_DIALOG_MODE_WITH_CANCEL;
        param.title = title;
        param.maxTextLength = static_cast<SceUInt32>(limit);
        param.initialText = initial;
        param.inputTextBuffer = output;
        const int result = sceImeDialogInit(&param);
        close_error_logged = false;
        Vita_Append_A22_Runtime_Breadcrumb("text-entry", "native IME begin code=%08X limit=%u", result, static_cast<unsigned>(limit));
        return result >= 0;
    }
    static RenegadeTextEntry::Status Get_Status() {
        switch (sceImeDialogGetStatus()) {
        case SCE_COMMON_DIALOG_STATUS_RUNNING: return RenegadeTextEntry::Status::Running;
        case SCE_COMMON_DIALOG_STATUS_FINISHED: return RenegadeTextEntry::Status::Finished;
        default: return RenegadeTextEntry::Status::Absent;
        }
    }
    static bool Accepted() {
        SceImeDialogResult result = {};
        const int code = sceImeDialogGetResult(&result);
        Vita_Append_A22_Runtime_Breadcrumb("text-entry", "native IME result code=%08X result=%d button=%d", code, result.result, result.button);
        return code >= 0 && result.result == SCE_COMMON_DIALOG_RESULT_OK && result.button == SCE_IME_DIALOG_BUTTON_ENTER;
    }
    static bool Close() {
        const int code = sceImeDialogTerm();
        if (code < 0 && !close_error_logged) {
            Vita_Append_A22_Runtime_Breadcrumb("text-entry", "native IME termination pending code=%08X", code);
            close_error_logged = true;
        }
        return code >= 0;
    }
    static void Abort() { sceImeDialogAbort(); }
};
RenegadeTextEntry::Session<NativeKeyboard> session;
}

namespace RenegadeVitaTextEntry {
bool Begin(const void *owner, const wchar_t *text, int limit) { return session.Begin(owner, text, limit); }
bool Take_Result(const void *owner, wchar_t *text, size_t capacity) { return session.Take_Result(owner, text, capacity); }
void Cancel(const void *owner) { session.Cancel(owner); }
bool Active() { return session.Active(); }
bool Block_Input(bool neutral) { return session.Block_Input(neutral); }
void Shutdown() {
    session.Cancel_All();
    if (!session.Active() && app_util_ready) {
        sceAppUtilShutdown();
        app_util_ready = config_ready = false;
    }
    if (!session.Active() && ime_module_owned &&
            sceSysmoduleUnloadModule(SCE_SYSMODULE_IME) >= 0) ime_module_owned = false;
}
}
