"""
RQ2: para quais aplicações e problemas de VANT a HE foi usada.

As 13 categorias de aplicação da extração misturam dois tipos de resposta, que
a página mostra separados:
  - domínio: a tarefa do sistema de VANTs (navegação, autenticação, imagem...);
  - padrão computacional: como o processamento é organizado (computation
    offloading ou federated learning).
A separação é só de apresentação; no banco continua uma faceta só.

  - estudos por domínio, com "No specific domain" para quem só tem padrão;
  - estudos por padrão, com "Neither" para quem não tem nenhum;
  - domínio x padrão.
"""
import streamlit as st

from db import run_query
from estilo import cabecalho, cartoes, secao
from graficos import barras, matriz, mostrar_selecao, total_estudos

cabecalho(
    2, "UAV applications",
    "Which applications and problems in UAV contexts have been addressed with HE?",
    descricao=(
        "The extraction recorded two kinds of answer, shown separately on this page: the "
        "application domain, that is, the task the UAV system performs with encrypted data "
        "(such as navigation, authentication or image processing), and the computational "
        "pattern that organizes where that processing happens (computation offloading to an "
        "edge or cloud server, or federated learning among UAVs). A study can have more than "
        "one of each."
    ),
)

total = total_estudos()

SEM_DOMINIO, SEM_PADRAO = "No specific domain", "Neither"
PADROES = ["Computation offloading", "Federated learning"]
LISTA_PADROES = ", ".join(f"'{p}'" for p in PADROES)

# Domínio e padrão de cada estudo, a partir da faceta única de aplicação.
# Quem não tem domínio vira "No specific domain"; quem não tem padrão, "Neither".
# VIEW: VwStudyFacet — uma linha por (estudo, aplicação)
CTE = f"""
WITH Aplicacao AS (
    SELECT StudyId, Value FROM VwStudyFacet WHERE Facet = 'UAV application'
), Dominio AS (
    SELECT StudyId, Value FROM Aplicacao WHERE Value NOT IN ({LISTA_PADROES})
    UNION
    SELECT S.StudyId, '{SEM_DOMINIO}' FROM Study S
    WHERE NOT EXISTS (SELECT 1 FROM Aplicacao A
                      WHERE A.StudyId = S.StudyId AND A.Value NOT IN ({LISTA_PADROES}))
), Padrao AS (
    SELECT StudyId, Value FROM Aplicacao WHERE Value IN ({LISTA_PADROES})
    UNION
    SELECT S.StudyId, '{SEM_PADRAO}' FROM Study S
    WHERE NOT EXISTS (SELECT 1 FROM Aplicacao A
                      WHERE A.StudyId = S.StudyId AND A.Value IN ({LISTA_PADROES}))
)
"""


def por_grupo(tabela, vazio):
    """Estudos por valor de Dominio ou Padrao, no formato de VwFacetCount."""
    df = run_query(
        CTE + f"""
        SELECT Value, COUNT(DISTINCT StudyId) AS Studies,
               ARRAY_AGG(DISTINCT StudyId) AS StudyIds
        FROM {tabela} GROUP BY Value
        """
    )
    df["isnotinformed"] = df["value"] == vazio
    return df.sort_values(["isnotinformed", "studies", "value"],
                          ascending=[True, False, True]).reset_index(drop=True)


dominios = por_grupo("Dominio", SEM_DOMINIO)
padroes = por_grupo("Padrao", SEM_PADRAO)
n_dominio = dict(zip(dominios["value"], dominios["studies"]))
n_padrao = dict(zip(padroes["value"], padroes["studies"]))
mais = dominios.iloc[0]
com_padrao = total - int(n_padrao.get(SEM_PADRAO, 0))

# ===========================================================================
# Domínios
# ===========================================================================
secao("Application domains",
      "Number of studies per UAV task in which HE was used. A study can address more than "
      "one domain.")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq2_dominio", dominios, total)
with texto_col:
    cartoes([
        {"rotulo": "Most frequent domain", "numero": f"{int(mais['studies'])} of {total}",
         "texto": f"{mais['value']}, the UAV task most often addressed with HE."},
        {"rotulo": "Compliance verification",
         "numero": f"{int(n_dominio.get('Compliance verification', 0))} of {total}",
         "texto": "Checking UAV operations against rules, such as geofences, without "
                  "revealing the data."},
        {"rotulo": "No specific domain", "numero": f"{int(n_dominio.get(SEM_DOMINIO, 0))} of {total}",
         "texto": "Studies described only by a computational pattern, without a particular "
                  "UAV task."},
    ], colunas=1)
st.caption(
    "No specific domain: studies described only by a computational pattern. A study can count "
    "in several bars. Click a bar to list its studies."
)
mostrar_selecao("rq2_dominio")

# ===========================================================================
# Padrões computacionais
# ===========================================================================
secao("Computational patterns",
      "How the encrypted processing is organized: delegated to an edge or cloud server, or "
      "distributed among UAVs that train a model together.")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq2_padrao", padroes, total)
with texto_col:
    cartoes([
        {"rotulo": "With a computational pattern", "numero": f"{com_padrao} of {total}",
         "texto": "Computation offloading, federated learning or both."},
    ], colunas=1)
st.caption(
    "Neither: the processing is not organized as offloading or federated learning. "
    "Click a bar to list its studies."
)
mostrar_selecao("rq2_padrao")

# ===========================================================================
# Domínio x padrão
# ===========================================================================
secao("Domains and patterns together",
      "Which computational pattern each application domain relies on.")

celulas = run_query(
    CTE + """
    SELECT D.Value AS Domain, P.Value AS Pattern,
           COUNT(DISTINCT D.StudyId) AS Studies, ARRAY_AGG(DISTINCT D.StudyId) AS StudyIds
    FROM Dominio D JOIN Padrao P ON P.StudyId = D.StudyId
    GROUP BY D.Value, P.Value
    """
).set_index(["domain", "pattern"])

linhas = list(dominios["value"])                  # mesma ordem das barras
colunas = list(padroes["value"])
# Cinza: sem domínio específico ou sem padrão, fora da escala de azul
cinza = {(d, SEM_PADRAO) for d in linhas} | {(SEM_DOMINIO, p) for p in colunas}
matriz("rq2_cruzamento", linhas, colunas, celulas, cinza=cinza)
st.caption(
    "Number of studies per application domain and computational pattern. Gray: no specific "
    "domain or no computational pattern. Click a cell to list its studies."
)
mostrar_selecao("rq2_cruzamento")
