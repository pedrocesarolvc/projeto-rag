"""
Fixtures compartilhadas pelos testes que precisam de um Postgres real
com pgvector (Etapas 4 e 5). Ver test_armazenador.py e test_buscador.py
para o motivo de pularem sem essa infraestrutura de pé.
"""

import pytest

from app.indexacao import armazenador


@pytest.fixture
def conexao():
    conexao = armazenador.conectar()
    armazenador.criar_tabela(conexao)
    conexao.execute("TRUNCATE chunks")
    conexao.commit()
    yield conexao
    conexao.execute("TRUNCATE chunks")
    conexao.commit()
    conexao.close()
