"""Gera ./db/04_populate_studies.sql a partir da planilha de extracao limpa.

Entradas (data/clean/):
  extracao_corrigida.csv       planilha exportada (linha 0 = grupos de RQ, linha 1 = cabecalho)
  comportamento_por_parte.csv  comportamento de cada parte, quando o estudo tem mais de um
  local_fase_por_operacao.csv  local x fase de cada operacao, quando o estudo tem mais de uma fase
  detalhes_por_esquema.csv     parametros de cada esquema, quando o estudo tem mais de um

Tabelas de padronizacao (etl/normalizacao/), revisadas a mao:
  esquemas_por_estudo.csv      esquema, biblioteca/versao e codificacao de cada estudo
  hescheme.csv                 familia (PHE/SHE/FHE) de cada esquema

Uso:  python etl/gerar_populate.py
O script para com erro se algum valor nao bater com os catalogos de 02_populate_catalogs.sql.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLEAN = RAIZ / 'data' / 'clean'
NORM = RAIZ / 'etl' / 'normalizacao'
SAIDA = RAIZ / 'db' / '04_populate_studies.sql'
OPERACOES = ['Encryption', 'Homomorphic evaluation', 'Decryption']
COL_LOCAL = {'Encryption': 'Encryption location',
             'Homomorphic evaluation': 'HE location',
             'Decryption': 'Decryption location'}

erros = []
avisos = []


def ler(nome, pasta=CLEAN):
    with open(pasta / nome, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def limpa(v):
    """Tira os marcadores da extracao: (inferred), (?) e espacos."""
    v = re.sub(r'\s*\((inferred|\?)\)', '', v)
    return v.strip()


def separa(v):
    """Separa uma celula de selecao multipla nas virgulas fora de parenteses."""
    partes, nivel, atual = [], 0, ''
    for c in v:
        if c in '([':
            nivel += 1
        elif c in ')]':
            nivel -= 1
        if c == ',' and nivel == 0:
            partes.append(atual)
            atual = ''
        else:
            atual += c
    partes.append(atual)
    return [limpa(p) for p in partes if limpa(p)]


def catalogos():
    """Le os nomes validos de cada catalogo direto de 02_populate_catalogs.sql."""
    sql = (RAIZ / 'db' / '02_populate_catalogs.sql').read_text(encoding='utf-8')
    cat = {}
    for m in re.finditer(r'INSERT INTO (\w+)\s*\(Name\)\s*VALUES(.*?);', sql, re.S):
        cat[m.group(1)] = [v.replace("''", "'") for v in re.findall(r"'((?:[^']|'')*)'", m.group(2))]
    return cat


def no_catalogo(valores, catalogo, estudo, campo):
    """Confere cada valor contra o catalogo; aceita 'Other (texto)' como 'Other'."""
    saida = []
    for v in valores:
        if v not in catalogo:
            base = re.sub(r'\s*\(.*\)$', '', v)
            if base in catalogo:
                v = base
            else:
                erros.append(f'Estudo {estudo}, {campo}: "{v}" nao esta no catalogo')
                continue
        if v not in saida:
            saida.append(v)
    return saida


def q(v):
    """Literal SQL: NULL, numero, booleano ou texto com aspas escapadas."""
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert(tabela, colunas, linhas, extra=''):
    if not linhas:
        return f'-- {tabela}: nenhuma tupla\n'
    cab = f"INSERT INTO {tabela} ({', '.join(colunas)}){extra} VALUES\n"
    corpo = ',\n'.join('    (' + ', '.join(q(v) for v in l) + ')' for l in linhas)
    return cab + corpo + ';\n'


def main():
    cat = catalogos()
    bruto = list(csv.reader(open(CLEAN / 'extracao_corrigida.csv', encoding='utf-8', newline='')))
    cab = bruto[1]
    estudos = [dict(zip(cab, r)) for r in bruto[2:] if r and r[0].strip()]
    id_de = {e['Title'].strip(): i for i, e in enumerate(estudos, 1)}

    def estudo_id(titulo, arquivo):
        if titulo.strip() not in id_de:
            erros.append(f'{arquivo}: titulo nao encontrado na planilha: "{titulo[:60]}"')
            return None
        return id_de[titulo.strip()]

    # ---------- tabelas de padronizacao e arquivos de detalhe ----------
    familia = {r['Name']: r['Family'] for r in ler('hescheme.csv', NORM)}
    esquemas = defaultdict(list)
    for r in ler('esquemas_por_estudo.csv', NORM):
        sid = estudo_id(r['Study'], 'esquemas_por_estudo.csv')
        if sid is not None and int(r['StudyId']) != sid:
            erros.append(f'esquemas_por_estudo.csv: StudyId {r["StudyId"]} nao bate com a ordem da planilha ({sid})')
        if r['Scheme'] not in familia:
            erros.append(f'esquemas_por_estudo.csv: esquema "{r["Scheme"]}" sem familia em hescheme.csv')
        esquemas[sid].append(r)

    comportamento = defaultdict(lambda: defaultdict(list))
    for r in ler('comportamento_por_parte.csv'):
        sid = estudo_id(r['Study'], 'comportamento_por_parte.csv')
        comportamento[sid][r['Party']].append(r['Behavior'])

    local_fase = defaultdict(list)
    for r in ler('local_fase_por_operacao.csv'):
        sid = estudo_id(r['Study'], 'local_fase_por_operacao.csv')
        local_fase[sid].append((r['Operation'], r['Location'], r['Phase']))

    param_esquema = {}
    for r in ler('detalhes_por_esquema.csv'):
        sid = estudo_id(r['Study'], 'detalhes_por_esquema.csv')
        param_esquema[(sid, r['Scheme'])] = r['Parameters']
        bate = [e for e in esquemas[sid] if e['Scheme'] == r['Scheme']]
        if not bate:
            erros.append(f'detalhes_por_esquema.csv: estudo {sid} nao tem o esquema {r["Scheme"]} na padronizacao')
        elif (bate[0]['LibraryName'], bate[0]['LibraryVersion'], bate[0]['Encoding']) != \
                (r['Library'], r['LibraryVersion'], r['Encoding']):
            erros.append(f'detalhes_por_esquema.csv x esquemas_por_estudo.csv divergem no estudo {sid}, {r["Scheme"]}')

    # ---------- tuplas ----------
    T = defaultdict(list)
    bibliotecas = []
    for sid, e in enumerate(estudos, 1):
        val = e['Validated parts']
        m = re.search(r'HE operations:\s*(not executed|executed)', val)
        executado = bool(m) and m.group(1) == 'executed'
        if not m and val.strip() != 'Not validated':
            erros.append(f'Estudo {sid}: Validated parts sem "HE operations: executed|not executed"')

        lib = e['Library and version']
        mc = re.search(r'code:\s*(https?://\S+)', lib)
        # StudyCodeCK: HE executado exige link ou 'not available'; sem HE executado,
        # so guarda link quando houver (ex.: FLASH)
        code_url = mc.group(1) if mc else ('not available' if executado else None)
        doi = e['DOI'].strip() or None
        T['Study'].append([sid, e['Title'].strip(), doi, int(e['Year']), e['Problem addressed'].strip(),
                           code_url, executado, e['Metrics and values'].strip()])

        for autor in [a.strip() for a in re.split(r'\s+and\s+', e['Authors']) if a.strip()]:
            if [sid, autor] not in T['StudyAuthor']:
                T['StudyAuthor'].append([sid, autor])

        simples = [('ClassifiedAs', 'Research type', 'ResearchType'),
                   ('Addresses', 'UAV application', 'UAVApplication'),
                   ('ValidatedBy', 'Validation approach', 'ValidationApproach'),
                   ('Reports', 'Cost types', 'CostType'),
                   ('ComparesWith', 'Baseline type', 'BaselineType'),
                   ('Encrypts', 'Protected data', 'DataCategory')]
        for tabela, campo, catalogo in simples:
            for v in no_catalogo(separa(e[campo]), cat[catalogo], sid, campo):
                T[tabela].append([sid, v])

        # RQ7: partes e comportamentos
        partes = no_catalogo(separa(e['Protected from']), cat['AdversaryParty'], sid, 'Protected from')
        comps = separa(e['Adversary model'])
        for p in partes:
            T['AdversaryModel'].append([sid, p])
        if sid in comportamento:
            arq = comportamento[sid]
            if set(arq) != set(partes):
                erros.append(f'Estudo {sid}: partes de comportamento_por_parte.csv {sorted(arq)} != planilha {partes}')
            if {b for bs in arq.values() for b in bs} != set(comps):
                erros.append(f'Estudo {sid}: comportamentos do arquivo != planilha {comps}')
            for p, bs in arq.items():
                for b in bs:
                    T['AdversaryBehavior'].append([sid, p, b])
        elif len(comps) == 1:
            for p in partes:
                T['AdversaryBehavior'].append([sid, p, comps[0]])
        else:
            erros.append(f'Estudo {sid}: {len(comps)} comportamentos e nenhuma linha em comportamento_por_parte.csv')

        # RQ2/RQ3: esquemas adotados
        if not esquemas[sid]:
            erros.append(f'Estudo {sid}: sem linha em esquemas_por_estudo.csv')
        params_planilha = e['Parameters and security level'].strip()
        for r in esquemas[sid]:
            esq = r['Scheme']
            params = param_esquema.get((sid, esq), params_planilha)
            mb = re.search(r'(\d+)-bit (?:post-quantum |classical-)?security', params)
            bits = int(mb.group(1)) if mb else None
            libnome, libver = r['LibraryName'] or None, r['LibraryVersion'] or None
            if libnome and not executado:
                avisos.append(f'Estudo {sid}: biblioteca {libnome} ignorada (HEExecuted falso)')
                libnome = libver = None
            if libnome and (libnome, libver) not in bibliotecas:
                bibliotecas.append((libnome, libver))
            T['SchemeAdoption'].append([sid, esq, libnome, libver, params, bits])
            cods = [c.strip() for c in r['Encoding'].split(';') if c.strip()]
            if cods and not executado:
                avisos.append(f'Estudo {sid}: codificacao ignorada (HEExecuted falso)')
                cods = []
            for c in cods:
                T['PlainTextEncode'].append([sid, esq, c])

            for op in OPERACOES:
                T['OperationExecution'].append([sid, esq, op])

        # RQ4: local x fase de cada operacao
        fases = no_catalogo(separa(e['Operation phase']), cat['Phase'], sid, 'Operation phase')
        locais = {op: no_catalogo(separa(e[COL_LOCAL[op]]), cat['Location'], sid, COL_LOCAL[op])
                  for op in OPERACOES}
        if sid in local_fase:
            combos = local_fase[sid]
            for op in OPERACOES:
                if {l for o, l, f in combos if o == op} != set(locais[op]):
                    erros.append(f'Estudo {sid}: locais de {op} no arquivo != planilha {locais[op]}')
            if {f for o, l, f in combos} != set(fases):
                erros.append(f'Estudo {sid}: fases do arquivo != planilha {fases}')
        elif len(fases) == 1:
            combos = [(op, l, fases[0]) for op in OPERACOES for l in locais[op]]
        else:
            erros.append(f'Estudo {sid}: {len(fases)} fases e nenhuma linha em local_fase_por_operacao.csv')
            combos = []
        for r in esquemas[sid]:
            for op, l, f in combos:
                T['ExecutedAt'].append([sid, r['Scheme'], op, l, f])

    usados = []
    for _, esq, *_ in T['SchemeAdoption']:
        if esq not in usados:
            usados.append(esq)

    if erros:
        print('Carga NAO gerada. Corrija:', *erros, sep='\n  ')
        sys.exit(1)

    # ---------- SQL ----------
    blocos = [
        ('Esquemas usados pelos estudos e sua familia (etl/normalizacao/hescheme.csv)',
         'HEScheme', ['Name', 'Family'], [[s, familia[s]] for s in usados], ''),
        ('Bibliotecas (so de estudos com HEExecuted verdadeiro)',
         'Library', ['Name', 'Version'], [list(b) for b in bibliotecas], ''),
        ('Estudos: StudyId explicito = ordem da planilha (OVERRIDING SYSTEM VALUE)',
         'Study', ['StudyId', 'Title', 'DOI', 'Year', 'ProblemAddressed', 'CodeURL', 'HEExecuted', 'MetricsAndValues'],
         T['Study'], ' OVERRIDING SYSTEM VALUE'),
        ('Autores', 'StudyAuthor', ['StudyId', 'AuthorName'], T['StudyAuthor'], ''),
        ('RQ1: tipo de pesquisa', 'ClassifiedAs', ['StudyId', 'ResearchTypeName'], T['ClassifiedAs'], ''),
        ('RQ1: aplicacao', 'Addresses', ['StudyId', 'UAVApplicationName'], T['Addresses'], ''),
        ('RQ2/RQ3: esquema adotado, biblioteca e parametros', 'SchemeAdoption',
         ['StudyId', 'SchemeName', 'LibraryName', 'LibraryVersion', 'Parameters', 'SecurityLevelBits'],
         T['SchemeAdoption'], ''),
        ('RQ3: codificacao do texto claro', 'PlainTextEncode', ['StudyId', 'SchemeName', 'Encoding'],
         T['PlainTextEncode'], ''),
        ('RQ4: as tres operacoes de cada esquema adotado', 'OperationExecution',
         ['StudyId', 'SchemeName', 'OperationName'], T['OperationExecution'], ''),
        ('RQ4: onde e em que fase cada operacao roda', 'ExecutedAt',
         ['StudyId', 'SchemeName', 'OperationName', 'LocationName', 'PhaseName'], T['ExecutedAt'], ''),
        ('RQ5: validacao', 'ValidatedBy', ['StudyId', 'ValidationApproachName'], T['ValidatedBy'], ''),
        ('RQ6: custos reportados', 'Reports', ['StudyId', 'CostTypeName'], T['Reports'], ''),
        ('RQ6: baseline', 'ComparesWith', ['StudyId', 'BaselineTypeName'], T['ComparesWith'], ''),
        ('RQ7: dados protegidos', 'Encrypts', ['StudyId', 'DataCategoryName'], T['Encrypts'], ''),
        ('RQ7: de quem os dados sao protegidos', 'AdversaryModel', ['StudyId', 'PartyName'],
         T['AdversaryModel'], ''),
        ('RQ7: comportamento de cada parte', 'AdversaryBehavior', ['StudyId', 'PartyName', 'Behavior'],
         T['AdversaryBehavior'], ''),
    ]
    out = ['-- =====================================================================',
           '-- 04_populate_studies.sql',
           '-- Carga dos estudos do mapeamento. ARQUIVO GERADO por etl/gerar_populate.py:',
           '-- nao edite a mao; corrija a planilha ou etl/normalizacao/ e gere de novo.',
           '-- Targets fica vazia: a planilha nao liga cada dado a cada parte.',
           '-- =====================================================================',
           '', 'BEGIN;', '']
    for i, (titulo, tabela, cols, linhas, extra) in enumerate(blocos, 1):
        out += [f'-- {i}. {titulo}', insert(tabela, cols, linhas, extra)]
    out += ['-- A identidade de Study continua depois do ultimo id carregado',
            "SELECT setval(pg_get_serial_sequence('study', 'studyid'), (SELECT MAX(StudyId) FROM Study));", '',
            '-- Participacoes totais (P1-P4): se faltar algo, aborta e desfaz a carga inteira',
            'SELECT VerificaCarga();', '', 'COMMIT;', '']
    SAIDA.write_text('\n'.join(out), encoding='utf-8')

    print(f'Gerado {SAIDA.relative_to(RAIZ)}')
    for titulo, tabela, cols, linhas, extra in blocos:
        print(f'  {tabela:20s} {len(linhas):4d}')
    if avisos:
        print('Avisos:', *avisos, sep='\n  ')


if __name__ == '__main__':
    main()
