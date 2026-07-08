import pytest
import uuid
from app.routers.portal import validar_documento
from app.models.cliente import Cliente
from app.models.tentativa_login import TentativaLogin

def test_validar_documento_cpf():
    # Valida CPF válido (dígitos verificadores corretos)
    cpf_valido = "11144477735"
    assert validar_documento(cpf_valido) == cpf_valido
    assert validar_documento("111.444.777-35") == cpf_valido

    # CPF inválido
    with pytest.raises(ValueError):
        validar_documento("11111111111")
    with pytest.raises(ValueError):
        validar_documento("111.444.777-00")

def test_validar_documento_cnpj():
    # Valida CNPJ válido
    cnpj_valido = "12345678000195"
    assert validar_documento(cnpj_valido) == cnpj_valido
    assert validar_documento("12.345.678/0001-95") == cnpj_valido

    # CNPJ inválido
    with pytest.raises(ValueError):
        validar_documento("12345678000100")

def test_gerar_chave_e_autenticacao(client, db):
    # 1. Cria cliente de teste no banco
    tenant_id = uuid.uuid4()
    # CNPJ válido para teste: 12345678000195
    cliente = Cliente(
        tenant_id=tenant_id,
        cliente="Empresa de Teste Login",
        cnpj="12.345.678/0001-95",
        email="teste@teste.com",
        status="ATIVO"
    )
    db.add(cliente)
    db.commit()

    # 2. Gerar chave via endpoint
    # Precisamos contornar a dependência require_admin que é mockada para retornar um Usuário com admin
    response_chave = client.post(f"/api/clientes/{cliente.id}/gerar-chave-portal")
    assert response_chave.status_code == 200
    data_chave = response_chave.json()
    assert data_chave["ok"] is True

    # 3. Para testar o login, injetamos um hash conhecido
    from app.core.security import get_password_hash
    import json
    from app.core.timezone import agora_br
    
    chave_conhecida = "JP-TESTE"
    hash_teste = get_password_hash(chave_conhecida)
    cliente.chaves_acesso = json.dumps({"teste@teste.com": {"hash": hash_teste, "gerada_em": agora_br().isoformat()}})
    db.commit()

    # 4. Tentar logar com chave correta
    response_login = client.post("/portal/auth", data={
        "documento": "12.345.678/0001-95",
        "email": "teste@teste.com",
        "chave": chave_conhecida
    }, follow_redirects=False)
    
    # Deve redirecionar para /portal
    assert response_login.status_code in [302, 303]
    assert response_login.headers.get("location") == "/portal"
    assert "__session" in response_login.headers.get("set-cookie", "")

    # 5. Tentar logar com chave incorreta
    response_errada = client.post("/portal/auth", data={
        "documento": "12.345.678/0001-95",
        "email": "teste@teste.com",
        "chave": "JP-ERRADA"
    })
    assert response_errada.status_code == 401
    assert "Dados de acesso incorretos" in response_errada.text

    # 5. Rate limiting: verificar registro de falhas no banco
    tentativas = db.query(TentativaLogin).filter(TentativaLogin.documento == "12345678000195").all()
    assert len(tentativas) >= 1
