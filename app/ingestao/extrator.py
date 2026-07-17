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
