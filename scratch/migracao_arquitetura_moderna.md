# 🚀 Checklist de Reestruturação e Migração (Nova Instância DB)

Este documento centraliza as tarefas necessárias para inicializar a nossa nova instância de banco de dados e completar a migração do sistema GAS para o GCP.
Todo o conhecimento teórico e arquitetural foi transferido para a base de conhecimento focada:
- 📖 [Arquitetura RLS e Multi-Tenant](./doc_arquitetura_rls_multitenant.md)
- 📖 [Segurança, IAM e Deploy GCP](./doc_seguranca_deploy_gcp.md)
- 📖 [Infraestrutura Chatwoot](./doc_chatwoot_infra.md)

---

## 🏗️ Fase 1: Inicialização da Nova Instância de Banco de Dados
Como a instância do Cloud SQL foi alterada e está vazia, precisamos recriar toda a estrutura do zero.
- [x] **1.1.** Configurar as variáveis de ambiente (`.env` local e Cloud Run) para apontar para a nova instância do banco.
- [x] **1.2.** Rodar as migrações do Alembic (`alembic upgrade head`) para recriar todas as tabelas (clientes, solicitacoes, usuarios, etc).
- [x] **1.3.** Aplicar as políticas de Row-Level Security (RLS) e recriar as Roles do PostgreSQL.
- [x] **1.4.** Criar o usuário Super Admin (owner) no banco de dados para acesso inicial ao portal.

## 📦 Fase 2: Construção da Rotina de Migração e Carga de Testes
O objetivo aqui é trazer uma "fotografia" atual do GAS para que você possa fazer testes exaustivos sem medo de sujar o banco de dados.
- [x] **2.1.** Mapear e exportar os dados essenciais das planilhas do GAS atual (DB_CLIENTES, DB_REGRAS, DB_USUARIOS, DB_WORKFLOWS).
- [x] **2.2.** Desenvolver um **script de importação automatizado** (`scripts/migracao_gas_to_pg.py`).
- [x] **2.3.** Rodar o script no banco de dados novo para termos um ambiente "Sandbox" populado com dados reais (129 clientes, 58 regras, 10 usuários, 69 workflows).
- [ ] **2.4.** Testar intensivamente a plataforma (criar, alterar, excluir, testar webhooks) sabendo que **esses dados serão apagados depois**.

## 📧 Modo Sandbox (Interceptação de E-mails)
O sistema opera em **modo de interceptação**: todas as funcionalidades rodam 100% (uploads reais, links acessíveis, e-mails reais via Gmail API), mas **todos os e-mails são redirecionados exclusivamente para `janiopontes@janiopontes.com.br`**, independentemente do destinatário original.

### 🔀 Procedimento de Go-Live (Liberar comunicação para clientes)
Quando todos os testes forem aprovados, basta alterar **UMA variável** em dois lugares (`.env` local e `$ENV_VARS` no `deploy.ps1`):
De `EMAIL_MODE=intercept` para `EMAIL_MODE=production`.

## 🔧 Fase 3: Módulos Pendentes e Próximos Passos (Durante os testes)
- [x] **Integração Chatwoot x FastAPI**: Conectar o Portal (SaaS) ao Chatwoot via Webhooks e envio outbound. *(A Infraestrutura já está 100% pronta e rodando em chat.janiopontes.com.br).*
- [ ] **Notificações via WhatsApp**: Conectar a API oficial no Chatwoot e desligar o Maxbot (GAS Legacy).

## 🌪️ Fase 4: Cutover (A Grande Virada)
No dia escolhido para o lançamento oficial:
- [ ] **4.1.** Travar a edição das planilhas do GAS atual (modo leitura para os usuários).
- [ ] **4.2.** **Limpeza (Wipe):** Rodar um comando para limpar todas as tabelas do banco de dados novo (ex: `alembic downgrade base` e depois `alembic upgrade head`), eliminando toda a "sujeira" dos testes.
- [ ] **4.3.** **Carga Final:** Executar o **script de importação automatizado** desenvolvido na Fase 2 com a fotografia *final e definitiva* do GAS.
- [ ] **4.4.** Validar a integridade da carga definitiva (quantidades, status, datas).

## 🚀 Fase 5: Go-Live (Lançamento em Produção)
- [ ] **5.1.** Habilitar script de Reverse Sync: Cada novo registro no novo banco salva uma cópia na planilha antiga (Rollback/Backup de segurança).
- [ ] **5.2.** Mudar variável `EMAIL_MODE` para `production`.
- [ ] **5.3.** Iniciar a operação exclusiva no novo sistema (nova URL de acesso `app.janiopontes.com.br`).
- [ ] **5.4.** Acompanhar os logs no *Google Cloud Logging* intensivamente por 48h.
- [ ] **5.5.** Fim da janela de 72h: Desligar o *Reverse Sync*.
- [ ] **5.6.** Arquivar os scripts antigos do Google Apps Script definitivamente.
