"""Local C check of the UDF with libclang against tests/stub/udf.h (a stand-in for Fluent's header).
    uv run --no-project --with libclang --with numpy --with scipy python tests/udf_syntax_check.py
Catches syntax and type errors before the cluster; the real compile happens in Fluent on Puma."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fluent2d.params import header, load_case, plan  # noqa: E402


def main():
    from clang import cindex
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "etch_params.h").write_text(header(plan(load_case("A_f1_I2_t45"))))
        tu = cindex.Index.create().parse(str(ROOT / "fluent2d" / "udf" / "etch.c"),
                                         args=["-std=c99", "-Wall", "-Wextra", "-I", str(ROOT / "tests" / "stub"),
                                               "-I", d])
        bad = 0
        for dg in tu.diagnostics:
            print(f"{dg.severity}: {dg.location.file}:{dg.location.line}: {dg.spelling}")
            bad += dg.severity >= cindex.Diagnostic.Error
        print(f"{len(list(tu.diagnostics))} diagnostics, {bad} errors")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
