"""Small auditable Decimal interval arithmetic for likelihood upper envelopes.

Algebra uses directed rounding. Decimal.exp/ln are correctly rounded under
ROUND_HALF_EVEN; one outward ULP encloses their exact real values. This relies
on CPython/libmpdec's documented arithmetic contract, not an external proof
assistant. Inputs are exact decimal strings; no floats or Monte Carlo here.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN
from typing import ClassVar

D=Decimal
PRECISION=50
NINF=D("-Infinity")


def rounded(op, mode):
    with localcontext() as c:
        c.prec=PRECISION
        c.rounding=mode
        return +op()


def elementary(x, name, lower):
    if name=="exp" and x==NINF:
        return D(0)
    if name=="ln" and x==0:
        return NINF
    with localcontext() as c:
        c.prec=PRECISION
        c.rounding=ROUND_HALF_EVEN
        result=getattr(x,name)()
        return result.next_minus(c) if lower else result.next_plus(c)


@dataclass(frozen=True)
class Interval:
    lo: Decimal
    hi: Decimal

    def __post_init__(self):
        if self.lo.is_nan() or self.hi.is_nan() or self.lo>self.hi:
            raise ArithmeticError("Invalid interval")

    @classmethod
    def exact(cls,value):
        if isinstance(value,float):
            raise TypeError("Use an exact decimal string, not a binary float")
        z=D(value)
        return cls(z,z)

    @staticmethod
    def coerce(value):
        return value if isinstance(value,Interval) else Interval.exact(value)

    def __add__(self,other):
        other=self.coerce(other)
        return Interval(rounded(lambda:self.lo+other.lo,ROUND_FLOOR),
                        rounded(lambda:self.hi+other.hi,ROUND_CEILING))
    __radd__=__add__

    def __neg__(self):
        return Interval(self.hi.copy_negate(),self.lo.copy_negate())
    def __sub__(self,other):
        return self+-self.coerce(other)
    def __rsub__(self,other):
        return self.coerce(other)+-self
    def __mul__(self,other):
        other=self.coerce(other)
        products=[(x,y) for x in (self.lo,self.hi) for y in (other.lo,other.hi)]
        return Interval(min(rounded(lambda x=x,y=y:x*y,ROUND_FLOOR) for x,y in products),
                        max(rounded(lambda x=x,y=y:x*y,ROUND_CEILING) for x,y in products))
    __rmul__=__mul__

    def reciprocal(self):
        if self.lo<=0<=self.hi:
            raise ZeroDivisionError("Interval contains zero")
        return Interval(rounded(lambda:D(1)/self.hi,ROUND_FLOOR),
                        rounded(lambda:D(1)/self.lo,ROUND_CEILING))
    def __truediv__(self,other):
        return self*self.coerce(other).reciprocal()
    def __rtruediv__(self,other):
        return self.coerce(other)*self.reciprocal()

    def square(self):
        if self.lo<=0<=self.hi:
            return Interval(D(0),max(rounded(lambda:self.lo*self.lo,ROUND_CEILING),
                                     rounded(lambda:self.hi*self.hi,ROUND_CEILING)))
        values=(self.lo,self.hi)
        return Interval(min(rounded(lambda x=x:x*x,ROUND_FLOOR) for x in values),
                        max(rounded(lambda x=x:x*x,ROUND_CEILING) for x in values))

    def exp(self):
        return Interval(max(D(0),elementary(self.lo,"exp",True)),elementary(self.hi,"exp",False))
    def ln(self):
        if self.lo<0:
            raise ArithmeticError("Log of interval extending below zero")
        return Interval(elementary(self.lo,"ln",True),elementary(self.hi,"ln",False))
    def sqrt(self):
        if self.lo<0:
            raise ArithmeticError("Negative square root")
        return Interval(max(D(0),elementary(self.lo,"sqrt",True)),elementary(self.hi,"sqrt",False))
    def contains(self,value):
        return self.lo<=D(value)<=self.hi
    def json(self):
        return {"lo":str(self.lo),"hi":str(self.hi)}


def log_trigger(x,Z):
    """Enclose log(1-exp(-Z*x²/2)) with exact zero/negative infinity."""
    square=x.square()
    def at(v,lower):
        if v==0:
            return NINF
        vI=Interval.exact(v)
        positive=1-(-Interval.exact(Z)*vI/2).exp()
        # Rounding may enclose a tiny negative number when v is almost zero;
        # nonnegativity is an analytic fact. If the upper endpoint is zero,
        # the correct response is unresolved, never a fabricated finite value.
        positive=Interval(max(D(0),positive.lo),max(D(0),positive.hi))
        answer=positive.ln()
        return answer.lo if lower else answer.hi
    return Interval(at(square.lo,True),at(square.hi,False))
