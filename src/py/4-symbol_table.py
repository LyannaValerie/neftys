#!/usr/bin/env python3
"""Etapa 4: AST -> vínculos, escopos, tipos estáveis e AST semântica."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from neftys_v1 import NeftysError, SemanticAnalyzer, build_tree_from_input, render_symbols, render_tree, save_tree


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 4/9: análise semântica visual.")
    cli.add_argument("arquivo", help=".nfs/.char/.tkn/.ast/.sem")
    cli.add_argument("--o", dest="saida", help="tabela textual .sym")
    cli.add_argument("--sem", dest="sem", help="AST anotada .sem para a etapa 5")
    cli.add_argument("--mostrar-ast", action="store_true")
    args = cli.parse_args()
    try:
        tree, source = build_tree_from_input(args.arquivo); source = source or ""
        analyzer = SemanticAnalyzer(source); diagnostics = analyzer.analyze(tree)
    except NeftysError as exc:
        print(exc.diagnostic.render(locals().get("source")), file=sys.stderr); return 1
    except (OSError, ValueError) as exc:
        print(f"NFS-E004\nAff... a análise semântica nem conseguiu abrir o material de trabalho: {exc}", file=sys.stderr); return 1
    table = render_symbols(analyzer.history)
    if args.saida: Path(args.saida).write_text(table + "\n", encoding="utf-8")
    else: print(table)
    if args.sem: save_tree(args.sem, tree, fmt="neftys-semantic", source=source)
    if args.mostrar_ast: print("\nAST semântica\n" + render_tree(tree))
    if diagnostics:
        for d in diagnostics: print("\n" + d.render(source), file=sys.stderr)
        return 1
    print("Análise semântica: sem diagnósticos.", file=sys.stderr); return 0
if __name__ == "__main__": raise SystemExit(main())
