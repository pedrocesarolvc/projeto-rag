"""
Testes unitários da Etapa 5 (recuperação): buscar() com conexão
simulada (mock), sem depender de Postgres/pgvector.

test_buscador.py cobre os 6 cenários da seção 5.10 fim a fim, mas
pula sem pgvector disponível — o que hoje é sempre, neste ambiente
(ver README, "Limitações conhecidas"). Este arquivo cobre a lógica
Python de buscar() (parâmetros da query, filtro por limiar, formato
do resultado) simulando o que o cursor devolveria, para que ao menos
essa parte tenha cobertura rodando de verdade, sempre.
"""

from unittest.mock import MagicMock

from app.recuperacao.buscador import buscar


def _conexao_fake(linhas: list[tuple]) -> MagicMock:
    cursor_fake = MagicMock()
    cursor_fake.fetchall.return_value = linhas
    cursor_fake.__enter__.return_value = cursor_fake
    cursor_fake.__exit__.return_value = False

    conexao_fake = MagicMock()
    conexao_fake.cursor.return_value = cursor_fake
    return conexao_fake


# --- filtra por limiar e preserva a ordem devolvida pelo banco ---


def test_filtra_resultados_acima_do_limiar():
    linhas = [
        (1, "chunk da pagina 1", 0.10),
        (3, "chunk da pagina 3", 0.55),
        (7, "chunk da pagina 7", 0.72),
    ]

    resultado = buscar(_conexao_fake(linhas), documento_id=42, pergunta="qualquer pergunta", limiar=0.65)

    assert resultado == [
        {"pagina": 1, "texto": "chunk da pagina 1", "distancia": 0.10},
        {"pagina": 3, "texto": "chunk da pagina 3", "distancia": 0.55},
    ]


# --- distância exatamente igual ao limiar é incluída (<=, não <) ---


def test_distancia_igual_ao_limiar_e_incluida():
    resultado = buscar(_conexao_fake([(1, "x", 0.65)]), documento_id=1, pergunta="p", limiar=0.65)

    assert len(resultado) == 1


# --- tudo acima do limiar -> lista vazia (a base do "não sei") ---


def test_tudo_acima_do_limiar_devolve_lista_vazia():
    linhas = [(1, "x", 0.9), (2, "y", 0.95)]

    resultado = buscar(_conexao_fake(linhas), documento_id=1, pergunta="p", limiar=0.65)

    assert resultado == []


# --- banco sem chunks para o documento -> lista vazia ---


def test_banco_sem_resultados_devolve_lista_vazia():
    resultado = buscar(_conexao_fake([]), documento_id=1, pergunta="p")

    assert resultado == []


# --- os parâmetros certos chegam na query, na ordem certa ---


def test_query_recebe_documento_id_e_k_corretos():
    conexao_fake = _conexao_fake([])

    buscar(conexao_fake, documento_id=42, pergunta="qual o prazo?", k=3)

    _, params = conexao_fake.cursor.return_value.execute.call_args[0]
    vetor_select, documento_id, vetor_order_by, k = params

    assert documento_id == 42
    assert k == 3
    # o mesmo vetor da pergunta é usado no SELECT (para calcular a
    # distância exibida) e no ORDER BY (para ordenar) — não pode
    # divergir, ou a distância mostrada mentiria sobre a ordenação
    assert vetor_select == vetor_order_by
    assert isinstance(vetor_select, list)
    assert len(vetor_select) == 768
