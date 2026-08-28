#!/usr/bin/env python3
"""Etapa 1: preserva exatamente os caracteres do fonte Neftys em um artefato .char."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from neftys_v1 import save_char


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 1/9: fonte -> fluxo observável de caracteres.")
    cli.add_argument("arquivo", help="arquivo .nfs")
    cli.add_argument("--o", dest="saida", help="saída .char")
    cli.add_argument("--estatisticas", action="store_true")
    args = cli.parse_args(); p = Path(args.arquivo)
    try: source = p.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"NFS-E001\nAff... nem consegui ler '{p}': {exc}", file=sys.stderr); return 1
    if args.saida: save_char(args.saida, source); print(f"Caracteres salvos em '{args.saida}'.")
    else: print(repr(list(source)))
    if args.estatisticas:
        print(f"Total: {len(source)}")
        print(f"Espaços: {source.count(' ')}")
        print(f"Quebras de linha: {source.count(chr(10))}")
        print(f"Tabulações: {source.count(chr(9))}")
        print("Nota: espaços iniciais são semânticos na Neftys v1; esta etapa não normaliza indentação.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
