"""
Explorador de estudos: busca, filtros pelas facetas e uma tabela com um
estudo por linha. Clicar numa linha abre a extração completa do estudo.

Tudo vem da VwStudyOverview (uma linha por estudo, com as facetas em JSON);
os filtros são aplicados aqui, sobre os 37 estudos já carregados.
"""
import json

import pandas as pd
import streamlit as st

from db import run_query
from estilo import tabela

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
# VIEW: VwStudyOverview — um estudo por linha, com facetas e esquemas em JSON
estudos = run_query(
    "SELECT StudyId, Title, Year, DoiUrl, Authors, ProblemAddressed, HEExecuted, "
    "CodeURL, MetricsAndValues, Facets, Schemes FROM VwStudyOverview"
)


def _json(valor, vazio):
    """psycopg2 já devolve JSONB como dict/list; texto é convertido por segurança."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return vazio
    return json.loads(valor) if isinstance(valor, str) else valor


estudos["facets"] = estudos["facets"].apply(lambda v: _json(v, {}))
estudos["schemes"] = estudos["schemes"].apply(lambda v: _json(v, []))
estudos["temcodigo"] = estudos["codeurl"].fillna("").astype(str).str.startswith("http")
total = len(estudos)


def valores(faceta):
    """Opções de uma faceta que aparecem nos estudos, da mais frequente à menos."""
    contagem = pd.Series([v for f in estudos["facets"] for v in f.get(faceta, [])]).value_counts()
    return sorted(contagem.index, key=lambda v: (-contagem[v], v))


# Filtros principais e os "mais filtros" (RQ5-RQ7): rótulo -> faceta
FILTROS = {
    "Research type": "Research type",
    "UAV application": "UAV application",
    "HE family": "HE family",
    "Validation approach": "Validation approach",
}
MAIS_FILTROS = {
    "HE scheme": "HE scheme",
    "Encryption at": "Encryption location",
    "Homomorphic evaluation at": "Homomorphic evaluation location",
    "Decryption at": "Decryption location",
    "Flight phase": "Operation phase",
    "Reported cost": "Cost type",
    "Baseline": "Baseline type",
    "Protected data": "Protected data",
    "Protected from": "Protected from",
    "Adversary behavior": "Adversary behavior",
}
ANO_MIN, ANO_MAX = int(estudos["year"].min()), int(estudos["year"].max())


PADRAO = {"f_busca": "", "f_ano": (ANO_MIN, ANO_MAX), "f_executado": False, "f_codigo": False,
          **{f"f_{faceta}": [] for faceta in list(FILTROS.values()) + list(MAIS_FILTROS.values())}}


def limpar_filtros():
    for chave, valor in PADRAO.items():
        st.session_state[chave] = valor


# Valores iniciais pelo session_state (e não pelo parâmetro value dos
# widgets), para o botão "Clear filters" poder reiniciá-los sem aviso.
for chave, valor in PADRAO.items():
    st.session_state.setdefault(chave, valor)


def md(texto):
    """Escapa os caracteres que o Markdown do Streamlit interpretaria
    (ex.: "J* ... J*" viraria itálico, "$" viraria fórmula)."""
    for c in "\\`*_[]$~<>|":
        texto = texto.replace(c, "\\" + c)
    return texto


# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.html(
    '<div class="msl-cab"><div class="rotulo">Study explorer</div><h1>Studies</h1>'
    f'<p class="pergunta">All {total} primary studies of the mapping in one table, one row per '
    'study, with the attributes extracted to answer the research questions. The filters narrow '
    'the list by any combination of attributes, from research type and HE family to where the '
    'HE operations run and the threat model. Selecting a row opens the full extraction of that '
    'study, and the DOI link leads to the paper.</p></div>'
)

# ---------------------------------------------------------------------------
# Painel de filtros
# ---------------------------------------------------------------------------
with st.container(border=True):
    busca = st.text_input("Search", key="f_busca", label_visibility="collapsed",
                          placeholder="Search title, author or problem…")

    colunas = st.columns([1.1, 1, 1, 1, 1])
    with colunas[0]:
        anos = st.slider("Year", ANO_MIN, ANO_MAX, key="f_ano")
    escolhas = {}
    for coluna, (rotulo, faceta) in zip(colunas[1:], FILTROS.items()):
        with coluna:
            escolhas[faceta] = st.multiselect(rotulo, valores(faceta), key=f"f_{faceta}",
                                              placeholder="Any")

    chave_exec, chave_cod, _, limpar = st.columns([1, 1, 2.5, 0.8], vertical_alignment="center")
    with chave_exec:
        so_executado = st.toggle("HE executed only", key="f_executado")
    with chave_cod:
        so_codigo = st.toggle("Code available only", key="f_codigo")
    with limpar:
        st.button("Clear filters", on_click=limpar_filtros, type="tertiary")

    with st.expander("More filters: HE scheme, where HE runs, costs, threat model"):
        colunas = st.columns(3)
        for i, (rotulo, faceta) in enumerate(MAIS_FILTROS.items()):
            with colunas[i % 3]:
                escolhas[faceta] = st.multiselect(rotulo, valores(faceta), key=f"f_{faceta}",
                                                  placeholder="Any")

# ---------------------------------------------------------------------------
# Aplicação dos filtros: dentro de uma faceta basta uma das opções escolhidas;
# entre facetas, todas precisam valer.
# ---------------------------------------------------------------------------
filtro = estudos["year"].between(*anos)
if busca.strip():
    termo = busca.strip().lower()
    texto = (estudos["title"].fillna("") + " " + estudos["authors"].fillna("") + " "
             + estudos["problemaddressed"].fillna("")).str.lower()
    filtro &= texto.str.contains(termo, regex=False)
if so_executado:
    filtro &= estudos["heexecuted"].astype(bool)
if so_codigo:
    filtro &= estudos["temcodigo"]
for faceta, escolhidos in escolhas.items():
    if escolhidos:
        filtro &= estudos["facets"].apply(lambda f: bool(set(f.get(faceta, [])) & set(escolhidos)))

resultado = estudos[filtro].sort_values(["year", "title"], ascending=[False, True])

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------
st.markdown(f"**{len(resultado)}** of {total} studies")


def primeiro_autor(autores):
    nomes = [a.strip() for a in str(autores or "").split(";") if a.strip()]
    if not nomes:
        return ""
    return nomes[0] + (" et al." if len(nomes) > 1 else "")


tabela_df = pd.DataFrame({
    "Year": resultado["year"].astype(int),
    "Title": resultado["title"],
    "Authors": resultado["authors"].apply(primeiro_autor),
    "HE scheme": resultado["schemes"].apply(lambda s: [e["Scheme"] for e in s]),
    "UAV application": resultado["facets"].apply(lambda f: f.get("UAV application", [])),
    "Validation": resultado["facets"].apply(lambda f: f.get("Validation approach", [])),
    "HE executed": resultado["heexecuted"].astype(bool),
    "Code": resultado["temcodigo"],
    "Link": resultado["doiurl"],
}).reset_index(drop=True)

# A chave muda junto com o conjunto filtrado: a seleção antiga não passa a
# apontar para outro estudo quando os filtros mudam.
chave_tabela = "tabela_estudos_" + "_".join(map(str, resultado["studyid"]))

# A tabela nativa só seleciona células; para o clique parecer seleção de
# linha, a linha da célula clicada (guardada no session_state desde o clique)
# é pintada inteira de azul-claro.
estado = st.session_state.get(chave_tabela) or {}
celulas_antes = (estado.get("selection") or {}).get("cells") or []
linha_marcada = int(celulas_antes[0][0]) if celulas_antes else None
tabela_vista = tabela_df.style.apply(
    lambda r: ["background-color: #DCEBFA" if r.name == linha_marcada else ""] * len(r), axis=1
)

evento = st.dataframe(
    tabela_vista, hide_index=True,
    on_select="rerun", selection_mode="single-cell", key=chave_tabela,
    column_config={
        "Year": st.column_config.NumberColumn(format="%d", width="small"),
        "Title": st.column_config.TextColumn(width="large"),
        "Authors": st.column_config.TextColumn(width="medium"),
        "HE scheme": st.column_config.ListColumn(width="medium"),
        "UAV application": st.column_config.ListColumn(width="medium"),
        "Validation": st.column_config.ListColumn(width="medium"),
        "HE executed": st.column_config.CheckboxColumn("HE exec.", width="small"),
        "Code": st.column_config.CheckboxColumn(width="small"),
        "Link": st.column_config.LinkColumn(display_text="DOI ↗", width="small"),
    },
)
st.caption(
    "Click a row to see the full extraction of that study. Click a column header "
    "to sort; the icons above the table search, download the filtered table as CSV and open "
    "it full screen. Filters: any of the options chosen in one filter, and all filters together."
)


# ---------------------------------------------------------------------------
# Detalhes do estudo (janela)
# ---------------------------------------------------------------------------
@st.dialog("Study details", width="large")
def detalhes(estudo):
    f = estudo["facets"]
    tipos = " · ".join(f.get("Research type", []))
    st.caption(f"{int(estudo['year'])} · {tipos}")
    st.markdown(f"#### [{md(str(estudo['title']))}]({estudo['doiurl']})")
    st.caption(md(str(estudo["authors"] or "")))
    st.markdown(
        "HE operations executed: " + ("Yes" if estudo["heexecuted"] else "No") + " · "
        + "Code: " + (f"[available]({estudo['codeurl']})" if estudo["temcodigo"] else "not available")
    )

    st.markdown("**Problem addressed**")
    st.markdown(md(str(estudo["problemaddressed"] or "Not reported")))

    st.markdown("**HE schemes**")
    tabela(
        ["Scheme", "Family", "Library", "Version", "Security (bits)"],
        [[e["Scheme"], e["Family"], e.get("Library") or "—", e.get("LibraryVersion") or "—",
          e.get("SecurityLevelBits") or "—"] for e in estudo["schemes"]],
    )

    st.markdown("**Classification**")
    linhas = [
        ("UAV application", "UAV application"),
        ("Validation", "Validation approach"),
        ("Encryption at", "Encryption location"),
        ("Evaluation at", "Homomorphic evaluation location"),
        ("Decryption at", "Decryption location"),
        ("Flight phase", "Operation phase"),
        ("Costs", "Cost type"),
        ("Baselines", "Baseline type"),
        ("Protected data", "Protected data"),
        ("Protected from", "Protected from"),
        ("Adversary behavior", "Adversary behavior"),
    ]
    tabela(["Aspect", "Value"], [[rotulo, ", ".join(f.get(faceta, [])) or "—"] for rotulo, faceta in linhas])

    st.markdown("**Reported metrics**")
    st.markdown(md(str(estudo["metricsandvalues"] or "Not reported")))


# Clique em qualquer célula abre a janela do estudo daquela linha (menos na
# coluna Link, que já abre o DOI). A janela abre só quando a célula clicada
# muda, para não reabrir a cada interação com os filtros.
celulas_sel = list(evento.selection.get("cells", [])) if evento is not None else []
if celulas_sel:
    linha, coluna = celulas_sel[0]
    marca = (int(linha), str(coluna))
    if st.session_state.get("celula_aberta") != marca:
        st.session_state["celula_aberta"] = marca
        if coluna != "Link":
            detalhes(resultado.iloc[int(linha)])
else:
    st.session_state["celula_aberta"] = None