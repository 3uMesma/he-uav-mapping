"""
Ponto de entrada do dashboard: configuração da página e menu lateral.

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

paginas = [
    st.Page("paginas/visao_geral.py", title="Overview", icon=":material/dashboard:", default=True),
]

st.navigation(paginas).run()
