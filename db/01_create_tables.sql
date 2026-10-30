-- ---------------------------------------------------------------------
-- Conjuntos de Entidades regulares
-- ---------------------------------------------------------------------

CREATE TABLE Study (
    StudyId           INTEGER GENERATED ALWAYS AS IDENTITY,
    Title             VARCHAR(400) NOT NULL,
    DOI               VARCHAR(120),
    Year              SMALLINT     NOT NULL,
    ProblemAddressed  TEXT         NOT NULL,
    CodeURL           VARCHAR(300),
    HEExecuted        BOOLEAN      NOT NULL,
    MetricsAndValues  TEXT         NOT NULL,   -- RQ6: metricas de todos os custos do estudo
    CONSTRAINT StudyPK      PRIMARY KEY (StudyId),
    CONSTRAINT StudyTitleUK UNIQUE (Title),         -- chave candidata
    CONSTRAINT StudyDOIUK   UNIQUE (DOI),           -- chave candidata (aceita nulo)
    CONSTRAINT StudyYearCK  CHECK (Year BETWEEN 1978 AND 2100),
    -- HE executado exige CodeURL (link ou 'not available'); sem HE executado,
    -- o estudo ainda pode ter link de codigo (ex.: codigo so da parte nao-HE)
    CONSTRAINT StudyCodeCK  CHECK (NOT HEExecuted OR CodeURL IS NOT NULL)
);

CREATE TABLE HEScheme (
    Name    VARCHAR(80) NOT NULL,
    Family  VARCHAR(16) NOT NULL,
    CONSTRAINT HESchemePK       PRIMARY KEY (Name),
    CONSTRAINT HESchemeFamilyCK CHECK (Family IN ('PHE', 'SHE', 'FHE', 'Not determined'))
);

CREATE TABLE Library (
    Name     VARCHAR(80) NOT NULL,
    Version  VARCHAR(40) NOT NULL,     -- 'Not reported' quando o estudo nao informa
    CONSTRAINT LibraryPK PRIMARY KEY (Name, Version)
);

CREATE TABLE HEOperation (
    Name  VARCHAR(30) NOT NULL,
    CONSTRAINT HEOperationPK     PRIMARY KEY (Name),
    CONSTRAINT HEOperationNameCK CHECK (Name IN ('Encryption', 'Homomorphic evaluation', 'Decryption'))
);

-- Os 9 catalogos: so o nome da opcao
CREATE TABLE ResearchType       (Name VARCHAR(80) NOT NULL, CONSTRAINT ResearchTypePK       PRIMARY KEY (Name));
CREATE TABLE UAVApplication     (Name VARCHAR(80) NOT NULL, CONSTRAINT UAVApplicationPK     PRIMARY KEY (Name));
CREATE TABLE ValidationApproach (Name VARCHAR(80) NOT NULL, CONSTRAINT ValidationApproachPK PRIMARY KEY (Name));
CREATE TABLE Location           (Name VARCHAR(80) NOT NULL, CONSTRAINT LocationPK           PRIMARY KEY (Name));
CREATE TABLE Phase              (Name VARCHAR(80) NOT NULL, CONSTRAINT PhasePK              PRIMARY KEY (Name));
CREATE TABLE CostType           (Name VARCHAR(80) NOT NULL, CONSTRAINT CostTypePK           PRIMARY KEY (Name));
CREATE TABLE BaselineType       (Name VARCHAR(80) NOT NULL, CONSTRAINT BaselineTypePK       PRIMARY KEY (Name));
CREATE TABLE DataCategory       (Name VARCHAR(80) NOT NULL, CONSTRAINT DataCategoryPK       PRIMARY KEY (Name));
CREATE TABLE AdversaryParty     (Name VARCHAR(80) NOT NULL, CONSTRAINT AdversaryPartyPK     PRIMARY KEY (Name));

-- ---------------------------------------------------------------------
-- Agregacoes (os CR geradores sem atributos nao viram tabela)
-- ---------------------------------------------------------------------

-- Agregacao sobre Adopt (Study x HEScheme)
CREATE TABLE SchemeAdoption (
    StudyId            INTEGER     NOT NULL,
    SchemeName         VARCHAR(80) NOT NULL,
    LibraryName        VARCHAR(80),
    LibraryVersion     VARCHAR(40),
    Parameters         TEXT        NOT NULL,
    SecurityLevelBits  SMALLINT,
    CONSTRAINT SchemeAdoptionPK PRIMARY KEY (StudyId, SchemeName),
    CONSTRAINT SchemeAdoptionStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT SchemeAdoptionSchemeFK FOREIGN KEY (SchemeName)
        REFERENCES HEScheme (Name) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT SchemeAdoptionLibraryFK FOREIGN KEY (LibraryName, LibraryVersion)
        REFERENCES Library (Name, Version) MATCH FULL ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT SchemeAdoptionSecCK CHECK (SecurityLevelBits > 0)
);

-- Agregacao sobre Considers (Study x AdversaryParty)
CREATE TABLE AdversaryModel (
    StudyId    INTEGER     NOT NULL,
    PartyName  VARCHAR(80) NOT NULL,
    CONSTRAINT AdversaryModelPK PRIMARY KEY (StudyId, PartyName),
    CONSTRAINT AdversaryModelStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT AdversaryModelPartyFK FOREIGN KEY (PartyName)
        REFERENCES AdversaryParty (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Agregacao sobre Perform (SchemeAdoption x HEOperation)
CREATE TABLE OperationExecution (
    StudyId        INTEGER     NOT NULL,
    SchemeName     VARCHAR(80) NOT NULL,
    OperationName  VARCHAR(30) NOT NULL,
    CONSTRAINT OperationExecutionPK PRIMARY KEY (StudyId, SchemeName, OperationName),
    CONSTRAINT OperationExecutionAdoptFK FOREIGN KEY (StudyId, SchemeName)
        REFERENCES SchemeAdoption (StudyId, SchemeName) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT OperationExecutionOpFK FOREIGN KEY (OperationName)
        REFERENCES HEOperation (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- CR binarios N:M
-- ---------------------------------------------------------------------

CREATE TABLE ClassifiedAs (
    StudyId           INTEGER     NOT NULL,
    ResearchTypeName  VARCHAR(80) NOT NULL,
    CONSTRAINT ClassifiedAsPK PRIMARY KEY (StudyId, ResearchTypeName),
    CONSTRAINT ClassifiedAsStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ClassifiedAsTypeFK FOREIGN KEY (ResearchTypeName)
        REFERENCES ResearchType (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Addresses (
    StudyId             INTEGER     NOT NULL,
    UAVApplicationName  VARCHAR(80) NOT NULL,
    CONSTRAINT AddressesPK PRIMARY KEY (StudyId, UAVApplicationName),
    CONSTRAINT AddressesStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT AddressesAppFK FOREIGN KEY (UAVApplicationName)
        REFERENCES UAVApplication (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE ValidatedBy (
    StudyId                 INTEGER     NOT NULL,
    ValidationApproachName  VARCHAR(80) NOT NULL,
    CONSTRAINT ValidatedByPK PRIMARY KEY (StudyId, ValidationApproachName),
    CONSTRAINT ValidatedByStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ValidatedByApproachFK FOREIGN KEY (ValidationApproachName)
        REFERENCES ValidationApproach (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Encrypts (
    StudyId           INTEGER     NOT NULL,
    DataCategoryName  VARCHAR(80) NOT NULL,
    CONSTRAINT EncryptsPK PRIMARY KEY (StudyId, DataCategoryName),
    CONSTRAINT EncryptsStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT EncryptsDataFK FOREIGN KEY (DataCategoryName)
        REFERENCES DataCategory (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE Reports (
    StudyId       INTEGER     NOT NULL,
    CostTypeName  VARCHAR(80) NOT NULL,
    CONSTRAINT ReportsPK PRIMARY KEY (StudyId, CostTypeName),
    CONSTRAINT ReportsStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ReportsTypeFK FOREIGN KEY (CostTypeName)
        REFERENCES CostType (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE ComparesWith (
    StudyId           INTEGER     NOT NULL,
    BaselineTypeName  VARCHAR(80) NOT NULL,
    CONSTRAINT ComparesWithPK PRIMARY KEY (StudyId, BaselineTypeName),
    CONSTRAINT ComparesWithStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ComparesWithBaselineFK FOREIGN KEY (BaselineTypeName)
        REFERENCES BaselineType (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Um dos papeis e a agregacao AdversaryModel
CREATE TABLE Targets (
    StudyId           INTEGER     NOT NULL,
    PartyName         VARCHAR(80) NOT NULL,
    DataCategoryName  VARCHAR(80) NOT NULL,
    CONSTRAINT TargetsPK PRIMARY KEY (StudyId, PartyName, DataCategoryName),
    CONSTRAINT TargetsModelFK FOREIGN KEY (StudyId, PartyName)
        REFERENCES AdversaryModel (StudyId, PartyName) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT TargetsDataFK FOREIGN KEY (DataCategoryName)
        REFERENCES DataCategory (Name) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT TargetsNotStatedCK CHECK (PartyName <> 'Not stated')
);

-- ---------------------------------------------------------------------
-- CR de ordem > 2 
-- ---------------------------------------------------------------------

CREATE TABLE ExecutedAt (
    StudyId        INTEGER     NOT NULL,
    SchemeName     VARCHAR(80) NOT NULL,
    OperationName  VARCHAR(30) NOT NULL,
    LocationName   VARCHAR(80) NOT NULL,
    PhaseName      VARCHAR(80) NOT NULL,
    CONSTRAINT ExecutedAtPK PRIMARY KEY (StudyId, SchemeName, OperationName, LocationName, PhaseName),
    CONSTRAINT ExecutedAtExecFK FOREIGN KEY (StudyId, SchemeName, OperationName)
        REFERENCES OperationExecution (StudyId, SchemeName, OperationName)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ExecutedAtLocationFK FOREIGN KEY (LocationName)
        REFERENCES Location (Name) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ExecutedAtPhaseFK FOREIGN KEY (PhaseName)
        REFERENCES Phase (Name) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- Atributos multivalorados
-- ---------------------------------------------------------------------

CREATE TABLE StudyAuthor (
    StudyId     INTEGER      NOT NULL,
    AuthorName  VARCHAR(150) NOT NULL,
    CONSTRAINT StudyAuthorPK PRIMARY KEY (StudyId, AuthorName),
    CONSTRAINT StudyAuthorStudyFK FOREIGN KEY (StudyId)
        REFERENCES Study (StudyId) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Multivalorado da agregacao SchemeAdoption: herda a chave dela
CREATE TABLE PlainTextEncode (
    StudyId     INTEGER      NOT NULL,
    SchemeName  VARCHAR(80)  NOT NULL,
    Encoding    VARCHAR(80)  NOT NULL,
    CONSTRAINT PlainTextEncodePK PRIMARY KEY (StudyId, SchemeName, Encoding),
    CONSTRAINT PlainTextEncodeAdoptFK FOREIGN KEY (StudyId, SchemeName)
        REFERENCES SchemeAdoption (StudyId, SchemeName) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Multivalorado da agregacao AdversaryModel: uma parte pode ter mais de um
-- comportamento no mesmo estudo 
CREATE TABLE AdversaryBehavior (
    StudyId    INTEGER     NOT NULL,
    PartyName  VARCHAR(80) NOT NULL,
    Behavior   VARCHAR(20) NOT NULL,
    CONSTRAINT AdversaryBehaviorPK PRIMARY KEY (StudyId, PartyName, Behavior),
    CONSTRAINT AdversaryBehaviorModelFK FOREIGN KEY (StudyId, PartyName)
        REFERENCES AdversaryModel (StudyId, PartyName) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT AdversaryBehaviorCK CHECK (
        Behavior IN ('Honest-but-curious', 'Malicious', 'Other', 'Not stated')),
    CONSTRAINT AdversaryBehaviorNotStCK CHECK (
        PartyName <> 'Not stated' OR Behavior = 'Not stated')
);
