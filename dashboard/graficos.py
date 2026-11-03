"""
Gráficos que se repetem nas páginas: barras, matriz de blocos arredondados e a
lista de estudos que aparece ao clicar.

Toda contagem chega pronta das views (com a coluna StudyIds); aqui só se desenha.
Cada gráfico tem uma chave; o clique guarda a seleção em
st.session_state["sel_<chave>"] e mostrar_selecao(chave) lista os estudos.
"""
import textwrap

import plotly.graph_objects as go
import streamlit as st

from db import run_query
from estilo import (AZUL, CINZA, TITULO, bloco_arredondado, cor_escala, grafico,
                    layout_grafico, lista_estudos, pontos_clicados)


def estudos_por_id(ids):
    # VIEW: VwStudyOverview — dados bibliográficos dos estudos selecionados
    return run_query(
        "SELECT StudyId, Year, Title, DoiUrl FROM VwStudyOverview "
        "WHERE StudyId = ANY(%s) ORDER BY Year, Title",
        (list(ids),),
    )


def total_estudos():
    # VIEW: VwKpi — total de estudos, para os "n of N"
    return int(run_query("SELECT Studies FROM VwKpi").iloc[0]["studies"])


def contagem(faceta):
    # VIEW: VwFacetCount — estudos por opção da faceta, com a lista de estudos
    return run_query(
        "SELECT Value, Studies, IsNotInformed, StudyIds FROM VwFacetCount "
        "WHERE Facet = %s ORDER BY Studies DESC, Value",
        (faceta,),
    )


def mostrar_selecao(chave):
    """Lista os estudos do último clique no gráfico de chave dada, se houver."""
    sel = st.session_state.get(f"sel_{chave}")
    if sel:
        lista_estudos(estudos_por_id(sel["ids"]), f'{sel["rotulo"]}: {len(sel["ids"])} studies')


def mostrar(fig):
    """Gráfico sem clique para listar estudos (ex.: icicle, que tem zoom próprio)."""
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})


def _quebra(texto, largura=16):
    return "<br>".join(textwrap.wrap(str(texto), largura))


# ---------------------------------------------------------------------------
# Barras horizontais: uma opção por linha, mais frequente no topo
# ---------------------------------------------------------------------------
def barras(chave, df, total=None, cores=None):
    """df: colunas value, studies, isnotinformed, studyids (como em VwFacetCount).
    Opções "não informado" ficam em cinza e por último. total, se dado, aparece
    no hover como "n of total". cores: dict opção -> cor (padrão: azul)."""
    cores = cores or {}
    df = df.sort_values(["isnotinformed", "studies"], ascending=[True, False])
    ordem = list(df["value"])[::-1]          # Plotly desenha o primeiro y embaixo
    df = df.set_index("value").loc[ordem].reset_index()

    fig = go.Figure(go.Bar(
        x=df["studies"], y=df["value"], orientation="h",
        marker=dict(color=[CINZA if n else cores.get(v, AZUL)
                           for v, n in zip(df["value"], df["isnotinformed"])],
                    cornerradius=4),
        text=df["studies"], textposition="outside", cliponaxis=False,
        textfont=dict(family="Inter, sans-serif", size=12, color=TITULO),
        hovertemplate="<b>%{y}</b><br>%{x} " + (f"of {total} " if total else "") +
                      "studies<extra></extra>",
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.4)),
    ))
    layout_grafico(fig, altura=60 + 30 * len(df))
    fig.update_layout(showlegend=False, bargap=0.35, margin=dict(l=10, r=30, t=10, b=10))
    fig.update_xaxes(visible=False, range=[0, df["studies"].max() * 1.12 + 0.5])
    fig.update_yaxes(categoryorder="array", categoryarray=ordem)

    def ao_clicar():
        pts = pontos_clicados(chave)
        if not pts:
            st.session_state[f"sel_{chave}"] = None
            return
        valor = pts[0]["y"]
        ids = list(df.loc[df["value"] == valor, "studyids"].iloc[0])
        st.session_state[f"sel_{chave}"] = {"rotulo": valor, "ids": ids} if ids else None

    grafico(fig, chave, ao_clicar)


# ---------------------------------------------------------------------------
# Matriz de blocos arredondados (gap map)
# ---------------------------------------------------------------------------
ALTURA_LINHA = 44


def matriz(chave, linhas, colunas, celulas, largura_maxima=1000, cinza=()):
    """linhas e colunas: listas de rótulos, na ordem de exibição (linha 0 no topo).
    celulas: DataFrame indexado por (linha, coluna), com studies e studyids.
    Célula ausente ou com 0 estudos aparece como "·" (lacuna).
    Com poucas colunas a matriz ocupa só parte da largura.
    cinza: células (linha, coluna) desenhadas em cinza, fora da escala de azul."""
    linhas_y = linhas[::-1]                  # Plotly desenha o primeiro y embaixo

    def n_de(a, c):
        try:
            return int(celulas.loc[(a, c), "studies"])
        except KeyError:
            return 0

    n_cel = {(a, c): n_de(a, c) for a in linhas_y for c in colunas}
    maior = max([n for k, n in n_cel.items() if k not in cinza] + [1])

    # O caminho do bloco é medido em unidades de categoria; os raios convertem
    # 9 px para essas unidades, com a largura estimada de cada coluna.
    fracao = min(1.0, 0.3 + 0.1 * len(colunas))
    raio_y = 9 / ALTURA_LINHA
    raio_x = 9 / (largura_maxima * fracao / len(colunas))
    formas = [
        dict(type="path", layer="below", line=dict(width=0),
             fillcolor="#E2E8F0" if (a, c) in cinza else cor_escala(n, maior),
             path=bloco_arredondado(colunas.index(c), linhas_y.index(a), 0.92, 0.78, raio_x, raio_y))
        for (a, c), n in n_cel.items() if n > 0
    ]

    # Um ponto invisível por célula, com o número escrito: recebe o clique e o
    # hover (o Streamlit só devolve seleção de pontos).
    pontos = [(a, c, n_cel[(a, c)]) for a in linhas_y for c in colunas]
    fig = go.Figure(go.Scatter(
        x=[c for _, c, _ in pontos], y=[a for a, _, _ in pontos],
        mode="markers+text", showlegend=False,
        text=[str(n) if n else "·" for _, _, n in pontos],
        textfont=dict(family="Inter, sans-serif", size=13,
                      color=["white" if n > maior / 2 and (a, c) not in cinza
                             else (TITULO if n else "#CBD5E0")
                             for a, c, n in pontos]),
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
                     tickvals=colunas, ticktext=[_quebra(c, 14) for c in colunas])
    fig.update_yaxes(categoryorder="array", categoryarray=linhas_y,
                     range=[-0.5, len(linhas_y) - 0.5])

    def ao_clicar():
        pts = pontos_clicados(chave)
        if not pts:
            st.session_state[f"sel_{chave}"] = None
            return
        a, c = pts[0]["y"], pts[0]["x"]
        ids = list(celulas.loc[(a, c), "studyids"]) if n_cel.get((a, c)) else []
        rotulo = f"{a} only" if (a, c) in cinza and a == c else f"{a} · {c}"
        st.session_state[f"sel_{chave}"] = {"rotulo": rotulo, "ids": ids} if ids else None

    if fracao < 1:
        coluna, _ = st.columns([fracao, 1 - fracao])
        with coluna:
            grafico(fig, chave, ao_clicar)
    else:
        grafico(fig, chave, ao_clicar)
