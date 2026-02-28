from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import time

app = Flask(__name__)

def is_internal(base_url, target_url):
    """Verifica se o link pertence ao mesmo domínio do site original."""
    return urlparse(base_url).netloc == urlparse(target_url).netloc

@app.route('/raspar', methods=['POST'])
def raspar():
    data = request.get_json()
    url_inicial = data.get('url')
    
    if not url_inicial:
        return jsonify({"erro": "Nenhuma URL fornecida"}), 400

    urls_para_visitar = {url_inicial}
    urls_visitadas = set()
    resultados = []
    limite_paginas = 10  # Define o máximo de páginas internas a navegar

    try:
        while urls_para_visitar and len(urls_visitadas) < limite_paginas:
            url = urls_para_visitar.pop()
            if url in urls_visitadas:
                continue
            
            # Pausa de 1 segundo para evitar bloqueios por excesso de acessos
            time.sleep(1)
            
            # Faz a requisição simulando um navegador real
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            urls_visitadas.add(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Limpeza: remove elementos que poluem o texto
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()

                # Extração Inteligente: mantém estrutura de títulos e parágrafos
                elementos = soup.find_all(['h1', 'h2', 'h3', 'p'])
                texto_formatado = ""
                
                for el in elementos:
                    if el.name == 'h1':
                        texto_formatado += f"\n\n# {el.get_text(strip=True).upper()}\n"
                    elif el.name in ['h2', 'h3']:
                        texto_formatado += f"\n\n## {el.get_text(strip=True)}\n"
                    else:
                        conteudo_p = el.get_text(strip=True)
                        if len(conteudo_p) > 20: # Ignora textos muito curtos/fragmentos
                            texto_formatado += f"\n{conteudo_p}\n"

                # Adiciona aos resultados
                resultados.append({
                    "url": url,
                    "titulo": soup.title.string.strip() if soup.title else "Sem título",
                    "texto": texto_formatado[:10000] # Limite para não exceder memória
                })

                # Procura novos links internos para continuar a navegar
                for a in soup.find_all('a', href=True):
                    link_completo = urljoin(url, a['href'])
                    # Remove fragmentos (#) da URL para não repetir a mesma página
                    link_limpo = link_completo.split('#')[0]
                    if is_internal(url_inicial, link_limpo) and link_limpo not in urls_visitadas:
                        urls_para_visitar.add(link_limpo)

        return jsonify({"dados": resultados})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    # O servidor corre na porta 80 para o Easypanel
    app.run(host='0.0.0.0', port=80)
