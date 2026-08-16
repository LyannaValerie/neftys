#!/usr/bin/env python3
import sys
import re

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
    # Adicione outros operadores conforme necessário
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

# Constroi o padrão regex combinado com grupos nomeados
regex_pattern = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specs)
regex = re.compile(regex_pattern)

def tokenize(code):
    """
    Analisa o código-fonte e retorna uma lista de tokens.
    Cada token é uma tupla (tipo, valor, linha, coluna).
    """
    tokens = []
    line_num = 1
    line_start = 0  # posição do início da linha atual no código

    for match in regex.finditer(code):
        kind = match.lastgroup
        value = match.group()
        start = match.start()
        end = match.end()

        # Atualiza número da linha e coluna
        # Conta quantas quebras de linha ocorreram desde o último token
        # Para simplificar, calculamos a linha baseando-se na posição
        # (melhor usar um contador separado, mas vamos recalcular)
        # Vamos usar um método mais simples: contar quebras até a posição
        # Mas para eficiência, podemos manter um índice de linha incremental.
        # Vou recalcular a linha e coluna a partir do início do arquivo.
        # Isso é mais lento, mas para fins didáticos serve.
        # Melhor: atualizar linha/coluna ao encontrar \n.
        pass

    # Vamos refazer de uma forma mais robusta: percorrer caractere por caractere para controle de linha.
    # Mas o regex é mais simples. Vou usar uma abordagem mista: usar regex para tokens e manter posição.
    # Vou reimplementar com um loop manual para controle preciso de linha/coluna.

    # Na verdade, vou usar a abordagem com regex e calcular linha/coluna a partir da posição.
    # Para cada match, calculamos a linha contando as quebras de linha antes do match.
    # Isso é feito com code[:start].count('\n') + 1
    # E a coluna = start - code.rfind('\n', 0, start) (ou start + 1 se não houver quebra)
    # Vamos fazer isso.

    # Reiniciar a iteração porque precisamos da posição.
    for match in regex.finditer(code):
        kind = match.lastgroup
        value = match.group()
        start = match.start()

        # Se for comentário ou espaço, ignoramos
        if kind in ('COMMENT', 'WHITESPACE'):
            continue

        # Calcula linha e coluna
        line_num = code[:start].count('\n') + 1
        last_newline = code.rfind('\n', 0, start)
        col = start - last_newline if last_newline != -1 else start + 1

        # Mapeia o tipo para o nome do token
        token_type = TOKEN_MAP.get(kind, kind)  # se não mapeado, usa o nome do grupo
        tokens.append((token_type, value, line_num, col))

    return tokens

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 lexer.py <arquivo.nfs>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        sys.exit(1)

    # Tokeniza
    tokens = tokenize(code)

    # Exibe os tokens formatados
    print("Lista de tokens (tipo, valor, linha, coluna):")
    for token in tokens:
        print(f"{token}")

    # Opcional: exibe apenas os tipos e valores
    print("\nApenas tipos e valores:")
    for ttype, value, _, _ in tokens:
        print(f"{ttype}: '{value}'")

if __name__ == "__main__":
    main()
