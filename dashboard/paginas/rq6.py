"""
RQ6: quais custos de HE são reportados e com quais baselines são comparados.

  - estudos por tipo de custo (VwFacetCount);
  - combinações de custos reportadas juntas, em gráfico UpSet (Reports);
  - estudos por tipo de baseline (VwFacetCount);
  - custo x baseline (VwFacetCross).
"""
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, BORDA, FUNDO_CARTAO, TITULO, cabecalho, cartoes, grafico,
                    layout_grafico, pontos_clicados, rodape, secao)
from graficos import barras, contagem, matriz, mostrar_selecao, total_estudos

cabecalho(6, "Costs and baselines",
          "Which costs of HE are reported, and against which baselines are they compared?")

total = total_estudos()
custos = contagem("Cost type")
baselines = contagem("Baseline type")
n_custo = dict(zip(custos["value"], custos["studies"]))
n_baseline = dict(zip(baselines["value"], baselines["studies"]))
# Custos reportados, do mais frequente ao menos (sem "Not reported")
linhas_custo = list(custos.loc[~custos["isnotinformed"], "value"])

# Combinações de custos: uma linha por combinação exata, com os estudos que a
# reportam. "Not reported" fica de fora (são os estudos sem custo nenhum).
combinacoes = run_query(
    """
    SELECT Combo, Costs, COUNT(*) AS Studies, ARRAY_AGG(StudyId ORDER BY StudyId) AS StudyIds
    FROM (SELECT StudyId,
                 string_agg(CostTypeName, ' + ' ORDER BY CostTypeName) AS Combo,
                 COUNT(*) AS Costs
          FROM Reports
          WHERE CostTypeName <> 'Not reported'
          GROUP BY StudyId) AS PorEstudo
    GROUP BY Combo, Costs
    ORDER BY Studies DESC, Costs DESC, Combo
    """
)
algum_custo = int(combinacoes["studies"].sum())
dois_ou_mais = int(combinacoes.loc[combinacoes["costs"] >= 2, "studies"].sum())


# ===========================================================================
# Custos reportados
# ===========================================================================
secao("Which costs are reported",
      "The overhead each study measures or estimates when HE is added to the UAV system.")

grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq6_custo", custos, total=total)
with texto_col:
    cartoes([
        {"rotulo": "At least one cost", "numero": f"{algum_custo} of {total}",
         "texto": "The other studies do not report any cost of HE."},
        {"rotulo": "Computation time/latency",
         "numero": f"{int(n_custo.get('Computation time/latency', 0))} of {total}",
         "texto": "The most reported cost by far."},
        {"rotulo": "Energy/power", "numero": f"{int(n_custo.get('Energy/power', 0))} of {total}",
         "texto": "Energy limits flight time, yet few studies measure it."},
    ], colunas=1)
st.caption("A study can count in several bars. Click a bar to list its studies.")
mostrar_selecao("rq6_custo")


# ===========================================================================
# Custos reportados juntos (UpSet)
# ===========================================================================
secao("Which costs are reported together",
      "Each column is a combination of costs and the number of studies that report exactly "
      "that combination.")

colunas = list(range(len(combinacoes)))
membros = [c.split(" + ") for c in combinacoes["combo"]]
linhas_y = linhas_custo[::-1]                # Plotly desenha o primeiro y embaixo

fig = go.Figure()
# Traço 0: barras com o número de estudos de cada combinação (parte de cima)
fig.add_trace(go.Bar(
    x=colunas, y=combinacoes["studies"], yaxis="y2", width=0.6,
    marker=dict(color=AZUL, cornerradius=4),
    text=combinacoes["studies"], textposition="outside", cliponaxis=False,
    textfont=dict(family="Inter, sans-serif", size=12, color=TITULO),
    customdata=combinacoes["combo"],
    hovertemplate="<b>%{customdata}</b><br>%{y} studies<extra></extra>",
    selected=dict(marker=dict(opacity=1)),
    unselected=dict(marker=dict(opacity=0.4)),
))
# Traço 1: linhas ligando os custos de cada combinação
xs_linha, ys_linha = [], []
for j, m in enumerate(membros):
    if len(m) > 1:
        posicoes = sorted(linhas_y.index(c) for c in m)
        xs_linha += [j, j, None]
        ys_linha += [linhas_y[posicoes[0]], linhas_y[posicoes[-1]], None]
fig.add_trace(go.Scatter(
    x=xs_linha, y=ys_linha, mode="lines", line=dict(color=AZUL, width=3),
    hoverinfo="skip", showlegend=False,
))
# Traço 2: um ponto por (combinação, custo), cheio se o custo faz parte dela
pontos = [(j, c, c in m) for j, m in enumerate(membros) for c in linhas_y]
fig.add_trace(go.Scatter(
    x=[j for j, _, _ in pontos], y=[c for _, c, _ in pontos], mode="markers",
    marker=dict(size=14, color=[AZUL if dentro else BORDA for _, _, dentro in pontos]),
    customdata=[combinacoes["combo"].iloc[j] for j, _, _ in pontos],
    hovertemplate="<b>%{customdata}</b><extra></extra>",
    showlegend=False,
    selected=dict(marker=dict(opacity=1)),
    unselected=dict(marker=dict(opacity=1)),
))

# Faixas alternadas atrás das linhas de pontos, para guiar o olho
faixas = [
    dict(type="rect", layer="below", line=dict(width=0), fillcolor=FUNDO_CARTAO,
         xref="x", yref="y", x0=-0.5, x1=len(colunas) - 0.5, y0=i - 0.5, y1=i + 0.5)
    for i in range(len(linhas_y)) if (len(linhas_y) - 1 - i) % 2 == 0
]

ALTURA_LINHA = 30
altura_pontos = ALTURA_LINHA * len(linhas_y)
altura = altura_pontos + 170
divisa = altura_pontos / (altura - 30)       # fração da altura útil ocupada pelos pontos
layout_grafico(fig, altura=altura)
fig.update_layout(
    showlegend=False, shapes=faixas, margin=dict(l=10, r=10, t=30, b=0),
    yaxis=dict(domain=[0, divisa], categoryorder="array", categoryarray=linhas_y,
               range=[-0.5, len(linhas_y) - 0.5]),
    yaxis2=dict(domain=[divisa + 0.04, 1], anchor="x", visible=False,
                range=[0, combinacoes["studies"].max() * 1.15]),
)
fig.update_xaxes(visible=False, range=[-0.5, len(colunas) - 0.5])


def ao_clicar_combinacao():
    # Clique na barra ou em qualquer ponto da coluna seleciona a combinação
    pts = pontos_clicados("rq6_combinacao")
    if not pts or pts[0].get("x") is None:
        st.session_state["sel_rq6_combinacao"] = None
        return
    linha = combinacoes.iloc[int(pts[0]["x"])]
    st.session_state["sel_rq6_combinacao"] = {"rotulo": linha["combo"],
                                              "ids": list(linha["studyids"])}


grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    grafico(fig, "rq6_combinacao", ao_clicar_combinacao)
with texto_col:
    cartoes([
        {"rotulo": "Two or more costs", "numero": f"{dois_ou_mais} of {total}",
         "texto": "Mostly time together with ciphertext size, communication or accuracy."},
        {"rotulo": "Only one cost", "numero": f"{algum_custo - dois_ou_mais} of {total}",
         "texto": "Usually computation time alone."},
    ], colunas=1)
st.caption(
    "Filled dots: costs in the combination. Bar: studies with exactly that combination. "
    f"Studies that report no cost ({int(n_custo.get('Not reported', 0))}) are left out. "
    "Click a column to list its studies."
)
mostrar_selecao("rq6_combinacao")


# ===========================================================================
# Baselines
# ===========================================================================
secao("Compared against what",
      "The reference each study uses to put its costs in context.")

grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq6_baseline", baselines, total=total)
with texto_col:
    cartoes([
        {"rotulo": "Plaintext computation",
         "numero": f"{int(n_baseline.get('Plaintext computation', 0))} of {total}",
         "texto": "The same computation without encryption: the direct price of HE."},
        {"rotulo": "No baseline", "numero": f"{int(n_baseline.get('No baseline', 0))} of {total}",
         "texto": "Costs, if any, are shown without a reference."},
    ], colunas=1)
st.caption("A study can count in several bars. Click a bar to list its studies.")
mostrar_selecao("rq6_baseline")


# ===========================================================================
# Custo x baseline
# ===========================================================================
secao("Which cost against which baseline", "How each cost was put in context.")

# Baselines na ordem das barras: mais frequente primeiro, "No baseline" por último
colunas_baseline = list(
    baselines.sort_values(["isnotinformed", "studies"], ascending=[True, False])["value"]
)
# VIEW: VwFacetCross — estudos por (custo, baseline)
celulas = run_query(
    "SELECT ValueA, ValueB, Studies, StudyIds FROM VwFacetCross "
    "WHERE FacetA = 'Cost type' AND FacetB = 'Baseline type'"
).set_index(["valuea", "valueb"])
matriz("rq6_cruzamento", linhas_custo, colunas_baseline, celulas)
st.caption(
    "Number of studies per reported cost and baseline. Studies that report no cost are left "
    "out. Click a cell to list its studies."
)
mostrar_selecao("rq6_cruzamento")