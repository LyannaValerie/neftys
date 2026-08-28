from __future__ import annotations

from .ast import Node
from .diagnostics import artigo_tipo, nome_tipo


class SemanticExprMixin:
    def infer(self, node: Node) -> str:
        kind = node.kind
        if kind in {"Inteiro", "Real", "String", "Booleano", "SV"}:
            mapping = {"Inteiro": "Inteiro", "Real": "Real", "String": "String", "Booleano": "Booleano", "SV": "SV"}
            node.attrs["tipo"] = mapping[kind]
            return mapping[kind]

        if kind == "Grupo":
            type_ = self.infer(node.fields["expressão"])
            node.attrs["tipo"] = type_
            return type_

        if kind == "Nome":
            name = node.fields["nome"]
            symbol = self._lookup(name)
            if symbol is None:
                self.error(
                    "NFS-E332",
                    f"Aff... '{name}' apareceu do nada. Eu verifico nomes, não invoco espíritos.",
                    node,
                    "declare o nome antes de usá-lo no escopo visível.",
                )
                node.attrs["tipo"] = "Desconhecido"
                return "Desconhecido"
            node.attrs.update({"tipo": symbol.stable_type or symbol.type, "vínculo": f"{symbol.scope}::{name}", "categoria": symbol.category})
            return symbol.stable_type or symbol.type

        if kind == "Esse":
            if not self.class_stack or not self.function_stack:
                self.error("NFS-E333", "Aff... 'esse' só faz sentido dentro de método de uma classe.", node)
                return "Desconhecido"
            node.attrs["tipo"] = "Instância"
            return "Instância"

        if kind == "Sup":
            if not self.class_stack or not self.function_stack or not self.class_stack[-1][1]:
                self.error("NFS-E334", "Aff... 'sup' só existe dentro de método cuja classe realmente herda de outra.", node)
                return "Desconhecido"
            node.attrs["tipo"] = "Instância"
            return "Instância"

        if kind == "Campo":
            self.infer(node.fields["objeto"])
            node.attrs["tipo"] = "Desconhecido"
            return "Desconhecido"

        if kind == "Chamada":
            callee_type = self.infer(node.fields["callee"])
            for arg in node.fields["argumentos"]:
                self.infer(arg)
            # Built-in conhecido: relog() -> Real.
            callee = node.fields["callee"]
            if callee.kind == "Nome" and callee.fields["nome"] == "relog":
                node.attrs["tipo"] = "Real"
                return "Real"
            if callee_type == "Classe":
                node.attrs["tipo"] = "Instância"
                return "Instância"
            node.attrs["tipo"] = "Desconhecido"
            return "Desconhecido"

        if kind == "Unária":
            op = node.fields["operador"]
            operand = self.infer(node.fields["operando"])
            if op == "!":
                if operand not in {"Booleano", "Desconhecido"}:
                    self.error("NFS-E335", f"Aff... '!' inverte booleano, não {artigo_tipo(operand)}.", node)
                node.attrs["tipo"] = "Booleano"
                return "Booleano"
            if op == "-":
                if operand not in {"Inteiro", "Real", "Desconhecido"}:
                    self.error("NFS-E336", f"Aff... '-' na frente de {artigo_tipo(operand)} não transforma isso em número por intimidação.", node)
                    node.attrs["tipo"] = "Desconhecido"
                    return "Desconhecido"
                node.attrs["tipo"] = operand
                return operand

        if kind == "Binária":
            op = node.fields["operador"]
            left = self.infer(node.fields["esquerda"])
            right = self.infer(node.fields["direita"])
            result = self.binary_type(op, left, right, node)
            node.attrs["tipo"] = result
            return result

        self.error("NFS-E398", f"Tá. Essa fui eu. Não sei inferir o tipo do nó '{kind}'.", node, "isso é lacuna do experimento.")
        return "Desconhecido"

    def binary_type(self, op: str, left: str, right: str, node: Node) -> str:
        unknown = "Desconhecido" in {left, right}
        numeric = {"Inteiro", "Real"}

        if op in {"e", "ou"}:
            if not unknown and (left != "Booleano" or right != "Booleano"):
                self.error("NFS-E337", f"Aff... '{op}' trabalha com booleanos. Recebi {nome_tipo(left)} e {nome_tipo(right)}.", node)
            return "Booleano"

        if op in {"==", "!=", "diff"}:
            return "Booleano"

        if op in {"<", ">", "<=", ">="}:
            if not unknown and not (left in numeric and right in numeric):
                self.error("NFS-E338", f"Aff... '{op}' compara números nesta versão, não {nome_tipo(left)} com {nome_tipo(right)}.", node)
            return "Booleano"

        if op == "+" and (left == "String" or right == "String"):
            if left == right == "String":
                return "String"
            if not unknown:
                self.error(
                    "NFS-E339",
                    "A expressão '+' deve ser usada entre duas strings: CONCATENATION FAILED!",
                    node,
                    f"recebido: {nome_tipo(left)} + {nome_tipo(right)}.",
                )
            return "Desconhecido"

        if op in {"+", "-", "*", "/"}:
            if unknown:
                return "Desconhecido"
            if left not in numeric or right not in numeric:
                self.error("NFS-E340", f"Aff... '{op}' esperava números e recebeu {nome_tipo(left)} com {nome_tipo(right)}.", node)
                return "Desconhecido"
            if op == "/":
                return "Real"
            return "Real" if "Real" in {left, right} else "Inteiro"

        self.error("NFS-E397", f"Tá. Essa fui eu. Operador '{op}' caiu fora da tabela semântica.", node)
        return "Desconhecido"

