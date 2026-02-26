from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

app = Flask(__name__)

@app.route('/raspar', methods=['POST'])
def raspar_site():
    # 1. Recebe a URL que o n8n enviou
    dados = request.json
    url_alvo = dados.get('url')
    
    if not url_alvo:
        return jsonify({"erro": "Nenhuma URL fornecida. Envie um JSON com a chave 'url'."}), 400

    dominio_base = urlparse(url_alvo).netloc
    visitados = set()
    fila = [url_alvo]
    resultados = []

    # TRAVA DE SEGURANÇA: Servidores gratuitos na nuvem (como Render) costumam derrubar
    # conexões que demoram mais de 1 ou 2 minutos. 
    # Limitamos a 15 páginas por vez para garantir que o n8n receba a resposta a tempo.
    limite_paginas = 15 

    # 2. O Loop de Raspagem (Crawling)
    while fila and len(visitados) < limite_paginas:
        url_atual = fila.pop(0)
        
        if url_atual in visitados:
            continue
            
        visitados.add(url_atual)
        
        try:
            resposta = requests.get(url_atual, timeout=10)
            sopa = BeautifulSoup(resposta.text, 'html.parser')
            
            # Puxa o título e os textos
            titulo = sopa.title.string if sopa.title else 'Sem título'
            paragrafos = [p.text for p in sopa.find_all('p')]
            texto_puro = ' '.join(paragrafos).strip()
            
            if titulo or texto_puro:
                resultados.append({
                    "url": url_atual,
                    "titulo": titulo.strip() if titulo else 'Sem título',
                    "texto": texto_puro
                })
            
            # 3. Acha novos links e coloca na fila
            for link in sopa.find_all('a', href=True):
                link_completo = urljoin(url_alvo, link['href'])
                # Só adiciona se for do mesmo domínio e se já não foi visitado
                if dominio_base in urlparse(link_completo).netloc and link_completo not in visitados:
                    fila.append(link_completo)
                    
        except Exception as e:
            print(f"Erro ao acessar {url_atual}: {e}")

    # 4. Devolve tudo para o n8n em formato JSON
    return jsonify({"dados": resultados})

if __name__ == '__main__':
    # A porta 10000 é o padrão de muitos serviços em nuvem
    app.run(host='0.0.0.0', port=10000)
