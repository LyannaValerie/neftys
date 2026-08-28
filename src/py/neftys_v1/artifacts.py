from __future__ import annotations

import ast as pyast
import json
from pathlib import Path
from typing import Any

from .ast import Node
from .lexer import Token, Lexer
from .parser import Parser


def load_source(path: str | Path) -> str:
    p = Path(path)
    if p.suffix == ".nfs":
        return p.read_text(encoding="utf-8")
    if p.suffix in {".char", ".o"}:
        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = pyast.literal_eval(raw)
        if isinstance(data, dict):
            data = data.get("characters")
        if not isinstance(data, list) or not all(isinstance(c, str) and len(c) == 1 for c in data):
            raise ValueError("artefato de caracteres inválido")
        return "".join(data)
    raise ValueError(f"entrada fonte não suportada: {p.suffix}")


def save_char(path: str | Path, source: str) -> None:
    payload = {"format": "neftys-char", "version": 1, "characters": list(source)}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def token_to_data(t: Token) -> dict[str, Any]:
    return {"kind": t.kind, "lexeme": t.lexeme, "value": t.value, "line": t.line, "column": t.column, "escaped": t.escaped}


def token_from_data(d: dict[str, Any]) -> Token:
    return Token(d["kind"], d.get("lexeme", ""), d.get("value"), int(d["line"]), int(d["column"]), bool(d.get("escaped", False)))


def save_tokens(path: str | Path, tokens: list[Token]) -> None:
    payload = {"format": "neftys-tokens", "version": 1, "tokens": [token_to_data(t) for t in tokens]}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_tokens(path: str | Path) -> list[Token]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != "neftys-tokens": raise ValueError("arquivo não é um artefato de tokens Neftys")
    return [token_from_data(item) for item in data["tokens"]]


def node_to_data(node: Node) -> dict[str, Any]:
    def conv(value: Any) -> Any:
        if isinstance(value, Node): return node_to_data(value)
        if isinstance(value, list): return [conv(x) for x in value]
        return value
    return {
        "kind": node.kind,
        "fields": {k: conv(v) for k, v in node.fields.items()},
        "token": token_to_data(node.token) if node.token else None,
        "attrs": dict(node.attrs),
    }


def node_from_data(data: dict[str, Any]) -> Node:
    def conv(value: Any) -> Any:
        if isinstance(value, dict) and "kind" in value and "fields" in value: return node_from_data(value)
        if isinstance(value, list): return [conv(x) for x in value]
        return value
    tok = token_from_data(data["token"]) if data.get("token") else None
    return Node(data["kind"], {k: conv(v) for k, v in data.get("fields", {}).items()}, tok, dict(data.get("attrs", {})))


def save_tree(path: str | Path, tree: Node, *, fmt: str = "neftys-ast", source: str | None = None) -> None:
    payload: dict[str, Any] = {"format": fmt, "version": 1, "tree": node_to_data(tree)}
    if source is not None: payload["source"] = source
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_tree(path: str | Path) -> tuple[Node, str | None, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fmt = data.get("format")
    if fmt not in {"neftys-ast", "neftys-semantic"}: raise ValueError("arquivo não é AST/semântica Neftys")
    return node_from_data(data["tree"]), data.get("source"), fmt


def build_tree_from_input(path: str | Path) -> tuple[Node, str | None]:
    p = Path(path)
    if p.suffix in {".nfs", ".char", ".o"}:
        source = load_source(p); return Parser(Lexer(source).tokenize()).parse(), source
    if p.suffix == ".tkn":
        return Parser(load_tokens(p)).parse(), None
    if p.suffix in {".ast", ".sem"}:
        tree, source, _ = load_tree(p); return tree, source
    raise ValueError(f"entrada não suportada: {p.suffix}")
