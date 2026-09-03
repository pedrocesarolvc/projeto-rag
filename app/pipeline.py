"""
Etapa 7 — Entrega: orquestração entre as etapas, chamada pelas rotas.

main.py fica fino (seção 7.2): recebe HTTP, valida com Pydantic,
delega para cá, devolve. Nenhuma lógica de RAG mora na camada de
rota — ela só traduz HTTP em chamada de função e volta.

As duas rotas do núcleo (POST /documentos, POST /perguntas) são a
fronteira indexação/consulta, agora visível de fora: indexar_documento
roda as Etapas 2, 3 e 4; responder_pergunta roda as Etapas 5 e 6.
"""

from fastapi import UploadFile

from app.chunking.divisor import dividir
from app.geracao.responder import responder as gerar_resposta
from app.indexacao import armazenador
from app.ingestao.extrator import extrair
from app.ingestao.upload import receber_upload
from app.recuperacao.buscador import buscar


async def indexar_documento(
    conexao,
    arquivo: UploadFile,
    usuario_id: int | None = None,
    sessao_anonima_id: str | None = None,
) -> dict:
    """
    Roda a fase de indexação inteira para um upload: extrai (Etapa 2),
    divide em chunks (Etapa 3), gera embeddings e grava no banco
    (Etapa 4).

    Síncrono, por decisão do v1 (seção 7.4): a rota só responde depois
    que tudo terminou — o teto de 20 MB da Etapa 2 mantém isso dentro
    do aceitável. Fila assíncrona fica no roadmap.

    `usuario_id` e `sessao_anonima_id` dão dono ao documento desde a
    criação — nunca os dois, conforme quem chamou está autenticado ou
    não (cadastro adiado, seção 1.5).
    """
    meta = await receber_upload(arquivo)
    documento_id = armazenador.criar_documento(
        conexao, meta["nome_original"], usuario_id, sessao_anonima_id
    )

    try:
        paginas = extrair(meta["caminho"])
        chunks = dividir(paginas)
        armazenador.indexar(conexao, documento_id, chunks)
    except Exception:
        armazenador.atualizar_status_documento(conexao, documento_id, "falhou")
        raise

    armazenador.atualizar_status_documento(conexao, documento_id, "pronto")
    return {
        "id": documento_id,
        "nome_original": meta["nome_original"],
        "status": "pronto",
    }


def eh_dono(
    documento: dict, usuario_id: int | None, sessao_anonima_id: str | None
) -> bool:
    """
    A regra de acesso do v1 (Etapa 1, "documentos por usuário"): um
    documento é visível a quem o criou — o usuário dono, ou, enquanto
    não houver dono, a sessão anônima que fez o upload.

    Um documento já adotado (`usuario_id` preenchido) nunca mais
    responde à sessão anônima antiga — só ao usuário.
    """
    if documento.get("usuario_id") is not None:
        return usuario_id is not None and documento["usuario_id"] == usuario_id
    return (
        sessao_anonima_id is not None
        and documento.get("sessao_anonima_id") == sessao_anonima_id
    )


def responder_pergunta(conexao, documento_id: int, pergunta: str) -> dict:
    """
    Roda a fase de consulta inteira: busca os chunks mais relevantes
    (Etapa 5) e gera a resposta ancorada neles (Etapa 6).
    """
    chunks = buscar(conexao, documento_id, pergunta)
    return gerar_resposta(pergunta, chunks)
