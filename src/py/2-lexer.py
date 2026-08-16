#!/usr/bin/env python3
import sys
import re
import argparse
import ast

# Mapeamento dos nomes dos grupos para os tokens desejados
TOKEN_MAP = {
    'CONS': 'TokenCons',
    'VAR': 'TokenVar',
    'FALAR': 'TokenFalar',
    'IDENT': 'TokenIdentifier',
    'NUMBER': 'TokenNumber',
    'STRING': 'TokenString',
    'DDOT': 'TokenDDot',        # :
    'COMMA': 'TokenComma',      # ,
    'SEMICOLON': 'TokenSemicolon',  # ;
    'LPAREN': 'TokenLParen',    # (
    'RPAREN': 'TokenRParen',    # )
    'ASSIGN': 'TokenAssign',    # =
    'PLUS': 'TokenPlus',        # +
    'MINUS': 'TokenMinus',      # -
    'MULT': 'TokenMult',        # *
    'DIV': 'TokenDiv',          # /
    'LT': 'TokenLT',            # <
    'GT': 'TokenGT',            # >
}

# Especificação dos padrões regex com nomes de grupos
token_specs = [
    ('COMMENT', r'#.*'),                          # comentários (ignorar)
    ('WHITESPACE', r'\s+'),                       # espaços e quebras (ignorar)
    ('CONS', r'cons'),                            # palavra-chave cons
    ('VAR', r'var'),                              # palavra-chave var
    ('FALAR', r'falar'),                          # palavra-chave falar
    ('IDENT', r'[a-zA-Z_][a-zA-Z0-9_]*'),        # identificadores
    ('NUMBER', r'\d+(\.\d+)?'),                   # números (inteiros ou floats)
    ('STRING', r'\"([^"\\]|\\.)*\"'),             # strings entre aspas duplas
    ('DDOT', r':'),                               # dois pontos
    ('COMMA', r','),                              # vírgula
    ('SEMICOLON', r';'),                          # ponto e vírgula
    ('LPAREN', r'\('),                            # parêntese esquerdo
    ('RPAREN', r'\)'),                            # parêntese direito
    ('ASSIGN', r'='),                             # atribuição
    ('PLUS', r'\+'),                              # adição
    ('MINUS', r'-'),                              # subtração
    ('MULT', r'\*'),                              # multiplicação
    ('DIV', r'/'),                                # divisão
    ('LT', r'<'),                                 # menor que
    ('GT', r'>'),                                 # maior que
]

regex_pattern = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specs)
regex = re.compile(regex_pattern)

def ler_arquivo(nome_arquivo):
    """
    Lê o arquivo e retorna o código como string.
    Se o arquivo terminar com .o, interpreta como uma lista de caracteres.
    Caso contrário, lê como texto puro.
    """
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{nome_arquivo}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        sys.exit(1)

    # Se terminar com .o, tenta interpretar como lista de caracteres
    if nome_arquivo.endswith('.o'):
        try:
            # Avalia o conteúdo como uma lista Python
            lista_caracteres = ast.literal_eval(conteudo)
            if not isinstance(lista_caracteres, list):
                raise ValueError("O conteúdo não é uma lista.")
            # Converte para string
            codigo = ''.join(lista_caracteres)
            print(f"Arquivo '{nome_arquivo}' interpretado como lista de caracteres.")
            return codigo
        except Exception as e:
            print(f"Erro ao interpretar arquivo .o como lista de caracteres: {e}")
            sys.exit(1)
    else:
        # Arquivo normal: retorna o conteúdo cru
        return conteudo

def tokenize(code):
    """
    Analisa o código-fonte e retorna uma lista de tokens.
    Cada token é uma tupla (tipo, valor, linha, coluna).
    """
    tokens = []
    for match in regex.finditer(code):
        kind = match.lastgroup
        value = match.group()
        start = match.start()

        # Ignora comentários e espaços
        if kind in ('COMMENT', 'WHITESPACE'):
            continue

        # Calcula linha e coluna
        line_num = code[:start].count('\n') + 1
        last_newline = code.rfind('\n', 0, start)
        col = start - last_newline if last_newline != -1 else start + 1

        # Mapeia o tipo para o nome do token
        token_type = TOKEN_MAP.get(kind, kind)
        tokens.append((token_type, value, line_num, col))

    return tokens

def formatar_tokens(tokens):
    """
    Formata a lista de tokens para saída (apenas tipos e valores).
    """
    linhas = []
    for ttype, value, _, _ in tokens:
        linhas.append(f"{ttype}: '{value}'")
    return "\n".join(linhas)

def main():
    parser = argparse.ArgumentParser(
        description="Lexer para a linguagem Nefthys. Suporta arquivos .nfs (código) ou .o (lista de caracteres)."
    )
    parser.add_argument('arquivo', help="Arquivo de entrada (.nfs ou .o)")
    parser.add_argument('--o', dest='saida', help="Arquivo de saída para tokens (ex: char.tkn).")
    parser.add_argument('--detalhado', action='store_true',
                        help="Exibe tokens completos (tipo, valor, linha, coluna).")
    args = parser.parse_args()

    # Lê o arquivo (detecta .o automaticamente)
    codigo = ler_arquivo(args.arquivo)

    # Tokeniza
    tokens = tokenize(codigo)

    # Prepara saída
    if args.detalhado:
        saida = "\n".join(str(t) for t in tokens)
    else:
        saida = formatar_tokens(tokens)

    # Salva ou imprime
    if args.saida:
        try:
            with open(args.saida, 'w', encoding='utf-8') as f:
                f.write(saida)
            print(f"Tokens salvos em '{args.saida}'")
        except Exception as e:
            print(f"Erro ao escrever arquivo de saída: {e}")
            sys.exit(1)
    else:
        print(saida)

if __name__ == "__main__":
    main()
