FROM postgres:14

RUN \
mkdir -p /oracle/pg_data/archive/ &&\
chmod -R 777 /oracle/pg_data/archive

COPY init.sql /docker-entrypoint-initdb.d/init.sql
