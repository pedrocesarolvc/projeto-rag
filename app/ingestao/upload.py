"""
Etapa 2 — Ingestão: recebimento e validação do arquivo.

Recebe o PDF enviado pelo usuário, valida o tamanho e a assinatura de
bytes (é de fato um PDF?), e guarda o arquivo em disco com um nome
gerado para que extrator.py o processe em seguida. A validação de
conteúdo — PDF corrompido, protegido por senha ou sem texto
extraível (escaneado) — só é possível ao abrir o arquivo, e por isso
é responsabilidade de extrator.py, não deste módulo.

O v1 aceita um documento por vez; não há gestão de coleções de
múltiplos arquivos (fica no roadmap).
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

# Teto do v1. Sem limite, um único arquivo grande derruba o processo.
TAMANHO_MAXIMO_BYTES = 20 * 1024 * 1024  # 20 MB

# Todo PDF começa com esta sequência de bytes. Extensão é sugestão;
# bytes são fato — é assim que se valida o tipo pelo conteúdo, não
# pelo nome do arquivo.
ASSINATURA_PDF = b"%PDF-"

# Fora da árvore da aplicação (app/), de propósito: é onde o PDF
# original fica guardado para permitir reindexar sem novo upload.
# Listado em .gitignore — não é versionado.
DIRETORIO_UPLOADS = Path(__file__).resolve().parent.parent.parent / "uploads"


async def receber_upload(arquivo: UploadFile) -> dict:
    """
    Valida e guarda o PDF enviado.

    Levanta HTTPException (400) para arquivo acima do limite de
    tamanho ou sem a assinatura de PDF nos bytes iniciais — nenhum
    dos dois casos chega perto da extração de texto.

    O nome usado para escrever em disco é sempre gerado (UUID), nunca
    o nome enviado pelo usuário: usar o nome do usuário para montar um
    caminho abre a porta para path traversal (ex.: "../../config/.env").
    O nome original é devolvido apenas como metadado.
    """
    conteudo = await arquivo.read()

    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Arquivo acima do limite de 20 MB.",
        )

    if not conteudo.startswith(ASSINATURA_PDF):
        raise HTTPException(
            status_code=400,
            detail="Arquivo não é um PDF válido.",
        )

    nome_gerado = f"{uuid.uuid4()}.pdf"
    DIRETORIO_UPLOADS.mkdir(parents=True, exist_ok=True)
    caminho = DIRETORIO_UPLOADS / nome_gerado
    caminho.write_bytes(conteudo)

    return {
        "nome_original": arquivo.filename,
        "nome_gerado": nome_gerado,
        "caminho": str(caminho),
    }
