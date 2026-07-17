"""
Schemas Pydantic — os contratos de dados entre as etapas do pipeline.

Ingestão, chunking, vetorização, busca e resposta trocam dados pelas
formas definidas aqui. Validar formato e tipo em um único lugar evita
que cada etapa reimplemente sua própria checagem, e deixa explícito o
que uma etapa espera receber da anterior.

Os schemas concretos (ex.: modelo de um chunk, de uma pergunta, de uma
resposta com citação) nascem junto com a etapa que os introduz.
"""
