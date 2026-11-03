"""
RQ3: quais esquemas e bibliotecas de HE foram adotados.

  - estudos por esquema, com a cor da família (VwFacetCount, VwSchemeHierarchy);
  - família > esquema > biblioteca, em cartões com etiquetas (VwSchemeHierarchy);
  - o que os estudos informam sobre biblioteca, versão e parâmetros (VwReportingMatrix);
  - codificação do texto claro (VwFacetCount).
"""
import streamlit as st

from db import run_query
from estilo import (CORES_FAMILIA, CORES_FAMILIA_CLARO, cabecalho, cartoes, cartoes_esquemas,
                    rodape, secao)
from graficos import barras, contagem, mostrar_selecao, total_estudos

cabecalho(3, "HE schemes and libraries", "Which HE schemes and libraries have been adopted?")

total = total_estudos()
esquemas = contagem("HE scheme")
familias = contagem("HE family")
n_familia = dict(zip(familias["value"], familias["studies"]))
# VIEW: VwSchemeHierarchy — família > esquema > biblioteca > versão, com estudos
hierarquia = run_query(
    "SELECT Family, SchemeName, Library, LibraryVersion, Studies FROM VwSchemeHierarchy"
)
# Cor de cada esquema = cor da família dele (generic FHE fica verde: a família é conhecida)
familia_de = dict(zip(hierarquia["schemename"], hierarquia["family"]))
cor_esquema = {e: CORES_FAMILIA[f] for e, f in familia_de.items()}


# ===========================================================================
# Estudos por esquema
# ===========================================================================
secao("Studies by HE scheme")
cartoes([
    {"rotulo": "PHE · partially homomorphic", "cor": CORES_FAMILIA["PHE"],
     "numero": f"{int(n_familia.get('PHE', 0))} of {total}",
     "texto": "One operation over ciphertexts, such as addition in Paillier."},
    {"rotulo": "FHE · fully homomorphic", "cor": CORES_FAMILIA["FHE"],
     "numero": f"{int(n_familia.get('FHE', 0))} of {total}",
     "texto": "Additions and multiplications without a depth limit: CKKS, BFV, TFHE."},
    {"rotulo": "SHE · somewhat homomorphic", "cor": CORES_FAMILIA["SHE"],
     "numero": f"{int(n_familia.get('SHE', 0))} of {total}",
     "texto": "Both operations, but only up to a limited depth."},
    {"rotulo": "Family not determined", "cor": CORES_FAMILIA["Not determined"],
     "numero": f"{int(n_familia.get('Not determined', 0))} of {total}",
     "texto": "The study says it uses HE but does not name the scheme."},
])
# Nas barras, os esquemas não nomeados ("generic HE" e "generic FHE") viram um só
# "Not reported": a pergunta aqui é qual esquema, e nos dois casos o estudo não diz.
# VIEW: VwStudyFacet — uma linha por (estudo, esquema)
esquemas_barras = run_query(
    """
    SELECT CASE WHEN Value LIKE 'Not reported%' THEN 'Not reported' ELSE Value END AS Value,
           COUNT(DISTINCT StudyId)                  AS Studies,
           BOOL_OR(Value LIKE 'Not reported%')      AS IsNotInformed,
           ARRAY_AGG(DISTINCT StudyId)              AS StudyIds
    FROM VwStudyFacet
    WHERE Facet = 'HE scheme'
    GROUP BY 1
    """
)
generico_fhe = int(esquemas.loc[esquemas["value"] == "Not reported (generic FHE)", "studies"].sum())
barras("rq3_esquema", esquemas_barras, total, cores=cor_esquema)
st.caption(
    "Bar color: family of the scheme (blue PHE, green FHE, orange SHE). Not reported: the "
    f"scheme is not named ({generico_fhe} of these state FHE and count in the FHE card). "
    "A study can adopt more than one scheme. Click a bar to list its studies."
)
mostrar_selecao("rq3_esquema")


# ===========================================================================
# Família > esquema > biblioteca (icicle)
# ===========================================================================
secao("From family to library")

NAO_INFORMADO = ("Not reported", "Not applicable")
n_esquema = dict(zip(esquemas["value"], esquemas["studies"]))
blocos = []
for familia in [f for f in ("PHE", "FHE", "SHE", "Not determined") if f in set(hierarquia["family"])]:
    da_familia = hierarquia[hierarquia["family"] == familia]
    lista = []
    for esquema in sorted(set(da_familia["schemename"]), key=lambda e: (-n_esquema.get(e, 0), e)):
        bibs = da_familia[da_familia["schemename"] == esquema]
        # Bibliotecas nomeadas primeiro (mais estudos antes); "Not reported" e
        # "Not applicable" por último
        bibs = bibs.assign(nomeada=~bibs["library"].isin(NAO_INFORMADO))
        bibs = bibs.sort_values(["nomeada", "studies"], ascending=[False, False])
        lista.append({
            "nome": esquema,
            "studies": n_esquema.get(esquema, 0),
            "bibliotecas": [
                {"rotulo": b.library + ("" if b.libraryversion in NAO_INFORMADO else f" {b.libraryversion}"),
                 "n": int(b.studies), "informada": bool(b.nomeada)}
                for b in bibs.itertuples()
            ],
        })
    blocos.append({"nome": familia, "cor": CORES_FAMILIA[familia],
                   "claro": CORES_FAMILIA_CLARO[familia], "esquemas": lista})

cartoes_esquemas(blocos)
st.caption(
    "Each scheme with the libraries used to implement it (and the version, when reported); "
    "×n: number of studies. Dashed: library not reported, or not applicable because HE was "
    "not executed. A study with two schemes appears under both."
)


# ===========================================================================
# O que os estudos informam
# ===========================================================================
secao("Implementation details reported",
      "Whether the studies give the library, its version, the HE parameters and the security "
      "level. Without them, costs cannot be compared across studies.")

# VIEW: VwReportingMatrix — por estudo, TRUE/FALSE/NULL para cada item informado
rep = run_query(
    """
    SELECT COUNT(*) FILTER (WHERE HEExecuted)             AS Executados,
           COUNT(*) FILTER (WHERE LibraryReported)        AS Biblioteca,
           COUNT(*) FILTER (WHERE LibraryVersionReported) AS Versao,
           COUNT(*) FILTER (WHERE ParametersReported)     AS Parametros,
           COUNT(*) FILTER (WHERE SecurityLevelStated)    AS Seguranca
    FROM VwReportingMatrix
    """
).iloc[0]
# VIEW: VwStudyOverview — nível de segurança de cada esquema adotado (JSON Schemes)
niveis = run_query(
    """
    SELECT (S ->> 'SecurityLevelBits')::INTEGER AS Bits, COUNT(DISTINCT O.StudyId) AS Studies
    FROM VwStudyOverview O, jsonb_array_elements(O.Schemes) AS S
    WHERE S ->> 'SecurityLevelBits' IS NOT NULL
    GROUP BY 1 ORDER BY 1
    """
)
niveis_txt = ", ".join(f"{int(r.bits)}-bit: {int(r.studies)}" for r in niveis.itertuples())
executados = int(rep["executados"])

cartoes([
    {"rotulo": "Library named", "numero": f"{int(rep['biblioteca'])} of {executados}",
     "texto": "Studies that executed HE and name the library, including custom code."},
    {"rotulo": "Library version", "numero": f"{int(rep['versao'])} of {executados}",
     "texto": "Studies that executed HE and give the library version."},
    {"rotulo": "Parameters reported", "numero": f"{int(rep['parametros'])} of {total}",
     "texto": "Key size, polynomial degree, modulus or scale, at least in part."},
    {"rotulo": "Security level in bits", "numero": f"{int(rep['seguranca'])} of {total}",
     "texto": f"Stated explicitly ({niveis_txt}); key size alone does not count."},
])


# ===========================================================================
# Codificação do texto claro
# ===========================================================================
secao("How data become plaintexts",
      "Before encryption, real values such as positions, images or model weights must be "
      "turned into numbers the scheme accepts.")
grafico_col, texto_col = st.columns([2, 1], vertical_alignment="center")
with grafico_col:
    barras("rq3_codificacao", contagem("Plaintext encoding"), executados)
with texto_col:
    st.caption(
        f"How input data become plaintexts, only for the {executados} studies that executed HE. "
        "Fixed-point scaling turns real values into integers; CKKS encodes real values directly; "
        "SIMD packing puts several values in one ciphertext. Click a bar to list its studies."
    )
mostrar_selecao("rq3_codificacao")