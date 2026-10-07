"""Walk the retail campaign.ini chain the way CampaignManager::Continue does.

Read-only: campaign.ini is read in memory from the user's retail always.dat and
only directive names, archive/movie names and pass/fail status are printed.
No retail payload is written.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.renegade_cinematic_dependency_scan import MixArchive  # noqa: E402


def read_member(archive_path, name):
    archive = MixArchive(archive_path)
    entry = archive.entries.get(name.lower())
    if entry is None:
        return None
    _crc, offset, size = entry
    with archive_path.open("rb") as stream:
        stream.seek(offset)
        return stream.read(size)


def parse_ini(text):
    """Ordered sections/entries; mirrors INIClass comment and trim rules."""
    sections, current = {}, None
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line:
            current = line[1:line.index("]")].strip()
            sections.setdefault(current, [])
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            sections[current].append((key.strip(), value.strip()))
    return sections


def resolve_ci(root, logical):
    """Case-insensitive per-component lookup, as Renegade_Resolve_Path does."""
    path = root
    for part in logical.replace("\\", "/").split("/"):
        if not part:
            continue
        if not path.is_dir():
            return None
        names = {child.name.lower(): child for child in path.iterdir()}
        path = names.get(part.lower())
        if path is None:
            return None
    return path


def mission_number(map_name):
    if map_name[:5].lower() == "m00_t":
        return 90
    digits = ""
    for ch in map_name[1:]:
        if not ch.isdigit():
            break
        digits += ch
    return int(digits) if digits else 0


def walk(retail_root):
    data = resolve_ci(retail_root, "Data")
    if data is None:
        raise SystemExit(f"retail Data directory missing under {retail_root}")
    always = resolve_ci(data, "always.dat")
    payload = read_member(always, "campaign.ini") if always else None
    if payload is None:
        raise SystemExit("campaign.ini not found in always.dat")
    ini = parse_ini(payload.decode("latin-1"))
    flow = [value for _key, value in ini.get("Campaign", [])]
    backdrops = {int(name[8:]) for name in ini if name.startswith("Backdrop") and
                 name[8:].isdigit() and ini[name]}
    steps, failures = [], []
    state = -1  # Start_Campaign
    while True:
        if state >= len(flow) - 1:
            steps.append({"state": state, "directive": "END",
                          "action": "End_Game + Display_End_Game_Menu (LOC_MAIN_MENU)", "ok": True})
            break
        state += 1
        directive = flow[state]
        step = {"state": state, "directive": directive, "ok": True}
        if directive.startswith("Level "):
            parts = directive[6:].split()
            archive = parts[0] if parts else ""
            number = mission_number(archive)
            found = resolve_ci(data, archive) is not None
            step.update(archive=archive, archive_present=found,
                        backdrop=number, backdrop_present=number in backdrops,
                        autosave=archive[:3].lower() != "m13",
                        single_arg=len(parts) == 1 and "." in archive)
            step["ok"] = found and number in backdrops and step["single_arg"]
        elif directive.startswith("Movie "):
            parts = directive[6:].split()
            movie = parts[0] if parts else ""
            resolved = resolve_ci(retail_root, movie) if movie else None
            step.update(movie=movie, unlock=parts[1] if len(parts) > 1 else "",
                        movie_present=resolved is not None,
                        on_disk=str(resolved.relative_to(retail_root)) if resolved else None)
            step["ok"] = resolved is not None and len(parts) >= 2
        elif directive.startswith("Score"):
            step["action"] = "Save_Stats + End_Game + ScoreScreen; On_Destroy -> Continue"
        elif directive.startswith("Message "):
            step["action"] = "End_Game + ScoreScreen"
        else:
            step["ok"] = False
        if not step["ok"]:
            failures.append(step)
        steps.append(step)
    levels = [s["archive"] for s in steps if "archive" in s]
    return {"flow_entries": len(flow), "backdrops": sorted(backdrops),
            "level_order": levels, "steps": steps, "failures": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retail-root", type=Path, required=True,
                        help="directory containing Data/ (Vita retail root)")
    args = parser.parse_args()
    report = walk(args.retail_root)
    print(json.dumps(report, indent=1))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
