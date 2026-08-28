# Experimento 1 — mapa entre documentação e código

Este diretório documenta o primeiro pipeline visual da Neftys. Os nomes históricos foram preservados para não apagar a evolução do projeto.

## Regra de sincronização

Sempre que uma etapa experimental em `src/py/` ganhar comportamento observável novo, a documentação correspondente em `docs/1/` deve ser atualizada no mesmo recorte de trabalho.

Documentação não deve afirmar como implementado aquilo que existe apenas como intenção. Use estas categorias:

- **confirmado no experimento**;
- **documentado como decisão da linguagem**;
- **proposta**;
- **futuro em Pinker**.

## Mapa atual

| Código | Documento | Estado |
| --- | --- | --- |
| `src/py/1-conversor.py` | `docs/1/1.codigo` | histórico |
| `src/py/2-lexer.py` | `docs/1/2.lexer` | histórico |
| `src/py/3-parser.py` | `docs/1/3.parser` | histórico |
| `src/py/4-symbol_table.py` | `docs/1/4.analise-estatica` | sincronizado nesta revisão |
| `src/py/5-ir.py` | `docs/1/4.ir` | nome histórico preservado |
| `src/py/6-otimizador.py` | `docs/1/5.otimização` | nome histórico preservado |
| `src/py/7-codegen.py` | `docs/1/6.geracao-de-codigo` | nome histórico preservado |
| `src/py/8-vm.py` | `docs/1/7.vm` | nome histórico preservado |
| `src/py/9-runtime.py` | `docs/1/8.runtime` | nome histórico preservado |
| `src/py/10-gramatica.py` + `src/py/neftys_v1/` | `docs/1/10.gramatica-v1` | gramática atual experimental |

A numeração deslocada a partir da análise estática é um artefato histórico, não uma declaração de que a etapa não existe.

## Python e Pinker

`src/py/` é uma bancada didática e experimental. Python serve para tornar as transformações visíveis e permitir testes baratos da linguagem enquanto a gramática amadurece.

A implementação real da Neftys será em Pinker. Nenhum detalhe acidental da implementação Python deve ser promovido automaticamente a semântica da linguagem.
