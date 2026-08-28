from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

MAGIC = b"NFTYV1\0"

STMT_CODES = {"assign":1,"print":2,"expr":3,"if":4,"while":5,"for":6,"function":7,"class":8,"return":9,"break":10,"continue":11}
EXPR_CODES = {"literal":101,"name":102,"this":103,"super":104,"unary":105,"binary":106,"field":107,"call":108}


def compile_expr(e: dict[str, Any]) -> dict[str, Any]:
    kind = e["kind"]; out = {"tag": EXPR_CODES[kind]}
    if kind == "literal": out.update(type=e["type"], value=e.get("value"))
    elif kind == "name": out["name"] = e["name"]
    elif kind in {"this","super"}: pass
    elif kind == "unary": out.update(op=e["op"], value=compile_expr(e["value"]))
    elif kind == "binary": out.update(op=e["op"], left=compile_expr(e["left"]), right=compile_expr(e["right"]))
    elif kind == "field": out.update(object=compile_expr(e["object"]), name=e["name"])
    elif kind == "call": out.update(callee=compile_expr(e["callee"]), args=[compile_expr(a) for a in e["args"]])
    return out


def compile_stmt(s: dict[str, Any]) -> dict[str, Any]:
    op = s["op"]; out = {"op": STMT_CODES[op]}
    if op == "assign": out.update(target=compile_expr(s["target"]), value=compile_expr(s["value"]))
    elif op == "print": out["args"] = [compile_expr(a) for a in s["args"]]
    elif op == "expr": out["value"] = compile_expr(s["value"])
    elif op == "if": out.update(branches=[{"condition":compile_expr(b["condition"]),"body":[compile_stmt(x) for x in b["body"]]} for b in s["branches"]], else_body=None if s["else"] is None else [compile_stmt(x) for x in s["else"]])
    elif op == "while": out.update(condition=compile_expr(s["condition"]), body=[compile_stmt(x) for x in s["body"]])
    elif op == "for": out.update(target=s["target"], iterable=compile_expr(s["iterable"]), body=[compile_stmt(x) for x in s["body"]])
    elif op == "function": out.update(name=s["name"], params=s["params"], body=[compile_stmt(x) for x in s["body"]])
    elif op == "class": out.update(name=s["name"], superclass=None if s["superclass"] is None else compile_expr(s["superclass"]), body=[compile_stmt(x) for x in s["body"]])
    elif op == "return": out["value"] = None if s["value"] is None else compile_expr(s["value"])
    return out


def compile_ir(ir: dict[str, Any]) -> dict[str, Any]:
    return {"format":"neftys-bytecode","version":1,"code":[compile_stmt(s) for s in ir["instructions"]]}


def encode_bundle(bytecode: dict[str, Any]) -> bytes:
    payload = json.dumps(bytecode, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return MAGIC + struct.pack(">I", len(payload)) + payload


def decode_bundle(data: bytes) -> dict[str, Any]:
    if not data.startswith(MAGIC): raise ValueError("arquivo não é bytecode Neftys v1")
    pos = len(MAGIC)
    if len(data) < pos + 4: raise ValueError("bytecode truncado")
    size = struct.unpack(">I", data[pos:pos+4])[0]; payload = data[pos+4:]
    if len(payload) != size: raise ValueError("tamanho do bytecode não confere")
    out = json.loads(payload.decode("utf-8"))
    if out.get("format") != "neftys-bytecode" or out.get("version") != 1: raise ValueError("versão de bytecode não suportada")
    return out


def save_bundle(path: str | Path, bytecode: dict[str, Any]) -> None: Path(path).write_bytes(encode_bundle(bytecode))
def load_bundle(path: str | Path) -> dict[str, Any]: return decode_bundle(Path(path).read_bytes())
def disassemble(bytecode: dict[str, Any]) -> str: return json.dumps(bytecode, ensure_ascii=False, indent=2)
