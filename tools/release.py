"""The release: build/game.ssd, build/game.adl, build/ta.ssd and build/ta.adl (make game, make ta) in OUT named as
tools/disc_readme.py's values name them (super-sprint-WHEN-VERSION.ssd, super-sprint-ta-..., WHEN the commit's time
in UTC: Tom, 2026-11-10: "named with commit time and date (in UTC) as well as the part of the commit hash shown
in-game"), the zip's README.txt (disc_readme.py pc), and all five in one zip named the same, its entries' times the
commit's so the same commit makes the same zip; then each file's SHA-256 said. The GitHub build runs it (make release,
.github/workflows/build.yml), so a release can be looked at here first (Tom, 2026-11-15).

The discs must have this build's README: each .ssd's the one disc_readme.py makes now (game.ssd's game's, ta.ssd's
ta's), else it stops, saying to make them again. So a disc made at another commit is caught (the link's always on
it), and one whose README shows another value; not one made at another version the README doesn't show (MEASURED: make
release VERSION=abcde, with a README without {{version}} or the names, went ahead).

Under GitHub Actions (GITHUB_OUTPUT set) it adds name=NAME and files=FILES (the five, not the zip) there.

Usage (from the repo root, after make game and make ta): release.py OUT   (make release: OUT dist)
"""
import hashlib, os, shutil, sys, zipfile

sys.path.insert(0, os.path.dirname(__file__))
import disc_readme
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs                              # the kit's .ssd reader (as tools/make_game.py)


def main(out):
    vals = disc_readme.values()
    for kind in ('game', 'ta'):
        disc = f'build/{kind}.ssd'
        if not os.path.exists(disc):
            sys.exit(f'{disc}: not there (make game, make ta first)')
        got = dfs.read_image(disc).files['README'].data
        if got != disc_readme.readme(kind, vals):
            sys.exit(f'{disc}: its README isn\'t this build\'s (another commit, or another value it shows): make game and '
                     f'make ta again (as two makes: they share build/sprint.*)')
    name = f'super-sprint-{vals["stamp"]}'
    files = [(vals['game_ssd'], 'build/game.ssd'), (vals['game_adl'], 'build/game.adl'),
             (vals['ta_ssd'], 'build/ta.ssd'), (vals['ta_adl'], 'build/ta.adl')]
    os.makedirs(out, exist_ok=True)
    for to, frm in files:
        shutil.copyfile(frm, os.path.join(out, to))
    open(os.path.join(out, 'README.txt'), 'wb').write(disc_readme.readme('pc', vals))
    names = [to for to, _ in files] + ['README.txt']
    when = vals['stamp'].split('-')
    stamp = (int(when[0][:4]), int(when[0][4:6]), int(when[0][6:8]), int(when[1][:2]), int(when[1][2:]), 0) \
        if when[0] != 'unknown' else (1980, 1, 1, 0, 0, 0)
    zipped = os.path.join(out, f'{name}.zip')
    with zipfile.ZipFile(zipped, 'w') as z:
        for n in names:
            info = zipfile.ZipInfo(n, stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(os.path.join(out, n), 'rb').read())
    for n in names + [f'{name}.zip']:
        print(f'{hashlib.sha256(open(os.path.join(out, n), "rb").read()).hexdigest()}  {n}')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'name={name}\nfiles={" ".join(names)}\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
