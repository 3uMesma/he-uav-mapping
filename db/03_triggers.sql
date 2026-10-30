-- =====================================================================
-- Regras de integridade que envolvem mais de uma tabela
--
-- Parte 1: estudo sem HE executado (triggers de tupla).
-- Parte 2: opcoes exclusivas, como "Not reported".
-- Parte 3: verificacao da participacao total (linhas duplas do DE-R).
--          Ela nao cabe em trigger de tupla: o estudo e inserido antes das
--          suas classificacoes, entao no momento do INSERT em Study ele
--          ainda nao tem nenhuma. Por isso ela e uma funcao chamada no fim
--          do populate dos estudos, antes do COMMIT.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Parte 1: estudo sem HE executado
--
-- Regras:
--   HEExecuted falso => adocoes sem biblioteca
--   HEExecuted falso => adocoes sem linhas em PlainTextEncode
--   Validation research => HEExecuted verdadeiro
--
-- As tres pedem a mesma pesquisa em Study, entao usam uma funcao so.
-- O argumento do CREATE TRIGGER (TG_ARGV[0]) diz o que foi recusado.
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION ExigeHEExecutado() RETURNS TRIGGER AS $$
    DECLARE
        Executado BOOLEAN;
    BEGIN
        SELECT HEExecuted INTO Executado
            FROM Study
            WHERE StudyId = NEW.StudyId;

        IF NOT Executado THEN
            RAISE EXCEPTION 'Estudo %: HEExecuted e falso, entao nao pode ter %.',
                NEW.StudyId, TG_ARGV[0]
                USING HINT = 'Corrija HEExecuted em Study ou remova o valor na planilha.';
        END IF;

        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

-- Biblioteca so em estudo com HE executado
CREATE OR REPLACE TRIGGER TR_SchemeAdoption_Biblioteca
    BEFORE INSERT OR UPDATE OF LibraryName, LibraryVersion, StudyId ON SchemeAdoption
    FOR EACH ROW
    WHEN (NEW.LibraryName IS NOT NULL)
    EXECUTE FUNCTION ExigeHEExecutado('biblioteca em SchemeAdoption');

-- Codificacao do texto claro so em estudo com HE executado
CREATE OR REPLACE TRIGGER TR_PlainTextEncode_Executado
    BEFORE INSERT OR UPDATE OF StudyId ON PlainTextEncode
    FOR EACH ROW
    EXECUTE FUNCTION ExigeHEExecutado('codificacao em PlainTextEncode');

-- Validation research so com HE executado (regra da RQ1)
CREATE OR REPLACE TRIGGER TR_ClassifiedAs_ValidationResearch
    BEFORE INSERT OR UPDATE ON ClassifiedAs
    FOR EACH ROW
    WHEN (NEW.ResearchTypeName = 'Validation research')
    EXECUTE FUNCTION ExigeHEExecutado('Research type = Validation research');


-- O mesmo conjunto de regras, visto do lado de Study: um estudo que ja tem
-- biblioteca, codificacao ou Validation research nao pode passar a ter
-- HEExecuted falso.
CREATE OR REPLACE FUNCTION ProtegeHEExecutado() RETURNS TRIGGER AS $$
    BEGIN
        IF EXISTS (SELECT 1 FROM SchemeAdoption
                       WHERE StudyId = NEW.StudyId AND LibraryName IS NOT NULL) THEN
            RAISE EXCEPTION 'Estudo %: nao pode ter HEExecuted falso, porque tem biblioteca em SchemeAdoption.',
                NEW.StudyId;
        END IF;

        IF EXISTS (SELECT 1 FROM PlainTextEncode WHERE StudyId = NEW.StudyId) THEN
            RAISE EXCEPTION 'Estudo %: nao pode ter HEExecuted falso, porque tem codificacao em PlainTextEncode.',
                NEW.StudyId;
        END IF;

        IF EXISTS (SELECT 1 FROM ClassifiedAs
                       WHERE StudyId = NEW.StudyId
                         AND ResearchTypeName = 'Validation research') THEN
            RAISE EXCEPTION 'Estudo %: nao pode ter HEExecuted falso, porque esta classificado como Validation research.',
                NEW.StudyId;
        END IF;

        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER TR_Study_HEExecutado
    BEFORE UPDATE OF HEExecuted ON Study
    FOR EACH ROW
    WHEN (OLD.HEExecuted AND NOT NEW.HEExecuted)
    EXECUTE FUNCTION ProtegeHEExecutado();


-- ---------------------------------------------------------------------
-- Parte 2: opcoes exclusivas
--
--   Tabela           Coluna                   Valor exclusivo   Dono
--   ValidatedBy      ValidationApproachName   Not validated     estudo
--   CostReport       CostTypeName             Not reported      estudo
--   ComparesWith     BaselineTypeName         No baseline       CostReport
--   AdversaryModel   PartyName                Not stated        estudo
--   ExecutedAt       LocationName             Not reported      execucao da operacao
--   ExecutedAt       PhaseName                Not reported      execucao da operacao
--
-- Uma funcao generica atende a todos os casos. Os argumentos do
-- CREATE TRIGGER (TG_ARGV) dizem a coluna, o valor exclusivo e as colunas
-- que identificam o dono; a funcao monta a consulta com SQL dinamico
-- (EXECUTE ... USING). Ha conflito quando exatamente um dos dois valores,
-- o novo ou o ja gravado, e o exclusivo.
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION OpcaoExclusiva() RETURNS TRIGGER AS $$
    DECLARE
        Coluna    TEXT  := lower(TG_ARGV[0]);
        Exclusivo TEXT  := TG_ARGV[1];
        Nova      JSONB := to_jsonb(NEW);
        Velha     JSONB := CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD) END;
        Valor     TEXT  := Nova ->> lower(TG_ARGV[0]);
        Filtro    TEXT  := '';
        Dono      TEXT  := '';
        Conflito  TEXT;
    BEGIN
        -- Filtro pelo dono: TG_ARGV[2], TG_ARGV[3], ...
        FOR I IN 2 .. TG_NARGS - 1 LOOP
            Filtro := Filtro || format(' AND T.%I::TEXT = ($1 ->> %L)',
                                       lower(TG_ARGV[I]), lower(TG_ARGV[I]));
            Dono   := Dono || CASE WHEN Dono = '' THEN '' ELSE ', ' END
                           || TG_ARGV[I] || ' = ' || (Nova ->> lower(TG_ARGV[I]));
        END LOOP;

        EXECUTE format(
            'SELECT T.%I FROM %I T
              WHERE (T.%I = $2) <> ($3 = $2) %s
                AND ($4 IS NULL OR to_jsonb(T) <> $4)
              LIMIT 1',
            Coluna, TG_TABLE_NAME, Coluna, Filtro)
            INTO Conflito
            USING Nova, Exclusivo, Valor, Velha;

        IF Conflito IS NOT NULL THEN
            RAISE EXCEPTION '%: "%" nao pode aparecer junto de outra opcao (% ja tem "%"; tentou "%").',
                TG_TABLE_NAME, Exclusivo, Dono, Conflito, Valor
                USING HINT = 'Escolha so a opcao exclusiva ou so as demais.';
        END IF;

        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER TR_ValidatedBy_Exclusiva
    BEFORE INSERT OR UPDATE ON ValidatedBy
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('ValidationApproachName', 'Not validated', 'StudyId');

CREATE OR REPLACE TRIGGER TR_Reports_Exclusiva
    BEFORE INSERT OR UPDATE ON Reports
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('CostTypeName', 'Not reported', 'StudyId');

CREATE OR REPLACE TRIGGER TR_ComparesWith_Exclusiva
    BEFORE INSERT OR UPDATE ON ComparesWith
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('BaselineTypeName', 'No baseline', 'StudyId');

CREATE OR REPLACE TRIGGER TR_AdversaryModel_Exclusiva
    BEFORE INSERT OR UPDATE ON AdversaryModel
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('PartyName', 'Not stated', 'StudyId');

CREATE OR REPLACE TRIGGER TR_AdversaryBehavior_Exclusiva
    BEFORE INSERT OR UPDATE ON AdversaryBehavior
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('Behavior', 'Not stated', 'StudyId', 'PartyName');

CREATE OR REPLACE TRIGGER TR_ExecutedAt_LocalExclusivo
    BEFORE INSERT OR UPDATE ON ExecutedAt
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('LocationName', 'Not reported', 'StudyId', 'SchemeName', 'OperationName');

CREATE OR REPLACE TRIGGER TR_ExecutedAt_FaseExclusiva
    BEFORE INSERT OR UPDATE ON ExecutedAt
    FOR EACH ROW
    EXECUTE FUNCTION OpcaoExclusiva('PhaseName', 'Not reported', 'StudyId', 'SchemeName', 'OperationName');


-- ---------------------------------------------------------------------
-- Parte 3: participacao total (linhas duplas do DE-R)
--
--   P1. Todo estudo participa de ClassifiedAs, Addresses, Adopt
--       (SchemeAdoption), ValidatedBy, Reports (CostReport), Encrypts e
--       Considers (AdversaryModel)
--   P2. Toda adocao realiza as 3 operacoes HE (Perform)
--   P3. Toda execucao de operacao tem ao menos um par (local, fase)
--   P4. Todo CostReport tem ao menos um ComparesWith
--
-- ViolacoesParticipacao() lista o que falta, para consultar no DBeaver.
-- VerificaCarga() aborta a transacao se houver qualquer violacao.
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION ViolacoesParticipacao()
    RETURNS TABLE (Regra TEXT, Estudo INTEGER, Detalhe TEXT) AS $$
    BEGIN
        -- P1: estudo sem vinculo em alguma RQ
        RETURN QUERY
            SELECT 'P1 estudo sem ' || T.Rel, S.StudyId, NULL::TEXT
            FROM Study S
            CROSS JOIN (VALUES ('ClassifiedAs'), ('Addresses'), ('SchemeAdoption'),
                               ('ValidatedBy'), ('Reports'), ('ComparesWith'),
                               ('Encrypts'), ('AdversaryModel')) AS T (Rel)
            WHERE NOT EXISTS (
                SELECT 1 FROM (
                    SELECT 'ClassifiedAs' AS Rel, StudyId FROM ClassifiedAs   UNION ALL
                    SELECT 'Addresses',      StudyId FROM Addresses           UNION ALL
                    SELECT 'SchemeAdoption', StudyId FROM SchemeAdoption      UNION ALL
                    SELECT 'ValidatedBy',    StudyId FROM ValidatedBy         UNION ALL
                    SELECT 'Reports',        StudyId FROM Reports             UNION ALL
                    SELECT 'ComparesWith',   StudyId FROM ComparesWith        UNION ALL
                    SELECT 'Encrypts',       StudyId FROM Encrypts            UNION ALL
                    SELECT 'AdversaryModel', StudyId FROM AdversaryModel) V
                WHERE V.Rel = T.Rel AND V.StudyId = S.StudyId);

        -- P2: adocao sem alguma das 3 operacoes
        RETURN QUERY
            SELECT 'P2 adocao sem a operacao', A.StudyId, A.SchemeName || ' / ' || O.Name
            FROM SchemeAdoption A CROSS JOIN HEOperation O
            WHERE NOT EXISTS (
                SELECT 1 FROM OperationExecution E
                WHERE (E.StudyId, E.SchemeName, E.OperationName)
                    = (A.StudyId, A.SchemeName, O.Name));

        -- P3: execucao sem local e fase
        RETURN QUERY
            SELECT 'P3 execucao sem ExecutedAt', E.StudyId, E.SchemeName || ' / ' || E.OperationName
            FROM OperationExecution E
            WHERE NOT EXISTS (
                SELECT 1 FROM ExecutedAt X
                WHERE (X.StudyId, X.SchemeName, X.OperationName)
                    = (E.StudyId, E.SchemeName, E.OperationName));

        -- P4: parte do modelo de ameaca sem comportamento
        RETURN QUERY
            SELECT 'P4 parte sem AdversaryBehavior', M.StudyId, M.PartyName::TEXT
            FROM AdversaryModel M
            WHERE NOT EXISTS (
                SELECT 1 FROM AdversaryBehavior B
                WHERE (B.StudyId, B.PartyName) = (M.StudyId, M.PartyName));
    END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION VerificaCarga() RETURNS VOID AS $$
    DECLARE
        V     RECORD;
        Total INTEGER := 0;
    BEGIN
        FOR V IN SELECT * FROM ViolacoesParticipacao() ORDER BY Estudo, Regra LOOP
            RAISE NOTICE 'Estudo %: % %', V.Estudo, V.Regra, COALESCE('(' || V.Detalhe || ')', '');
            Total := Total + 1;
        END LOOP;

        IF Total > 0 THEN
            RAISE EXCEPTION 'Carga recusada: % violacao(oes) de participacao total (detalhes acima).', Total;
        END IF;

        RAISE NOTICE 'Carga verificada: nenhuma violacao de participacao total.';
    END;
$$ LANGUAGE plpgsql;
