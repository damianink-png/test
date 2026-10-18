import pytest
from accuracy_cases import cases,box,rec
from dsac29.compare import compare

@pytest.mark.parametrize('name,a,b,expected',list(cases()),ids=lambda x:x if isinstance(x,str) else None)
def test_controlled_change(name,a,b,expected):
 result=compare(a,b)
 assert sorted(r.a_index for r in result if r.a_index is not None)==list(range(len(a)))
 assert sorted(r.b_index for r in result if r.b_index is not None)==list(range(len(b)))
 if expected is None:assert all(r.status=='UNCERTAIN' for r in result)
 else:assert {(r.a_index,r.b_index,r.status) for r in result}==set(expected)

@pytest.mark.parametrize('spacing,length,offset,reverse',[(80,92,0,False),(120,87,1000,True),(200,96,-700,True),(350,89,20,False),(95,94,-200,False),(160,91,3500,True),(70,86,200,True),(230,95,-1200,False)])
def test_changed_pair_holdout(spacing,length,offset,reverse):
 a=[box(y=offset),box(y=offset+spacing)]
 b=[box(y=offset,length=length),box(y=offset+spacing,length=length-2)]
 if reverse:b.reverse()
 result=compare(a,b)
 assert {(r.a_index,r.b_index,r.status) for r in result}=={(0,int(reverse),'CHANGED'),(1,int(not reverse),'CHANGED')}
