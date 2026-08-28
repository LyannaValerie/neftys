from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .ast import Node
from .diagnostics import Diagnostic, artigo_tipo, nome_tipo
from .semantic_expr import SemanticExprMixin

@dataclass
class Symbol:
    name: str
    category: str
    type: str
    mutable: bool
    scope: str
    stable_type: str | None = None
    origin: str = "usuário"


class SemanticAnalyzer(SemanticExprMixin):
    def __init__(self, source: str):
        self.source = source
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.scope_names = ["global"]
        self.history: list[Symbol] = []
        self.diagnostics: list[Diagnostic] = []
        self.function_stack: list[str] = []
        self.class_stack: list[tuple[str, bool]] = []
        self.loop_depth = 0
        self._install_builtins()

    def _install_builtins(self) -> None:
        for name in ("PI", "TAU", "PHI", "EULER"):
            self._define(Symbol(name, "constante", "Real", False, "global", "Real", "padrão"))
        self._define(Symbol("relog", "função", "Função", False, "global", "Função", "padrão"))

    def _define(self, symbol: Symbol) -> None:
        self.scopes[-1][symbol.name] = symbol
        self.history.append(symbol)

    def _lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _lookup_current(self, name: str) -> Symbol | None:
        return self.scopes[-1].get(name)

    def _enter(self, name: str) -> None:
        self.scopes.append({})
        self.scope_names.append(name)

    def _exit(self) -> None:
        self.scopes.pop()
        self.scope_names.pop()

    @property
    def scope(self) -> str:
        return self.scope_names[-1]

    def error(self, code: str, message: str, node: Node | None, hint: str | None = None) -> None:
        token = node.token if node else None
        self.diagnostics.append(Diagnostic(
            code,
            message,
            token.line if token else None,
            token.column if token else None,
            hint,
        ))

    def analyze(self, program: Node) -> list[Diagnostic]:
        for stmt in program.fields["instruções"]:
            self.statement(stmt)
        return self.diagnostics

    def statement(self, node: Node) -> None:
        kind = node.kind
        if kind == "Atribuição":
            rhs_type = self.infer(node.fields["valor"])
            self.assign(node.fields["alvo"], rhs_type)
            node.attrs["tipo_valor"] = rhs_type
            return
        if kind == "Fale":
            for expr in node.fields["argumentos"]:
                self.infer(expr)
            return
        if kind == "Expressão":
            self.infer(node.fields["valor"])
            return
        if kind == "Se":
            for idx, branch in enumerate(node.fields["ramos"]):
                cond_type = self.infer(branch.fields["condição"])
                self.require_boolean(cond_type, branch.fields["condição"])
                self._enter(f"se#{idx + 1}")
                for stmt in branch.fields["corpo"]:
                    self.statement(stmt)
                self._exit()
            else_body = node.fields["senão"]
            if else_body is not None:
                self._enter("senão")
                for stmt in else_body:
                    self.statement(stmt)
                self._exit()
            return
        if kind == "Enquanto":
            cond_type = self.infer(node.fields["condição"])
            self.require_boolean(cond_type, node.fields["condição"])
            self.loop_depth += 1
            self._enter("enquanto")
            for stmt in node.fields["corpo"]:
                self.statement(stmt)
            self._exit()
            self.loop_depth -= 1
            return
        if kind == "Para":
            self.infer(node.fields["iterável"])
            self.loop_depth += 1
            self._enter("para")
            target = node.fields["alvo"]
            self._define(Symbol(target.fields["nome"], "variável", "Desconhecido", True, self.scope, None))
            for stmt in node.fields["corpo"]:
                self.statement(stmt)
            self._exit()
            self.loop_depth -= 1
            return
        if kind == "Função":
            self.declare_callable(node, "função", "Função")
            self.function_stack.append(node.fields["nome"])
            self._enter(f"fun:{node.fields['nome']}")
            for param in node.fields["parâmetros"]:
                pname = param.fields["nome"]
                if self._lookup_current(pname):
                    self.error("NFS-E320", f"Aff... parâmetro '{pname}' apareceu duas vezes. Uma cópia já dava trabalho.", param)
                else:
                    self._define(Symbol(pname, "parâmetro", "Desconhecido", True, self.scope, None))
            for stmt in node.fields["corpo"]:
                self.statement(stmt)
            self._exit()
            self.function_stack.pop()
            return
        if kind == "Classe":
            self.declare_callable(node, "classe", "Classe")
            has_super = node.fields["superclasse"] is not None
            if has_super:
                stype = self.infer(node.fields["superclasse"])
                if stype not in {"Classe", "Desconhecido"}:
                    self.error("NFS-E321", "Aff... 'herda' precisa apontar para uma classe, não para qualquer coisa que estava passando.", node.fields["superclasse"])
            self.class_stack.append((node.fields["nome"], has_super))
            self._enter(f"class:{node.fields['nome']}")
            for stmt in node.fields["corpo"]:
                self.statement(stmt)
            self._exit()
            self.class_stack.pop()
            return
        if kind == "Retorne":
            if not self.function_stack:
                self.error("NFS-E322", "Aff... 'retorne' fora de função vai retornar para onde, exatamente?", node, "use 'retorne' apenas dentro de 'fun'.")
                return
            value = node.fields["valor"]
            value_type = "SV" if value is None else self.infer(value)
            if self.function_stack[-1] == "inic" and value_type not in {"SV", "Desconhecido"}:
                self.error("NFS-E323", "Aff... 'inic' inicializa a instância; ele não devolve um prêmio no final.", node, "use 'retorne' sem valor, ou simplesmente deixe o método terminar.")
            return
        if kind == "Pare":
            if self.loop_depth == 0:
                self.error("NFS-E324", "Aff... 'pare' fora de laço não tem nada para parar.", node)
            return
        if kind == "Continue":
            if self.loop_depth == 0:
                self.error("NFS-E325", "Aff... 'continue' fora de laço quer continuar o quê?", node)
            return

        self.error("NFS-E399", f"Tá. Essa fui eu. A análise semântica não conhece o nó '{kind}'.", node, "isso indica lacuna do experimento, não erro do programa.")

    def declare_callable(self, node: Node, category: str, type_: str) -> None:
        name = node.fields["nome"]
        if self._lookup_current(name):
            self.error("NFS-E326", f"Aff... '{name}' já existe neste escopo. Dois donos para o mesmo nome é burocracia demais.", node)
            return
        self._define(Symbol(name, category, type_, False, self.scope, type_))

    def assign(self, target: Node, rhs_type: str) -> None:
        if target.kind == "Campo":
            self.infer(target.fields["objeto"])
            target.attrs["tipo"] = rhs_type
            target.attrs["regra"] = "campo estabiliza por instância em runtime"
            return

        name = target.fields["nome"]
        escaped = target.fields.get("escapado", False)
        if self.is_constant_name(name, escaped):
            current = self._lookup_current(name)
            if current is not None:
                if current.origin == "padrão":
                    self.error("NFS-E327", f"Aff... '{name}' é constante do ambiente padrão. Nem tenta domesticar a matemática.", target)
                else:
                    self.error(
                        "NFS-E328",
                        f"Aff... a constante '{name}' já recebeu {artigo_tipo(current.stable_type or current.type)} neste bloco. Constante não é ioiô.",
                        target,
                        "use outro nome ou abra um bloco interno, onde uma nova constante pode sombrear a externa.",
                    )
                return
            stable = None if rhs_type == "SV" else rhs_type
            self._define(Symbol(name, "constante", rhs_type, False, self.scope, stable))
            target.attrs.update({"categoria": "constante", "escopo": self.scope, "tipo": rhs_type})
            return

        symbol = self._lookup(name)
        if symbol is None:
            stable = None if rhs_type == "SV" else rhs_type
            self._define(Symbol(name, "variável", rhs_type, True, self.scope, stable))
            target.attrs.update({"categoria": "variável", "escopo": self.scope, "tipo": rhs_type})
            return

        if not symbol.mutable:
            self.error("NFS-E329", f"Aff... '{name}' é um vínculo imutável ({symbol.category}). Não se reatribui só porque bateu vontade.", target)
            return

        if rhs_type == "SV":
            target.attrs.update({"categoria": symbol.category, "escopo": symbol.scope, "tipo": symbol.stable_type or "SV"})
            return
        if symbol.stable_type is None:
            symbol.stable_type = rhs_type
            symbol.type = rhs_type
            target.attrs.update({"categoria": symbol.category, "escopo": symbol.scope, "tipo": rhs_type})
            return
        if rhs_type not in {symbol.stable_type, "Desconhecido"}:
            self.error(
                "NFS-E330",
                f"Não se reatribui {artigo_tipo(rhs_type)} a uma variável que recebeu {artigo_tipo(symbol.stable_type)}, seu doido!",
                target,
                f"mantenha o vínculo como {nome_tipo(symbol.stable_type)} ou use outro nome.",
            )
            return
        target.attrs.update({"categoria": symbol.category, "escopo": symbol.scope, "tipo": symbol.stable_type})

    @staticmethod
    def is_constant_name(name: str, escaped: bool) -> bool:
        if escaped and not any(ch.isalpha() for ch in name):
            return False
        letters = [ch for ch in name if ch.isalpha()]
        return bool(letters) and all(ch.upper() == ch and ch.lower() != ch for ch in letters)

    def require_boolean(self, type_: str, node: Node) -> None:
        if type_ not in {"Booleano", "Desconhecido"}:
            self.error(
                "NFS-E331",
                f"Aff... condição precisa ser booleana. Você me trouxe {artigo_tipo(type_)}.",
                node,
                "faça a expressão resultar em Ver ou Fal.",
            )

def render_symbols(symbols: Iterable[Symbol]) -> str:
    rows = list(symbols)
    header = f"{'Nome':<16} {'Categoria':<12} {'Tipo':<18} {'Mutável':<8} {'Escopo':<18} Origem"
    lines = ["Tabela de símbolos", "=" * len(header), header, "-" * len(header)]
    for s in rows:
        shown_type = s.stable_type or s.type
        lines.append(f"{s.name:<16} {s.category:<12} {shown_type:<18} {str(s.mutable):<8} {s.scope:<18} {s.origin}")
    lines.append("=" * len(header))
    return "\n".join(lines)


