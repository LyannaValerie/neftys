from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ast import Node


def expr_ir(node: Node) -> dict[str, Any]:
    k = node.kind
    if k in {"Inteiro", "Real", "String", "Booleano", "SV"}:
        return {"kind": "literal", "type": k, "value": node.fields.get("valor")}
    if k == "Nome": return {"kind": "name", "name": node.fields["nome"]}
    if k == "Esse": return {"kind": "this"}
    if k == "Sup": return {"kind": "super"}
    if k == "Grupo": return expr_ir(node.fields["expressão"])
    if k == "Unária": return {"kind": "unary", "op": node.fields["operador"], "value": expr_ir(node.fields["operando"])}
    if k == "Binária": return {"kind": "binary", "op": node.fields["operador"], "left": expr_ir(node.fields["esquerda"]), "right": expr_ir(node.fields["direita"])}
    if k == "Campo": return {"kind": "field", "object": expr_ir(node.fields["objeto"]), "name": node.fields["nome"]}
    if k == "Chamada": return {"kind": "call", "callee": expr_ir(node.fields["callee"]), "args": [expr_ir(a) for a in node.fields["argumentos"]]}
    raise ValueError(f"expressão não suportada pela IR: {k}")


def stmt_ir(node: Node) -> dict[str, Any]:
    k = node.kind
    if k == "Atribuição": return {"op": "assign", "target": expr_ir(node.fields["alvo"]), "value": expr_ir(node.fields["valor"])}
    if k == "Fale": return {"op": "print", "args": [expr_ir(a) for a in node.fields["argumentos"]]}
    if k == "Expressão": return {"op": "expr", "value": expr_ir(node.fields["valor"])}
    if k == "Se":
        return {"op": "if", "branches": [{"condition": expr_ir(b.fields["condição"]), "body": [stmt_ir(s) for s in b.fields["corpo"]]} for b in node.fields["ramos"]], "else": None if node.fields["senão"] is None else [stmt_ir(s) for s in node.fields["senão"]]}
    if k == "Enquanto": return {"op": "while", "condition": expr_ir(node.fields["condição"]), "body": [stmt_ir(s) for s in node.fields["corpo"]]}
    if k == "Para": return {"op": "for", "target": node.fields["alvo"].fields["nome"], "iterable": expr_ir(node.fields["iterável"]), "body": [stmt_ir(s) for s in node.fields["corpo"]]}
    if k == "Função": return {"op": "function", "name": node.fields["nome"], "params": [p.fields["nome"] for p in node.fields["parâmetros"]], "body": [stmt_ir(s) for s in node.fields["corpo"]]}
    if k == "Classe": return {"op": "class", "name": node.fields["nome"], "superclass": None if node.fields["superclasse"] is None else expr_ir(node.fields["superclasse"]), "body": [stmt_ir(s) for s in node.fields["corpo"]]}
    if k == "Retorne": return {"op": "return", "value": None if node.fields["valor"] is None else expr_ir(node.fields["valor"])}
    if k == "Pare": return {"op": "break"}
    if k == "Continue": return {"op": "continue"}
    raise ValueError(f"instrução não suportada pela IR: {k}")


def build_ir(tree: Node) -> dict[str, Any]:
    if tree.kind != "Programa": raise ValueError("raiz da AST precisa ser Programa")
    return {"format": "neftys-ir", "version": 1, "instructions": [stmt_ir(s) for s in tree.fields["instruções"]]}


def save_ir(path: str | Path, ir: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_ir(path: str | Path) -> dict[str, Any]:
    ir = json.loads(Path(path).read_text(encoding="utf-8"))
    if ir.get("format") != "neftys-ir": raise ValueError("arquivo não é Neftys IR")
    return ir


def _lit(expr: dict[str, Any]) -> tuple[str, Any] | None:
    if expr.get("kind") == "literal": return expr["type"], expr.get("value")
    return None


def _equal(a_t: str, a: Any, b_t: str, b: Any) -> bool: return a_t == b_t and a == b


def optimize_expr(expr: dict[str, Any], events: list[str]) -> dict[str, Any]:
    k = expr.get("kind")
    if k in {"literal", "name", "this", "super"}: return expr
    if k == "field": return {**expr, "object": optimize_expr(expr["object"], events)}
    if k == "call": return {**expr, "callee": optimize_expr(expr["callee"], events), "args": [optimize_expr(a, events) for a in expr["args"]]}
    if k == "unary":
        value = optimize_expr(expr["value"], events); lit = _lit(value)
        if lit:
            t, v = lit
            if expr["op"] == "!" and t == "Booleano":
                out = {"kind":"literal","type":"Booleano","value":not v}; events.append(f"fold: !{v} -> {not v}"); return out
            if expr["op"] == "-" and t in {"Inteiro","Real"}:
                out = {"kind":"literal","type":t,"value":-v}; events.append(f"fold: -{v} -> {-v}"); return out
        return {**expr, "value": value}
    if k == "binary":
        left = optimize_expr(expr["left"], events); op = expr["op"]; ll = _lit(left)
        if op == "e" and ll == ("Booleano", False):
            events.append("fold curto-circuito: Fal e ... -> Fal"); return {"kind":"literal","type":"Booleano","value":False}
        if op == "ou" and ll == ("Booleano", True):
            events.append("fold curto-circuito: Ver ou ... -> Ver"); return {"kind":"literal","type":"Booleano","value":True}
        right = optimize_expr(expr["right"], events); rr = _lit(right)
        if ll and rr:
            lt, lv = ll; rt, rv = rr
            try:
                if op in {"+","-","*","/"} and lt in {"Inteiro","Real"} and rt in {"Inteiro","Real"}:
                    value = {"+":lambda:lv+rv,"-":lambda:lv-rv,"*":lambda:lv*rv,"/":lambda:lv/rv}[op](); typ = "Real" if op == "/" or "Real" in {lt,rt} else "Inteiro"
                elif op == "+" and lt == rt == "String": value, typ = lv + rv, "String"
                elif op in {"==","!=","diff"}:
                    value = _equal(lt,lv,rt,rv); value = (not value) if op in {"!=","diff"} else value; typ = "Booleano"
                elif op in {"<",">","<=",">="} and lt in {"Inteiro","Real"} and rt in {"Inteiro","Real"}:
                    value = {"<":lv<rv,">":lv>rv,"<=":lv<=rv,">=":lv>=rv}[op]; typ = "Booleano"
                elif op in {"e","ou"} and lt == rt == "Booleano": value = (lv and rv) if op == "e" else (lv or rv); typ = "Booleano"
                else: raise ValueError
                events.append(f"fold: {lv!r} {op} {rv!r} -> {value!r}"); return {"kind":"literal","type":typ,"value":value}
            except (ZeroDivisionError, ValueError): pass
        return {**expr, "left": left, "right": right}
    return expr


def optimize_stmt(stmt: dict[str, Any], events: list[str]) -> dict[str, Any]:
    op = stmt["op"]
    if op == "assign": return {**stmt, "target": optimize_expr(stmt["target"], events), "value": optimize_expr(stmt["value"], events)}
    if op == "print": return {**stmt, "args": [optimize_expr(a, events) for a in stmt["args"]]}
    if op == "expr": return {**stmt, "value": optimize_expr(stmt["value"], events)}
    if op == "if": return {**stmt, "branches": [{"condition": optimize_expr(b["condition"], events), "body": [optimize_stmt(s, events) for s in b["body"]]} for b in stmt["branches"]], "else": None if stmt["else"] is None else [optimize_stmt(s, events) for s in stmt["else"]]}
    if op == "while": return {**stmt, "condition": optimize_expr(stmt["condition"], events), "body": [optimize_stmt(s, events) for s in stmt["body"]]}
    if op == "for": return {**stmt, "iterable": optimize_expr(stmt["iterable"], events), "body": [optimize_stmt(s, events) for s in stmt["body"]]}
    if op in {"function","class"}: return {**stmt, "body": [optimize_stmt(s, events) for s in stmt["body"]]}
    if op == "return" and stmt["value"] is not None: return {**stmt, "value": optimize_expr(stmt["value"], events)}
    return stmt


def optimize_ir(ir: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    events: list[str] = []
    out = {**ir, "instructions": [optimize_stmt(s, events) for s in ir["instructions"]], "optimized": True}
    return out, events
