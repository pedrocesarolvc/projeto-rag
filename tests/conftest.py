"""
Fixtures compartilhadas pelos testes que precisam de um Postgres real
com pgvector (Etapas 4, 5 e 7). Ver test_armazenador.py, test_buscador.py
e test_e2e.py para o motivo de pularem sem essa infraestrutura de pé.
"""

import pytest

from app.auth import armazenador as auth_armazenador
from app.indexacao import armazenador


@pytest.fixture
def conexao():
    conexao = armazenador.conectar()
    auth_armazenador.criar_tabela_usuarios(conexao)
    armazenador.criar_tabelas(conexao)
    conexao.execute("TRUNCATE usuarios, documentos, chunks")
    conexao.commit()
    yield conexao
    conexao.execute("TRUNCATE usuarios, documentos, chunks")
    conexao.commit()
    conexao.close()
