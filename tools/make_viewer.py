"""Build a bootable viewer disc per palette option: build/viewer/disc<option>.ssd.

Each disc holds the 8 converted tracks (with sample cars), as T0-T7 for *LOAD to &4180, and a !BOOT that
types the viewer into BASIC and runs it (boot option 3, *EXEC). The viewer sets MODE 1, prints a sample HUD
row, then cuts the screen to 26 rows from &3F00. SPACE (or any key) shows the next track.
Run after tools/convert.py build/conv. Needs baron on the PATH.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from convert import OPTIONS, PHYS

VIEWER = '''10 REM Option {key}: {name}
20 P0={p0}:P1={p1}:P2={p2}:P3={p3}:C0={c0}:C1={c1}:C2={c2}:CD={cd}
30 MODE 1:VDU 23,1,0;0;0;0;
40 VDU 19,0,P0;0;19,1,P1;0;19,2,P2;0;19,3,P3;0;
50 PRINT TAB(0,6);:COLOUR C0:PRINT "99,999 L1 ";:COLOUR C1:PRINT "12,340 L2 ";:COLOUR C2:PRINT " 5,260 L3  ";:COLOUR CD:PRINT "T1 D1";
60 VDU 23,0,6,26;0;0;0;23,0,7,31;0;0;0;23,0,12,7;0;0;0;23,0,13,&E0;0;0;0;
70 T=0
80 OSCLI "LOAD T"+STR$T+" 4180"
90 A=GET:T=(T+1) MOD 8:GOTO 80
'''


def body(opt, car):
    """The logical colour of a player's car, for its HUD text."""
    return opt['pal'].index(opt['slots'][car])


def main():
    os.makedirs('build/viewer', exist_ok=True)
    for key, opt in OPTIONS.items():
        p = [PHYS[c] for c in opt['pal']]
        white = opt['pal'].index('W')
        text = VIEWER.format(key=key, name=opt['name'], p0=p[0], p1=p[1], p2=p[2], p3=p[3],
                             c0=body(opt, 0), c1=body(opt, 1), c2=body(opt, 2), cd=white)
        boot = '*BASIC\r' + text.replace('\n', '\r') + 'RUN\r'
        src = [f'\\\\ Viewer disc for option {key} (made by tools/make_viewer.py)',
               'SECTION Boot, filename = "!BOOT", org = 0',
               '    EQUS ' + ', '.join(f'{ord(ch)}' for ch in boot),
               'ENDSECTION']
        for t in range(8):
            src += [f'SECTION Track{t}, filename = "T{t}", org = &4180',
                    f'    INCBIN "../conv/{key}_t{t}.bin"', 'ENDSECTION']
        path = f'build/viewer/disc{key}.6502'
        open(path, 'w').write('\n'.join(src) + '\n')
        subprocess.run(['baron', '--opt', '3', '--title', f'SPRINT {key}', '-o', f'build/viewer/disc{key}.ssd', path],
                       check=True)
        print(f'build/viewer/disc{key}.ssd')


if __name__ == '__main__':
    main()
