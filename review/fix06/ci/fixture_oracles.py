"""Independent golden counts for immutable, SHA-256 pinned public STEP fixtures.

Counts were established by separate source imports and frozen EXE audits in
GitHub run 41245568510. They are never derived from the EXE under test.
"""
ORACLES={
 'e64c83bcb84d41c0324e104a1c911879174d08aa':('06b372e40217caa1a7d1f516cb74887247f809e41e1e389f740f290e98441b55',1715),
 'e47cc70edbdb0c36916885b54a5e1f30f52a717a':('edd2ea87a509eb39ea59de360e47f0fbbb0fdb0fe412ce478b6932525b5131ee',1707),
 '1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a':('416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf',1595),
 '9d9223311f2b0fce72484023d6a755e13a733319':('f50fd54a5074a15168ee85ee59d6250ddd5db349b74bca8e128e2760b4b08b0c',1595),
}

def expected_count(revision,digest):
    expected,count=ORACLES[revision]
    if digest!=expected:raise AssertionError('Public STEP fixture SHA-256 mismatch: '+revision)
    return count


def verify_counts(summary,old_count,new_count):
    for role,count in (('A',old_count),('B',new_count)):
        if type(summary.get('solids_'+role)) is not int or summary['solids_'+role]!=count:
            raise AssertionError(f'Frozen EXE revision {role}: expected exactly {count} source occurrences')


def sha256_file(path):
    import hashlib
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
    return digest.hexdigest()
