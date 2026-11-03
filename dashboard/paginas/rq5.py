"""
RQ5: onde e em que fase da operação do VANT cada operação de HE é executada.

  - local x operação (cifragem, avaliação homomórfica, decifragem), em matriz
    (VwFacetCount);
  - fluxo entre zonas, de onde se cifra até onde se decifra, em Sankey
    (ExecutedAt agrupado em zonas);
  - fluxos completos que se repetem (VwOperationFlowPattern);
  - fase da operação do VANT (VwFacetCount).
"""
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, CINZA, LARANJA, TITULO, VERDE, cabecalho, cartoes, layout_grafico,
                    secao, tabela)
from graficos import barras, contagem, matriz, mostrar, mostrar_selecao, total_estudos

cabecalho(
    5, "Where and when HE runs",
    "Where and at which stage of the UAV operation is each HE operation executed?",
    descricao=(
        "Using HE involves three operations that can run in different places: encryption, "
        "homomorphic evaluation and decryption. Where each one runs shows who sees the data in "
        "plaintext and who only handles ciphertexts. The page shows the location of each "
        "operation, how the data travel from encryption to decryption, which complete flows "
        "repeat across studies, and at which phase of the UAV operation (before, during or "
        "after the flight) HE is used."
    ),
)

total = total_estudos()
ETAPAS = ["Encryption", "Homomorphic evaluation", "Decryption"]
# Do próprio VANT até partes de fora da operação
LOCAIS = ["On board", "Peer UAV", "Sensor or external device", "Ground station/user",
          "Edge server", "Cloud", "Third party", "Not reported"]


# ===========================================================================
# Local x operação
# ===========================================================================
secao("Where each HE operation runs",
      "Who encrypts the data, who computes on the ciphertexts without the key, and who "
      "holds the key and decrypts the result.")

# As três operações, explicadas antes da matriz e do Sankey, que usam as mesmas colunas
OPERACOES = [
    ("Step 1", "Encryption",
     "Turns the data into ciphertexts. Whoever encrypts still sees the data in plaintext."),
    ("Step 2", "Homomorphic evaluation",
     "Computes on the ciphertexts without the secret key, so this party never sees the data."),
    ("Step 3", "Decryption",
     "Recovers the result in plaintext. Only the holder of the secret key can do it."),
]
st.html(
    '<div class="msl-grade c3">'
    + "".join(
        f'<div class="msl-cartao"><div class="rotulo">{passo}</div>'
        f'<div style="font-family: Poppins, sans-serif; font-weight: 700; font-size: 1rem; '
        f'color: {AZUL}; margin: .15rem 0 .3rem 0;">{nome}</div>'
        f'<div class="texto">{texto}</div></div>'
        for passo, nome, texto in OPERACOES
    )
    + "</div>"
)

# VIEW: VwFacetCount — estudos por local, uma faceta por operação
# ('Encryption location', 'Homomorphic evaluation location', 'Decryption location')
locais = run_query(
    "SELECT REPLACE(Facet, ' location', '') AS Operation, Value, Studies, StudyIds "
    "FROM VwFacetCount WHERE RQ = 'RQ5' AND Facet LIKE '% location'"
)
n_local = {(r.value, r.operation): int(r.studies) for r in locais.itertuples()}
celulas = locais.rename(columns={"value": "linha", "operation": "coluna"}) \
                .set_index(["linha", "coluna"])

# Avaliação longe do VANT: qualquer local de avaliação que não seja a bordo
# (nem "Not reported")
fora = int(run_query(
    "SELECT COUNT(DISTINCT StudyId) AS n FROM ExecutedAt "
    "WHERE OperationName = 'Homomorphic evaluation' "
    "AND LocationName NOT IN ('On board', 'Not reported')"
).iloc[0]["n"])

grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    matriz("rq5_local", LOCAIS, ETAPAS, celulas)
with texto_col:
    cartoes([
        {"rotulo": "Encryption on board",
         "numero": f"{n_local.get(('On board', 'Encryption'), 0)} of {total}",
         "texto": "The focal UAV encrypts its own data."},
        {"rotulo": "Computation away from the UAV", "numero": f"{fora} of {total}",
         "texto": "Homomorphic evaluation by a peer UAV, the ground, an edge server, "
                  "the cloud or a third party."},
        {"rotulo": "Decryption on board",
         "numero": f"{n_local.get(('On board', 'Decryption'), 0)} of {total}",
         "texto": "The UAV keeps the secret key and decrypts the result."},
    ], colunas=1)
st.caption(
    "Number of studies per location and HE operation. Rows go from the UAV itself to parties "
    "outside the operation. A study can have more than one location per operation. "
    "Click a cell to list its studies."
)
mostrar_selecao("rq5_local")


# ===========================================================================
# Fluxo entre zonas (Sankey)
# ===========================================================================
secao("From encryption to decryption",
      "How the data travel between the three steps, with the 8 locations grouped into 5 "
      "zones: where they are encrypted, where they are computed on and where the result "
      "is decrypted.")

ZONAS = ["UAVs", "Ground", "Edge / cloud", "Third party", "Not reported"]
CORES_ZONA = {"UAVs": AZUL, "Ground": LARANJA, "Edge / cloud": VERDE,
              "Third party": "#805AD5", "Not reported": CINZA}

# Zona de cada (estudo, operação). DISTINCT: dois locais da mesma zona
# (ex.: On board e Peer UAV) contam uma vez só para o estudo.
ZONA_SQL = """
    SELECT DISTINCT StudyId, OperationName,
           CASE WHEN LocationName IN ('On board', 'Peer UAV', 'Sensor or external device')
                     THEN 'UAVs'
                WHEN LocationName = 'Ground station/user'     THEN 'Ground'
                WHEN LocationName IN ('Edge server', 'Cloud') THEN 'Edge / cloud'
                WHEN LocationName = 'Third party'             THEN 'Third party'
                ELSE 'Not reported' END AS Zone
    FROM ExecutedAt
"""
# Nós: estudos distintos por (operação, zona)
nos = run_query(
    f"WITH Zona AS ({ZONA_SQL}) "
    "SELECT OperationName, Zone, COUNT(DISTINCT StudyId) AS Studies "
    "FROM Zona GROUP BY OperationName, Zone"
)
# Fitas: estudos distintos por par de zonas em operações consecutivas
fitas = run_query(
    f"""
    WITH Zona AS ({ZONA_SQL}),
    Passo (De, Para) AS (
        VALUES ('Encryption', 'Homomorphic evaluation'),
               ('Homomorphic evaluation', 'Decryption')
    )
    SELECT P.De AS StepFrom, P.Para AS StepTo, A.Zone AS ZoneFrom, B.Zone AS ZoneTo,
           COUNT(DISTINCT A.StudyId) AS Studies
    FROM Passo P
    JOIN Zona A ON A.OperationName = P.De
    JOIN Zona B ON B.OperationName = P.Para AND B.StudyId = A.StudyId
    GROUP BY P.De, P.Para, A.Zone, B.Zone
    """
)

n_no = {(r.operationname, r.zone): int(r.studies) for r in nos.itertuples()}


def rgba(hexa, alfa):
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


# Um nó por (etapa, zona) com estudos, na ordem de ZONAS, de cima para baixo.
# Posições fixas: etapas em três colunas e zonas empilhadas na mesma ordem.
indice, rotulos, cores, dicas, xs, ys = {}, [], [], [], [], []
FOLGA = 0.05
for i, etapa in enumerate(ETAPAS):
    presentes = [z for z in ZONAS if n_no.get((etapa, z))]
    soma = sum(n_no[(etapa, z)] for z in presentes)
    livre = 1 - FOLGA * (len(presentes) - 1)
    acumulado = 0.0
    for z in presentes:
        n = n_no[(etapa, z)]
        altura = livre * n / soma
        indice[(etapa, z)] = len(rotulos)
        rotulos.append(f"{z} {n}")
        cores.append(CORES_ZONA[z])
        dicas.append(f"<b>{z}</b><br>{etapa}: {n} studies")
        xs.append([0.001, 0.5, 0.999][i])
        ys.append(min(max(acumulado + altura / 2, 0.001), 0.999))
        acumulado += altura + FOLGA

fig = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        label=rotulos, color=cores, x=xs, y=ys, pad=18, thickness=14,
        line=dict(width=0), customdata=dicas, hovertemplate="%{customdata}<extra></extra>",
    ),
    link=dict(
        source=[indice[(r.stepfrom, r.zonefrom)] for r in fitas.itertuples()],
        target=[indice[(r.stepto, r.zoneto)] for r in fitas.itertuples()],
        value=[int(r.studies) for r in fitas.itertuples()],
        color=[rgba(CORES_ZONA[r.zonefrom], 0.35) for r in fitas.itertuples()],
        customdata=[f"<b>{r.zonefrom} → {r.zoneto}</b><br>{r.stepfrom} → {r.stepto}"
                    for r in fitas.itertuples()],
        hovertemplate="%{customdata}<br>%{value:.0f} studies<extra></extra>",
    ),
    textfont=dict(family="Inter, sans-serif", size=13, color=TITULO),
))
layout_grafico(fig, altura=560)
# Sankey não usa eixos: esconde os que layout_grafico configura
fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)
fig.update_layout(
    showlegend=False, margin=dict(l=10, r=10, t=50, b=10),
    annotations=[
        dict(x=x, y=1.06, xref="paper", yref="paper", xanchor=ancora, yanchor="bottom",
             text=f"<b>{etapa}</b>", showarrow=False,
             font=dict(family="Poppins, sans-serif", size=14, color=TITULO))
        for x, ancora, etapa in zip([0, 0.5, 1], ["left", "center", "right"], ETAPAS)
    ],
)
mostrar(fig)
st.caption(
    "UAVs = on board, peer UAV or on-board sensor · Ground = ground station or user · "
    "Edge / cloud = edge server or cloud. Ribbon width: studies with that pair of zones in "
    "consecutive steps; each ribbon takes the color of the zone the data come from. A study "
    "with two zones in one step contributes to two ribbons, so ribbons do not add up to "
    f"{total}. Hover a ribbon to see its count."
)


# ===========================================================================
# Fluxos completos que se repetem
# ===========================================================================
# VIEW: VwOperationFlowPattern — fluxos completos (cifra -> avalia -> decifra)
padroes = run_query(
    "SELECT EncryptAt, EvaluateAt, DecryptAt, Studies FROM VwOperationFlowPattern "
    "ORDER BY Studies DESC, EncryptAt, EvaluateAt, DecryptAt"
)
repetidos = padroes[padroes["studies"] > 1]

secao("Full flows are almost all different",
      f"{len(padroes)} distinct encryption → evaluation → decryption flows in {total} "
      "studies (locations, not zones); only these repeat:")
tabela(
    ["Encryption", "Homomorphic evaluation", "Decryption", "Studies"],
    [[r.encryptat, r.evaluateat, r.decryptat, int(r.studies)] for r in repetidos.itertuples()],
)


# ===========================================================================
# Fase da operação do VANT
# ===========================================================================
secao("Flight phase",
      "When the HE operations happen relative to the flight: before take-off, during the "
      "flight or after landing.")

grafico_col, _ = st.columns([3, 2])
with grafico_col:
    barras("rq5_fase", contagem("Operation phase"), total=total)
st.caption(
    "Not reported: operations not tied to the flight timeline, such as federated learning "
    "rounds. A study can count in several bars. Click a bar to list its studies."
)
mostrar_selecao("rq5_fase")