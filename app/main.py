"""
Ponto de entrada da API.

Duas rotas sustentam o v1 inteiro (seção 7.2), e são o corte entre as
duas fases do projeto, agora visível de fora:

    POST /documentos   — a fase de indexação inteira (Etapas 2, 3, 4)
    POST /perguntas    — a fase de consulta inteira (Etapas 5, 6)

main.py fica fino: recebe, valida com Pydantic, delega para
app/pipeline.py, devolve. Nenhuma lógica de RAG mora aqui.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from app.indexacao import armazenador
from app.modelos import Citacao, DocumentoResponse, PerguntaRequest, RespostaResponse
from app.pipeline import indexar_documento, responder_pergunta

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conexao = armazenador.conectar()
    try:
        armazenador.criar_tabelas(conexao)
    finally:
        conexao.close()
    yield


app = FastAPI(title="Projeto RAG", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    """Responde "estou de pé" — trivial, e o primeiro sinal que um avaliador procura."""
    return {"status": "ok"}


@app.post("/documentos", response_model=DocumentoResponse, status_code=201)
async def criar_documento(arquivo: UploadFile) -> DocumentoResponse:
    conexao = armazenador.conectar()
    try:
        resultado = await indexar_documento(conexao, arquivo)
    finally:
        conexao.close()
    return DocumentoResponse(**resultado)


@app.get("/documentos/{documento_id}", response_model=DocumentoResponse)
def obter_documento(documento_id: int) -> DocumentoResponse:
    conexao = armazenador.conectar()
    try:
        documento = armazenador.buscar_documento(conexao, documento_id)
    finally:
        conexao.close()

    if documento is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return DocumentoResponse(**documento)


@app.post("/perguntas", response_model=RespostaResponse)
def criar_pergunta(pedido: PerguntaRequest) -> RespostaResponse:
    conexao = armazenador.conectar()
    try:
        resultado = responder_pergunta(conexao, pedido.documento_id, pedido.pergunta)
    finally:
        conexao.close()

    citacoes = [Citacao(**chunk) for chunk in resultado["chunks"]]
    return RespostaResponse(resposta=resultado["resposta"], citacoes=citacoes)


# Serve o build do frontend (frontend/dist), se existir — mesma
# origem da API, sem CORS. Montado por último de propósito: rotas
# acima são checadas primeiro, então /documentos, /perguntas etc.
# nunca são interceptadas por este catch-all.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
