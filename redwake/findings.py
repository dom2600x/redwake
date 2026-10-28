"""Validate submitted read-authorization findings against declared policy and evidence."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Invalid finding or contract fields')


def label(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', value))


def path_valid(value):
    return (isinstance(value, str) and value.startswith('/') and not value.startswith('//')
            and not any(c in value for c in '?%#\\\r\n\t')
            and all(part not in ('.', '..', '') for part in value[1:].split('/')))


def validate_contract(contract):
    fields(contract, ('version', 'actors', 'rules'))
    if type(contract['version']) is not int or contract['version'] != 1:
        raise ValueError('Unsupported access contract version')
    actors = contract['actors']
    if (not isinstance(actors, list) or len(actors) < 2 or not all(label(a) for a in actors)
            or len(set(actors)) != len(actors)):
        raise ValueError('Contract needs distinct actor aliases')
    if not isinstance(contract['rules'], list) or not contract['rules']:
        raise ValueError('Contract needs read-access rules')
    ids, paths = set(), set()
    for rule in contract['rules']:
        fields(rule, ('id', 'path', 'owner', 'allowed_actors', 'identity'))
        if not label(rule['id']) or rule['id'] in ids or not path_valid(rule['path']) or rule['path'] in paths:
            raise ValueError('Invalid or duplicate rule ID/path')
        ids.add(rule['id']); paths.add(rule['path'])
        allowed = rule['allowed_actors']
        if (not isinstance(allowed, list) or not all(a in actors for a in allowed)
                or len(set(allowed)) != len(allowed) or rule['owner'] not in actors
                or rule['owner'] not in allowed):
            raise ValueError('Invalid owner or permitted actors')
        identity = rule['identity']
        if not isinstance(identity, dict) or not identity:
            raise ValueError('Record identity assertions are required')
        for pointer, value in identity.items():
            if (not isinstance(pointer, str) or not pointer.startswith('/')
                    or re.search(r'~(?![01])', pointer)
                    or type(value) not in (str, int, bool) or value == ''):
                raise ValueError('Identity requires JSON pointers and nonempty scalar values')


def matches(body, identity):
    for pointer, expected in identity.items():
        current = body
        for part in pointer[1:].split('/'):
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        if type(current) is not type(expected) or current != expected:
            return False
    return True


def evaluate(contract, finding, evidence):
    """Evaluate only the submitted rule; never invent findings for other resources."""
    validate_contract(contract)
    fields(finding, ('rule_id', 'actor', 'evidence_ids', 'reproduction', 'impact'))
    if not label(finding['rule_id']) or not label(finding['actor']):
        raise ValueError('Invalid finding rule or actor')
    ids = finding['evidence_ids']
    if not isinstance(ids, list) or len(ids) != 2 or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != 2:
        raise ValueError('Finding needs two distinct positive evidence IDs')
    steps = finding['reproduction']
    if not isinstance(steps, list) or len(steps) != 2:
        raise ValueError('Finding needs owner and cross-account reproduction steps')
    for step in steps:
        fields(step, ('method', 'actor', 'path', 'evidence_id'))
        if step['method'] != 'GET' or not label(step['actor']) or not path_valid(step['path']) or type(step['evidence_id']) is not int:
            raise ValueError('Invalid read reproduction step')
    result = dict(accepted=False, reason=None, rule_id=finding['rule_id'], evidence_ids=ids)
    def reject(reason):
        return dict(result, reason=reason)
    if finding['impact'] != 'unauthorized_record_read':
        return reject('unsupported_impact')
    rule = next((r for r in contract['rules'] if r['id'] == finding['rule_id']), None)
    if rule is None:
        return reject('unknown_rule')
    if finding['actor'] not in contract['actors']:
        return reject('unknown_actor')
    if finding['actor'] in rule['allowed_actors']:
        return reject('access_permitted')
    by_id, latest = {}, {}
    for item in evidence:
        if type(item.get('id')) is not int or item['id'] in by_id:
            raise ValueError('Invalid evidence inventory')
        by_id[item['id']] = item
        latest[(item['actor'], item['path'])] = item['id']
    if any(i not in by_id for i in ids):
        return reject('unknown_evidence')
    actors = (rule['owner'], finding['actor'])
    expected_steps = [dict(method='GET', actor=a, path=rule['path'], evidence_id=i) for a, i in zip(actors, ids)]
    if steps != expected_steps:
        return reject('reproduction_mismatch')
    for actor, evidence_id in zip(actors, ids):
        item = by_id[evidence_id]
        if item['actor'] != actor or item['path'] != rule['path']:
            return reject('evidence_mismatch')
        if latest[(actor, rule['path'])] != evidence_id:
            return reject('superseded_evidence')
        if item['status'] != 200 or not matches(item['body'], rule['identity']):
            return reject('missing_successful_control' if actor == rule['owner'] else 'unproved_cross_account_read')
    return dict(result, accepted=True, reason='proved', impact='unauthorized_record_read',
                actor=finding['actor'], path=rule['path'], reproduction=expected_steps)


def read_json(path):
    return json.loads(Path(path).read_text())


def source_evidence(source):
    from .artifacts import verify_bundle
    verify_bundle(source)
    manifest = read_json(source / 'manifest.json')
    if manifest.get('kind') != 'investigation' or manifest['run_count'] != 1:
        raise ValueError('Use a single-investigation export as the evidence source')
    return read_json(source / 'runs' / manifest['run_ids'][0] / 'evidence.json')


def inventory(directory):
    result = []
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in finding proof')
        if path.is_file() and path != directory / 'manifest.json':
            raw = path.read_bytes()
            result.append(dict(path=path.relative_to(directory).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    return result


def verify_proof(directory):
    directory = Path(directory)
    manifest = read_json(directory / 'manifest.json')
    fields(manifest, ('schema_version', 'kind', 'files'))
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or manifest['kind'] != 'finding_proof':
        raise ValueError('Invalid finding proof manifest')
    if manifest['files'] != inventory(directory):
        raise ValueError('Finding proof inventory or hash mismatch')
    expected = {'contract.json', 'finding.json', 'validation.json'}
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p != directory/'manifest.json'}
    if {p for p in actual if not p.startswith('source/')} != expected:
        raise ValueError('Unexpected finding proof files')
    result = evaluate(read_json(directory/'contract.json'), read_json(directory/'finding.json'), source_evidence(directory/'source'))
    if result != read_json(directory/'validation.json'):
        raise ValueError('Finding validation differs from evidence')
    return dict(bundle=directory.name, runs=1, files=len(actual), finding=result)


def export_proof(source, contract, finding, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a fresh proof destination')
    if any(p.is_symlink() for p in source.rglob('*')) or source.is_symlink():
        raise ValueError('Symlink in source bundle')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.redwake-finding-', dir=destination.parent))
    try:
        shutil.copytree(source, stage/'source')
        result = evaluate(contract, finding, source_evidence(stage/'source'))
        for name, value in (('contract', contract), ('finding', finding), ('validation', result)):
            (stage/(name+'.json')).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
        (stage/'manifest.json').write_text(json.dumps(dict(schema_version=1, kind='finding_proof', files=inventory(stage)), indent=2)+'\n')
        verify_proof(stage)
        destination.mkdir()
        try:
            for path in stage.iterdir(): path.rename(destination/path.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(stage)
    return result
