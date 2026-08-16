#!/usr/bin/env python3
import sys
import argparse

# ==================== AST NODES ====================

class ASTNode:
    def __init__(self):
        self.attrs = {}  # dicionário para atributos extras (tipo, escopo, etc.)

    def to_tree(self, prefix="", show_attr=False):
        """Retorna uma lista de strings, cada uma uma linha da árvore.
        A primeira linha é o nome do nó (sem prefixo).
        As demais já têm o prefixo passado.
        Se show_attr for True, exibe os atributos armazenados em self.attrs.
        """
        raise NotImplementedError

    def _format_attrs(self, prefix, show_attr):
        """Retorna linhas representando os atributos, se show_attr for True e houver atributos."""
        if not show_attr or not self.attrs:
            return []
        lines = []
        # Adiciona um cabeçalho "attrs:" (opcional)
        # Vamos listar cada atributo como uma linha com prefixo
        attrs_items = list(self.attrs.items())
        for i, (key, value) in enumerate(attrs_items):
            is_last = (i == len(attrs_items) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(prefix + connector + f"{key}: {value}")
        return lines


class Program(ASTNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements

    def to_tree(self, prefix="", show_attr=False):
        lines = ["Programa"]
        # Atributos do nó (se houver)
        lines.extend(self._format_attrs(prefix, show_attr))
        for i, stmt in enumerate(self.statements):
            is_last = (i == len(self.statements) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            stmt_lines = stmt.to_tree(child_prefix, show_attr)
            lines.append(prefix + connector + stmt_lines[0])
            lines.extend(stmt_lines[1:])
        return lines


class DeclaracaoConstantes(ASTNode):
    def __init__(self, vinculos):
        super().__init__()
        self.vinculos = vinculos

    def to_tree(self, prefix="", show_attr=False):
        lines = ["DeclaracaoConstantes"]
        lines.extend(self._format_attrs(prefix, show_attr))
        for i, vinculo in enumerate(self.vinculos):
            is_last = (i == len(self.vinculos) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            v_lines = vinculo.to_tree(child_prefix, show_attr)
            lines.append(prefix + connector + v_lines[0])
            lines.extend(v_lines[1:])
        return lines


class Vinculo(ASTNode):
    def __init__(self, nome, valor):
        super().__init__()
        self.nome = nome
        self.valor = valor

    def to_tree(self, prefix="", show_attr=False):
        lines = ["Vinculo"]
        lines.extend(self._format_attrs(prefix, show_attr))
        # nome
        lines.append(prefix + "├── " + f"nome: {self.nome}")
        # valor
        v_lines = self.valor.to_tree(prefix + "    ", show_attr)
        lines.append(prefix + "└── " + v_lines[0])
        lines.extend(v_lines[1:])
        return lines


class DeclaracaoVariavel(ASTNode):
    def __init__(self, nome, inicializador):
        super().__init__()
        self.nome = nome
        self.inicializador = inicializador

    def to_tree(self, prefix="", show_attr=False):
        lines = ["DeclaracaoVariavel"]
        lines.extend(self._format_attrs(prefix, show_attr))
        lines.append(prefix + "├── " + f"nome: {self.nome}")
        init_lines = self.inicializador.to_tree(prefix + "    ", show_attr)
        lines.append(prefix + "└── " + init_lines[0])
        lines.extend(init_lines[1:])
        return lines


class Falar(ASTNode):
    def __init__(self, string_node, args):
        super().__init__()
        self.string_node = string_node
        self.args = args

    def to_tree(self, prefix="", show_attr=False):
        lines = ["Falar"]
        lines.extend(self._format_attrs(prefix, show_attr))
        # string
        s_lines = self.string_node.to_tree(prefix + "    ", show_attr)
        lines.append(prefix + "├── " + s_lines[0])
        lines.extend(s_lines[1:])
        # argumentos
        for i, arg in enumerate(self.args):
            is_last = (i == len(self.args) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            arg_lines = arg.to_tree(child_prefix, show_attr)
            lines.append(prefix + connector + arg_lines[0])
            lines.extend(arg_lines[1:])
        return lines


class OperacaoBinaria(ASTNode):
    def __init__(self, esquerda, operador, direita):
        super().__init__()
        self.esquerda = esquerda
        self.operador = operador
        self.direita = direita

    def to_tree(self, prefix="", show_attr=False):
        op_map = {
            'TokenPlus': 'Soma',
            'TokenMinus': 'Subtracao',
            'TokenMult': 'Multiplicacao',
            'TokenDiv': 'Divisao'
        }
        op_nome = op_map.get(self.operador, self.operador)
        lines = [op_nome]
        lines.extend(self._format_attrs(prefix, show_attr))
        # esquerda
        esq_lines = self.esquerda.to_tree(prefix + "│   ", show_attr)
        lines.append(prefix + "├── " + esq_lines[0])
        lines.extend(esq_lines[1:])
        # direita
        dir_lines = self.direita.to_tree(prefix + "    ", show_attr)
        lines.append(prefix + "└── " + dir_lines[0])
        lines.extend(dir_lines[1:])
        return lines


class Numero(ASTNode):
    def __init__(self, valor):
        super().__init__()
        self.valor = valor

    def to_tree(self, prefix="", show_attr=False):
        lines = [f"Numero: {self.valor}"]
        lines.extend(self._format_attrs(prefix, show_attr))
        return lines


class Identificador(ASTNode):
    def __init__(self, nome):
        super().__init__()
        self.nome = nome

    def to_tree(self, prefix="", show_attr=False):
        lines = [f"Identificador: {self.nome}"]
        lines.extend(self._format_attrs(prefix, show_attr))
        return lines


class StringNode(ASTNode):
    def __init__(self, valor):
        super().__init__()
        self.valor = valor

    def to_tree(self, prefix="", show_attr=False):
        lines = [f'String: "{self.valor}"']
        lines.extend(self._format_attrs(prefix, show_attr))
        return lines


# ==================== PARSER ====================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[0] if tokens else None

    def next_token(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = None

    def match(self, expected_type, expected_value=None):
        if self.current_token is None:
            raise SyntaxError("Unexpected EOF")
        token_type, token_value = self.current_token
        if token_type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {token_type}")
        if expected_value is not None and token_value != expected_value:
            raise SyntaxError(f"Expected value {expected_value}, got {token_value}")
        value = token_value
        self.next_token()
        return value

    def parse(self):
        return self.parse_program()

    def parse_program(self):
        statements = []
        while self.current_token is not None:
            stmt = self.parse_statement()
            statements.append(stmt)
        return Program(statements)

    def parse_statement(self):
        token_type, _ = self.current_token
        if token_type == 'TokenCons':
            return self.parse_cons_decl()
        elif token_type == 'TokenVar':
            return self.parse_var_decl()
        elif token_type == 'TokenFalar':
            return self.parse_falar_stmt()
        else:
            raise SyntaxError(f"Unexpected statement token: {self.current_token}")

    def parse_cons_decl(self):
        self.match('TokenCons', 'cons')
        self.match('TokenDDot', ':')
        ids = []
        ids.append(self.match('TokenIdentifier'))
        while self.current_token is not None and self.current_token[0] == 'TokenComma':
            self.match('TokenComma', ',')
            ids.append(self.match('TokenIdentifier'))
        self.match('TokenAssign', '=')
        exprs = []
        exprs.append(self.parse_expr())
        while self.current_token is not None and self.current_token[0] == 'TokenComma':
            self.match('TokenComma', ',')
            exprs.append(self.parse_expr())
        vinculos = [Vinculo(nome, valor) for nome, valor in zip(ids, exprs)]
        return DeclaracaoConstantes(vinculos)

    def parse_var_decl(self):
        self.match('TokenVar', 'var')
        self.match('TokenDDot', ':')
        name = self.match('TokenIdentifier')
        self.match('TokenAssign', '=')
        expr = self.parse_expr()
        return DeclaracaoVariavel(name, expr)

    def parse_falar_stmt(self):
        self.match('TokenFalar', 'falar')
        self.match('TokenDDot', ':')
        string_token = self.match('TokenString')
        string_value = string_token[1:-1]  # remove aspas
        string_node = StringNode(string_value)
        args = []
        if self.current_token is not None and self.current_token[0] == 'TokenComma':
            self.match('TokenComma', ',')
            args.append(self.parse_expr())
            while self.current_token is not None and self.current_token[0] == 'TokenComma':
                self.match('TokenComma', ',')
                args.append(self.parse_expr())
        return Falar(string_node, args)

    def parse_expr(self):
        node = self.parse_term()
        while self.current_token is not None and self.current_token[0] in ('TokenPlus', 'TokenMinus'):
            op = self.current_token[0]
            self.next_token()
            right = self.parse_term()
            node = OperacaoBinaria(node, op, right)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current_token is not None and self.current_token[0] in ('TokenMult', 'TokenDiv'):
            op = self.current_token[0]
            self.next_token()
            right = self.parse_factor()
            node = OperacaoBinaria(node, op, right)
        return node

    def parse_factor(self):
        token_type, token_value = self.current_token
        if token_type == 'TokenNumber':
            self.next_token()
            return Numero(float(token_value))
        elif token_type == 'TokenIdentifier':
            self.next_token()
            return Identificador(token_value)
        elif token_type == 'TokenLParen':
            self.match('TokenLParen', '(')
            expr = self.parse_expr()
            self.match('TokenRParen', ')')
            return expr
        else:
            raise SyntaxError(f"Unexpected token in factor: {self.current_token}")


# ==================== LEITOR DE TOKENS DO .tkn ====================

def ler_tokens_do_arquivo(nome_arquivo):
    tokens = []
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                if ':' not in linha:
                    continue
                tipo, valor = linha.split(':', 1)
                tipo = tipo.strip()
                valor = valor.strip()
                if valor.startswith("'") and valor.endswith("'"):
                    valor = valor[1:-1]
                tokens.append((tipo, valor))
    except FileNotFoundError:
        print(f"Erro: Arquivo '{nome_arquivo}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        sys.exit(1)
    return tokens


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(
        description="Parser para a linguagem Nefthys. Lê o arquivo .tkn e exibe a AST."
    )
    parser.add_argument('arquivo', help="Arquivo de entrada (.tkn)")
    parser.add_argument('--o', dest='saida', help="Salva a AST em um arquivo de texto.")
    parser.add_argument('--show-attr', action='store_true',
                        help="Exibe atributos extras armazenados nos nós da AST.")
    args = parser.parse_args()

    tokens = ler_tokens_do_arquivo(args.arquivo)

    try:
        parser_obj = Parser(tokens)
        ast = parser_obj.parse()
    except SyntaxError as e:
        print(f"Erro de sintaxe: {e}")
        sys.exit(1)

    # Gera a árvore como lista de linhas
    linhas_arvore = ast.to_tree(show_attr=args.show_attr)
    arvore_str = "\n".join(linhas_arvore)

    if args.saida:
        try:
            with open(args.saida, 'w', encoding='utf-8') as f:
                f.write(arvore_str)
            print(f"AST salva em '{args.saida}'")
        except Exception as e:
            print(f"Erro ao escrever arquivo: {e}")
            sys.exit(1)
    else:
        print(arvore_str)


if __name__ == "__main__":
    main()
