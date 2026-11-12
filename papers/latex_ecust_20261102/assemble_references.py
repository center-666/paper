"""Maintain numeric references in order of first citation."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
old=(HERE/'references_base.tex').read_text(encoding='utf-8')
new=(HERE/'references_additions.tex').read_text(encoding='utf-8')
items={}
for text in [old,new]:
    text=text.split(r'\end{thebibliography}')[0]
    for match in re.finditer(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\Z)',text,re.S):
        assert match[1] not in items
        display = re.sub(r'\\url\{https://doi\.org/([^}]+)\}',
                         lambda m: r'\paperdoi{' + m[1] + '}', match[2].rstrip())
        # The reference articles link titles without printing a separate DOI line.
        # Keep DOI metadata in the two source files and preserve it as a title link.
        doi = re.search(r'DOI:\s*\\paperdoi\{([^}]+)\}\.', display)
        if doi:
            display = display[:doi.start()] + display[doi.end():]
            lines = display.strip().splitlines()
            assert len(lines) >= 3
            lines[1] = r'\href{https://doi.org/' + doi[1] + '}{' + lines[1] + '}'
            display = '\n' + '\n'.join(lines)
        items[match[1]]=r'\bibitem{'+match[1]+'}'+display+'\n'
order=[];locations={}
for name in ['introduction.tex','theory.tex','record_design.tex','numerical.tex','conclusion.tex',
             'vector_proof.tex','scalar_counterexample.tex','validation_appendix.tex',
             'statistical_extension.tex','finite_sample.tex','statistical_numerical.tex']:
    body=(HERE/name).read_text(encoding='utf-8')
    for match in re.finditer(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',body):
        for key in match[1].split(','):
            if key not in order: order.append(key)
            locations.setdefault(key,[]).append(dict(file=name,line=body[:match.start()].count('\n')+1))
assert not (set(order)-set(items)),set(order)-set(items)
(HERE/'references.tex').write_text('\\begin{thebibliography}{99}\n\n'+'\n'.join(items[k] for k in order)+'\n\\end{thebibliography}\n',encoding='utf-8')
(HERE/'citation_map.json').write_text(json.dumps(dict(count=len(order),order=order,locations=locations),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(order)} references; all cited; ordered by first appearance.')
