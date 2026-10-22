"""Import the exact user-supplied DS Compare R6 Python/runtime changes.

This script applies an LZMA-compressed, SHA-256-verified patch against the
R3 precompile source snapshot. Any baseline mismatch FAILS the build, never
silently compiles older or partially patched sources.

The authoritative R6 source archive SHA-256:
94a349f7f1b12322614f1625d7f2781fab8b6685507ce8103e5176efc83d0a51
"""
from pathlib import Path
import base64,hashlib,json,lzma,os

repo=Path(os.environ['GITHUB_WORKSPACE'])
root=Path(os.environ['DS_COMPARE_SOURCE'])
input_file=repo/'patches/dscompare_r6_delta.b64'
blob=base64.b64decode(input_file.read_text('ascii').strip(),validate=True)
package=json.loads(lzma.decompress(blob).decode('utf8'))
assert package['format']=='dscompare_r6_v2'
assert package['source_sha256']=='94a349f7f1b12322614f1625d7f2781fab8b6685507ce8103e5176efc83d0a51'
files=package['files']
assert len(files)==24,len(files)
for relative,spec in files.items():
    target=root/relative
    expected=spec.get('before_sha256')
    if 'added' in spec:
        if target.exists() and target.read_text('utf8')!=spec['added']:
            raise RuntimeError('R6 new file conflict: '+relative)
        payload=spec['added'].encode('utf8')
    else:
        if not target.is_file() and relative=='BUDUJ_WINDOWS.ps1':
            # The R3 CI pipeline generated this helper only inside its ZIP,
            # not in the in-memory precompile directory.
            payload=(repo/'scripts/R6_BUDUJ_WINDOWS.ps1').read_bytes()
            if hashlib.sha256(payload).hexdigest()!=spec['after_sha256']:
                raise RuntimeError('R6 build helper differs from uploaded source ZIP')
            target.write_bytes(payload)
            print('R6 RECOVERED BUILD HELPER',relative,flush=True)
            continue
        if not target.is_file():
            raise RuntimeError('R3 expected source absent: '+relative)
        original=target.read_bytes()
        got=hashlib.sha256(original).hexdigest()
        if got!=expected:
            raise RuntimeError(f'Unexpected R3 base for {relative}: {got} != {expected}')
        source_lines=original.decode('utf8').splitlines()
        for start,end,replacement in reversed(spec['operations']):
            source_lines[start:end]=replacement
        line_end=spec['eol']
        body=line_end.join(source_lines)
        if spec['trailing_newline']:body+=line_end
        payload=body.encode('utf8')
    got=hashlib.sha256(payload).hexdigest()
    if got!=spec['after_sha256']:
        raise RuntimeError(f'Invalid R6 reconstruction for {relative}: {got} != {spec["after_sha256"]}')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(payload)
    print('R6 VERIFIED',relative,len(payload),flush=True)
assert (root/'VERSION.txt').read_text('utf8').startswith('DS Compare 1.0 R6')
print('DS Compare R6 successfully reconstructed: 24 source/test files match the user archive byte-for-byte.')
