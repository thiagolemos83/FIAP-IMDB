
---

## 3. `data-model.md` — Modelagem de Dados

```markdown
# Modelagem de Dados
## MongoDB (Schema Flexível) + Redis (Estruturas Específicas)

---

## 1. MongoDB Collections

### 1.1 `postos` (Cadastro Base)
```json
{
  "_id": ObjectId("..."),
  "posto_id": "POSTO_001",
  "nome": "Posto Shell Center",
  "endereco": "Av. Paulista, 1000",
  "bairro": "bela_vista",
  "cidade": "sao_paulo",
  "uf": "SP",
  "localizacao": {
    "type": "Point",
    "coordinates": [-46.6539, -23.5648]  // [long, lat]
  },
  "bandeira": "shell",
  "servicos": ["troca_oleo", "lavagem"],
  "ativo": true,
  "metadata": {
    "updated_at": ISODate("2026-03-17T10:00:00Z")
  }
}

Índices: posto_id (unique), localizacao (2dsphere), bairro (text)
1.2 precos_historico (Eventos de Preço)

{
  "_id": ObjectId("..."),
  "evento_id": "EVT_12345",
  "posto_id": "POSTO_001",
  "tipo_combustivel": "gasolina_comum",  // ou etanol, diesel_s10
  "preco": 5.899,
  "preco_anterior": 5.799,  // opcional, facilita cálculo
  "variacao_pct": 1.72,      // calculado no pipeline
  "timestamp": ISODate("2026-03-17T14:30:00Z"),
  "origem": "manual"  // ou "scraper", "sistema"
}

Índices: {posto_id: 1, tipo_combustivel: 1, timestamp: -1} (compound)
TTL: Opcional (expirar registros após 1 ano se volume alto)
1.3 buscas (Interação Usuário)

{
  "_id": ObjectId("..."),
  "busca_id": "BUSCA_789",
  "user_id": "USER_123",  // ou anonimo
  "timestamp": ISODate("2026-03-17T14:35:00Z"),
  "localizacao_busca": {
    "type": "Point",
    "coordinates": [-46.6540, -23.5650]
  },
  "raio_km": 2,
  "combustivel_filtro": "etanol",
  "bairro_detectado": "bela_vista",  // geocoding reverso
  "resultados_retornados": 5
}

Tipo: Capped collection (tamanho 1GB) para retenção automática
2. Redis Data Structures (Detalhado)
2.1 Cache de Entidades (Hash)
Chave: posto:{posto_id}
Tipo: HSET
TTL: 24 horas (refresh no acesso)
Campos:
HSET posto:POSTO_001 \
  nome "Posto Shell Center" \
  endereco "Av. Paulista, 1000" \
  lat "-23.5648" \
  lng "-46.6539" \
  bairro "bela_vista" \
  bandeira "shell" \
  gasolina_comum "5.899" \
  etanol "4.299" \
  updated_at "1710678600"

  Justificativa: O(1) acesso aos dados do posto sem consultar MongoDB.
2.2 Rankings por Preço (Sorted Set)
Chave: rank:{combustivel}:{bairro}
Exemplo: rank:gasolina_comum:bela_vista
Operações:
Atualização: ZADD rank:gasolina_comum:bela_vista 5.899 POSTO_001
Query (Top 10 mais baratos): ZRANGE rank:gasolina_comum:bela_vista 0 9 WITHSCORES
Query (Range de preço): ZRANGEBYSCORE rank:gasolina_comum:bela_vista 5.0 6.0
Variação Global (sem filtro bairro):
Chave: rank:global:etanol
2.3 Índice Geoespacial (Geo)
Chave: geo:{combustivel}
Exemplo: geo:gasolina_comum
Operações:
Adicionar: GEOADD geo:gasolina_comum -46.6539 -23.5648 POSTO_001
Buscar próximos:
GEORADIUS geo:gasolina_comum -46.6540 -23.5650 2 km WITHDIST ASC

Buscar próximos + preço (combinação aplicativa):
GEORADIUS para obter IDs em 2km
HGETALL posto:{id} para cada um (ou pipelined)
Ordenar em memória (Python) ou usar ZINTERSTORE temporário
Alternativa híbrida (recomendada para performance):
Manter Geo separado por bairro para sets menores: geo:gasolina:bela_vista
2.4 Monitoramento de Variação (Sorted Set por Score)
Chave: alerta:variacao:{periodo}:{combustivel}
Exemplos: alerta:variacao:24h:gasolina_comum, alerta:variacao:7d:etanol
Estrutura:
Score: valor absoluto da variação percentual (ex: 5.5 para +5.5% ou -5.5%)
Member: posto_id
Query: Top 10 maiores altas: ZREVRANGE alerta:variacao:24h:gasolina_comum 0 9
Query: Top 10 maiores quedas: ZRANGE alerta:variacao:24h:gasolina_comum 0 9
2.5 Estatísticas Agregadas (Hash)
Chave: stats:bairro:{bairro_id}
Campos:
HSET stats:bairro:bela_vista \
  preco_medio_gasolina "5.950" \
  preco_medio_etanol "4.350" \
  postos_count "15" \
  buscas_hoje "42" \
  ultima_atualizacao "1710678600"

 Atualização: Calculada pelo pipeline a cada N eventos ou a cada janela de tempo.
2.6 Contadores de Buscas (HyperLogLog vs Hash)
Opção A (Precisão absoluta - Hash):
Chave: buscas:{bairro}:2026-03-17
Comando: HINCRBY buscas:bela_vista:2026-03-17 contador 1
Opção B (Cardinalidade estimada - HyperLogLog):
Para contar usuários únicos (se tiver user_id):
PFADD buscas:unicas:bela_vista USER_123
Recomendação para trabalho: Hash (mais simples de explicar e visualizar).
2.7 Time Series Simplificado (Sorted Set como TS)
Chave: ts:preco:{posto_id}:{combustivel}
Estrutura:
Score: timestamp unix
Member: preco:evento_id ou apenas o valor serializado
Exemplo:
ZADD ts:preco:POSTO_001:gasolina 1710678600 "5.899:EVT_123"

Query média últimas 24h:
ZRANGE ts:preco:POSTO_001:gasolina -24 -1 (se inserir a cada hora) ou por range de score (timestamp).