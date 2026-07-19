"""
Testes da Etapa 6 (geração): responder() com a LLM mockada.

A saída da LLM não é determinística (seção 6.10) — nenhum teste
verifica "a resposta é exatamente esta string". O que se testa são
os arredores, que são determinísticos: o prompt foi montado certo, e
a função de LLM foi chamada uma vez, com ele. Um dublê (mock) fica no
lugar da API real — sem isso, o teste seria lento, custaria e ficaria
instável, exatamente o que a Etapa 6 avisa para não fazer.
"""

from unittest.mock import MagicMock

import app.geracao.responder as modulo_responder


# --- gerar() é chamado uma vez, com o prompt montado ---


def test_gerar_e_chamado_uma_vez_com_o_prompt_montado(monkeypatch):
    gerar_fake = MagicMock(return_value="resposta qualquer da LLM")
    monkeypatch.setattr(modulo_responder, "gerar", gerar_fake)

    chunks = [{"pagina": 3, "texto": "trecho relevante", "distancia": 0.1}]
    resultado = modulo_responder.responder("qual o prazo de rescisao?", chunks)

    gerar_fake.assert_called_once()
    (prompt_recebido,), _ = gerar_fake.call_args
    assert "trecho relevante" in prompt_recebido
    assert "qual o prazo de rescisao?" in prompt_recebido


# --- o retorno traz a resposta e os chunks, para a citação na interface ---


def test_retorno_traz_resposta_e_os_chunks_recebidos(monkeypatch):
    monkeypatch.setattr(modulo_responder, "gerar", MagicMock(return_value="a resposta"))

    chunks = [{"pagina": 5, "texto": "trecho", "distancia": 0.2}]
    resultado = modulo_responder.responder("pergunta qualquer", chunks)

    assert resultado == {"resposta": "a resposta", "chunks": chunks}


# --- contexto vazio: gerar() ainda é chamado, com o prompt do "não sei" ---


def test_chunks_vazios_ainda_chama_gerar_com_prompt_de_nao_sei(monkeypatch):
    gerar_fake = MagicMock(return_value="não encontrei isso no documento")
    monkeypatch.setattr(modulo_responder, "gerar", gerar_fake)

    resultado = modulo_responder.responder("pergunta sem resposta", [])

    gerar_fake.assert_called_once()
    assert resultado["chunks"] == []
