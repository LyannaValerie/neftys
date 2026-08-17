#!/usr/bin/env python3
"""
Máquina Virtual didática da Neftys.

Lê o bytecode de 7-codegen.py e simula:
  - pilha de operandos;
  - temporários;
  - contador de instrução (IP);
  - operações aritméticas;
  - nomes via runtime;
  - PRINT e HALT.

Use --trace para observar cada instrução.

Pontos de extensão futura:
  - saltos e controle de fluxo;
  - call stack e funções;
  - exceções;
  - instruções especializadas;
  - JIT/AOT alternativo.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import struct
import sys
from typing import Any


MAGIC = b"NFTY"
VERSION = 1

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


def load_runtime_module():
    path = Path(__file__).resolve().with_name("9-runtime.py")
    if not path.exists():
        raise FileNotFoundError(f"runtime não encontrado: {path}")
    spec = importlib.util.spec_from_file_location("neftys_runtime_visual", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, size: int) -> bytes:
        end = self.pos + size
        if end > len(self.data):
            raise ValueError("bytecode truncado")
        chunk = self.data[self.pos:end]
        self.pos = end
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

    def f64(self) -> float:
        return struct.unpack(">d", self.take(8))[0]


def read_bundle(filename: str | Path):
    reader = Reader(Path(filename).read_bytes())
    if reader.take(4) != MAGIC:
        raise ValueError("arquivo não é bytecode Neftys")
    version = reader.u8()
    if version != VERSION:
        raise ValueError(f"versão de bytecode não suportada: {version}")

    constants = []
    for _ in range(reader.u16()):
        tag = reader.u8()
        if tag == 1:
            constants.append(reader.f64())
        elif tag == 2:
            size = reader.u32()
            constants.append(reader.take(size).decode("utf-8"))
        else:
            raise ValueError(f"tag de constante desconhecida: {tag}")

    names = []
    for _ in range(reader.u16()):
        size = reader.u16()
        names.append(reader.take(size).decode("utf-8"))

    temp_count = reader.u16()
    code_size = reader.u32()
    code = reader.take(code_size)
    if reader.pos != len(reader.data):
        raise ValueError("bytes extras após o bundle")
    return constants, names, temp_count, code


class VM:
    def __init__(self, constants, names, temp_count, code, runtime, trace=False):
        self.constants = constants
        self.names = names
        self.temps: list[Any] = [None] * temp_count
        self.stack: list[Any] = []
        self.code = code
        self.ip = 0
        self.runtime = runtime
        self.trace = trace

    def read_u8(self) -> int:
        if self.ip >= len(self.code):
            raise ValueError("fim inesperado do bytecode")
        value = self.code[self.ip]
        self.ip += 1
        return value

    def read_u16(self) -> int:
        if self.ip + 2 > len(self.code):
            raise ValueError("fim inesperado do bytecode")
        value = struct.unpack(">H", self.code[self.ip:self.ip + 2])[0]
        self.ip += 2
        return value

    def trace_state(self, offset: int, instruction: str) -> None:
        if self.trace:
            print(
                f"{offset:04X}  {instruction:<24} "
                f"pilha={self.stack!r} ambiente={self.runtime.snapshot()}"
            )

    def run(self) -> None:
        while self.ip < len(self.code):
            offset = self.ip
            opcode = self.read_u8()

            if opcode == OP_PUSH_CONST:
                idx = self.read_u16()
                self.stack.append(self.constants[idx])
                self.trace_state(offset, f"PUSH_CONST {idx}")
                continue

            if opcode == OP_LOAD_NAME:
                idx = self.read_u16()
                self.stack.append(self.runtime.load_name(self.names[idx]))
                self.trace_state(offset, f"LOAD_NAME {self.names[idx]}")
                continue

            if opcode == OP_DEFINE_CONST:
                idx = self.read_u16()
                self.runtime.define_const(self.names[idx], self.stack.pop())
                self.trace_state(offset, f"DEFINE_CONST {self.names[idx]}")
                continue

            if opcode == OP_STORE_NAME:
                idx = self.read_u16()
                self.runtime.store_name(self.names[idx], self.stack.pop())
                self.trace_state(offset, f"STORE_NAME {self.names[idx]}")
                continue

            if opcode == OP_LOAD_TEMP:
                idx = self.read_u16()
                self.stack.append(self.temps[idx])
                self.trace_state(offset, f"LOAD_TEMP %{idx}")
                continue

            if opcode == OP_STORE_TEMP:
                idx = self.read_u16()
                self.temps[idx] = self.stack.pop()
                self.trace_state(offset, f"STORE_TEMP %{idx}")
                continue

            if opcode in (OP_ADD, OP_SUB, OP_MUL, OP_DIV):
                right = self.stack.pop()
                left = self.stack.pop()
                if opcode == OP_ADD:
                    result, name = left + right, "ADD"
                elif opcode == OP_SUB:
                    result, name = left - right, "SUB"
                elif opcode == OP_MUL:
                    result, name = left * right, "MUL"
                else:
                    if right == 0:
                        raise ZeroDivisionError("divisão por zero")
                    result, name = left / right, "DIV"
                self.stack.append(result)
                self.trace_state(offset, name)
                continue

            if opcode == OP_PRINT:
                argc = self.read_u8()
                if argc > len(self.stack):
                    raise ValueError("pilha insuficiente para PRINT")
                values = self.stack[-argc:] if argc else []
                if argc:
                    del self.stack[-argc:]
                self.trace_state(offset, f"PRINT {argc}")
                self.runtime.falar(values)
                continue

            if opcode == OP_HALT:
                self.trace_state(offset, "HALT")
                return

            raise ValueError(f"opcode desconhecido 0x{opcode:02X} em 0x{offset:04X}")

        raise ValueError("bytecode terminou sem HALT")


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa bytecode da VM didática da Neftys.")
    parser.add_argument("arquivo", help="Arquivo .bc")
    parser.add_argument("--trace", action="store_true", help="Mostra instrução por instrução")
    args = parser.parse_args()

    try:
        runtime_module = load_runtime_module()
        constants, names, temp_count, code = read_bundle(args.arquivo)
        runtime = runtime_module.NeftysRuntime()
        VM(constants, names, temp_count, code, runtime, trace=args.trace).run()
    except (OSError, ValueError, ImportError, IndexError, ZeroDivisionError, RuntimeError) as exc:
        print(f"Erro de runtime/VM: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
