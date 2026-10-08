"""
Testes unitários da Etapa 5 (recuperação): buscar() com conexão
simulada (mock), sem depender de Postgres/pgvector.

test_buscador.py cobre os cenários da seção 5.10 fim a fim, mas pula
sem pgvector disponível. Este arquivo cobre a lógica Python de
buscar() (parâmetros da query, filtro por limiar, junção de vários
documentos, formato do resultado) simulando o que o cursor devolveria,
para que ao menos essa parte tenha cobertura rodando de verdade,
sempre.
"""

from unittest.mock import MagicMock

from pgvector import Vector

from app.recuperacao.buscador import buscar


def _conexao_fake(*respostas_por_consulta: list[tuple]) -> MagicMock:
    """
    Cada argumento é o que UMA consulta devolveria (fetchall), na ordem
    em que buscar() as faz — uma por documento.
    """
    cursor_fake = MagicMock()
    cursor_fake.fetchall.side_effect = list(respostas_por_consulta)
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

    resultado = buscar(
        _conexao_fake(linhas), documento_ids=[42], pergunta="qualquer pergunta", limiar=0.65
    )

    assert resultado == [
        {"documento_id": 42, "pagina": 1, "texto": "chunk da pagina 1", "distancia": 0.10},
        {"documento_id": 42, "pagina": 3, "texto": "chunk da pagina 3", "distancia": 0.55},
    ]


# --- distância exatamente igual ao limiar é incluída (<=, não <) ---


def test_distancia_igual_ao_limiar_e_incluida():
    resultado = buscar(
        _conexao_fake([(1, "x", 0.65)]), documento_ids=[1], pergunta="p", limiar=0.65
    )

    assert len(resultado) == 1


# --- tudo acima do limiar -> lista vazia (a base do "não sei") ---


def test_tudo_acima_do_limiar_devolve_lista_vazia():
    linhas = [(1, "x", 0.9), (2, "y", 0.95)]

    resultado = buscar(_conexao_fake(linhas), documento_ids=[1], pergunta="p", limiar=0.65)

    assert resultado == []


# --- banco sem chunks para o documento -> lista vazia ---


def test_banco_sem_resultados_devolve_lista_vazia():
    resultado = buscar(_conexao_fake([]), documento_ids=[1], pergunta="p")

    assert resultado == []


# --- os parâmetros certos chegam na query, na ordem certa ---


def test_query_recebe_documento_id_e_k_corretos():
    conexao_fake = _conexao_fake([])

    buscar(conexao_fake, documento_ids=[42], pergunta="qual o prazo?", k=3)

    _, params = conexao_fake.cursor.return_value.execute.call_args[0]
    vetor_select, documento_id, vetor_order_by, k = params

    assert documento_id == 42
    assert k == 3
    # o mesmo vetor da pergunta é usado no SELECT (para calcular a
    # distância exibida) e no ORDER BY (para ordenar) — não pode
    # divergir, ou a distância mostrada mentiria sobre a ordenação
    assert vetor_select == vetor_order_by
    # Vector, não list: é o tipo que o adaptador do pgvector reconhece
    # como parâmetro — uma list pura cai no dumper padrão do psycopg e
    # vira array double precision, e o operador <=> não casa com isso
    # (achado testando contra um Postgres real — ver buscador.py)
    assert isinstance(vetor_select, Vector)
    assert len(vetor_select.to_list()) == 768


# --- vários documentos: uma consulta por documento, com o k de cada um ---


def test_faz_uma_consulta_por_documento_com_o_k_de_cada():
    """
    O top-k é por documento (ver docstring de buscar()): cada documento
    recebe a própria consulta e o próprio LIMIT k — é isso que impede um
    PDF de ocupar todas as vagas e esconder o outro.
    """
    conexao_fake = _conexao_fake([], [])

    buscar(conexao_fake, documento_ids=[10, 20], pergunta="p", k=5)

    chamadas = conexao_fake.cursor.return_value.execute.call_args_list
    assert len(chamadas) == 2
    documentos_consultados = [chamada[0][1][1] for chamada in chamadas]
    ks = [chamada[0][1][3] for chamada in chamadas]
    assert documentos_consultados == [10, 20]
    assert ks == [5, 5]


def test_o_vetor_da_pergunta_e_calculado_uma_unica_vez(monkeypatch):
    import app.recuperacao.buscador as modulo_buscador

    gerar_fake = MagicMock(return_value=[[0.0] * 768])
    monkeypatch.setattr(modulo_buscador, "gerar_embeddings", gerar_fake)

    buscar(_conexao_fake([], []), documento_ids=[10, 20], pergunta="p")

    gerar_fake.assert_called_once()


# --- vários documentos: junta, marca a origem e ordena por distância ---


def test_junta_chunks_dos_dois_documentos_ordenados_por_distancia():
    do_primeiro = [(1, "trecho do primeiro", 0.30), (2, "outro do primeiro", 0.60)]
    do_segundo = [(5, "trecho do segundo", 0.10)]

    resultado = buscar(
        _conexao_fake(do_primeiro, do_segundo), documento_ids=[10, 20], pergunta="p"
    )

    assert [(r["documento_id"], r["distancia"]) for r in resultado] == [
        (20, 0.10),
        (10, 0.30),
        (10, 0.60),
    ]


def test_um_documento_sem_chunks_relevantes_nao_atrapalha_o_outro():
    """Se o assunto só existe num PDF, o outro simplesmente não contribui."""
    do_primeiro = [(1, "longe demais", 0.90)]
    do_segundo = [(5, "relevante", 0.20)]

    resultado = buscar(
        _conexao_fake(do_primeiro, do_segundo), documento_ids=[10, 20], pergunta="p"
    )

    assert [r["documento_id"] for r in resultado] == [20]
