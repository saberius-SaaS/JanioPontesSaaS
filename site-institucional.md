# Plan: Site Institucional & Integração com o Portal

## Meta

Produzir um site institucional moderno, objetivo e de alta elegância visual para a **Jânio Pontes Contabilidade** diretamente integrado ao sistema existente, usando a página inicial pública `/` como vitrine e ponto de acesso unificado.

---

## 🎨 Identidade Visual & Design System

Para garantir um visual moderno, limpo e premium (sem "enchimento de linguiça"), usaremos:
- **Cores**: 
  - Primária: `#1C3051` (Azul escuro corporativo / Navy)
  - Secundária/Acentos: Indigo/Violeta suave (para realçar CTAs) e tons de ardósia (`slate-900`/`slate-50`)
- **Tipografia**: Outfit ou Inter (via Google Fonts) para um visual limpo e contemporâneo.
- **Efeitos**: Glassmorphism sutil, bordas arredondadas generosas, gradientes suaves e micro-transições nos botões.

---

## Estrutura da Página Inicial (Objetiva e Moderna)

1. **Header (Navegação)**:
   - Logo JP Contabilidade
   - Menu simples de scroll âncora: *Serviços*, *Sobre Nós*, *Contato*
   - Botão em destaque (CTA principal): **Área do Cliente** (redireciona para `/portal/login`)

2. **Hero Section (Principal)**:
   - Título impactante: *"Contabilidade Estratégica para Impulsionar seu Negócio"*
   - Subtítulo curto e forte focando em inteligência fiscal e apoio a tomadas de decisão.
   - Botão duplo: **Falar com um Especialista** (WhatsApp) e **Acessar Portal do Cliente**

3. **Pilares de Serviços (Sem enrolação)**:
   - Grid com 4 cards limpos e elegantes (ícones minimalistas + descrição direta):
     - **Assessoria Fiscal e Tributária**
     - **Gestão Contábil Estratégica**
     - **Departamento Pessoal e Trabalhista**
     - **Legalização e Societário**

4. **Sobre Nós (NCE - Núcleo de Consultoria Estratégica)**:
   - Descrição em 2 parágrafos objetivos sobre a dedicação em oferecer soluções eficientes e tecnologia de ponta para os clientes.

5. **Formulário de Contato Direto & WhatsApp**:
   - Um botão flutuante/seção para WhatsApp direto.
   - Um formulário de contato simplificado (Nome, E-mail, Telefone, Mensagem).

6. **Footer**:
   - Informações institucionais (CNPJ, Endereço, Direitos Reservados).
   - Link discreto: **Acesso Equipe** (redireciona para `/login` - Google OAuth).

---

## 🛠️ Arquivos Afetados & Novas Rotas

| Arquivo | Tipo de Alteração | Descrição |
|---|---|---|
| `app/routers/institucional.py` | Novo Arquivo | Roteador para servir a home e processar contatos |
| `app/templates/institucional/home.html` | Novo Arquivo | Template principal do site público com design premium |
| `app/main.py` | Modificação | Registrar o novo router e alterar a rota `/` (redireciona se logado, serve o site público se deslogado) |

---

## Tarefas de Execução

### Task 1: Template do Site Institucional
**Arquivo:** `app/templates/institucional/home.html`
- Criar o arquivo HTML estendendo uma base simples ou autônoma.
- Utilizar Tailwind CSS e fontes do Google para visual moderno.
- Incluir o formulário de contato, cards de serviços, botão de WhatsApp e os CTAs da Área do Cliente e Acesso Equipe.

### Task 2: Novo Roteador Público
**Arquivo:** `app/routers/institucional.py`
- Criar a rota `GET /` que renderiza o template `institucional/home.html` caso o usuário não esteja logado.
- Adicionar uma rota `POST /contato` para coletar mensagens de clientes interessados (podendo disparar e-mail ou registrar log).

### Task 3: Modificação da Rota Principal no Main
**Arquivo:** [main.py](file:///g:/Meu%20Drive/JanioPontesSaas/app/main.py)
- Importar e registrar `app.routers.institucional`.
- Atualizar a rota `@app.get("/")` para verificar se existe usuário logado através do cookie de sessão:
  - **Usuário logado**: renderiza a tela atual do sistema (painel interno com tarefas, etc.).
  - **Usuário deslogado**: exibe o site institucional público.

### Task 4: Integração de CTAs de Login
- Botão "Área do Cliente" direciona para `/portal/login`.
- Botão "Acesso Equipe" direciona para `/login` (Google SSO).

---

## Verificação e Testes

- [ ] Acessar `/` deslogado exibe o novo site institucional público.
- [ ] Acessar `/` logado (Equipe) exibe o painel de tarefas interno normalmente.
- [ ] Clicar em "Área do Cliente" abre a nova tela de login do portal.
- [ ] O design é 100% responsivo e com excelente visualização mobile.
