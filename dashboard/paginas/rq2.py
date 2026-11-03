"""
RQ2: para quais aplicações e problemas de VANT a HE foi usada.

  - estudos por aplicação (VwFacetCount);
  - aplicações que aparecem juntas no mesmo estudo (VwFacetCross, faceta x ela mesma).
"""
import pandas as pd
import streamlit as st

from db import run_query
from estilo import cabecalho, cartoes, rodape, secao
from graficos import barras, contagem, matriz, mostrar_selecao, total_estudos

cabecalho(2, "UAV applications",
          "Which applications and problems in UAV contexts have been addressed with HE?")

total = total_estudos()
aplicacoes = contagem("UAV application")

# Quantos estudos têm mais de uma aplicação
# VIEW: VwStudyFacet — uma linha por (estudo, aplicação)
varias = int(run_query(
    """
    SELECT COUNT(*) AS N FROM (
        SELECT StudyId FROM VwStudyFacet
        WHERE Facet = 'UAV application'
        GROUP BY StudyId HAVING COUNT(*) > 1
    ) AS X
    """
).iloc[0]["n"])
mais = aplicacoes.iloc[0]

# ===========================================================================
# Estudos por aplicação
# ===========================================================================
secao("Studies by application")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq2_aplicacao", aplicacoes, total)
with texto_col:
    cartoes([
        {"rotulo": "Most frequent", "numero": f"{int(mais['studies'])} of {total}",
         "texto": f"{mais['value']} is the most addressed application."},
        {"rotulo": "More than one application", "numero": f"{varias} of {total}",
         "texto": "Studies that combine a domain with a computational pattern, "
                  "such as authentication + federated learning."},
    ], colunas=1)
st.caption(
    "Application domain and, when present, the computational pattern. "
    "Click a bar to list its studies."
)
mostrar_selecao("rq2_aplicacao")

# ===========================================================================
# Aplicações que aparecem juntas
# ===========================================================================
secao("Applications that appear together")

ordem = list(aplicacoes["value"])
# VIEW: VwFacetCross — pares de aplicações no mesmo estudo. A diagonal (a mesma
# aplicação com ela mesma) é só o total da aplicação e fica de fora.
pares = run_query(
    "SELECT ValueA, ValueB, Studies, StudyIds FROM VwFacetCross "
    "WHERE FacetA = 'UAV application' AND FacetB = 'UAV application' AND ValueA <> ValueB"
).set_index(["valuea", "valueb"])

# Diagonal: estudos que têm só esta aplicação (em cinza)
# VIEW: VwStudyFacet — uma linha por (estudo, aplicação)
sozinhos = run_query(
    """
    SELECT Value AS ValueA, Value AS ValueB, COUNT(*) AS Studies,
           ARRAY_AGG(StudyId ORDER BY StudyId) AS StudyIds
    FROM VwStudyFacet
    WHERE Facet = 'UAV application'
      AND StudyId IN (SELECT StudyId FROM VwStudyFacet
                      WHERE Facet = 'UAV application'
                      GROUP BY StudyId HAVING COUNT(*) = 1)
    GROUP BY Value
    """
).set_index(["valuea", "valueb"])

matriz("rq2_pares", ordem, ordem, pd.concat([pares, sozinhos]),
       cinza={(a, a) for a in ordem})
st.caption(
    "Blue: studies that address both applications (the matrix is symmetric, so each pair "
    "appears twice). Gray, on the diagonal: studies with only this application. "
    "Click a cell to list its studies."
)
mostrar_selecao("rq2_pares")