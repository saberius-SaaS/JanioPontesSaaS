# 🔐 Segurança e Deploy no Google Cloud Platform

## 1. Infraestrutura
*   **Backend:** FastAPI em contêiner Docker rodando no Google Cloud Run.
*   **Banco de Dados:** Google Cloud SQL (PostgreSQL). Conexão via Unix Socket (Cloud SQL Connector), sem IP público exposto.
*   **Storage:** Google Cloud Storage (`janio-pontes-saas-docs`). Acesso via Service Account.

## 2. Hardening e Permissões IAM
*   **Cloud Run:** Papel "Chamador do Cloud Run" para `allUsers` (acesso público).
*   **Service Account (`jpsaas-backend`):** Possui apenas permissões mínimas (Princípio do menor privilégio). Inclui obrigatoriamente "Administrador de Objetos do Storage".
*   **Autenticação Restrita:** Login exclusivamente via Google OAuth, validando que somente e-mails `@janiopontes.com.br` acessem a plataforma. JWT expira em 8 horas.

## 3. Gestão de Segredos (GCP Secret Manager)
*   O arquivo `.env` não é versionado.
*   Credenciais como `DB_PASSWORD`, `SECRET_KEY` (64+ caracteres gerados aleatoriamente), e `GOOGLE_CLIENT_SECRET` estão armazenados no **GCP Secret Manager**.
*   O Cloud Run lê os segredos diretamente do Secret Manager para as variáveis de ambiente.

## 4. Segurança da Aplicação FastAPI
*   Rotas estruturais e CRUDs protegidos por `Depends(require_login)` ou `Depends(require_admin)`.
*   Swagger UI (`/docs`) desativado ou restrito em produção.
*   Headers HTTP de segurança aplicados via middleware (CSP, X-Frame-Options, HSTS).

## 5. Processo de Deploy
Pipeline atual executa testes unitários/integração (`pytest`), constrói a imagem Docker, envia para o Artifact Registry e lança nova revisão no Cloud Run. O deploy local (`deploy.ps1`) gerencia chaves sem expor no repositório.
