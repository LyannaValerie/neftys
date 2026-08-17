#!/usr/bin/env python3
"""
Análise estática visual da Neftys.

A ferramenta fecha a etapa didática iniciada pelos scripts anteriores:

    .nfs / .char / .o -> lexer -> parser -> AST -> análise estática -> tabela de símbolos
    .tkn      -> parser -> AST -> análise estática -> tabela de símbolos
    .ast      -> reconstrução da AST visual -> análise estática -> tabela de símbolos

Ela não executa o programa. Seu trabalho é descobrir, estaticamente:
- quais nomes são declarados;
- a que declaração cada identificador se vincula;
- o escopo visível de cada símbolo;
- o tipo simples das expressões que a Neftys didática já representa.

Os arquivos 2-lexer.py e 3-parser.py têm hífens no nome, portanto são carregados
explicitamente por caminho quando uma entrada precisa reconstruir a AST real.
"""

from __future__ import annotations

import argparse
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
from typing import Any, Iterable


# -----------------------------------------------------------------------------
# Símbolos e escopos
# -----------------------------------------------------------------------------


@dataclass
class Symbol:
    name: str
    kind: str
    type: str = "desconhecido"
    value: Any = None
    scope: str = "global"

    @property
    def binding(self) -> str:
        return f"{self.scope}::{self.name}"


class SymbolTable:
    """Tabela de símbolos com pilha de escopos e histórico para visualização."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.scope_names: list[str] = ["global"]
        self._history: list[Symbol] = []

    @property
    def current_scope_name(self) -> str:
        return self.scope_names[-1]

    def enter_scope(self, name: str = "local") -> None:
        self.scopes.append({})
        self.scope_names.append(name)

    def exit_scope(self) -> None:
        if len(self.scopes) == 1:
            raise RuntimeError("Não é possível sair do escopo global.")
        self.scopes.pop()
        self.scope_names.pop()

    def define(self, name: str, kind: str, type_: str, value: Any = None) -> Symbol:
        current = self.scopes[-1]
        if name in current:
            raise ValueError(
                f"símbolo '{name}' já declarado no escopo '{self.current_scope_name}'"
            )
        symbol = Symbol(name, kind, type_, value, self.current_scope_name)
        current[name] = symbol
        self._history.append(symbol)
        return symbol

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current(self, name: str) -> Symbol | None:
        return self.scopes[-1].get(name)

    def get_all_symbols(self) -> list[Symbol]:
        return list(self._history)


# -----------------------------------------------------------------------------
# AST textual (.ast)
# -----------------------------------------------------------------------------


@dataclass
class GenericNode:
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list["GenericNode"] = field(default_factory=list)


_TREE_LINE = re.compile(r"^(?P<indent>(?:(?:│   )|(?:    ))*)(?P<connector>├── |└── )?(?P<body>.*)$")
_VALUE_NODES = {"Numero", "String", "Identificador"}


def parse_ast_file(filename: str | Path) -> GenericNode:
    """Reconstrói a estrutura necessária a partir da AST textual do 3-parser.py."""

    raw_lines = Path(filename).read_text(encoding="utf-8").splitlines()
    root: GenericNode | None = None
    stack: list[tuple[int, GenericNode]] = []

    for raw in raw_lines:
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

        # Folhas como "Numero: 5.0" e "Identificador: min" são nós reais.
        if ": " in body:
            key, value = body.split(": ", 1)
            key = key.strip()
            value = value.strip()

            if key in _VALUE_NODES:
                node = GenericNode(key, {"value": _unquote(value)})
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

            # nome, tipo, vínculo, escopo etc. pertencem ao nó pai.
            parent.attrs[key] = _unquote(value)
            continue

        node = GenericNode(body)
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


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


# -----------------------------------------------------------------------------
# Carregamento do lexer/parser numerados
# -----------------------------------------------------------------------------


def _load_sibling_module(filename: str, module_name: str):
    path = Path(__file__).resolve().with_name(filename)
    if not path.exists():
        raise FileNotFoundError(f"módulo auxiliar não encontrado: {path}")

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {path.name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalizar_tokens(tokens: Iterable[tuple]) -> list[tuple[str, str]]:
    """O lexer guarda posição; o parser atual consome apenas (tipo, valor)."""
    result: list[tuple[str, str]] = []
    for token in tokens:
        if len(token) < 2:
            raise ValueError(f"token inválido: {token!r}")
        result.append((token[0], token[1]))
    return result


def build_real_ast_from_file(filename: str | Path):
    filename = str(filename)
    suffix = Path(filename).suffix.lower()
    parser_module = _load_sibling_module("3-parser.py", "neftys_parser_visual")

    if suffix == ".tkn":
        tokens = parser_module.ler_tokens_do_arquivo(filename)
    elif suffix in {".nfs", ".char", ".o"}:
        lexer_module = _load_sibling_module("2-lexer.py", "neftys_lexer_visual")
        code = lexer_module.ler_arquivo(filename)
        tokens = _normalizar_tokens(lexer_module.tokenize(code))
    else:
        raise ValueError(f"entrada não suportada para AST real: {suffix}")

    return parser_module.Parser(tokens).parse()


# -----------------------------------------------------------------------------
# Análise estática
# -----------------------------------------------------------------------------
# Pontos de expansão futura ficam concentrados nesta seção:
# - novos tipos em _infer_expr/_binary_type;
# - novos nós em _visit_statement;
# - novos escopos quando surgirem blocos/funções.



class StaticAnalyzer:
    """Resolve identificadores, infere tipos simples e preenche attrs da AST."""

    NUMERIC_TYPE = "numero"
    STRING_TYPE = "texto"
    UNKNOWN_TYPE = "desconhecido"

    def __init__(self) -> None:
        self.symbols = SymbolTable()
        self.diagnostics: list[str] = []

    def analyze(self, tree: Any) -> SymbolTable:
        if self._kind(tree) != "Program":
            self._error("a raiz da AST deveria ser 'Programa/Program'")
        self._visit_statement_container(tree)
        return self.symbols

    # ----- utilidades de adaptação entre AST real e GenericNode -----

    def _kind(self, node: Any) -> str:
        if isinstance(node, GenericNode):
            aliases = {
                "Programa": "Program",
                "Soma": "OperacaoBinaria",
                "Subtracao": "OperacaoBinaria",
                "Multiplicacao": "OperacaoBinaria",
                "Divisao": "OperacaoBinaria",
                "String": "StringNode",
            }
            return aliases.get(node.type, node.type)
        return type(node).__name__

    def _attrs(self, node: Any) -> dict[str, Any]:
        attrs = getattr(node, "attrs", None)
        if attrs is None:
            attrs = {}
            setattr(node, "attrs", attrs)
        return attrs

    def _children(self, node: Any) -> list[Any]:
        if isinstance(node, GenericNode):
            return node.children
        return []

    def _statements(self, node: Any) -> list[Any]:
        if isinstance(node, GenericNode):
            return node.children
        return list(getattr(node, "statements", []))

    def _vinculos(self, node: Any) -> list[Any]:
        if isinstance(node, GenericNode):
            return [c for c in node.children if c.type == "Vinculo"]
        return list(getattr(node, "vinculos", []))

    def _name(self, node: Any) -> str | None:
        if isinstance(node, GenericNode):
            return node.attrs.get("nome")
        return getattr(node, "nome", None)

    def _value_expr(self, vinculo: Any) -> Any | None:
        if isinstance(vinculo, GenericNode):
            return vinculo.children[0] if vinculo.children else None
        return getattr(vinculo, "valor", None)

    def _initializer(self, node: Any) -> Any | None:
        if isinstance(node, GenericNode):
            return node.children[0] if node.children else None
        return getattr(node, "inicializador", None)

    def _falar_exprs(self, node: Any) -> list[Any]:
        if isinstance(node, GenericNode):
            return node.children
        result = []
        string_node = getattr(node, "string_node", None)
        if string_node is not None:
            result.append(string_node)
        result.extend(getattr(node, "args", []))
        return result

    def _binary_parts(self, node: Any) -> tuple[Any | None, str, Any | None]:
        if isinstance(node, GenericNode):
            op = {
                "Soma": "TokenPlus",
                "Subtracao": "TokenMinus",
                "Multiplicacao": "TokenMult",
                "Divisao": "TokenDiv",
            }.get(node.type, node.type)
            left = node.children[0] if len(node.children) >= 1 else None
            right = node.children[1] if len(node.children) >= 2 else None
            return left, op, right
        return (
            getattr(node, "esquerda", None),
            getattr(node, "operador", ""),
            getattr(node, "direita", None),
        )

    def _literal_value(self, node: Any) -> Any:
        if isinstance(node, GenericNode):
            value = node.attrs.get("value")
            if node.type == "Numero":
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return value
            return value
        return getattr(node, "valor", None)

    # ----- visita semântica -----

    def _visit_statement_container(self, node: Any) -> None:
        for stmt in self._statements(node):
            self._visit_statement(stmt)

    def _visit_statement(self, node: Any) -> None:
        kind = self._kind(node)

        if kind == "DeclaracaoConstantes":
            self._declare_constants(node)
            return

        if kind == "DeclaracaoVariavel":
            self._declare_variable(node)
            return

        if kind == "Falar":
            for expr in self._falar_exprs(node):
                self._infer_expr(expr)
            return

        self._error(f"nó de declaração não reconhecido: {kind}")

    def _declare_constants(self, node: Any) -> None:
        for vinculo in self._vinculos(node):
            name = self._name(vinculo)
            expr = self._value_expr(vinculo)
            if not name:
                self._error("vínculo de constante sem nome")
                continue

            type_ = self._infer_expr(expr)
            value = self._constant_literal_value(expr)
            try:
                symbol = self.symbols.define(name, "const", type_, value)
            except ValueError as exc:
                self._error(str(exc))
                continue

            self._annotate_declaration(vinculo, symbol)

    def _declare_variable(self, node: Any) -> None:
        name = self._name(node)
        if not name:
            self._error("declaração de variável sem nome")
            return

        # O inicializador é analisado antes da definição. Assim, "var: a = a"
        # não se auto-resolve por acidente.
        type_ = self._infer_expr(self._initializer(node))
        try:
            symbol = self.symbols.define(name, "var", type_)
        except ValueError as exc:
            self._error(str(exc))
            return

        self._annotate_declaration(node, symbol)

    def _infer_expr(self, node: Any | None) -> str:
        if node is None:
            return self.UNKNOWN_TYPE

        kind = self._kind(node)
        attrs = self._attrs(node)

        if kind == "Numero":
            attrs["tipo"] = self.NUMERIC_TYPE
            return self.NUMERIC_TYPE

        if kind == "StringNode":
            attrs["tipo"] = self.STRING_TYPE
            return self.STRING_TYPE

        if kind == "Identificador":
            name = self._name(node)
            if isinstance(node, GenericNode):
                name = node.attrs.get("value")
            if not name:
                self._error("identificador sem nome")
                attrs["tipo"] = self.UNKNOWN_TYPE
                return self.UNKNOWN_TYPE

            symbol = self.symbols.lookup(name)
            if symbol is None:
                self._error(f"identificador '{name}' usado antes de uma declaração visível")
                attrs["vinculo"] = "não resolvido"
                attrs["tipo"] = self.UNKNOWN_TYPE
                return self.UNKNOWN_TYPE

            attrs["vinculo"] = symbol.binding
            attrs["categoria"] = symbol.kind
            attrs["escopo"] = symbol.scope
            attrs["tipo"] = symbol.type
            return symbol.type

        if kind == "OperacaoBinaria":
            left, op, right = self._binary_parts(node)
            left_type = self._infer_expr(left)
            right_type = self._infer_expr(right)
            result_type = self._binary_type(op, left_type, right_type)
            attrs["tipo"] = result_type
            return result_type

        self._error(f"expressão não reconhecida: {kind}")
        attrs["tipo"] = self.UNKNOWN_TYPE
        return self.UNKNOWN_TYPE

    def _binary_type(self, op: str, left: str, right: str) -> str:
        arithmetic = {"TokenPlus", "TokenMinus", "TokenMult", "TokenDiv"}
        if op not in arithmetic:
            self._error(f"operador ainda não suportado pela análise: {op}")
            return self.UNKNOWN_TYPE

        if left == self.UNKNOWN_TYPE or right == self.UNKNOWN_TYPE:
            return self.UNKNOWN_TYPE

        # Nesta fase didática, Numero é uma única categoria semântica. O parser
        # atual converte todo literal numérico para float, então fingir distinguir
        # int de float aqui produziria precisão falsa.
        if left == right == self.NUMERIC_TYPE:
            return self.NUMERIC_TYPE

        if op == "TokenPlus" and left == right == self.STRING_TYPE:
            return self.STRING_TYPE

        self._error(
            f"operação inválida: {left} {self._operator_lexeme(op)} {right}"
        )
        return self.UNKNOWN_TYPE

    def _constant_literal_value(self, expr: Any | None) -> Any:
        if expr is None:
            return None
        kind = self._kind(expr)
        if kind in {"Numero", "StringNode"}:
            return self._literal_value(expr)
        return None

    def _annotate_declaration(self, node: Any, symbol: Symbol) -> None:
        attrs = self._attrs(node)
        attrs["categoria"] = symbol.kind
        attrs["tipo"] = symbol.type
        attrs["escopo"] = symbol.scope
        attrs["vinculo"] = symbol.binding

    def _operator_lexeme(self, op: str) -> str:
        return {
            "TokenPlus": "+",
            "TokenMinus": "-",
            "TokenMult": "*",
            "TokenDiv": "/",
        }.get(op, op)

    def _error(self, message: str) -> None:
        self.diagnostics.append(message)


# -----------------------------------------------------------------------------
# Entrada e saída
# -----------------------------------------------------------------------------


def build_symbol_table_from_file(filename: str | Path) -> tuple[SymbolTable, Any, list[str]]:
    path = Path(filename)
    suffix = path.suffix.lower()

    if suffix == ".ast":
        tree = parse_ast_file(path)
    elif suffix in {".nfs", ".char", ".o", ".tkn"}:
        tree = build_real_ast_from_file(path)
    else:
        raise ValueError(
            f"extensão '{suffix}' não suportada; use .nfs, .char, .o, .tkn ou .ast"
        )

    analyzer = StaticAnalyzer()
    table = analyzer.analyze(tree)
    return table, tree, analyzer.diagnostics


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def format_symbol_table(symtab: SymbolTable) -> str:
    symbols = symtab.get_all_symbols()
    lines = [
        "Tabela de Símbolos",
        "=" * 74,
        f"{'Nome':<15} {'Categoria':<12} {'Tipo':<14} {'Valor':<15} {'Escopo':<12}",
        "-" * 74,
    ]

    for sym in symbols:
        lines.append(
            f"{sym.name:<15} {sym.kind:<12} {sym.type:<14} "
            f"{_format_value(sym.value):<15} {sym.scope:<12}"
        )

    lines.append("=" * 74)
    return "\n".join(lines)


def format_diagnostics(diagnostics: list[str]) -> str:
    if not diagnostics:
        return "Análise estática: sem diagnósticos."
    lines = [f"Análise estática: {len(diagnostics)} diagnóstico(s):"]
    lines.extend(f"  - {message}" for message in diagnostics)
    return "\n".join(lines)


def render_generic_tree(node: GenericNode, show_attrs: bool = True) -> str:
    """Render simples para observar atributos preenchidos após a análise."""
    lines: list[str] = []

    def label(current: GenericNode) -> str:
        if current.type in _VALUE_NODES and "value" in current.attrs:
            value = current.attrs["value"]
            if current.type == "String":
                return f'String: "{value}"'
            return f"{current.type}: {value}"
        return current.type

    def walk(current: GenericNode, prefix: str = "", is_last: bool = True, root: bool = False):
        connector = "" if root else ("└── " if is_last else "├── ")
        lines.append(prefix + connector + label(current))
        child_prefix = prefix if root else prefix + ("    " if is_last else "│   ")

        semantic_attrs = [
            (k, v) for k, v in current.attrs.items()
            if k != "value" and (show_attrs or k == "nome")
        ]
        items: list[tuple[str, Any]] = [("attr", item) for item in semantic_attrs]
        items.extend(("node", child) for child in current.children)

        for index, (item_kind, item) in enumerate(items):
            last = index == len(items) - 1
            item_connector = "└── " if last else "├── "
            next_prefix = child_prefix
            if item_kind == "attr":
                key, value = item
                lines.append(next_prefix + item_connector + f"{key}: {value}")
            else:
                walk(item, next_prefix, last, False)

    walk(node, root=True)
    return "\n".join(lines)


def render_annotated_ast(tree: Any) -> str:
    if isinstance(tree, GenericNode):
        return render_generic_tree(tree, show_attrs=True)
    if hasattr(tree, "to_tree"):
        return "\n".join(tree.to_tree(show_attr=True))
    raise TypeError("AST não possui representação textual conhecida")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Executa a etapa visual de análise estática da Neftys e constrói "
            "a tabela de símbolos."
        )
    )
    parser.add_argument("arquivo", help="Entrada: .nfs, .char, .o, .tkn ou .ast")
    parser.add_argument("--o", dest="saida", help="Salva a tabela de símbolos neste arquivo")
    parser.add_argument(
        "--ast-anotada",
        metavar="ARQUIVO",
        help="Salva a AST após resolução/tipagem, expondo os atributos semânticos",
    )
    parser.add_argument(
        "--mostrar-ast",
        action="store_true",
        help="Mostra no terminal a AST enriquecida pela análise estática",
    )
    args = parser.parse_args()

    try:
        symtab, tree, diagnostics = build_symbol_table_from_file(args.arquivo)
    except (OSError, ValueError, ImportError, SyntaxError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    table_text = format_symbol_table(symtab)

    if args.saida:
        Path(args.saida).write_text(table_text + "\n", encoding="utf-8")
        print(f"Tabela de símbolos salva em '{args.saida}'")
    else:
        print(table_text)

    if args.mostrar_ast or args.ast_anotada:
        ast_text = render_annotated_ast(tree)
        if args.mostrar_ast:
            print("\nAST após análise estática")
            print("=" * 74)
            print(ast_text)
        if args.ast_anotada:
            Path(args.ast_anotada).write_text(ast_text + "\n", encoding="utf-8")
            print(f"AST anotada salva em '{args.ast_anotada}'")

    print(format_diagnostics(diagnostics))
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
