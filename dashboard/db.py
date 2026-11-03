"""
Camada de acesso ao banco.

Toda consulta do dashboard lê uma VIEW criada em db/05_views.sql.
Não há lógica de negócio em Python: este módulo só abre a conexão e executa
o SQL, que fica explícito em cada ponto de chamada nas páginas.
"""
import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Rodando fora do Docker, lê o .env da raiz do repositório (o mesmo do banco).
# Dentro do container o arquivo não existe e valem as variáveis do docker-compose.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "he_uav_mapping")),
    "user": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "he_uav")),
    "password": os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
    # Bancos gerenciados (ex.: Neon) exigem conexão cifrada: DB_SSLMODE=require.
    # Localmente, "prefer" usa SSL se o servidor oferecer e segue sem se não houver.
    "sslmode": os.getenv("DB_SSLMODE", "prefer"),
}


@st.cache_resource
def get_connection():
    """Conexão reaproveitada entre as execuções do Streamlit.

    readonly=True: o dashboard só lê. Qualquer INSERT, UPDATE ou DELETE que
    chegasse por esta conexão seria recusado pelo próprio PostgreSQL.
    autocommit=True: cada chamada é um único SELECT, sem transação a controlar.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _executa(sql, params):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        colunas = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=colunas)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(sql, params=None):
    """Executa um SELECT explícito e devolve um DataFrame."""
    try:
        return _executa(sql, params)
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        get_connection.clear()
        return _executa(sql, params)
