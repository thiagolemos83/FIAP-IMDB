# ⛽ Radar de Combustíveis SP - Projeto IMDB 2025

Dashboard de monitoramento estratégico de preços de combustíveis na cidade de São Paulo em tempo real. Utiliza **MongoDB Change Streams** para captura de eventos, **Redis** para caching e rankings (Sorting Sets) e **Streamlit** para o Dashboard com design "Luxury Magnetic Gold".

## 🚀 Como Executar

Siga os passos abaixo para rodar o projeto localmente via Docker.

### 1. Preparar o Ambiente
Clone o repositório e acesse a pasta raiz.
Certifique-se de ter Docker e Python 3.10+ instalados.

### 2. Subir Infraestrutura (MongoDB e Redis)
```bash
docker-compose up -d
```
> Isso iniciará o MongoDB (com Replica Set configurado para Change Streams) e o Redis.

### 3. Instalar Dependências Python
```bash
pip install -r requirements.txt
```

### 4. Executar os Componentes em Terminais Separados

Recomenda-se abrir 3 terminais diferentes:

**Terminal 1: Processamento em Tempo Real (Pipeline)**
Escuta o MongoDB e atualiza os rankings no Redis instantaneamente.
```bash
python src/pipeline.py
```

**Terminal 2: Simulador de Dados**
Gera eventos de mudança de preço e buscas de usuários aleatoriamente.
```bash
python src/data_simulator.py
```

**Terminal 3: Dashboard Streamlit**
Interface administrativa premium para visualizar preços e tendências.
```bash
streamlit run src/app.py
```

## 💎 Design System & UX
O dashboard foi desenvolvido com uma estética corporativa premium utilizando as fontes **Cinzel** (serifa magnética) e **Josefin Sans** (moderna).
- **Esquema de Cores**: #d4af37 (Ouro Magnético) sobre Fundo Profundo (#0c0c0c).
- **Cards Customizados**: Implementados em HTML/CSS para maior controle sobre a experiência do usuário.

## 🛠️ Arquitetura Técnica
- **Simulador**: Produz eventos de escrita no MongoDB (Oplog).
- **Pipeline de Integração**: Sincronização MongoDB -> Redis via Change Streams.
- **Serving Layer (Redis)**: Rankings (Sorted Sets), estatísticas (HASHs) e caching de metadados.
- **Frontend (Streamlit)**: Dashboard reativo que consome dados diretamente do Redis (In-memory).

---
*Projeto concluído com sucesso e validado via testes E2E.*
