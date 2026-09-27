# Renegade Vita identity

Renegade Vita uses an original R/V insignia: an angular red R with machined
stencil cuts and a steel V chevron. The geometry draws on the industrial,
military tone of *Command & Conquer: Renegade* without tracing or extracting
EA's retail emblem or the Westwood Studios logo. This is an independent port,
not an official EA or Westwood product. No retail image is required to build
or distribute this artwork.

The editable SVGs and generated application PNGs are project-authored work
distributed under this repository's GPLv3 license. This does not grant rights
to EA or Westwood names or marks; see the [license scope](../LICENSE-NOTICE.md).

## Source and generated assets

| Asset | Purpose | Size |
| --- | --- | --- |
| [`renegade-vita-mark.svg`](../assets/branding/renegade-vita-mark.svg) | Editable master monogram. | 512 × 512 source |
| [`renegade-vita-banner.svg`](../assets/branding/renegade-vita-banner.svg) | Editable LiveArea background and launch image. | 960 × 544 source |
| [`renegade-vita-startup.svg`](../assets/branding/renegade-vita-startup.svg) | Editable LiveArea gate. | 280 × 158 source |
| `sce_sys/icon0.png` | Vita application bubble. | 128 × 128 indexed PNG |
| `sce_sys/pic0.png` | Full-screen launch image. | 960 × 544 indexed PNG |
| `sce_sys/livearea/contents/bg0.png` | LiveArea background. | 840 × 500 indexed PNG |
| `sce_sys/livearea/contents/startup.png` | LiveArea gate. | 280 × 158 indexed PNG |

The build renders the candidate label into `bg0.png`, `startup.png`, and
`pic0.png`. It does not alter the master SVGs or reuse a previous candidate's
version stamp. The [`template.xml`](../assets/livearea/template.xml) binds the
background and gate through Vita's `a1` LiveArea layout. All four PNGs and the
template are packaged alongside `eboot.bin` and `param.sfo`; no retail asset is
included.

The [Dev204 Vita3K LiveArea capture](media/vita3k/dev204-livearea.png) confirms
that this candidate's background, gate, and version stamp render in the
emulator. It is not physical-Vita visual acceptance.

Generate a local preview with:

```bash
python3 tools/render_livearea.py --candidate A3.5-devNN \
  --assets assets --output build/livearea-preview
```

ImageMagick's `convert` is required. The renderer validates dimensions and
indexed PNG color type. The identity and package checks reject missing or
mis-sized Vita images. Visual appearance still requires physical Vita review;
a successful package check alone does not prove LiveArea display.

## Sources

The package layout follows [VitaSDK's VPK resource mechanism](https://github.com/vitasdk/vita-toolchain/blob/master/cmake_toolchain/vita.cmake)
and its [sample LiveArea package](https://github.com/vitasdk/samples/blob/master/hello_cpp_world/Makefile).
The [GTASA Vita LiveArea template](https://github.com/TheOfficialFloW/gtasa_vita/blob/master/sce_sys/livearea/contents/template.xml)
provided a practical `a1` template reference. No code or art was copied from
these examples.
