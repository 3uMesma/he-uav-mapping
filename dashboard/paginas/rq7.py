"""
RQ7: modelo de ameaça. Quais dados são protegidos com HE, de quem e sob qual
comportamento do adversário.

  - estudos por categoria de dado protegido (VwFacetCount);
  - partes adversárias, divididas pelo comportamento assumido (AdversaryBehavior);
  - dado protegido x parte (VwFacetCross; a ligação é pelo estudo).
"""
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, CINZA, LARANJA, TITULO, cabecalho, cartoes, grafico, layout_grafico,
                    pontos_clicados, secao)
from graficos import barras, contagem, matriz, mostrar_selecao, total_estudos

cabecalho(
    7, "Threat model",
    "Which data are protected with HE, from whom, and under which adversary behavior?",
    descricao=(
        "A threat model states what must be kept secret and from whom. For each study, the "
        "page shows which data are encrypted with HE, which parties the data are protected "
        "from (an external eavesdropper, an edge or cloud server, another UAV or operator, an "
        "auditor or regulator, or an untrusted on-board component) and how those parties are "
        "assumed to behave: honest-but-curious parties follow the protocol but try to learn "
        "from what they see, while malicious parties may deviate from it."
    ),
)

total = total_estudos()
dados = contagem("Protected data")
partes = contagem("Protected from")
comportamentos = contagem("Adversary behavior")
n_dado = dict(zip(dados["value"], dados["studies"]))
n_parte = dict(zip(partes["value"], partes["studies"]))
n_comportamento = dict(zip(comportamentos["value"], comportamentos["studies"]))


def ordem(df):
    """Mais frequente primeiro, "não informado" por último (como nas barras)."""
    return list(df.sort_values(["isnotinformed", "studies"], ascending=[True, False])["value"])


ordem_dados, ordem_partes = ordem(dados), ordem(partes)

# Estudos que cifram mais de um tipo de dado, e estudos que cifram a posição ou
# a rota e citam um auditor/regulador entre os adversários (a ligação é pelo
# estudo: a extração não liga cada dado a cada parte)
extras = run_query(
    """
    SELECT (SELECT COUNT(*) FROM (SELECT StudyId FROM Encrypts
                                  GROUP BY StudyId HAVING COUNT(*) > 1) AS X) AS Varios,
           (SELECT COUNT(DISTINCT E.StudyId)
            FROM Encrypts E
            JOIN AdversaryModel A ON A.StudyId = E.StudyId
            WHERE E.DataCategoryName IN ('Position/trajectory', 'Planned route/flight path')
              AND A.PartyName = 'Auditor/regulator') AS Regulador
    """
).iloc[0]


# ===========================================================================
# Dados protegidos
# ===========================================================================
secao("What data are protected",
      "The data each study keeps encrypted while it is processed. A study can protect "
      "several kinds of data.")

grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq7_dado", dados, total=total)
with texto_col:
    cartoes([
        {"rotulo": "More than one kind of data", "numero": f"{int(extras['varios'])} of {total}",
         "texto": "Studies that encrypt data from two or more categories, such as position "
                  "and sensor readings."},
        {"rotulo": "Restricted zone or policy data",
         "numero": f"{int(n_dado.get('Restricted zone or policy data', 0))} of {total}",
         "texto": "No study encrypts no-fly zones or operating rules."},
    ], colunas=1)
st.caption(
    "A study can count in several bars. Other: data outside the listed categories. "
    "Restricted zone or policy data: an option of the extraction form that no study uses. "
    "Click a bar to list its studies."
)
mostrar_selecao("rq7_dado")


# ===========================================================================
# Partes adversárias x comportamento
# ===========================================================================
secao("Protected from whom",
      "The parties each study protects the data from, and how those parties are assumed "
      "to behave.")

# Estudos por (parte, comportamento), com a lista de estudos
por_parte = run_query(
    """
    SELECT PartyName, Behavior,
           COUNT(DISTINCT StudyId)               AS Studies,
           ARRAY_AGG(DISTINCT StudyId)           AS StudyIds
    FROM AdversaryBehavior
    GROUP BY PartyName, Behavior
    """
)
n_segmento = {(r.partyname, r.behavior): int(r.studies) for r in por_parte.itertuples()}
linhas_y = ordem_partes[::-1]                # Plotly desenha o primeiro y embaixo

# "Other" não aparece: nenhum estudo usou
SEGMENTOS = [("Honest-but-curious", AZUL), ("Malicious", LARANJA), ("Not stated", CINZA)]
fig = go.Figure()
for comportamento, cor in SEGMENTOS:
    fig.add_trace(go.Bar(
        x=[n_segmento.get((p, comportamento), 0) for p in linhas_y], y=linhas_y,
        orientation="h", name=comportamento,
        marker=dict(color=cor, line=dict(color="white", width=1)),
        hovertemplate=f"<b>%{{y}}</b><br>%{{x}} studies, {comportamento.lower()}<extra></extra>",
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.4)),
    ))

# Números dentro de cada parte em branco; à direita, o total de estudos da
# parte contando cada estudo uma vez (um estudo pode assumir dois comportamentos)
notas = []
for p in linhas_y:
    inicio = 0
    for comportamento, _ in SEGMENTOS:
        n = n_segmento.get((p, comportamento), 0)
        if n:
            notas.append(dict(x=inicio + n / 2, y=p, text=str(n), showarrow=False,
                              font=dict(family="Inter, sans-serif", size=12, color="white")))
        inicio += n
    notas.append(dict(x=inicio, y=p, text=f"<b>{int(n_parte.get(p, 0))}</b>", showarrow=False,
                      xanchor="left", xshift=8,
                      font=dict(family="Inter, sans-serif", size=12, color=TITULO)))

maior = max(sum(n_segmento.get((p, c), 0) for c, _ in SEGMENTOS) for p in linhas_y)
layout_grafico(fig, altura=80 + 42 * len(linhas_y))
fig.update_layout(barmode="stack", bargap=0.35, annotations=notas,
                  margin=dict(l=10, r=40, t=40, b=10))
fig.update_xaxes(visible=False, range=[0, maior * 1.08])
fig.update_yaxes(categoryorder="array", categoryarray=linhas_y)


def ao_clicar_parte():
    pts = pontos_clicados("rq7_parte")
    if not pts or pts[0].get("curve_number", 0) >= len(SEGMENTOS):
        st.session_state["sel_rq7_parte"] = None
        return
    comportamento = SEGMENTOS[pts[0]["curve_number"]][0]
    linha = por_parte[(por_parte["partyname"] == pts[0]["y"])
                      & (por_parte["behavior"] == comportamento)]
    ids = list(linha.iloc[0]["studyids"]) if len(linha) else []
    rotulo = f'{pts[0]["y"]} · {comportamento.lower()}'
    st.session_state["sel_rq7_parte"] = {"rotulo": rotulo, "ids": ids} if ids else None


grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    grafico(fig, "rq7_parte", ao_clicar_parte)
with texto_col:
    cartoes([
        {"rotulo": "Honest-but-curious", "cor": AZUL,
         "numero": f"{int(n_comportamento.get('Honest-but-curious', 0))} of {total}",
         "texto": "Follows the protocol but tries to learn from what it sees."},
        {"rotulo": "Malicious", "cor": LARANJA,
         "numero": f"{int(n_comportamento.get('Malicious', 0))} of {total}",
         "texto": "May deviate from the protocol, tamper with or drop data."},
        {"rotulo": "Behavior not stated", "cor": CINZA,
         "numero": f"{int(n_comportamento.get('Not stated', 0))} of {total}",
         "texto": "The party is named, but not how it behaves."},
    ], colunas=1)

# Estudos que assumem mais de um comportamento para a mesma parte
duplos = run_query(
    """
    SELECT PartyName, COUNT(*) AS Studies
    FROM (SELECT StudyId, PartyName FROM AdversaryBehavior
          GROUP BY StudyId, PartyName HAVING COUNT(*) > 1) AS Dois
    GROUP BY PartyName ORDER BY Studies DESC, PartyName
    """
)
texto_duplos = ""
if len(duplos):
    lista = " and ".join(f"{int(r.studies)} for {r.partyname.lower()}" for r in duplos.itertuples())
    texto_duplos = f" A study can assume two behaviors for the same party ({lista})."
st.caption(
    "Bar: studies that protect against the party, split by the assumed behavior; the number "
    f"at the right counts each study once.{texto_duplos} A study can count in several bars. "
    "Click a bar segment to list its studies."
)
mostrar_selecao("rq7_parte")


# ===========================================================================
# Dado protegido x parte
# ===========================================================================
secao("Which data, protected from whom",
      "Number of studies per kind of protected data and adversary party, linked through the "
      "study.")

# VIEW: VwFacetCross — estudos por (dado protegido, parte)
celulas = run_query(
    "SELECT ValueA, ValueB, Studies, StudyIds FROM VwFacetCross "
    "WHERE FacetA = 'Protected data' AND FacetB = 'Protected from'"
).set_index(["valuea", "valueb"])
matriz("rq7_cruzamento", ordem_dados, ordem_partes, celulas)
st.caption(
    "Number of studies that encrypt the data in the row and protect against the party in the "
    "column. The extraction links both through the study, not each piece of data to each "
    "party. Click a cell to list its studies."
)
mostrar_selecao("rq7_cruzamento")