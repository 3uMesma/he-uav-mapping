"""
RQ4: como as propostas foram validadas e se as operações de HE foram executadas.

  - estudos por abordagem de validação, divididos em HE executado ou não
    (VwStudyFacet + VwStudyOverview);
  - abordagem de validação x família HE (VwFacetCross).
"""
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, CINZA, TITULO, cabecalho, cartoes, grafico, layout_grafico,
                    pontos_clicados, rodape, secao)
from graficos import contagem, matriz, mostrar_selecao, total_estudos

cabecalho(4, "Validation", "How have the proposals been validated, and which parts?")

total = total_estudos()
abordagens = contagem("Validation approach")
n_abordagem = dict(zip(abordagens["value"], abordagens["studies"]))
# Ordem das abordagens: mais frequente primeiro, "Not validated" por último
ordem = list(abordagens.sort_values(["isnotinformed", "studies"], ascending=[True, False])["value"])
nao_informado = set(abordagens.loc[abordagens["isnotinformed"], "value"])
# VIEW: VwKpi — quantos executaram HE
executados = int(run_query("SELECT HEExecuted FROM VwKpi").iloc[0]["heexecuted"])


# ===========================================================================
# Estudos por abordagem, divididos em HE executado ou não
# ===========================================================================
secao("Studies by validation approach",
      "Every approach each study used, split by whether the HE operations were actually "
      "executed. A study can count in several bars.")

# VIEWS: VwStudyFacet (abordagens de cada estudo) e VwStudyOverview (HE executado)
por_abordagem = run_query(
    """
    SELECT F.Value, O.HEExecuted,
           COUNT(DISTINCT F.StudyId)   AS Studies,
           ARRAY_AGG(DISTINCT F.StudyId) AS StudyIds
    FROM VwStudyFacet F
    JOIN VwStudyOverview O ON O.StudyId = F.StudyId
    WHERE F.Facet = 'Validation approach'
    GROUP BY F.Value, O.HEExecuted
    """
)
n_parte = {(r.value, bool(r.heexecuted)): int(r.studies) for r in por_abordagem.itertuples()}
linhas_y = ordem[::-1]                       # Plotly desenha o primeiro y embaixo

# Dois traços empilhados: HE executado (cheio) e não executado (hachurado).
# "Not validated" fica em cinza, como todo "não informado" do site.
SEGMENTOS = [True, False]
fig = go.Figure()
for executado in SEGMENTOS:
    cores = [CINZA if v in nao_informado else AZUL for v in linhas_y]
    fig.add_trace(go.Bar(
        x=[n_parte.get((v, executado), 0) for v in linhas_y], y=linhas_y, orientation="h",
        name="HE executed" if executado else "HE not executed",
        marker=dict(
            color=cores if executado else "white",
            line=dict(color=cores, width=1.5),
            pattern=dict(shape="" if executado else "/", fgcolor=cores, size=6, solidity=0.35),
        ),
        hovertemplate=(f"<b>%{{y}}</b><br>%{{x}} studies, HE "
                       f"{'executed' if executado else 'not executed'}<extra></extra>"),
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.4)),
    ))

# Números: dentro da parte cheia em branco; na hachurada, sobre um fundo branco
# para não se perderem nas listras; o total à direita da barra
notas = []
for v in linhas_y:
    a, b = n_parte.get((v, True), 0), n_parte.get((v, False), 0)
    if a:
        notas.append(dict(x=a / 2, y=v, text=str(a), showarrow=False,
                          font=dict(family="Inter, sans-serif", size=12, color="white")))
    if b:
        notas.append(dict(x=a + b / 2, y=v, text=str(b), showarrow=False, bgcolor="white",
                          borderpad=1, font=dict(family="Inter, sans-serif", size=12, color=TITULO)))
    notas.append(dict(x=a + b, y=v, text=f"<b>{a + b}</b>", showarrow=False, xanchor="left",
                      xshift=8, font=dict(family="Inter, sans-serif", size=12, color=TITULO)))

layout_grafico(fig, altura=80 + 42 * len(linhas_y))
fig.update_layout(barmode="stack", bargap=0.35, annotations=notas,
                  margin=dict(l=10, r=40, t=40, b=10))
fig.update_xaxes(visible=False, range=[0, max(n_abordagem.values()) * 1.08])
fig.update_yaxes(categoryorder="array", categoryarray=linhas_y)


def ao_clicar_abordagem():
    pts = pontos_clicados("rq4_abordagem")
    if not pts or pts[0].get("curve_number", 0) >= len(SEGMENTOS):
        st.session_state["sel_rq4_abordagem"] = None
        return
    executado = SEGMENTOS[pts[0]["curve_number"]]
    linha = por_abordagem[(por_abordagem["value"] == pts[0]["y"])
                          & (por_abordagem["heexecuted"] == executado)]
    ids = list(linha.iloc[0]["studyids"]) if len(linha) else []
    rotulo = f'{pts[0]["y"]} · HE {"executed" if executado else "not executed"}'
    st.session_state["sel_rq4_abordagem"] = {"rotulo": rotulo, "ids": ids} if ids else None


grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    grafico(fig, "rq4_abordagem", ao_clicar_abordagem)
with texto_col:
    cartoes([
        {"rotulo": "HE operations executed", "numero": f"{executados} of {total}",
         "texto": "Encryption, homomorphic evaluation and decryption actually ran; "
                  "the others only proposed or estimated them."},
        {"rotulo": "Embedded or UAV hardware",
         "numero": f"{int(n_abordagem.get('Embedded/UAV-representative hardware', 0))} of {total}",
         "texto": "Code ran on a single-board or companion computer, such as a Raspberry Pi."},
        {"rotulo": "Real flight",
         "numero": f"{int(n_abordagem.get('Field test or real flight', 0))} of {total}",
         "texto": "A real UAV flew during the evaluation."},
    ], colunas=1)
st.caption(
    "Bar length: studies that used the approach. Solid: HE operations executed; hatched: "
    "HE operations proposed but not executed. Click a bar segment to list its studies."
)
mostrar_selecao("rq4_abordagem")


# ===========================================================================
# Abordagem de validação x família HE
# ===========================================================================
secao("Validation by HE family",
      "Which families of HE schemes were validated with each approach.")

# VIEW: VwFacetCross — estudos por (abordagem de validação, família HE)
celulas = run_query(
    "SELECT ValueA, ValueB, Studies, StudyIds FROM VwFacetCross "
    "WHERE FacetA = 'Validation approach' AND FacetB = 'HE family'"
).set_index(["valuea", "valueb"])
matriz("rq4_familia", ordem, ["PHE", "SHE", "FHE", "Not determined"], celulas)
st.caption(
    "Number of studies per validation approach and family of the HE scheme, most frequent "
    "approach on top. A study can count in several rows. Click a cell to list its studies."
)
mostrar_selecao("rq4_familia")