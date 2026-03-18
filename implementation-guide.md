
---

## 6. `implementation-guide.md` — Guia de Implementação Passo a Passo

```markdown
# Guia de Implementação Passo a Passo
## Checklist Técnico para Equipe

---

## Fase 1: Setup Inicial (Dia 1-2)

### 1.1 Infraestrutura Base
```bash
# docker-compose.yml básico
mkdir radar-pipeline && cd radar-pipeline

Arquivo docker-compose.yml:
version: '3.8'
services:
  mongodb:
    image: mongo:6-jammy
    ports: ["27017:27017"]
    environment:
      MONGO_INITDB_DATABASE: radar_combustivel
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

volumes:
  mongo_data:

  Comandos:
  docker-compose up -d

  radar-pipeline/
├── docker-compose.yml
├── data_generator/          # Simulador de carga
│   ├── generator.py
│   └── postos_seed.json   # Dados fake de postos
├── pipeline/                # Processador principal
│   ├── main.py
│   ├── processors.py
│   └── state_manager.py
├── frontend/                # Streamlit
│   ├── app.py
│   ├── pages/
│   │   ├── 1_mapa.py
│   │   ├── 2_rankings.py
│   │   └── 3_tendencias.py
│   └── services/
│       └── redis_service.py
└── docs/                    # Diagramas para o PDF
    └── arquitetura.png

1.3 Seed de Dados (MongoDB)
Criar script data_generator/seed_mongo.py para inserir 20-30 postos fictícios em São Paulo (coordenadas reais de bairros variados).
Script template:
from pymongo import MongoClient
import random

postos = [
    {"posto_id": "P001", "nome": "Posto Ipiranga Centro", "bairro": "centro", 
     "localizacao": {"type": "Point", "coordinates": [-46.6333, -23.5505]}, 
     "bandeira": "ipiranga"},
    # ... mais 20
]

client = MongoClient("mongodb://localhost:27017")
db = client.radar_combustivel
db.postos.insert_many(postos)

Fase 2: Pipeline Core (Dia 3-5)
2.1 Implementar Change Stream (Processor Base)
pipeline/main.py:

from pymongo import MongoClient
import redis
import time
from processors import PriceProcessor

def main():
    mongo = MongoClient()
    db = mongo.radar_combustivel
    cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    processor = PriceProcessor(cache)
    
    # Resume token para continuidade
    state = db.pipeline_state.find_one({"_id": "main"})
    resume_after = state.get("resume_token") if state else None
    
    with db.watch([{"$match": {"ns.coll": "precos_historico"}}], 
                  resume_after=resume_after) as stream:
        for change in stream:
            try:
                processor.handle(change['fullDocument'])
                # Checkpoint a cada 10 eventos
                if processor.count % 10 == 0:
                    db.pipeline_state.update_one(
                        {"_id": "main"},
                        {"$set": {"resume_token": stream.resume_token, 
                                  "ts": datetime.utcnow()}},
                        upsert=True
                    )
            except Exception as e:
                print(f"Erro processando: {e}")
                # Salvar em dead letter
                db.eventos_falhos.insert_one({
                    "evento": change, "erro": str(e), "ts": datetime.utcnow()
                })

if __name__ == "__main__":
    main()

2.2 Implementar Processadores Específicos
pipeline/processors.py:
Classe PriceProcessor (conforme spec em pipeline-spec.md)
Classe SearchProcessor (mais simples, apenas incrementa counters)
Teste Unitário Simples:
def test_variacao_calculo():
    cache = redis.Redis()
    p = PriceProcessor(cache)
    assert p.calcular_variacao("P001", "gasolina", 6.00, ts) == 0.0  # primeiro
    # inserir um e testar segundo...

2.3 Simulador de Eventos
data_generator/generator.py:
Loop infinito (com time.sleep(random.randint(2,5)))
Insere eventos de preço aleatórios
Insere eventos de busca aleatórios
Execução paralela:
# Terminal 1
python pipeline/main.py

# Terminal 2  
python data_generator/generator.py

# Terminal 3 (depois)
streamlit run frontend/app.py

Fase 3: Frontend Streamlit (Dia 6-7)
3.1 Camada de Serviço
Implementar frontend/services/redis_service.py com métodos:
get_postos_by_proximity(lat, lng, raio, combustivel) → usa Geo + Hash
get_cheapest_by_bairro(bairro, combustivel, n=10) → usa ZRANGE
get_price_history(posto_id, combustivel, dias=7) → usa ZRANGE na série temporal
3.2 Mapa (A complexidade visual maior)
Usar streamlit-folium:

import folium
from streamlit_folium import st_folium

m = folium.Map(location=[lat, lng], zoom_start=13)
for posto in postos:
    folium.Marker(
        [posto['lat'], posto['lng']],
        popup=f"{posto['nome']}: R${posto['preco']}",
        icon=folium.Icon(color='green' if posto['preco'] < media else 'red')
    ).add_to(m)

st_folium(m, width=700)

3.3 Validação de Dados
Verificar se dados estão fluindo:
Abrir Redis CLI: redis-cli monitor (ver comandos chegando em tempo real)
Abrir Mongo Compass: ver inserts na collection precos_historico

Fase 4: Documentação e Entrega (Dia 8)
4.1 Diagramas para PDF
Ferramentas: Draw.io, Mermaid, ou Lucidchart.
Diagramas Obrigatórios:
Arquitetura: Componentes e fluxo de dados
Modelo de Dados: Entidades MongoDB + Estruturas Redis
Fluxo do Pipeline: Diagrama de sequência (Change → Process → Redis)
4.2 Capturas de Tela
Screenshot do terminal mostrando pipeline processando eventos (com timestamps)
Screenshot do Streamlit (Mapa, Ranking, Tendência)
Screenshot do Redis Insight (ou redis-cli) mostrando estruturas preenchidas
4.3 README.md do Repositório
Deve conter:
Nomes dos integrantes e grupo
Comandos exatos para rodar: docker-compose up -d, pip install -r requirements.txt, etc.
Descrição das estruturas Redis usadas e por quê (copiar de data-model.md)
Link para o vídeo de demonstração (se houver)
4.4 PDF Final
Organização sugerida:
Capa (nome grupo, disciplina, data)
Sumário
Descrição do Problema (Radar Combustível)
Arquitetura Proposta (com diagrama)
Modelagem de Dados (Mongo + Redis)
Implementação do Pipeline (código explicado, fluxo)
Visualizações (prints das telas Streamlit)
Conclusão (desafios encontrados, aprendizados)
Referências / GitHub
Checklist Final de Validação
Antes de entregar, verificar:
[ ] docker-compose up sobe tudo sem erros
[ ] Simulador gera dados e pipeline processa (ver logs)
[ ] Streamlit abre na porta 8501 sem crash
[ ] Consultas no Streamlit respondem em <2s (Redis funcionando)
[ ] PDF contém todos os elementos obrigatórios (diagrama, prints, nomes)
[ ] Repositório GitHub está público (ou acesso concedido ao professor)
[ ] Código tem requirements.txt ou Pipfile claro
[ ] Justificativa das estruturas Redis está escrita (ex: "Usamos Sorted Set para ranking porque O(log N) para inserção e range queries nativas...")