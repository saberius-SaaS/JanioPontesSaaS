# 💬 Integração Omnichannel (Chatwoot Self-Hosted)

## 1. Arquitetura
*   **Modelo:** Self-Hosted (Máquina Virtual no Google Compute Engine, Ubuntu 22.04).
*   **Serviços Base:** Rails, Redis, Sidekiq via Docker Compose.
*   **Banco de Dados:** Aponta para a mesma instância Cloud SQL (PostgreSQL) da aplicação SaaS para garantir backups unificados.

## 2. Fluxo de Comunicação e FastAPI
*   **Integração no Portal:** Widget do Chatwoot no template `base.html` (Jinja2), com validação HMAC para autenticação automática do cliente.
*   **Envio de Arquivos (Outbound):** FastAPI envia arquivos (PDFs, guias) para a API do Chatwoot (`multipart/form-data`) ao finalizar uma tarefa. Permite roteamento inteligente (tentar WhatsApp, fallback para E-mail).
*   **Webhooks (Inbound):** Rota POST no FastAPI captura webhooks do Chatwoot (respostas de clientes) e registra no log/histórico de tarefas do sistema.

## 3. Motivo da Escolha
Centraliza WhatsApp, E-mail (via Workspace) e Webchat em um único *Inbox*, substituindo ferramentas pulverizadas (Maxbot). Organiza a comunicação de forma isolada para cada tenant da aplicação.
