5. Simulador de Carga (Data Generator)
Para demonstrar o pipeline funcionando sem dados reais:
Python
Copy
# data_generator.py
def gerar_evento_preco():
    posto = random.choice(postos_cadastrados)
    combustivel = random.choice(["gasolina_comum", "etanol", "diesel_s10"])
    # Variação realista: ±2% do preço atual
    preco_base = 5.50 if combustivel == "gasolina_comum" else 4.20
    preco_novo = preco_base * random.uniform(0.98, 1.02)
    
    mongo.precos_historico.insert_one({
        "posto_id": posto["id"],
        "tipo_combustivel": combustivel,
        "preco": round(preco_novo, 3),
        "timestamp": datetime.utcnow()
    })

# Loop: inserir a cada 2-5 segundos para visualização em tempo real
Isso permite demonstrar o pipeline funcionando durante a apresentação.
plain
Copy

---

## 5. `frontend-spec.md` — Especificação da Interface (Streamlit)

```markdown
# Especificação da Interface de Visualização
## Streamlit Dashboard — Radar Combustível

---

## 1. Estrutura de Navegação
Radar Combustível Analytics
├── 📍 Mapa ao Vivo (Radar Map)
├── 📊 Rankings & Comparativos
├── 📈 Tendências e Anomalias
└── 🔍 Métricas de Uso (Heatmap)
plain
Copy

## 2. Telas/Funcionalidades Detalhadas

### 2.1 Página: "Mapa ao Vivo" (`pages/1_mapa.py`)

**Objetivo:** Visualização geográfica dos preços em tempo real.

**Layout:**
- **Sidebar:**
  - Selectbox: Tipo de combustível (Gasolina, Etanol, Diesel)
  - Slider: Raio de busca (1km - 10km)
  - Botão: "Detectar Minha Localização" (HTML5 Geolocation via componente custom)
  
- **Main:**
  - Mapa Folium centrado na coordenada do usuário
  - Marcadores coloridos por faixa de preço (verde < média, vermelho > média)
  - Popup ao clicar: Nome do posto, preço atual, variação nas últimas 24h

**Dados (Redis):**
1. `GEOADD geo:{combustivel}` → obter IDs próximos via `GEORADIUS`
2. `HMGET posto:{id}` nome, endereço, preço, bandeira

**Cache Streamlit:** `@st.cache_data(ttl=30)` para evitar sobrecarregar Redis a cada interação.

### 2.2 Página: "Rankings" (`pages/2_rankings.py`)

**Objetivo:** Tabelas comparativas e filtros.

**Componentes:**
- **Filtros:** 
  - Dropdown: Bairro (lista de `KEYS stats:bairro:*` parseada)
  - Radio: Ordenação (Menor Preço, Maior Variação Recentemente, Mais Próximo)
  
- **Tabela Principal (st.dataframe):**
  Colunas: Bandeira | Nome | Bairro | Preço | Variação 24h | Distância
  
- **Gráfico de Barras (st.bar_chart):**
  Preço médio por bandeira no bairro selecionado (dados agregados no pipeline)

**Queries Redis:**
```python
# Top 10 mais baratos no bairro
postos_ids = redis.zrange(f"rank:{combustivel}:{bairro}", 0, 9)
# Dados complementares
for pid in postos_ids:
    info = redis.hgetall(f"posto:{pid}")
    variacao = redis.zscore(f"alerta:variacao:24h:{combustivel}", pid)

2.3 Página: "Tendências" (pages/3_tendencias.py)
Objetivo: Análise temporal e detecção de anomalias.
Seções:
Alertas de Variação:
Lista expandível (st.expander) dos postos que tiveram alta >5% nas últimas 24h
Fonte: ZREVRANGE alerta:variacao:24h:{combustivel} 0 9
Gráfico de Série Temporal:
Para um posto selecionado, mostrar evolução dos últimos 7 dias
Dados: ZRANGE ts:preco:{posto_id}:{combustivel} -168 -1 (últimas 168 horas)
Parser: extrair preço do member "preco:evento_id"
Heatmap de Mercado:
st.map (básico) ou heatmap de densidade (advanced) mostrando concentração de postos caros vs baratos por região
2.4 Página: "Métricas de Uso" (pages/4_metricas.py) — Diferencial
Objetivo: Mostrar dados de comportamento dos usuários.
Visualizações:
KPIs em cards: Total de buscas hoje, Bairro mais consultado, Variação média de preço hoje
Tabela: Ranking de bairros por volume de busca (fonte: stats:bairro:* campo buscas_hoje)
Gráfico de pizza: Distribuição de tipos de combustível mais buscados (requer agregação no Mongo ou Redis separado)
3. Padrões de Código (Boas Práticas)
3.1 Isolamento de Camadas
Python
Copy
# services/redis_service.py
class RadarRedisService:
    def __init__(self, redis_client):
        self.r = redis_client
    
    def get_postos_proximos(self, lat, lng, raio_km, combustivel):
        # encapsula GEORADIUS + HMGET
        pass
    
    def get_ranking_bairro(self, bairro, combustivel, top_n=10):
        # encapsula ZRANGE + lookups
        pass

# app.py (página streamlit)
from services.redis_service import RadarRedisService
service = RadarRedisService(redis_client)

# UI pura, sem lógica de Redis direta
3.2 Tratamento de Erros
Python
Copy
try:
    dados = service.get_ranking_bairro(bairro_sel, comb_sel)
except RedisError:
    st.error("⚠️ Camada de cache indisponível. Mostrando dados estáticos de fallback.")
    dados = mongo_fallback_query(bairro_sel, comb_sel)  # Fallback direto ao Mongo (lento mas funciona)
3.3 Configuração
Python
Copy
# config.py
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "radar_combustivel"
4. Requisitos de Pacotes (requirements.txt)
plain
Copy
streamlit>=1.28.0
pandas>=2.0.0
redis>=5.0.0
pymongo>=4.5.0
folium>=0.14.0
streamlit-folium>=0.15.0
python-dotenv>=1.0.0
5. Checklist de Validação Visual
[ ] Mapa interativo mostra pins em locais corretos (lat/long não invertidos)
[ ] Cores dos pins mudam conforme faixa de preço (legenda clara)
[ ] Ranking atualiza em <3s após novo dado inserido no Mongo (demonstrar pipeline vivo)
[ ] Tabela mostra variação percentual com coloração (verde positivo, vermelho negativo)
[ ] Responsividade básica (não quebra em telas menores, usa st.columns corretamente)

