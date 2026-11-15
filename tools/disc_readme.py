"""The READMEs, each Tom's text and a template: the game's disc's, from disc/README-game.txt, time attack's disc's,
from disc/README-ta.txt (both README on the disc), and the release zip's README.txt, from disc/README-pc.txt (Tom,
2026-11-15: "I think maybe it could do with 3 versions of the README actually"). {{name}} is filled in from the build
(values()), an unknown name an error. Then each file's trailing blank lines dropped. A file without {{link}} gets a
blank line and a line linking to README.md at the build's commit after it (Tom, 2026-11-10: "so that each release
contains a link to its version-appropriate README"; 2026-11-15, on the blank line: "The link is quite long in Mode 7.
I think it's worth having (just for reference) but it'd be nice to separate it visually from the instruction to press
Shift+break"); with {{link}}, it's where Tom puts it (2026-11-15: "Maybe it's going to need some kind of basic
templating, so that the disk images' actual names can be inserted into the README as well"). The discs' lines end in
CR, as the BBC's *TYPE wants them, ASCII; the zip's in CR LF, UTF-8.

The values (values()): {{version}}, the options screen's (the Makefile's VERSION, given to make_game.py and
release.py; else git's, as the Makefile makes it: 5 hex digits, "m" after them if the tree has changes); {{commit}},
the whole hash (COMMIT, else git's HEAD); {{date}}, the commit's time in UTC, "2026-11-14 11:03" (from WHEN, else
git's); {{link}}, README.md at that commit; and the release zip's discs' names (tools/release.py's, so the GitHub
build's too), {{game_ssd}}, {{game_adl}}, {{ta_ssd}}, {{ta_adl}}: super-sprint-WHEN-VERSION.ssd and so on, WHEN
the commit's time, 20261114-1103. tools/suite_remote.sh gives VERSION, COMMIT and WHEN where there's no .git; with
neither, "(not known)". A tree with changes still has HEAD's commit and time, the nearest there are.

Usage: disc_readme.py game|ta|pc OUT   (writes the file; tools/make_game.py puts game's or ta's on its disc as README,
                                        and tools/release.py pc's in the zip as README.txt)
       disc_readme.py --check          (all three filled in: an unknown name exit status 1. No check of the discs'
                                        line lengths: Tom, 2026-11-15, "I don't think the column check is worth
                                        having, as the README link will automatically run over. There won't be much
                                        churn in the README, I don't think, so I can check this by eye.")
"""
import os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
Repo = 'https://github.com/tom-seddon/super-sprint-beeb'
Unknown = '(not known)'
Placeholder = re.compile(r'\{\{(\w+)\}\}')
Kinds = ('game', 'ta', 'pc')            # disc/README-KIND.txt; pc's read on a PC, the others on a BBC


def git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True,
                              env={**os.environ, 'TZ': 'UTC'}).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def values():
    """-> the placeholders' values, by name."""
    commit = os.environ.get('COMMIT') or git('rev-parse', 'HEAD')
    if commit:
        assert len(commit) == 40 and all(ch in '0123456789abcdef' for ch in commit), commit
    version = os.environ.get('VERSION')
    if version is None:                 # (as the Makefile makes it)
        short = git('rev-parse', '--short=5', 'HEAD')
        version = (short + ('m' if git('status', '--porcelain') else '')) if short else ''
    when = os.environ.get('WHEN') or git('log', '-1', '--format=%cd', '--date=format-local:%Y%m%d-%H%M')
    assert not when or re.fullmatch(r'\d{8}-\d{4}', when), when
    stamp = f'{when or "unknown"}-{version or "unknown"}'
    return {
        'version': version or Unknown,
        'commit': commit or Unknown,
        'date': f'{when[:4]}-{when[4:6]}-{when[6:8]} {when[9:11]}:{when[11:13]}' if when else Unknown,
        'link': f'{Repo}/blob/{commit}/README.md' if commit else Unknown,
        'game_ssd': f'super-sprint-{stamp}.ssd', 'game_adl': f'super-sprint-{stamp}.adl',
        'ta_ssd': f'super-sprint-ta-{stamp}.ssd', 'ta_adl': f'super-sprint-ta-{stamp}.adl',
        'stamp': stamp,
    }


def text(kind, vals=None):
    """-> README kind's text (Kinds), filled in, its lines ending in \\n."""
    assert kind in Kinds, kind
    vals = vals or values()
    name = os.path.join('disc', f'README-{kind}.txt')
    t = open(os.path.join(ROOT, name), encoding='utf-8' if kind == 'pc' else 'ascii').read().replace('\r\n', '\n')
    unknown = sorted({n for n in Placeholder.findall(t) if n not in vals or n == 'stamp'})
    if unknown:
        sys.exit(f'{name}: no such value: {", ".join("{{" + n + "}}" for n in unknown)} '
                 f'(there are {", ".join("{{" + n + "}}" for n in vals if n != "stamp")})')
    linked = '{{link}}' in t
    t = Placeholder.sub(lambda m: vals[m.group(1)], t).rstrip('\n') + '\n'
    if not linked and vals['link'] != Unknown:
        t += f'\nThe full README, for this version: {vals["link"]}\n'
    return t


def readme(kind, vals=None):
    """-> README kind's bytes: a disc's (game, ta) its lines ending CR; the zip's (pc) ending CR LF."""
    pc = kind == 'pc'
    return text(kind, vals).replace('\n', '\r\n' if pc else '\r').encode('utf-8' if pc else 'ascii')


def check():
    vals = values()
    for kind in Kinds:
        text(kind, vals)                # (an unknown name: exits)
    print(f'the READMEs filled in: {", ".join(f"{k} {v}" for k, v in vals.items() if k != "stamp")}')


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        check()
    elif len(sys.argv) == 3 and sys.argv[1] in Kinds:
        open(sys.argv[2], 'wb').write(readme(sys.argv[1]))
    else:
        sys.exit(__doc__)
