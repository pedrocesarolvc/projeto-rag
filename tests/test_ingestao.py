"""
Testes da Etapa 2 (ingestão): upload e extração de texto.

Cobre as partes determinísticas do pipeline. Dado um PDF de entrada
(tests/fixtures/), o texto extraído e a página de origem de cada
trecho são previsíveis e, portanto, testáveis sem depender de LLM,
embedding ou banco de dados — o que é reservado para as etapas
seguintes, quando existirem.
"""

import asyncio
import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.ingestao import upload as modulo_upload
from app.ingestao.extrator import extrair
from app.ingestao.upload import ASSINATURA_PDF, receber_upload

FIXTURES = Path(__file__).parent / "fixtures"


def _upload_file(caminho: Path, nome: str | None = None) -> UploadFile:
    conteudo = caminho.read_bytes()
    return UploadFile(file=io.BytesIO(conteudo), filename=nome or caminho.name)


# --- extrator.py: PDF de texto simples → páginas e conteúdo conferem ---


def test_extrai_texto_simples_pagina_por_pagina():
    paginas = extrair(str(FIXTURES / "texto_simples.pdf"))

    assert len(paginas) == 2
    assert paginas[0]["pagina"] == 1
    assert "distrato" in paginas[0]["texto"].lower()
    assert paginas[1]["pagina"] == 2
    assert "continuacao" in paginas[1]["texto"].lower()


# --- extrator.py: página em branco não entra na lista ---


def test_pagina_em_branco_nao_entra_na_lista():
    paginas = extrair(str(FIXTURES / "pagina_em_branco.pdf"))

    assert [p["pagina"] for p in paginas] == [1, 3]


# --- extrator.py: PDF escaneado (só imagem) → detectado e recusado ---


def test_pdf_escaneado_e_recusado():
    with pytest.raises(HTTPException) as exc:
        extrair(str(FIXTURES / "escaneado.pdf"))

    assert exc.value.status_code == 400


# --- extrator.py: PDF com senha → recusado ---


def test_pdf_com_senha_e_recusado():
    with pytest.raises(HTTPException) as exc:
        extrair(str(FIXTURES / "com_senha.pdf"))

    assert exc.value.status_code == 400


# --- extrator.py: PDF corrompido → recusado ---


def test_pdf_corrompido_e_recusado():
    with pytest.raises(HTTPException) as exc:
        extrair(str(FIXTURES / "corrompido.pdf"))

    assert exc.value.status_code == 400


# --- upload.py: PDF válido é aceito e guardado com nome gerado ---


def test_upload_pdf_valido_e_aceito(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo_upload, "DIRETORIO_UPLOADS", tmp_path)

    arquivo = _upload_file(FIXTURES / "texto_simples.pdf")
    resultado = asyncio.run(receber_upload(arquivo))

    assert resultado["nome_original"] == "texto_simples.pdf"
    assert resultado["nome_gerado"] != "texto_simples.pdf"  # nome sempre gerado
    caminho_salvo = Path(resultado["caminho"])
    assert caminho_salvo.exists()
    assert caminho_salvo.read_bytes().startswith(ASSINATURA_PDF)


# --- upload.py: arquivo .txt renomeado para .pdf → recusado no upload ---


def test_arquivo_que_nao_e_pdf_e_recusado():
    arquivo = _upload_file(FIXTURES / "nao_e_pdf.pdf")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(receber_upload(arquivo))

    assert exc.value.status_code == 400


# --- upload.py: arquivo acima do limite de tamanho → recusado ---


def test_arquivo_acima_do_limite_e_recusado(monkeypatch):
    monkeypatch.setattr(modulo_upload, "TAMANHO_MAXIMO_BYTES", 10)

    conteudo = ASSINATURA_PDF + b"0" * 100
    arquivo = UploadFile(file=io.BytesIO(conteudo), filename="grande.pdf")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(receber_upload(arquivo))

    assert exc.value.status_code == 400


# --- upload.py: nome de arquivo com ../ não escapa do diretório previsto ---


def test_nome_com_path_traversal_nao_escapa_do_diretorio(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo_upload, "DIRETORIO_UPLOADS", tmp_path)

    arquivo = _upload_file(
        FIXTURES / "texto_simples.pdf", nome="../../../../config/.env"
    )
    resultado = asyncio.run(receber_upload(arquivo))

    caminho_salvo = Path(resultado["caminho"]).resolve()
    assert caminho_salvo.parent == tmp_path.resolve()
