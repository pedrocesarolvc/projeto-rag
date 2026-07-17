"""
Testes da Etapa 2 (ingestão): upload e extração de texto.

Cobre as partes determinísticas do pipeline. Dado um PDF de entrada
(tests/fixtures/), o texto extraído e a página de origem de cada
trecho são previsíveis e, portanto, testáveis sem depender de LLM,
embedding ou banco de dados — o que é reservado para as etapas
seguintes, quando existirem.
"""
