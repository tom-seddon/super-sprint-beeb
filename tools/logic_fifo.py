#!/usr/bin/env python3
"""Send commands to a Hatari started with --cmd-fifo <path>, without blocking if Hatari has gone.
Usage: tools/logic_fifo.py <fifo> 'cmd' ['sleep:0.5'] 'cmd' ...
Commands are Hatari control-socket commands, e.g. 'hatari-event keydown 42' (42 = ST scancode),
'hatari-event keyup 42', 'hatari-debug m $462 4', 'hatari-debug screenshot /abs/x.png'."""
import os, sys, time, errno
fifo = sys.argv[1]
for c in sys.argv[2:]:
    if c.startswith('sleep:'):
        time.sleep(float(c[6:])); continue
    for _ in range(50):
        try:
            fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK); break
        except OSError as e:
            if e.errno != errno.ENXIO: raise
            time.sleep(0.1)
    else:
        sys.exit('no reader on ' + fifo)
    os.write(fd, (c + '\n').encode()); os.close(fd)
    time.sleep(0.2)
