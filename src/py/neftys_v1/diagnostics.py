from __future__ import annotations

from dataclasses import dataclass

@dataclass
class Diagnostic:
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    hint: str | None = None

    def render(self, source: str | None = None) -> str:
        where = ""
        if self.line is not None and self.column is not None:
            where = f" [linha {self.line}, coluna {self.column}]"
        lines = [f"{self.code}{where}", self.message]

        if source is not None and self.line is not None:
            source_lines = source.splitlines()
            if 1 <= self.line <= len(source_lines):
                text = source_lines[self.line - 1]
                width = len(str(self.line))
                lines.append(f"{' ' * width} |")
                lines.append(f"{self.line:>{width}} | {text}")
                caret_col = max(1, self.column or 1)
                lines.append(f"{' ' * width} | {' ' * (caret_col - 1)}^")

        if self.hint:
            lines.append(f"Como faz: {self.hint}")
        return "\n".join(lines)


class NeftysError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.message)


def erro_lexico(code: str, message: str, line: int, column: int, hint: str | None = None):
    raise NeftysError(Diagnostic(code, message, line, column, hint))


def nome_tipo(tipo: str) -> str:
    return {
        "Inteiro": "inteiro",
        "Real": "ponto flutuante",
        "String": "string",
        "Booleano": "booleano",
        "SV": "SV",
        "Função": "função",
        "Classe": "classe",
        "Instância": "instância",
        "Desconhecido": "valor de tipo ainda desconhecido",
    }.get(tipo, tipo.lower())


def artigo_tipo(tipo: str) -> str:
    feminino = tipo in {"String", "Função", "Classe", "Instância"}
    return ("uma " if feminino else "um ") + nome_tipo(tipo)


