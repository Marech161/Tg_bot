\set DB_REPL_USER `echo "${DB_REPL_USER}"`
\set DB_REPL_PASSWORD `echo "${DB_REPL_PASSWORD}"`
CREATE ROLE :DB_REPL_USER WITH REPLICATION LOGIN PASSWORD :'DB_REPL_PASSWORD';
SELECT pg_create_physical_replication_slot('replication_slot');

CREATE TABLE phones (
    id SERIAL PRIMARY KEY,
    value VARCHAR(50)
);

INSERT INTO phones (value) VALUES
('89282281345'),
('+79281997103');

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    value VARCHAR(50)
);

INSERT INTO emails (value) VALUES
('mark@mail.ru'),
('zlata@sfedu.ru');

\set DB_REPL_HOST `echo "${DB_REPL_HOST}"`
CREATE TABLE hba ( lines text );
COPY hba FROM '/var/lib/postgresql/data/pg_hba.conf';
\set val 'host replication ' :DB_REPL_USER ' 0.0.0.0/0 scram-sha-256'
INSERT INTO hba (lines) VALUES (:'val');
COPY hba TO '/var/lib/postgresql/data/pg_hba.conf';
DROP TABLE hba;
SELECT pg_reload_conf()
