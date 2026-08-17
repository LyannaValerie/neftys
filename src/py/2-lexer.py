#!/usr/bin/env python3
import argparse
import ast
from pathlib import Path
import re
import sys


# =============================================================================
# VOCABULÁRIO LÉXICO
# =============================================================================
# Novas palavras-chave, literais, pontuação e operadores devem ser adicionados
# nas seções abaixo. A ideia é expandir o vocabulário sem reescrever o scanner.
# =============================================================================

# ------------------------------ Palavras-chave -------------------------------

KEYWORDS = {
    "cons": "TokenCons",
    "var": "TokenVar",
    "falar": "TokenFalar",

    # Futuro:
    # "se": "TokenSe",
    # "senao": "TokenSenao",
    # "enquanto": "TokenEnquanto",
    # "funcao": "TokenFuncao",
}


# --------------------------- Padrões de tokens -------------------------------

# A ordem importa: padrões mais específicos devem vir antes dos mais genéricos.
TOKEN_SPECS = [
    # --- comentários e espaçamento ---
    ("COMMENT",    r"#.*"),
    ("WHITESPACE", r"\s+"),

    # --- literais ---
    ("STRING",     r'"([^"\\]|\\.)*"'),
    ("NUMBER",     r"\d+(?:\.\d+)?"),

    # Futuro: outros literais entram aqui.
    # ("BOOL",     r"\b(?:verdadeiro|falso)\b"),

    # --- pontuação ---
    ("DDOT",       r":"),
    ("COMMA",      r","),
    ("SEMICOLON",  r";"),
    ("LPAREN",     r"\("),
    ("RPAREN",     r"\)"),

    # Futuro:
    # ("LBRACE",   r"\{"),
    # ("RBRACE",   r"\}"),

    # --- operadores ---
    # Operadores compostos futuros devem vir ANTES dos simples.
    # Futuro:
    # ("EQ",       r"=="),
    # ("LTE",      r"<="),
    # ("GTE",      r">="),

    ("ASSIGN",     r"="),
    ("PLUS",       r"\+"),
    ("MINUS",      r"-"),
    ("MULT",       r"\*"),
    ("DIV",        r"/"),
    ("LT",         r"<"),
    ("GT",         r">"),

    # --- identificadores ---
    ("IDENT",      r"[a-zA-Z_][a-zA-Z0-9_]*"),
]


TOKEN_MAP = {
    "STRING": "TokenString",
    "NUMBER": "TokenNumber",
    "DDOT": "TokenDDot",
    "COMMA": "TokenComma",
    "SEMICOLON": "TokenSemicolon",
    "LPAREN": "TokenLParen",
    "RPAREN": "TokenRParen",
    "ASSIGN": "TokenAssign",
    "PLUS": "TokenPlus",
    "MINUS": "TokenMinus",
    "MULT": "TokenMult",
    "DIV": "TokenDiv",
    "LT": "TokenLT",
    "GT": "TokenGT",

    # Futuro: mapeamentos dos novos grupos entram aqui.
}


REGEX_PATTERN = "|".join(
    f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECS
)
REGEX = re.compile(REGEX_PATTERN)


# =============================================================================
# ERROS LÉXICOS
# =============================================================================

class LexicalError(Exception):
    """Erro encontrado antes que toda a entrada consiga virar tokens."""

    def __init__(self, message, line=None, column=None, fragment=None):
        self.message = message
        self.line = line
        self.column = column
        self.fragment = fragment

        location = ""
        if line is not None and column is not None:
            location = f" (linha {line}, coluna {column})"

        detail = ""
        if fragment is not None:
            detail = f": {fragment!r}"

        super().__init__(f"{message}{location}{detail}")


# =============================================================================
# ENTRADA / REPRESENTAÇÕES
# =============================================================================

# Artefatos que guardam uma lista Python literal de caracteres.
CHARACTER_LIST_SUFFIXES = {".char", ".o"}

# Código-fonte textual conhecido hoje.
SOURCE_SUFFIXES = {".nfs"}

# Futuro:
# CHARACTER_LIST_SUFFIXES.add(".chars")
# SOURCE_SUFFIXES.add(".neftys")


def _posicao(code, index):
    """Retorna linha e coluna (1-based) para um índice da string."""
    line = code.count("\n", 0, index) + 1
    last_newline = code.rfind("\n", 0, index)
    column = index - last_newline if last_newline != -1 else index + 1
    return line, column


def _desserializar_lista_caracteres(conteudo, nome_arquivo):
    """Reconstrói o fluxo real de caracteres produzido por 1-conversor.py."""
    try:
        lista_caracteres = ast.literal_eval(conteudo)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(
            f"'{nome_arquivo}' não contém uma lista de caracteres válida"
        ) from exc

    if not isinstance(lista_caracteres, list):
        raise ValueError(
            f"'{nome_arquivo}' deveria conter uma lista, "
            f"mas contém {type(lista_caracteres).__name__}"
        )

    for index, caractere in enumerate(lista_caracteres):
        if not isinstance(caractere, str) or len(caractere) != 1:
            raise ValueError(
                "elemento inválido na lista de caracteres "
                f"(índice {index}): {caractere!r}"
            )

    return "".join(lista_caracteres)


def ler_arquivo(nome_arquivo):
    """
    Lê uma entrada e devolve o fluxo de caracteres que o lexer deve analisar.

    .nfs         -> código-fonte textual.
    .char / .o   -> lista serializada de caracteres, desserializada primeiro.

    O lexer nunca tokeniza a representação Python da lista; ele recebe de volta
    exatamente os caracteres do programa que aquela lista representa.
    """
    path = Path(nome_arquivo)

    try:
        conteudo = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Erro: Arquivo '{nome_arquivo}' não encontrado.", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Erro ao ler arquivo: {exc}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()

    if suffix in CHARACTER_LIST_SUFFIXES:
        try:
            codigo = _desserializar_lista_caracteres(conteudo, nome_arquivo)
        except ValueError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            sys.exit(1)

        print(
            f"Arquivo '{nome_arquivo}' interpretado como lista de caracteres.",
            file=sys.stderr,
        )
        return codigo

    # Compatibilidade didática: formatos desconhecidos ainda podem ser tratados
    # como texto puro. Quando a linguagem exigir contratos rígidos de extensão,
    # este é o único ponto que precisa ser endurecido.
    return conteudo


# =============================================================================
# TOKENIZAÇÃO
# =============================================================================


def _token_type(kind, value):
    """Converte o grupo regex no tipo final do token."""
    if kind == "IDENT":
        # Palavras-chave são reconhecidas como identificadores lexicais e então
        # reclassificadas pelo lexema. Isso evita que "falante" vire "falar" + ...
        return KEYWORDS.get(value, "TokenIdentifier")

    return TOKEN_MAP.get(kind, kind)


def tokenize(code):
    """
    Analisa o fluxo inteiro e retorna tuplas:
        (tipo, lexema, linha, coluna)

    Além dos matches, verifica os intervalos ENTRE eles. Assim, caracteres que
    nenhum padrão reconhece geram erro léxico em vez de sumirem silenciosamente.
    """
    tokens = []
    cursor = 0

    for match in REGEX.finditer(code):
        start = match.start()

        if start != cursor:
            fragment = code[cursor:start]
            line, column = _posicao(code, cursor)
            raise LexicalError(
                "caractere ou sequência não reconhecida",
                line,
                column,
                fragment,
            )

        kind = match.lastgroup
        value = match.group()

        if kind not in ("COMMENT", "WHITESPACE"):
            line, column = _posicao(code, start)
            tokens.append((_token_type(kind, value), value, line, column))

        cursor = match.end()

    if cursor != len(code):
        fragment = code[cursor:]
        line, column = _posicao(code, cursor)
        raise LexicalError(
            "caractere ou sequência não reconhecida",
            line,
            column,
            fragment,
        )

    return tokens


# =============================================================================
# SAÍDA
# =============================================================================


def formatar_tokens(tokens):
    """Serializa tokens em .tkn usando repr() para preservar o lexema."""
    linhas = []
    for token_type, value, _, _ in tokens:
        linhas.append(f"{token_type}: {value!r}")
    return "\n".join(linhas)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Lexer visual da Neftys. Aceita código textual (.nfs) ou uma "
            "lista serializada de caracteres (.char/.o)."
        )
    )
    parser.add_argument("arquivo", help="Arquivo de entrada (.nfs, .char ou .o)")
    parser.add_argument(
        "--o",
        dest="saida",
        help="Arquivo de saída para tokens (ex: programa.tkn).",
    )
    parser.add_argument(
        "--detalhado",
        action="store_true",
        help="Exibe tokens completos (tipo, valor, linha, coluna).",
    )
    args = parser.parse_args()

    codigo = ler_arquivo(args.arquivo)

    try:
        tokens = tokenize(codigo)
    except LexicalError as exc:
        print(f"Erro léxico: {exc}", file=sys.stderr)
        return 1

    if args.detalhado:
        saida = "\n".join(str(token) for token in tokens)
    else:
        saida = formatar_tokens(tokens)

    if args.saida:
        try:
            Path(args.saida).write_text(
                saida + ("\n" if saida else ""),
                encoding="utf-8",
            )
            print(f"Tokens salvos em '{args.saida}'")
        except OSError as exc:
            print(f"Erro ao escrever arquivo: {exc}", file=sys.stderr)
            return 1
    else:
        print(saida)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
