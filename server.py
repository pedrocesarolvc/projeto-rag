"""
Entrypoint local para expor o Lastro via túnel público (Cloudflare
Tunnel) na apresentação — sobe a mesma API FastAPI de app/main.py via
uvicorn na porta 7860, igual a rodar `uvicorn app.main:app`, só que
como script (mais simples de deixar em background).
"""

import uvicorn

from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
