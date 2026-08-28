from __future__ import annotations

import sys
from pathlib import Path
import unittest

SRC_PY = Path(__file__).parents[1] / "src" / "py"
sys.path.insert(0, str(SRC_PY))
import neftys_v1 as mod



def analyze(source: str):
    tokens = mod.Lexer(source).tokenize()
    tree = mod.Parser(tokens).parse()
    semantic = mod.SemanticAnalyzer(source)
    diagnostics = semantic.analyze(tree)
    return tokens, tree, semantic, diagnostics


class GrammarV1Tests(unittest.TestCase):
    def test_indent_dedent(self):
        tokens, *_ = analyze("se Ver então\n    fale \"x\"\nfale \"y\"\n")
        kinds = [t.kind for t in tokens]
        self.assertIn("INDENT", kinds)
        self.assertIn("DEDENT", kinds)

    def test_escaped_numeric_identifier(self):
        _, _, sem, diags = analyze("`1` = 2\nfale `1` == 2\n")
        self.assertFalse(diags)
        self.assertEqual(sem._lookup("1").stable_type, "Inteiro")

    def test_bare_numeric_assignment_is_rejected(self):
        with self.assertRaises(mod.NeftysError) as ctx:
            analyze("1 = 2\n")
        self.assertEqual(ctx.exception.diagnostic.code, "NFS-E204")

    def test_variable_type_is_stable(self):
        *_, diags = analyze("dois = 2\ndois = 3.14\n")
        self.assertTrue(any(d.code == "NFS-E330" for d in diags))

    def test_sv_does_not_lock_type(self):
        _, _, sem, diags = analyze("x = SV\nx = 10\nx = SV\nx = 20\n")
        self.assertFalse(diags)
        self.assertEqual(sem._lookup("x").stable_type, "Inteiro")

    def test_constant_can_shadow_outer_constant(self):
        _, _, sem, diags = analyze("UM = 1\nse Ver então\n    UM = 2\n")
        self.assertFalse(diags)
        found = [s for s in sem.history if s.name == "UM" and s.origin == "usuário"]
        self.assertEqual(len(found), 2)
        self.assertNotEqual(found[0].scope, found[1].scope)

    def test_constant_cannot_reassign_same_scope(self):
        *_, diags = analyze("UM = 1\nUM = 2\n")
        self.assertTrue(any(d.code == "NFS-E328" for d in diags))

    def test_concat_requires_two_strings(self):
        *_, diags = analyze('x = "a" + 1\n')
        self.assertTrue(any(d.code == "NFS-E339" for d in diags))

    def test_unary_plus_has_specific_error(self):
        with self.assertRaises(mod.NeftysError) as ctx:
            analyze('x = +"a"\n')
        self.assertEqual(ctx.exception.diagnostic.code, "NFS-E205")
        self.assertIn("CONCATENATION FAILED", ctx.exception.diagnostic.message)

    def test_unary_minus_string_errors(self):
        *_, diags = analyze('x = -"4"\n')
        self.assertTrue(any(d.code == "NFS-E336" for d in diags))

    def test_boolean_logic(self):
        _, tree, _, diags = analyze("x = !Ver ou (Ver e Fal)\n")
        self.assertFalse(diags)
        assignment = tree.fields["instruções"][0]
        self.assertEqual(assignment.attrs["tipo_valor"], "Booleano")

    def test_math_builtins_and_clock(self):
        _, tree, sem, diags = analyze("x = PI * 2\nt = relog()\n")
        self.assertFalse(diags)
        self.assertEqual(sem._lookup("x").stable_type, "Real")
        self.assertEqual(sem._lookup("t").stable_type, "Real")

    def test_semicolon_is_rejected(self):
        with self.assertRaises(mod.NeftysError) as ctx:
            mod.Lexer("x = 1;\n").tokenize()
        self.assertEqual(ctx.exception.diagnostic.code, "NFS-E103")

    def test_old_double_comparison_symbol_is_rejected(self):
        with self.assertRaises(mod.NeftysError) as ctx:
            mod.Lexer("x = 1 << 2\n").tokenize()
        self.assertEqual(ctx.exception.diagnostic.code, "NFS-E105")

    def test_class_inheritance_esse_sup(self):
        source = """\
class Base
    fun inic(x)
        esse.x = x

class Filha herda Base
    fun inic(x)
        sup.inic(x)
        esse.y = 2
"""
        *_, diags = analyze(source)
        self.assertFalse(diags)

    def test_return_outside_function(self):
        *_, diags = analyze("retorne 1\n")
        self.assertTrue(any(d.code == "NFS-E322" for d in diags))

    def test_init_cannot_return_value(self):
        source = """\
class X
    fun inic()
        retorne 1
"""
        *_, diags = analyze(source)
        self.assertTrue(any(d.code == "NFS-E323" for d in diags))

    def test_break_continue_need_loop(self):
        *_, diags = analyze("pare\ncontinue\n")
        codes = {d.code for d in diags}
        self.assertIn("NFS-E324", codes)
        self.assertIn("NFS-E325", codes)


if __name__ == "__main__":
    unittest.main()
