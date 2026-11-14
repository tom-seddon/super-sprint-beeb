"""The disc's README: disc/README.txt, Tom's text, with one line after it linking to README.md as it was at the commit
the build was made from (Tom, 2026-11-10: "so that each release contains a link to its version-appropriate README").
Its lines end in CR, as the BBC's *TYPE wants them; with --pc in CR LF, for the release's zip, read on a PC (Tom,
2026-11-14: the zip holds the discs and "the disk's README as well").

The commit: COMMIT in the environment (tools/suite_remote.sh gives it where there's no .git), else git's HEAD. With
neither, no link line. A tree with changes still links to HEAD's README.md, the nearest there is (the options screen's
version says "m": tools/version.py).

Usage: disc_readme.py [--pc] OUT   (writes the file; tools/make_game.py puts it on the disc as README, and the
GitHub build, .github/workflows/build.yml, puts --pc's in its zip as README.txt)
"""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
Repo = 'https://github.com/tom-seddon/super-sprint-beeb'


def commit():
    c = os.environ.get('COMMIT')
    if c:
        return c
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def readme(eol='\r'):
    """-> the file's bytes, its lines ending in eol."""
    text = open(os.path.join(ROOT, 'disc', 'README.txt'), encoding='ascii').read().rstrip('\n') + '\n'
    c = commit()
    if c:
        assert len(c) == 40 and all(ch in '0123456789abcdef' for ch in c), c
        text += f'The full README, for this version: {Repo}/blob/{c}/README.md\n'
    return text.replace('\r\n', '\n').replace('\n', eol).encode('ascii')


if __name__ == '__main__':
    pc = sys.argv[1:2] == ['--pc']
    open(sys.argv[-1], 'wb').write(readme('\r\n' if pc else '\r'))
