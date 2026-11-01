#!/usr/bin/env python3
"""Lift Megamax C 68000 code from build/super.s into rough pseudo-C, one function at a time.

Usage: tools/logic_lift.py <hex addr> [<hex addr> ...]   (or 'all')
Symbolic execution within basic blocks: register contents become expressions, stores
become assignments, compares + branches become 'if (...) goto'. Anything not understood
is printed as the raw instruction in a comment. Names: G_xxxxxx globals (a4-relative),
lN locals (-N(a6)), pN parameters (N(a6)), w[]/l[]/b[] word/long/byte arrays.
"""
import re, sys, os, json

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A4 = 0x1F296

LINE = re.compile(r'^([0-9A-F]{6})  (\S+)\s*(.*?)\s*(?:->\s*(\S+))?\s*(?:;\s*(.*))?$')

def load():
    lines = open(os.path.join(ROOT, 'build/super.s')).read().split('\n')
    insns = []
    for ln in lines:
        m = LINE.match(ln)
        if not m:
            continue
        addr, mn, ops, tgt, cmt = m.groups()
        ops = ops.strip()
        insns.append((int(addr, 16), mn, ops, tgt, cmt or ''))
    return insns

def split_ops(s):
    out, depth, cur = [], 0, ''
    for c in s:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += c
    if cur.strip():
        out.append(cur.strip())
    return out

def num(s):
    s = s.strip()
    neg = s.startswith('-')
    if neg:
        s = s[1:]
    v = int(s[1:], 16) if s.startswith('$') else int(s)
    return -v if neg else v

# ---- expressions: tuples
# ('n', v) const; ('v', name) variable/register; ('a', name) address of global; ('b', op, x, y)
# ('m', size, addrexpr) memory; ('u', op, x); ('c', text) opaque

def C(v): return ('n', v)
def V(n): return ('v', n)

def simp(e):
    if e[0] == 'b':
        op, x, y = e[1], simp(e[2]), simp(e[3])
        if x[0] == 'n' and y[0] == 'n':
            a, b = x[1], y[1]
            try:
                r = {'+': a + b, '-': a - b, '*': a * b, '<<': a << b, '&': a & b, '|': a | b}[op]
                return C(r)
            except KeyError:
                pass
        if op == '+' and y[0] == 'n' and y[1] == 0: return x
        if op == '+' and x[0] == 'n' and x[1] == 0: return y
        if op == '-' and y[0] == 'n' and y[1] < 0: return ('b', '+', x, C(-y[1]))
        if op == '+' and y[0] == 'n' and y[1] < 0: return ('b', '-', x, C(-y[1]))
        if op == '+' and x[0] == 'b' and x[1] == '+' and x[3][0] == 'n' and y[0] == 'n':
            return simp(('b', '+', x[2], C(x[3][1] + y[1])))
        return ('b', op, x, y)
    if e[0] == 'm':
        return ('m', e[1], simp(e[2]))
    if e[0] == 'u':
        return ('u', e[1], simp(e[2]))
    return e

def hexs(v):
    if -10 < v < 10:
        return str(v)
    return ('-' if v < 0 else '') + '0x%X' % abs(v)

PREC = {'*': 5, '/': 5, '%': 5, '+': 4, '-': 4, '<<': 3, '>>': 3, '>>u': 3, '<': 2, '>': 2, '<=': 2, '>=': 2,
        '==': 2, '!=': 2, '<u': 2, '>u': 2, '<=u': 2, '>=u': 2, '&': 1, '^': 1, '|': 1}

def index_of(addr, size):
    """If addr is base + idx*size, return (basestr, idxexpr) for array printing."""
    sh = {1: 0, 2: 1, 4: 2}[size]
    base, idx, off = None, None, 0
    terms = []
    def flat(e, sign=1):
        if e[0] == 'b' and e[1] == '+':
            flat(e[2], sign); flat(e[3], sign)
        elif e[0] == 'b' and e[1] == '-' and e[3][0] == 'n':
            flat(e[2], sign); terms.append(C(-e[3][1]))
        else:
            terms.append(e)
    flat(addr)
    rest = []
    for t in terms:
        if t[0] == 'a' and base is None:
            base = t
        elif t[0] == 'n':
            off += t[1]
        else:
            rest.append(t)
    return base, rest, off

def scaled(t, sh):
    """t is idx<<sh or idx*(1<<sh)? return idx expression else None"""
    if sh == 0:
        return t
    if t[0] == 'b' and t[1] == '<<' and t[3][0] == 'n':
        k = t[3][1]
        if k == sh:
            return t[2]
        if k > sh:
            return ('b', '<<', t[2], C(k - sh))
    if t[0] == 'b' and t[1] == '*' and t[3][0] == 'n' and t[3][1] % (1 << sh) == 0:
        return ('b', '*', t[2], C(t[3][1] >> sh)) if t[3][1] >> sh != 1 else t[2]
    return None

SZ = {1: 'b', 2: 'w', 4: 'l'}

def gname(off):
    return 'G_%06X' % (A4 + off)

def P(e, prec=0):
    k = e[0]
    if k == 'n':
        return hexs(e[1])
    if k == 'v':
        return e[1]
    if k == 'c':
        return e[1]
    if k == 'a':
        return '&' + e[1]
    if k == 'u':
        if e[1] == 'call':
            return e[2][1]
        return e[1] + P(e[2], 9)
    if k == 'b':
        op = e[1]
        p = PREC.get(op, 0)
        s = P(e[2], p) + ' ' + op + ' ' + P(e[3], p + 1)
        return '(' + s + ')' if p < prec else s
    if k == 'm':
        size, addr = e[1], e[2]
        base, rest, off = index_of(addr, size)
        sh = {1: 0, 2: 1, 4: 2}[size]
        if base is not None:
            name = base[1]
            if not rest:
                if off == 0:
                    return name if size == 2 else name + '.' + SZ[size]
                if off % size == 0:
                    return '%s.%s[%d]' % (name, SZ[size], off // size)
                return '%s.%s[+%d]' % (name, SZ[size], off)
            if len(rest) == 1:
                idx = scaled(rest[0], sh)
                if idx is not None:
                    a = base[1] if off == 0 else '%s+%d' % (base[1], off)
                    if off and off % size == 0:
                        a = gname_add(base[1], off)
                    return '%s.%s[%s]' % (a, SZ[size], P(idx))
        # pointer + offset
        if base is None and len(rest) == 1:
            return '%s->%s%s' % (P(rest[0], 9), SZ[size], hexs(off) if off else '0')
        return '*(%s*)(%s)' % (SZ[size], P(addr))
    return repr(e)

def gname_add(name, off):
    m = re.match(r'G_([0-9A-F]{6})$', name)
    if m:
        return 'G_%06X' % (int(m.group(1), 16) + off)
    return '%s+%d' % (name, off)

class Lifter:
    def __init__(self, insns):
        self.insns = insns
        self.targets = set()
        for a, mn, ops, tgt, cmt in insns:
            if tgt and tgt.startswith('L_') and (mn.startswith('b') or mn.startswith('db') or mn == 'jmp'):
                self.targets.add(int(tgt[2:], 16))
        funcs = json.load(open(os.path.join(ROOT, 'build/super.json')))['functions']
        self.funcs = sorted(int(k, 16) for k in funcs)
        self.fnames = {int(k, 16): v['name'] for k, v in funcs.items()}

    def reset(self):
        self.r = {}
        for i in range(8):
            self.r['d%d' % i] = V('d%d' % i)
            self.r['a%d' % i] = V('a%d' % i)
        self.flags = None

    def ea(self, s, size):
        """Return ('val', expr) or ('mem', addr) or ('reg', name) or ('push',) or ('pop',)"""
        s = s.strip()
        if re.fullmatch(r'[da][0-7]', s):
            return ('reg', s)
        if s == 'sp':
            return ('reg', 'a7')
        if s.startswith('#'):
            return ('val', C(num(s[1:])))
        if s == '-(a7)' or s == '-(sp)':
            return ('push',)
        if s == '(a7)+':
            return ('pop',)
        m = re.fullmatch(r'(-?\$?[0-9a-f]*)\((a[0-7]|pc)\)', s)
        if m:
            off = num(m.group(1)) if m.group(1) else 0
            reg = m.group(2)
            if reg == 'a4':
                return ('mem', ('a', gname(off)))
            if reg == 'a6':
                nm = ('l%X' % -off) if off < 0 else ('p%X' % off)
                return ('mem', ('a', nm))
            if reg == 'pc':
                return ('mem', ('a', 'T_%06X' % off))
            return ('mem', simp(('b', '+', self.r[reg], C(off))))
        m = re.fullmatch(r'(-?\$?[0-9a-f]*)\((a[0-7]),\s*([da][0-7])\.([wl])\)', s)
        if m:
            off = num(m.group(1)) if m.group(1) else 0
            return ('mem', simp(('b', '+', ('b', '+', self.r[m.group(2)], self.r[m.group(3)]), C(off))))
        m = re.fullmatch(r'\((a[0-7])\)\+', s)
        if m:
            return ('postinc', m.group(1))
        m = re.fullmatch(r'-\((a[0-7])\)', s)
        if m:
            return ('predec', m.group(1))
        m = re.fullmatch(r'\$([0-9a-f]+)\.[lw]', s)
        if m:
            return ('mem', ('a', 'HW_%X' % (int(m.group(1), 16) & 0xFFFFFF)))
        m = re.fullmatch(r'\$([0-9a-f]+)', s)
        if m:
            return ('mem', ('a', 'ABS_%X' % int(m.group(1), 16)))
        return None

    def read(self, e, size):
        if e is None:
            return None
        if e[0] == 'reg':
            return self.r[e[1]]
        if e[0] == 'val':
            return e[1]
        if e[0] == 'mem':
            return simp(('m', size, e[1]))
        if e[0] == 'postinc':
            v = simp(('m', size, self.r[e[1]]))
            self.r[e[1]] = simp(('b', '+', self.r[e[1]], C(size)))
            return v
        if e[0] == 'predec':
            self.r[e[1]] = simp(('b', '-', self.r[e[1]], C(size)))
            return simp(('m', size, self.r[e[1]]))
        if e[0] == 'pop':
            return V('pop')
        return None

    def lea(self, s):
        e = self.ea(s, 4)
        if e and e[0] == 'mem':
            return e[1]
        return None

    def write(self, e, size, val, out, op='='):
        if e[0] == 'reg':
            if op == '=':
                self.r[e[1]] = val
            else:
                self.r[e[1]] = simp(('b', op, self.r[e[1]], val))
            return
        if e[0] == 'push':
            self.stack.append((size, val))
            return
        if e[0] in ('postinc', 'predec'):
            if e[0] == 'predec':
                self.r[e[1]] = simp(('b', '-', self.r[e[1]], C(size)))
            dst = simp(('m', size, self.r[e[1]]))
            if e[0] == 'postinc':
                self.r[e[1]] = simp(('b', '+', self.r[e[1]], C(size)))
        else:
            dst = simp(('m', size, e[1]))
        if op == '=':
            out.append('%s = %s;' % (P(dst), P(val)))
        else:
            out.append('%s %s= %s;' % (P(dst), op, P(val)))
        # registers holding the old memory value become stale: keep it simple
        for k, v in self.r.items():
            if v == dst:
                self.r[k] = V(k + "'")

    def lift(self, start, end):
        out = []
        self.reset()
        self.stack = []
        pending = None
        for a, mn, ops, tgt, cmt in self.insns:
            if a < start or a >= end:
                continue
            if a in self.targets:
                if pending:
                    out.append(pending); pending = None
                out.append('L_%06X:' % a)
                self.reset()
            base = mn.split('.')[0]
            size = {'b': 1, 'w': 2, 'l': 4}.get(mn.split('.')[1], 4) if '.' in mn else 4
            o = split_ops(ops)
            note = ('  // ' + cmt) if cmt and not cmt.startswith('G_') else ''
            try:
                handled = self.step(a, base, size, o, tgt, out, note)
            except Exception as ex:
                handled = False
            if handled == 'call':
                continue
            if not handled:
                out.append('    /* %06X %s %s */%s' % (a, mn, ops, note))
                # invalidate destination register
                if o and re.fullmatch(r'[da][0-7]', o[-1]):
                    self.r[o[-1]] = V(o[-1] + '?')
        return out

    def flush_call(self, out):
        pass

    def step(self, a, base, size, o, tgt, out, note):
        r = self.r
        if base == 'link':
            out.append('{ // frame %d' % -num(o[1][1:]))
            return True
        if base in ('unlk', 'nop'):
            return True
        if base == 'rts':
            out.append('return %s;' % P(r['d0']))
            return True
        if base == 'movem':
            return True
        if base in ('move', 'movea'):
            src = self.ea(o[0], size)
            dst = self.ea(o[1], size)
            if src is None or dst is None:
                return False
            v = self.read(src, size)
            if v is None:
                return False
            if dst[0] == 'reg' and dst[1] == 'a7':
                return True
            self.write(dst, size, v, out)
            self.flags = ('t', v)
            return True
        if base == 'clr':
            dst = self.ea(o[0], size)
            self.write(dst, size, C(0), out)
            self.flags = ('t', C(0))
            return True
        if base == 'moveq':
            r[o[1]] = C(num(o[0][1:]))
            return True
        if base == 'lea':
            ad = self.lea(o[0])
            if ad is None:
                return False
            r[o[1]] = ad
            return True
        if base == 'pea':
            ad = self.lea(o[0])
            if ad is None:
                return False
            self.stack.append((4, ad))
            return True
        if base in ('add', 'adda', 'addq', 'addi', 'sub', 'suba', 'subq', 'subi', 'and', 'andi', 'or', 'ori',
                    'eor', 'eori', 'muls', 'mulu', 'divs', 'divu', 'asl', 'lsl', 'asr', 'lsr'):
            opmap = {'add': '+', 'sub': '-', 'and': '&', 'or': '|', 'eor': '^', 'muls': '*', 'mulu': '*',
                     'divs': '/', 'divu': '/', 'asl': '<<', 'lsl': '<<', 'asr': '>>', 'lsr': '>>u'}
            k = base.rstrip('aqi') if base not in ('asl', 'lsl', 'asr', 'lsr', 'muls', 'mulu', 'divs', 'divu') else base
            if base in ('suba', 'subq', 'subi'):
                k = 'sub'
            if base in ('adda', 'addq', 'addi'):
                k = 'add'
            if base in ('andi',):
                k = 'and'
            if base in ('ori',):
                k = 'or'
            if base in ('eori',):
                k = 'eor'
            op = opmap[k]
            if len(o) == 1:  # shift by 1 of memory
                o = ['#1', o[0]]
            dst = self.ea(o[1], size)
            if dst[0] == 'reg' and dst[1] == 'a7':
                # stack cleanup after call
                if k == 'add' and self.pcall is not None:
                    n = num(o[0][1:])
                    self.emit_call(n, out)
                return True
            src = self.read(self.ea(o[0], size), size)
            if src is None:
                return False
            if k in ('divs', 'divu'):
                r[o[1]] = ('b', '/', r[o[1]], src)
                r['_div'] = (r[o[1]][2], src)
                self.flags = ('t', r[o[1]])
                return True
            if dst[0] == 'reg':
                r[dst[1]] = simp(('b', op, r[dst[1]], src))
                self.flags = ('t', r[dst[1]])
            else:
                self.write(dst, size, src, out, op)
                self.flags = None
            return True
        if base == 'swap':
            v = r[o[0]]
            if v[0] == 'b' and v[1] == '/':
                r[o[0]] = ('b', '%', v[2], v[3])
            else:
                r[o[0]] = ('u', 'swap ', v)
            return True
        if base in ('ext', 'extb'):
            return True
        if base in ('neg', 'not'):
            dst = self.ea(o[0], size)
            v = self.read(dst, size)
            self.write(dst, size, ('u', '-' if base == 'neg' else '~', v), out)
            return True
        if base == 'exg':
            r[o[0]], r[o[1]] = r[o[1]], r[o[0]]
            return True
        if base in ('cmp', 'cmpi', 'cmpa'):
            s = self.read(self.ea(o[0], size), size)
            d = self.read(self.ea(o[1], size), size)
            self.flags = ('c', d, s)
            return True
        if base == 'tst':
            self.flags = ('t', self.read(self.ea(o[0], size), size))
            return True
        if base == 'btst':
            b = self.read(self.ea(o[0], size), size)
            d = self.read(self.ea(o[1], size), size)
            self.flags = ('t', ('b', '&', d, ('b', '<<', C(1), b)))
            return True
        if base in ('bset', 'bclr'):
            b = self.read(self.ea(o[0], size), size)
            dst = self.ea(o[1], size)
            if base == 'bset':
                self.write(dst, size, ('b', '<<', C(1), b), out, '|')
            else:
                self.write(dst, size, ('u', '~', ('b', '<<', C(1), b)), out, '&')
            return True
        if base in ('beq', 'bne', 'blt', 'bgt', 'ble', 'bge', 'bmi', 'bpl', 'bcc', 'bcs', 'bhi', 'bls'):
            cond = self.cond(base[1:])
            out.append('    if (%s) goto %s;' % (cond, tgt))
            return True
        if base in ('bra', 'jmp') and tgt and tgt.startswith('L_'):
            out.append('    goto %s;' % tgt)
            return True
        if base in ('seq', 'sne', 'slt', 'sgt', 'sle', 'sge', 'scs', 'scc', 'smi', 'spl'):
            r[o[0]] = ('c', '(' + self.cond(base[1:]) + ')')
            return True
        if base == 'dbra':
            out.append('    if (--%s != -1) goto %s;' % (P(r[o[0]]), tgt))
            r[o[0]] = V(o[0])
            return True
        if base in ('jsr', 'bsr'):
            name = tgt or o[0]
            m = re.match(r'(\S+?)_?([0-9A-F]{6})$', name or '')
            self.pcall = (name, list(self.stack), note)
            # a call with no cleanup: emit now with 0 bytes of args (fixed up if cleanup follows)
            self.call_out_idx = len(out)
            out.append(None)
            self.emit_call(0, out, provisional=True)
            return True
        if base == 'trap':
            out.append('    trap %s (args %s)%s' % (o[0], ', '.join(P(v) for s, v in reversed(self.stack)), note))
            self.stack = []
            r['d0'] = V('trapret')
            return True
        return False

    def emit_call(self, nbytes, out, provisional=False):
        name, stack, note = self.pcall
        args = []
        stk = list(stack)
        n = nbytes
        while n > 0 and stk:
            s, v = stk.pop()
            args.append(P(v))
            n -= s
        txt = '    rv = %s(%s);%s' % (name, ', '.join(args), note)
        out[self.call_out_idx] = txt
        self.stack = stk
        self.r['d0'] = V('rv')
        for k in ('d1', 'd2', 'a0', 'a1'):
            self.r[k] = V(k + '?')
        if not provisional:
            self.pcall = None

    def cond(self, cc):
        f = self.flags
        if f is None:
            return 'flags ' + cc
        if f[0] == 'c':
            d, s = f[1], f[2]
            op = {'eq': '==', 'ne': '!=', 'lt': '<', 'gt': '>', 'le': '<=', 'ge': '>=', 'cs': '<u', 'cc': '>=u',
                  'hi': '>u', 'ls': '<=u', 'mi': '-<0', 'pl': '->=0'}[cc]
            if op.startswith('-'):
                return '%s - %s %s' % (P(d), P(s), op[1:])
            return '%s %s %s' % (P(d, 3), op, P(s, 3))
        v = f[1]
        op = {'eq': '== 0', 'ne': '!= 0', 'lt': '< 0', 'gt': '> 0', 'le': '<= 0', 'ge': '>= 0', 'mi': '< 0',
              'pl': '>= 0', 'cs': 'C', 'cc': '!C', 'hi': 'hi', 'ls': 'ls'}[cc]
        return '%s %s' % (P(v, 3), op)


def main():
    insns = load()
    L = Lifter(insns)
    L.pcall = None
    args = sys.argv[1:]
    if args == ['all']:
        args = ['%06X' % f for f in L.funcs]
    for h in args:
        a = int(h, 16)
        i = L.funcs.index(a)
        end = L.funcs[i + 1] if i + 1 < len(L.funcs) else 0x1C722
        print('// ==== %s (%06X-%06X)' % (L.fnames[a], a, end))
        for s in L.lift(a, end):
            if s is not None:
                print(s if s.startswith((' ', 'L_', '{', '/')) else '    ' + s)
        print()

if __name__ == '__main__':
    main()
