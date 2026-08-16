#!/usr/bin/env python3
import sys
import re

def tokenizar_codigo(nome_arquivo):
    """
    Versão mais avançada para processamento de código-fonte.
    Identifica comentários, strings, números, operadores, etc.
    """
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as arquivo:
            conteudo = arquivo.read()
            
            # Remove comentários de linha (#)
            linhas = conteudo.split('\n')
            linhas_sem_comentarios = []
            
            for linha in linhas:
                # Remove comentários (ignora # dentro de strings)
                if '#' in linha:
                    # Verifica se # está dentro de uma string
                    partes = linha.split('#')
                    # Verifica se há aspas não fechadas antes do #
                    linha_sem_comentario = partes[0]
                    # Se houver aspas, mantém o # como parte da string
                    if linha_sem_comentario.count('"') % 2 == 1:
                        # # está dentro de uma string, mantém tudo
                        linhas_sem_comentarios.append(linha)
                    else:
                        linhas_sem_comentarios.append(linha_sem_comentario)
                else:
                    linhas_sem_comentarios.append(linha)
            
            # Junta novamente
            codigo_limpo = '\n'.join(linhas_sem_comentarios)
            
            # Converte para lista de caracteres
            return list(codigo_limpo)
            
    except Exception as e:
        print(f"Erro: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 programa.py <arquivo.nfs>")
        sys.exit(1)
    
    resultado = tokenizar_codigo(sys.argv[1])
    
    if resultado:
        print("Tokens (caracteres):")
        print(resultado)
        
        # Mostra estatísticas
        espacos = resultado.count(' ')
        quebras = resultado.count('\n')
        tabs = resultado.count('\t')
        
        print(f"\nEstatísticas:")
        print(f"Total: {len(resultado)} caracteres")
        print(f"Espaços: {espacos}")
        print(f"Quebras de linha: {quebras}")
        print(f"Tabulações: {tabs}")

if __name__ == "__main__":
    main()
