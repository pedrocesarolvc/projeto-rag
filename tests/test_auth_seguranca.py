"""
Testes de app/auth/seguranca.py: hash de senha e token — determinísticos
o bastante para testar de verdade, sem precisar de banco (bcrypt e
JWT são só função pura + biblioteca padrão).
"""

from datetime import timedelta

from app.auth.seguranca import decodificar_token, gerar_token, hash_senha, verificar_senha


def test_hash_senha_nao_guarda_texto_puro():
    hash_ = hash_senha("minha-senha-123")

    assert hash_ != "minha-senha-123"


def test_verificar_senha_aceita_a_senha_certa():
    hash_ = hash_senha("minha-senha-123")

    assert verificar_senha("minha-senha-123", hash_) is True


def test_verificar_senha_rejeita_senha_errada():
    hash_ = hash_senha("minha-senha-123")

    assert verificar_senha("outra-senha-qualquer", hash_) is False


def test_token_gerado_decodifica_para_o_mesmo_usuario():
    token = gerar_token(42)

    assert decodificar_token(token) == 42


def test_token_invalido_devolve_none():
    assert decodificar_token("isto-nao-e-um-token-jwt") is None


def test_token_expirado_devolve_none(monkeypatch):
    import app.auth.seguranca as modulo

    monkeypatch.setattr(modulo, "EXPIRACAO_TOKEN", timedelta(seconds=-1))

    token = gerar_token(1)

    assert decodificar_token(token) is None
