"""The disc's README: disc/README.txt, Tom's text, with one line after it linking to README.md as it was at the commit
the build was made from (Tom, 2026-11-10: "so that each release contains a link to its version-appropriate README").
Its lines end in CR, as the BBC's *TYPE wants them. With --pc, the release zip's: disc/README-pc.txt, also Tom's text,
and the same line, the lines ending CR LF, in UTF-8 (Tom, 2026-11-14: "perhaps the zip should have a different README
from the disk, as it's intended for reading on a PC rather than the BBC's tiny screen").

The commit: COMMIT in the environment (tools/suite_remote.sh gives it where there's no .git), else git's HEAD. With
neither, no link line. A tree with changes still links to HEAD's README.md, the nearest there is (the options screen's
version says "m": tools/version.py).

Usage: disc_readme.py [--pc] OUT   (writes the file; tools/make_game.py puts the disc's on the disc as README, and the
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


def readme(pc=False):
    """-> the disc's README's bytes, its lines ending CR; or with pc the zip's, ending CR LF."""
    code = 'utf-8' if pc else 'ascii'      # (the BBC's: ASCII; a PC's may have more)
    text = open(os.path.join(ROOT, 'disc', 'README-pc.txt' if pc else 'README.txt'), encoding=code).read()
    text = text.replace('\r\n', '\n').rstrip('\n') + '\n'
    c = commit()
    if c:
        assert len(c) == 40 and all(ch in '0123456789abcdef' for ch in c), c
        text += f'The full README, for this version: {Repo}/blob/{c}/README.md\n'
    return text.replace('\n', '\r\n' if pc else '\r').encode(code)


if __name__ == '__main__':
    open(sys.argv[-1], 'wb').write(readme(sys.argv[1:2] == ['--pc']))
