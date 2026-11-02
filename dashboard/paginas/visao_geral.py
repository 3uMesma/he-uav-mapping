"""
Visão geral: o que o mapeamento cobre, em números.

Nesta parte só os indicadores (VwKpi). A linha do tempo e o bubble plot de
Petersen entram na parte 2.
"""
import streamlit as st

from db import run_query
from estilo import abertura, cartoes, nota, rodape, secao, tabela

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
     "texto": "Studies that state the security level in bits; key size alone does not count."}
])

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
