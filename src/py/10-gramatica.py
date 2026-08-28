#!/usr/bin/env python3
"""Inspetor agregado da gramática v1. Não é uma etapa paralela ao pipeline 1–9."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from neftys_v1 import Lexer, NeftysError, Parser, SemanticAnalyzer, render_symbols, render_tree


def main() -> int:
    cli = argparse.ArgumentParser(description="Inspeciona tokens, AST e semântica da mesma gramática usada pelo pipeline 1–9.")
    cli.add_argument("arquivo"); args = cli.parse_args(); source = Path(args.arquivo).read_text(encoding="utf-8")
    try: tokens = Lexer(source).tokenize(); tree = Parser(tokens).parse()
    except NeftysError as exc: print(exc.diagnostic.render(source), file=sys.stderr); return 1
    sem = SemanticAnalyzer(source); diags = sem.analyze(tree)
    print("TOKENS\n" + "="*72); [print(t.short()) for t in tokens]
    print("\nAST\n" + "="*72 + "\n" + render_tree(tree)); print("\n" + render_symbols(sem.history))
    for d in diags: print("\n" + d.render(source), file=sys.stderr)
    return 1 if diags else 0
if __name__ == "__main__": raise SystemExit(main())
