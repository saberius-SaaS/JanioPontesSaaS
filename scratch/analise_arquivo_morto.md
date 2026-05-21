# 📊 Análise: Estratégia de Arquivo Morto — DB_PROTOCOLOS e DB_HISTORICO

## 1. Diagnóstico do Problema

O Google Apps Script possui limites rígidos de performance ao operar com planilhas grandes:
- `getDataRange().getValues()` carrega **toda a aba** na memória do servidor
- Cada chamada `getRange()` adiciona latência de rede (~100-300ms)
- O tempo de execução máximo de um script é **6 minutos** (gatilhos) ou **30 segundos** (chamadas do Portal)

As abas **DB_PROTOCOLOS** e **DB_HISTORICO** crescem indefinidamente. Quando atingem milhares de linhas, cada operação que as lê (especialmente as chamadas do Portal, que têm timeout curto) começa a degradar.

---

## 2. Mapeamento de Impacto (Todos os Pontos de Leitura)

### 2.1 DB_PROTOCOLOS — 16 referências em 8 arquivos

| Arquivo | Função | Tipo de Leitura | Risco |
|---|---|---|---|
| [DashboardService.js](file:///g:/Meu%20Drive/JanioPontesSaas/DashboardService.js#L116) | `getListaProtocolos()` | Últimos 500-3000 rows | 🟡 Médio |
| [DashboardService.js](file:///g:/Meu%20Drive/JanioPontesSaas/DashboardService.js#L205) | `getDadosProtocolosWeb()` | Chama `getListaProtocolos` 2x | 🔴 Alto |
| [WebAppRoute.js](file:///g:/Meu%20Drive/JanioPontesSaas/WebAppRoute.js#L190) | `getPrioridadesPortal()` | Cache `DATA_PROTOCOLOS` (full) | 🔴 Alto |
| [WebAppRoute.js](file:///g:/Meu%20Drive/JanioPontesSaas/WebAppRoute.js#L659) | `baixarProtocoloManual()` | `getDataRange()` full | 🟡 Médio |
| [UiHandler.js](file:///g:/Meu%20Drive/JanioPontesSaas/UiHandler.js#L332) | `getPrioridades()` | Cache `DATA_PROTOCOLOS` (full) | 🟡 Médio |
| [UiHandler.js](file:///g:/Meu%20Drive/JanioPontesSaas/UiHandler.js#L583) | `aprovarTarefaRevisao()` | `getDataRange()` full | 🟡 Médio |
| [WhatsAppService.js](file:///g:/Meu%20Drive/JanioPontesSaas/WhatsAppService.js#L54) | `_getProtocolosPendentesWpp()` | Últimos 3000 rows | 🟢 Baixo |
| [EmailService.js](file:///g:/Meu%20Drive/JanioPontesSaas/EmailService.js#L212) | `registrarInteracaoEmail()` | `getDataRange()` full | 🟡 Médio |
| [EmailService.js](file:///g:/Meu%20Drive/JanioPontesSaas/EmailService.js#L577) | `reenviarNotificacaoPorProtocolo()` | `getDataRange()` full | 🟡 Médio |
| [DriveActivityService.js](file:///g:/Meu%20Drive/JanioPontesSaas/DriveActivityService.js#L12) | `sincronizarProvasDeEntregaAPI()` | `getDataRange()` full (últimos 300 lidos) | 🟡 Médio |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L142) | `arquivarTarefasConcluidas()` | `getDataRange()` full (mapa) | 🟡 Médio |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L207) | `moverTarefaParaHistoricoImediato()` | `getDataRange()` full | 🟡 Médio |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L306) | `sincronizarHistoricoComProtocolos()` | `getDataRange()` full (mapa) | 🔴 Alto |
| [Utils.js](file:///g:/Meu%20Drive/JanioPontesSaas/Utils.js#L212) | `registrarProtocoloDB()` | `appendRow` (somente escrita) | 🟢 Nulo |

### 2.2 DB_HISTORICO — 9 referências em 6 arquivos

| Arquivo | Função | Tipo de Leitura | Risco |
|---|---|---|---|
| [DashboardService.js](file:///g:/Meu%20Drive/JanioPontesSaas/DashboardService.js#L13) | `getDashboardData()` | `getDataRange()` **full** | 🔴 Alto |
| [DashboardService.js](file:///g:/Meu%20Drive/JanioPontesSaas/DashboardService.js#L229) | `getRelatorioAuditoria()` | `getDataRange()` **full** | 🔴 Alto |
| [WebAppRoute.js](file:///g:/Meu%20Drive/JanioPontesSaas/WebAppRoute.js#L482) | `getDadosHistoricoWeb()` | Últimos 100 rows (otimizado) | 🟢 Baixo |
| [TaskCoreService.js](file:///g:/Meu%20Drive/JanioPontesSaas/TaskCoreService.js#L29) | `gerarTarefasDoMes()` | `getDataRange()` **full** | 🔴 Alto |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L141) | `arquivarTarefasConcluidas()` | Somente escrita (append) | 🟢 Nulo |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L206) | `moverTarefaParaHistoricoImediato()` | Somente escrita (append) | 🟢 Nulo |
| [MaintenanceService.js](file:///g:/Meu%20Drive/JanioPontesSaas/MaintenanceService.js#L305) | `sincronizarHistoricoComProtocolos()` | `getDataRange()` **full** | 🔴 Alto |
| [EmailService.js](file:///g:/Meu%20Drive/JanioPontesSaas/EmailService.js#L613) | `reenviarNotificacaoPorProtocolo()` | `getDataRange()` full (busca) | 🟡 Médio |

---

## 3. Critérios de Elegibilidade para Arquivo Morto

### 3.1 DB_PROTOCOLOS → DB_PROTOCOLOS_MORTO

Um protocolo é considerado **totalmente resolvido** quando:
1. **STATUS_ENVIO** (Col I) = `ENTREGUE` ou `LIDO_MANUAL`
2. **CONF_RECTO** (Col J) ≠ vazio, `---`, ou `AGUARDANDO` (ou seja, já foi lido/confirmado)
3. **Antiguidade** ≥ 90 dias (janela de segurança para reenvios e auditorias recentes)
4. **WPP_NOTIF** (Col M) já foi processado ou está vazio (sem notificação pendente)

### 3.2 DB_HISTORICO → DB_HISTORICO_MORTO

Um registro histórico é considerado **frio** quando:
1. **MES_ANO** (Col A) é anterior ao trimestre retroativo configurado (`JANELA_RETROATIVA_MESES = 3`)
2. **STATUS_ENVIO** (Col L) e **CONF_RECTO** (Col M) já estão sincronizados (não pendentes de atualização)
3. **Antiguidade** ≥ 90 dias

> [!IMPORTANT]
> A `gerarTarefasDoMes()` lê o DB_HISTORICO inteiro para verificar se uma tarefa já foi ENTREGUE (evitar duplicação). Precisamos garantir que essa verificação continue funcionando **mesmo com o arquivo morto**. Isso será resolvido buscando também no MORTO somente nessa função específica.

---

## 4. Proposta de Implementação (5 Fases)

### Fase 1 — Infraestrutura (Risco: Nulo)
- Criar as abas `DB_PROTOCOLOS_MORTO` e `DB_HISTORICO_MORTO` com o mesmo schema das originais
- Adicionar as novas constantes no `Config.js`:
  ```javascript
  ABA_PROTOCOLOS_MORTO: "DB_PROTOCOLOS_MORTO",
  ABA_HISTORICO_MORTO: "DB_HISTORICO_MORTO",
  DIAS_PARA_ARQUIVO_MORTO: 90
  ```
- **Impacto zero** no sistema em operação

### Fase 2 — Rotina de Migração (Risco: Baixo)
- Criar função `migrarParaArquivoMorto()` no `MaintenanceService.js`
- A função usa **LockService** e opera em batch (leitura/escrita em lote)
- Fluxo: Lê → Filtra elegíveis → Copia para MORTO → Remove das ativas → Flush
- Disponibilizar via menu: `⚙️ Configurações Avançadas > 📦 Migrar Arquivo Morto`
- Também pode ser agendada como trigger diário/semanal

### Fase 3 — Blindagem das Funções Críticas (Risco: Médio — **requer mais cuidado**)
- `gerarTarefasDoMes()`: Adicionar busca no `DB_HISTORICO_MORTO` para validação de duplicidade
- `sincronizarHistoricoComProtocolos()`: Operar **somente** sobre as abas ativas (dados já resolvidos no morto não precisam de sincronização)
- `getDashboardData()`: Operar somente sobre ativas (Dashboard mostra dados do mês corrente e anterior)

### Fase 4 — Toggle no Portal (Risco: Baixo)
- Adicionar um botão/toggle nas abas **Protocolos** e **Histórico** do Portal
- Estado padrão: **Desligado** (busca somente ativas = rápido)
- Quando acionado: Busca adicional nas abas MORTO e concatena resultados
- Funções impactadas:
  - `getListaProtocolos()` → aceitar parâmetro `incluirArquivoMorto`
  - `getDadosHistoricoWeb()` → aceitar parâmetro `incluirArquivoMorto`
  - `getDadosProtocolosWeb()` → propagar o toggle

### Fase 5 — Validação e Ativação
- Executar `migrarParaArquivoMorto()` pela primeira vez manualmente
- Validar contagem: Ativas + Morto = Total anterior
- Monitorar logs por 48h
- Instalar trigger automático se tudo estiver estável

---

## 5. Análise de Riscos

### 🟢 Riscos Baixos (Controláveis)
| Risco | Mitigação |
|---|---|
| Dados migrados por engano | A migração usa critérios conservadores (90 dias + confirmado). Backup antes de migrar. |
| Toggle esquecido pelo usuário | Estado padrão = OFF. O sistema sempre busca nas ativas por padrão. |
| Abas novas não existem | Criar as abas antes de qualquer código. A função verifica existência antes de operar. |

### 🟡 Riscos Médios (Requerem atenção)
| Risco | Mitigação |
|---|---|
| `gerarTarefasDoMes()` não encontrar tarefa no MORTO | Adicionar busca complementar APENAS nesta função (leitura read-only no MORTO). |
| Cache desatualizado após migração | Chamar `invalidarCacheSistema()` ao final da migração. |
| Reenvio de protocolo (`reenviarNotificacaoPorProtocolo`) não encontrar protocolo migrado | Adicionar fallback: se não achar na ativa, buscar na MORTO. |

### 🔴 Riscos Altos (Exigem teste rigoroso)
| Risco | Mitigação |
|---|---|
| `sincronizarHistoricoComProtocolos()` tentar atualizar dados que já foram migrados | A função cria um mapa por ID_TAREFA. Se o protocolo já foi para o MORTO, o mapa simplesmente não terá a entrada — **sem erro, sem efeito colateral**. ✅ |
| Perda de dados durante a migração | Usar padrão **Copy-then-Delete** com `SpreadsheetApp.flush()` entre as etapas. Se a cópia falhar, a deleção não ocorre. |

---

## 6. Estimativa de Ganho de Performance

Supondo **5.000 linhas** em DB_PROTOCOLOS e **8.000 linhas** em DB_HISTORICO, e migrando ~70% para arquivo morto:

| Operação | Antes | Depois | Ganho |
|---|---|---|---|
| `getListaProtocolos()` (Portal) | ~5.000 rows lidas | ~1.500 rows | **~70%** |
| `getDashboardData()` (Dashboard) | ~8.000 rows no histórico | ~2.400 rows | **~70%** |
| `gerarTarefasDoMes()` | ~8.000 rows scan | ~2.400 rows (+ lookup pontual no morto) | **~60%** |
| `sincronizarHistoricoComProtocolos()` | ~5.000 + ~8.000 = 13.000 rows | ~1.500 + ~2.400 = 3.900 rows | **~70%** |

> [!TIP]
> O maior ganho será sentido nas funções do **Portal** (timeout de 30s), onde a redução de volume terá impacto direto na responsividade para o usuário final.

---

## 7. Resumo da Recomendação

A implementação é **viável e segura** desde que seja feita de forma faseada. O ponto mais crítico é a **Fase 3** (blindagem das funções), que precisa ser feita com revisão linha a linha.

A proposta respeita todas as regras do sistema:
- ✅ Não altera nenhuma função que não seja explicitamente necessária
- ✅ Preserva byte a byte todo código não afetado
- ✅ Usa batch operations (Regra 5.1)
- ✅ Usa LockService na migração (Regra 5.4)
- ✅ Registra logs em DB_LOGS (Regra 5.3)
- ✅ Schema das novas abas é idêntico às originais

---

# 🛡️ Anexo: Ações de Segurança & Vulnerabilidades (Para Execução Conjunta)

Como o sistema está em operação e é baseado em Google Apps Script (GAS) que executa no contexto do proprietário ("Me"), as vulnerabilidades identificadas possuem severidade **crítica** e devem ser resolvidas durante a janela de manutenção.

## 1. Vulnerabilidades Críticas

### 1.1 Bypass de Assinatura JWT na Validação de Token (Quebra de Autenticação)
- **Localização:** `Utils.js` -> Função `validarTokenGIS(token)`
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 9.8)
- **Descrição:**
  A validação do token do Google Identity Services (GIS) possui um bloco de `fallback` que decodifica o payload Base64 e aceita o e-mail sem validar a assinatura criptográfica, permitindo forjar tokens.
- **Impacto:** Acesso de `ADMIN` total ao invasor no Portal.
- **Ação Planejada:** **Remover completamente o bloco de fallback.** Se o Google Auth API não validar o token (retornar erro ou não ser 200), o token deve ser considerado **inválido** e rejeitado.

### 1.2 Exposição de Funções Administrativas no Escopo Global (Falta de Controle de Acesso)
- **Localização:** Global (`AccessService.js`, `MaintenanceService.js`, `AIService.js`, `DashboardService.js`)
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 8.5)
- **Descrição:** Funções críticas (ex: `limparDbLogsEmLote()`, `salvarConfigIACompl()`) não terminam com `_` e são acessíveis via `google.script.run` por qualquer cliente autenticado no portal.
- **Impacto:** Leitura de dados confidenciais e alteração de regras de negócio.
- **Ação Planejada:** Renomear funções sensíveis para terminar com underline (ex: `limparVersoesAntigas_()`). Criar wrappers que validem o papel (`ADMIN`) internamente.

### 1.3 Upload Arbitrário de Arquivos e Path Traversal
- **Localização:** `UploadAndDemandService.js` -> `processarFragmentoUpload()`
- **Severidade:** 🔴 Crítica (Pontuação CVSS estimada: 9.3)
- **Descrição:** A função confia no `folderId` vindo diretamente do cliente no navegador.
- **Impacto:** O script usa permissões do proprietário, permitindo que um invasor salve arquivos em qualquer pasta do Google Drive do dono.
- **Ação Planejada:** O servidor não deve receber o `folderId` do cliente. Deve receber o `solId`, buscar no BD qual a pasta segura do cliente associada, e resolver o ID no servidor.

## 2. Vulnerabilidades de Severidade Média

### 2.1 Identificadores de Solicitações Previsíveis (ID Guessing / Brute-Force)
- **Localização:** `UploadAndDemandService.js` -> `enviarSolicitacaoDocumento()`
- **Severidade:** 🟡 Média
- **Descrição:** IDs sequenciais (ex: `SOL1715697600000`) enviados nos links.
- **Impacto:** Atacantes podem deduzir outros IDs válidos e visualizar solicitações de outros clientes.
- **Ação Planejada:** Usar um gerador de hash (MD5, etc.) ao criar solicitações para gerar um ID imprevisível (ex: `SOL_a3f9e8d2c1`).

> [!WARNING]
> Corrigir o **Bypass de JWT (1.1)** e o **Upload Arbitrário de Pastas (1.3)** deve ser a maior prioridade técnica, pois colocam diretamente a autenticidade dos dados e o acesso aos arquivos em risco. As correções podem ser validadas e testadas com segurança junto com a migração do Arquivo Morto.
