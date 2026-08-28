# Pipeline demonstrativo da Neftys

`src/py/` é uma bancada visual, não a implementação de referência. A implementação real da Neftys será escrita em Pinker.

A gramática v1 não vive em uma etapa paralela. Ela atravessa o pipeline demonstrativo inteiro:

| Etapa | Código | Documento | Artefato principal |
|---|---|---|---|
| 1 | `src/py/1-conversor.py` | `1.codigo` | `.char` |
| 2 | `src/py/2-lexer.py` | `2.lexer` | `.tkn` |
| 3 | `src/py/3-parser.py` | `3.parser` | `.ast` |
| 4 | `src/py/4-symbol_table.py` | `4.analise-estatica` | `.sem` + `.sym` |
| 5 | `src/py/5-ir.py` | `4.ir` | `.ir` |
| 6 | `src/py/6-otimizador.py` | `5.otimização` | `.ir` otimizada |
| 7 | `src/py/7-codegen.py` | `6.geracao-de-codigo` | `.bc` |
| 8 | `src/py/8-vm.py` | `7.vm` | execução observável |
| 9 | `src/py/9-runtime.py` | `8.runtime` | serviços de runtime |

`10-gramatica.py` é apenas um inspetor agregado das etapas 2–4. Ele usa a mesma implementação compartilhada em `src/py/neftys_v1/`; não é outra Neftys escondida num subdiretório.
