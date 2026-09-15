# License notice

This repository is a modified version and build integration of EA's officially
released *Command & Conquer: Renegade* source. The source and modifications are
distributed under **GNU General Public License v3 (GPL-3.0)**, together with
the additional terms in the upstream notice. Those terms prohibit implying EA
affiliation, grant no EA trademark rights, and require modified versions to be
identified as modified.

The complete, controlling GPLv3 text and EA additional terms are retained
verbatim in the pinned upstream source at:

`upstream/CnC_Renegade/LICENSE.md`

After cloning, initialize the submodule with:

```bash
git submodule update --init --recursive
```

Port-specific source changes in this repository are conveyed under the same
applicable GPLv3 and upstream additional terms. The root repository contains
the corresponding source, build scripts, and deterministic patch set for this
port; generated binaries and retail files are intentionally excluded.

For the canonical license text outside a populated submodule, see the official
[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html). Users must provide their
own legally obtained retail installation/data files.
