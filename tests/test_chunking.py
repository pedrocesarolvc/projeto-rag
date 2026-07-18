"""
Testes da Etapa 3 (chunking): divisão do texto em pedaços.

Chunking é determinístico — mesma entrada, mesma saída — e por isso é
testável como a ingestão: sem LLM, sem embedding, sem banco. Os 9
cenários abaixo seguem a seção 3.9 de docs/documentacao.md.
"""

from app.chunking import divisor as modulo_divisor
from app.chunking.divisor import dividir


# --- Texto menor que o tamanho do chunk → devolve exatamente 1 chunk ---


def test_texto_menor_que_o_chunk_devolve_um_chunk(monkeypatch):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 1000)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 150)

    texto = "Um texto curto, que cabe inteiro num único chunk."
    chunks = dividir([{"pagina": 1, "texto": texto}])

    assert chunks == [{"indice": 0, "pagina": 1, "texto": texto}]


# --- Texto vazio → devolve 0 chunks ---


def test_texto_vazio_devolve_zero_chunks():
    assert dividir([{"pagina": 1, "texto": ""}]) == []
    assert dividir([]) == []


# --- Nenhum chunk excede o tamanho máximo / nenhuma palavra é cortada ---


def test_nenhum_chunk_excede_o_tamanho_maximo_e_nenhuma_palavra_e_cortada(
    monkeypatch,
):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 100)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 20)

    palavras = [f"palavra{n:03d}" for n in range(200)]
    palavras_validas = set(palavras)
    texto = " ".join(palavras)

    chunks = dividir([{"pagina": 1, "texto": texto}])

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["texto"]) <= 100
        for token in chunk["texto"].split():
            assert token in palavras_validas


# --- Todo chunk carrega uma página válida ---


def test_todo_chunk_carrega_uma_pagina_valida(monkeypatch):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 50)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 10)

    paginas = [
        {"pagina": 1, "texto": "Primeira pagina com um pouco de texto para dividir."},
        {"pagina": 2, "texto": "Segunda pagina, também com texto suficiente."},
    ]
    chunks = dividir(paginas)

    numeros_validos = {1, 2}
    assert chunks  # tem conteúdo o suficiente para gerar chunk
    for chunk in chunks:
        assert chunk["pagina"] in numeros_validos


# --- Nenhum chunk atravessa páginas ---


def test_nenhum_chunk_atravessa_paginas(monkeypatch):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 1000)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 100)

    paginas = [
        {"pagina": 1, "texto": "Conteudo exclusivo da pagina um."},
        {"pagina": 2, "texto": "Conteudo exclusivo da pagina dois."},
    ]
    chunks = dividir(paginas)

    for chunk in chunks:
        if chunk["pagina"] == 1:
            assert "pagina dois" not in chunk["texto"]
        else:
            assert "pagina um" not in chunk["texto"]


# --- A sobreposição existe de fato ---


def test_sobreposicao_existe_de_fato(monkeypatch):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 100)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 30)

    palavras = [f"palavra{n:03d}" for n in range(60)]
    texto = " ".join(palavras)
    chunks = dividir([{"pagina": 1, "texto": texto}])

    assert len(chunks) >= 2
    for anterior, atual in zip(chunks, chunks[1:]):
        ultima_palavra_anterior = anterior["texto"].split()[-1]
        # a cauda do chunk anterior deve aparecer bem no início do próximo
        assert ultima_palavra_anterior in atual["texto"][:50]


# --- Os índices são sequenciais e sem buraco ---


def test_indices_sao_sequenciais_e_sem_buraco(monkeypatch):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 60)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 15)

    paginas = [
        {"pagina": 1, "texto": " ".join(f"pag1palavra{n}" for n in range(30))},
        {"pagina": 2, "texto": " ".join(f"pag2palavra{n}" for n in range(30))},
    ]
    chunks = dividir(paginas)

    indices = [c["indice"] for c in chunks]
    assert indices == list(range(len(chunks)))


# --- Parágrafo curto seguido de outro não é fundido nem estilhaçado ---


def test_paragrafos_curtos_ficam_no_mesmo_chunk_com_separador_preservado(
    monkeypatch,
):
    monkeypatch.setattr(modulo_divisor, "TAMANHO_CHUNK_CARACTERES", 1000)
    monkeypatch.setattr(modulo_divisor, "SOBREPOSICAO_CARACTERES", 100)

    texto = "Primeiro paragrafo curto.\n\nSegundo paragrafo tambem curto."
    chunks = dividir([{"pagina": 1, "texto": texto}])

    assert len(chunks) == 1  # não estilhaçado em vários chunks
    assert "\n\n" in chunks[0]["texto"]  # não fundido sem o separador original
