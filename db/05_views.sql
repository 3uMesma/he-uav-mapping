-- =====================================================================
-- 05_views.sql
-- Visões de consulta do dashboard. O site só lê estas visões:
-- nenhuma regra de contagem fica no front.
--
-- Regra geral: quase toda faceta é multivalorada (um estudo pode ter
-- vários valores na mesma faceta). Por isso:
--   - toda contagem é COUNT(DISTINCT StudyId);
--   - percentual é "% dos estudos" e NÃO soma 100% dentro da faceta;
--   - cada contagem traz StudyIds, a lista de estudos que a produz,
--     para o site abrir os estudos de uma barra, bolha ou célula.
--
-- Visões:
--   1  VwStudyFacet            formato longo: (estudo, faceta, valor)
--   2  VwFacetOption           todas as opções de cada faceta, usadas ou não
--   3  VwFacetCount            contagem por opção
--   4  VwFacetCross            contagem por par de opções (MATERIALIZADA)
--   5  VwStudyOverview         uma linha por estudo
--   6  VwKpi                   números da página inicial
--   7  VwOperationFlow         onde cifra, computa e decifra, por estudo
--   8  VwOperationFlowPattern  padrões de fluxo e quantos estudos seguem cada um
--   9  VwValidationLadder      degrau mais alto de validação por estudo
--   10 VwReportingMatrix       o que cada estudo informa (sim/não)
--   11 VwSchemeHierarchy       família > esquema > biblioteca > versão
--   12 VwThreatMatrix          dado protegido x parte x comportamento
--   13 VwAuthor                autores e número de estudos
--   14 VwCoAuthorship          pares de coautores
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. VwStudyFacet
-- Base de quase todas as outras. Uma linha por (estudo, faceta, valor).
-- UNION tira repetições
-- ---------------------------------------------------------------------
CREATE VIEW VwStudyFacet (StudyId, RQ, Facet, Value) AS
      SELECT StudyId, 'General', 'Year', Year::TEXT
      FROM Study
UNION SELECT StudyId, 'RQ1', 'Research type', ResearchTypeName
      FROM ClassifiedAs
UNION SELECT StudyId, 'RQ2', 'UAV application', UAVApplicationName
      FROM Addresses
UNION SELECT StudyId, 'RQ3', 'HE scheme', SchemeName
      FROM SchemeAdoption
UNION SELECT A.StudyId, 'RQ3', 'HE family', H.Family
      FROM SchemeAdoption A
      JOIN HEScheme H ON H.Name = A.SchemeName
UNION SELECT StudyId, 'RQ3', 'Library', COALESCE(LibraryName, 'Not applicable')
      FROM SchemeAdoption
UNION SELECT StudyId, 'RQ3', 'Plaintext encoding', Encoding
      FROM PlainTextEncode
UNION SELECT StudyId, 'RQ4', 'Validation approach', ValidationApproachName
      FROM ValidatedBy
UNION SELECT StudyId, 'RQ4', 'HE executed', CASE WHEN HEExecuted THEN 'Yes' ELSE 'No' END
      FROM Study
UNION SELECT StudyId, 'RQ4', 'Code availability',
             CASE WHEN CodeURL LIKE 'http%' THEN 'Available' ELSE 'Not available' END
      FROM Study
UNION SELECT StudyId, 'RQ5', OperationName || ' location', LocationName
      FROM ExecutedAt
UNION SELECT StudyId, 'RQ5', 'Operation phase', PhaseName
      FROM ExecutedAt
UNION SELECT StudyId, 'RQ6', 'Cost type', CostTypeName
      FROM Reports
UNION SELECT StudyId, 'RQ6', 'Baseline type', BaselineTypeName
      FROM ComparesWith
UNION SELECT StudyId, 'RQ7', 'Protected data', DataCategoryName
      FROM Encrypts
UNION SELECT StudyId, 'RQ7', 'Protected from', PartyName
      FROM AdversaryModel
UNION SELECT StudyId, 'RQ7', 'Adversary behavior', Behavior
      FROM AdversaryBehavior;


-- ---------------------------------------------------------------------
-- 2. VwFacetOption
-- Todas as opções de cada faceta, inclusive as que nenhum estudo usou:
-- é o que faz a lacuna aparecer como célula vazia no gap map.
-- Família e comportamento vêm de CHECK: a lista abaixo repete a da CHECK 
-- em 01_create_tables.sql. IsNotInformed marca 'Not reported', 'Not stated', 
-- 'No baseline' etc., que o site pinta de cinza em todos os gráficos.
-- ---------------------------------------------------------------------
CREATE VIEW VwFacetOption (RQ, Facet, Value, IsNotInformed) AS
WITH Opcao (RQ, Facet, Value) AS (
              SELECT 'General', 'Year', G::TEXT
              FROM generate_series((SELECT MIN(Year)::INTEGER FROM Study),
                                   (SELECT MAX(Year)::INTEGER FROM Study)) AS G
    UNION ALL SELECT 'RQ1', 'Research type', Name FROM ResearchType
    UNION ALL SELECT 'RQ2', 'UAV application', Name FROM UAVApplication
    UNION ALL SELECT 'RQ3', 'HE scheme', Name FROM HEScheme
    UNION ALL SELECT 'RQ3', 'HE family', F
              FROM (VALUES ('PHE'), ('SHE'), ('FHE'), ('Not determined')) AS V (F)
    UNION ALL SELECT DISTINCT 'RQ3', 'Library', Name FROM Library
    UNION ALL SELECT 'RQ3', 'Library', 'Not applicable'
    UNION ALL SELECT DISTINCT 'RQ3', 'Plaintext encoding', Encoding FROM PlainTextEncode
    UNION ALL SELECT 'RQ4', 'Validation approach', Name FROM ValidationApproach
    UNION ALL SELECT 'RQ4', 'HE executed', V
              FROM (VALUES ('Yes'), ('No')) AS X (V)
    UNION ALL SELECT 'RQ4', 'Code availability', V
              FROM (VALUES ('Available'), ('Not available')) AS X (V)
    UNION ALL SELECT 'RQ5', O.Name || ' location', L.Name
              FROM HEOperation O CROSS JOIN Location L
    UNION ALL SELECT 'RQ5', 'Operation phase', Name FROM Phase
    UNION ALL SELECT 'RQ6', 'Cost type', Name FROM CostType
    UNION ALL SELECT 'RQ6', 'Baseline type', Name FROM BaselineType
    UNION ALL SELECT 'RQ7', 'Protected data', Name FROM DataCategory
    UNION ALL SELECT 'RQ7', 'Protected from', Name FROM AdversaryParty
    UNION ALL SELECT 'RQ7', 'Adversary behavior', V
              FROM (VALUES ('Honest-but-curious'), ('Malicious'), ('Other'), ('Not stated')) AS X (V)
)
SELECT RQ, Facet, Value,
       (Value LIKE 'Not %' OR Value = 'No baseline') AS IsNotInformed
FROM Opcao;


-- ---------------------------------------------------------------------
-- 3. VwFacetCount
-- Quantos estudos têm cada opção. Opção sem estudo aparece com 0.
-- ---------------------------------------------------------------------
CREATE VIEW VwFacetCount (RQ, Facet, Value, IsNotInformed, Studies, PercentOfStudies, StudyIds) AS
SELECT O.RQ, O.Facet, O.Value, O.IsNotInformed,
       COUNT(DISTINCT F.StudyId),
       ROUND(100.0 * COUNT(DISTINCT F.StudyId) / NULLIF((SELECT COUNT(*) FROM Study), 0), 1),
       COALESCE(ARRAY_AGG(DISTINCT F.StudyId) FILTER (WHERE F.StudyId IS NOT NULL), '{}')
FROM VwFacetOption O
LEFT JOIN VwStudyFacet F ON F.Facet = O.Facet AND F.Value = O.Value
GROUP BY O.RQ, O.Facet, O.Value, O.IsNotInformed;


-- ---------------------------------------------------------------------
-- 4. VwFacetCross (MATERIALIZADA)
-- Quantos estudos têm, ao mesmo tempo, a opção A de uma faceta e a
-- opção B de outra, para TODOS os pares, com zeros. Alimenta o bubble
-- plot de Petersen e o gap map: o site escolhe as duas facetas e lê
-- WHERE FacetA = ... AND FacetB = ...
-- Pares da mesma faceta também entram (coocorrência, ex.: aplicações
-- que aparecem juntas); na diagonal (A = B) fica a contagem da opção.
-- Materializada porque é a mais cara (autojunção de VwStudyFacet com
-- produto de todas as opções) e os dados só mudam quando a carga muda.
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW VwFacetCross AS
WITH Par AS (
    SELECT A.Facet AS FacetA, A.Value AS ValueA,
           B.Facet AS FacetB, B.Value AS ValueB,
           COUNT(DISTINCT A.StudyId)     AS Studies,
           ARRAY_AGG(DISTINCT A.StudyId) AS StudyIds
    FROM VwStudyFacet A
    JOIN VwStudyFacet B ON B.StudyId = A.StudyId
    GROUP BY A.Facet, A.Value, B.Facet, B.Value
)
SELECT OA.RQ AS RQA, OA.Facet AS FacetA, OA.Value AS ValueA,
       OB.RQ AS RQB, OB.Facet AS FacetB, OB.Value AS ValueB,
       COALESCE(P.Studies, 0)     AS Studies,
       COALESCE(P.StudyIds, '{}') AS StudyIds
FROM VwFacetOption OA
CROSS JOIN VwFacetOption OB
LEFT JOIN Par P ON P.FacetA = OA.Facet AND P.ValueA = OA.Value
               AND P.FacetB = OB.Facet AND P.ValueB = OB.Value
WITH DATA;


-- ---------------------------------------------------------------------
-- 5. VwStudyOverview
-- Uma linha por estudo:
-- Facets: objeto JSON {faceta: [valores]} com todas as facetas.
-- Schemes: lista JSON com o detalhe de cada esquema adotado.
-- ---------------------------------------------------------------------
CREATE VIEW VwStudyOverview AS
SELECT S.StudyId, S.Title, S.Year, S.DOI,
       'https://doi.org/' || S.DOI AS DoiUrl,
       (SELECT string_agg(A.AuthorName, '; ' ORDER BY A.AuthorName)
        FROM StudyAuthor A WHERE A.StudyId = S.StudyId) AS Authors,
       S.ProblemAddressed, S.HEExecuted, S.CodeURL, S.MetricsAndValues,
       (SELECT jsonb_object_agg(X.Facet, X.Vals)
        FROM (SELECT F.Facet, jsonb_agg(F.Value ORDER BY F.Value) AS Vals
              FROM VwStudyFacet F
              WHERE F.StudyId = S.StudyId AND F.Facet <> 'Year'
              GROUP BY F.Facet) AS X) AS Facets,
       (SELECT jsonb_agg(jsonb_build_object(
                   'Scheme',            A.SchemeName,
                   'Family',            H.Family,
                   'Library',           A.LibraryName,
                   'LibraryVersion',    A.LibraryVersion,
                   'Parameters',        A.Parameters,
                   'SecurityLevelBits', A.SecurityLevelBits,
                   'Encodings',         (SELECT jsonb_agg(E.Encoding ORDER BY E.Encoding)
                                         FROM PlainTextEncode E
                                         WHERE E.StudyId = A.StudyId AND E.SchemeName = A.SchemeName))
               ORDER BY A.SchemeName)
        FROM SchemeAdoption A
        JOIN HEScheme H ON H.Name = A.SchemeName
        WHERE A.StudyId = S.StudyId) AS Schemes
FROM Study S;


-- ---------------------------------------------------------------------
-- 6. VwKpi
-- Uma linha só, com os números principais da página inicial.
-- ---------------------------------------------------------------------
CREATE VIEW VwKpi AS
SELECT COUNT(*)                                        AS Studies,
       MIN(Year)                                       AS FirstYear,
       MAX(Year)                                       AS LastYear,
       COUNT(*) FILTER (WHERE HEExecuted)              AS HEExecuted,
       COUNT(*) FILTER (WHERE CodeURL LIKE 'http%')    AS WithCode,
       (SELECT COUNT(DISTINCT StudyId) FROM SchemeAdoption
        WHERE SecurityLevelBits IS NOT NULL)           AS WithSecurityLevel,
       (SELECT COUNT(DISTINCT StudyId) FROM ValidatedBy
        WHERE ValidationApproachName <> 'Not validated') AS Validated,
       (SELECT COUNT(DISTINCT SchemeName) FROM SchemeAdoption
        WHERE SchemeName NOT LIKE 'Not reported%')     AS NamedSchemes,
       (SELECT COUNT(DISTINCT LibraryName) FROM SchemeAdoption
        WHERE LibraryName <> 'Not reported')           AS NamedLibraries
FROM Study;


-- ---------------------------------------------------------------------
-- 7. VwOperationFlow
-- Onde cada estudo cifra, computa e decifra. Quando uma etapa tem mais
-- de um local, eles viram um nó só ('Edge server + Cloud'): cada estudo
-- é UMA fita no diagrama de fluxo, sem contar o mesmo estudo duas vezes.
-- ---------------------------------------------------------------------
CREATE VIEW VwOperationFlow AS
WITH Etapa AS (
    SELECT StudyId, OperationName,
           string_agg(DISTINCT LocationName, ' + ' ORDER BY LocationName) AS Locais
    FROM ExecutedAt
    GROUP BY StudyId, OperationName
)
SELECT S.StudyId,
       Enc.Locais AS EncryptAt,
       Ev.Locais  AS EvaluateAt,
       Dec.Locais AS DecryptAt,
       (SELECT string_agg(DISTINCT X.PhaseName, ' + ' ORDER BY X.PhaseName)
        FROM ExecutedAt X WHERE X.StudyId = S.StudyId) AS Phases,
       (Enc.Locais LIKE '%+%' OR Ev.Locais LIKE '%+%' OR Dec.Locais LIKE '%+%') AS IsMultiLocation
FROM Study S
JOIN Etapa Enc ON Enc.StudyId = S.StudyId AND Enc.OperationName = 'Encryption'
JOIN Etapa Ev  ON Ev.StudyId  = S.StudyId AND Ev.OperationName  = 'Homomorphic evaluation'
JOIN Etapa Dec ON Dec.StudyId = S.StudyId AND Dec.OperationName = 'Decryption';


-- ---------------------------------------------------------------------
-- 8. VwOperationFlowPattern
-- Os padrões de fluxo e quantos estudos seguem cada um
-- (ex.: On board -> Edge server -> Ground station/user: n estudos).
-- ---------------------------------------------------------------------
CREATE VIEW VwOperationFlowPattern AS
SELECT EncryptAt, EvaluateAt, DecryptAt,
       COUNT(*)                         AS Studies,
       ARRAY_AGG(StudyId ORDER BY StudyId) AS StudyIds
FROM VwOperationFlow
GROUP BY EncryptAt, EvaluateAt, DecryptAt;


-- ---------------------------------------------------------------------
-- 9. VwValidationLadder
-- Degrau mais alto de validação que cada estudo alcançou. A ordem dos
-- degraus é decisão de projeto (do mais abstrato ao mais próximo do VANT
-- real).
-- ---------------------------------------------------------------------
CREATE VIEW VwValidationLadder AS
WITH Degrau (Approach, Rung) AS (
    VALUES ('Not validated', 0),
           ('Analytical evaluation', 1),
           ('Simulation', 2),
           ('Virtual machines', 3),
           ('General-purpose computer', 4),
           ('Embedded/UAV-representative hardware', 5),
           ('Field test or real flight', 6)
), PorEstudo AS (
    SELECT V.StudyId,
           MAX(D.Rung)                                     AS TopRung,
           ARRAY_AGG(V.ValidationApproachName ORDER BY D.Rung) AS Approaches
    FROM ValidatedBy V
    JOIN Degrau D ON D.Approach = V.ValidationApproachName
    GROUP BY V.StudyId
)
SELECT S.StudyId, P.TopRung, D.Approach AS TopApproach, P.Approaches,
       S.HEExecuted,
       COALESCE(S.CodeURL LIKE 'http%', FALSE) AS HasCode
FROM Study S
JOIN PorEstudo P ON P.StudyId = S.StudyId
JOIN Degrau D    ON D.Rung = P.TopRung;


-- ---------------------------------------------------------------------
-- 10. VwReportingMatrix
-- O que cada estudo informa: TRUE informa, FALSE não informa, NULL não
-- se aplica (biblioteca, versão e codificação só contam para estudos
-- que executaram HE). 
-- ---------------------------------------------------------------------
CREATE VIEW VwReportingMatrix AS
WITH Esq AS (
    SELECT StudyId,
           bool_or(SchemeName NOT LIKE 'Not reported%')        AS SchemeNamed,
           bool_or(LibraryName <> 'Not reported')               AS LibraryReported,
           bool_or(LibraryVersion <> 'Not reported')            AS LibraryVersionReported,
           bool_or(Parameters NOT LIKE 'Not reported%'
                   AND Parameters NOT LIKE 'Not applicable%')   AS ParametersReported,
           bool_or(SecurityLevelBits IS NOT NULL)               AS SecurityLevelStated
    FROM SchemeAdoption
    GROUP BY StudyId
), Item AS (
    SELECT S.StudyId, S.HEExecuted,
           E.SchemeNamed,
           CASE WHEN S.HEExecuted THEN E.LibraryReported END        AS LibraryReported,
           CASE WHEN S.HEExecuted THEN E.LibraryVersionReported END AS LibraryVersionReported,
           E.ParametersReported,
           E.SecurityLevelStated,
           CASE WHEN S.HEExecuted THEN EXISTS (
               SELECT 1 FROM PlainTextEncode P
               WHERE P.StudyId = S.StudyId AND P.Encoding <> 'Not reported') END AS EncodingReported,
           COALESCE(S.CodeURL LIKE 'http%', FALSE) AS CodeAvailable,
           NOT EXISTS (SELECT 1 FROM Reports R
                       WHERE R.StudyId = S.StudyId AND R.CostTypeName = 'Not reported')       AS CostsQuantified,
           NOT EXISTS (SELECT 1 FROM ComparesWith C
                       WHERE C.StudyId = S.StudyId AND C.BaselineTypeName = 'No baseline')    AS BaselineCompared,
           EXISTS     (SELECT 1 FROM AdversaryBehavior B
                       WHERE B.StudyId = S.StudyId AND B.Behavior <> 'Not stated')            AS AdversaryStated
    FROM Study S
    JOIN Esq E ON E.StudyId = S.StudyId
)
SELECT I.*,
       (SELECT COUNT(*) FILTER (WHERE x)         FROM unnest(L.Itens) AS x) AS ItemsReported,
       (SELECT COUNT(*) FILTER (WHERE x IS NOT NULL) FROM unnest(L.Itens) AS x) AS ItemsApplicable
FROM Item I
CROSS JOIN LATERAL (SELECT ARRAY[I.SchemeNamed, I.LibraryReported, I.LibraryVersionReported,
                                 I.ParametersReported, I.SecurityLevelStated, I.EncodingReported,
                                 I.CodeAvailable, I.CostsQuantified, I.BaselineCompared,
                                 I.AdversaryStated] AS Itens) AS L;


-- ---------------------------------------------------------------------
-- 11. VwSchemeHierarchy
-- Família > Esquema > Biblioteca > Versão, para o icicle. Um estudo com
-- dois esquemas aparece em dois ramos.
-- ---------------------------------------------------------------------
CREATE VIEW VwSchemeHierarchy AS
SELECT H.Family,
       A.SchemeName,
       COALESCE(A.LibraryName, 'Not applicable')    AS Library,
       COALESCE(A.LibraryVersion, 'Not applicable') AS LibraryVersion,
       COUNT(DISTINCT A.StudyId)                    AS Studies,
       ARRAY_AGG(DISTINCT A.StudyId)                AS StudyIds
FROM SchemeAdoption A
JOIN HEScheme H ON H.Name = A.SchemeName
GROUP BY H.Family, A.SchemeName, COALESCE(A.LibraryName, 'Not applicable'),
         COALESCE(A.LibraryVersion, 'Not applicable');


-- ---------------------------------------------------------------------
-- 12. VwThreatMatrix
-- Dado protegido x parte x comportamento, com zeros, para os small
-- multiples da RQ7. Como Targets está vazia (a planilha não liga cada
-- dado a cada parte), a ligação é feita pelo estudo: conta o estudo que
-- cifra o dado D e declara a parte P com o comportamento C.
-- ---------------------------------------------------------------------
CREATE VIEW VwThreatMatrix AS
WITH Comportamento (Behavior) AS (
    VALUES ('Honest-but-curious'), ('Malicious'), ('Other'), ('Not stated')
), Combinacao AS (
    SELECT E.StudyId, E.DataCategoryName, B.PartyName, B.Behavior
    FROM Encrypts E
    JOIN AdversaryBehavior B ON B.StudyId = E.StudyId
)
SELECT D.Name AS DataCategory, P.Name AS Party, C.Behavior,
       COUNT(DISTINCT X.StudyId) AS Studies,
       COALESCE(ARRAY_AGG(DISTINCT X.StudyId) FILTER (WHERE X.StudyId IS NOT NULL), '{}') AS StudyIds
FROM DataCategory D
CROSS JOIN AdversaryParty P
CROSS JOIN Comportamento C
LEFT JOIN Combinacao X ON X.DataCategoryName = D.Name
                      AND X.PartyName = P.Name
                      AND X.Behavior = C.Behavior
GROUP BY D.Name, P.Name, C.Behavior;


-- ---------------------------------------------------------------------
-- 13. VwAuthor
-- Nós da rede de coautoria: cada autor e em quantos estudos aparece.
-- O nome vem do BibTeX.
-- ---------------------------------------------------------------------
CREATE VIEW VwAuthor AS
SELECT AuthorName,
       COUNT(*)                            AS Studies,
       ARRAY_AGG(StudyId ORDER BY StudyId) AS StudyIds
FROM StudyAuthor
GROUP BY AuthorName;


-- ---------------------------------------------------------------------
-- 14. VwCoAuthorship
-- Arestas da rede: cada par de autores que assinou junto, uma vez só
-- (AuthorA < AuthorB), e em quantos estudos.
-- ---------------------------------------------------------------------
CREATE VIEW VwCoAuthorship AS
SELECT A.AuthorName AS AuthorA,
       B.AuthorName AS AuthorB,
       COUNT(*)                              AS JointStudies,
       ARRAY_AGG(A.StudyId ORDER BY A.StudyId) AS StudyIds
FROM StudyAuthor A
JOIN StudyAuthor B ON B.StudyId = A.StudyId AND A.AuthorName < B.AuthorName
GROUP BY A.AuthorName, B.AuthorName;
