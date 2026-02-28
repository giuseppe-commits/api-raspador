from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import time

app = Flask(__name__)

def is_internal(base_url, target_url):
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
    limite_paginas = 10  # Ele vai navegar em até 10 páginas do mesmo site

    try:
        while urls_para_visitar and len(urls_visitadas) < limite_paginas:
            url = urls_para_visitar.pop()
            if url in urls_visitadas:
                continue
            
            # Pequena pausa para não ser bloqueado pelo site
            time.sleep(1)
            
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            urls_visitadas.add(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove elementos inúteis como scripts e estilos
                for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                    script_or_style.decompose()

                # Pega o texto limpo
                texto = soup.get_text(separator=' ', strip=True)
                
                resultados.append({
                    "url": url,
                    "titulo": soup.title.string if soup.title else "Sem título",
                    "texto": texto[:8000] # Limite de caracteres para o doc não ficar gigante
                })

                # Procura mais links internos para continuar navegando
                for a in soup.find_all('a', href=True):
                    link_completo = urljoin(url, a['href'])
                    if is_internal(url_inicial, link_completo) and link_completo not in urls_visitadas:
                        urls_para_visitar.add(link_completo)

        return jsonify({"dados": resultados})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
