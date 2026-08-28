#!/usr/bin/env python3
"""Serviços de runtime usados pela VM demonstrativa da Neftys v1."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Callable


class RuntimeFault(RuntimeError):
    def __init__(self, code: str, message: str, hint: str | None = None):
        self.code, self.message, self.hint = code, message, hint
        super().__init__(message)
    def render(self) -> str:
        text = f"{self.code}\n{self.message}"
        if self.hint: text += f"\nComo faz: {self.hint}"
        return text


def type_name(v: Any) -> str:
    if v is None: return "SV"
    if type(v) is bool: return "Booleano"
    if type(v) is int: return "Inteiro"
    if type(v) is float: return "Real"
    if type(v) is str: return "String"
    if isinstance(v, Function): return "Função"
    if isinstance(v, Class): return "Classe"
    if isinstance(v, Instance): return "Instância"
    if isinstance(v, BoundMethod): return "Função"
    if isinstance(v, Builtin): return "Função"
    if isinstance(v, SuperProxy): return "Instância"
    return type(v).__name__


def is_constant_name(name: str) -> bool:
    letters = [c for c in name if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


@dataclass
class Binding:
    value: Any
    mutable: bool
    stable_type: str | None
    category: str


class Environment:
    def __init__(self, parent: "Environment | None" = None, name: str = "escopo"):
        self.parent, self.name = parent, name
        self.values: dict[str, Binding] = {}
    def current(self, name: str) -> Binding | None: return self.values.get(name)
    def resolve_env(self, name: str) -> "Environment | None":
        env: Environment | None = self
        while env:
            if name in env.values: return env
            env = env.parent
        return None
    def get(self, name: str) -> Any:
        env = self.resolve_env(name)
        if env is None: raise RuntimeFault("NFS-R401", f"Aff... '{name}' não existe nesse caminho de execução. Eu procurei, infelizmente.")
        return env.values[name].value
    def define(self, name: str, value: Any, mutable: bool, category: str, stable_type: str | None = None) -> None:
        if name in self.values: raise RuntimeFault("NFS-R402", f"Aff... '{name}' já existe neste escopo. Dois vínculos no mesmo endereço social não dá.")
        if stable_type is None and value is not None: stable_type = type_name(value)
        self.values[name] = Binding(value, mutable, stable_type, category)


@dataclass
class Builtin:
    name: str
    fn: Callable[..., Any]


@dataclass
class Function:
    name: str
    params: list[str]
    body: list[dict[str, Any]]
    closure: Environment
    owner_class: "Class | None" = None


@dataclass
class BoundMethod:
    function: Function
    instance: "Instance"
    owner_class: "Class"


@dataclass
class Class:
    name: str
    superclass: "Class | None"
    methods: dict[str, Function] = field(default_factory=dict)
    def find_method(self, name: str) -> tuple[Function, "Class"] | None:
        if name in self.methods: return self.methods[name], self
        if self.superclass: return self.superclass.find_method(name)
        return None


@dataclass
class FieldBinding:
    value: Any
    stable_type: str | None


@dataclass
class Instance:
    klass: Class
    fields: dict[str, FieldBinding] = field(default_factory=dict)


@dataclass
class SuperProxy:
    superclass: Class
    instance: Instance


class NeftysRuntime:
    def __init__(self):
        self.global_env = Environment(None, "global")
        for name, value in {"PI":math.pi, "TAU":math.tau, "PHI":(1+math.sqrt(5))/2, "EULER":math.e}.items():
            self.global_env.define(name, float(value), False, "constante", "Real")
        self.global_env.define("relog", Builtin("relog", lambda: float(time.monotonic())), False, "função", "Função")

    def assign_name(self, env: Environment, name: str, value: Any) -> None:
        if is_constant_name(name):
            if env.current(name) is not None:
                b = env.current(name)
                received = type_name(value); prior = b.stable_type or type_name(b.value)
                raise RuntimeFault("NFS-R410", f"Não se reatribui um {received.lower()} a uma constante que recebeu um {prior.lower()}, seu doido!")
            env.define(name, value, False, "constante"); return
        owner = env.resolve_env(name)
        if owner is None:
            env.define(name, value, True, "variável"); return
        b = owner.values[name]
        if not b.mutable:
            raise RuntimeFault("NFS-R411", f"Aff... '{name}' é imutável. Reatribuição não vira permitida por insistência.")
        self._check_stable(b, value, f"variável '{name}'")
        b.value = value

    def _check_stable(self, binding: Binding | FieldBinding, value: Any, subject: str) -> None:
        if value is None: return
        t = type_name(value)
        if binding.stable_type is None:
            binding.stable_type = t; return
        if t != binding.stable_type:
            raise RuntimeFault("NFS-R412", f"Não se reatribui um {t.lower()} a {subject} que recebeu um {binding.stable_type.lower()}, seu doido!")

    def set_field(self, instance: Instance, name: str, value: Any) -> None:
        field = instance.fields.get(name)
        if field is None:
            instance.fields[name] = FieldBinding(value, None if value is None else type_name(value)); return
        self._check_stable(field, value, f"campo '{name}'"); field.value = value

    def get_field(self, obj: Any, name: str) -> Any:
        if isinstance(obj, SuperProxy):
            found = obj.superclass.find_method(name)
            if not found: raise RuntimeFault("NFS-R413", f"Aff... a superclasse não tem método '{name}'. Nem herança inventa membro.")
            fn, owner = found; return BoundMethod(fn, obj.instance, owner)
        if not isinstance(obj, Instance):
            raise RuntimeFault("NFS-R414", f"Aff... tentei acessar '.{name}' em {type_name(obj).lower()}. Campo precisa de objeto.")
        if name in obj.fields: return obj.fields[name].value
        found = obj.klass.find_method(name)
        if found:
            fn, owner = found; return BoundMethod(fn, obj, owner)
        raise RuntimeFault("NFS-R415", f"Aff... '{obj.klass.name}' não tem campo nem método '{name}'. Digitação criativa não cria propriedade.")

    @staticmethod
    def format_value(v: Any) -> str:
        if v is None: return "SV"
        if type(v) is bool: return "Verdadeiro!" if v else "Falso!"
        if type(v) is float and v.is_integer(): return str(int(v))
        return str(v)

    def fale(self, values: list[Any]) -> None: print("".join(self.format_value(v) for v in values))

    def snapshot(self, env: Environment | None = None) -> str:
        env = env or self.global_env; parts=[]
        while env:
            parts.append(env.name + ":{" + ", ".join(f"{k}={self.format_value(b.value)}<{b.category}:{b.stable_type or type_name(b.value)}>" for k,b in env.values.items()) + "}")
            env = env.parent
        return " <- ".join(parts)


def main() -> int:
    rt = NeftysRuntime()
    print("Neftys Runtime v1")
    print(rt.snapshot())
    return 0

if __name__ == "__main__": raise SystemExit(main())
