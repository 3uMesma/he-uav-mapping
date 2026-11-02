"""
Visão geral: o que o mapeamento cobre, em números, no tempo e por aplicação.

  - indicadores (VwKpi);
  - estudos por ano, empilhados por família HE (VwStudyOverview + VwStudyFacet);
  - matriz de lacunas: aplicação x uma faceta escolhida (VwFacetCross).
Clicar numa barra ou numa célula lista os estudos por trás dela.
"""
import textwrap

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, BORDA, CORES_FAMILIA, TEXTO, TITULO, abertura, bloco_arredondado,
                    cartoes, cor_escala, grafico,
                    layout_grafico, lista_estudos, nota, pontos_clicados, rodape, secao, tabela)

# Ordem de exibição das categorias (a ordem do formulário, não a alfabética)
FAMILIAS = ["PHE", "SHE", "FHE", "Not determined"]


def estudos_por_id(ids):
    # VIEW: VwStudyOverview — dados bibliográficos dos estudos selecionados
    return run_query(
        "SELECT StudyId, Year, Title, DoiUrl FROM VwStudyOverview "
        "WHERE StudyId = ANY(%s) ORDER BY Year, Title",
        (list(ids),),
    )


# ===========================================================================
# Abertura e indicadores
# ===========================================================================

# VIEW: VwKpi — uma única linha com os números da página inicial
kpi = run_query("SELECT * FROM VwKpi").iloc[0]
total = int(kpi["studies"])

abertura(
    "Homomorphic encryption in UAVs:<br>applications, schemes and costs",
    f"Interactive companion to the systematic mapping study. Explore the {total} "
    "primary studies by research question, and from any number get to the studies behind it.",
    "Amanda Kasat Baltor · Advisor: Prof. Dr. Kalinka Castelo Branco · ICMC/USP",
)

secao("The mapping in numbers")
cartoes([
    {"rotulo": "Primary studies", "numero": total,
     "texto": "Included after full-text reading and data extraction."},
    {"rotulo": "Years covered", "numero": f"{int(kpi['firstyear'])}–{int(kpi['lastyear'])}",
     "texto": "Publication year of the first and the most recent study."},
    {"rotulo": "HE operations executed", "numero": f"{int(kpi['heexecuted'])} of {total}",
     "texto": "Studies that actually ran encryption, homomorphic evaluation and decryption."},
    {"rotulo": "Named HE schemes", "numero": int(kpi["namedschemes"]),
     "texto": "Distinct schemes identified by name, such as Paillier or CKKS."},
    {"rotulo": "Named libraries", "numero": int(kpi["namedlibraries"]),
     "texto": "Distinct libraries reported, including custom implementations."},
    {"rotulo": "Security level stated", "numero": f"{int(kpi['withsecuritylevel'])} of {total}",
     "texto": "Studies that state the security level in bits; key size alone does not count."},
])


# ===========================================================================
# Estudos por ano: barras empilhadas por família, hachura = HE não executado
# ===========================================================================
secao("Studies over time")

# VIEWS: VwStudyOverview (ano, HE executado) e VwStudyFacet (família HE; uma por estudo)
por_ano = run_query(
    """
    SELECT O.Year, F.Value AS Family, O.HEExecuted,
           COUNT(*) AS Studies,
           ARRAY_AGG(O.StudyId ORDER BY O.StudyId) AS StudyIds
    FROM VwStudyOverview O
    JOIN VwStudyFacet F ON F.StudyId = O.StudyId AND F.Facet = 'HE family'
    GROUP BY O.Year, F.Value, O.HEExecuted
    """
)
# Os dois números ao lado do gráfico: quanto da área é dos dois últimos anos
recente = run_query(
    """
    SELECT MAX(O.Year) - 1                                            AS Desde,
           COUNT(*) FILTER (WHERE O.Year >= (SELECT MAX(Year) - 1 FROM Study)) AS Recentes,
           COUNT(*)                                                    AS Total,
           COUNT(*) FILTER (WHERE O.Year >= (SELECT MAX(Year) - 1 FROM Study)
                              AND F.Value = 'FHE')                     AS FheRecentes,
           COUNT(*) FILTER (WHERE F.Value = 'FHE')                     AS Fhe
    FROM VwStudyOverview O
    JOIN VwStudyFacet F ON F.StudyId = O.StudyId AND F.Facet = 'HE family'
    """
).iloc[0]

# Um traço por (família, executado), empilhados de baixo para cima nesta ordem
SEGMENTOS = [(f, e) for f in FAMILIAS for e in (True, False)]
fig = go.Figure()
for familia, executado in SEGMENTOS:
    parte = por_ano[(por_ano["family"] == familia) & (por_ano["heexecuted"] == executado)]
    cor = CORES_FAMILIA[familia]
    fig.add_trace(go.Bar(
        x=parte["year"], y=parte["studies"], name=familia,
        legendgroup=familia, showlegend=executado,
        marker=dict(
            color=cor if executado else "white",
            line=dict(color=cor, width=1.5),
            pattern=dict(shape="" if executado else "/", fgcolor=cor, size=6, solidity=0.4),
        ),
        hovertemplate=(f"<b>%{{x}} · {familia}</b><br>%{{y}} studies, HE "
                       f"{'executed' if executado else 'not executed'}<extra></extra>"),
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.35)),
    ))
# Entrada de legenda só para explicar a hachura
fig.add_trace(go.Bar(
    x=[None], y=[None], name="HE not executed", hoverinfo="skip",
    marker=dict(color="white", line=dict(color=TEXTO, width=1.5),
                pattern=dict(shape="/", fgcolor=TEXTO, size=6, solidity=0.4)),
))
layout_grafico(fig, altura=340)
fig.update_layout(barmode="stack", bargap=0.35, margin=dict(l=10, r=10, t=40, b=40))
anos = list(range(int(por_ano["year"].min()), int(por_ano["year"].max()) + 1))
fig.update_xaxes(tickvals=anos, ticktext=[str(a) for a in anos])
fig.update_yaxes(title_text="Studies", showgrid=True, gridcolor=BORDA, dtick=2)


def ao_clicar_ano():
    pontos = pontos_clicados("grafico_ano")
    ids = []
    for p in pontos:
        if p.get("curve_number", 0) >= len(SEGMENTOS):
            continue
        familia, executado = SEGMENTOS[p["curve_number"]]
        ano = int(p["x"])
        linha = por_ano[(por_ano["year"] == ano) & (por_ano["family"] == familia)
                        & (por_ano["heexecuted"] == executado)]
        if len(linha):
            ids += list(linha.iloc[0]["studyids"])
            rotulo = f'{ano} · {familia} · HE {"executed" if executado else "not executed"}'
    st.session_state["sel_ano"] = {"rotulo": rotulo, "ids": ids} if ids else None


grafico_col, texto_col = st.columns([3, 1], vertical_alignment="center")
with grafico_col:
    grafico(fig, "grafico_ano", ao_clicar_ano)
with texto_col:
    cartoes([
        {"rotulo": f"Published {int(recente['desde'])}–{int(recente['desde']) + 1}",
         "numero": f"{int(recente['recentes'])} of {int(recente['total'])}",
         "texto": "The area is recent: most studies are from the last two years."},
        {"rotulo": f"FHE studies since {int(recente['desde'])}",
         "numero": f"{int(recente['fherecentes'])} of {int(recente['fhe'])}",
         "texto": "Fully homomorphic schemes (CKKS, BFV) grow in the recent studies."},
    ], colunas=1)
st.caption(
    "Number of studies per publication year, by family of the HE scheme. Hatched: HE "
    "operations proposed but not executed. The last year covers the studies published "
    "until the search date. Click a bar segment to list its studies."
)
if st.session_state.get("sel_ano"):
    sel = st.session_state["sel_ano"]
    lista_estudos(estudos_por_id(sel["ids"]), f'{sel["rotulo"]}: {len(sel["ids"])} studies')


# ===========================================================================
# Matriz de lacunas: aplicação x uma faceta escolhida (evidence gap map)
# ===========================================================================
secao("Where research concentrates")

# Facetas que podem ir nas colunas da matriz (as linhas são sempre as aplicações)
COLUNAS_MATRIZ = {
    "HE family": "HE scheme family (RQ3)",
    "HE scheme": "HE scheme (RQ3)",
    "Validation approach": "Validation approach (RQ4)",
    "Operation phase": "Flight phase (RQ5)",
    "Cost type": "Reported cost (RQ6)",
    "Baseline type": "Baseline (RQ6)",
    "Protected data": "Protected data (RQ7)",
    "Protected from": "Protected from (RQ7)",
    "Research type": "Research type (RQ1)",
}


def ao_trocar_faceta():
    st.session_state["sel_matriz"] = None


faceta = st.selectbox(
    "Cross UAV applications with", list(COLUNAS_MATRIZ),
    format_func=COLUNAS_MATRIZ.get, key="faceta_matriz", on_change=ao_trocar_faceta,
)

# VIEW: VwFacetCount — ordem das linhas (aplicação mais frequente no topo) e das
# colunas (mais frequente à esquerda, "Not reported" e afins por último)
linhas = list(run_query(
    "SELECT Value FROM VwFacetCount WHERE Facet = 'UAV application' "
    "ORDER BY Studies DESC, Value"
)["value"])
colunas = list(run_query(
    "SELECT Value FROM VwFacetCount WHERE Facet = %s "
    "ORDER BY IsNotInformed, Studies DESC, Value",
    (faceta,),
)["value"])
# VIEW: VwFacetCross — estudos de cada célula (aplicação, opção), inclusive as vazias
celulas = run_query(
    "SELECT ValueA AS Application, ValueB AS Category, Studies, StudyIds "
    "FROM VwFacetCross WHERE FacetA = 'UAV application' AND FacetB = %s",
    (faceta,),
)
celulas = celulas.set_index(["application", "category"])
maior = max(int(celulas["studies"].max()), 1)

linhas_y = linhas[::-1]
n_cel = {(a, c): int(celulas.loc[(a, c), "studies"]) for a in linhas_y for c in colunas}

ALTURA_LINHA = 44
fracao = min(1.0, 0.3 + 0.1 * len(colunas))
largura_coluna = 1000 * fracao / len(colunas)
raio_y = 9 / ALTURA_LINHA
raio_x = 9 / largura_coluna
formas = [
    dict(type="path", layer="below", line=dict(width=0), fillcolor=cor_escala(n, maior),
         path=bloco_arredondado(colunas.index(c), linhas_y.index(a), 0.92, 0.78, raio_x, raio_y))
    for (a, c), n in n_cel.items() if n > 0
]

fig = go.Figure()
# Um ponto invisível por célula, com o número escrito. É ele que recebe o clique e
# o hover (o Streamlit só devolve seleção de pontos). Célula vazia mostra "·".
pontos = [(a, c, n_cel[(a, c)]) for a in linhas_y for c in colunas]
fig.add_trace(go.Scatter(
    x=[c for _, c, _ in pontos], y=[a for a, _, _ in pontos],
    mode="markers+text", showlegend=False,
    text=[str(n) if n else "·" for _, _, n in pontos],
    textfont=dict(family="Inter, sans-serif", size=13,
                  color=["white" if n > maior / 2 else (TITULO if n else "#CBD5E0")
                         for _, _, n in pontos]),
    marker=dict(size=34, symbol="square", color="rgba(0,0,0,0)"),
    customdata=[n for _, _, n in pontos],
    hovertemplate="<b>%{y}</b><br>%{x}<br>%{customdata} studies<extra></extra>",
    selected=dict(marker=dict(opacity=1)),
    unselected=dict(marker=dict(opacity=1)),
))
layout_grafico(fig, altura=90 + ALTURA_LINHA * len(linhas))
fig.update_layout(showlegend=False, shapes=formas, margin=dict(l=10, r=10, t=10, b=10))
fig.update_xaxes(side="top", categoryorder="array", categoryarray=colunas,
                 range=[-0.5, len(colunas) - 0.5], linecolor="rgba(0,0,0,0)",
                 tickvals=colunas, ticktext=["<br>".join(textwrap.wrap(c, 14)) for c in colunas])
fig.update_yaxes(categoryorder="array", categoryarray=linhas_y, range=[-0.5, len(linhas_y) - 0.5])


def ao_clicar_celula():
    pts = pontos_clicados("grafico_matriz")
    pts = [p for p in pts if p.get("curve_number", 0) == 0]
    if not pts:
        st.session_state["sel_matriz"] = None
        return
    a, c = pts[0]["y"], pts[0]["x"]
    ids = list(celulas.loc[(a, c), "studyids"])
    st.session_state["sel_matriz"] = {"rotulo": f"{a} · {c}", "ids": ids} if ids else None


if fracao < 1:
    matriz_col, _ = st.columns([fracao, 1 - fracao])
    with matriz_col:
        grafico(fig, "grafico_matriz", ao_clicar_celula)
else:
    grafico(fig, "grafico_matriz", ao_clicar_celula)
st.caption(
    "Number of studies per pair: UAV application × the attribute chosen above. Empty cells "
    "are gaps in the literature. A study can address several applications and have several "
    "values of the chosen attribute, so it can count in more than one cell. Click a cell to "
    "list its studies."
)
if st.session_state.get("sel_matriz"):
    sel = st.session_state["sel_matriz"]
    lista_estudos(estudos_por_id(sel["ids"]), f'{sel["rotulo"]}: {len(sel["ids"])} studies')


# ===========================================================================
# RQs e nota final
# ===========================================================================
secao("Research questions")
tabela(["RQ", "Topic"], [
    ["RQ1", "Research type"],
    ["RQ2", "UAV application and problem addressed"],
    ["RQ3", "HE schemes, libraries and parameters"],
    ["RQ4", "Validation approach"],
    ["RQ5", "Where and when each HE operation runs (location and flight phase)"],
    ["RQ6", "Reported costs and baselines"],
    ["RQ7", "Threat model: adversaries, their behavior and protected data"],
])

nota(
    "Most attributes are multi-valued: a study can address several applications, "
    "report several costs or adopt several schemes. Counts are always numbers of "
    "studies, so percentages within one attribute do not add up to 100%."
)
