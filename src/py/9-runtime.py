#!/usr/bin/env python3
"""
Runtime mínimo da Neftys.

Este arquivo NÃO é outra transformação do compilador. Ele fornece serviços
ENQUANTO o programa executa:
  - ambiente de nomes;
  - constantes e variáveis;
  - serviço `falar`;
  - erros de runtime;
  - snapshot para observação da VM.

Pontos de extensão futura:
  - heap e garbage collector;
  - metadados de tipo em runtime;
  - built-ins;
  - chamadas / stack frames;
  - exceções e I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class RuntimeFault(RuntimeError):
    pass


@dataclass
class Binding:
    kind: str
    value: Any


class NeftysRuntime:
    def __init__(self) -> None:
        self.environment: dict[str, Binding] = {}

    def define_const(self, name: str, value: Any) -> None:
        if name in self.environment:
            raise RuntimeFault(f"nome '{name}' já existe em runtime")
        self.environment[name] = Binding("const", value)

    def store_name(self, name: str, value: Any) -> None:
        binding = self.environment.get(name)
        if binding is None:
            self.environment[name] = Binding("var", value)
            return
        if binding.kind == "const":
            raise RuntimeFault(f"não é possível alterar a constante '{name}'")
        binding.value = value

    def load_name(self, name: str) -> Any:
        binding = self.environment.get(name)
        if binding is None:
            raise RuntimeFault(f"nome '{name}' não existe em runtime")
        return binding.value

    def falar(self, values: list[Any]) -> None:
        print("".join(self.format_value(value) for value in values))

    @staticmethod
    def format_value(value: Any) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def snapshot(self) -> str:
        if not self.environment:
            return "{}"
        items = [
            f"{name}={self.format_value(binding.value)}<{binding.kind}>"
            for name, binding in self.environment.items()
        ]
        return "{" + ", ".join(items) + "}"


def main() -> int:
    print("Neftys Runtime")
    print("=" * 40)
    print("Este módulo é carregado pela VM durante a execução.")
    print("Ele não transforma .bc em outro artefato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
