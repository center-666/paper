"""Small exact rational matrix helpers for reproducible two-state certificates."""
from fractions import Fraction as F


def matrix(rows):return [[F(x) for x in row] for row in rows]
def transpose(a):return [list(row) for row in zip(*a)]
def identity(n):return [[F(i==j) for j in range(n)] for i in range(n)]
def add(a,b):return [[x+y for x,y in zip(ra,rb)] for ra,rb in zip(a,b)]
def sub(a,b):return [[x-y for x,y in zip(ra,rb)] for ra,rb in zip(a,b)]
def scale(a,s):return [[x*s for x in row] for row in a]
def matmul(a,b):
    bt=transpose(b)
    return [[sum((x*y for x,y in zip(row,col)),F(0)) for col in bt] for row in a]


def inverse(a):
    n=len(a)
    rows=[list(row)+eye for row,eye in zip(a,identity(n))]
    for i in range(n):
        pivot=next((j for j in range(i,n) if rows[j][i]),None)
        if pivot is None:raise ValueError("Singular")
        rows[i],rows[pivot]=rows[pivot],rows[i]
        divisor=rows[i][i]
        rows[i]=[x/divisor for x in rows[i]]
        for j in range(n):
            if j==i:continue
            factor=rows[j][i]
            rows[j]=[x-factor*y for x,y in zip(rows[j],rows[i])]
    return [row[n:] for row in rows]


def det2(a):return a[0][0]*a[1][1]-a[0][1]*a[1][0]
def psd2(a):
    return a==transpose(a) and a[0][0]>=0 and a[1][1]>=0 and det2(a)>=0
def spd2(a):
    return a==transpose(a) and a[0][0]>0 and det2(a)>0
def encode(a):return [[str(x) for x in row] for row in a]
def asfloat(a):return [[float(x) for x in row] for row in a]


def update(P,C,R):
    pc=matmul(P,transpose(C))
    variance=matmul(C,pc)[0][0]+R
    K=scale(pc,1/variance)
    T=sub(identity(len(P)),matmul(K,C))
    posterior=matmul(T,P)
    assert posterior==transpose(posterior)
    return posterior,K,T
