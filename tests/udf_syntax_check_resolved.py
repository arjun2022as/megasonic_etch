"""Local C check (libclang, tests/stub/udf.h) of the case-10 UDF exactly as run_resolved.py assembles it:
etch.c with the parameters inlined + resolved_extra.c appended.
    uv run --no-project --with libclang --with numpy --with scipy python tests/udf_syntax_check_resolved.py"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_resolved as RR  # noqa: E402


def main():
    from clang import cindex
    p = RR.plan(RR.load("R15_comb", RR.CASES_CSV))
    p["mesh_info"] = dict(y_top_cell=9.953e-6, h_top_cell=0.094e-6)     # as meshed (top-row pin, 2026-11-27)
    RR.pin_top(p)
    src = (ROOT / "fluent2d" / "udf" / "etch.c").read_text()
    src = src.replace('#include "etch_params.h"', RR.header_resolved(p)) + "\n" + \
        (ROOT / "fluent2d" / "udf" / "resolved_extra.c").read_text()
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "etch.c"
        f.write_text(src)
        tu = cindex.Index.create().parse(str(f), args=["-std=c99", "-Wall", "-Wextra", "-I",
                                                       str(ROOT / "tests" / "stub")])
        bad = 0
        for dg in tu.diagnostics:
            print(f"{dg.severity}: line {dg.location.line}: {dg.spelling}")
            bad += dg.severity >= cindex.Diagnostic.Error
        print(f"{len(list(tu.diagnostics))} diagnostics, {bad} errors")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
