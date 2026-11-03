"""
Ponto de entrada do dashboard: configuração da página e menu lateral.

Cada página fica em paginas/ e é registrada aqui. Para rodar:
    streamlit run dashboard/app.py
ou, com Docker, o serviço "dashboard" do docker-compose.yml.
"""
import psycopg2
import streamlit as st

from db import get_connection
from estilo import aplicar_estilo

st.set_page_config(
    page_title="HE in UAVs: systematic mapping",
    page_icon=":material/flight:",
    layout="wide",
)
aplicar_estilo()

# Sem banco não há o que mostrar: avisa uma vez, com a causa mais provável.
try:
    get_connection()
except psycopg2.OperationalError as erro:
    st.error(
        "Could not connect to the database. Check that the container is running "
        "(`docker compose ps`) and that the settings in `.env` are correct."
    )
    st.code(str(erro))
    st.stop()

# Menu lateral em seções. Cada página nova entra aqui.
paginas = {
    "": [
        st.Page("paginas/visao_geral.py", title="Overview", icon=":material/dashboard:", default=True),
    ],
    ":material/manage_search: Research questions": [
        st.Page("paginas/rq1.py", title="RQ1 · Research type"),
        st.Page("paginas/rq2.py", title="RQ2 · UAV applications"),
        st.Page("paginas/rq3.py", title="RQ3 · HE schemes and libraries"),
        st.Page("paginas/rq4.py", title="RQ4 · Validation"),
        st.Page("paginas/rq5.py", title="RQ5 · Where and when HE runs"),
    ],
}

# Menu no topo, como num site (Streamlit 1.46 ou mais novo)
st.navigation(paginas, position="top").run()
