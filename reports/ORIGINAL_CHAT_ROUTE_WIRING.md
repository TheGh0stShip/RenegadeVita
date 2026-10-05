# Original public/team chat entry source wiring

The selected `dlgmpingamechat.cpp` already owns the original chat popup,
message type, recipient resolution, command parsing and text-event send path.
The original Combat_Keyboard entry was excluded with service-specific UI, and
native gameplay services Input/Combat directly instead of calling that handler.
Thus selecting the popup alone did not connect gameplay chat input.

The new selected `commando-a36-chat-input-owner.patch` extracts the unchanged
entry block into CombatGameModeClass::Process_Chat_Input. Original desktop
Combat_Keyboard and the full native simulation input boundary share the same
method. Existing public/team edge functions, game/mission/client checks,
message-type selection, Start_Dialog and reference release are retained.
The native call runs after Input::Update, before control generation; the
existing original DialogMgr update/render path remains the dialog owner.
DialogMgr enters/exits menu input mode, which suppresses gameplay functions
through Input::Get_State. No alternative chat protocol or send loop is added.

Correction after provider inspection: Windows candidate/IME methods are stubs,
but a separate selected native provider already exists at
`port/platform/vita/renegade_vita_text_entry.cpp`. It uses SceImeDialog;
`renegade_text_entry_session.h` owns bounded UTF-16 buffers, accepted/cancelled
results and neutral-input release. The existing EditCtrl patch applies results
and cancels sessions on destruction, DirectInput blocks input during IME, and
the renderer enables common-dialog presentation. This is source evidence,
not hardware acceptance. Earlier statements that native text entry was absent
were incorrect.

Local continuation maps Select+Triangle to public chat and Select+Circle to
team chat only in non-mission gameplay. Associated Action/crouch inputs are
suppressed while those chords are active. Original T/Y BUTTON_HIT functions
own the resulting edges; existing menu input mode suppresses them in dialogs.
Campaign controls retain their prior behavior.

Cross on an edit opens the existing keyboard. Square in dialog navigation
feeds a native virtual-key edge; a selected DialogBase patch forwards it to
the focused enabled, writable edit's original Enter handler. This avoids
reopening the keyboard and reaches the chat parent's original Process_Message
and close behavior. The platform boundary does not send a network message.
The keyboard title is now generic Enter text, because the provider serves
multiple original edit fields. Cancel/submit and held-key behavior remain
unverified. Password-specific keyboard mode remains a separate open question.

Unicode entry/cancel/send, recipient behavior, repeated dialog ownership,
Vita/PSTV control usability, and controlled peer delivery remain required.
Existing in-game keyboard hints are not Vita prompts. No tests, builds,
staging execution, network connections or device actions were performed.
Local source wiring is not runtime chat acceptance.
