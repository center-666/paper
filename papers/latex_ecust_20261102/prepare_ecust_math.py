"""Generate typography-only inputs; keep the audited equations as the source.

Vectors and matrices are bold italic. Ambiguous names (event logs H, scalar
weights w, record variables R and the scalar counterexample) remain explicit.
"""
from pathlib import Path
import re,json,hashlib
P=Path(__file__).resolve().parent
OUT=P/'ecust_typeset';OUT.mkdir(exist_ok=True)
NAMES=['theory','main_joint_kernel','numerical','record_condition_numerical','protocol-figure','damage_table_float','graphical_abstract']
REGION=re.compile(r'\$[^$]*?\$|\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}.*?\\end\{\1\}|\\\[.*?\\\]',re.S)
# Protect text, indices, record names, calligraphic sets and LaTeX identifiers.
PROTECT=re.compile(r'\\(?:label|ref|eqref|text|operatorname|mathrm|textrm|mathcal|mathbb|begin|end)\{[^{}]*\}|\\rm\s*[A-Za-z]+|\\(?:mathrm|mathcal|mathbb|textrm)\s+[A-Za-z]|\\operatorname\s+[A-Za-z]+|(?<![A-Za-z])d(?=[ezt](?![A-Za-z])|\\xi)')
TOKEN=re.compile(r'\\[A-Za-z]+|[A-Za-z]')
stats={}
for name in NAMES:
    source=(P/(name+'.tex')).read_text(encoding='utf-8')
    assert r'\$' not in source.replace(r'\\$', '$'), 'Review escaped currency delimiters'
    count=[0]
    def region(m):
        text=m[0];saved=[]
        assert r'\draw' not in text and r'\node' not in text, 'Nonmath TikZ command in math span'
        def protect(p):
            saved.append(p[0]);return f'§{len(saved)-1}§'
        text=PROTECT.sub(protect,text)
        def token(t):
            s=t[0];tail=text[t.end():]
            bold=False
            if s=='Q' and name=='main_joint_kernel' and tail.startswith('_h'):
                bold=False # Q_h^eta denotes a mixture measure, not covariance Q
            elif s in ['A','Q','Z','I','P','K','D',r'\Sigma']:
                bold=True
            elif s==r'\xi':bold=name=='main_joint_kernel'
            elif s==r'\mu':bold=tail.startswith('_') # indexed conditional mean; bare mu is a probability law
            elif s=='R':
                # R_full, R_bits, R_marked and R_j are record variables.
                bold=not re.match(r'_\s*(?:j|\{?§)',tail)
            elif s=='H':bold=tail.startswith('(P)')
            elif s=='W':bold=name=='theory' and tail.startswith('_h')
            elif s in ['y','m','d','v','z']:bold=True
            elif s=='x':bold=tail.startswith('_') or 'y=Cx' in text
            elif s=='C':bold='(A,C)' in text or 'y=Cx' in text or tail.startswith('A')
            elif s in ['w','a']:bold=bool(re.match(r'_(?:[tk]|\{[tk]|\{k\+1\})',tail))
            elif s=='S':bold=name=='main_joint_kernel' and bool(re.match(r"'?_h",tail))
            elif s in ['e','u','z']:
                bold=name=='main_joint_kernel' # here all three are vector innovations
            if bold:
                count[0]+=1;return r'{\bm{'+s+'}}'
            return s
        text=TOKEN.sub(token,text)
        for i,v in enumerate(saved):text=text.replace(f'§{i}§',v)
        return text
    result=REGION.sub(region,source)
    # Typography must be exactly reversible, before input paths are adjusted.
    unbold=re.sub(r'\{\\bm\{(\\[A-Za-z]+|[A-Za-z])\}\}',r'\1',result)
    assert unbold==source,name
    for child in NAMES:result=result.replace(r'\input{'+child+'}',r'\input{ecust_typeset/'+child+'}')
    (OUT/(name+'.tex')).write_text(result,encoding='utf-8')
    stats[name]={'bold_symbols':count[0],'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'reversible':True}
(P/'math_typography_check.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for src,dst in [('protocol-figure','fig01_protocol'),('graphical_abstract','graphical_summary')]:
    data=(OUT/(src+'.tex')).read_text(encoding='utf-8')
    tikz=re.search(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',data,re.S)[0]
    target=P/'figures'/(dst+'.tex')
    old=target.read_text(encoding='utf-8')
    old=re.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',lambda m:tikz,old,flags=re.S)
    old=old.replace('fontspec,amsmath,amssymb,newtxmath,tikz','fontspec,amsmath,amssymb,newtxmath,bm,tikz')
    target.write_text(old,encoding='utf-8')
print('Bold-italic typography generated from unchanged source tokens:',sum(s['bold_symbols'] for s in stats.values()))
