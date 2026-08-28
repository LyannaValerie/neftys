#!/usr/bin/env python3
"""Executa o bytecode estrutural demonstrativo da Neftys v1."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from typing import Any

from neftys_v1.bytecode import load_bundle

STMT = {1:"assign",2:"print",3:"expr",4:"if",5:"while",6:"for",7:"function",8:"class",9:"return",10:"break",11:"continue"}
EXPR = {101:"literal",102:"name",103:"this",104:"super",105:"unary",106:"binary",107:"field",108:"call"}


def load_runtime():
    path = Path(__file__).with_name("9-runtime.py")
    spec = importlib.util.spec_from_file_location("neftys_runtime_v1", path)
    if spec is None or spec.loader is None: raise ImportError("runtime da Neftys não pôde ser carregado")
    mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod; spec.loader.exec_module(mod); return mod


class ReturnSignal(Exception):
    def __init__(self, value): self.value = value
class BreakSignal(Exception): pass
class ContinueSignal(Exception): pass


class VM:
    def __init__(self, bytecode: dict[str, Any], runtime_module, trace: bool = False):
        self.code = bytecode["code"]; self.m = runtime_module; self.runtime = runtime_module.NeftysRuntime(); self.trace = trace

    def log(self, text: str, env) -> None:
        if self.trace: print(f"[VM] {text:<30} {self.runtime.snapshot(env)}")

    def run(self) -> None: self.exec_block(self.code, self.runtime.global_env)

    def exec_block(self, code: list[dict[str, Any]], env) -> None:
        for ins in code:
            op = STMT[ins["op"]]; self.log(op, env)
            if op == "assign":
                value = self.eval_expr(ins["value"], env); self.assign(ins["target"], value, env)
            elif op == "print": self.runtime.fale([self.eval_expr(a, env) for a in ins["args"]])
            elif op == "expr": self.eval_expr(ins["value"], env)
            elif op == "if":
                taken = False
                for branch in ins["branches"]:
                    cond = self.eval_expr(branch["condition"], env); self.require_bool(cond)
                    if cond:
                        child = self.m.Environment(env, "se"); self.exec_block(branch["body"], child); taken = True; break
                if not taken and ins.get("else_body") is not None:
                    self.exec_block(ins["else_body"], self.m.Environment(env, "senão"))
            elif op == "while":
                while True:
                    cond = self.eval_expr(ins["condition"], env); self.require_bool(cond)
                    if not cond: break
                    try: self.exec_block(ins["body"], self.m.Environment(env, "enquanto"))
                    except ContinueSignal: continue
                    except BreakSignal: break
            elif op == "for":
                iterable = self.eval_expr(ins["iterable"], env)
                if type(iterable) is not str:
                    raise self.m.RuntimeFault("NFS-R420", "Aff... 'para' ainda só sabe percorrer String neste experimento. Coleções de verdade ainda nem foram definidas.")
                for item in iterable:
                    child = self.m.Environment(env, "para"); child.define(ins["target"], item, True, "variável", "String")
                    try: self.exec_block(ins["body"], child)
                    except ContinueSignal: continue
                    except BreakSignal: break
            elif op == "function":
                fn = self.m.Function(ins["name"], list(ins["params"]), ins["body"], env)
                env.define(ins["name"], fn, False, "função", "Função")
            elif op == "class":
                superclass = None if ins.get("superclass") is None else self.eval_expr(ins["superclass"], env)
                if superclass is not None and not isinstance(superclass, self.m.Class):
                    raise self.m.RuntimeFault("NFS-R421", "Aff... 'herda' recebeu algo que não é classe. Genealogia também tem requisitos mínimos.")
                klass = self.m.Class(ins["name"], superclass)
                env.define(ins["name"], klass, False, "classe", "Classe")
                for member in ins["body"]:
                    if STMT[member["op"]] != "function":
                        raise self.m.RuntimeFault("NFS-R422", "Aff... corpo de classe, por enquanto, contém métodos. Esse membro resolveu inovar sozinho.")
                    fn = self.m.Function(member["name"], list(member["params"]), member["body"], env, klass)
                    klass.methods[fn.name] = fn
            elif op == "return": raise ReturnSignal(None if ins.get("value") is None else self.eval_expr(ins["value"], env))
            elif op == "break": raise BreakSignal()
            elif op == "continue": raise ContinueSignal()

    def assign(self, target: dict[str, Any], value: Any, env) -> None:
        kind = EXPR[target["tag"]]
        if kind == "name": self.runtime.assign_name(env, target["name"], value); return
        if kind == "field":
            obj = self.eval_expr(target["object"], env)
            if not isinstance(obj, self.m.Instance): raise self.m.RuntimeFault("NFS-R423", "Aff... atribuição de campo exige uma instância. O ponto não faz milagres.")
            self.runtime.set_field(obj, target["name"], value); return
        raise self.m.RuntimeFault("NFS-I901", "Tá. Essa fui eu. O bytecode trouxe um alvo de atribuição impossível.")

    def eval_expr(self, e: dict[str, Any], env):
        kind = EXPR[e["tag"]]
        if kind == "literal": return e.get("value")
        if kind == "name": return env.get(e["name"])
        if kind == "this": return env.get("esse")
        if kind == "super": return env.get("sup")
        if kind == "field": return self.runtime.get_field(self.eval_expr(e["object"], env), e["name"])
        if kind == "unary":
            v = self.eval_expr(e["value"], env)
            if e["op"] == "!": self.require_bool(v); return not v
            if e["op"] == "-":
                if type(v) not in {int,float}: raise self.m.RuntimeFault("NFS-R424", "Aff... '-' não torna uma coisa numérica por pressão social.")
                return -v
        if kind == "binary": return self.binary(e, env)
        if kind == "call":
            callee = self.eval_expr(e["callee"], env); args = [self.eval_expr(a, env) for a in e["args"]]
            return self.call(callee, args)
        raise self.m.RuntimeFault("NFS-I902", f"Tá. Essa fui eu. Expressão de bytecode desconhecida: {kind}")

    def binary(self, e: dict[str, Any], env):
        op = e["op"]; left = self.eval_expr(e["left"], env)
        if op == "e": self.require_bool(left); return False if not left else self._bool_right(e, env)
        if op == "ou": self.require_bool(left); return True if left else self._bool_right(e, env)
        right = self.eval_expr(e["right"], env)
        lt, rt = self.m.type_name(left), self.m.type_name(right)
        if op in {"==","!=","diff"}:
            eq = lt == rt and left == right; return (not eq) if op in {"!=","diff"} else eq
        if op in {"<",">","<=",">="}:
            if type(left) not in {int,float} or type(right) not in {int,float}: raise self.m.RuntimeFault("NFS-R425", f"Aff... '{op}' compara números neste experimento.")
            return {"<":left<right,">":left>right,"<=":left<=right,">=":left>=right}[op]
        if op == "+" and (type(left) is str or type(right) is str):
            if type(left) is not str or type(right) is not str: raise self.m.RuntimeFault("NFS-R426", "A expressão '+' deve ser usada entre duas strings: CONCATENATION FAILED!")
            return left + right
        if op in {"+","-","*","/"}:
            if type(left) not in {int,float} or type(right) not in {int,float}: raise self.m.RuntimeFault("NFS-R427", f"Aff... '{op}' esperava números. Recebeu {lt} e {rt}.")
            if op == "/" and right == 0: raise self.m.RuntimeFault("NFS-R428", "Aff... divisão por zero. Nem a Neftys consegue distribuir coisa nenhuma para zero pessoas.")
            return {"+":lambda:left+right,"-":lambda:left-right,"*":lambda:left*right,"/":lambda:left/right}[op]()
        raise self.m.RuntimeFault("NFS-I903", f"Tá. Essa fui eu. Operador '{op}' escapou da VM.")

    def _bool_right(self, e, env):
        right = self.eval_expr(e["right"], env); self.require_bool(right); return right

    def require_bool(self, value):
        if type(value) is not bool: raise self.m.RuntimeFault("NFS-R429", f"Aff... condição lógica precisa ser booleana, não {self.m.type_name(value).lower()}.")

    def call(self, callee, args):
        if isinstance(callee, self.m.Builtin): return callee.fn(*args)
        if isinstance(callee, self.m.Class):
            inst = self.m.Instance(callee)
            found = callee.find_method("inic")
            if found:
                fn, owner = found; self.call(self.m.BoundMethod(fn, inst, owner), args)
            elif args: raise self.m.RuntimeFault("NFS-R430", f"Aff... '{callee.name}' não tem 'inic', então esses argumentos chegaram sem convite.")
            return inst
        if isinstance(callee, self.m.BoundMethod):
            fn = callee.function; call_env = self.m.Environment(fn.closure, f"método:{fn.name}")
            call_env.define("esse", callee.instance, False, "especial", "Instância")
            if callee.owner_class.superclass is not None:
                call_env.define("sup", self.m.SuperProxy(callee.owner_class.superclass, callee.instance), False, "especial", "Instância")
            return self.call_function(fn, args, call_env)
        if isinstance(callee, self.m.Function): return self.call_function(callee, args, self.m.Environment(callee.closure, f"fun:{callee.name}"))
        raise self.m.RuntimeFault("NFS-R431", f"Aff... {self.m.type_name(callee).lower()} não é chamável. Parênteses não concedem poderes.")

    def call_function(self, fn, args, env):
        if len(args) != len(fn.params): raise self.m.RuntimeFault("NFS-R432", f"Aff... '{fn.name}' esperava {len(fn.params)} argumento(s) e recebeu {len(args)}.")
        for name, value in zip(fn.params, args): env.define(name, value, True, "parâmetro")
        try: self.exec_block(fn.body, env)
        except ReturnSignal as ret: return ret.value
        return None


def main() -> int:
    cli = argparse.ArgumentParser(description="Executa bytecode da VM demonstrativa Neftys v1.")
    cli.add_argument("arquivo"); cli.add_argument("--trace", action="store_true")
    args = cli.parse_args()
    try:
        mod = load_runtime(); VM(load_bundle(args.arquivo), mod, args.trace).run(); return 0
    except Exception as exc:
        mod = sys.modules.get("neftys_runtime_v1")
        if mod is not None and isinstance(exc, getattr(mod, "RuntimeFault", ())): print(exc.render(), file=sys.stderr)
        else: print(f"NFS-I900\nTá. Essa fui eu. A VM tropeçou sozinha.\nDetalhe interno: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__": raise SystemExit(main())
