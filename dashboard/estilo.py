"""
Identidade visual do dashboard, a mesma dos slides do mapeamento:
Poppins nos títulos, Inter no texto, fundo branco e azul como única cor de
destaque. Verde, laranja e cinza ficam para os gráficos (cinza = "não informado").

As páginas não escrevem CSS: usam as funções daqui (secao, cartoes, nota...).
"""
import html
from pathlib import Path

import streamlit as st

# Paleta dos slides
AZUL = "#2B6CB0"
VERDE = "#38A169"
LARANJA = "#DD6B20"
CINZA = "#A0AEC0"      # "Not reported", "Not stated" e afins, em todo o site
TITULO = "#2D3748"
TEXTO = "#4A5568"
SUAVE = "#718096"
BORDA = "#E2E8F0"
FUNDO_CARTAO = "#F7FAFC"

# Cor de cada família de esquema HE, igual ao gráfico por ano dos slides
CORES_FAMILIA = {"PHE": AZUL, "FHE": VERDE, "SHE": LARANJA, "Not determined": CINZA}

DRONE = Path(__file__).resolve().parent / "assets" / "drone.png"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700&display=swap');

.stApp p, .stApp li, .stApp td, .stApp th, .stApp label {{
  font-family: 'Inter', sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3 {{
  font-family: 'Poppins', sans-serif;
  color: {TITULO};
}}

/* Abertura da página inicial */
.msl-hero h1 {{
  font-family: 'Poppins', sans-serif; font-weight: 700;
  color: {AZUL}; font-size: 2.5rem; line-height: 1.2; margin: 0 0 .8rem 0; padding: 0;
}}
@media (max-width: 700px) {{ .msl-hero h1 {{ font-size: 1.9rem; }} }}
.msl-hero .sub {{ font-family: 'Inter', sans-serif; color: {TEXTO}; font-size: 1.05rem; margin: 0 0 .6rem 0; }}
.msl-hero .autoria {{ font-family: 'Inter', sans-serif; color: {SUAVE}; font-size: .95rem; }}

/* Título de seção */
.msl-sec {{
  font-family: 'Poppins', sans-serif; font-weight: 700; color: {TITULO};
  font-size: 1.55rem; line-height: 1.3; margin: 1.6rem 0 .4rem 0;
}}

/* Cartões: fundo cinza-claro e borda fina, sem faixa colorida.
   Grade com número fixo de colunas, que cai para 2 e 1 em telas estreitas. */
.msl-grade {{ display: grid; gap: 1rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.msl-grade.c3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.msl-grade.c2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.msl-grade.c1 {{ grid-template-columns: 1fr; }}
@media (max-width: 1000px) {{ .msl-grade:not(.c1), .msl-grade.c3 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@media (max-width: 560px)  {{ .msl-grade, .msl-grade.c3, .msl-grade.c2 {{ grid-template-columns: 1fr; }} }}
.msl-cartao {{
  background: {FUNDO_CARTAO}; border: 1px solid {BORDA};
  border-radius: 8px; padding: .9rem 1.1rem 1rem 1.1rem;
}}
.msl-cartao .rotulo {{
  font-family: 'Inter', sans-serif; font-size: .72rem; font-weight: 600;
  letter-spacing: .05em; text-transform: uppercase; color: {SUAVE};
}}
.msl-cartao .numero {{
  font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2.1rem;
  line-height: 1.25; color: {AZUL}; margin: .15rem 0 .25rem 0;
}}
.msl-cartao.laranja .numero {{ color: {LARANJA}; }}
.msl-cartao .texto {{ font-family: 'Inter', sans-serif; font-size: .88rem; color: {TEXTO}; line-height: 1.45; }}

/* Tabela simples: cabeçalho em cinza-claro, linhas separadas por borda fina */
.msl-tabela {{ border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: .95rem; margin-top: .3rem; }}
.msl-tabela th {{
  text-align: left; font-weight: 600; color: {TITULO};
  background: {FUNDO_CARTAO}; border-bottom: 1px solid {BORDA}; padding: .5rem 1rem;
}}
.msl-tabela td {{ color: {TEXTO}; border-bottom: 1px solid {BORDA}; padding: .5rem 1rem; }}
.msl-tabela td:first-child {{ font-weight: 600; color: {AZUL}; white-space: nowrap; }}

/* Nota com ícone de informação */
.msl-nota {{
  display: flex; gap: .7rem; align-items: flex-start;
  font-family: 'Inter', sans-serif; font-size: .9rem; color: {TEXTO};
  background: {FUNDO_CARTAO}; border: 1px solid {BORDA};
  border-radius: 8px; padding: .8rem 1.1rem; margin-top: 1.2rem;
}}
.msl-nota .icone {{
  flex: none; width: 1.15rem; height: 1.15rem; margin-top: .1rem;
  border: 1.5px solid {AZUL}; border-radius: 50%; color: {AZUL};
  display: flex; align-items: center; justify-content: center;
  font-family: 'Poppins', sans-serif; font-weight: 700; font-size: .72rem; line-height: 1;
}}

/* Rodapé */
.msl-rodape {{
  font-family: 'Inter', sans-serif; font-size: .85rem; color: {SUAVE}; text-align: center;
  border-top: 1px solid {BORDA}; margin-top: 2.5rem; padding-top: .8rem;
}}
.msl-rodape b {{ color: {AZUL}; font-weight: 600; }}
</style>
"""


def aplicar_estilo():
    """Injeta o CSS do site. Chamada uma vez, em app.py, antes das páginas."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _e(texto):
    return html.escape(str(texto))


def abertura(titulo, subtitulo, autoria):
    """Título grande em azul, como a capa dos slides, com o drone ao lado."""
    texto, imagem = st.columns([4, 1], vertical_alignment="center")
    with texto:
        st.html(
            f'<div class="msl-hero"><h1>{titulo}</h1>'
            f'<p class="sub">{subtitulo}</p>'
            f'<p class="autoria">{_e(autoria)}</p></div>'
        )
    with imagem:
        st.image(str(DRONE), width=220)


def secao(titulo):
    """Título de seção."""
    st.html(f'<div class="msl-sec">{_e(titulo)}</div>')


def cartoes(itens, colunas=4):
    """Grade de cartões (colunas: 1, 2, 3 ou 4). Cada item é um dict com:
    rotulo (texto pequeno em maiúsculas), numero, texto e, opcionalmente,
    cor='laranja' para destacar o número (padrão azul)."""
    blocos = []
    for i in itens:
        partes = [f'<div class="rotulo">{_e(i["rotulo"])}</div>']
        if "numero" in i:
            partes.append(f'<div class="numero">{_e(i["numero"])}</div>')
        if i.get("texto"):
            partes.append(f'<div class="texto">{_e(i["texto"])}</div>')
        blocos.append(f'<div class="msl-cartao {i.get("cor", "")}">{"".join(partes)}</div>')
    classe = {1: "c1", 2: "c2", 3: "c3"}.get(colunas, "")
    st.html(f'<div class="msl-grade {classe}">{"".join(blocos)}</div>')


def tabela(cabecalho, linhas):
    """Tabela simples. cabecalho: lista de títulos; linhas: lista de listas."""
    th = "".join(f"<th>{_e(c)}</th>" for c in cabecalho)
    tr = "".join("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in l) + "</tr>" for l in linhas)
    st.html(f'<table class="msl-tabela"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>')


def nota(texto):
    """Caixa de observação com ícone de informação."""
    st.html(
        f'<div class="msl-nota"><span class="icone">i</span>'
        f'<span>{_e(texto)}</span></div>'
    )


def rodape():
    st.html('<div class="msl-rodape"><b>ICMC/USP</b> · 2026</div>')


# ---------------------------------------------------------------------------
# Gráficos (Plotly)
# ---------------------------------------------------------------------------
def layout_grafico(fig, altura):
    """Aplica a identidade do site a uma figura Plotly: fundo transparente,
    Inter, sem grade e legenda em linha acima do gráfico."""
    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color=TEXTO),
        hoverlabel=dict(bgcolor="white", bordercolor=BORDA,
                        font=dict(family="Inter, sans-serif", size=13, color=TITULO)),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                    title_text="", font=dict(size=13)),
        showlegend=True,
    )
    # automargin: a margem cresce até caber o rótulo mais longo (sem cortar nomes)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=BORDA, ticks="",
                     automargin=True, tickfont=dict(color=TEXTO, size=12))
    fig.update_yaxes(showgrid=False, zeroline=False, ticks="",
                     automargin=True, tickfont=dict(color=TEXTO, size=12))
    return fig


def cor_escala(n, maior):
    """Azul da escala da matriz: de #DCEBFA (1 estudo) até AZUL (o maior valor)."""
    claro, escuro = (0xDC, 0xEB, 0xFA), (0x2B, 0x6C, 0xB0)
    t = (n - 1) / (maior - 1) if maior > 1 else 1
    return "#%02x%02x%02x" % tuple(round(claro[i] + (escuro[i] - claro[i]) * t) for i in range(3))


def bloco_arredondado(x, y, largura, altura, rx, ry):
    """Caminho SVG de um retângulo de cantos arredondados centrado em (x, y).
    Em eixo de categorias o Plotly mede o caminho pelo índice da categoria."""
    x0, x1, y0, y1 = x - largura / 2, x + largura / 2, y - altura / 2, y + altura / 2
    return (f"M{x0 + rx},{y0} L{x1 - rx},{y0} Q{x1},{y0} {x1},{y0 + ry} "
            f"L{x1},{y1 - ry} Q{x1},{y1} {x1 - rx},{y1} L{x0 + rx},{y1} "
            f"Q{x0},{y1} {x0},{y1 - ry} L{x0},{y0 + ry} Q{x0},{y0} {x0 + rx},{y0} Z")


def grafico(fig, chave, ao_clicar):
    """Mostra a figura com clique em pontos ligado. ao_clicar é chamada a
    cada clique e lê a seleção em st.session_state[chave]."""
    st.plotly_chart(
        fig, key=chave, on_select=ao_clicar, selection_mode="points",
        theme=None, config={"displayModeBar": False},
    )


def pontos_clicados(chave):
    """Pontos selecionados no gráfico de chave dada (lista vazia se nenhum)."""
    estado = st.session_state.get(chave)
    if not estado:
        return []
    return estado["selection"]["points"]


def lista_estudos(df, titulo):
    """Lista de estudos (colunas year, title, doiurl) como tabela simples,
    com o título levando ao DOI."""
    def md(texto):
        for c in "\\`*_[]|<>":
            texto = texto.replace(c, "\\" + c)
        return texto

    linhas = ["| Year | Study |", "| --- | --- |"]
    for r in df.itertuples():
        nome = f"[{md(r.title)}]({r.doiurl})" if r.doiurl else md(r.title)
        linhas.append(f"| {r.year} | {nome} |")
    st.markdown(f"**{md(titulo)}**")
    st.markdown("\n".join(linhas))
