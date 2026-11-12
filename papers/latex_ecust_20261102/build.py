"""Compile the local XeLaTeX project and resolve cross-document references."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent

def executable(name):
    texlive_bin = os.environ.get('TEXLIVE_BIN')
    if texlive_bin:
        candidate = Path(texlive_bin) / name
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name) or shutil.which(Path(name).stem)
    if not found:
        raise FileNotFoundError(f'{name} was not found on PATH; set TEXLIVE_BIN if needed')
    return found

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(stem):
    result = subprocess.run(
        [executable('xelatex.exe'), '-interaction=nonstopmode', '-halt-on-error',
         '-file-line-error', '-synctex=1', stem + '.tex'], cwd=HERE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (HERE / (stem + '_build.txt')).write_bytes(result.stdout)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace')[-5000:])
        raise SystemExit(result.returncode)

def main():
    # A draft run is for locating layout warnings before all edits are final.
    draft = '--draft' in sys.argv
    sequence = ['paper', 'supplement', 'paper', 'supplement', 'paper', 'paper_submission', 'paper_submission', 'graphical', 'graphical']
    if draft:
        sequence = ['paper', 'supplement', 'paper']
    subprocess.run([sys.executable, str(HERE / 'assemble_references.py')], check=True)
    subprocess.run([sys.executable, str(HERE / 'prepare_ecust_math.py')], check=True)
    for stem in sequence:
        run(stem)
    if not draft:
        for stem in ['fig01_protocol', 'graphical_summary']:
            result = subprocess.run(
                [executable('xelatex.exe'), '-interaction=nonstopmode', '-halt-on-error', stem+'.tex'],
                cwd=HERE/'figures', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (HERE/'figures'/(stem+'_build.txt')).write_bytes(result.stdout)
            if result.returncode:
                print(result.stdout.decode('utf-8',errors='replace')[-2500:])
                raise SystemExit(result.returncode)
    rows = {}
    for stem in ['paper', 'supplement'] + ([] if draft else ['paper_submission','graphical']):
        log = (HERE / (stem + '.log')).read_text(encoding='utf-8', errors='replace')
        warnings = []
        for marker in ['undefined references', 'undefined on input', 'multiply defined',
                       'Overfull \\hbox', 'Overfull \\vbox', 'Missing character:',
                       'Invalid page number', 'There were undefined citations']:
            if marker in log:
                warnings.append(marker)
        subprocess.run([executable('pdftotext.exe'), '-layout', '-enc', 'UTF-8',
                        stem + '.pdf', stem + '_extracted.txt'], cwd=HERE, check=True)
        text = (HERE / (stem + '_extracted.txt')).read_text(encoding='utf-8')
        assert '\ufffd' not in text
        if '??' in text:
            warnings.append('unresolved printed reference')
        match = re.search(r'Output written on .*? \((\d+) pages?\)', log)
        rows[stem] = dict(pages=int(match.group(1)), warnings=warnings,
                          pdf_sha256=sha(HERE / (stem + '.pdf')))
    result = dict(passed=all(not row['warnings'] for row in rows.values()),
                  draft=draft, engine=executable('xelatex.exe'), documents=rows,
                  source_sha256={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('*.tex'))})
    (HERE / ('draft_build.json' if draft else 'build_check.json')).write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, ensure_ascii=True, indent=2))
    if not draft and not result['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
