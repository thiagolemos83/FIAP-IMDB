# Product Requirements Document (PRD)
## Radar Combustível — Pipeline de Dados em Tempo Quase Real
**Versão:** 1.0  
**Data:** 2026-03-17  
**Contexto:** Trabalho Final de Disciplina (IMDB/NoSQL)

---

### 1. Visão Geral
Sistema de pipeline de dados que captura eventos operacionais de uma plataforma de comparação de preços de combustível (Radar Combustível), processa via MongoDB como fonte de verdade e disponibiliza consultas de alta performance através de Redis como camada de serving.

### 2. Objetivos de Negócio
- **OB1:** Permitir consultas sub-segundo para "postos mais baratos por região"
- **OB2:** Identificar tendências de preço em tempo quase real (combustíveis em alta/baixa)
- **OB3:** Analisar comportamento de busca dos usuários (heatmaps de demanda)
- **OB4:** Detectar anomalias de variação de preço (>10% em 24h)

### 3. Escopo do Projeto (MVP Obrigatório)
| Componente | Descrição | Critério de Aceitação |
|------------|-----------|----------------------|
| **MongoDB** | Fonte transacional/documental | Collections: postos, precos_historico, buscas_usuarios, eventos_preco |
| **Pipeline** | Processamento contínuo Mongo→Redis | Atualização < 5s entre mudança no Mongo e disponibilidade no Redis |
| **Redis** | Camada de serving estruturada | Uso mínimo de 3 tipos de estruturas distintas justificadas |
| **Visualização** | Interface Streamlit | 3+ telas funcionais demonstrando consultas ao Redis |

### 4. Fora de Escopo (Explicitamente)
- Sistema de autenticação de usuários (dados mockados são aceitáveis)
- Pagamento/Transações reais (apenas leitura de preços)
- Machine Learning preditivo (apenas estatísticas descritivas)
- Deploy em nuvem (execução local/container é suficiente)

### 5. Personas
1. **Consumidor Final:** Quer saber "gasolina mais barata em 2km" em <1s
2. **Analista de Preços:** Quer ver rankings de variação por bairro
3. **Operador do Radar:** Quer ver volume de buscas heatmap para decisão de marketing

### 6. Requisitos Funcionais (RF)

#### RF1 — Ingestão de Dados
- RF1.1: Sistema deve permitir carga inicial de postos com coordenadas geográficas (lat/long)
- RF1.2: Sistema deve capturar eventos de atualização de preço (tipo combustível, valor, timestamp, posto_id)
- RF1.3: Sistema deve registrar logs de busca (user_id, coordenada_busca, raio, timestamp, resultado_count)

#### RF2 — Pipeline de Processamento
- RF2.1: Implementar Change Streams ou polling eficiente (≤5s) do MongoDB
- RF2.2: Processar eventos de preço calculando variação percentual vs última cotação
- RF2.3: Atualizar estruturas Redis de forma atômica (transações Redis ou pipelines)

#### RF3 — Consultas Rápidas (Redis)
- RF3.1: **Ranking por Proximidade:** Dada uma coordenada (lat,long) e raio (km), retornar top N postos ordenados por preço do combustível X (Geo + Sorted Set)
- RF3.2: **Heatmap de Buscas:** Retornar agregação de buscas por célula geohash ou bairro (Hash com contadores)
- RF3.3: **Variação de Preço:** Listar postos com maior delta de preço nas últimas 24h/7d (Time Series ou Sorted Set por score de variação)
- RF3.4: **Tendência de Combustível:** Média de preço por tipo combustível por bairro (Hash estruturado)

#### RF4 — Visualização (Streamlit)
- RF4.1: Dashboard "Radar Map": Mapa interativo (folium/st.map) mostrando postos coloridos por faixa de preço
- RF4.2: Dashboard "Ranking Inteligente": Tabela com filtros (combustível, bairro, raio) alimentada por Redis
- RF4.3: Dashboard "Análise de Tendências": Gráfico de linha (preço médio vs tempo) e alertas de variação brusca
- RF4.4: Dashboard "Comportamento": Heatmap de densidade de buscas (opcional, diferencial)

### 7. Requisitos Não-Funcionais (RNF)
- **RNF1 — Latência:** 95% das consultas Redis devem responder em <100ms (p95)
- **RNF2 — Consistência:** Dados no Redis podem ter consistência eventual de até 5s vs MongoDB (aceitável para o caso)
- **RNF3 — Disponibilidade:** Pipeline deve tolerar falhas temporárias do Redis (fila de retry em memória ou MongoDB capped collection)
- **RNF4 — Escalabilidade:** Arquitetura deve suportar aumento de volume 10x sem reescrita (uso de índices adequados)

### 8. Casos de Uso Principais (Queries de Negócio)

| ID | Query de Negócio | Estrutura Redis Sugerida | Justificativa |
|----|------------------|-------------------------|---------------|
| Q1 | "Etanol mais barato em 5km do centro" | GeoADD (index espacial) + Sorted Set por preço | Geospatial queries nativas |
| Q2 | "Top 10 bairros com maior volume de busca hoje" | Sorted Set (zincrby por bairro) | Ranking dinâmico eficiente |
| Q3 | "Postos que subiram >5% a gasolina esta semana" | Sorted Set (score = pct_variação) + Hash (metadados) | Cálculo de score customizado |
| Q4 | "Preço médio da gasolina no bairro X agora" | Hash (campo = bairro, valor = json/média) | O(1) acesso direto |

### 9. Critérios de Aceitação para Nota Máxima
- [ ] Pipeline funcional demonstrado em vídeo ou print com timestamps
- [ ] Justificativa técnica escrita para cada estrutura Redis escolhida (trade-offs discutidos)
- [ ] Diagrama de arquitetura mostrando fluxo de dados entre Mongo→Pipeline→Redis→Frontend
- [ ] Código Python limpo com type hints e tratamento de exceções nos conectores
- [ ] README executável (docker-compose up ou pip install -r requirements.txt + instruções claras)

### 10. Riscos e Mitigações
| Risco | Mitigação |
|-------|-----------|
| Volume de dados pequeno para "demonstrar" pipeline | Implementar simulador de carga (data generator) que insere eventos a cada X segundos |
| Redis não persistir dados | Documentar que é camada de serving, não fonte de verdade; usar AOF opcional |
| Coordenação do grupo | Definir interfaces claras (schemas) para integração pipeline←→frontend |