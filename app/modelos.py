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
    """Corpo de POST /perguntas."""

    documento_id: int
    pergunta: str


class Citacao(BaseModel):
    """Um chunk recuperado, exibido ao lado da resposta como fonte (Etapa 6, seção 6.6)."""

    pagina: int
    texto: str
    distancia: float


class RespostaResponse(BaseModel):
    """Resposta de POST /perguntas."""

    resposta: str
    citacoes: list[Citacao]
