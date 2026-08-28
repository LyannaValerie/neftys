#!/usr/bin/env python3
"""Etapa 5: AST/semântica -> IR estrutural independente da VM."""
from __future__ import annotations
import argparse
import json
import sys
from neftys_v1 import build_ir, build_tree_from_input, save_ir


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 5/9: AST semântica -> IR.")
    cli.add_argument("arquivo", help="preferencialmente .sem; aceita .ast/.nfs para inspeção")
    cli.add_argument("--o", dest="saida", help="saída .ir")
    args = cli.parse_args()
    try: tree, _ = build_tree_from_input(args.arquivo); ir = build_ir(tree)
    except (OSError, ValueError) as exc:
        print(f"NFS-E005\nAff... a IR não nasce de material incompreensível: {exc}", file=sys.stderr); return 1
    if args.saida: save_ir(args.saida, ir); print(f"IR salva em '{args.saida}'.")
    else: print(json.dumps(ir, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
