"""Controlled changes: truth is defined when constructing B, not from matching output."""
import sys,json,time
from pathlib import Path
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from dsac29.geometry import describe,transform
from dsac29.compare import compare

def box(name='P',x=0,y=0,length=100,width=20,height=10):
 return describe(transform(BRepPrimAPI_MakeBox(length,width,height).Shape(),np.eye(3),np.array([x,y,0.])),name,name)
def hole(x,r=3):
 block=BRepPrimAPI_MakeBox(100,60,10).Shape()
 tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,20,-1),gp_Dir(0,0,1)),r,12).Shape()
 cut=BRepAlgoAPI_Cut(block,tool);cut.Build()
 return describe(cut.Shape(),'PLYTA','PLYTA')
def rec(a,b,s):return (a,b,s)
def cases():
 yield 'bez zmian',[box()],[box()],[rec(0,0,'SAME')]
 yield 'zmiana nazwy',[box('OLD')],[box('NEW')],[rec(0,0,'RENAMED')]
 yield 'przesunięcie',[box()],[box(x=170)],[rec(0,0,'MOVED')]
 a=box();r=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
 yield 'obrót 90 stopni',[a],[describe(transform(a.shape,r,np.array([200.,0.,0.])),a.name,a.path)],[rec(0,0,'MOVED')]
 yield 'skrócenie profilu',[box()],[box(length=90)],[rec(0,0,'CHANGED')]
 yield 'skrócenie i nazwa',[box('OLD')],[box('NEW',length=90)],[rec(0,0,'CHANGED')]
 yield 'dodany otwór',[box('PLYTA',width=60)],[hole(20)],[rec(0,0,'CHANGED')]
 yield 'zmieniona średnica',[hole(20)],[hole(20,4)],[rec(0,0,'CHANGED')]
 yield 'przesunięty otwór',[hole(20)],[hole(35)],[rec(0,0,'CHANGED')]
 yield 'nowa część',[box()],[box(),box('NEW',x=300,length=32)],[rec(0,0,'SAME'),rec(None,1,'ADDED')]
 yield 'usunięta część',[box(),box('OLD',x=300,length=32)],[box()],[rec(0,0,'SAME'),rec(1,None,'REMOVED')]
 yield 'dodane wystąpienie',[box()],[box(),box(x=300)],[rec(0,0,'SAME'),rec(None,1,'ADDED')]
 yield 'dwa skrócone profile',[box(y=0),box(y=100)],[box(y=0,length=90),box(y=100,length=90)],[rec(0,0,'CHANGED'),rec(1,1,'CHANGED')]
 # Nearest-first picks A0->B0 (9), A1->B1 (21). Global minimum is 11+1.
 yield 'globalne przesunięcia',[box(x=0,length=2,width=3,height=4),box(x=10,length=2,width=3,height=4)],[box(x=9,length=2,width=3,height=4),box(x=-11,length=2,width=3,height=4)],[rec(0,1,'MOVED'),rec(1,0,'MOVED')]
 yield 'zmiany z przestawioną listą',[box(y=0),box(y=100)],[box(y=100,length=90),box(y=0,length=90)],[rec(0,1,'CHANGED'),rec(1,0,'CHANGED')]
 yield 'różne części ta sama objętość',[box(length=100,width=20)],[box('OTHER',x=300,length=50,width=40)],[rec(0,None,'REMOVED'),rec(None,0,'ADDED')]
 yield 'niejednoznaczne nakładanie',[box(),box()],[box(length=90),box(length=90)],None
 yield 'puste B',[box()],[],[rec(0,None,'REMOVED')]
 yield 'puste A',[],[box()],[rec(None,0,'ADDED')]
 yield 'puste oba',[],[],[]
