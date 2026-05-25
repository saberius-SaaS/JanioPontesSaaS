# 🏛️ Plano de Migração Arquitetural Enterprise (GAS para GCP Native)

A migração de um sistema Google Apps Script (GAS) operacional para uma arquitetura moderna exige um planejamento rigoroso. Como a sua empresa já possui uma infraestrutura corporativa **Google Workspace**, a decisão arquitetural mais robusta, coesa e de nível empresarial é centralizar a infraestrutura no **Google Cloud Platform (GCP)**.

Este documento avalia a arquitetura nativa na nuvem (GCP) proposta em comparação com ecossistemas descentralizados (Supabase/Vercel), focando em **governança, segurança, performance e eficiência de custo**.

---

## 1. Avaliação da Arquitetura Google Cloud Native (A Proposta Ideal)

A arquitetura sugerida por você representa o padrão-ouro de engenharia de software sustentável (*Server-Side Rendering* moderno com contêineres gerenciados).

| Camada | Tecnologia Escolhida | Avaliação Técnica & Vantagens Corporativas |
| :--- | :--- | :--- |
| **Backend** | **Python 3.12+ (FastAPI)** | **Perfeito.** FastAPI é um dos frameworks web mais rápidos do mercado (assíncrono, baseado em Starlette/Pydantic). Permite documentação automática (Swagger), processamento rápido e integrações robustas com IA e webhooks. |
| **Banco de Dados** | **Google Cloud SQL (PostgreSQL)** | **Padrão Enterprise.** Banco de dados relacional totalmente gerenciado pela Google. Backups automáticos, alta disponibilidade, criptografia em repouso e sem o engessamento do Google Sheets. É a base definitiva para milhões de registros. |
| **Frontend / UI** | **Jinja2 + Tailwind CSS + HTML5** | **Decisão Estratégica Brilhante.** Ao invés de criar um frontend separado (React/Vercel) que gera complexidade de CORS e duplo deploy, usar *Server-Side Rendering* (SSR) com Jinja2 entrega o HTML já montado pelo servidor. É incrivelmente rápido, SEO-friendly e simplifica drasticamente a manutenção (um único repositório de código). Tailwind garante o design premium. |
| **Integrações** | **Gmail API (via Workspace)** | **Aproveitamento de Ecossistema.** Ao invés de pagar serviços externos (SendGrid), utiliza-se o domínio já aquecido da empresa. Maior taxa de entrega (deliverability) e rastreamento nativo dentro do seu Workspace. |
| **Hospedagem** | **Google Cloud Run** | **Estado da Arte em Serverless.** O sistema é empacotado em um contêiner Docker. O Cloud Run escala automaticamente para milhares de acessos em segundos e **escala para zero** quando não há uso. Você paga estritamente pelos milissegundos de CPU consumidos. |

---

## 2. Comparativo Arquitetural: GCP Native vs Ecossistema Descentralizado

Para fins de auditoria, comparamos a estrutura GCP com a alternativa descentralizada baseada em Supabase + Vercel.

| Critério | Stack Google Cloud (Sua Proposta) 🏆 | Stack Descentralizada (Supabase/Vercel) |
| :--- | :--- | :--- |
| **Governança & Billing** | **Centralizada.** Faturamento unificado no GCP, atrelado ao painel do seu Google Workspace. | Descentralizada. Contas separadas no Supabase, Vercel, serviço de email, etc. |
| **Complexidade de Deploy** | **Baixa.** Um único contêiner (Backend + Jinja2) sobe no Cloud Run via GitHub Actions. | Média. Deploy separado do frontend (Vercel) e backend/banco (Supabase). |
| **Segurança e Rede** | **Máxima.** O Cloud Run pode se conectar ao Cloud SQL via VPC interna, sem expor o banco à internet pública. | Alta, porém as requisições transitam via internet pública entre os provedores. |
| **Custo Inicial (Startup)** | ~ U$ 10 a U$ 15 / mês. O Cloud Run e Gmail API são praticamente gratuitos (Free Tier), o custo base é a menor instância do Cloud SQL. | U$ 0 inicial, porém custos ocultos escalam rapidamente com o tráfego de rede (Egress). |
| **Manutenibilidade** | **Excelente.** Python é maduro, desenvolvedores são fáceis de encontrar e a arquitetura MVC com Jinja2 é comprovada e estável. | Boa, mas frameworks frontend (React/Next) sofrem mutações drásticas anualmente. |

**Veredito:** A arquitetura **GCP Native + SSR (Jinja2)** é, sem dúvida, a mais profissional. Ela foge das tendências voláteis do mercado (hypes de frameworks frontend) e aposta em tecnologias estáveis, seguras e com custo altamente previsível.

---

## 3. Rota Profissional de Migração (Roadmap)

A transição do GAS para o Cloud Run deve ser feita sob o conceito de **Tolerância Zero a Falhas**, mantendo a operação atual intacta enquanto a nova infraestrutura é homologada.

### Fase 1: Infraestrutura As Code e Configuração (Semanas 1-2)
1. **Configuração GCP:** Habilitar Cloud Run, Cloud SQL Admin API, Gmail API e Cloud Build no seu Google Cloud Console associado ao Workspace.
2. **Setup do Banco:** Instanciar o PostgreSQL no Cloud SQL (instância `db-f1-micro` com IP privado e backup diário).
3. **Modelagem de Dados:** Criar os esquemas via SQLAlchemy (ORM do Python) reproduzindo a estrutura normalizada de `Clientes`, `Protocolos`, `Historico` e `Usuarios`.

### Fase 2: Desenvolvimento do Core Backend & Frontend (Semanas 3-5)
1. **Motor FastAPI:** Construir as rotas principais.
2. **Integração Workspace:** Autenticação via Google OAuth (Login com a conta Google do usuário) e integração com a Gmail API usando Service Accounts do Workspace para disparo de notificações.
3. **Conversão de UI (Jinja2):** Portar todo o código atual do `Portal_JS.html` e `Portal.html` para templates limpos em Jinja2. O Tailwind CSS será compilado no processo de build do Docker.

### Fase 3: Migração de Dados a Quente (Semana 6)
1. Construir scripts em Python/GAS para sincronização.
2. Congelar as abas do Google Sheets em um final de semana e realizar o "Dump" (exportação massiva) para o banco PostgreSQL no Cloud SQL.
3. Redirecionar a URL atual do portal para o endereço oficial no Cloud Run (podendo inclusive usar um subdomínio profissional, ex: `app.janiopontes.com.br`).

### Fase 4: Otimizações e Workers Background (Semanas 7-8)
1. Transferir o processamento assíncrono (ex: disparos em massa do WhatsApp Maxbot) para rotinas de Background Tasks nativas do FastAPI.
2. Configurar o **Cloud Scheduler** para substituir os gatilhos de tempo do Apps Script (ex: rodar tarefas de manutenção à meia-noite).

---

## 4. Projeção Profissional de Custos Mensais (TCO)

Focando no menor custo operacional possível, sem sacrificar a segurança empresarial:

*   **Google Cloud Run:** U$ 0. (A cota gratuita do GCP concede 2 milhões de requisições e 360.000 segundos de computação por mês).
*   **Integração Gmail API:** U$ 0. (Incluído na sua assinatura do Google Workspace existente).
*   **Google Cloud SQL (PostgreSQL):** ~ U$ 9 a U$ 14 / mês (Instância compartilhada micro + 10GB de armazenamento SSD de alta performance). Ideal para dezenas de milhares de requisições diárias de escritório.
*   **Storage (Google Cloud Storage):** ~ U$ 0.02 / GB. (Para substituir uploads de clientes no Drive, se necessário).

**Custo Total de Operação Estimado (Fixo):** **~ R$ 60,00 a R$ 80,00 por mês**.

---

## 5. Contribuições Estratégicas de Engenharia

### 5.1 Corrigir Débitos Técnicos Gratuitamente
As 4 vulnerabilidades críticas identificadas na auditoria de segurança do GAS (JWT bypass, funções globais expostas, upload arbitrário, IDs previsíveis) **não precisam ser corrigidas no sistema antigo**. A arquitetura Python/FastAPI já nasce com autenticação OAuth2 nativa, rotas protegidas por decorators (`@require_admin`), upload controlado pelo servidor e IDs criptográficos. **O custo de correção é zero** porque o problema simplesmente não é replicado.

### 5.2 Normalização do Modelo de Dados (PostgreSQL)
Migrar as planilhas para tabelas normalizadas (`clientes`, `obrigacoes`, `protocolos`, `historico`) com chaves estrangeiras elimina a repetição massiva de dados (nome, e-mail, telefone em cada linha) e transforma buscas que hoje varrem milhares de strings em queries indexadas retornando em milissegundos.

### 5.3 Período de Coexistência Controlada (Parallel Run)
Durante 2 a 4 semanas pós-migração, ambos os sistemas devem rodar em paralelo. O GAS continua gravando no Sheets, um script Python sincroniza para o PostgreSQL a cada hora, e a equipe valida a paridade dos dados. Somente após confirmação total é que o GAS é desligado.

### 5.4 Adoção de HTMX no Frontend (Redução de ~80% do JavaScript)
O portal atual possui ~2.500 linhas de JavaScript manual para controlar abas, modais, filtros e chamadas ao servidor. A biblioteca **HTMX** permite substituir a maior parte disso por atributos HTML declarativos (ex: `hx-get="/protocolos"`), combinando perfeitamente com Jinja2 (SSR) e eliminando a necessidade de frameworks pesados como React.

### 5.5 Cloud Scheduler como Substituto dos Triggers GAS
O **Google Cloud Scheduler** (3 jobs gratuitos/mês) substitui perfeitamente os `ScriptApp.newTrigger()` atuais, disparando requisições HTTP para o Cloud Run nos horários configurados, com interface profissional e logs completos.

---

## 6. Lacunas Identificadas na Revisão (Gaps Críticos)

Após revisão completa do documento, as seguintes brechas foram identificadas e precisam ser endereçadas antes da execução:

### 6.1 Plano de Rollback (Ausente)
**O que faltava:** O documento não define o que acontece se algo der errado durante a Fase 3 (Migração de Dados a Quente). Se o novo sistema apresentar um bug crítico na segunda-feira de manhã, qual é o procedimento?

**Correção:** Definir uma janela de rollback garantida de **72 horas** pós-migração. Durante esse período:
- O sistema GAS permanece funcional (apenas com triggers desativados, não deletados).
- O DNS pode ser revertido para o endereço antigo do `script.google.com` em menos de 5 minutos.
- Um script de "reverse sync" (PostgreSQL → Sheets) deve ser construído previamente para garantir que qualquer dado criado no sistema novo possa ser devolvido ao Sheets em caso de emergência.

### 6.2 Estratégia de Testes (Ausente)
**O que faltava:** Nenhuma menção a como validamos que o sistema novo se comporta identicamente ao antigo antes de colocá-lo em produção.

**Correção:** Implementar 3 camadas de teste:
1. **Testes Unitários (pytest):** Cada regra de negócio traduzida do GAS (ex: cálculo de vencimento, critérios de prioridade, lógica de deduplicação do WhatsApp) precisa de um teste automatizado que garante resultado idêntico ao do sistema atual.
2. **Testes de Integração:** Validar que as rotas FastAPI + Cloud SQL + Gmail API funcionam em cadeia (ex: criar protocolo → disparar e-mail → registrar log).
3. **Teste de Aceitação do Usuário (UAT):** A equipe do escritório acessa o sistema novo por 1 semana em ambiente de homologação e reporta divergências.

### 6.3 Observabilidade e Monitoramento (Ausente)
**O que faltava:** O sistema atual registra logs na aba `DB_LOGS` do Sheets. O documento não define como a nova arquitetura monitora erros, latência e saúde do sistema.

**Correção:** Utilizar o **Google Cloud Logging** (nativo e gratuito no GCP). Todo `print()` ou `logger.info()` do Python é capturado automaticamente pelo Cloud Run e exibido no console do GCP. Complementar com:
- **Cloud Monitoring:** Alertas automáticos por e-mail se o sistema ficar fora do ar ou se a latência média ultrapassar 2 segundos. (Gratuito para métricas básicas).
- **Structured Logging:** Logs em formato JSON com campos padronizados (`usuario`, `acao`, `protocolo_id`, `duracao_ms`) para facilitar buscas e auditoria.

### 6.4 Pipeline de Deploy Automatizado — CI/CD (Ausente)
**O que faltava:** O documento menciona "sobe no Cloud Run via GitHub Actions" mas não detalha o fluxo.

**Correção:** Definir o pipeline:
1. O código vive em um repositório privado no **GitHub** (ou Google Cloud Source Repositories, gratuito).
2. A cada `git push` na branch `main`, o **GitHub Actions** (ou Cloud Build) executa automaticamente:
   - Roda os testes (`pytest`).
   - Constrói a imagem Docker.
   - Publica no **Google Artifact Registry**.
   - Faz deploy no Cloud Run.
3. Esse pipeline garante que nenhum código com bug chegue à produção. Custo: **U$ 0** (GitHub Actions oferece 2.000 minutos gratuitos/mês).

### 6.5 Migração dos Arquivos do Google Drive (Ausente)
**O que faltava:** O sistema atual armazena documentos de clientes em pastas do Google Drive (organizadas por cliente/obrigação). O documento não define se esses arquivos permanecem no Drive ou migram para o Cloud Storage.

**Correção — Recomendação:** **Manter os arquivos no Google Drive**. O Drive é gratuito dentro do Workspace (com cota de 30GB a 5TB dependendo do plano) e já está organizado por pastas de clientes. O sistema novo pode acessar os mesmos arquivos via **Google Drive API** (usando Service Account), sem custo adicional de storage e sem necessidade de migrar terabytes de documentos. Novos uploads passariam a ser gerenciados pelo Cloud Storage apenas se o volume futuro justificar.

### 6.6 Separação de Ambientes (Dev / Staging / Produção) (Ausente)
**O que faltava:** Trabalhar diretamente na produção é a principal causa de incidentes em sistemas profissionais. O documento não distingue ambientes.

**Correção:** Criar 2 ambientes no GCP:
- **Staging (Homologação):** Cloud Run com instância separada do Cloud SQL (pode ser a mesma `db-f1-micro` com um banco `staging` isolado). Custo adicional: praticamente zero (o Cloud Run staging escala para zero quando não está em uso).
- **Produção:** O ambiente real com domínio customizado (`app.janiopontes.com.br`).

Toda alteração de código passa primeiro pelo Staging, é validada, e só então é promovida para Produção via o pipeline CI/CD.

---

## 7. Arquitetura Multi-Tenant SaaS (Opção A — Row-Level Security)

**Decisão aprovada:** O sistema será construído desde o dia 1 como uma plataforma SaaS escalável, capaz de atender múltiplos escritórios contábeis sob a mesma infraestrutura, utilizando isolamento por Row-Level Security (RLS) no PostgreSQL.

### 7.1 Modelo de Dados Multi-Tenant

Toda tabela do sistema conterá uma coluna `tenant_id` (UUID) que identifica o escritório proprietário do registro. O PostgreSQL aplicará políticas de segurança automáticas que tornam fisicamente impossível um escritório acessar dados de outro.

```
tenants (id, razao_social, cnpj, logo_url, cor_primaria, plano, criado_em)
   │
   ├── usuarios (id, tenant_id → FK, email, nome, papel, ativo)
   │
   ├── clientes (id, tenant_id → FK, razao_social, emails[], telefones[])
   │
   ├── obrigacoes (id, tenant_id → FK, nome, departamento, periodicidade)
   │
   ├── protocolos (id, tenant_id → FK, cliente_id → FK, obrigacao_id → FK, ...)
   │
   └── historico (id, tenant_id → FK, protocolo_id → FK, acao, timestamp, ...)
```

### 7.2 Isolamento Automático via RLS (Row-Level Security)

Exemplo real de como o PostgreSQL protege os dados:

```sql
-- Ativa RLS na tabela de protocolos
ALTER TABLE protocolos ENABLE ROW LEVEL SECURITY;

-- Cria política: cada usuário só vê linhas do seu tenant
CREATE POLICY tenant_isolation ON protocolos
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

Com essa configuração, mesmo que um desenvolvedor escreva uma query genérica como `SELECT * FROM protocolos`, o banco retornará **somente** os registros do escritório logado. Não existe possibilidade de vazamento entre tenants.

### 7.3 Fluxo de Autenticação Multi-Tenant

```
Usuário acessa app.janiopontes.com.br
    │
    ▼
Login via Google OAuth (Supabase Auth / Google Identity)
    │
    ▼
Backend identifica o email → busca na tabela 'usuarios' → obtém tenant_id
    │
    ▼
Define SET app.current_tenant = '{tenant_id}' na conexão PostgreSQL
    │
    ▼
Todas as queries da sessão são automaticamente filtradas pelo RLS
```

### 7.4 Customização por Escritório (White-Label)

A tabela `tenants` armazena configurações visuais por escritório:
- **Logo:** Cada escritório vê seu próprio logotipo no portal.
- **Cor primária:** O Tailwind CSS aplica a paleta do escritório dinamicamente via variáveis CSS.
- **Domínio customizado (futuro):** Possibilidade de cada escritório acessar via `app.escritorioxyz.com.br` apontando para o mesmo Cloud Run (via mapeamento de domínio).

### 7.5 Impacto no Custo (Escala Horizontal)

| Cenário | Infra Necessária | Custo Mensal Estimado |
|:---|:---|:---|
| 1 escritório (atual) | Cloud SQL micro + Cloud Run | ~ R$ 60-80 |
| 10 escritórios | Mesma infra (RLS isola tudo) | ~ R$ 60-80 |
| 50 escritórios | Cloud SQL small (upgrade de CPU) | ~ R$ 150-200 |
| 100+ escritórios | Cloud SQL medium + Read Replicas | ~ R$ 400-500 |

O custo de servir 10 escritórios é **idêntico** ao de servir 1. A infraestrutura só precisa de upgrade quando o volume combinado de dados e acessos simultâneos justificar. Isso significa que **cada novo cliente é receita pura** até atingir o teto da instância atual.

### 7.6 Controle de Acesso Baseado em Perfis (RBAC)

O sistema distinguirá as permissões de acesso com base no papel (role) atribuído a cada usuário no banco de dados (`usuarios.papel`):
- **ADMIN:** Acesso total à plataforma, incluindo CRUD de Clientes, Obrigações (Regras), Perfis de Clientes, Workflows e gestão de outros Usuários.
- **USER (Operacional):** Acesso restrito. Não visualiza nem edita cadastros estruturais (Clientes, Regras, Perfis, Workflows). O foco deste perfil é a operação de protocolos, atendimento (Chatwoot) e resolução de tarefas designadas.

Isso será implementado no FastAPI através de *Dependências* (ex: `Depends(require_admin)`), garantindo que um `USER` seja bloqueado no backend caso tente acessar rotas restritas. No frontend (Jinja2), os menus de administração serão ocultados para o perfil `USER`.

---

## 8. Integração Omnichannel com Chatwoot (Decisão: Self-Hosted)

Para centralizar a comunicação com os clientes e elevar o nível de suporte da plataforma, o sistema integrará o **Chatwoot** como motor de atendimento Omnichannel. Foi decidido que adotaremos o modelo **Self-Hosted**, rodando um servidor próprio para garantir controle total dos dados e alinhar-se à infraestrutura da nuvem do Google (GCP).

### 8.1 Benefícios e Vantagens da Integração
*   **Centralização Absoluta:** O Chatwoot consolida WhatsApp, E-mail (via Workspace) e o Webchat do Portal em uma única interface (Inbox).
*   **Envio de Arquivos Flexível (Roteamento Inteligente):** O sistema não é limitado a um único canal. O FastAPI, ao finalizar uma tarefa, envia o arquivo anexo (PDFs, guias) para a API do Chatwoot (`multipart/form-data`). A regra de negócio no backend pode decidir enviar via WhatsApp, via E-mail ou ambos. É possível configurar um mecanismo de *Fallback* (ex: "Tente enviar por WhatsApp; se o cliente não possuir, envie por E-mail").
*   **Substituição de Ferramentas Terceiras:** Permite aposentar ferramentas pulverizadas (como Maxbot), mantendo o histórico de interações unificado e seguro.
*   **Pronto para SaaS (Multi-tenant):** As "Inboxes" e "Teams" do Chatwoot isolam a comunicação. Se novos escritórios entrarem na plataforma, cada um terá sua própria caixa de atendimento separada.

### 8.2 Ações Necessárias para Implantação (Roadmap Chatwoot)
1. **Provisionamento de Infra (GCP):**
   - Criar uma **Máquina Virtual (Google Compute Engine)** (Recomendado: 2 vCPUs, 4 a 8GB RAM, Ubuntu 22.04) para hospedar os serviços base (Rails, Redis, Sidekiq) via Docker Compose.
2. **Setup do Banco de Dados:**
   - Apontar o banco de dados de produção do Chatwoot para a mesma instância **Cloud SQL (PostgreSQL)** já criada para a aplicação principal, aproveitando a segurança e os backups automatizados.
3. **Desenvolvimento Frontend (Portal):**
   - Inserir o script do widget do Chatwoot no template base (Jinja2).
   - Implementar validação de identidade (HMAC via FastAPI) para autenticar automaticamente o cliente logado no widget e carregar seu histórico.
4. **Integração Backend (FastAPI):**
   - Desenvolver lógicas no Python para enviar arquivos `multipart/form-data` para a API do Chatwoot quando uma tarefa for concluída.
   - Criar *Endpoints* no FastAPI para receber *Webhooks* do Chatwoot (ex: capturar uma resposta do cliente no WhatsApp e registrar no log de tarefas).

---

## 9. Conclusão Estratégica

A decisão de construir o sistema como **plataforma SaaS multi-tenant desde o dia 1** transforma o projeto de uma simples modernização tecnológica em uma **oportunidade de negócio escalável**. O escritório Janio Pontes deixa de ser apenas usuário do sistema e passa a ser o **dono da plataforma**, podendo comercializá-la para outros escritórios contábeis com custo marginal próximo de zero por novo cliente.

A stack `FastAPI + Cloud SQL (RLS) + Cloud Run + Jinja2/HTMX`, agora potencializada pelo ecossistema de comunicação **Chatwoot Self-Hosted**, funde a velocidade de desenvolvimento do Python com a autoridade de infraestrutura do Google. Tudo isso gerenciado sob o guarda-chuva de faturamento da sua conta Workspace, entregando um produto de altíssimo padrão por um custo operacional otimizado e centralizado.

---

## 10. Roteiro Executivo Passo a Passo (Checklist de Desenvolvimento)

Para garantir que o desenvolvimento ocorra de forma sólida, segura e sequencial (sem pular etapas críticas), este roteiro foi subdividido em micro-tarefas. **A regra de ouro é: uma etapa só pode ser iniciada quando a anterior estiver 100% testada e concluída.**

### 🟢 Etapa 1: Preparação do Ambiente e Infraestrutura Base

**1.1. Criar repositório no GitHub para o código fonte**
- [x] 1.1.1. Criar repositório privado no GitHub (ex: `janio-pontes-saas`).
- [x] 1.1.2. Clonar o repositório para o disco local (`g:\Meu Drive\JanioPontesSaas`).
- [x] 1.1.3. Criar arquivo `.gitignore` padrão para Python/Node.
- [x] 1.1.4. Realizar o primeiro `commit` e `push` de inicialização.

**1.2. Criar o projeto no Google Cloud Platform (GCP)**
- [x] 1.2.1. Acessar o GCP Console com a conta Google corporativa.
- [x] 1.2.2. Criar um novo projeto (ex: `jp-saas-producao`).
- [x] 1.2.3. Vincular a conta de faturamento (Billing) ativa.

**1.3. Habilitar APIs e Credenciais no GCP**
- [x] 1.3.1. Habilitar a API do Cloud Run e Cloud Build.
- [x] 1.3.2. Habilitar a API do Cloud SQL Admin.
- [x] 1.3.3. Habilitar a Gmail API e Google Drive API.
- [x] 1.3.4. Criar uma *Service Account* com permissões necessárias e baixar a chave `.json`.

**1.4. Provisionar o Banco de Dados (PostgreSQL no Cloud SQL)**
- [x] 1.4.1. Criar instância Cloud SQL (PostgreSQL, tier `db-f1-micro`).
- [x] 1.4.2. Definir senha master e criar o database da aplicação (ex: `jpsaas_db`).
- [x] 1.4.3. Configurar rede: Autorizar seu IP local para testes ou instalar o *Cloud SQL Auth Proxy*.

**1.5. Configurar o Ambiente Local**
- [x] 1.5.1. Instalar Python 3.12+ e criar ambiente virtual (`python -m venv venv`).
- [x] 1.5.2. Criar o arquivo `.env` na raiz do projeto.
- [x] 1.5.3. Adicionar variáveis de configuração (String de conexão DB, chaves de API).

### 🟡 Etapa 2: Estruturação do Banco de Dados e Multi-Tenant (RLS)

**2.1. Inicializar o projeto Backend (FastAPI)**
- [x] 2.1.1. Instalar dependências base (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `asyncpg`).
- [x] 2.1.2. Criar estrutura de pastas (`app/models`, `app/routers`, `app/schemas`).
- [x] 2.1.3. Criar arquivo `main.py` e rodar servidor local (Hello World).

**2.2. Desenvolver os Modelos de Dados (Esquema do Banco)**
- [x] 2.2.1. Criar modelo base SQLAlchemy.
- [x] 2.2.2. Codificar modelos `Tenants` e `Usuarios`.
- [x] 2.2.3. Codificar modelos `Clientes` e `Obrigacoes`.
- [x] 2.2.4. Codificar modelos `Protocolos` e `Historico`.

**2.3. Migrações de Banco (Alembic)**
- [x] 2.3.1. Inicializar o Alembic no projeto (`alembic init alembic`).
- [x] 2.3.2. Gerar a primeira migração (`alembic revision --autogenerate`).
- [x] 2.3.3. Aplicar a migração no Cloud SQL (`alembic upgrade head`).

**2.4. Implementar Políticas de Isolamento (Row-Level Security - RLS)**
- [x] 2.4.1. Criar script SQL para habilitar RLS nas tabelas.
- [x] 2.4.2. Criar *Policy* limitando leitura/escrita com base no `tenant_id` ativo.
- [x] 2.4.3. Aplicar o script no banco de dados.

**2.5. Popular o banco (Seed de Teste)**
- [x] 2.5.1. Criar script Python para inserir dados iniciais.
- [x] 2.5.2. Inserir 1 Tenant de teste (Escritório Janio Pontes).
- [x] 2.5.3. Inserir 1 Usuário Admin vinculado ao Tenant.

### 🟠 Etapa 3: Autenticação e Segurança de Acesso

**3.1. Tela Base de Login**
- [x] 3.1.1. Criar arquivo HTML básico com o botão "Entrar com Google".
- [x] 3.1.2. Configurar rota estática no FastAPI para servir essa tela.

**3.2. Fluxo de Autenticação (Google OAuth)**
- [x] 3.2.1. Criar credenciais OAuth 2.0 no GCP (Client ID e Secret).
- [x] 3.2.2. Instalar biblioteca `authlib` ou `google-auth`.
- [x] 3.2.3. Implementar rota de login e rota de callback (receber token do Google).
- [x] 3.2.4. Gerar *JWT (JSON Web Token)* de sessão para o usuário logado.

**3.3. Middleware de Isolamento (O Coração do RLS)**
- [x] 3.3.1. Criar um Middleware no FastAPI que intercepta todas as requisições.
- [x] 3.3.2. Extrair o `tenant_id` do JWT do usuário na requisição.
- [x] 3.3.3. Injetar o comando `SET app.current_tenant = {id}` na sessão do SQLAlchemy.

**3.4. Teste de Isolamento**
- [x] 3.4.1. Criar Tenant B e Usuário B no banco.
- [x] 3.4.2. Logar como Usuário A e tentar ler dados; Logar como B e ler dados.
- [x] 3.4.3. Validar se o RLS bloqueia vazamentos de dados 100%.

### 🔵 Etapa 4: Motor de UI (Frontend Base)

**4.1. Configuração do Jinja2 (SSR)**
- [x] 4.1.1. Instalar `jinja2` e configurar o motor de templates no FastAPI.
- [x] 4.1.2. Criar a pasta `templates/` e um arquivo `base.html`.

**4.2. Configuração do Tailwind CSS**
- [x] 4.2.1. Inicializar o NPM localmente (`npm init -y`).
- [x] 4.2.2. Instalar o Tailwind via CLI (`npm install -D tailwindcss`).
- [x] 4.2.3. Configurar arquivo `tailwind.config.js` para ler a pasta `templates/`.
- [x] 4.2.4. Criar script no `package.json` para compilar o CSS (`npm run watch`).

**4.3. Biblioteca HTMX**
- [x] 4.3.1. Injetar a tag `<script>` do HTMX no `base.html`.
- [x] 4.3.2. Testar uma requisição assíncrona simples (ex: clique de botão recarregando uma div).

**4.4. Desenvolver o Shell da Aplicação**
- [x] 4.4.1. Desenvolver o Menu Lateral (Sidebar) com Tailwind.
- [x] 4.4.2. Desenvolver o Cabeçalho Responsivo (Header).
- [x] 4.4.3. Criar container principal que receberá o conteúdo dinâmico.

### 🟣 Etapa 5: Módulos de Negócio (CRUD e Regras)

**5.1. Módulo de Clientes**
- [x] 5.1.1. Criar rota (Backend) de listagem de clientes.
- [x] 5.1.2. Criar template HTML (Frontend) com a tabela de clientes.
- [x] 5.1.3. Implementar modal/página de criação e edição.
- [x] 5.1.4. Integrar paginação e busca.

**5.2. Módulo de Obrigações/Serviços**
- [x] 5.2.1. Criar rotas CRUD no Backend.
- [x] 5.2.2. Criar telas no Frontend.

**5.3. Módulo Central de Protocolos**
- [x] 5.3.1. Criar rotas para listar os protocolos ativos.
- [x] 5.3.2. Desenvolver o painel (Tabela com filtros dinâmicos).
- [x] 5.3.3. Criar formulário de envio de novo protocolo.

**5.4. Integração Google Drive API**
- [x] 5.4.1. Implementar função de upload de arquivos anexos para uma pasta específica do Drive.
- [x] 5.4.2. Implementar função para gerar link de leitura do arquivo.
- [x] 5.4.3. Conectar a interface (input type=file) à rota do FastAPI.

**5.5. Log de Histórico**
- [x] 5.5.1. Criar função genérica que grava um registro no `Historico` toda vez que um protocolo é alterado.
- [x] 5.5.2. Exibir o histórico na tela de detalhes do protocolo.

**5.6. Módulo de Usuários e Controle de Acesso**
- [x] 5.6.1. Criar rotas CRUD de usuários (Cadastro, Edição, Inativação).
- [x] 5.6.2. Implementar a tela de Gestão de Usuários (acessível apenas para ADMIN).
- [x] 5.6.3. Implementar Middlewares/Dependências no FastAPI para bloquear rotas estruturais (Clientes, Regras, Perfis, Workflows) para o perfil USER.
- [x] 5.6.4. Ocultar menus e botões no Frontend (Jinja2) baseados no papel do usuário logado.

**5.7. Módulo de Perfis (Vinculação a Clientes e Regras)**
- [x] 5.7.1. Criar rotas CRUD para Perfis.
- [x] 5.7.2. Criar interface para vincular Perfis aos Clientes e às Regras.

### 🟤 Etapa 6: Infraestrutura de Comunicação (Chatwoot & E-mails)

**6.1. Provisionar Chatwoot (Self-hosted)**
- [x] 6.1.1. Criar VM no Google Compute Engine (Ubuntu).
- [x] 6.1.2. Instalar Docker e Docker Compose na VM.
- [x] 6.1.3. Baixar arquivo `docker-compose.yaml` do Chatwoot e subir o serviço.

**6.2. Conexão e Autenticação do Chatwoot**
- [x] 6.2.1. Apontar as variáveis de ambiente do Chatwoot para o Cloud SQL.
- [x] 6.2.2. Acessar o painel Admin do Chatwoot e realizar o setup inicial.
- [x] 6.2.3. Incorporar o Widget do Chatwoot no `base.html` do portal e configurar validação HMAC.

**6.3. Disparo de E-mails (Gmail API)**
- [x] 6.3.1. Codificar função Python que formata e-mails.
- [x] 6.3.2. Autenticar com a Service Account e enviar e-mail de teste.
- [x] 6.3.3. Integrar disparo na rotina de "Protocolo Criado".

**6.4. Webhooks do Chatwoot**
- [x] 6.4.1. Criar uma rota POST no FastAPI para receber webhooks do Chatwoot.
- [x] 6.4.2. Configurar o Chatwoot para apontar para essa rota.
- [x] 6.4.3. Implementar a lógica: ler mensagem recebida e atualizar status do protocolo.

### ⚫ Etapa 7: Automações e Tarefas em Segundo Plano (Background Tasks)

**7.1. Background Tasks no FastAPI**
- [x] 7.1.1. Modificar a rota de envio de protocolo para que e-mails sejam enviados via `BackgroundTasks`.
- [x] 7.1.2. Modificar rotinas de comunicação do Chatwoot para usar a mesma estratégia.

**7.2. Endpoints de Rotinas Diárias**
- [x] 7.2.1. Criar rota que varre os protocolos e marca como "Atrasado" os vencidos.
- [x] 7.2.2. Criar rota que gera relatórios diários para a gerência.

**7.3. Google Cloud Scheduler**
- [x] 7.3.1. Acessar o Cloud Scheduler no GCP.
- [x] 7.3.2. Criar os *Jobs* informando a URL das rotinas diárias e expressão CRON (ex: `0 0 * * *`).

### ⚪ Etapa 8: Pipeline de Deploy Automático (CI/CD) e Testes

**8.1. Testes Automatizados (pytest)**
- [x] 8.1.1. Configurar o `pytest` no projeto.
- [x] 8.1.2. Escrever testes unitários para o isolamento RLS e autenticação.
- [x] 8.1.3. Escrever testes para as rotas CRUD de protocolos.

**8.2. Containerização (Docker)**
- [x] 8.2.1. Criar arquivo `Dockerfile` na raiz do projeto.
- [x] 8.2.2. Testar build local da imagem (`docker build`).

**8.3. GitHub Actions e Cloud Run**
- [x] 8.3.1. Criar arquivo `.github/workflows/deploy.yml`.
- [x] 8.3.2. Configurar passos: Rodar Testes -> Build da Imagem -> Push para Artifact Registry -> Deploy no Cloud Run.
- [x] 8.3.3. Realizar o primeiro `git push` e acompanhar o deploy até ver a aplicação online.

### 🔴 Etapa 9: Hardening de Segurança e Controle de Acesso

> ⚠️ Esta etapa foi adicionada para corrigir as brechas de segurança identificadas durante a fase de homologação inicial (deploy em produção). **Todos os itens abaixo devem ser implementados antes do Go-Live.**

**9.1. Autenticação por Google OAuth (Substituir Login por E-mail/Senha)**
- [x] 9.1.1. Remover o login provisório por e-mail sem senha e habilitar obrigatoriamente o Google OAuth.
- [x] 9.1.2. Configurar as Origens Autorizadas no painel de Credenciais OAuth do GCP com a URL de produção do Cloud Run.
- [x] 9.1.3. Validar que somente e-mails do domínio `@janiopontes.com.br` podem fazer login (restrição de Workspace).
- [x] 9.1.4. Garantir que tokens JWT expirem em 8h (horário comercial) para sessões de trabalho seguras.

**9.2. Permissões do Cloud Run (IAM)**
- [x] 9.2.1. Aplicar o papel "Chamador do Cloud Run" para `allUsers` (acesso público à URL do serviço).
- [ ] 9.2.2. Revogar acesso de administrador da Service Account `jpsaas-backend` (que atualmente possui permissões excessivas).
- [ ] 9.2.3. Criar uma IAM Role customizada com permissões mínimas necessárias para a Service Account (princípio do menor privilégio).
- [ ] 9.2.4. Guardar a chave da Service Account no **Secret Manager** do GCP (remover o `credentials.json` do repositório e do container Docker).

**9.3. Segurança do Banco de Dados (Cloud SQL)**
- [ ] 9.3.1. Verificar que o Cloud SQL está configurado para aceitar conexões **apenas via Unix Socket** (Cloud SQL Connector), sem IP público exposto.
- [ ] 9.3.2. Criar um usuário PostgreSQL dedicado para a aplicação (`app_user`) com privilégios mínimos (sem permissão de `CREATE TABLE`, `DROP`, etc.).
- [ ] 9.3.3. Remover o usuário `postgres` (superusuário) do acesso remoto.
- [ ] 9.3.4. Habilitar backups automáticos no Cloud SQL com retenção de 7 dias.

**9.4. Revisão das Políticas de RLS (Row-Level Security)**
- [x] 9.4.1. Confirmar que RLS está habilitado com `FORCE ROW LEVEL SECURITY` em todas as tabelas tenant-bound.
- [x] 9.4.2. Confirmar que o bypass de RLS na rota `/login` usa `SET LOCAL` (escopo limitado à transação, não à conexão toda).
- [ ] 9.4.3. Escrever teste automatizado (pytest) que valida que um usuário do Tenant A **não consegue** ver dados do Tenant B, mesmo com SQL direto.
- [ ] 9.4.4. Verificar que o mecanismo `app.bypass_rls = 'on'` é ativado **somente** em rotas internas de sistema (scheduler, seed), nunca em rotas públicas.

**9.5. Proteção das Rotas da API**
- [ ] 9.5.1. Auditar todas as rotas FastAPI e confirmar que cada uma usa `Depends(require_login)` ou `Depends(verify_scheduler_key)`.
- [ ] 9.5.2. Remover (ou proteger com senha) a rota `/docs` (Swagger UI) em ambiente de produção.
- [ ] 9.5.3. Adicionar rate limiting nas rotas públicas (especialmente `/login`) para prevenir ataques de força bruta.
- [ ] 9.5.4. Configurar headers de segurança HTTP (CSP, X-Frame-Options, Strict-Transport-Security) via middleware no FastAPI.

**9.6. Variáveis de Ambiente e Segredos**
- [x] 9.6.1. Garantir que o arquivo `.env` está no `.gitignore` e nunca é versionado.
- [ ] 9.6.2. Migrar os segredos do `.env` (DB_PASSWORD, SECRET_KEY, GOOGLE_CLIENT_SECRET) para o **GCP Secret Manager**.
- [ ] 9.6.3. Configurar o Cloud Run para ler os segredos diretamente do Secret Manager via variáveis de ambiente (sem hardcode no código).
- [ ] 9.6.4. Rodar `SECRET_KEY` com pelo menos 64 caracteres gerados aleatoriamente (verificado ✅ — já implementado).

**9.7. GitHub Actions e Segredos do CI/CD**
- [ ] 9.7.1. Adicionar o conteúdo do `credentials.json` como Secret do GitHub (`GCP_SA_KEY`) para que o GitHub Actions possa autenticar sem o arquivo físico.
- [ ] 9.7.2. Adicionar as variáveis de banco de dados (`DB_PASSWORD`, `SECRET_KEY`) como Secrets do GitHub para injeção no deploy.
- [ ] 9.7.3. Configurar o Cloud Run no GitHub Actions para ler segredos do Secret Manager (em vez de `--set-env-vars` com valores em texto claro).
- [ ] 9.7.4. Verificar que o repositório GitHub está configurado como **privado**.

### 🔶 Etapa 10: Homologação Final e Migração de Dados

**10.1. Homologação (Staging)**
- [x] 10.1.1. Equipe acessa a URL gerada pelo Cloud Run.
- [ ] 10.1.2. Equipe testa o fluxo completo de criação de protocolos e comunicação.
- [ ] 10.1.3. Ajuste de bugs e correções visuais finais.

**10.2. Migração de Dados (Google Sheets -> PostgreSQL)**
- [ ] 10.2.1. Travar a edição das planilhas do GAS atual (modo leitura).
- [x] 10.2.2. Rodar o script Python de extração de dados (lendo a API do Sheets e gravando no PostgreSQL via SQLAlchemy).
- [x] 10.2.3. Validar a integridade dos dados migrados (125 clientes e 57 regras importados com sucesso).
- [ ] 10.2.4. Desenvolver e rodar script de extração/importação para os **Perfis**, mapeando as vinculações com Clientes e Regras.
- [ ] 10.2.5. Desenvolver e rodar script de extração/importação dos **Usuários**, garantindo a atribuição correta dos níveis ADMIN e USER.

**10.3. Rollback de Segurança**
- [ ] 10.3.1. Habilitar script de Reverse Sync: Cada novo registro no banco salva uma cópia na planilha antiga.
- [ ] 10.3.2. Manter este script rodando por 72h.

### 🚀 Etapa 11: Go-Live (Lançamento em Produção)

**11.1. Apontamento de Domínio**
- [ ] 11.1.1. Acessar gerenciador de DNS do domínio da empresa.
- [ ] 11.1.2. Criar registro CNAME/A apontando para o Cloud Run (`app.janiopontes.com.br`).
- [ ] 11.1.3. Aguardar propagação e emissão do certificado SSL (Automático pelo Google).

**11.2. Lançamento Oficial**
- [ ] 11.2.1. Comunicar à equipe e clientes a nova URL de acesso.
- [ ] 11.2.2. Iniciar a operação exclusiva no novo sistema.

**11.3. Monitoramento e Encerramento**
- [ ] 11.3.1. Acompanhar os logs no *Google Cloud Logging* intensivamente por 48h.
- [ ] 11.3.2. Fim da janela de 72h: Desligar o *Reverse Sync*.
- [ ] 11.3.3. Arquivar os scripts antigos do Google Apps Script definitivamente.
