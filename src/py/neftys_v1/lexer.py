from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .diagnostics import Diagnostic, NeftysError, erro_lexico

@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    value: Any
    line: int
    column: int
    escaped: bool = False

    def short(self) -> str:
        shown = repr(self.lexeme)
        return f"{self.kind:<14} {shown:<22} @ {self.line}:{self.column}"


KEYWORDS = {
    "fale": "FALE",
    "Ver": "VER",
    "Fal": "FAL",
    "SV": "SV",
    "e": "AND",
    "ou": "OR",
    "diff": "NE",
    "se": "SE",
    "então": "ENTAO",
    "senão": "SENAO",
    "enquanto": "ENQUANTO",
    "faça": "FACA",
    "para": "PARA",
    "em": "EM",
    "fun": "FUN",
    "retorne": "RETORNE",
    "class": "CLASS",
    "herda": "HERDA",
    "esse": "ESSE",
    "sup": "SUP",
    "pare": "PARE",
    "continue": "CONTINUE",
}

SIMPLE = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    "!": "BANG",
    "<": "LT",
    ">": "GT",
    "=": "ASSIGN",
    "(": "LPAREN",
    ")": "RPAREN",
    ",": "COMMA",
    ".": "DOT",
}

COMPOSITE = {
    "==": "EQ",
    "!=": "NE",
    "<=": "LE",
    ">=": "GE",
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self.indents = [0]
        self.paren_depth = 0

    def tokenize(self) -> list[Token]:
        if "\t" in self.source:
            idx = self.source.index("\t")
            line = self.source.count("\n", 0, idx) + 1
            last = self.source.rfind("\n", 0, idx)
            col = idx - last if last >= 0 else idx + 1
            erro_lexico(
                "NFS-E101",
                "Aff... tabulação em bloco? Escolhe uma tragédia por vez. A Neftys usa espaços para indentação.",
                line,
                col,
                "substitua a tabulação por espaços; quatro espaços são a convenção recomendada.",
            )

        lines = self.source.splitlines()
        for line_no, raw in enumerate(lines, 1):
            self._tokenize_line(raw, line_no)

        # Se o arquivo termina dentro de parênteses, a origem está incompleta.
        if self.paren_depth != 0:
            line = len(lines) if lines else 1
            col = len(lines[-1]) + 1 if lines else 1
            erro_lexico(
                "NFS-E102",
                "Aff... abriu '(' e decidiu abandonar a obra no meio.",
                line,
                col,
                "feche o grupo com ')'.",
            )

        while len(self.indents) > 1:
            self.indents.pop()
            self.tokens.append(Token("DEDENT", "", None, len(lines) + 1, 1))
        self.tokens.append(Token("EOF", "", None, len(lines) + 1, 1))
        return self.tokens

    def _tokenize_line(self, raw: str, line_no: int) -> None:
        leading = len(raw) - len(raw.lstrip(" "))
        content = raw[leading:]

        # Linhas vazias ou somente comentário não mexem na pilha de blocos.
        if not content or content.startswith("#"):
            return

        if self.paren_depth == 0:
            self._handle_indent(leading, line_no)

        i = leading
        n = len(raw)
        while i < n:
            ch = raw[i]
            col = i + 1

            if ch == " ":
                i += 1
                continue
            if ch == "#":
                break
            if ch == ";":
                erro_lexico(
                    "NFS-E103",
                    "Aff... isso aqui não é C. Esse ';' está sobrando e ele sabe disso.",
                    line_no,
                    col,
                    "remova o ';'; a quebra de linha encerra a instrução.",
                )
            if ch == ":":
                erro_lexico(
                    "NFS-E104",
                    "Aff... dois-pontos não abrem bloco na Neftys.",
                    line_no,
                    col,
                    "termine o cabeçalho com 'então' ou 'faça', quando a construção pedir isso.",
                )

            pair = raw[i:i + 2]
            if pair in {"<<", ">>"}:
                wanted = "<=" if pair == "<<" else ">="
                erro_lexico(
                    "NFS-E105",
                    f"Aff... '{pair}' não significa comparação inclusiva aqui.",
                    line_no,
                    col,
                    f"use '{wanted}'. '{pair}' fica reservado para um possível deslocamento de bits futuro.",
                )
            if pair in COMPOSITE:
                self.tokens.append(Token(COMPOSITE[pair], pair, pair, line_no, col))
                i += 2
                continue

            if ch == '"':
                token, i = self._string(raw, i, line_no)
                self.tokens.append(token)
                continue

            if ch == "`":
                token, i = self._escaped_identifier(raw, i, line_no)
                self.tokens.append(token)
                continue

            if ch.isdigit():
                token, i = self._number(raw, i, line_no)
                self.tokens.append(token)
                continue

            if ch == "_" or ch.isalpha():
                start = i
                i += 1
                while i < n and (raw[i] == "_" or raw[i].isalnum()):
                    i += 1
                lexeme = raw[start:i]
                kind = KEYWORDS.get(lexeme, "IDENT")
                value: Any = lexeme
                if kind == "VER":
                    value = True
                elif kind == "FAL":
                    value = False
                elif kind == "SV":
                    value = None
                self.tokens.append(Token(kind, lexeme, value, line_no, start + 1))
                continue

            if ch in SIMPLE:
                kind = SIMPLE[ch]
                self.tokens.append(Token(kind, ch, ch, line_no, col))
                if kind == "LPAREN":
                    self.paren_depth += 1
                elif kind == "RPAREN":
                    self.paren_depth -= 1
                    if self.paren_depth < 0:
                        erro_lexico(
                            "NFS-E106",
                            "Aff... apareceu ')' sem nenhum '(' para justificar a existência dele.",
                            line_no,
                            col,
                            "remova ')' ou abra o grupo correspondente antes dele.",
                        )
                i += 1
                continue

            erro_lexico(
                "NFS-E107",
                f"Aff... nem eu sei o que fazer com {ch!r} aqui.",
                line_no,
                col,
                "remova o caractere ou use um token válido da gramática.",
            )

        if self.paren_depth == 0:
            self.tokens.append(Token("NEWLINE", "\\n", None, line_no, n + 1))

    def _handle_indent(self, width: int, line: int) -> None:
        current = self.indents[-1]
        if width > current:
            self.indents.append(width)
            self.tokens.append(Token("INDENT", " " * width, width, line, 1))
            return
        if width == current:
            return

        while len(self.indents) > 1 and width < self.indents[-1]:
            self.indents.pop()
            self.tokens.append(Token("DEDENT", "", width, line, 1))
        if width != self.indents[-1]:
            erro_lexico(
                "NFS-E108",
                "Aff... esse bloco voltou para uma coluna que nunca existiu. Nem a indentação sabe onde mora.",
                line,
                1,
                f"alinhe a linha com um nível já aberto: {self.indents}.",
            )

    def _number(self, raw: str, start: int, line: int) -> tuple[Token, int]:
        i = start
        while i < len(raw) and raw[i].isdigit():
            i += 1

        is_real = False
        if i < len(raw) and raw[i] == ".":
            if i + 1 < len(raw) and raw[i + 1].isdigit():
                is_real = True
                i += 1
                while i < len(raw) and raw[i].isdigit():
                    i += 1
                if i < len(raw) and raw[i] == "." and i + 1 < len(raw) and raw[i + 1].isdigit():
                    erro_lexico(
                        "NFS-E109",
                        "Aff... sabe nem escrever um ponto flutuante direito? Um número só precisa de um ponto decimal.",
                        line,
                        start + 1,
                        "por exemplo: 3.14",
                    )
            elif i + 1 == len(raw) or raw[i + 1] in " #,+-*/()<>=!":
                erro_lexico(
                    "NFS-E110",
                    "Aff... sabe nem escrever um ponto flutuante direito? Faltou a parte depois do ponto.",
                    line,
                    start + 1,
                    "use algo como 1.0, ou escreva 1 se queria um inteiro.",
                )

        if i < len(raw) and (raw[i].isalpha() or raw[i] == "_"):
            erro_lexico(
                "NFS-E111",
                "Aff... sabe nem escrever um inteiro direito? Número e nome grudados não viram uma coisa só por amizade.",
                line,
                start + 1,
                "use 123 para um inteiro; para um nome, comece com letra/_ ou escape-o com crases, como `123`.",
            )

        lexeme = raw[start:i]
        if is_real:
            return Token("REAL", lexeme, float(lexeme), line, start + 1), i
        return Token("INT", lexeme, int(lexeme), line, start + 1), i

    def _string(self, raw: str, start: int, line: int) -> tuple[Token, int]:
        i = start + 1
        out: list[str] = []
        escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
        while i < len(raw):
            ch = raw[i]
            if ch == '"':
                lexeme = raw[start:i + 1]
                return Token("STRING", lexeme, "".join(out), line, start + 1), i + 1
            if ch == "\\":
                if i + 1 >= len(raw):
                    break
                nxt = raw[i + 1]
                if nxt not in escapes:
                    erro_lexico(
                        "NFS-E112",
                        f"Aff... a sequência '\\{nxt}' não é uma fuga que a Neftys conheça.",
                        line,
                        i + 1,
                        r'use \\n, \\t, \\" ou \\\\.',
                    )
                out.append(escapes[nxt])
                i += 2
                continue
            out.append(ch)
            i += 1

        erro_lexico(
            "NFS-E113",
            "Aff... abriu uma string e esqueceu de fechá-la. As aspas não se reproduzem sozinhas.",
            line,
            start + 1,
            'feche a cadeia com ".',
        )
        raise AssertionError("unreachable")

    def _escaped_identifier(self, raw: str, start: int, line: int) -> tuple[Token, int]:
        end = raw.find("`", start + 1)
        if end < 0:
            erro_lexico(
                "NFS-E114",
                "Aff... abriu um identificador escapado e esqueceu da segunda crase.",
                line,
                start + 1,
                "use algo como `1`.",
            )
        value = raw[start + 1:end]
        if not value or any(c.isspace() for c in value):
            erro_lexico(
                "NFS-E115",
                "Aff... identificador escapado vazio ou com espaço não é nome, é pedido de socorro.",
                line,
                start + 1,
                "use conteúdo sem espaços, por exemplo `1` ou `nome-especial`.",
            )
        return Token("IDENT", raw[start:end + 1], value, line, start + 1, escaped=True), end + 1


