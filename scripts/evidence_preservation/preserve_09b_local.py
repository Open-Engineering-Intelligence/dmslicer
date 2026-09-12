"""Copy the explicit 09B allowlist to a second local custody root; hashes are bytes only."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def preserve(repo, plan_path, mirror):
    repo, plan_path, mirror = repo.resolve(), plan_path.resolve(), mirror.resolve()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if plan.get('goal_id') != 'WORKBENCH-MATERIAL-SEMANTIC-UI-01' or plan.get('hash_semantics') != 'BYTE_INTEGRITY_ONLY':
        raise ValueError('09B byte-integrity custody plan required')
    if not plan.get('implementation_commit') or not plan.get('run_id'):
        raise ValueError('Commit and run identity required')
    if mirror == repo or mirror.is_relative_to(repo):
        raise ValueError('Second custody root must be outside this worktree')
    payloads, local_paths, seen = [], [], set()
    for item in plan['files']:
        relative = item['path']
        path = (repo / relative).resolve()
        if path == repo or not path.is_relative_to(repo) or Path(relative).is_absolute() or relative in seen:
            raise ValueError('Invalid/duplicate allowlisted path: ' + relative)
        seen.add(relative)
        data = path.read_bytes()
        if digest(data) != item['sha256']:
            raise ValueError('Source byte mismatch: ' + relative)
        destination = (mirror / relative).resolve()
        if not destination.is_relative_to(mirror):
            raise ValueError('Destination escapes custody root')
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError('Immutable custody conflict: ' + relative)
        if path.suffix in ('.json', '.txt', '.md', '.xml', '.patch'):
            text = data.decode('utf-8', errors='replace')
            if re.search(r'(?:[A-Z]:[\\/]|/tmp/)', text):
                local_paths.append(relative)
            if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}', text):
                raise ValueError('Potential secret requires review: ' + relative)
        payloads.append((path, destination, data, relative))
    if not set(plan['failure_artifacts']).issubset(seen) or not plan['failure_artifacts']:
        raise ValueError('Failure preservation allowlist is missing')
    for path, destination, data, relative in payloads:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with destination.open('xb') as stream:
                stream.write(data)
        if path.read_bytes() != data or destination.read_bytes() != data:
            raise ValueError('Two-copy byte verification failed: ' + relative)
    by_digest = {}
    for _, _, data, relative in payloads:
        by_digest.setdefault(digest(data), []).append(relative)
    plan_copy = mirror / plan_path.relative_to(repo)
    plan_copy.parent.mkdir(parents=True, exist_ok=True)
    plan_bytes = plan_path.read_bytes()
    if plan_copy.exists() and plan_copy.read_bytes() != plan_bytes:
        raise ValueError('Immutable plan conflict')
    if not plan_copy.exists():
        with plan_copy.open('xb') as stream:
            stream.write(plan_bytes)
    result = {'goal_id': plan['goal_id'], 'run_id': plan['run_id'], 'implementation_commit': plan['implementation_commit'],
              'status': 'PASS', 'recoverable_local_copies': 2, 'verified_file_count': len(payloads),
              'hash_semantics': 'BYTE_INTEGRITY_ONLY', 'geometry_equivalence': 'NOT_ASSESSED',
              'failure_artifacts_preserved': plan['failure_artifacts'], 'mirror': str(mirror),
              'path_scan': {'local_paths_in_diagnostics': local_paths, 'potential_private_keys': 'NONE_DETECTED',
                            'disposition': 'Local custody only; no external publication'},
              'duplication_scan': {'identical_payload_groups': [paths for paths in by_digest.values() if len(paths) > 1],
                                   'disposition': 'Explicit allowlist only; repeated historical failure and verification artifacts retained'},
              'independent_disaster_recovery': 'NOT_ESTABLISHED'}
    data = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    for target in [plan_path.with_name('custody-verification.json'), plan_copy.with_name('custody-verification.json')]:
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Immutable verification conflict')
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(data)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--mirror', type=Path, required=True)
    args = parser.parse_args()
    result = preserve(args.repo, args.plan, args.mirror)
    print(json.dumps({key: result[key] for key in ('status', 'verified_file_count', 'recoverable_local_copies', 'hash_semantics')}))
