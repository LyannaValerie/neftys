#!/usr/bin/env python3
import sys
import os
import argparse

def converter_arquivo_para_lista(nome_arquivo):
    """
    Lê um arquivo e retorna a lista de caracteres.
    """
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            conteudo = arquivo.read()
            return list(conteudo)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return None

def formatar_lista(lista_caracteres):
    """
    Formata a lista de caracteres como uma representação Python (string).
    """
    return repr(lista_caracteres)

def main():
    parser = argparse.ArgumentParser(
        description="Converte um arquivo para uma lista de caracteres (como ['c', 'o', 'n', ...])."
    )
    parser.add_argument('arquivo', help="Arquivo de entrada (ex: ponto_medio.nfs)")
    parser.add_argument('--o', dest='saida', help="Arquivo de saída (ex: char.o). Se omitido, imprime na tela.")
    parser.add_argument('--estatisticas', action='store_true', help="Exibe estatísticas (total, espaços, etc.)")
    
    args = parser.parse_args()
    
    # Verifica se o arquivo de entrada existe
    if not os.path.exists(args.arquivo):
        print(f"Erro: Arquivo '{args.arquivo}' não encontrado.")
        sys.exit(1)
    
    # Converte
    lista = converter_arquivo_para_lista(args.arquivo)
    if lista is None:
        sys.exit(1)
    
    # Formata a lista
    saida_str = formatar_lista(lista)
    
    # Se for especificado arquivo de saída, escreve nele
    if args.saida:
        try:
            with open(args.saida, 'w', encoding='utf-8') as f:
                f.write(saida_str)
            print(f"Lista salva em '{args.saida}'")
        except Exception as e:
            print(f"Erro ao escrever arquivo de saída: {e}")
            sys.exit(1)
    else:
        # Senão, imprime na tela
        print("Lista de caracteres:")
        print(saida_str)
    
    # Estatísticas (opcional)
    if args.estatisticas:
        espacos = lista.count(' ')
        quebras = lista.count('\n')
        tabs = lista.count('\t')
        print(f"\nEstatísticas:")
        print(f"Total: {len(lista)} caracteres")
        print(f"Espaços: {espacos}")
        print(f"Quebras de linha: {quebras}")
        print(f"Tabulações: {tabs}")

if __name__ == "__main__":
    main()
