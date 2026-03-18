
---

## 7. `evaluation-checklist.md` — Alinhamento com Rubrica de Avaliação

```markdown
# Checklist de Alinhamento com Critérios de Avaliação
## Como garantir a nota máxima em cada critério

---

## Critério 1: Modelagem do Caso (2,0 pts) → **Como Atender**

| O que o professor quer ver | Evidência no projeto |
|---------------------------|---------------------|
| Entendimento do domínio | PDF explica o caso Radar Combustível contextualizado (problema real de preços) |
| Entidades coerentes | MongoDB com pelo menos: postos, preços, buscas (entidades do domínio) |
| Eventos bem definidos | Change Stream configurado para capturar "atualização de preço" e "busca do usuário" como eventos de negócio |
| Consultas relevantes | Pelo menos 4 queries de negócio documentadas no PRD (menor preço, variação, heatmap, tendência) |

**Entrega:** Seção "Descrição do Problema" no PDF mostrando que o grupo entendeu o Radar Combustível.

---

## Critério 2: Pipeline Mongo → Redis (3,0 pts) → **Como Atender**

| O que o professor quer ver | Evidência no projeto |
|---------------------------|---------------------|
| Funcionamento técnico | Código Python executável que lê do Mongo e escreve no Redis |
| Clareza do fluxo | Diagrama de arquitetura mostrando: Mongo → Change Stream → Processor → Redis |
| Lógica de atualização | Código mostrando processamento (ex: cálculo de variação percentual) antes de salvar no Redis |
| Near real-time | Simulador demonstrando atualização em <5s (print com timestamp ou vídeo) |

**Dica de Ouro:** Incluir no PDF um print do terminal mostrando:

[14:32:01] Mongo INSERT detectado: POSTO_001 - Gasolina: 5.89
[14:32:02] Redis atualizado: rank:gasolina:centro (ZADD 5.89 POSTO_001)
[14:32:02] Variação calculada: +1.2%



---

## Critério 3: Estruturas Redis (2,0 pts) → **Como Atender**

| O que o professor quer ver | Evidência no projeto |
|---------------------------|---------------------|
| Escolha justificada | Tabela no PDF: "Estrutura X usada porque..." |
| Coerência com consulta | Hash para cache (justificar: O(1) lookup), Sorted Set para ranking (justificar: range queries nativas) |
| Uso correto dos comandos | Código usando ZADD, HSET, GEOADD, ZRANGE corretamente (não apenas SET/GET genérico) |
| Variedade | Usar pelo menos 3 tipos diferentes (Hash, Sorted Set, Geo ou HyperLogLog) |

**Template para o PDF:**

Estrutura: Sorted Set (rank:gasolina:{bairro})
Justificativa: Permite consultar top-N mais baratos em O(log N + N) e range de preços nativamente.
Alternativa descartada: Lista simples (ineficiente para ordenação) ou Hash (impossível ordenar por valor).


---

## Critério 4: Visualização (1,5 pt) → **Como Atender**

| O que o professor quer ver | Evidência no projeto |
|---------------------------|---------------------|
| Clareza | Interface Streamlit organizada (sidebar, títulos, métricas em st.metric()) |
| Utilidade prática | Usuário consegue realmente encontrar postos baratos ou ver tendências |
| Demonstração do valor | Dashboard mostrando dados que só existem no Redis (rankings calculados, não raw data) |
| Funcionalidade | 3+ telas funcionando (Mapa, Ranking, Tendência) |

**Entrega:** Prints das 3 telas no PDF com dados reais (não placeholders).

---

## Critério 5: Documentação (1,5 pt) → **Como Atender**

| O que o professor quer ver | Evidência no projeto |
|---------------------------|---------------------|
| Organização do repo | README.md claro, requirements.txt presente, código comentado |
| Qualidade do PDF | Capa, sumário, seções bem estruturadas, português correto |
| Diagrama de arquitetura | Imagem clara (não pixelada) mostrando componentes e fluxo de dados |
| Prints de evidência | Prints legíveis, com timestamp quando possível, provando funcionamento |
| Instruções de execução | Passo a passo: "1. docker-compose up 2. pip install... 3. streamlit run..." |

---

## Diferenciais Positivos (Extras)

Se quiser se destacar além da nota base:

| Diferencial | Implementação Simples | Evidência no PDF |
|------------|---------------------|------------------|
| **Consultas Geográficas** | Usar Redis Geo (GEOADD/GEORADIUS) + visualização no mapa Streamlit | Print do mapa com raio de busca circulado |
| **Séries Temporais** | Usar Sorted Set com score=timestamp para histórico de preço | Gráfico de linha mostrando evolução de preço de um posto |
| **Ranking por Bairro/Cidade** | Separar Sorted Sets por bairro (rank:gasolina:centro) vs global | Print mostrando rankings diferentes para bairros diferentes |
| **Batch vs Eventos** | Implementar dois modos no pipeline (um com Change Stream, outro com polling) e comparar latência | Tabela comparativa no PDF: "Modo Evento: 2s latência vs Modo Batch: 60s" |
| **Observabilidade** | Adicionar logs estruturados, métricas no Redis (contadores), health check | Print do log ou dashboard simples de métricas do pipeline |
| **Tratamento de Falhas** | Implementar retry, dead letter queue, ou fallback para MongoDB quando Redis falha | Código mostrando try/except e fallback, ou seção no PDF explicando resiliência |
| **Interface Refinada** | Usar componentes avançados do Streamlit (gráficos Plotly, animações, cache otimizado) | GIF ou print mostrando interatividade (hover, filtros dinâmicos) |

---

## Checklist Final de Submissão

Antes de enviar, conferir:

- [ ] Repositório GitHub contém todos os arquivos de código
- [ ] PDF tem **todos** os elementos obrigatórios listados acima
- [ ] Nomes dos integrantes constam na capa do PDF e no README
- [ ] Link do GitHub está no final do PDF (funcional e testado)
- [ ] Video ou GIF curto (opcional mas impressiona) mostrando pipeline funcionando em tempo real
- [ ] `requirements.txt` está atualizado (`pip freeze > requirements.txt` no ambiente limpo)
- [ ] Não há chaves de API/senhas hardcoded no código (usar .env)

