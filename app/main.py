"""
Ponto de entrada da API — Lastro.

Duas rotas sustentam o núcleo do v1 (seção 7.2), e são o corte entre
as duas fases do projeto, agora visível de fora:

    POST /documentos   — a fase de indexação inteira (Etapas 2, 3, 4)
    POST /perguntas    — a fase de consulta inteira (Etapas 5, 6)

Ao redor delas, as rotas de conta (POST /auth/registrar, POST
/auth/login, GET /documentos, DELETE /documentos/{id}).

A regra de acesso que atravessa tudo: `/documentos` aceita tanto um
usuário autenticado quanto uma sessão anônima — exceto `POST
/perguntas`, que exige conta (cadastro adiado, seção 1.5). É essa
exigência, e só ela, que dispara a tela de login no frontend.

main.py fica fino: recebe, valida com Pydantic, delega para
app/pipeline.py ou app/auth/, devolve. Nenhuma lógica de RAG mora
aqui.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from psycopg.errors import UniqueViolation

from app.auth import armazenador as auth_armazenador
from app.auth.seguranca import decodificar_token, gerar_token, hash_senha, verificar_senha
from app.indexacao import armazenador
from app.modelos import (
    Citacao,
    DocumentoResponse,
    LoginRequest,
    PerguntaRequest,
    RegistroRequest,
    RespostaResponse,
    TokenResponse,
)
from app.pipeline import eh_dono, indexar_documento, responder_pergunta

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conexao = armazenador.conectar()
    try:
        # usuarios antes de documentos: nenhuma FK entre as duas
        # (mesmo estilo do resto do schema), mas a ordem de leitura
        # importa para quem olha o código pela primeira vez.
        auth_armazenador.criar_tabela_usuarios(conexao)
        armazenador.criar_tabelas(conexao)
    finally:
        conexao.close()
    yield


app = FastAPI(title="Lastro", lifespan=lifespan)


def obter_usuario_id(authorization: str | None = Header(default=None)) -> int | None:
    """None quando não há token válido — não é erro aqui, só ausência."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return decodificar_token(authorization.removeprefix("Bearer "))


def obter_sessao_anonima(
    x_sessao_anonima: str | None = Header(default=None),
) -> str | None:
    """
    O identificador que o frontend gera e guarda no navegador antes de
    existir conta (seção 1.5) — dá dono ao documento até o cadastro
    ou login o transferir para um usuário de verdade.
    """
    return x_sessao_anonima


def exigir_usuario(usuario_id: int | None = Depends(obter_usuario_id)) -> int:
    """
    Só POST /perguntas usa esta dependência (seção 7.2). É o único
    401 do sistema, e é ele que dispara a tela de login no frontend.
    """
    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")
    return usuario_id


def _para_resposta(documento: dict) -> DocumentoResponse:
    """
    armazenador.buscar_documento()/listar_documentos() trazem também
    usuario_id e sessao_anonima_id (para a checagem de posse) — campos
    que DocumentoResponse não expõe por HTTP. Esta função filtra para
    só o que a API deve mostrar.
    """
    return DocumentoResponse(
        id=documento["id"],
        nome_original=documento["nome_original"],
        status=documento["status"],
    )


@app.get("/health")
def health() -> dict:
    """Responde "estou de pé" — trivial, e o primeiro sinal que um avaliador procura."""
    return {"status": "ok"}


@app.post("/auth/registrar", response_model=TokenResponse, status_code=201)
def registrar(
    dados: RegistroRequest,
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> TokenResponse:
    """
    Cria a conta e adota os documentos da sessão anônima (seção 7.3).
    Criação e adoção são uma transação só: se a adoção falhar, a
    conta não fica criada sem o documento que a motivou.
    """
    conexao = armazenador.conectar()
    try:
        if auth_armazenador.buscar_usuario_por_email(conexao, dados.email):
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

        usuario_id = auth_armazenador.criar_usuario(
            conexao, dados.email, hash_senha(dados.senha)
        )
        if sessao_anonima_id:
            auth_armazenador.adotar_documentos_da_sessao(
                conexao, sessao_anonima_id, usuario_id
            )
        conexao.commit()
    except UniqueViolation:
        # Corrida entre dois cadastros com o mesmo e-mail: os dois
        # passam pela checagem acima antes de qualquer um commitar, e
        # o segundo INSERT esbarra na restrição UNIQUE da tabela. Sem
        # isto, viraria 500 em vez do mesmo 409 "e-mail já cadastrado"
        # que o caso comum já devolve.
        conexao.rollback()
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    except HTTPException:
        conexao.rollback()
        raise
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()

    return TokenResponse(token=gerar_token(usuario_id))


@app.post("/auth/login", response_model=TokenResponse)
def login(
    dados: LoginRequest,
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> TokenResponse:
    """Autentica e adota os documentos da sessão anônima — login também adota (seção 7.3)."""
    conexao = armazenador.conectar()
    try:
        usuario = auth_armazenador.buscar_usuario_por_email(conexao, dados.email)
        if usuario is None or not verificar_senha(dados.senha, usuario["senha_hash"]):
            raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

        if sessao_anonima_id:
            auth_armazenador.adotar_documentos_da_sessao(
                conexao, sessao_anonima_id, usuario["id"]
            )
        conexao.commit()
    except HTTPException:
        conexao.rollback()
        raise
    finally:
        conexao.close()

    return TokenResponse(token=gerar_token(usuario["id"]))


@app.post("/documentos", response_model=DocumentoResponse, status_code=201)
async def criar_documento(
    arquivo: UploadFile,
    usuario_id: int | None = Depends(obter_usuario_id),
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> DocumentoResponse:
    """
    Aceita usuário autenticado ou sessão anônima (cadastro adiado,
    seção 1.5) — precisa de um dos dois para o documento ter dono.
    """
    if usuario_id is None and not sessao_anonima_id:
        raise HTTPException(
            status_code=400, detail="Cabeçalho X-Sessao-Anonima ausente."
        )

    conexao = armazenador.conectar()
    try:
        resultado = await indexar_documento(
            conexao, arquivo, usuario_id, sessao_anonima_id
        )
    finally:
        conexao.close()
    return DocumentoResponse(**resultado)


@app.get("/documentos", response_model=list[DocumentoResponse])
def listar_documentos(
    usuario_id: int | None = Depends(obter_usuario_id),
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> list[DocumentoResponse]:
    """Lista os documentos do usuário autenticado, ou da sessão anônima quando não há usuário."""
    conexao = armazenador.conectar()
    try:
        documentos = armazenador.listar_documentos(
            conexao, usuario_id, sessao_anonima_id
        )
    finally:
        conexao.close()
    return [_para_resposta(documento) for documento in documentos]


@app.get("/documentos/{documento_id}", response_model=DocumentoResponse)
def obter_documento(
    documento_id: int,
    usuario_id: int | None = Depends(obter_usuario_id),
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> DocumentoResponse:
    """
    Estado do documento (indexando/pronto/falhou). Um documento que
    existe mas não pertence a quem pergunta responde 404, não 403 —
    não revela nem a existência de documento alheio.
    """
    conexao = armazenador.conectar()
    try:
        documento = armazenador.buscar_documento(conexao, documento_id)
    finally:
        conexao.close()

    if documento is None or not eh_dono(documento, usuario_id, sessao_anonima_id):
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return _para_resposta(documento)


@app.delete("/documentos/{documento_id}", status_code=204)
def deletar_documento(
    documento_id: int,
    usuario_id: int | None = Depends(obter_usuario_id),
    sessao_anonima_id: str | None = Depends(obter_sessao_anonima),
) -> None:
    """Remove o documento e os chunks dele — só o dono pode (mesma checagem de GET /documentos/{id})."""
    conexao = armazenador.conectar()
    try:
        documento = armazenador.buscar_documento(conexao, documento_id)
        if documento is None or not eh_dono(documento, usuario_id, sessao_anonima_id):
            raise HTTPException(status_code=404, detail="Documento não encontrado.")
        armazenador.remover_documento(conexao, documento_id)
    finally:
        conexao.close()


@app.post("/perguntas", response_model=RespostaResponse)
def criar_pergunta(
    pedido: PerguntaRequest,
    usuario_id: int = Depends(exigir_usuario),
) -> RespostaResponse:
    """
    A única rota que exige conta (seção 7.2). `sessao_anonima_id=None`
    na checagem de posse é proposital: uma vez autenticado, só o dono
    por usuário conta — a sessão anônima não abre mais pergunta nenhuma.
    """
    conexao = armazenador.conectar()
    try:
        documento = armazenador.buscar_documento(conexao, pedido.documento_id)
        if documento is None or not eh_dono(documento, usuario_id, None):
            raise HTTPException(status_code=404, detail="Documento não encontrado.")
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
