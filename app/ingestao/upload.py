"""
Etapa 2 — Ingestão: recebimento e validação do arquivo.

Recebe o PDF enviado pelo usuário, valida que é de fato um PDF, que
tem texto extraível (PDF escaneado é recusado com mensagem clara — o
projeto não faz OCR) e guarda o arquivo em disco para que
extrator.py o processe em seguida.

O v1 aceita um documento por vez; não há gestão de coleções de
múltiplos arquivos (fica no roadmap).
"""
