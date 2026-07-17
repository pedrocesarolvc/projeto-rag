"""
Etapa 2 — Ingestão: extração de texto do PDF.

Abre o arquivo validado por upload.py usando PyMuPDF e extrai o texto
página por página, mantendo o número da página junto de cada trecho.
Essa associação texto-página é o que permite, no fim do pipeline,
citar exatamente a página que fundamentou a resposta (Etapa 1,
seção 1.3 — a citação não é enfeite, é requisito).

Limitações conhecidas e assumidas aqui, não escondidas: texto em duas
colunas pode sair embaralhado (PDF não garante ordem de leitura) e
tabelas viram texto corrido (PDF não guarda estrutura de tabela).
"""

import fitz
from fastapi import HTTPException


def extrair(caminho: str) -> list[dict]:
    """
    Extrai o texto de `caminho`, página por página.

    Retorna exatamente o contrato que a Etapa 3 espera:

        [{"pagina": 1, "texto": "..."}, {"pagina": 2, "texto": "..."}, ...]

    Páginas sem texto (em branco) não entram na lista. `sort=True`
    reordena os blocos de texto por posição na página, o que reduz —
    sem eliminar — o problema de ordem de leitura em duas colunas.

    Levanta HTTPException (400) para os casos que quebram a extração:
    PDF corrompido, PDF protegido por senha, ou PDF sem nenhuma
    camada de texto (escaneado — a soma do texto de todas as páginas
    fica vazia). Nenhum desses três é consertável ajustando parâmetros;
    o único remédio para o último seria OCR, que fica fora do v1.
    """
    try:
        doc = fitz.open(caminho)
    except fitz.FileDataError:
        raise HTTPException(status_code=400, detail="PDF corrompido ou inválido.")

    if doc.needs_pass:
        doc.close()
        raise HTTPException(
            status_code=400,
            detail="PDF protegido por senha não é suportado.",
        )

    paginas = []
    for numero, pagina in enumerate(doc, start=1):
        texto = pagina.get_text("text", sort=True)
        if texto.strip():
            paginas.append({"pagina": numero, "texto": texto})
    doc.close()

    if not paginas:
        raise HTTPException(
            status_code=400,
            detail="Este PDF parece ser digitalizado; OCR não é suportado.",
        )

    return paginas
