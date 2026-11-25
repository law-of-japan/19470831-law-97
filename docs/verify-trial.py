"""Re-run the trial's checks and invariants from any working directory.

Usage: python -X utf8 19470831-law-97/docs/verify-trial.py [path-to-loj-validator.exe]
The validator should be a build of the commit recorded in docs/trial-snapshot.json.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
root = repo.parent
snapshot = json.loads((repo / 'docs/trial-snapshot.json').read_text(encoding='utf-8'))
exe = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'loj-validator/target/release/loj-validator.exe'
out = repo / 'docs/validation'
out.mkdir(exist_ok=True)
first = repo / 'versions' / snapshot['revisions']['enactment']
second = repo / 'versions' / snapshot['revisions']['amendment']
related = [repo / 'docs/related' / rid for rid in snapshot['relatedRecords'].values()]
rel = lambda p: str(Path(p).relative_to(root)).replace('\\', '/')

jobs = [(f'{name}-{level}', [rel(path), '--level', level])
        for name, path in [('enactment', first), ('amendment', second)] for level in ['L0', 'L1']]
jobs += [('history-L3', [rel(repo), '--level', 'L3']), ('rebuild', [rel(repo), '--check', 'rebuild']),
         ('registry', ['loj-registry', '--check', 'registry', '--registration-space', 'law-of-japan'])]
jobs += [(p.name + '-L3', [rel(p), '--level', 'L3']) for p in related]
jobs += [('relations-L4', ['--registry', 'loj-registry', '--repository', rel(repo)]
          + sum([['--repository', rel(p)] for p in related], []) + ['--level', 'L4', '--registration-space', 'law-of-japan'])]

summary = []
for name, args in jobs:
    cmd = [str(exe), 'check'] + args + ['--format', 'json']
    result = subprocess.run(cmd, capture_output=True, cwd=root)
    (out / (name + '.json')).write_bytes(result.stdout)
    report = json.loads(result.stdout)
    summary.append({'name': name, 'command': ['loj-validator'] + cmd[1:], 'exitCode': result.returncode,
                    'results': report.get('results', [])})
    print(name, [f"{r['check']}={r['result']}" for r in report.get('results', [])])

# Invariant 1: the amendment changes only items 2 and 3 of article 6.
item = re.compile(rb'<!-- loj:item number=(\d+) -->\n(.*?)<!-- loj:end-item -->\n', re.S)
art6 = lambda b: b.split('## 第六條\n'.encode())[1].split('## 第七條\n'.encode())[0]
before, after = (first / 'main.md').read_bytes(), (second / 'main.md').read_bytes()
items_before, items_after = dict(item.findall(art6(before))), dict(item.findall(art6(after)))
assert sorted(items_before) == sorted(items_after) == [str(i).encode() for i in range(1, 9)]
changed = sorted(k.decode() for k in items_before if items_before[k] != items_after[k])
assert changed == ['2', '3'], changed
expected = {
    '2': '二　産業安全に関する事項（鉱山における保安に関する事項を除く。）\n',
    '3': '三　労働衛生に関する事項（鉱山における通氣及び災害時の救護に関する事項を除く。）\n',
}
assert all(items_after[k.encode()].decode('utf-8') == v for k, v in expected.items())
restored = after
for k, v in expected.items():
    restored = restored.replace(v.encode(), items_before[k.encode()])
assert restored == before, 'Unexpected change outside article 6 items 2 and 3'
# Invariant 2: the supplement and manifest are byte-identical; glyph notes differ only in the revision line.
assert (first / 'supplement.md').read_bytes() == (second / 'supplement.md').read_bytes()
assert (first / 'law.yaml').read_bytes() == (second / 'law.yaml').read_bytes()
g1, g2 = [(v / 'glyphs.yaml').read_text(encoding='utf-8').split('\n', 2)[2] for v in (first, second)]
assert g1 == g2
# Invariant 3: saved source images match their recorded hashes.
for entry in json.loads((repo / 'docs/sources/downloads.json').read_text(encoding='utf-8')):
    assert hashlib.sha256((repo / 'docs/sources' / entry['file']).read_bytes()).hexdigest() == entry['sha256'], entry['file']
# Invariant 4: legacy refs are unchanged.
for line in snapshot['legacyRefs']:
    sha, ref = line.split(' ', 1)
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', ref], text=True).strip() == sha, ref

invariants = {'changedItems': ['19470831-law-97/main/article/6/paragraph/1/item/2', '19470831-law-97/main/article/6/paragraph/1/item/3'],
              'unchangedOtherMainText': True, 'unchangedSupplement': True, 'unchangedManifest': True,
              'glyphNotesSameExceptRevision': True, 'sourceHashesMatch': True, 'legacyRefsUnchanged': True,
              'replacedItems': expected}
(out / 'invariants.json').write_text(json.dumps(invariants, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
(out / 'commands.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
provenance = {'binarySha256': hashlib.sha256(exe.read_bytes()).hexdigest(), 'validatorCommit': snapshot['loj-validator'],
              'specCommit': snapshot['loj-spec'],
              'note': 'Directory checks, not canonical-commit certification. The binary hash identifies the executable only.'}
(out / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Trial invariants passed.')
