"""Read-only literal preset/cinematic dependency tracing across retail archives.

Archive collision alternatives are scanned conservatively and hashed. This is
not a claim that a particular archive mount order or branch executes at runtime.
"""
import hashlib
import re
if __package__:
    from .renegade_cinematic_dependency_scan import MixArchive, parse_command
else:
    from renegade_cinematic_dependency_scan import MixArchive, parse_command


def literal_presets(source):
    # Create_Object_At_Bone and Give_PowerUp take the object as argument one.
    first = r'Commands\s*->\s*(?:Create_Object|Create_Explosion|Create_Explosion_At_Bone|Create_Sound|Create_2D_Sound)\s*\(\s*"([^"\n]+)"'
    second = r'Commands\s*->\s*(?:Create_Object_At_Bone|Give_PowerUp)\s*\([^,;]+,\s*"([^"\n]+)"'
    return set(re.findall(first, source) + re.findall(second, source))


class DeepContentDependencies:
    def __init__(self, directory, mission):
        self.archives = [mission]
        # Global archives only: other missions are not presumed mounted.
        for p in sorted(directory.iterdir()):
            if p.name.lower().startswith('always') and p.suffix.lower() in ('.dat', '.dbs', '.mix'):
                self.archives.append(MixArchive(p))
        self.visited = set()
        self.records = []
        self.missing = set()
        self.edges = []

    def from_source(self, source, script):
        presets = literal_presets(source)
        names = set(re.findall(r'"([^"\n]+\.txt)"', source, re.I))
        scripts = set()
        pending = [(n.lower(), script) for n in sorted(names)]
        while pending:
            name, origin = pending.pop()
            self.edges.append({'from': origin, 'text': name})
            candidates = [a for a in self.archives if name in a.entries]
            if not candidates:
                self.missing.add(name)
            for archive in candidates:
                key = (archive.path.name, name)
                if key in self.visited:
                    continue
                self.visited.add(key)
                data = archive.read_binary(name)
                count = 0
                for line in data.decode('latin1').splitlines():
                    parsed = parse_command(line)
                    if parsed is None:
                        continue
                    _, command, args = parsed
                    count += 1
                    if command == 'create_real_object' and len(args) >= 2:
                        presets.add(args[1])
                    if command == 'attach_script' and len(args) >= 2:
                        scripts.add(args[1])
                    for arg in args:
                        if arg.lower().endswith('.txt'):
                            pending.append((arg.lower(), name))
                self.records.append({'archive': key[0], 'member': name,
                                     'sha256': hashlib.sha256(data).hexdigest(), 'commands': count})
        return presets, scripts

    def receipt(self):
        return {'text_members': self.records, 'missing_text_names': sorted(self.missing),
                'text_edges': [dict(zip(('from', 'text'), e)) for e in sorted({(e['from'], e['text']) for e in self.edges})],
                'limit': 'Literal calls and text references; collision candidates included conservatively, mount order not asserted.'}
