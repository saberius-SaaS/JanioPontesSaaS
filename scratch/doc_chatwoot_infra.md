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

## 4. Troubleshooting e Configurações Críticas (Nginx)
Durante migrações (como a mudança de região da VM), as configurações do Nginx podem ser perdidas ou sobrescritas. Para garantir o funcionamento em tempo real e em iframes, as seguintes regras são obrigatórias no `/etc/nginx/sites-available/chatwoot` (certifique-se de que `/etc/nginx/sites-enabled/chatwoot` seja sempre um **symlink** e não um arquivo solto).

### Regras Obrigatórias Nginx:
1. **Permitir Iframe:** Remover o bloqueio padrão do Rails (`X-Frame-Options: SAMEORIGIN`) adicionando `proxy_hide_header X-Frame-Options;` no bloco raiz `/`.
2. **WebSockets (Action Cable):** Criar um bloco isolado `location /cable` passando explicitamente os cabeçalhos `Upgrade $http_upgrade` e `Connection "upgrade"` (minúsculo), além de um timeout elevado.

```nginx
server {
  server_name chat.seu_dominio.com.br;

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_hide_header X-Frame-Options; # CRÍTICO PARA IFRAMES
  }

  location /cable {
    proxy_pass http://127.0.0.1:3000/cable;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade"; # MINÚSCULO E OBRIGATÓRIO
    proxy_set_header Host $host;
    proxy_read_timeout 86400; # MANTER WEBSOCKET ABERTO
  }
}
```
