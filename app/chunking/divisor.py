"""
Etapa 3 — Chunking: divisão do texto em pedaços.

Entra: a lista de páginas com texto (contrato da Etapa 2). Sai: uma
lista de chunks, cada um com o texto, a página de origem e um índice
sequencial — pronta para ganhar o vetor na Etapa 4.

Estratégia: corte recursivo por separadores (parágrafo, linha, frase,
espaço), nunca tamanho fixo cego. Um chunk vira um único vetor; se ele
mistura assuntos, o vetor é a média deles e não representa nenhum —
cortar em fronteiras de significado (parágrafo primeiro) é o que
mantém o vetor focado. (docs/documentacao.md, Etapa 3, seções 3.2 e 3.5)

O chunk nunca atravessa página: cada página é dividida de forma
independente. Perde-se um parágrafo que atravessa a virada de página
(vira dois chunks); ganha-se citação sem ambiguidade — a página de um
chunk é sempre uma única página, nunca um intervalo. Trade-off
assumido, não escondido (seção 3.7).
"""

# Chute educado, não medido — não há evals ainda (Etapa 3, seção 3.6).
# ~400 tokens / ~60 tokens, a ~4 caracteres por token em português.
TAMANHO_CHUNK_CARACTERES = 1600
SOBREPOSICAO_CARACTERES = 240

# Do mais para o menos prioritário: tenta preservar a fronteira de
# significado mais forte (parágrafo) antes de recorrer a um corte
# mais bruto. Nunca chega a cortar dentro de uma palavra.
SEPARADORES = ["\n\n", "\n", ".", " "]


def _fragmentar(texto: str, separadores: list[str]) -> list[str]:
    """
    Quebra `texto` em fragmentos atômicos que já cabem no tamanho do
    chunk, tentando os separadores em ordem de prioridade. Cada
    fragmento carrega o separador que o encerrava, para que a
    concatenação dos fragmentos reproduza o texto original — inclusive
    a quebra de parágrafo, que _mesclar_com_sobreposicao depende de
    preservar.

    Se um fragmento ainda for grande demais depois de esgotados todos
    os separadores (uma palavra isolada maior que o teto), ele é
    devolvido do mesmo jeito: nunca se corta uma palavra ao meio, nem
    para respeitar o tamanho máximo.
    """
    if not texto:
        return []
    if not separadores:
        return [texto]

    separador, *resto = separadores
    partes = texto.split(separador)

    fragmentos = []
    for i, parte in enumerate(partes):
        ultimo = i == len(partes) - 1
        pedaco = parte if ultimo else parte + separador
        if not pedaco:
            continue
        if len(pedaco) <= TAMANHO_CHUNK_CARACTERES:
            fragmentos.append(pedaco)
        else:
            fragmentos.extend(_fragmentar(pedaco, resto))
    return fragmentos


def _mesclar_com_sobreposicao(fragmentos: list[str]) -> list[str]:
    """
    Agrupa fragmentos em chunks de até TAMANHO_CHUNK_CARACTERES,
    repetindo no início de cada chunk a cauda (~SOBREPOSICAO_CARACTERES)
    do chunk anterior.

    Dois invariantes competem aqui, e o tamanho máximo sempre vence: se
    manter a sobreposição faria o próximo chunk estourar o teto (a
    cauda mais o próximo fragmento já passam do limite — só acontece
    quando um fragmento isolado é grande), a sobreposição é descartada
    para aquele chunk em vez de violar o teto. Como se trabalha sempre
    com fragmentos inteiros, nunca se corta uma palavra para caber.
    """
    if not fragmentos:
        return []

    chunks: list[str] = []
    janela: list[str] = []
    tamanho_janela = 0

    for fragmento in fragmentos:
        if janela and tamanho_janela + len(fragmento) > TAMANHO_CHUNK_CARACTERES:
            chunks.append("".join(janela))

            # cauda da sobreposição: mantém fragmentos do fim do chunk
            # que acabou de fechar, até ~SOBREPOSICAO_CARACTERES.
            while len(janela) > 1 and tamanho_janela > SOBREPOSICAO_CARACTERES:
                removido = janela.pop(0)
                tamanho_janela -= len(removido)

            if tamanho_janela + len(fragmento) > TAMANHO_CHUNK_CARACTERES:
                janela = []
                tamanho_janela = 0

        janela.append(fragmento)
        tamanho_janela += len(fragmento)

    if janela:
        chunks.append("".join(janela))

    return chunks


def dividir(paginas: list[dict]) -> list[dict]:
    """
    Divide o texto de cada página em chunks, seguindo o contrato:

        [{"indice": 0, "pagina": 1, "texto": "..."}, ...]

    O índice é sequencial e global (não reinicia a cada página); a
    página nunca é ambígua porque cada página é processada de forma
    independente, sem juntar texto de páginas diferentes.
    """
    chunks = []
    indice = 0
    for pagina in paginas:
        fragmentos = _fragmentar(pagina["texto"], SEPARADORES)
        for texto_chunk in _mesclar_com_sobreposicao(fragmentos):
            chunks.append(
                {"indice": indice, "pagina": pagina["pagina"], "texto": texto_chunk}
            )
            indice += 1
    return chunks
