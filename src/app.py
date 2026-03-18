import streamlit as st
import redis
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379

r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

COMBUSTIVEIS = ["gasolina_comum", "etanol", "diesel_s10"]
BAIRROS = ["bela_vista", "pinheiros", "itaim_bibi", "vila_madalena", "moema"]

# UI Configuration
st.set_page_config(page_title="Radar de Combustíveis SP", layout="wide", page_icon="⛽")

# Load CSS
with open("src/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Main Title and Subtitle
st.title("RADAR DE COMBUSTÍVEL")
st.markdown("##### MONITORAMENTO ESTRATÉGICO EM TEMPO REAL")

# Sidebar filters
st.sidebar.header("CONTROLES")
selected_fuel = st.sidebar.selectbox("Combustível", COMBUSTIVEIS)
selected_bairro = st.sidebar.selectbox("Bairro", BAIRROS)

# Helper to get posto details
def get_posto_info(posto_id):
    return r.hgetall(f"posto:{posto_id}")

# Row 1: Key Metrics (Custom Cards)
col1, col2, col3 = st.columns(3)

# Helper for custom cards
def custom_card(title, value, subtitle="", icon_svg=""):
    st.markdown(f"""
    <div class="stMetric">
        <div style="font-family: 'Josefin Sans'; font-size: 0.8rem; color: #a0a0a0; text-transform: uppercase; letter-spacing: 1px;">
            {title}
        </div>
        <div style="font-family: 'Cinzel'; font-size: 1.8rem; color: #d4af37; margin: 5px 0;">
            {value}
        </div>
        <div style="font-family: 'Josefin Sans'; font-size: 0.9rem; color: #ffffff;">
            {subtitle}
        </div>
    </div>
    """, unsafe_allow_html=True)

# 1. Cheaper in Bairro
cheapest_in_bairro = r.zrange(f"rank:{selected_fuel}:{selected_bairro}", 0, 0, withscores=True)
with col1:
    if cheapest_in_bairro:
        p_id, p_price = cheapest_in_bairro[0]
        p_info = get_posto_info(p_id)
        custom_card(f"Mínimo em {selected_bairro}", f"R$ {p_price:.3f}", p_info.get("nome", p_id))
    else:
        custom_card(f"Mínimo em {selected_bairro}", "N/A")

# 2. Global Cheapest
cheapest_global = r.zrange(f"rank:global:{selected_fuel}", 0, 0, withscores=True)
with col2:
    if cheapest_global:
        p_id_g, p_price_g = cheapest_global[0]
        p_info_g = get_posto_info(p_id_g)
        custom_card("Mínimo Global", f"R$ {p_price_g:.3f}", f"{p_info_g.get('nome')} ({p_info_g.get('bairro')})")
    else:
        custom_card("Mínimo Global", "N/A")

# 3. Search stats
bairro_stats = r.hgetall(f"stats:bairro:{selected_bairro}")
buscas = bairro_stats.get("buscas_hoje", "0")
with col3:
    custom_card("Monitoramento Ativo", buscas, f"Buscas em {selected_bairro}")

st.divider()

# Row 2: Charts and Tables
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader(f"RANKING ESTRATÉGICO - {selected_fuel.replace('_', ' ').upper()}")
    top_10 = r.zrange(f"rank:global:{selected_fuel}", 0, 9, withscores=True)
    if top_10:
        data = []
        for p_id, p_price in top_10:
            p_info = get_posto_info(p_id)
            data.append({
                "Posto": p_info.get("nome", p_id),
                "Preço": p_price,
                "Bairro": p_info.get("bairro", ""),
                "Bandeira": p_info.get("bandeira", "")
            })
        df = pd.DataFrame(data)
        fig = px.bar(df, x='Preço', y='Posto', color='Bandeira', orientation='h', 
                     text='Preço', height=500,
                     color_discrete_sequence=['#d4af37', '#a0a0a0', '#ffffff', '#444444'])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Josefin Sans",
            font_color="#ffffff",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis={'categoryorder':'total descending', 'showgrid': False},
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando sincronização de dados...")

with col_right:
    st.subheader("ALERTAS DE VOLATILIDADE")
    variations = r.zrevrange(f"alerta:variacao:24h:{selected_fuel}", 0, 4, withscores=True)
    if variations:
        for p_id, var_pct in variations:
            p_info = get_posto_info(p_id)
            st.warning(f"📈 **{p_info.get('nome')}**: Alta de {var_pct}%")
    else:
        st.success("Estabilidade detectada no mercado.")

    st.subheader("FLUXO POR REGIÃO")
    bairro_activity = []
    for b in BAIRROS:
        updates = r.hget(f"stats:bairro:{b}", "updates_count") or "0"
        bairro_activity.append({"Região": b.replace('_', ' ').title(), "Updates": int(updates)})
    
    df_activity = pd.DataFrame(bairro_activity)
    st.dataframe(df_activity, hide_index=True, use_container_width=True)

# Auto-refresh
if st.sidebar.button("Refresh manual"):
    st.rerun()

time.sleep(2)
st.rerun()
