"""
Etapa 4 — Indexação: geração de embeddings.

Converte texto em vetor usando um modelo de embedding local (seção
4.5 de docs/documentacao.md): grátis, roda offline, e o documento não
sai da máquina — ao contrário de mandar cada chunk para uma API.

A regra inegociável da seção 4.5: o mesmo modelo que vetoriza os
chunks tem de vetorizar a pergunta na Etapa 5. Vetores de modelos
diferentes vivem em mapas diferentes; medir distância entre eles não
significa nada. Por isso o modelo é uma constante deste módulo, não
um parâmetro — trocá-lo é uma decisão de projeto que obriga
reindexar tudo, não uma escolha por chamada.
"""

from sentence_transformers import SentenceTransformer

# Multilíngue (cobre português) e local. Produz vetores de 768
# dimensões — é esse número, e não outro, que a coluna
# chunks.vetor (Etapa 4, seção 4.9) precisa declarar.
NOME_MODELO = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DIMENSAO = 768

# Carregado uma vez por processo. Instanciar o modelo tem custo (lê
# os pesos do disco); reutilizar a mesma instância entre chamadas é
# o que torna gerar_embeddings barato na segunda vez em diante.
_modelo: SentenceTransformer | None = None


def _carregar_modelo() -> SentenceTransformer:
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(NOME_MODELO)
    return _modelo


def gerar_embeddings(textos: list[str]) -> list[list[float]]:
    """
    Gera um vetor de DIMENSAO números por texto, na mesma ordem da
    entrada. Mesmo texto, mesmo vetor sempre — o modelo é
    determinístico (Etapa 4, seção 4.10).
    """
    if not textos:
        return []
    modelo = _carregar_modelo()
    vetores = modelo.encode(textos, convert_to_numpy=True)
    return [vetor.tolist() for vetor in vetores]
