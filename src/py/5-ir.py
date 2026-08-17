#!/usr/bin/env python3
"""
Visualizador de Representação Intermediária (IR) da Neftys.

Entrada atual:
    .ast -> IR textual de três endereços

A IR deliberadamente não conhece detalhes de x86, ARM ou de uma VM específica.
Ela apenas torna explícitas operações semânticas simples da linguagem.

Pontos de extensão futura:
    - chamadas de função;
    - saltos e labels;
    - blocos básicos / CFG;
    - comparações e booleanos;
    - estruturas, listas e objetos;
    - informações de tipo anexadas à IR.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any


@dataclass
class Node:
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)


_TREE_LINE = re.compile(
    r"^(?P<indent>(?:(?:│   )|(?:    ))*)"
    r"(?P<connector>├── |└── )?"
    r"(?P<body>.*)$"
)
_VALUE_NODES = {"Numero", "String", "Identificador"}


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_ast_file(filename: str | Path) -> Node:
    lines = Path(filename).read_text(encoding="utf-8").splitlines()
    root: Node | None = None
    stack: list[tuple[int, Node]] = []

    for raw in lines:
        if not raw.strip():
            continue
        match = _TREE_LINE.match(raw)
        if not match:
            raise ValueError(f"linha de AST não reconhecida: {raw!r}")

        indent = match.group("indent")
        connector = match.group("connector")
        body = match.group("body").strip()
        depth = len(indent) // 4 + (1 if connector else 0)

        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else None

        if ": " in body:
            key, value = body.split(": ", 1)
            key = key.strip()
            value = value.strip()
            if key in _VALUE_NODES:
                node = Node(key, {"value": _unquote(value)})
                if parent is None:
                    if root is not None:
                        raise ValueError("AST contém mais de uma raiz")
                    root = node
                else:
                    parent.children.append(node)
                stack.append((depth, node))
                continue

            if parent is None:
                raise ValueError(f"atributo sem nó pai: {body!r}")
            parent.attrs[key] = _unquote(value)
            continue

        node = Node(body)
        if parent is None:
            if root is not None:
                raise ValueError("AST contém mais de uma raiz")
            root = node
        else:
            parent.children.append(node)
        stack.append((depth, node))

    if root is None:
        raise ValueError("arquivo .ast vazio")
    return root


@dataclass
class Instruction:
    op: str
    args: list[str]

    def render(self) -> str:
        return " ".join([self.op, *self.args])


def encode_literal(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return json.dumps(value, ensure_ascii=False)


def parse_number(text: str) -> int | float:
    value = float(text)
    return int(value) if value.is_integer() else value


class IRBuilder:
    BINOPS = {
        "Soma": "ADD",
        "Subtracao": "SUB",
        "Multiplicacao": "MUL",
        "Divisao": "DIV",
    }

    def __init__(self) -> None:
        self.instructions: list[Instruction] = []
        self.temp_counter = 0

    def new_temp(self) -> str:
        temp = f"%{self.temp_counter}"
        self.temp_counter += 1
        return temp

    def emit(self, op: str, *args: str) -> None:
        self.instructions.append(Instruction(op, list(args)))

    def build(self, root: Node) -> list[Instruction]:
        if root.type != "Programa":
            raise ValueError(f"raiz esperada: Programa; recebida: {root.type}")
        for stmt in root.children:
            self.emit_statement(stmt)
        self.emit("HALT")
        return self.instructions

    # FUTURO: novas formas de statement entram aqui sem alterar expressões.
    def emit_statement(self, node: Node) -> None:
        if node.type == "DeclaracaoConstantes":
            for vinculo in node.children:
                if vinculo.type != "Vinculo":
                    continue
                name = vinculo.attrs.get("nome")
                if not name or not vinculo.children:
                    raise ValueError("vínculo de constante incompleto")
                value_temp = self.emit_expr(vinculo.children[0])
                self.emit("BIND_CONST", name, value_temp)
            return

        if node.type == "DeclaracaoVariavel":
            name = node.attrs.get("nome")
            if not name or not node.children:
                raise ValueError("declaração de variável incompleta")
            value_temp = self.emit_expr(node.children[0])
            self.emit("STORE", name, value_temp)
            return

        if node.type == "Falar":
            args = [self.emit_expr(child) for child in node.children]
            self.emit("PRINT", *args)
            return

        raise ValueError(f"statement ainda não suportado na IR: {node.type}")

    # FUTURO: novos literais, chamadas, indexação etc. entram aqui.
    def emit_expr(self, node: Node) -> str:
        if node.type == "Numero":
            temp = self.new_temp()
            value = parse_number(str(node.attrs.get("value")))
            self.emit("CONST", temp, encode_literal(value))
            return temp

        if node.type == "String":
            temp = self.new_temp()
            self.emit("CONST", temp, encode_literal(node.attrs.get("value", "")))
            return temp

        if node.type == "Identificador":
            temp = self.new_temp()
            name = node.attrs.get("value")
            if not name:
                raise ValueError("Identificador sem nome")
            self.emit("LOAD", temp, name)
            return temp

        if node.type in self.BINOPS:
            if len(node.children) != 2:
                raise ValueError(f"{node.type} deveria possuir dois operandos")
            left = self.emit_expr(node.children[0])
            right = self.emit_expr(node.children[1])
            result = self.new_temp()
            self.emit(self.BINOPS[node.type], result, left, right)
            return result

        raise ValueError(f"expressão ainda não suportada na IR: {node.type}")


def render_ir(instructions: list[Instruction]) -> str:
    lines = [
        "; Neftys IR v0",
        "; IR de três endereços, independente de arquitetura",
        "",
    ]
    lines.extend(instr.render() for instr in instructions)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Transforma uma AST da Neftys em IR visual.")
    parser.add_argument("arquivo", help="Arquivo .ast")
    parser.add_argument("--o", dest="saida", help="Saída .ir")
    args = parser.parse_args()

    try:
        tree = parse_ast_file(args.arquivo)
        text = render_ir(IRBuilder().build(tree))
    except (OSError, ValueError) as exc:
        print(f"Erro ao gerar IR: {exc}", file=sys.stderr)
        return 1

    if args.saida:
        Path(args.saida).write_text(text + "\n", encoding="utf-8")
        print(f"IR salva em '{args.saida}'")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
