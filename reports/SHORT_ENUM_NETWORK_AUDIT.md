# Short-enum network serialization audit

Scope: staged `wwbitpack/bitstream.h` (BitStreamClass, base of cPacket in
`wwnet/wwpacket.h`), and Export/Import paths in `staging/commando`,
`staging/combat`, `staging/wwnet`. Static review only (8-minute timebox, no build).

## Finding: no wire-format break found from short enums

1. `staging/wwbitpack/bitstream.h:121-135` — the public `Add`/`Get` API is a
   closed set of non-template overloads (BYTE, USHORT, UINT, ULONG, char, int,
   float, plus bool). `Internal_Add`/`Internal_Get` templates (lines 147, 180)
   are private, so `sizeof(T)` / `BIT_DEPTH(T)` (lines 51-52, 170-173, 211-213)
   is only ever instantiated with those fixed-width scalars, never an enum type.
2. An uncast unscoped enum passed to `Add(...)` undergoes integral promotion
   to `int` (C++ [conv.prom]: an unscoped enum without fixed underlying type
   promotes to `int` regardless of `-fshort-enums` storage size). Promotion
   outranks conversion, so `Add(int)` is selected: 32 bits, identical to PC.
3. `Get(EnumType&)` has no matching overload (enum& cannot bind to int&), so
   any enum read must go through a scalar temporary; the source does exactly
   that, e.g. `staging/commando/gamedata.cpp:1002`
   `Set_Radar_Mode((RadarModeEnum) packet.Get(i_placeholder));`.
4. Writers already cast explicitly, preserving PC widths, e.g.
   `commando/winevent.cpp:166` `(int)Get_Win_Type()`,
   `commando/evictionevent.cpp:120`, `commando/lanchat.cpp:226,235`,
   `commando/player.cpp:996`, `commando/gamedata.cpp:977`,
   `wwnet/connect.cpp:1708`, `combat/soldier.cpp:1189` (encoded with
   BITPACK_HUMAN_STATE, width from encoder table, not sizeof),
   `commando/cstextobj.cpp:132`, `commando/sctextobj.cpp:363`,
   `commando/AnnounceEvent.cpp:134,322` (`(BYTE)` — same width on PC).
5. Grep found no `Get((int&)enumVar)` / `reinterpret_cast<int&>` reads and no
   `Add_Bits/Get_Bits(..., sizeof(enum))` in these trees.

## Residual risks (not wire-format, outside this audit's proof)

- Any `memcpy`/raw struct copy of a struct containing enum members into a
  packet or save buffer would change layout (enum fields 1-2 bytes vs 4).
  Not exhaustively checked here; worth a follow-up grep of `Add_Raw`/`memcpy`
  into packets and of ChunkSave `WRITE_MICRO_CHUNK(enum)` in save/load
  (save-game compat, not network).
- `-fshort-enums` was not found in CMakeLists.txt; arm-vita-eabi defaults
  per AAPCS/EABI config. Verify with a one-line `static_assert(sizeof(enum)==4)`
  probe in a future build.

## Recommended minimal fix (defensive, optional)

No change is required for current code. To make future regressions a compile
error rather than silent wire drift, add to BitStreamClass a deleted catch-all
plus an enum funnel at the template boundary:

```cpp
template<class E, class = typename std::enable_if<std::is_enum<E>::value>::type>
void Add(E val, int type = NO_ENCODER) { Internal_Add(static_cast<int>(val), type); }
```

(and never add an enum `Get` overload; keep reads through an `int` temporary).
Alternatively build with `-fno-short-enums` only if the struct-layout follow-up
finds raw enum copies on the wire; that flag affects VitaSDK ABI and must
match all linked libraries, so prefer the cast.
