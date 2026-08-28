# Neftys

Neftys é uma linguagem de programação em construção cujo objetivo central é tornar visíveis as transformações pelas quais um programa passa: fonte, caracteres, tokens, AST, vínculos, tipos, IR, otimização, bytecode, execução e runtime.

> “A Nefy, minha bebezinha, é meio obscura e ranzinza, mas, ela é maravilhosamente fantástica!” — Rosa

## Linguagem-mãe

Python **não** é a linguagem-mãe da Neftys. `src/py/` é uma bancada experimental para tornar o pipeline observável e testar decisões antes da implementação real.

A implementação de referência da Neftys será escrita em **Pinker**.

## Pipeline demonstrativo

A gramática v1 atravessa o pipeline numerado existente. Ela não mora isolada em `10-gramatica.py`:

```text
1-conversor.py
    ↓ .char
2-lexer.py
    ↓ .tkn
3-parser.py
    ↓ .ast
4-symbol_table.py
    ↓ .sem / .sym
5-ir.py
    ↓ .ir
6-otimizador.py
    ↓ .ir otimizada
7-codegen.py
    ↓ .bc
8-vm.py
    ↔ 9-runtime.py
```

`src/py/neftys_v1/` contém código compartilhado por essas etapas para impedir que cada script desenvolva uma gramática própria. `10-gramatica.py` é apenas um inspetor agregado das etapas de front-end.

Veja `docs/1/README.md` para o mapa entre código e documentação e `docs/1/10.gramatica-v1` para o contrato atual da linguagem.
