#!/usr/bin/env python3
"""Package the files needed by Gradescope. Provided; DO NOT EDIT."""
from pathlib import Path
import zipfile
from gridworld import integrity, native


def main():
    root=Path(__file__).resolve().parent
    lang=native.language(root)
    files=[n for n in integrity.PROTECTED if not n.startswith('native/') or n.startswith(f'native/{lang}/')]
    files += list(native.editable(root))
    files += ['gridworld/__init__.py','gridworld/_manifest.py','language.txt','README.md','report.txt','report.pdf','.a1log']
    missing=[n for n in files if not (root/n).is_file()]
    if missing:
        raise SystemExit('Missing: '+', '.join(missing)+'. Complete report.txt, run python3 autograder.py, then python3 make_report.py.')
    out=root/'submission.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n in sorted(set(files)):
            z.write(root/n, 'cs440-a1/'+n)
    print(f'Wrote {out.name} ({lang}). Upload it to Gradescope and add all team members.')
    print('Generate report.pdf again after changing code, answers, or team members.')

if __name__=='__main__':main()
