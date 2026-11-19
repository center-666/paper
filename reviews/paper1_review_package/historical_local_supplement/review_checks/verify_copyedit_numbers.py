"""Verify printed scalar intervals and table-derived details without simulation."""
from pathlib import Path
from fractions import Fraction as F
import json,math
P=Path(__file__).resolve().parent.parent

class I:
    def __init__(self,a,b=None):self.lo=F(a);self.hi=F(a if b is None else b)
    def __add__(self,other):
        o=other if isinstance(other,I) else I(other)
        return I(self.lo+o.lo,self.hi+o.hi)
    __radd__=__add__
    def __neg__(self):return I(-self.hi,-self.lo)
    def __sub__(self,o):return self+-as_i(o)
    def __rsub__(self,o):return as_i(o)+-self
    def __mul__(self,other):
        o=as_i(other);v=[a*b for a in (self.lo,self.hi) for b in (o.lo,o.hi)]
        return I(min(v),max(v))
    __rmul__=__mul__
    def __truediv__(self,other):
        o=as_i(other);assert o.lo*o.hi>0
        return self*I(1/o.hi,1/o.lo)
    def pack(self):return dict(lower=str(self.lo),upper=str(self.hi),midpoint_float=float((self.lo+self.hi)/2))
def as_i(x):return x if isinstance(x,I) else I(x)

den=10**20
qs=['3','143/25','1701/295','4617/715','461/75','5567/965']
ns=[57735026918962576450,41812100500354538535,41644614975962723125,
    39352568506259571953,40334824255503366866,41634470525994220264]
roots=[]
for q,N in zip(map(F,qs),ns):
    assert N*N*q.numerator<den*den*q.denominator<(N+1)**2*q.numerator
    roots.append(I(F(N,den),F(N+1,den)))
s0,s1,ss,sn,salt,snextalt=roots
w0=1-s0;pn=F(378,715);ps=F(54,295);c1=F(16,143);dn2=F(28,143)**2
c2=dn2/(1+2*(F(2)+pn+F(1,5)))
jE=w0*s1*(-c1*(pn-ps)+dn2)
dE=w0*s1*(c1*(ss-sn)-sn*c2)
jL=I(0);dL=I(0)
for p,mass,scur,snext in [(F(54,25),w0,s1,ss),(F(178,75),s0,salt,snextalt)]:
    K=p/(p+F(1,5));post=p*F(1,5)/(p+F(1,5));Dp=1+2*(F(2)+post+F(1,5))
    jL+=mass*(1-scur)*K*K
    dL-=mass*(1-scur)*snext*K*K/Dp
lam=dE/(dE-dL);cstar=(dE*jL-dL*jE)/(dE-dL)
intervals={'d_E':dE,'d_L':dL,'lambda_0':lam,'c_star':cstar}
printed={'d_E':('0.00004029915481592','0.00004029915481593'),
         'd_L':('-0.036025793676275','-0.036025793676274'),
         'lambda_0':('0.00111736957492','0.00111736957494'),
         'c_star':('0.00049907284044','0.00049907284046')}
for key,interval in intervals.items():
    lo,hi=map(F,printed[key]);assert lo<interval.lo<=interval.hi<hi,key
data=json.loads((P/'vector_data/results.json').read_text(encoding='utf-8'))
physical=json.loads((P/'vector_data/physical_check.json').read_text(encoding='utf-8'))
stats={}
for name,case in data['cases'].items():
    s=case['sampling'];c=case['constants'];n=s['n'];alpha=s['alpha'];pop=case['budget_base_row']['population_certificate']
    known=pop+c['C_record']*math.sqrt(math.log(1/alpha)/(2*n))
    two=pop+c['C_record']*math.sqrt(math.log(1/alpha)/n)
    assert abs(known-s['centered_known_bound'])<1e-12
    assert abs(two-s['centered_two_bound'])<1e-12
    stats[name]=dict(known=known,two=two,centered_planning_known=s['centered_known_planning_n'],
                     centered_planning_two_each=s['centered_two_planning_each_n'])
zmax=max(abs(r['z_difference']) for r in physical['rows'])
assert f'{zmax:.3f}'=='1.125'
result=dict(passed=True,scalar_intervals={k:v.pack() for k,v in intervals.items()},
            all_six_integer_square_tests_passed=True,all_four_printed_intervals_enclose_exact_intervals=True,
            statistical_table_checks=stats,maximum_absolute_standardized_difference=zmax,
            new_simulations=False,scope='Exact rational audit of Appendix D coefficients; other numerical checks use stored floating-point values.')
out=Path(__file__).with_suffix('.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,scalar_midpoints={k:v.pack()['midpoint_float'] for k,v in intervals.items()},
                     max_standardized_difference=zmax,statistical_tables=stats),indent=2))
