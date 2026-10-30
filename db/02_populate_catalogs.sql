-- =====================================================================
-- Populate dos catalogos: as opcoes fixas do formulario de extracao
--
-- Fonte das opcoes: formulario de extracao (RQ1-RQ7) e planilha de
-- extracao (38 estudos), com as opcoes adotadas durante a extracao:
-- UAVApplication: Navigation; Data collection and aggregation;
--   Task allocation; Formation control; Network clustering/routing
-- DataCategory: Control signals/commands
-- AdversaryParty: Untrusted on-board component
-- HEScheme e Library nao estao aqui: sao listas abertas, que crescem com
-- os estudos, e entram no populate dos estudos.
-- =====================================================================

BEGIN;

-- RQ1: tipo de pesquisa (Wieringa et al., 2005)
INSERT INTO ResearchType (Name) VALUES
    ('Solution proposal'),
    ('Validation research'),
    ('Evaluation research'),
    ('Philosophical paper'),
    ('Opinion paper'),
    ('Experience report');

-- RQ2: aplicacao em VANTs
INSERT INTO UAVApplication (Name) VALUES
    ('Compliance verification'),
    ('Collision avoidance'),
    ('State estimation'),
    ('Navigation'),
    ('Authentication'),
    ('Computation offloading'),
    ('Federated learning'),
    ('Image/video processing'),
    ('Data collection and aggregation'),
    ('Task allocation'),
    ('Formation control'),
    ('Network clustering/routing'),
    ('Other');

-- RQ4: abordagem de validacao
INSERT INTO ValidationApproach (Name) VALUES
    ('Analytical evaluation'),
    ('Simulation'),
    ('Virtual machines'),
    ('General-purpose computer'),
    ('Embedded/UAV-representative hardware'),
    ('Field test or real flight'),
    ('Not validated');

-- RQ5: as tres operacoes do protocolo HE
INSERT INTO HEOperation (Name) VALUES
    ('Encryption'),
    ('Homomorphic evaluation'),
    ('Decryption');

-- RQ5: onde cada operacao e executada
INSERT INTO Location (Name) VALUES
    ('On board'),
    ('Peer UAV'),
    ('Ground station/user'),
    ('Sensor or external device'),
    ('Edge server'),
    ('Cloud'),
    ('Third party'),
    ('Not reported');

-- RQ5: fase da operacao do VANT
INSERT INTO Phase (Name) VALUES
    ('Pre-flight'),
    ('In-flight'),
    ('Post-flight'),
    ('Not reported');

-- RQ6: tipos de custo
INSERT INTO CostType (Name) VALUES
    ('Computation time/latency'),
    ('Communication/bandwidth'),
    ('Storage/memory'),
    ('Ciphertext size'),
    ('Energy/power'),
    ('CPU utilization'),
    ('Accuracy loss'),
    ('Not reported');

-- RQ6: tipos de baseline
INSERT INTO BaselineType (Name) VALUES
    ('Plaintext computation'),
    ('Other privacy-enhancing technique'),
    ('Non-HE cryptographic scheme'),
    ('Other HE scheme or configuration'),
    ('Architectural variant'),
    ('No baseline');

-- RQ7: dados protegidos (usado por Encrypts e por Targets)
INSERT INTO DataCategory (Name) VALUES
    ('Position/trajectory'),
    ('Planned route/flight path'),
    ('Restricted zone or policy data'),
    ('Sensor measurements/state estimates'),
    ('Images/video'),
    ('Model parameters'),
    ('Control signals/commands'),
    ('Other');

-- RQ7: de quem os dados sao protegidos
INSERT INTO AdversaryParty (Name) VALUES
    ('External eavesdropper'),
    ('Auditor/regulator'),
    ('Edge/cloud server'),
    ('Other UAV or operator'),
    ('Untrusted on-board component'),
    ('Not stated');

COMMIT;
