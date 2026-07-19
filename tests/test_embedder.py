"""
Testes da Etapa 4 (indexação): geração de embeddings.

O embedding não é determinístico no sentido de valores previsíveis —
não dá para escrever "o vetor de 'contrato' deve ser [0.2, ...]". O
que se testa são propriedades (seção 4.10 de docs/documentacao.md):
dimensão, determinismo, e a afirmação central da etapa — perto é
parecido.
"""

import math

from app.indexacao.embedder import DIMENSAO, gerar_embeddings


def _distancia_cosseno(a: list[float], b: list[float]) -> float:
    produto = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    return 1 - produto / (norma_a * norma_b)


# --- o vetor gerado tem exatamente a dimensão da coluna ---


def test_vetor_tem_a_dimensao_esperada():
    vetores = gerar_embeddings(["qualquer texto de exemplo"])

    assert len(vetores) == 1
    assert len(vetores[0]) == DIMENSAO


# --- o mesmo texto gera o mesmo vetor duas vezes ---


def test_mesmo_texto_gera_o_mesmo_vetor():
    texto = "O distrato devera ser comunicado com 90 dias de antecedencia."

    vetor1 = gerar_embeddings([texto])[0]
    vetor2 = gerar_embeddings([texto])[0]

    assert vetor1 == vetor2


# --- textos de sentido próximo ficam mais perto que textos distantes ---


def test_textos_parecidos_ficam_mais_perto_que_textos_distantes():
    cachorro, cao, planilha = gerar_embeddings(["cachorro", "cão", "planilha"])

    distancia_perto = _distancia_cosseno(cachorro, cao)
    distancia_longe = _distancia_cosseno(cachorro, planilha)

    assert distancia_perto < distancia_longe
