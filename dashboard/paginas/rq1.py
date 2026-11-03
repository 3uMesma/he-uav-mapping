"""
RQ1: que tipos de pesquisa foram feitos (classificação de Wieringa et al.).

  - estudos por tipo de pesquisa (VwFacetCount).
"""
import streamlit as st

from estilo import cabecalho, cartoes, rodape, secao
from graficos import barras, contagem, mostrar_selecao, total_estudos

cabecalho(1, "Research type", "What types of research have been conducted?")

total = total_estudos()
tipos = contagem("Research type")
n_tipo = dict(zip(tipos["value"], tipos["studies"]))

secao("Studies by research type")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq1_tipo", tipos, total)
with texto_col:
    cartoes([
        {"rotulo": "Solution proposals", "numero": f"{int(n_tipo['Solution proposal'])} of {total}",
         "texto": "Almost every study proposes a new HE-based solution."},
        {"rotulo": "Validation research", "numero": f"{int(n_tipo['Validation research'])} of {total}",
         "texto": "Executed or measured the HE operations outside real practice "
                  "(simulation, computer, embedded hardware)."},
        {"rotulo": "Evaluation research", "numero": f"{int(n_tipo['Evaluation research'])} of {total}",
         "texto": "Used and evaluated in real UAV operation."},
    ], colunas=1)
st.caption(
    "Classification by Wieringa et al. (2005). A study can have more than one type, "
    "typically Solution proposal + Validation research. Click a bar to list its studies."
)
mostrar_selecao("rq1_tipo")