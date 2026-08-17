#!/usr/bin/env python3
"""
Otimizador visual da IR da Neftys.

Demonstra apenas duas ideias do mapa do livro:
  1. propagação de constantes declaradas com BIND_CONST;
  2. constant folding de ADD/SUB/MUL/DIV quando os operandos são conhecidos.

A saída continua sendo a mesma IR.

Pontos de extensão futura:
  - dead code elimination;
  - common subexpression elimination;
  - strength reduction;
  - análise de fluxo / blocos básicos;
  - otimizações específicas de alvo.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import sys
from typing import Any


@dataclass
class Instruction:
    op: str
    args: list[str]

    def render(self) -> str:
        return " ".join([self.op, *self.args])


def parse_ir(filename: str | Path) -> list[Instruction]:
    instructions = []
    for raw in Path(filename).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        parts = shlex.split(line, posix=True)
        instructions.append(Instruction(parts[0], parts[1:]))
    return instructions


def decode_literal(token: str) -> Any:
    try:
        return json.loads(token)
    except (json.JSONDecodeError, TypeError):
        return token


def encode_literal(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return json.dumps(value, ensure_ascii=False)


class Optimizer:
    BINOPS = {"ADD", "SUB", "MUL", "DIV"}

    def __init__(self) -> None:
        self.temp_constants: dict[str, Any] = {}
        self.named_constants: dict[str, Any] = {}
        self.events: list[str] = []

    def optimize(self, instructions: list[Instruction]) -> list[Instruction]:
        out: list[Instruction] = []

        for instr in instructions:
            op, args = instr.op, instr.args

            if op == "CONST":
                dest, literal = args
                value = decode_literal(literal)
                self.temp_constants[dest] = value
                out.append(Instruction("CONST", [dest, encode_literal(value)]))
                continue

            if op == "BIND_CONST":
                name, src = args
                if src in self.temp_constants:
                    self.named_constants[name] = self.temp_constants[src]
                out.append(instr)
                continue

            if op == "LOAD":
                dest, name = args
                if name in self.named_constants:
                    value = self.named_constants[name]
                    self.temp_constants[dest] = value
                    replacement = Instruction("CONST", [dest, encode_literal(value)])
                    self.events.append(
                        f"propagação: {instr.render()} -> {replacement.render()}"
                    )
                    out.append(replacement)
                else:
                    self.temp_constants.pop(dest, None)
                    out.append(instr)
                continue

            if op in self.BINOPS:
                dest, left, right = args
                if left in self.temp_constants and right in self.temp_constants:
                    try:
                        value = self._fold(
                            op,
                            self.temp_constants[left],
                            self.temp_constants[right],
                        )
                    except (TypeError, ZeroDivisionError):
                        self.temp_constants.pop(dest, None)
                        out.append(instr)
                        continue

                    self.temp_constants[dest] = value
                    replacement = Instruction("CONST", [dest, encode_literal(value)])
                    self.events.append(
                        f"constant folding: {instr.render()} -> {replacement.render()}"
                    )
                    out.append(replacement)
                else:
                    self.temp_constants.pop(dest, None)
                    out.append(instr)
                continue

            # STORE é tratado como mutável em princípio. Não fazemos propagação
            # por variáveis, mesmo que a sintaxe atual ainda seja mínima.
            out.append(instr)

        return out

    @staticmethod
    def _fold(op: str, a: Any, b: Any) -> Any:
        if op == "ADD":
            return a + b
        if op == "SUB":
            return a - b
        if op == "MUL":
            return a * b
        if op == "DIV":
            return a / b
        raise ValueError(op)


def render_ir(instructions: list[Instruction], events: list[str]) -> str:
    lines = [
        "; Neftys IR v0 - otimizada",
        "; mesma semântica, forma interna simplificada",
    ]
    if events:
        lines.append(";")
        lines.extend(f"; {event}" for event in events)
    lines.append("")
    lines.extend(instr.render() for instr in instructions)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplica otimizações didáticas à IR.")
    parser.add_argument("arquivo", help="Arquivo .ir")
    parser.add_argument("--o", dest="saida", help="Saída .ir otimizada")
    parser.add_argument("--trace", action="store_true", help="Mostra as otimizações aplicadas")
    args = parser.parse_args()

    try:
        instructions = parse_ir(args.arquivo)
        optimizer = Optimizer()
        text = render_ir(optimizer.optimize(instructions), optimizer.events)
    except (OSError, ValueError) as exc:
        print(f"Erro na otimização: {exc}", file=sys.stderr)
        return 1

    if args.trace:
        if optimizer.events:
            print("Otimizações aplicadas:")
            for event in optimizer.events:
                print(f"  - {event}")
        else:
            print("Nenhuma otimização aplicável.")

    if args.saida:
        Path(args.saida).write_text(text + "\n", encoding="utf-8")
        print(f"IR otimizada salva em '{args.saida}'")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
