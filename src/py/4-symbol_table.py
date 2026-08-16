#!/usr/bin/env python3
"""
Módulo para construção e exibição da tabela de símbolos da linguagem Nefthys.

Lê:
  - Arquivos .nfs (código fonte): usa lexer + parser para gerar a AST.
  - Arquivos .ast (gerados pelo parser com --o): interpreta a representação visual da AST.

Opções:
  --o <arquivo> : salva a tabela de símbolos no arquivo especificado.
"""

import sys
import argparse
import re

# ==================== CLASSE SYMBOL ====================

class Symbol:
    def __init__(self, name, kind, type=None, value=None, scope='global'):
        self.name = name
        self.kind = kind          # 'var', 'const', 'function', 'param'
        self.type = type          # 'int', 'float', 'string', 'bool', 'unknown'
        self.value = value        # valor literal (se constante)
        self.scope = scope

    def __repr__(self):
        return f"Symbol(name={self.name}, kind={self.kind}, type={self.type}, value={self.value}, scope={self.scope})"


# ==================== CLASSE SYMBOL TABLE ====================

class SymbolTable:
    def __init__(self):
        self.scopes = [{}]
        self.scope_names = ['global']

    def enter_scope(self, name='local'):
        self.scopes.append({})
        self.scope_names.append(name)

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_names.pop()
        else:
            raise RuntimeError("Cannot exit global scope")

    def current_scope(self):
        return self.scopes[-1]

    def define(self, name, symbol):
        if name in self.current_scope():
            raise ValueError(f"Symbol '{name}' already defined in current scope")
        self.current_scope()[name] = symbol

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current(self, name):
        return self.current_scope().get(name)

    def get_all_symbols(self):
        all_syms = []
        for scope_dict in self.scopes:
            all_syms.extend(scope_dict.values())
        return all_syms


# ==================== CONSTRUÇÃO A PARTIR DA AST REAL (ARQUIVO .nfs) ====================

def build_symbol_table_from_ast(ast):
    """Constrói a tabela a partir de uma AST real (objetos do parser)."""
    from parser import (Program, DeclaracaoConstantes, DeclaracaoVariavel,
                        Falar, Vinculo, Numero, StringNode, Identificador,
                        OperacaoBinaria)

    symtab = SymbolTable()

    def inferir_tipo(expr):
        if isinstance(expr, Numero):
            return 'float' if '.' in str(expr.valor) else 'int'
        elif isinstance(expr, StringNode):
            return 'string'
        elif isinstance(expr, Identificador):
            sym = symtab.lookup(expr.nome)
            return sym.type if sym else 'unknown'
        elif isinstance(expr, OperacaoBinaria):
            t1 = inferir_tipo(expr.esquerda)
            t2 = inferir_tipo(expr.direita)
            if t1 in ('int', 'float') and t2 in ('int', 'float'):
                return 'float' if ('float' in (t1, t2)) else 'int'
            return 'unknown'
        return 'unknown'

    def process(node):
        if node is None:
            return

        if isinstance(node, DeclaracaoConstantes):
            for vinculo in node.vinculos:
                tipo = inferir_tipo(vinculo.valor)
                valor = vinculo.valor.valor if hasattr(vinculo.valor, 'valor') else None
                sym = Symbol(vinculo.nome, 'const', tipo, valor)
                try:
                    symtab.define(vinculo.nome, sym)
                except ValueError as e:
                    print(f"Aviso: {e}")

        elif isinstance(node, DeclaracaoVariavel):
            tipo = inferir_tipo(node.inicializador)
            sym = Symbol(node.nome, 'var', tipo, None)
            try:
                symtab.define(node.nome, sym)
            except ValueError as e:
                print(f"Aviso: {e}")

        elif isinstance(node, Falar):
            for arg in node.args:
                process(arg)
            return

        # Processar filhos
        if hasattr(node, 'statements'):
            for stmt in node.statements:
                process(stmt)
        if hasattr(node, 'vinculos'):
            for v in node.vinculos:
                process(v)
        if hasattr(node, 'args'):
            for arg in node.args:
                process(arg)
        if hasattr(node, 'esquerda'):
            process(node.esquerda)
        if hasattr(node, 'direita'):
            process(node.direita)
        if hasattr(node, 'inicializador'):
            process(node.inicializador)

    process(ast)
    return symtab


# ==================== LEITURA DE ARQUIVO .ast (REPRESENTAÇÃO VISUAL) ====================

class GenericNode:
    """Nó genérico para a árvore reconstruída a partir do .ast."""
    def __init__(self, type, attrs=None, children=None):
        self.type = type
        self.attrs = attrs if attrs is not None else {}
        self.children = children if children is not None else []

    def __repr__(self):
        return f"GenericNode(type={self.type}, attrs={self.attrs}, children={len(self.children)})"


def parse_ast_file(filename):
    """
    Lê um arquivo .ast (gerado pelo parser com --o) e reconstrói uma árvore genérica.
    Retorna o nó raiz (GenericNode).
    """
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    # Remove linhas vazias
    lines = [line for line in lines if line.strip()]

    # Função para determinar o nível de indentação (número de espaços / 4)
    def get_indent(line):
        # Remover caracteres de desenho para contar apenas os espaços
        stripped = line.lstrip('│├└─ ')
        return (len(line) - len(stripped)) // 4

    # Pilha para construir a árvore
    root = None
    stack = []  # lista de (node, indent_level)

    for line in lines:
        # Remover prefixos de conexão e espaços iniciais
        clean = line
        for prefix in ['├── ', '└── ', '│   ']:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                break
        clean = clean.strip()

        # Verificar se é um atributo (contém ': ')
        if ': ' in clean:
            key, value = clean.split(': ', 1)
            key = key.strip()
            value = value.strip()
            # O atributo pertence ao nó atual no topo da pilha
            if stack:
                # Se a chave for um tipo conhecido (Numero, String, Identificador), 
                # criamos um nó filho com esse tipo e valor como atributo.
                if key in ('Numero', 'String', 'Identificador'):
                    # Criar nó filho
                    child = GenericNode(key, {'value': value})
                    stack[-1][0].children.append(child)
                else:
                    # Atributo normal (ex: nome)
                    stack[-1][0].attrs[key] = value
            else:
                # Se não houver pai, trata como nó raiz (caso raro)
                node = GenericNode(key, {'value': value})
                root = node
                stack = [(node, 0)]
        else:
            # É um nó com nome
            node_type = clean
            node = GenericNode(node_type)
            indent_level = get_indent(line)

            if root is None:
                root = node
                stack = [(node, indent_level)]
            else:
                # Desempilhar até encontrar o pai (nível - 1)
                while stack and stack[-1][1] >= indent_level:
                    stack.pop()
                if stack:
                    parent = stack[-1][0]
                    parent.children.append(node)
                else:
                    # Se não houver pai, define como root (não deve ocorrer)
                    root = node
                stack.append((node, indent_level))

    return root


def build_symbol_table_from_generic_tree(tree):
    """Constrói a tabela a partir de uma árvore genérica (parseada do .ast)."""
    symtab = SymbolTable()

    def process_node(node):
        if node.type == 'DeclaracaoConstantes':
            for child in node.children:
                if child.type == 'Vinculo':
                    nome = None
                    valor_node = None
                    for sub in child.children:
                        if sub.type == 'nome':
                            nome = sub.attrs.get('', '')
                        elif sub.type in ('Numero', 'String', 'Identificador'):
                            valor_node = sub
                    if nome and valor_node:
                        tipo = 'float' if (valor_node.type == 'Numero' and '.' in valor_node.attrs.get('value', '')) else \
                               'int' if valor_node.type == 'Numero' else \
                               'string' if valor_node.type == 'String' else 'unknown'
                        valor = valor_node.attrs.get('value', None)
                        sym = Symbol(nome, 'const', tipo, valor)
                        try:
                            symtab.define(nome, sym)
                        except ValueError as e:
                            print(f"Aviso: {e}")

        elif node.type == 'DeclaracaoVariavel':
            nome = None
            expr_node = None
            for child in node.children:
                if child.type == 'nome':
                    nome = child.attrs.get('', '')
                elif child.type in ('Soma', 'Subtracao', 'Multiplicacao', 'Divisao', 'Numero', 'Identificador'):
                    expr_node = child
            if nome:
                tipo = 'unknown'
                if expr_node:
                    if expr_node.type == 'Numero':
                        tipo = 'float' if '.' in expr_node.attrs.get('value', '') else 'int'
                    elif expr_node.type == 'String':
                        tipo = 'string'
                    elif expr_node.type == 'Identificador':
                        sym = symtab.lookup(expr_node.attrs.get('value', ''))
                        tipo = sym.type if sym else 'unknown'
                    elif expr_node.type in ('Soma', 'Subtracao', 'Multiplicacao', 'Divisao'):
                        tipo = 'float'
                sym = Symbol(nome, 'var', tipo, None)
                try:
                    symtab.define(nome, sym)
                except ValueError as e:
                    print(f"Aviso: {e}")

        # Processar filhos recursivamente
        for child in node.children:
            process_node(child)

    process_node(tree)
    return symtab


# ==================== FUNÇÕES PRINCIPAIS ====================

def build_symbol_table_from_file(filename):
    """
    Decide o tipo de arquivo e constrói a tabela de símbolos.
    Retorna uma instância de SymbolTable.
    """
    if filename.endswith('.nfs'):
        try:
            from lexer import tokenize
            from parser import Parser
        except ImportError:
            print("Erro: Não foi possível importar lexer/parser. Certifique-se de que estão no mesmo diretório.")
            sys.exit(1)

        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        return build_symbol_table_from_ast(ast)

    elif filename.endswith('.ast'):
        tree = parse_ast_file(filename)
        return build_symbol_table_from_generic_tree(tree)

    else:
        print(f"Erro: Extensão de arquivo não suportada: {filename}")
        print("Use .nfs para código fonte ou .ast para saída do parser.")
        sys.exit(1)


# ==================== EXIBIÇÃO FORMATADA ====================

def format_symbol_table(symtab):
    """Retorna uma string formatada da tabela de símbolos."""
    lines = []
    lines.append("Tabela de Símbolos")
    lines.append("=" * 60)
    lines.append(f"{'Nome':<15} {'Categoria':<10} {'Tipo':<12} {'Valor':<15} {'Escopo':<10}")
    lines.append("-" * 60)
    for scope_idx, scope_dict in enumerate(symtab.scopes):
        escopo_nome = symtab.scope_names[scope_idx]
        for name, sym in scope_dict.items():
            valor_str = str(sym.value) if sym.value is not None else '-'
            lines.append(f"{name:<15} {sym.kind:<10} {sym.type or 'unknown':<12} {valor_str:<15} {escopo_nome:<10}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(
        description="Constrói e exibe a tabela de símbolos a partir de um arquivo .nfs ou .ast."
    )
    parser.add_argument('arquivo', help="Arquivo de entrada (.nfs ou .ast)")
    parser.add_argument('--o', dest='saida', help="Salva a tabela de símbolos em um arquivo.")
    args = parser.parse_args()

    try:
        symtab = build_symbol_table_from_file(args.arquivo)
    except Exception as e:
        print(f"Erro durante a construção da tabela: {e}")
        sys.exit(1)

    saida = format_symbol_table(symtab)

    if args.saida:
        try:
            with open(args.saida, 'w', encoding='utf-8') as f:
                f.write(saida)
            print(f"Tabela de símbolos salva em '{args.saida}'")
        except Exception as e:
            print(f"Erro ao escrever arquivo: {e}")
            sys.exit(1)
    else:
        print(saida)


if __name__ == "__main__":
    main()
