from sqlalchemy import create_engine, exc
from flask import current_app, g

import config


def get_dyna_db():
    if 'dyna_db' not in g:
        dyna_server = current_app.config['dynaServer']
        dyna_db = current_app.config['dynaDBName']
        dyna_user = current_app.config['dynaUserName']
        dyna_password = current_app.config['dynaPassword']
        dynacom_eng = \
            create_engine(f'mssql+pyodbc://{dyna_user}:{dyna_password}@{dyna_server}/'
                          f'{dyna_db}?driver=SQL Server')
        g.dyna_db = dynacom_eng.connect()
    return g.dyna_db


def get_db():
    if 'db' not in g:
        postgres_server = current_app.config['postgresServer']
        postgres_db = current_app.config['postgresDBName']
        postgres_user = current_app.config['postgresUserName']
        postgres_password = current_app.config['postgresPassword']
        postgres_eng = \
            create_engine(f'postgresql://{postgres_user}:{postgres_password}@'
                          f'{postgres_server}:5432/{postgres_db}')
        g.db = postgres_eng.connect()
    return g.db


def close_dyna_db(e=None):
    db = g.pop('dyna_db',None)

    if db is not None:
        db.close()


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.teardown_appcontext(close_dyna_db)
