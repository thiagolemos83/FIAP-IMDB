# Documentação de Arquitetura
## Radar Combustível — Pipeline MongoDB → Redis

---

## 1. Visão Geral da Arquitetura (C4 - Level 1)
┌─────────────┐      ┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│   Gerador   │      │   MongoDB       │      │   Pipeline   │      │   Redis     │
│   de Dados  │─────▶│   (Fonte de     │─────▶│   Python     │─────▶│   (Serving  │
│  (Simulador)│      │   Verdade)      │      │   Worker     │      │    Layer)   │
└─────────────┘      └─────────────────┘      └──────────────┘      └──────┬──────┘
│
▼
┌─────────────┐
│  Streamlit  │
│  Dashboard  │
└─────────────┘


## 2. Componentes Detalhados

### 2.1 MongoDB (Camada Transacional)
**Responsabilidade:** Persistência durável, schema flexível, event sourcing.

**Collections Principais:**
1. **`postos`**: Documentos estáticos (dados cadastrais, localização)
2. **`precos_historico`**: Time-series like (insert-only, TTL opcional)
3. **`buscas`**: Eventos de interação do usuário (capped collection recomendada)
4. **`eventos_preco`**: Change log (registra toda alteração de preço para audit)

**Índices Obrigatórios:**
```javascript
// postos
db.postos.createIndex({ "location": "2dsphere" })  // Geospatial
db.postos.createIndex({ "posto_id": 1 }, { unique: true })

// precos_historico
db.precos_historico.createIndex({ "posto_id": 1, "tipo_combustivel": 1, "timestamp": -1 })

// buscas (se capped collection, índice limitado)
db.buscas.createIndex({ "timestamp": 1, "location": "2dsphere" })

2.2 Pipeline Processor (Python)
Responsabilidade: Detectar mudanças, transformar, atualizar Redis atomicamente.
Estratégias de Detecção (escolher uma):
Opção A (Recomendada): MongoDB Change Streams (reação a eventos reais)
Opção B: Polling com timestamp de checkpoint (mais simples, aceitável para trabalho)
Padrão de Processamento:

# Pseudo-código da lógica
for change in mongo.watch():
    if change['operationType'] == 'insert':
        if change['ns']['coll'] == 'precos_historico':
            # 1. Atualizar hash do posto (cache)
            # 2. Atualizar sorted set do ranking por região
            # 3. Calcular variação e atualizar sorted set de alertas
            # 4. Atualizar série temporal (se usando RedisTimeSeries)

Idempotência: Todo update no Redis deve ser idempotente (usar SETNX ou verificar versão/timestamp antes de atualizar).
2.3 Redis (Camada de Serving)
Responsabilidade: Leitura rápida, estruturas otimizadas por query pattern.
Estruturas por Domínio:

| Domínio             | Estrutura Redis     | Chave Pattern                    | Conteúdo                                                |
| ------------------- | ------------------- | -------------------------------- | ------------------------------------------------------- |
| **Cache Posto**     | Hash                | `posto:{id}`                     | nome, endereço, coords (json)                           |
| **Ranking Preço**   | Sorted Set          | `rank:{combustivel}:{bairro_id}` | score=preço, member=posto\_id                           |
| **Geospatial**      | Geo                 | `geo:{combustivel}`              | coordenadas indexadas por preço                         |
| **Variação**        | Sorted Set          | `variacao:24h:{combustivel}`     | score=%variação, member=posto\_id                       |
| **Stats Bairro**    | Hash                | `stats:bairro:{id}`              | preco\_medio\_gas, preco\_medio\_eta, contador\_buscas  |
| **Contador Buscas** | HyperLogLog ou Hash | `buscas:{bairro}:{data}`         | (se usar HLL para cardinalidade, Hash para total exato) |


Justificativas Técnicas:
Hash para cache: O(1) lookup, compacto em memória
Sorted Sets para rankings: Range queries e top-N nativas (O(log N))
Geo: Busca por raio nativa (GEORADIUS) sem cálculo manual de distância
Separação por combustível: Evita chaves grandes (Big Keys) e permite TTL diferenciado
2.4 Interface Streamlit
Responsabilidade: Demonstrar valor analítico, consumir apenas Redis (nunca Mongo direto nas queries de visualização).
Camadas:
Service Layer: Funções puras Python que encapsulam comandos Redis (get_ranking_proximo(), get_variacoes())
UI Layer: Componentes Streamlit (mapas, tabelas, métricas)
3. Fluxo de Dados (Data Flow)
3.1 Evento: Novo Preço Registrado
Fonte: Simulador ou carga manual insere em precos_historico
Change Stream: Pipeline detecta insert
Processamento:
Busca último preço anterior (último no Sorted Set temporal ou Mongo)
Calcula variação percentual
Atualiza posto:{id} hash com preço atual
Atualiza rank:gasolina:bairro_X (ZADD)
Atualiza variacao:24h:gasolina (ZADD com score da variação)
Atualiza geo:gasolina (GEOADD se necessário atualizar posição/preço)
Serving: Dashboard mostra imediatamente novo ranking
3.2 Evento: Busca do Usuário
Fonte: Frontend ou simulador insere em buscas
Pipeline: Incrementa contador no Redis (HINCRBY em stats:bairro:{id})
Serving: Dashboard de heatmap atualiza densidade
4. Decisões Arquiteturais (ADRs)
ADR 1: Uso de Change Streams vs Polling
Decisão: Change Streams (se possível) ou Polling otimizado com índice em timestamp.
Justificativa: Near real-time com menor carga no MongoDB.
ADR 2: Normalização no Redis
Decisão: Dados desnormalizados no Redis (posto_id → nome completo armazenado no Hash).
Justificativa: Evitar JOINs em tempo de consulta; Redis é serving, não transacional.
ADR 3: Separação de Sorted Sets por Bairro vs Global
Decisão: Separar por bairro (rank:gasolina:centro, rank:gasolina:zona_sul).
Justificativa: Queries mais rápidas (sets menores) vs custo de atualização maior (pipeline atualiza múltiplos sets se posto muda de bairro).
ADR 4: Time Series
Decisão: Usar Sorted Sets com score=timestamp para séries temporais simples (não RedisTimeSeries module).
Justificativa: Compatibilidade com Redis padrão (sem módulos extras), suficiente para demonstração.
5. Diagrama de Deploy (Container)
yaml
Copy
# docker-compose.yml conceitual
version: '3.8'
services:
  mongo:
    image: mongo:6
    volumes:
      - mongo_data:/data/db
      
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes  # Persistência opcional
    
  pipeline:
    build: ./pipeline
    depends_on: [mongo, redis]
    # Processo contínuo (worker)
    
  streamlit:
    build: ./frontend
    ports: ["8501:8501"]
    depends_on: [redis]
    # NÃO depende do Mongo (isolamento correto)
6. Considerações de Observabilidade (Diferencial)
Métricas de latência do pipeline (tempo entre insert Mongo e update Redis)
Contador de eventos processados por segundo (Redis INCR em chave de métrica)
Health check: pipeline verifica conectividade a cada 30s