#!/usr/bin/env python3
"""Fronteira visual da gramática Neftys v1. Python observa; Pinker implementará."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from neftys_v1 import Lexer, NeftysError, Parser, SemanticAnalyzer, render_symbols, render_tree

def main() -> int:
    cli = argparse.ArgumentParser(description="Visualiza a gramática Neftys v1 sem fingir que Python é a mãe dela.")
    cli.add_argument("arquivo", help="arquivo .nfs")
    cli.add_argument("--tokens", action="store_true", help="mostra tokens")
    cli.add_argument("--ast", action="store_true", help="mostra AST")
    cli.add_argument("--simbolos", action="store_true", help="mostra tabela de símbolos")
    args = cli.parse_args()

    path = Path(args.arquivo)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"NFS-E001\nAff... nem consegui ler '{path}': {exc}", file=sys.stderr)
        return 1

    show_all = not (args.tokens or args.ast or args.simbolos)

    try:
        tokens = Lexer(source).tokenize()
        tree = Parser(tokens).parse()
    except NeftysError as exc:
        print(exc.diagnostic.render(source), file=sys.stderr)
        return 1
    except Exception as exc:  # erro interno não deve culpar o programa do usuário
        print("NFS-I900\nTá. Essa fui eu. O experimento tropeçou sozinho.", file=sys.stderr)
        print(f"Detalhe interno: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    analyzer = SemanticAnalyzer(source)
    diagnostics = analyzer.analyze(tree)

    if show_all or args.tokens:
        print("TOKENS")
        print("=" * 72)
        for token in tokens:
            print(token.short())
        print()

    if show_all or args.ast:
        print("AST")
        print("=" * 72)
        print(render_tree(tree))
        print()

    if show_all or args.simbolos:
        print(render_symbols(analyzer.history))
        print()

    if diagnostics:
        for index, diagnostic in enumerate(diagnostics):
            if index:
                print(file=sys.stderr)
            print(diagnostic.render(source), file=sys.stderr)
        return 1

    print("Análise semântica: sem diagnósticos.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
