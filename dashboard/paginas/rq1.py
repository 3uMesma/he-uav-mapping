"""
RQ1: que tipos de pesquisa foram feitos (classificação de Wieringa et al.).

  - estudos por tipo de pesquisa (VwFacetCount);
  - o esquema de classificação, com a definição de cada tipo e a regra
    adotada no mapeamento para Validation research.
"""
import streamlit as st

from estilo import cabecalho, cartoes, nota, secao, tabela
from graficos import barras, contagem, mostrar_selecao, total_estudos

cabecalho(
    1, "Research type", "What types of research have been conducted?",
    descricao=(
        "The primary studies are classified by research type following the scheme of "
        "Wieringa et al. (2005), widely adopted in systematic mapping studies. The research "
        "type describes the nature of each contribution: proposing a new HE-based solution, "
        "validating it outside real UAV operation, evaluating it in real operation, structuring "
        "the field, or reporting opinions and experiences."
    ),
)

total = total_estudos()
tipos = contagem("Research type")
n_tipo = dict(zip(tipos["value"], tipos["studies"]))

secao("Studies by research type",
      "Number of studies per research type. A study can have more than one type, usually "
      "Solution proposal together with Validation research.")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq1_tipo", tipos, total)
with texto_col:
    cartoes([
        {"rotulo": "Solution proposals", "numero": f"{int(n_tipo['Solution proposal'])} of {total}",
         "texto": "Almost every study proposes a new HE-based solution."},
        {"rotulo": "Validation research", "numero": f"{int(n_tipo['Validation research'])} of {total}",
         "texto": "Executed or measured the HE operations outside real practice "
                  "(simulation, computer, embedded hardware)."},
        {"rotulo": "Evaluation research", "numero": f"{int(n_tipo['Evaluation research'])} of {total}",
         "texto": "Solution already in use in real UAV operations and evaluated there. "
                  "Test flights by the authors count as Validation research."},
    ], colunas=1)
st.caption(
    "Classification by Wieringa et al. (2005). Click a bar to list its studies."
)
mostrar_selecao("rq1_tipo")


# ===========================================================================
# Esquema de classificação
# ===========================================================================
secao("Classification scheme",
      "The six research types of Wieringa et al. (2005) and the number of studies in each.")

DEFINICOES = [
    ("Solution proposal", "Proposes a new solution to a problem, or a significant revision of an "
                          "existing one, and argues for its relevance."),
    ("Validation research", "Investigates the properties of a new solution that has not yet been "
                            "used in practice, for example in a simulation or laboratory setting."),
    ("Evaluation research", "Investigates a solution used in practice, showing how it was applied "
                            "and what its consequences were."),
    ("Philosophical paper", "Structures the field in a new way, for example through a taxonomy or "
                            "a conceptual framework."),
    ("Opinion paper", "Presents the personal opinion of the authors about a topic, without relying "
                      "on research methods."),
    ("Experience report", "Reports the personal experience of the authors on how something was "
                          "done in practice."),
]
tabela(["Research type", "Definition"],
       [[t, d] for t, d in DEFINICOES])

nota(
    "Decision adopted in this mapping: a study is classified as Validation research only when "
    "its HE operations (encryption, homomorphic evaluation, decryption) were actually executed "
    "or measured, in simulation, on a general-purpose computer or on embedded hardware. "
    "Studies whose HE costs were only estimated analytically are not counted as Validation "
    "research. "
    "Evaluation research requires the solution to be used in real UAV operation."
)
