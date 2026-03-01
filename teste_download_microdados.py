import os
import sys
import requests
from urllib.parse import urlparse, unquote

def baixar_arquivo(url, pasta_destino="."):
    # Cria a pasta se não existir
    os.makedirs(pasta_destino, exist_ok=True)

    # Tenta pegar o nome do arquivo pela URL
    nome_arquivo = os.path.basename(urlparse(url).path)
    nome_arquivo = unquote(nome_arquivo) or "arquivo_baixado"

    caminho_saida = os.path.join(pasta_destino, nome_arquivo)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()

        total_bytes = int(r.headers.get("Content-Length", 0))
        baixado_bytes = 0
        chunk_size = 8192

        print(f"\nBaixando: {nome_arquivo}")

        with open(caminho_saida, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue

                f.write(chunk)
                baixado_bytes += len(chunk)

                if total_bytes > 0:
                    percentual = (baixado_bytes / total_bytes) * 100
                    mb_baixado = baixado_bytes / (1024 * 1024)
                    mb_total = total_bytes / (1024 * 1024)

                    # \r atualiza a mesma linha em tempo real
                    sys.stdout.write(
                        f"\rProgresso: {percentual:6.2f}% "
                        f"({mb_baixado:,.2f} MB / {mb_total:,.2f} MB)"
                    )
                    sys.stdout.flush()
                else:
                    # Caso o servidor não envie Content-Length
                    mb_baixado = baixado_bytes / (1024 * 1024)
                    sys.stdout.write(f"\rBaixado: {mb_baixado:,.2f} MB")
                    sys.stdout.flush()

        print("\nDownload concluído!")

    return caminho_saida


for i in range(2009, 2010):
    url = f"https://download.inep.gov.br/microdados/microdados_enem_{i}.zip"
    try:
        caminho = baixar_arquivo(url, pasta_destino="downloads")
        print(f"Arquivo salvo em: {caminho}")
    except requests.HTTPError as e:
        print(f"\nErro HTTP ao baixar {url}: {e}")
    except requests.RequestException as e:
        print(f"\nErro de conexão ao baixar {url}: {e}")