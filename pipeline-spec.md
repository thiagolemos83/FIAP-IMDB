3. Mapeamento de Campos (Mongo ↔ Redis)

| MongoDB (Source)               | Redis (Target)      | Lógica de Transformação                                     |
| ------------------------------ | ------------------- | ----------------------------------------------------------- |
| `postos` collection            | `posto:{id}` Hash   | Dump dos campos estáticos + último preço                    |
| `precos_historico` insert      | `rank:*` ZSET       | Atualização de score (preço) no sorted set do bairro        |
| `precos_historico` insert      | `ts:*` ZSET         | Adicionar ponto na série temporal                           |
| `precos_historico` (calculado) | `alerta:variacao:*` | Se variação > threshold, adicionar ao sorted set de alertas |
| `buscas` insert                | `stats:bairro:*`    | HINCRBY no campo buscas\_hoje                               |

---

## 4. `pipeline-spec.md` — Especificação Técnica do Pipeline

```markdown
# Especificação Técnica do Pipeline
## Pipeline de Processamento MongoDB → Redis

---

## 1. Componentes do Pipeline

### 1.1 Change Stream Listener
**Responsabilidade:** Conectar ao MongoDB Change Stream e filtrar eventos relevantes.

**Configuração:**
```python
pipeline = [
    {"$match": {
        "operationType": {"$in": ["insert", "update"]},
        "ns.coll": {"$in": ["precos_historico", "buscas"]}
    }},
    {"$project": {"fullDocument": 1, "operationType": 1, "ns": 1}}
]

with db.watch(pipeline) as stream:
    for change in stream:
        process_event(change)


Tratamento de Falhas:
Retry com backoff exponencial (1s, 2s, 4s, 8s) em falhas de conexão
Checkpoint do resume token em arquivo local ou MongoDB (collection pipeline_state)
Dead letter queue: eventos que falham após 3 retries vão para eventos_falhos collection
1.2 Event Processors
Processor A: PriceEventProcessor
Input: Change document de precos_historico (insert)
Steps:
Validação: Verificar se posto_id existe em postos
Enriquecimento: Buscar bairro do posto (cache local LRU ou Redis para evitar query Mongo)
Cálculo:
Buscar último preço no Redis (ts:preco:{id}:{comb} último elemento)
Calcular variacao_pct = ((novo - antigo) / antigo) * 100
Atualizações Atômicas (Redis Pipeline):

pipe = redis.pipeline()

# 1. Atualiza hash do posto (último preço)
pipe.hset(f"posto:{posto_id}", mapping={
    f"{combustivel}": str(preco),
    "updated_at": str(timestamp)
})

# 2. Atualiza ranking do bairro
pipe.zadd(f"rank:{combustivel}:{bairro}", {posto_id: preco})

# 3. Atualiza ranking global
pipe.zadd(f"rank:global:{combustivel}", {posto_id: preco})

# 4. Atualiza série temporal (últimas 168 horas = 7 dias)
pipe.zadd(f"ts:preco:{posto_id}:{combustivel}", {f"{preco}:{evento_id}": timestamp})
pipe.zremrangebyscore(f"ts:preco:{posto_id}:{combustivel}", 0, timestamp - (7*24*3600))

# 5. Atualiza alerta de variação (se variação > 1%)
if abs(variacao_pct) > 1.0:
    pipe.zadd(f"alerta:variacao:24h:{combustivel}", {posto_id: abs(variacao_pct)})
    pipe.zadd(f"alerta:variacao:tipo:{combustivel}:{posto_id}", {timestamp: variacao_pct})

# 6. Atualiza stats do bairro (de forma aproximada/parcial)
pipe.hincrby(f"stats:bairro:{bairro}", "updates_count", 1)

pipe.execute()

Processor B: SearchEventProcessor
Input: Change document de buscas (insert)
Steps:
Extrair bairro_detectado (ou fazer reverse geocoding se necessário)
Atualização Redis:
redis.hincrby(f"stats:bairro:{bairro}", "buscas_hoje", 1)
redis.expire(f"stats:bairro:{bairro}", 86400)  # TTL 24h para campo buscas_hoje resetar

1.3 State Manager
Responsabilidade: Manter estado do pipeline para recovery.
Collection MongoDB pipeline_state:
{
  "_id": "price_processor",
  "resume_token": "...",
  "last_processed_at": ISODate("..."),
  "event_count": 1500,
  "last_error": null
}

2. Lógica de Cálculo de Variação
def calcular_variacao(posto_id, combustivel, novo_preco, timestamp):
    # Buscar último preço no Redis Time Series (mais eficiente que Mongo)
    chave_ts = f"ts:preco:{posto_id}:{combustivel}"
    ultimos = redis.zrevrange(chave_ts, 0, 0, withscores=False)
    
    if not ultimos:
        return 0.0  # Primeira cotação
        
    ultimo_valor = float(ultimos[0].split(":")[0])  # formato "preco:evento_id"
    variacao = ((novo_preco - ultimo_valor) / ultimo_valor) * 100
    return round(variacao, 2)

3. Estratégia de Consistência
3.1 Write Concern MongoDB
Usar w=1 (padrão) para velocidade, mas j=true (journal) para durabilidade mínima.
3.2 Redis Durability
Opcional: AOF habilitado para persistência dos dados de serving (aceitável perder até 1s de dados)
Ou tratar como cache puro (reconstruído a partir do Mongo se reiniciar)
3.3 Transações
Redis MULTI/EXEC garante atomicidade das atualizações compostas (posto + ranking + stats).

4. Métricas e Observabilidade (Diferencial)
Chaves de Métrica no Redis:
pipeline:metrics:events_processed_total  (INCR)
pipeline:metrics:latency_avg           (média móvel calculada)
pipeline:metrics:errors_total            (INCR)

Exportação: Endpoint simples ou log a cada 100 eventos processados.

5. Simulador de Carga (Data Generator)
Para demonstrar o pipeline funcionando sem dados reais:

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




