#!/usr/bin/env python3
"""Etapa 6: otimizações demonstrativas preservando a IR Neftys v1."""
from __future__ import annotations
import argparse
import json
import sys
from neftys_v1 import load_ir, optimize_ir, save_ir


def main() -> int:
    cli = argparse.ArgumentParser(description="Neftys 6/9: otimização de IR.")
    cli.add_argument("arquivo"); cli.add_argument("--o", dest="saida"); cli.add_argument("--trace", action="store_true")
    args = cli.parse_args()
    try: optimized, events = optimize_ir(load_ir(args.arquivo))
    except (OSError, ValueError) as exc:
        print(f"NFS-E006\nAff... não dá para otimizar o que nem é uma IR válida: {exc}", file=sys.stderr); return 1
    if args.trace:
        print("Otimizações:")
        for event in events: print(f"  - {event}")
        if not events: print("  - nenhuma aplicável")
    if args.saida: save_ir(args.saida, optimized); print(f"IR otimizada salva em '{args.saida}'.")
    else: print(json.dumps(optimized, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
