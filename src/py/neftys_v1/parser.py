from __future__ import annotations

from .ast import Node
from .diagnostics import Diagnostic, NeftysError
from .lexer import Token

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def check(self, *kinds: str) -> bool:
        return self.current.kind in kinds

    def advance(self) -> Token:
        token = self.current
        if token.kind != "EOF":
            self.pos += 1
        return token

    def match(self, *kinds: str) -> Token | None:
        if self.check(*kinds):
            return self.advance()
        return None

    def expect(self, kind: str, message: str, hint: str | None = None) -> Token:
        if self.check(kind):
            return self.advance()
        t = self.current
        raise NeftysError(Diagnostic("NFS-E201", message, t.line, t.column, hint))

    def parse(self) -> Node:
        statements: list[Node] = []
        self._skip_newlines()
        while not self.check("EOF"):
            if self.check("DEDENT"):
                t = self.current
                raise NeftysError(Diagnostic(
                    "NFS-E202",
                    "Aff... apareceu o fim de um bloco sem ninguém ter pedido por ele.",
                    t.line,
                    t.column,
                    "alinhe a instrução com o bloco correto.",
                ))
            statements.append(self.statement())
            self._skip_newlines()
        return Node("Programa", {"instruções": statements})

    def _skip_newlines(self) -> None:
        while self.match("NEWLINE"):
            pass

    def _finish_simple(self) -> None:
        if self.match("NEWLINE"):
            return
        if self.check("EOF", "DEDENT"):
            return
        t = self.current
        raise NeftysError(Diagnostic(
            "NFS-E203",
            "Aff... tem coisa demais nessa linha e nenhuma regra para juntar tudo isso.",
            t.line,
            t.column,
            "encerre a instrução aqui ou use a construção sintática apropriada.",
        ))

    def statement(self) -> Node:
        if self.match("FALE"):
            node = self.fale_statement(self.tokens[self.pos - 1])
            self._finish_simple()
            return node
        if self.match("SE"):
            return self.se_statement(self.tokens[self.pos - 1])
        if self.match("ENQUANTO"):
            return self.enquanto_statement(self.tokens[self.pos - 1])
        if self.match("PARA"):
            return self.para_statement(self.tokens[self.pos - 1])
        if self.match("FUN"):
            return self.fun_statement(self.tokens[self.pos - 1])
        if self.match("CLASS"):
            return self.class_statement(self.tokens[self.pos - 1])
        if self.match("RETORNE"):
            token = self.tokens[self.pos - 1]
            expr = None if self.check("NEWLINE", "EOF", "DEDENT") else self.expression()
            node = Node("Retorne", {"valor": expr}, token)
            self._finish_simple()
            return node
        if self.match("PARE"):
            token = self.tokens[self.pos - 1]
            self._finish_simple()
            return Node("Pare", {}, token)
        if self.match("CONTINUE"):
            token = self.tokens[self.pos - 1]
            self._finish_simple()
            return Node("Continue", {}, token)

        expr = self.expression()
        if self.match("ASSIGN"):
            eq = self.tokens[self.pos - 1]
            if expr.kind not in {"Nome", "Campo"}:
                hint = "use `1` = 2 se você realmente quer um identificador chamado '1'." if expr.kind == "Inteiro" else "atribua apenas a um nome ou campo."
                raise NeftysError(Diagnostic(
                    "NFS-E204",
                    "Aff... o lado esquerdo de '=' precisa ser um nome ou campo, não um valor pronto.",
                    eq.line,
                    eq.column,
                    hint,
                ))
            value = self.expression()
            node = Node("Atribuição", {"alvo": expr, "valor": value}, eq)
            self._finish_simple()
            return node

        node = Node("Expressão", {"valor": expr}, expr.token)
        self._finish_simple()
        return node

    def block(self) -> list[Node]:
        self.expect(
            "NEWLINE",
            "Aff... o corpo de um bloco começa na linha seguinte.",
            "quebre a linha e indente as instruções do bloco.",
        )
        self.expect(
            "INDENT",
            "Aff... cadê o bloco? A Neftys não adivinha indentação por telepatia.",
            "indente pelo menos uma instrução abaixo do cabeçalho.",
        )
        statements: list[Node] = []
        self._skip_newlines()
        while not self.check("DEDENT", "EOF"):
            statements.append(self.statement())
            self._skip_newlines()
        self.expect("DEDENT", "Aff... esse bloco chegou ao fim do arquivo sem fechar direito.")
        return statements

    def fale_statement(self, token: Token) -> Node:
        args: list[Node] = []
        if not self.check("NEWLINE", "EOF", "DEDENT"):
            args.append(self.expression())
            while self.match("COMMA"):
                args.append(self.expression())
        return Node("Fale", {"argumentos": args}, token)

    def se_statement(self, token: Token) -> Node:
        condition = self.expression()
        self.expect(
            "ENTAO",
            "Aff... um 'se' sem 'então' é só uma suspeita, não uma instrução.",
            "escreva: se <condição> então",
        )
        body = self.block()
        branches: list[Node] = [Node("RamoSe", {"condição": condition, "corpo": body}, token)]
        else_body: list[Node] | None = None

        if self.match("SENAO"):
            sen = self.tokens[self.pos - 1]
            if self.match("SE"):
                while True:
                    cond = self.expression()
                    self.expect("ENTAO", "Aff... 'senão se' também precisa terminar em 'então'.")
                    branches.append(Node("RamoSenãoSe", {"condição": cond, "corpo": self.block()}, sen))
                    if not self.match("SENAO"):
                        break
                    sen = self.tokens[self.pos - 1]
                    if not self.match("SE"):
                        else_body = self.block()
                        break
            else:
                else_body = self.block()

        return Node("Se", {"ramos": branches, "senão": else_body}, token)

    def enquanto_statement(self, token: Token) -> Node:
        condition = self.expression()
        self.expect("FACA", "Aff... 'enquanto' precisa de 'faça'.", "escreva: enquanto <condição> faça")
        return Node("Enquanto", {"condição": condition, "corpo": self.block()}, token)

    def para_statement(self, token: Token) -> Node:
        name = self.expect("IDENT", "Aff... 'para' precisa dizer qual nome recebe cada item.")
        target = Node("Nome", {"nome": name.value, "escapado": name.escaped}, name)
        self.expect("EM", "Aff... 'para' precisa de 'em' para indicar a fonte dos itens.")
        iterable = self.expression()
        self.expect("FACA", "Aff... 'para' precisa de 'faça'.", "escreva: para item em coleção faça")
        return Node("Para", {"alvo": target, "iterável": iterable, "corpo": self.block()}, token)

    def fun_statement(self, token: Token) -> Node:
        name = self.expect("IDENT", "Aff... função sem nome é um vulto, não uma declaração.")
        self.expect("LPAREN", "Aff... faltou '(' depois do nome da função.")
        params: list[Node] = []
        if not self.check("RPAREN"):
            while True:
                p = self.expect("IDENT", "Aff... parâmetro precisa ser um identificador.")
                params.append(Node("Parâmetro", {"nome": p.value, "escapado": p.escaped}, p))
                if not self.match("COMMA"):
                    break
        self.expect("RPAREN", "Aff... faltou ')' fechando os parâmetros da função.")
        return Node("Função", {"nome": name.value, "parâmetros": params, "corpo": self.block()}, token)

    def class_statement(self, token: Token) -> Node:
        name = self.expect("IDENT", "Aff... classe sem nome não encapsula nem a própria identidade.")
        superclass: Node | None = None
        if self.match("HERDA"):
            sup = self.expect("IDENT", "Aff... 'herda' precisa apontar para uma classe.")
            superclass = Node("Nome", {"nome": sup.value, "escapado": sup.escaped}, sup)
        return Node("Classe", {"nome": name.value, "superclasse": superclass, "corpo": self.block()}, token)

    # Precedência: ou < e < igualdade < comparação < +,- < *,/ < unário < pós-fixa
    def expression(self) -> Node:
        return self.logical_or()

    def logical_or(self) -> Node:
        node = self.logical_and()
        while self.match("OR"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.logical_and()}, op)
        return node

    def logical_and(self) -> Node:
        node = self.equality()
        while self.match("AND"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.equality()}, op)
        return node

    def equality(self) -> Node:
        node = self.comparison()
        while self.match("EQ", "NE"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.comparison()}, op)
        return node

    def comparison(self) -> Node:
        node = self.addition()
        while self.match("LT", "GT", "LE", "GE"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.addition()}, op)
        return node

    def addition(self) -> Node:
        node = self.multiplication()
        while self.match("PLUS", "MINUS"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.multiplication()}, op)
        return node

    def multiplication(self) -> Node:
        node = self.unary()
        while self.match("STAR", "SLASH"):
            op = self.tokens[self.pos - 1]
            node = Node("Binária", {"operador": op.lexeme, "esquerda": node, "direita": self.unary()}, op)
        return node

    def unary(self) -> Node:
        if self.match("BANG", "MINUS"):
            op = self.tokens[self.pos - 1]
            return Node("Unária", {"operador": op.lexeme, "operando": self.unary()}, op)
        if self.match("PLUS"):
            op = self.tokens[self.pos - 1]
            # Consumimos o operando para apontar o erro ao operador sem deixar o parser perdido.
            self.unary()
            raise NeftysError(Diagnostic(
                "NFS-E205",
                "A expressão '+' deve ser usada entre duas strings: CONCATENATION FAILED!",
                op.line,
                op.column,
                "use <string> + <string>; '+' unário não existe na Neftys.",
            ))
        return self.postfix()

    def postfix(self) -> Node:
        node = self.primary()
        while True:
            if self.match("LPAREN"):
                lparen = self.tokens[self.pos - 1]
                args: list[Node] = []
                if not self.check("RPAREN"):
                    while True:
                        args.append(self.expression())
                        if not self.match("COMMA"):
                            break
                self.expect("RPAREN", "Aff... chamada abriu '(' e largou os argumentos sem fechar a porta.")
                node = Node("Chamada", {"callee": node, "argumentos": args}, lparen)
                continue
            if self.match("DOT"):
                dot = self.tokens[self.pos - 1]
                name = self.expect("IDENT", "Aff... depois de '.' precisa vir o nome de um campo ou método.")
                node = Node("Campo", {"objeto": node, "nome": name.value}, dot)
                continue
            break
        return node

    def primary(self) -> Node:
        token = self.current
        if self.match("INT"):
            return Node("Inteiro", {"valor": token.value}, token)
        if self.match("REAL"):
            return Node("Real", {"valor": token.value}, token)
        if self.match("STRING"):
            return Node("String", {"valor": token.value}, token)
        if self.match("VER", "FAL"):
            return Node("Booleano", {"valor": token.value}, token)
        if self.match("SV"):
            return Node("SV", {"valor": None}, token)
        if self.match("IDENT"):
            return Node("Nome", {"nome": token.value, "escapado": token.escaped}, token)
        if self.match("ESSE"):
            return Node("Esse", {}, token)
        if self.match("SUP"):
            return Node("Sup", {}, token)
        if self.match("LPAREN"):
            expr = self.expression()
            self.expect("RPAREN", "Aff... abriu '(' e esqueceu de fechar ')'.")
            return Node("Grupo", {"expressão": expr}, token)

        raise NeftysError(Diagnostic(
            "NFS-E206",
            f"Aff... eu esperava uma expressão, mas recebi {token.lexeme!r}.",
            token.line,
            token.column,
            "comece com literal, nome, chamada, 'esse', 'sup' ou '('.",
        ))


