"""Synthetic guards for original-frame STEP noise and genuine CAD edits.

Public Voron/Trident end-to-end tests use real community STEP in the CI matrix.
"""
from openassembly.model import Part, compare

def piece(i, src, noise=False, big_bbox=False, move=False, revision=False, exact=False):
    x,y,z = i*15., (i%23)*14., (i%19)*12.
    v,ar=1000.+i,2000.+i
    fp=(round(v,5),round(ar,5),(i%31,),((0,100.),),((0,30.),))
    if src=='B':
        if noise:
            v*=1.00047
            ar*=1.000224
            if not exact:
                fp=(round(v,5),round(ar,5),(i%31,),((0,100.002),),((0,30.),))
            x+=.001
        if move:x+=20.
        if revision:
            v*=1.075
            ar*=1.048
            fp=(round(v,5),round(ar,5),(i%31,),((0,105.),),((0,30.),))
    return Part(f'{src}{i}',f'Unique_{i}',f'/{src}/{i}',v,ar,(x,y,z),fp,
                pose=(1.,0.,0.,0.,1.,0.,0.,0.,1.),
                extents=(40.+(1.8 if src=='B' and big_bbox else 0.),30.,20.))

def overlap(old,new):
    if old.name=='Unique_599':
        return {'ok':True,'overlap':.9,'common_mm3':old.volume*.9,
                'added_mm3':old.volume*.1,'removed_mm3':old.volume*.1}
    return {'ok':True,'overlap':1.,'common_mm3':old.volume,
            'added_mm3':0.,'removed_mm3':0.}

def test_roundtrip_noise_and_real_edits():
    a=[piece(i,'A') for i in range(600)]
    b=[piece(i,'B',noise=560<=i<590,
             big_bbox=i in (560,561,562,563,595),
             move=i==598,revision=i==599,exact=i==595)
       for i in range(600) if i!=597]
    b.append(Part('B-new','new marker','/B/new',123,456,(1e6,0,0),('new',),
                  extents=(5.,5.,5.)))
    c=compare(a,b,revision_overlap=overlap)
    assert not c.alignment['applied'],c.alignment
    assert c.counts=={'unchanged':597,'moved':1,'removed':1,'new':1,
                      'revised_old':1,'revised_new':1},c.counts
    assert sum(p.match_quality=='approximate_roundtrip' for p in a)>=4
    assert a[595].match_quality=='boolean_verified_roundtrip'
    assert a[598].status=='moved'
    assert a[599].status=='revised_old'

def test_small_assembly_does_not_assume_roundtrip():
    a=[piece(i,'A') for i in range(25)]
    b=[piece(i,'B',noise=i==24,big_bbox=i==24) for i in range(25)]
    c=compare(a,b)
    assert c.counts=={'unchanged':24,'new':1,'removed':1},c.counts

def test_large_revision_does_not_assume_roundtrip():
    a=[piece(i,'A') for i in range(600)]
    b=[piece(i,'B',noise=450<=i<600,big_bbox=450<=i<600) for i in range(600)]
    c=compare(a,b)
    assert c.counts.get('unchanged',0)<500,c.counts
