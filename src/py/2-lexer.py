#!/usr/bin/env python3
"""Etapa 2: caracteres -> tokens, incluindo NEWLINE/INDENT/DEDENT."""
from __future__ import annotations
import argparse
import sys
from neftys_v1 import Lexer, NeftysError, load_source, save_tokens


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 2/9: fluxo de caracteres -> tokens.")
    cli.add_argument("arquivo", help=".nfs, .char ou .o")
    cli.add_argument("--o", dest="saida", help="saída .tkn")
    args = cli.parse_args()
    try:
        source = load_source(args.arquivo); tokens = Lexer(source).tokenize()
    except NeftysError as exc:
        print(exc.diagnostic.render(locals().get("source")), file=sys.stderr); return 1
    except (OSError, ValueError) as exc:
        print(f"NFS-E002\nAff... essa entrada nem chegou inteira ao lexer: {exc}", file=sys.stderr); return 1
    if args.saida: save_tokens(args.saida, tokens); print(f"Tokens salvos em '{args.saida}'.")
    else:
        for t in tokens: print(t.short())
    return 0
if __name__ == "__main__": raise SystemExit(main())
