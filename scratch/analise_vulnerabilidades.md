# 🛡️ Relatório de Análise de Segurança & Vulnerabilidades

Realizei um pente-fino de segurança (Security Audit) na estrutura do código do sistema. Como o sistema está em operação e é baseado em Google Apps Script (GAS) que executa no contexto do proprietário ("Me"), as vulnerabilidades identificadas possuem severidade **crítica**.

Aqui estão as vulnerabilidades encontradas, organizadas por severidade, com suas respectivas análises de código e recomendações de mitigação.

---

## 1. Vulnerabilidades Críticas

### 1.1 Bypass de Assinatura JWT na Validação de Token (Quebra de Autenticação)
- **Localização:** `Utils.js` -> Função `validarTokenGIS(token)` ([Utils.js:166-179](file:///g:/Meu%20Drive/JanioPontesSaas/Utils.js#L166-L179))
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 9.8)
- **Descrição:**
  A validação do token do Google Identity Services (GIS) é feita chamando a API do Google. No entanto, se essa requisição não retornar `200` (porque o token é falso, mal formado ou gerado pelo próprio atacante), o código entra em um bloco de `fallback`.
  
  O fallback decodifica a segunda parte do JWT (o payload Base64) e simplesmente aceita o e-mail que estiver escrito nela, **sem validar a assinatura criptográfica**.
  
  ```javascript
  // Código vulnerável atual:
  try {
    var payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    var decoded = Utilities.newBlob(Utilities.base64Decode(payloadB64)).getDataAsString();
    var localPayload = JSON.parse(decoded);
    if (localPayload && localPayload.email && (localPayload.email_verified === true || localPayload.email_verified === "true")) {
       var emailFallback = String(localPayload.email).toLowerCase().trim();
       // ... grava no cache e retorna o email!
  ```
- **Impacto:**
  Qualquer pessoa com conhecimentos básicos de desenvolvimento pode gerar um JWT autoassinado/falso contendo o e-mail de um administrador (ex: seu e-mail) e enviar nas requisições. O sistema aceitará o e-mail do payload sem validação, dando acesso de `ADMIN` total ao invasor no Portal.
- **Recomendação:**
  **Remover completamente o bloco de fallback.** Se o Google Auth API não validar o token (retornar erro ou não ser 200), o token deve ser considerado **inválido** e rejeitado. O único fallback aceitável para sessões expiradas é forçar o usuário a fazer o login novamente através do Google Sign-In.

---

### 1.2 Exposição de Funções Administrativas no Escopo Global (Falta de Controle de Acesso)
- **Localização:** Global (`AccessService.js`, `MaintenanceService.js`, `AIService.js`, `DashboardService.js`)
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 8.5)
- **Descrição:**
  No Google Apps Script, qualquer função global exposta em arquivos `.gs` que não termine com underline `_` é acessível do cliente através da API `google.script.run`.
  
  Funções críticas de administração como:
  - `getRelatorioEquipe()` (Relatório de atividade da equipe)
  - `getRelatorioEquipeMensal()`
  - `limparDbLogsEmLote()` (Limpeza de logs)
  - `limparVersoesAntigas()` (Exclusão de deploys do script)
  - `salvarConfigIACompl()` (Modificação de prompts de IA)
  - `obterConfigIACompl()` (Leitura de prompts e chaves)
  
  Estão declaradas globalmente e **não validam a identidade/papel** do usuário internamente.
- **Impacto:**
  Mesmo que a interface do Portal do Cliente oculte os botões de administração de usuários comuns, qualquer usuário com acesso ao portal (inclusive clientes externos ao enviar um documento) pode abrir o console do desenvolvedor (F12) e executar:
  ```javascript
  google.script.run.withSuccessHandler(console.log).getRelatorioEquipe();
  google.script.run.salvarConfigIACompl({prop: "PROMPTS", pa: "Novo prompt malicioso", pr: "...", qt: "..."});
  ```
  Isso permite a leitura de dados confidenciais e alteração de regras do negócio por qualquer usuário.
- **Recomendação:**
  1. Renomear todas as funções internas/sensíveis para terminar com underline (ex: `limparVersoesAntigas_()`), o que impede que o Google Apps Script as exponha ao `google.script.run`.
  2. Para as funções que precisam ser chamadas pelo front-end administrativo (ex: carregar relatórios), **exigir a passagem do token do usuário e validar o papel `ADMIN`** internamente na função antes de ler ou escrever qualquer dado.
     ```javascript
     function getRelatorioEquipeExposto(token) {
       var email = validarTokenGIS(token);
       if (!email || obterUserLevel(email) !== "ADMIN") {
         throw new Error("Acesso não autorizado.");
       }
       return getRelatorioEquipe_();
     }
     ```

---

### 1.3 Upload Arbitrário de Arquivos e Path Traversal
- **Localização:** `UploadAndDemandService.js` -> `processarFragmentoUpload()` ([UploadAndDemandService.js:527](file:///g:/Meu%20Drive/JanioPontesSaas/UploadAndDemandService.js#L527))
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 9.3)
- **Descrição:**
  A função de upload fragmentado aceita um parâmetro `folderId` vindo diretamente do cliente no navegador:
  ```javascript
  function processarFragmentoUpload(folderId, fileName, fileType, chunk, currentChunk, totalChunks, solId) {
    // ...
    var folder = DriveApp.getFolderById(folderId); // ID é confiado cego do cliente!
    var blob = Utilities.newBlob(Utilities.base64Decode(chunk), fileType, fileName + ".part" + currentChunk);
    var partFile = folder.createFile(blob);
  ```
- **Impacto:**
  Como a aplicação roda com as permissões da sua conta do Google Drive ("Executar como: Me"), o script tem acesso a **todas** as pastas do seu Google Drive corporativo e pessoal. Um invasor pode injetar qualquer ID de pasta do Google Drive nas chamadas de console e usar sua cota e permissões para salvar arquivos arbitrários em qualquer diretório de sua propriedade.
- **Recomendação:**
  **Não receber o `folderId` do cliente.** O servidor deve:
  1. Receber apenas o `solId`.
  2. Buscar no banco de dados (`DB_SOLICITACOES` / `DB_CLIENTES`) qual é a pasta segura de destino daquele cliente específico associada àquele `solId`.
  3. Resolver o ID da pasta internamente no servidor e criar o arquivo de forma segura.

---

## 2. Vulnerabilidades de Severidade Média

### 2.1 Identificadores de Solicitações Previsíveis (ID Guessing / Brute-Force)
- **Localização:** `UploadAndDemandService.js` -> `enviarSolicitacaoDocumento()` ([UploadAndDemandService.js:443](file:///g:/Meu%20Drive/JanioPontesSaas/UploadAndDemandService.js#L443))
- **Severidade:** 🟡 Média
- **Descrição:**
  As solicitações enviadas para clientes utilizam um ID sequencial baseado em timestamp:
  ```javascript
  var solId = "SOL" + new Date().getTime(); // Exemplo: SOL1715697600000
  ```
  Esses IDs são enviados por links de e-mail/WhatsApp no formato `?mode=client&sol=SOL1715697600000`.
- **Impacto:**
  Por serem puramente numéricos e sequenciais (milissegundos), é muito simples para um atacante deduzir outros IDs válidos de solicitações incrementando ou decrementando o valor. Como a rota de visualização de solicitação não possui autenticação (qualquer um com o link visualiza o nome da empresa e o que foi pedido), um atacante poderia mapear as pendências de outros clientes.
- **Recomendação:**
  Usar um gerador de hash pseudo-aleatório/criptográfico curto ao criar solicitações para tornar o ID imprevisível. Exemplo:
  ```javascript
  var hashUnico = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, new Date().getTime() + Math.random().toString())
                    .map(b => (b < 0 ? b + 256 : b).toString(16).padStart(2, '0')).join('').substring(0, 10);
  var solId = "SOL_" + hashUnico; // Exemplo: SOL_a3f9e8d2c1
  ```

---

## 3. Resumo & Próximos Passos recomendados

> [!WARNING]
> Corrigir o **Bypass de JWT (1.1)** e o **Upload Arbitrário de Pastas (1.3)** deve ser sua maior prioridade de segurança técnica, pois colocam diretamente a autenticidade dos dados e o acesso aos arquivos do seu Google Drive em risco.

O planejamento de correção dessas vulnerabilidades pode ser integrado em fases de manutenção preventiva, idealmente junto à implementação da rotina de **Arquivo Morto**, pois ambos exigem revisão do arquivo de configuração e das rotinas do portal.
