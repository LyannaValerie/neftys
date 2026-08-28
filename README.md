# Neftys

Neftys é uma linguagem de programação em construção cujo objetivo central é tornar visíveis as transformações pelas quais um programa passa: fonte, tokens, AST, vínculos, tipos, IR, bytecode, execução e runtime.

> “A Nefy, minha bebezinha, é meio obscura e ranzinza, mas, ela é maravilhosamente fantástica!” — Rosa

## Linguagem-mãe

Python **não** é a linguagem-mãe da Neftys. O conteúdo em `src/py/` é uma bancada experimental para estudar e visualizar o pipeline antes de cristalizar a implementação real.

A implementação de referência da Neftys será escrita em **Pinker**.

Consequentemente, neste repositório é importante distinguir:

- **decisão da linguagem**: contrato que queremos para a Neftys;
- **confirmado no experimento Python**: comportamento atualmente exercitável em `src/py/`;
- **implementação futura em Pinker**: ainda não existe como implementação de referência;
- **proposta**: ideia ainda não incorporada ao contrato.

## Pipeline didático

Os scripts históricos `src/py/1-*` a `src/py/9-*` formam o primeiro experimento visual. A documentação correspondente vive em `docs/1/`.

A gramática nova começa em `src/py/10-gramatica.py` e no pacote `src/py/neftys_v1/`. Ela não substitui silenciosamente o experimento histórico: é uma nova fronteira para testar o desenho atual da linguagem.

Consulte:

- `docs/1/README.md` para o mapa exato entre documentação e scripts;
- `docs/1/10.gramatica-v1` para o contrato sintático e semântico em evolução.

## Diagnósticos

A Neftys pode ser ranzinza, mas não pode ser vaga. Um diagnóstico deve priorizar:

1. código estável;
2. causa concreta;
3. linha e coluna quando disponíveis;
4. trecho da origem;
5. correção sugerida.

A personalidade vem depois da informação. Falhas internas devem assumir responsabilidade e nunca culpar o programa do usuário.
