from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
PYDIR = ROOT / "src" / "py"
sys.path.insert(0, str(PYDIR))

from neftys_v1 import Lexer, Parser, SemanticAnalyzer


def analyze(source: str):
    tokens = Lexer(source).tokenize(); tree = Parser(tokens).parse(); sem = SemanticAnalyzer(source); diags = sem.analyze(tree)
    return tokens, tree, sem, diags


class FrontendTests(unittest.TestCase):
    def test_indent_and_new_syntax(self):
        tokens, _, _, diags = analyze('se Ver então\n    fale "sim"\nfale "fim"\n')
        self.assertFalse(diags)
        kinds = [t.kind for t in tokens]
        self.assertIn("INDENT", kinds); self.assertIn("DEDENT", kinds)

    def test_numeric_identifier_requires_escape(self):
        with self.assertRaises(Exception): analyze("1 = 2\n")
        _, _, sem, diags = analyze("`1` = 2\nfale `1` == 2\n")
        self.assertFalse(diags); self.assertEqual(sem._lookup("1").stable_type, "Inteiro")

    def test_type_stability_and_sv(self):
        _, _, sem, diags = analyze("x = SV\nx = 1\nx = SV\nx = 2\n")
        self.assertFalse(diags); self.assertEqual(sem._lookup("x").stable_type, "Inteiro")
        *_, diags = analyze("x = 1\nx = 1.0\n")
        self.assertTrue(any(d.code == "NFS-E330" for d in diags))

    def test_class_function_semantics(self):
        source = '''class Base\n    fun inic(x)\n        esse.x = x\n\nclass Filha herda Base\n    fun inic(x)\n        sup.inic(x)\n'''
        *_, diags = analyze(source); self.assertFalse(diags)


class PipelineTests(unittest.TestCase):
    def run_stage(self, *args):
        p = subprocess.run([sys.executable, *map(str,args)], cwd=PYDIR, text=True, capture_output=True)
        if p.returncode != 0:
            self.fail(f"stage failed: {args}\nstdout={p.stdout}\nstderr={p.stderr}")
        return p

    def test_full_pipeline(self):
        source = ROOT / "src" / "neftys" / "pipeline_v1.nfs"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            char, tkn, ast, sem, sym, ir, opt, bc, dis = [td / n for n in ["a.char","a.tkn","a.ast","a.sem","a.sym","a.ir","a.opt.ir","a.bc","a.dis"]]
            self.run_stage(PYDIR/"1-conversor.py", source, "--o", char)
            self.run_stage(PYDIR/"2-lexer.py", char, "--o", tkn)
            self.run_stage(PYDIR/"3-parser.py", tkn, "--o", ast)
            self.run_stage(PYDIR/"4-symbol_table.py", ast, "--o", sym, "--sem", sem)
            self.run_stage(PYDIR/"5-ir.py", sem, "--o", ir)
            self.run_stage(PYDIR/"6-otimizador.py", ir, "--o", opt)
            self.run_stage(PYDIR/"7-codegen.py", opt, "--o", bc, "--dis", dis)
            vm = self.run_stage(PYDIR/"8-vm.py", bc)
            self.assertIn("objeto: 7", vm.stdout)
            self.assertIn("dobro: 8", vm.stdout)
            self.assertIn("Verdadeiro!", vm.stdout)
            self.assertTrue(char.exists() and tkn.exists() and ast.exists() and sem.exists() and ir.exists() and bc.exists())

    def test_concat_error_stops_semantic_stage(self):
        source = ROOT / "src" / "neftys" / "inteiro-mais-string-deve-retornar-erro.nfs"
        p = subprocess.run([sys.executable, str(PYDIR/"4-symbol_table.py"), str(source)], cwd=PYDIR, text=True, capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("CONCATENATION FAILED", p.stderr)


if __name__ == "__main__": unittest.main()
