# Dev143 campaign loading-screen correction

The full-port presenter previously forced backdrop 94 (`IF_LVL94LOAD`), the
original C&C multiplayer loading screen, for every campaign mission. The
original `CampaignManager` selects the backdrop from
`cGameData::Get_Mission_Number_From_Map_Name` when starting a level. Dev143
uses that original mission mapping on the full-port path: `M13.mix` selects 13;
the demo profile still selects 94 and is unchanged.

The full-port build now renders the original `LoadingScreenClass` backdrop,
translated text, and authored animation progress without the demo-only Vita
status line or demo progress scaling. The original 640x480 logical presentation
remains aspect-preserved on the Vita display. Retail assets are read from the
user's unchanged data, not packaged.

Evidence: deterministic staging with 184 ordered patches passed; 13 focused
loading/diagnostic tests passed; ARM ELF/SELF/VPK build passed. Dev143 SELF
SHA-256: `4a6d3b44905126fcdb54024e8ffbc59d57b08948bbeab962e9e41f5cc5bf1eb2`.
VPK SHA-256: `6b38acd8fed30904fc4ff325bf0d4a70e9bb3365d8f20efc35be1f82cad7342f`.
VPK inventory is only `eboot.bin` and `sce_sys/param.sfo`.

Vita3K trial 1: `campaign-dev143-retail-loading-trial-1/` in managed AppData.
The emulator stalled during frontend startup before a game window or new
runtime loading breadcrumb, so it supplies no visual-fidelity evidence. A
matching M13 campaign loading capture, retail PC reference comparison, and
physical Vita check remain open. This candidate does not establish 1:1 visual
acceptance or campaign objective completion.
