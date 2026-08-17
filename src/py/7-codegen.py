#!/usr/bin/env python3
"""
Gerador de bytecode visual da Neftys.

Entrada:
    IR textual

Saídas:
    .bc  -> bytecode BINÁRIO de uma VM hipotética
    .dis -> desmontagem legível opcional

A IR ainda é independente de alvo. Aqui escolhemos uma ISA concreta: a pequena
VM Neftys. É o momento em que o back-end transforma operações abstratas em
instruções de uma máquina específica.

Pontos de extensão futura:
    - saltos / labels;
    - chamadas e retorno;
    - frames de função;
    - comparações;
    - targets alternativos.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import struct
import sys
from typing import Any


MAGIC = b"NFTY"
VERSION = 1

# =============================================================================
# ISA DA VM
# =============================================================================

OP_PUSH_CONST   = 0x01
OP_LOAD_NAME    = 0x02
OP_DEFINE_CONST = 0x03
OP_STORE_NAME   = 0x04
OP_LOAD_TEMP    = 0x05
OP_STORE_TEMP   = 0x06
OP_ADD          = 0x10
OP_SUB          = 0x11
OP_MUL          = 0x12
OP_DIV          = 0x13
OP_PRINT        = 0x20
OP_HALT         = 0xFF

OP_NAMES = {
    OP_PUSH_CONST: "PUSH_CONST",
    OP_LOAD_NAME: "LOAD_NAME",
    OP_DEFINE_CONST: "DEFINE_CONST",
    OP_STORE_NAME: "STORE_NAME",
    OP_LOAD_TEMP: "LOAD_TEMP",
    OP_STORE_TEMP: "STORE_TEMP",
    OP_ADD: "ADD",
    OP_SUB: "SUB",
    OP_MUL: "MUL",
    OP_DIV: "DIV",
    OP_PRINT: "PRINT",
    OP_HALT: "HALT",
}


@dataclass
class IRInstruction:
    op: str
    args: list[str]


def parse_ir(filename: str | Path) -> list[IRInstruction]:
    instructions = []
    for raw in Path(filename).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        parts = shlex.split(line, posix=True)
        instructions.append(IRInstruction(parts[0], parts[1:]))
    return instructions


def decode_literal(token: str) -> Any:
    try:
        return json.loads(token)
    except (json.JSONDecodeError, TypeError):
        return token


class Pool:
    def __init__(self) -> None:
        self.items: list[Any] = []
        self.index: dict[tuple, int] = {}

    @staticmethod
    def _key(value: Any) -> tuple:
        return (type(value).__name__, value)

    def add(self, value: Any) -> int:
        key = self._key(value)
        if key in self.index:
            return self.index[key]
        idx = len(self.items)
        if idx > 0xFFFF:
            raise ValueError("pool excedeu 65535 entradas")
        self.items.append(value)
        self.index[key] = idx
        return idx


class CodeGenerator:
    def __init__(self) -> None:
        self.constants = Pool()
        self.names = Pool()
        self.code = bytearray()
        self.max_temp = -1
        self.disassembly: list[tuple[int, str]] = []

    @staticmethod
    def _u16(value: int) -> bytes:
        return struct.pack(">H", value)

    def _emit(self, opcode: int, operands: bytes = b"", note: str = "") -> None:
        offset = len(self.code)
        self.code.append(opcode)
        self.code.extend(operands)
        text = OP_NAMES[opcode] + (f" {note}" if note else "")
        self.disassembly.append((offset, text))

    def _temp_index(self, temp: str) -> int:
        if not temp.startswith("%"):
            raise ValueError(f"temporário inválido: {temp}")
        idx = int(temp[1:])
        if not 0 <= idx <= 0xFFFF:
            raise ValueError(f"temporário fora da faixa: {temp}")
        self.max_temp = max(self.max_temp, idx)
        return idx

    def _load_temp(self, temp: str) -> None:
        idx = self._temp_index(temp)
        self._emit(OP_LOAD_TEMP, self._u16(idx), f"%{idx}")

    def _store_temp(self, temp: str) -> None:
        idx = self._temp_index(temp)
        self._emit(OP_STORE_TEMP, self._u16(idx), f"%{idx}")

    def generate(self, ir: list[IRInstruction]) -> bytes:
        for instr in ir:
            op, args = instr.op, instr.args

            if op == "CONST":
                dest, literal = args
                value = decode_literal(literal)
                cidx = self.constants.add(value)
                self._emit(OP_PUSH_CONST, self._u16(cidx), f"{cidx} ; {value!r}")
                self._store_temp(dest)
                continue

            if op == "LOAD":
                dest, name = args
                nidx = self.names.add(name)
                self._emit(OP_LOAD_NAME, self._u16(nidx), f"{nidx} ; {name}")
                self._store_temp(dest)
                continue

            if op == "BIND_CONST":
                name, src = args
                self._load_temp(src)
                nidx = self.names.add(name)
                self._emit(OP_DEFINE_CONST, self._u16(nidx), f"{nidx} ; {name}")
                continue

            if op == "STORE":
                name, src = args
                self._load_temp(src)
                nidx = self.names.add(name)
                self._emit(OP_STORE_NAME, self._u16(nidx), f"{nidx} ; {name}")
                continue

            if op in {"ADD", "SUB", "MUL", "DIV"}:
                dest, left, right = args
                self._load_temp(left)
                self._load_temp(right)
                opcode = {"ADD": OP_ADD, "SUB": OP_SUB, "MUL": OP_MUL, "DIV": OP_DIV}[op]
                self._emit(opcode)
                self._store_temp(dest)
                continue

            if op == "PRINT":
                for temp in args:
                    self._load_temp(temp)
                argc = len(args)
                if argc > 255:
                    raise ValueError("PRINT suporta no máximo 255 argumentos")
                self._emit(OP_PRINT, bytes([argc]), str(argc))
                continue

            if op == "HALT":
                self._emit(OP_HALT)
                continue

            raise ValueError(f"instrução IR ainda não suportada: {op}")

        return self._build_binary()

    def _build_binary(self) -> bytes:
        data = bytearray(MAGIC)
        data.append(VERSION)

        data.extend(struct.pack(">H", len(self.constants.items)))
        for value in self.constants.items:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                data.append(1)
                data.extend(struct.pack(">d", float(value)))
            elif isinstance(value, str):
                encoded = value.encode("utf-8")
                data.append(2)
                data.extend(struct.pack(">I", len(encoded)))
                data.extend(encoded)
            else:
                raise ValueError(f"literal não representável em bytecode: {value!r}")

        data.extend(struct.pack(">H", len(self.names.items)))
        for name in self.names.items:
            encoded = str(name).encode("utf-8")
            data.extend(struct.pack(">H", len(encoded)))
            data.extend(encoded)

        data.extend(struct.pack(">H", self.max_temp + 1))
        data.extend(struct.pack(">I", len(self.code)))
        data.extend(self.code)
        return bytes(data)

    def render_disassembly(self) -> str:
        lines = ["Neftys Bytecode v1", "=" * 72, "", "Pool de constantes:"]
        for idx, value in enumerate(self.constants.items):
            lines.append(f"  [{idx:03}] {value!r}")
        lines.extend(["", "Pool de nomes:"])
        for idx, name in enumerate(self.names.items):
            lines.append(f"  [{idx:03}] {name}")
        lines.extend(["", f"Temporários: {self.max_temp + 1}", "", "Código:"])
        for offset, text in self.disassembly:
            lines.append(f"  {offset:04X}  {text}")
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Traduz IR da Neftys para bytecode da VM.")
    parser.add_argument("arquivo", help="Arquivo .ir")
    parser.add_argument("--o", dest="saida", required=True, help="Saída .bc")
    parser.add_argument("--dis", metavar="ARQUIVO", help="Salva a desmontagem textual")
    args = parser.parse_args()

    try:
        ir = parse_ir(args.arquivo)
        generator = CodeGenerator()
        bytecode = generator.generate(ir)
        dis = generator.render_disassembly()
    except (OSError, ValueError) as exc:
        print(f"Erro na geração de código: {exc}", file=sys.stderr)
        return 1

    Path(args.saida).write_bytes(bytecode)
    print(f"Bytecode salvo em '{args.saida}' ({len(bytecode)} bytes)")
    if args.dis:
        Path(args.dis).write_text(dis + "\n", encoding="utf-8")
        print(f"Desmontagem salva em '{args.dis}'")
    else:
        print("\n" + dis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
