from robust_translation import Anchor, propose_translation

def anchor(i, sig, xyz):
    return Anchor(i,sig,xyz)

def test_revision_shift_outliers():
    shift=(150.0,-32.0,7.0)
    a=[anchor(i, 'part-'+str(i), (i*13.0,i*i*2.0,i*3.0)) for i in range(8)]
    b=[anchor(i, 'part-'+str(i), tuple(v-shift[k] for k,v in enumerate(a[i].center))) for i in range(6)]
    b += [anchor(80,'new', (500,500,500))]
    p=propose_translation(a,b)
    assert p is not None
    assert p.shift==shift
    assert p.support==6

def test_not_enough_support():
    assert propose_translation([anchor(1,'a',(0,0,0))],[anchor(2,'a',(1,0,0))]) is None

def test_ambiguous_repeated_parts_fail_closed():
    a=[anchor(i,'bolt',(i*10.,0,0)) for i in range(3)]
    b=[anchor(i,'bolt',(i*10.,0,0)) for i in range(3)]
    assert propose_translation(a,b) is None

def test_zero_shift():
    a=[anchor(i,str(i),(i*10.,i*3.,i*2.)) for i in range(4)]
    p=propose_translation(a,a)
    assert p is not None and p.shift==(0,0,0)

def test_different_signatures():
    a=[anchor(i,'a'+str(i),(i,0,0)) for i in range(5)]
    b=[anchor(i,'b'+str(i),(i,0,0)) for i in range(5)]
    assert propose_translation(a,b) is None


