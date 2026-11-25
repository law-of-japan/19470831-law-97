"""Re-run the migration checks (labor-ministry-migration-plan.md, step 6) and save JSON reports.

Usage: python -I -X utf8 19470831-law-97/docs/verify-migration.py [path-to-loj-validator.exe]
Run with the law repository and loj-registry checked out side by side (as in the working directory).
Checks the committed trees (git archive / bundle), not the working tree.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[1]
root = repo.parent
registry = root / 'loj-registry'
validator = root / 'loj-validator'
exe = Path(sys.argv[1]) if len(sys.argv) > 1 else validator / 'target/release/loj-validator.exe'
out = repo / 'docs/migration-validation'
out.mkdir(exist_ok=True)

LAW_HEAD = 'main'
REGISTRY_BASE = '125961a38d3724be385fb567ba7eb438c412cce9'
REGISTRY_HEAD = 'records/labor-ministry-1947'
TRIAL = 'trial/labor-ministry-20261119'
REGISTRY_TRIAL = 'trial/labor-ministry-20261119'
REVISIONS = {'enactment': 'wykk6n1d', 'amendment': 'grst9hg0'}
LEGACY_REFS = {
    'refs/heads/master': '7d5d006ea805b2ebb7a6f9a0d24c7904b578befc',
    'refs/remotes/origin/master': '7d5d006ea805b2ebb7a6f9a0d24c7904b578befc',
    'refs/remotes/origin/19470831_97': '125a1adb090b5548418cb243e71c56d951c3f51c',
    f'refs/heads/{TRIAL}': '4e294c30f25f8da7dcb4a1fb899f346ffeb34571',
}
DATA = ['history.yaml', 'rebuild.yaml', 'versions', '.gitattributes', 'docs/sources']


def git(path, *args, text=True):
    return subprocess.check_output(['git', '-C', str(path), *args], text=text).strip() if text else \
        subprocess.check_output(['git', '-C', str(path), *args])


law_head = git(repo, 'rev-parse', LAW_HEAD)
registry_head = git(registry, 'rev-parse', REGISTRY_HEAD)
scratch = Path(tempfile.mkdtemp(prefix='loj-migration-'))
try:
    law_dir, reg_dir = scratch / 'law', scratch / 'registry'
    for src, ref, dst in [(repo, law_head, law_dir), (registry, registry_head, reg_dir)]:
        dst.mkdir()
        archive = git(src, 'archive', '--format=tar', ref, text=False)
        subprocess.run(['tar', '-x', '-C', str(dst)], input=archive, check=True)
    law_bundle, reg_bundle = scratch / 'law.bundle', scratch / 'registry.bundle'
    git(repo, 'bundle', 'create', str(law_bundle), LAW_HEAD)
    git(registry, 'bundle', 'create', str(reg_bundle), REGISTRY_HEAD)

    jobs = []
    for name, rid in REVISIONS.items():
        for level in ['L0', 'L1']:
            jobs.append((f'{name}-{level}', [str(law_dir / 'versions' / rid), '--level', level]))
    jobs += [
        ('history-L3', [str(law_dir), '--level', 'L3']),
        ('rebuild', [str(law_dir), '--check', 'rebuild']),
        ('registry', [str(reg_dir), '--check', 'registry', '--registration-space', 'law-of-japan']),
        ('relations-L4', ['--registry', str(reg_dir), '--repository', str(law_dir), '--level', 'L4',
                          '--registration-space', 'law-of-japan']),
        ('law-change', [str(law_bundle), '--head', law_head]),
        ('registry-change', [str(reg_bundle), '--repository-kind', 'registry', '--base', REGISTRY_BASE,
                             '--head', registry_head]),
    ]
    summary = []
    for name, args in jobs:
        cmd = [str(exe), 'check', *args, '--format', 'json']
        result = subprocess.run(cmd, capture_output=True)
        text = result.stdout.decode('utf-8')
        for form in (json.dumps(str(scratch))[1:-1], str(scratch), str(scratch).replace('\\', '/')):
            text = text.replace(form, '<scratch>')
        (out / f'{name}.json').write_text(text, encoding='utf-8', newline='\n')
        report = json.loads(text)
        results = [{'check': r.get('check'), 'category': r.get('category'), 'result': r.get('result'),
                    'diagnostics': len(r.get('diagnostics', []))} for r in report.get('results', [])]
        shown = ['loj-validator', 'check'] + [a.replace(str(scratch), '<scratch>') for a in args]
        summary.append({'name': name, 'command': shown, 'exitCode': result.returncode, 'results': results})
        print(name, result.returncode, [(r['category'] or r['check'], r['result'], r['diagnostics']) for r in results])
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# Invariant 1: canonical data, attributes and source files are the same Git objects as the trial tip.
same = {p: git(repo, 'rev-parse', f'{law_head}:{p}') == git(repo, 'rev-parse', f'{TRIAL}:{p}') for p in DATA}
assert all(same.values()), same
# Invariant 2: main differs from the trial tip only by README, the workflow, migration records and docs/related.
changed = git(repo, 'diff', '--name-only', TRIAL, law_head).splitlines()
allowed = re.compile(r'^(README\.md|\.github/workflows/validate\.yml|docs/related/.*|docs/verify-migration\.py|docs/migration-.*)$')
assert all(allowed.match(p) for p in changed), changed
# Invariant 3: every committed canonical data file is a regular non-executable file.
modes = {line.split()[0] for line in git(repo, 'ls-tree', '-r', law_head).splitlines()}
assert modes == {'100644'}, modes
# Invariant 4: the amendment changes only article 6 items 2 and 3.
item = re.compile(rb'<!-- loj:item number=(\d+) -->\n(.*?)<!-- loj:end-item -->\n', re.S)
blob = lambda rid, f: git(repo, 'show', f'{law_head}:versions/{rid}/{f}', text=False)
art6 = lambda b: b.split('## 第六條\n'.encode())[1].split('## 第七條\n'.encode())[0]
first, second = (blob(REVISIONS[k], 'main.md') for k in ('enactment', 'amendment'))
before, after = dict(item.findall(art6(first))), dict(item.findall(art6(second)))
assert sorted(k for k in before if before[k] != after[k]) == [b'2', b'3']
restored = second
for k in (b'2', b'3'):
    restored = restored.replace(after[k], before[k])
assert restored == first
for f in ('supplement.md', 'law.yaml'):
    assert blob(REVISIONS['enactment'], f) == blob(REVISIONS['amendment'], f), f
# Invariant 5: saved source images match their recorded hashes, and the registry cites the same hashes.
downloads = json.loads(git(repo, 'show', f'{law_head}:docs/sources/downloads.json'))
for entry in downloads:
    data = git(repo, 'show', f"{law_head}:docs/sources/{entry['file']}", text=False)
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['file']
hashes = {e['file']: e['sha256'] for e in downloads}
first_commit = git(repo, 'rev-list', '--max-parents=0', law_head)
cited = []
for rid in ['19470831-law-97', '19490516-law-70', 'ex0typ1a26']:
    record = git(registry, 'show', f'{registry_head}:records/{rid}.yaml')
    assert 'file:' not in record and 'trial/' not in record, rid
    pattern = r'fixed: https://github\.com/law-of-japan/19470831-law-97/blob/([0-9a-f]{40})/docs/sources/(\S+) SHA-256 ([0-9a-f]{64})'
    for commit, file, sha in re.findall(pattern, record):
        assert commit == first_commit and hashes[file] == sha, (rid, commit, file)
        cited.append({'record': rid, 'file': file})
assert len(cited) == 3, cited
# Invariant 6: the registry branch differs from the trial records only in location, canonicalBranch,
# removed repository blocks and fixed values.
diff = git(registry, 'diff', '-U0', REGISTRY_TRIAL, registry_head, '--', 'records/').splitlines()
body = [l for l in diff if l[:1] in '+-' and not l.startswith(('+++', '---'))]
assert all(re.match(r'^[-+](repository:|  location: |  canonicalBranch: |  fixed: )', l) for l in body), body
# Invariant 7: legacy and trial refs are unchanged.
refs = {ref: git(repo, 'rev-parse', ref) for ref in LEGACY_REFS}
assert refs == LEGACY_REFS, refs

invariants = {
    'lawHead': law_head, 'registryHead': registry_head, 'trialTip': LEGACY_REFS[f'refs/heads/{TRIAL}'],
    'dataSameAsTrial': same, 'filesChangedFromTrial': changed, 'fileModes': sorted(modes),
    'changedItems': ['19470831-law-97/main/article/6/paragraph/1/item/2', '19470831-law-97/main/article/6/paragraph/1/item/3'],
    'sourceHashesMatch': True, 'registryFixedCitations': cited, 'registryDiffFromTrialLimited': True,
    'legacyRefsUnchanged': refs,
}
(out / 'invariants.json').write_text(json.dumps(invariants, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
(out / 'commands.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
provenance = {'lawCommit': law_head, 'registryCommit': registry_head,
              'validatorCommit': git(validator, 'rev-parse', 'HEAD'),
              'specCommit': (validator / 'vendor/loj-spec/COMMIT').read_text().strip(),
              'binarySha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
              'note': 'Checks of committed trees before publication. Format checks do not prove agreement with the sources.'}
(out / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
failed = [s['name'] for s in summary if s['exitCode'] != 0]
print('invariants: ok', '| failed checks:', failed or 'none')
sys.exit(1 if failed else 0)
