"""
Testes da Etapa 6 (geração): montagem do prompt.

Determinístico — construção de string, testável como ingestão e
chunking (seção 6.10). A parte não determinística (o que a LLM
responde) fica isolada em llm.py e não é testada aqui.
"""

from app.geracao.prompt import INSTRUCAO, SEM_CONTEXTO, montar_prompt


# --- as três partes entram na ordem certa: instrução, contexto, pergunta ---


def test_prompt_tem_instrucao_contexto_e_pergunta_na_ordem_certa():
    chunks = [{"pagina": 3, "texto": "trecho relevante", "distancia": 0.2}]

    prompt = montar_prompt("qual o prazo de rescisao?", chunks)

    pos_instrucao = prompt.find(INSTRUCAO)
    pos_contexto = prompt.find("trecho relevante")
    pos_pergunta = prompt.find("qual o prazo de rescisao?")

    assert -1 not in (pos_instrucao, pos_contexto, pos_pergunta)
    assert pos_instrucao < pos_contexto < pos_pergunta


# --- todos os chunks recuperados entram no contexto, com sua página ---


def test_todos_os_chunks_entram_no_contexto_com_sua_pagina():
    chunks = [
        {"pagina": 3, "texto": "primeiro trecho", "distancia": 0.1},
        {"pagina": 7, "texto": "segundo trecho", "distancia": 0.3},
    ]

    prompt = montar_prompt("pergunta qualquer", chunks)

    assert "primeiro trecho" in prompt and "pág. 3" in prompt
    assert "segundo trecho" in prompt and "pág. 7" in prompt


# --- contexto vazio produz um prompt que instrui o "não sei" ---


def test_contexto_vazio_produz_prompt_que_instrui_nao_sei():
    prompt = montar_prompt("pergunta sem resposta no documento", [])

    assert SEM_CONTEXTO in prompt
    assert "não encontrou" in prompt  # parte da INSTRUCAO, sempre presente
