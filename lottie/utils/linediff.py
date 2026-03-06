from io import StringIO
from difflib import SequenceMatcher
from ..exporters import prettyprint


def difflines_str(a, b, widtha=None, widthb=None):
    lines_a = a.splitlines()
    lines_b = b.splitlines()
    ia = 0
    ib = 0

    if widtha is None:
        widtha = max(map(len, lines_a))
    if widthb is None:
        widthb = max(map(len, lines_b))

    for ja, jb, size in SequenceMatcher(None, lines_a, lines_b, False).get_matching_blocks():
        sideprinter(lines_a[ia:ja], lines_b[ib:jb], widtha, widthb, "\x1b[31m>", "=", "<\x1b[m")
        ia = ja+size
        ib = jb+size
        sideprinter(lines_a[ja:ia], lines_b[jb:ib], widtha, widthb, "\x1b[m ", "|", " \x1b[m")


def sideprinter(left, right, widtha=40, widthb=40, prefix="", infix=" | ", suffix=""):
    if len(left) > len(right):
        right += [""] * (len(left) - len(right))
    else:
        left += [""] * (len(right) - len(left))
    for l, r in zip(left, right):
        print("".join([prefix, l[:widtha].ljust(widtha), infix, r[:widthb].ljust(widthb), suffix]))


def difflines(a, b, widtha=None, widthb=None):
    ioa = StringIO()
    prettyprint(a, ioa)
    iob = StringIO()
    prettyprint(b, iob)
    difflines_str(ioa.getvalue(), iob.getvalue(), widtha, widthb)
