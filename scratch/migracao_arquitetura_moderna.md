# 🚀 Checklist Final de Migração (Status Board)

Este documento centraliza as tarefas finais da migração do sistema GAS para GCP.
Todo o conhecimento teórico e arquitetural foi transferido para a base de conhecimento focada:
- 📖 [Arquitetura RLS e Multi-Tenant](./doc_arquitetura_rls_multitenant.md)
- 📖 [Segurança, IAM e Deploy GCP](./doc_seguranca_deploy_gcp.md)
- 📖 [Infraestrutura Chatwoot](./doc_chatwoot_infra.md)

---

## 📧 Modo Sandbox (Interceptação de E-mails)
O sistema opera em **modo de interceptação**: todas as funcionalidades rodam 100% (uploads reais, links acessíveis, e-mails reais via Gmail API), mas **todos os e-mails são redirecionados exclusivamente para `janiopontes@janiopontes.com.br`**, independentemente do destinatário original.

Cada e-mail interceptado contém:
- Um banner amarelo indicando o destinatário original.
- O assunto prefixado com `[INTERCEPTADO de cliente@email.com]`.

### 🔀 Procedimento de Go-Live (Liberar comunicação para clientes)
Quando todos os testes forem aprovados, basta alterar **UMA variável** em dois lugares:

| Arquivo | Variável | Valor Atual | Valor Go-Live |
|---|---|---|---|
| `.env` (local) | `EMAIL_MODE` | `intercept` | `production` |
| `deploy.ps1` (Cloud Run) | `EMAIL_MODE` na lista `$ENV_VARS` | `intercept` | `production` |

Após a alteração, rode `.\deploy.ps1` para publicar. Nenhuma outra mudança de código é necessária.

- [x] **9.3.1.** Verificar se o Cloud SQL aceita conexões *apenas via Unix Socket* (sem IP público exposto).
- [x] **9.3.2.** Criar usuário PostgreSQL dedicado para a aplicação (`app_user`) com privilégios mínimos.
- [x] **9.3.4.** Habilitar backups automáticos no Cloud SQL com retenção de 7 dias.
- [x] **9.4.3.** Escrever teste automatizado (pytest) para RLS (validação cruzada entre tenants).
- [x] **9.4.4.** Verificar se `app.bypass_rls = 'on'` existe *somente* em rotas internas (scheduler, seed).
- [x] **9.5.1.** Auditar todas as rotas FastAPI garantindo `Depends(require_login)` ou `Depends(verify_scheduler_key)`.
- [x] **9.5.3.** Adicionar *rate limiting* nas rotas públicas (especialmente `/login`).

## 🔧 Módulos Prioritários (Pós-Auditoria)
- [x] **Workflows e Múltiplas Fases**: Implementar lógica de etapas contínuas para tarefas (Ex: Contábil > Fiscal > Paralegal). Desenvolvimento imediato. *(Concluído: a lógica de encadeamento automático via "Próxima Fase" já está operando 100% nas rotas atuais!)*
- [x] **Portal do Cliente / Repositório**: Desenvolver interface dedicada e segura (login restrito) para o cliente consultar todo o histórico de arquivos e obrigações. *(Concluído: Implementado com "Link Mágico" e módulo de Solicitações integrado ao portal).*
- [x] **Ferramentas Admin (GAS Legacy)**: Incorporar os scripts utilitários do sistema GAS para dentro do SaaS. *(Concluído: Gerador de Tarefas Híbrido e Disparador de Comunicados Oficiais em Massa inseridos na aba Ferramentas).*
- [ ] *Notificações via WhatsApp*: Será migrado no futuro com a adoção do Chatwoot (Aguardando integração futura).
- [ ] *Inteligência Artificial (AIService)*: Será migrado no futuro como projeto específico (Pausado).

## 🚀 Conclusão da Migração Final e Migração de Dados (Pendências)
- [ ] **10.2.1.** Travar a edição das planilhas do GAS atual (modo leitura).
- [ ] **10.3.1.** Habilitar script de Reverse Sync: Cada novo registro no banco salva uma cópia na planilha antiga (Rollback).
- [ ] **10.3.2.** Manter este script rodando por 72h em produção.

## 🚀 Etapa 11: Go-Live (Lançamento em Produção)
- [x] 11.1.1. Apontar CNAME/A no Registro.br para app.janiopontes.com.br (Via Firebase Hosting proxy)
- [x] 11.1.2. Mapear Domínio no Firebase (bridge para Cloud Run em southamerica-east1)
- [x] 11.1.3. Aguardar emissão do SSL (15-60 minutos)
- [ ] 11.1.4. Mudar variável `EMAIL_MODE` para `production` (Atualmente: `intercept`)
- [ ] 11.1.5. Realizar testes de ponta a ponta em ambiente real nova URL de acesso.
- [ ] **11.2.2.** Iniciar a operação exclusiva no novo sistema.
- [ ] **11.3.1.** Acompanhar os logs no *Google Cloud Logging* intensivamente por 48h.
- [ ] **11.3.2.** Fim da janela de 72h: Desligar o *Reverse Sync*.
- [ ] **11.3.3.** Arquivar os scripts antigos do Google Apps Script definitivamente.
