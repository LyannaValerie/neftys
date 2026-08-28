#!/usr/bin/env python3
"""Etapa 3: tokens -> AST Neftys v1 serializada e árvore visual."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from neftys_v1 import Lexer, NeftysError, Parser, load_source, load_tokens, render_tree, save_tree


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 3/9: tokens -> AST.")
    cli.add_argument("arquivo", help=".tkn, .nfs, .char ou .o")
    cli.add_argument("--o", dest="saida", help="saída .ast")
    cli.add_argument("--arvore", action="store_true", help="mostra a árvore legível")
    args = cli.parse_args(); p = Path(args.arquivo); source = None
    try:
        if p.suffix == ".tkn": tokens = load_tokens(p)
        else: source = load_source(p); tokens = Lexer(source).tokenize()
        tree = Parser(tokens).parse()
    except NeftysError as exc:
        print(exc.diagnostic.render(source), file=sys.stderr); return 1
    except (OSError, ValueError) as exc:
        print(f"NFS-E003\nAff... o parser recebeu um artefato torto: {exc}", file=sys.stderr); return 1
    if args.saida: save_tree(args.saida, tree, fmt="neftys-ast", source=source); print(f"AST salva em '{args.saida}'.")
    if args.arvore or not args.saida: print(render_tree(tree))
    return 0
if __name__ == "__main__": raise SystemExit(main())
