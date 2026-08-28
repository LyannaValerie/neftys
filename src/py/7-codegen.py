#!/usr/bin/env python3
"""Etapa 7: IR -> bytecode binário da VM demonstrativa Neftys v1."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from neftys_v1 import load_ir
from neftys_v1.bytecode import compile_ir, disassemble, save_bundle


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 7/9: IR -> bytecode.")
    cli.add_argument("arquivo"); cli.add_argument("--o", dest="saida", required=True); cli.add_argument("--dis", help="desmontagem textual")
    args = cli.parse_args()
    try:
        bc = compile_ir(load_ir(args.arquivo)); save_bundle(args.saida, bc)
        if args.dis: Path(args.dis).write_text(disassemble(bc) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"NFS-E007\nAff... o gerador de código recebeu uma IR que não consegue traduzir: {exc}", file=sys.stderr); return 1
    print(f"Bytecode salvo em '{args.saida}'."); return 0
if __name__ == "__main__": raise SystemExit(main())
