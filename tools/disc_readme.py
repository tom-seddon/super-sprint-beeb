"""The disc's README: disc/README.txt, Tom's text, with one line after it linking to README.md as it was at the commit
the build was made from (Tom, 2026-11-10: "so that each release contains a link to its version-appropriate README").
Its lines end in CR, as the BBC's *TYPE wants them.

The commit: COMMIT in the environment (tools/suite_remote.sh gives it where there's no .git), else git's HEAD. With
neither, no link line. A tree with changes still links to HEAD's README.md, the nearest there is (the options screen's
version says "m": tools/version.py).

Usage: disc_readme.py OUT   (writes the file, to look at; tools/make_game.py puts it on the disc as README)
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


def readme():
    """-> the file's bytes."""
    text = open(os.path.join(ROOT, 'disc', 'README.txt'), encoding='ascii').read().rstrip('\n') + '\n'
    c = commit()
    if c:
        assert len(c) == 40 and all(ch in '0123456789abcdef' for ch in c), c
        text += f'The full README, for this version: {Repo}/blob/{c}/README.md\n'
    return text.replace('\r\n', '\n').replace('\n', '\r').encode('ascii')


if __name__ == '__main__':
    open(sys.argv[1], 'wb').write(readme())
