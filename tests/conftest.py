"""
Fixtures compartilhadas pelos testes que precisam de um Postgres real
com pgvector (Etapas 4, 5 e 7). Ver test_armazenador.py, test_buscador.py
e test_e2e.py para o motivo de pularem sem essa infraestrutura de pé.
"""

import os
from urllib.parse import urlparse

import pytest

from app.auth import armazenador as auth_armazenador
from app.config import DATABASE_URL
from app.conversas import armazenador as conversas_armazenador
from app.indexacao import armazenador

TABELAS = "usuarios, documentos, chunks, conversas, conversa_documentos, mensagens"

# Estes testes dão TRUNCATE em todas as tabelas, antes e depois de cada
# um. Contra um banco que guarda dado de verdade (a instância pública
# da Neon, por exemplo) isso apaga contas e documentos de quem usou — e
# já aconteceu. Por isso só rodam, por padrão, em banco local; para
# apontá-los para outro banco descartável é preciso dizer isso
# explicitamente.
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1", "db"}
VARIAVEL_DE_AUTORIZACAO = "TESTES_PODEM_APAGAR_O_BANCO"


def _banco_e_descartavel() -> bool:
    if os.environ.get(VARIAVEL_DE_AUTORIZACAO) == "1":
        return True
    return urlparse(DATABASE_URL or "").hostname in HOSTS_LOCAIS


@pytest.fixture
def conexao():
    if not _banco_e_descartavel():
        pytest.fail(
            "Recusando rodar: estes testes apagam TODAS as tabelas e o DATABASE_URL "
            "não aponta para um banco local. Use o Postgres do docker compose, ou, se "
            f"este banco for mesmo descartável, defina {VARIAVEL_DE_AUTORIZACAO}=1.",
            pytrace=False,
        )
    conexao = armazenador.conectar()
    auth_armazenador.criar_tabela_usuarios(conexao)
    armazenador.criar_tabelas(conexao)
    conversas_armazenador.criar_tabelas(conexao)
    conexao.execute(f"TRUNCATE {TABELAS}")
    conexao.commit()
    yield conexao
    conexao.execute(f"TRUNCATE {TABELAS}")
    conexao.commit()
    conexao.close()
