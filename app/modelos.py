"""
Schemas Pydantic — os contratos de dados entre as etapas do pipeline.

Ingestão, chunking, vetorização, busca e resposta trocam dados pelas
formas definidas aqui. Validar formato e tipo em um único lugar evita
que cada etapa reimplemente sua própria checagem, e deixa explícito o
que uma etapa espera receber da anterior.

Os schemas concretos (ex.: modelo de um chunk, de uma pergunta, de uma
resposta com citação) nascem junto com a etapa que os introduz.

Etapa 7: os contratos internos entre etapas (Etapas 2-6) continuam
como dicts simples — são os contratos já documentados em cada etapa,
e mudar a forma agora só para caber em um BaseModel não ensinaria
nada. Os schemas abaixo são só da borda: o que a API expõe por HTTP.
"""

from pydantic import BaseModel, EmailStr, Field


class RegistroRequest(BaseModel):
    """Corpo de POST /auth/registrar (Etapa 7, seção 7.2)."""

    email: EmailStr
    senha: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Corpo de POST /auth/login."""

    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    """Resposta de POST /auth/registrar e POST /auth/login."""

    token: str


class DocumentoResponse(BaseModel):
    """Resposta de POST /documentos e GET /documentos/{id} (Etapa 7, seção 7.2)."""

    id: int
    nome_original: str
    status: str  # "indexando" | "pronto" | "falhou"


class PerguntaRequest(BaseModel):
    """
    Corpo de POST /perguntas. Entre 1 e 2 documentos por pergunta: a
    resposta junta o que vier de todos eles. O teto de 2 é uma escolha
    do v1 (a busca e o prompt crescem com cada documento), não uma
    limitação do desenho — subir é trocar este número.
    """

    documento_ids: list[int] = Field(min_length=1, max_length=2)
    pergunta: str
    # Sem conversa_id, a pergunta abre uma conversa nova com esses
    # documentos; com ele, continua a conversa existente (os documentos
    # pedidos precisam ser dela, ou um subconjunto dela).
    conversa_id: int | None = None


class NovaConversaRequest(BaseModel):
    """Corpo de POST /conversas: os documentos (1 a 2, como em PerguntaRequest) que ela consulta."""

    documento_ids: list[int] = Field(min_length=1, max_length=2)


class VincularDocumentoRequest(BaseModel):
    """Corpo de POST /conversas/{id}/documentos: o documento a acrescentar à conversa."""

    documento_id: int


class Citacao(BaseModel):
    """Um chunk recuperado, exibido ao lado da resposta como fonte (Etapa 6, seção 6.6)."""

    documento: str
    pagina: int
    texto: str
    distancia: float


class RespostaResponse(BaseModel):
    """Resposta de POST /perguntas."""

    resposta: str
    citacoes: list[Citacao]
    # A conversa onde a pergunta foi registrada: a que o cliente pediu,
    # ou a que acabou de nascer quando ele não pediu nenhuma.
    conversa_id: int


class MensagemResponse(BaseModel):
    """Uma pergunta e a resposta dela, como foram gravadas na conversa."""

    id: int
    pergunta: str
    resposta: str
    citacoes: list[Citacao]


class ConversaResponse(BaseModel):
    """Uma conversa na estante: os documentos dela dão o título da lombada."""

    id: int
    documentos: list[DocumentoResponse]


class ConversaDetalheResponse(ConversaResponse):
    """GET /conversas/{id}: a conversa com todo o histórico de mensagens."""

    mensagens: list[MensagemResponse]
