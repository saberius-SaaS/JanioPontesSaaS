"""
8.1.3 — Testes para as rotas CRUD de protocolos, clientes e scheduler.
Valida que as rotas respondem corretamente e que os dados são persistidos.
"""
import pytest


class TestCrudClientes:
    """Testa o ciclo completo de vida do módulo de Clientes."""

    def test_listagem_clientes_retorna_200(self, client):
        response = client.get("/clientes")
        assert response.status_code == 200

    def test_busca_clientes_retorna_200(self, client):
        response = client.get("/clientes/search?q=teste")
        assert response.status_code == 200

    def test_criar_cliente_via_form(self, client):
        response = client.post("/clientes", data={
            "cliente": "Empresa Teste Ltda",
            "cnpj": "12.345.678/0001-99",
            "responsavel": "João Silva",
            "email": "joao@empresa.com",
            "telefone": "(21) 99999-0000"
        })
        assert response.status_code == 200
        assert "Empresa Teste" in response.text

    def test_busca_encontra_cliente_criado(self, client):
        # Primeiro cria
        client.post("/clientes", data={
            "cliente": "Busca Empresa ABC",
            "cnpj": "00.000.000/0001-00"
        })
        # Depois busca
        response = client.get("/clientes/search?q=Busca Empresa")
        assert response.status_code == 200
        assert "Busca Empresa ABC" in response.text


class TestCrudObrigacoes:
    """Testa o ciclo completo de vida do módulo de Obrigações/Regras."""

    def test_listagem_obrigacoes_retorna_200(self, client):
        response = client.get("/obrigacoes")
        assert response.status_code == 200

    def test_criar_obrigacao_via_form(self, client):
        response = client.post("/obrigacoes", data={
            "obrigacao": "DCTFWeb Teste",
            "dia": "15",
            "departamento": "FISCAL",
            "regime": "SIMPLES",
            "acao": "ENVIAR"
        })
        assert response.status_code == 200
        assert "DCTFWeb Teste" in response.text


class TestCrudProtocolos:
    """Testa o ciclo completo de vida do módulo de Protocolos."""

    def test_listagem_protocolos_retorna_200(self, client):
        response = client.get("/protocolos")
        assert response.status_code == 200

    def test_busca_protocolos_retorna_200(self, client):
        response = client.get("/protocolos/search?q=PRT")
        assert response.status_code == 200

    def test_criar_protocolo_via_form(self, client):
        response = client.post("/protocolos", data={
            "cliente": "Empresa Protocolo Teste",
            "obrigacao": "DCTF Mensal",
            "email": "test@example.com"
        })
        assert response.status_code == 200
        assert "PRT-" in response.text


class TestSchedulerEndpoints:
    """Testa os endpoints de rotinas agendadas (CRON)."""

    def test_check_overdue_retorna_200(self, client):
        response = client.post("/scheduler/check-overdue")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "updated_count" in data

    def test_daily_report_retorna_200(self, client):
        response = client.post("/scheduler/daily-report")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "report_sent_to" in data


class TestWebhookEndpoints:
    """Testa a rota de recepção de webhooks do Chatwoot."""

    def test_webhook_chatwoot_aceita_payload(self, client):
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "Olá, recebi o documento, obrigado!",
            "sender": {"name": "Cliente Teste"}
        }
        response = client.post("/webhook/chatwoot", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_webhook_chatwoot_payload_vazio(self, client):
        response = client.post("/webhook/chatwoot", json={"event": "unknown"})
        assert response.status_code == 200
