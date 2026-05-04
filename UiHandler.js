/**
🖥️ GESTOR DE INTERFACE E ROTAS v131.09
FOCO: Rastreio Seguro e Roteamento de Permissões Elevadas.
*/
function onOpen() {
  var ss = getSs();
  var userEmail = Session.getActiveUser().getEmail().toLowerCase().trim();
  var isAuthorized = false;
  
  // 1. Validar se o e-mail está na lista de usuários (DB_USUARIOS)
  var wsUsr = ss.getSheetByName("DB_USUARIOS");
  if (wsUsr) {
    var dataU = wsUsr.getDataRange().getValues();
    for (var i = 1; i < dataU.length; i++) {
      if (String(dataU[i][0]).toLowerCase().trim() === userEmail) {
        isAuthorized = true;
        break;
      }
    }
  }

  // 2. Lógica de Escudo (Shielding)
  if (!isAuthorized && userEmail !== "") {
    // USUÁRIO NÃO AUTORIZADO: Esconder tudo e mostrar apenas aviso de segurança
    garantirEExibirAvisoSeguranca(ss);
    return; // Aborta a criação do menu e exibição das abas
  }

  // 3. USUÁRIO AUTORIZADO: Garantir que as abas de trabalho estão visíveis e criar menu
  restaurarAbasTrabalho(ss);

  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 Janio Pontes SaaS')
    .addItem('🚀 ABRIR SISTEMA', 'abrirSistema')
    .addSeparator()
    .addSubMenu(ui.createMenu('🔄 Sincronismo de Provas')
      .addItem('⚡ Sincronizar Agora (Manual)', 'comandoSincronizarProvas')
      .addSeparator()
      .addItem('🟢 ATIVAR Automação (1h)', 'instalarGatilhoSincronismo')
      .addItem('🔴 DESATIVAR Automação', 'removerGatilhosSincronismo'))
    .addSeparator()
    .addItem('✨ REPARAR LAYOUT ELITE', 'padronizarLayout')
    .addItem('🛡️ CHECK-UP DE SAÚDE', 'comandoValidarSaudeSistema')
    .addItem('🔑 RENOVAR PERMISSÕES', 'forcarAutorizacao')
    .addItem('⚙️ DEFINIR PERFIS (TAGS)', 'abrirSeletorPerfis')
    .addItem('🔍 AUDITAR REGRAS', 'abrirAuditorRegras')
    .addSeparator()
    .addItem('📅 1. Gerar/Sincronizar Tarefas', 'gerarTarefasDoMes')
    .addItem('📦 2. ARQUIVAR Concluídas', 'comandoArquivarTarefas')
    .addItem('⚠️ 3. ATUALIZAR RISCO', 'comandoAtualizarRisco')
    .addItem('🔄 4. SINCRONIZAR HISTÓRICO', 'comandoSincronizarHistorico')
    .addItem('💾 5. BACKUP TOTAL', 'comandoBackupManual')
    .addSeparator()
    .addItem('📊 Dashboard Visual', 'abrirDashboardVisual')
    .addSeparator()
    .addSubMenu(ui.createMenu('⚙️ Configurações Avançadas')
      .addItem('⚡ SINCRONIZAR PASTAS', 'comandoMapearPastas')
      .addItem('⚡ LIMPAR CACHE', 'comandoLimparCache')
      .addItem('⚙️ CONFIG IA (Chave API)', 'comandoInicializarIA')
      .addItem('⚙️ CONFIG IA (Módulo Avançado)', 'abrirPainelConfigIA')
      .addSeparator()
      .addItem('⏰ ATIVAR COBRANÇA AUTO', 'instalarGatilhoCobrancaDiaria')
      .addItem('⏰ Instalar Backup Automático', 'instalarGatilhoBackup')
      .addItem('❌ Remover Gatilho de Backup', 'removerGatilhoBackup'))
    .addToUi();
}

/**
 * Esconde todas as abas e mostra apenas o aviso de segurança.
 */
function garantirEExibirAvisoSeguranca(ss) {
  var abaAviso = ss.getSheetByName("AVISO_SEGURANCA");
  if (!abaAviso) {
    abaAviso = ss.insertSheet("AVISO_SEGURANCA");
    abaAviso.getRange("A1").setValue("🛡️ PROTOCOLO DE SEGURANÇA ATIVO")
      .setFontWeight("bold").setFontSize(14).setFontColor("#e11d48");
    abaAviso.getRange("A2").setValue("Seu acesso a este arquivo de dados não está autorizado nos registros do Janio Pontes SaaS.")
      .setFontWeight("bold");
    abaAviso.getRange("A4").setValue("Por favor, utilize o Portal Web para interagir com o sistema ou contate o administrador.");
    abaAviso.setTabColor("#e11d48");
  }
  
  abaAviso.showSheet();
  ss.setActiveSheet(abaAviso);

  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName() !== "AVISO_SEGURANCA") {
      sheets[i].hideSheet();
    }
  }
}

/**
 * Reexibe todas as abas DB_ e outras necessárias após autorização.
 */
function restaurarAbasTrabalho(ss) {
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var name = sheets[i].getName();
    if (name.indexOf("DB_") === 0 || name === "LOGS") {
      sheets[i].showSheet();
    }
  }
  var abaAviso = ss.getSheetByName("AVISO_SEGURANCA");
  if (abaAviso) {
    abaAviso.hideSheet();
  }
}

function abrirSeletorPerfis() {
  var ss = getSs();
  var sheet = ss.getActiveSheet();
  if (sheet.getName() !== CONFIG_SISTEMA.ABA_CLIENTES) {
    SpreadsheetApp.getUi().alert("⚠️ Selecione a aba " + CONFIG_SISTEMA.ABA_CLIENTES);
    return;
  }
  var row = sheet.getActiveRange().getRow();
  if (row < 2) return;
  var t = HtmlService.createTemplateFromFile('SeletorPerfis');
  t.clienteIndex = row;
  SpreadsheetApp.getUi().showModalDialog(t.evaluate().setHeight(600).setWidth(800), '⚙️ ENQUADRAMENTO POR PERFIL');
}

function getDadosPerfis(rowIdx) {
  var dataCli = getSheetDataCached(CONFIG_SISTEMA.ABA_CLIENTES, CACHE_CONFIG.KEYS.CLIENTES);
  var dataReg = getSheetDataCached(CONFIG_SISTEMA.ABA_REGRAS, CACHE_CONFIG.KEYS.REGRAS);
  var clienteNome = dataCli[rowIdx-1][1];
  var regime = dataCli[rowIdx-1][6]; 
  var perfisAtuais = String(dataCli[rowIdx-1][14] || "");
  var tagsSet = new Set();
  for (var i = 1; i < dataReg.length; i++) {
    var grupos = String(dataReg[i][11] || "").split(',');
    grupos.forEach(g => {
      var limpo = g.trim().toUpperCase();
      if (limpo && limpo !== "GLOBAL" && limpo !== "TODOS") tagsSet.add(limpo);
    });
  }
  return {
    cliente: clienteNome,
    regime: regime || "NÃO DEFINIDO",
    atuais: perfisAtuais,
    disponiveis: Array.from(tagsSet).sort()
  };
}

function salvarPerfisCliente(rowIdx, perfisStr) {
  var ss = getSs();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  wsCli.getRange(rowIdx, 15).setValue(perfisStr);
  invalidarCacheSistema();
}

/**
 * Gateway Web App: Gerencia o Portal do Cliente e Rastreio Seguro.
 * Importante: Deve ser publicado para "Executar como: Me".
 */
function doGet(e) {
  try {
    var params = e.parameter || {};
    var mode = String(params.mode || "").trim();
    var solId = String(params.sol || "").trim().replace(/^["']|["']$/g, "");
    var p = String(params.p || "").trim().replace(/^["']|["']$/g, "");
    var r = String(params.r || "").trim().replace(/^["']|["']$/g, "");
    var dest = params.dest || "";

    if (mode === "client" && solId !== "") {
      registrarInteracaoEmail(p, "PORTAL_SOLICITACAO_ABERTO", r);
      var template = HtmlService.createTemplateFromFile('SolicitacaoCliente');
      template.solId = solId;
      return template.evaluate()
        .setTitle('Portal NCE')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
        .addMetaTag('viewport', 'width=device-width, initial-scale=1');
    }

    if (mode === "track" && p !== "") {
      registrarInteracaoEmail(p, dest ? "CLIQUE_BOTAO" : "EMAIL_ABERTO", r);
      if (dest) {
        var htmlRedirect = `
          <!DOCTYPE html>
          <html>
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap" rel="stylesheet">
              <style>
                body { font-family: 'Inter', sans-serif; background: #F8FAFC; color: #1C3051; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; padding: 20px;}
                .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); max-width: 400px; width: 100%; border: 1px solid #E2E8F0; }
                .logo { font-weight: 800; font-size: 14px; letter-spacing: 1px; margin-bottom: 30px; color: #1C3051; text-transform: uppercase; }
                .btn { background-color: #1C3051; color: white; padding: 18px 35px; border-radius: 10px; text-decoration: none; font-weight: 700; margin-top: 25px; display: inline-block; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; transition: 0.2s; border: none; cursor: pointer; width: 100%; }
                .btn:hover { background-color: #2A4571; transform: translateY(-2px); }
                .status-icon { font-size: 40px; margin-bottom: 20px; color: #10B981; }
              </style>
            </head>
            <body>
              <div class="card">
                <div class="logo">Janio Pontes Contabilidade</div>
                <div class="status-icon">🛡️</div>
                <h2 style="margin:0; font-size: 20px; font-weight: 800;">Acesso Autorizado</h2>
                <p style="color: #64748B; font-size: 14px; margin-top: 10px;">Sua identidade foi confirmada e o documento está pronto para visualização.</p>
                <a href="${dest}" target="_top" class="btn">Visualizar Documento</a>
              </div>
            </body>
          </html>
        `;
        return HtmlService.createHtmlOutput(htmlRedirect)
          .setTitle("Acesso Seguro NCE")
          .addMetaTag('viewport', 'width=device-width, initial-scale=1')
          .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
      }
      return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
    }

    if (mode === "repo" && (p !== "" || params.folder)) {
      var folderId = params.folder;
      if (!folderId && p) {
         // Tentar extrair ID da pasta via protocolo se não vier no link
         var ss = getSs();
         var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
         var dataP = wsProt.getDataRange().getValues();
         var clienteNome = "";
         for(var i=0; i<dataP.length; i++) {
           if(String(dataP[i][2]) === String(p)) { clienteNome = dataP[i][1]; break; }
         }
         if (clienteNome) {
            folderId = buscarIdPastaCliente(clienteNome);
         }
      }

      if (folderId) {
        registrarInteracaoEmail(p, "REPOSITORIO_ABERTO", r);
        var template = HtmlService.createTemplateFromFile('RepositorioCliente');
        template.arquivos = listarArquivosRepositorioInterno(folderId);
        template.protocoloDestaque = p;
        return template.evaluate()
          .setTitle('Repositório Digital | JP NCE')
          .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
          .addMetaTag('viewport', 'width=device-width, initial-scale=1');
      }
    }

    // Caso base: Se nenhum modo especial for detectado, carrega o Portal principal
    return renderPage('Portal', 'Gerenciador de Tarefas - Janio Pontes');
  } catch (err) { 
    return HtmlService.createHtmlOutput("Erro de conexão: " + err.message); 
  }
}

/**
 * Recepção de POST via Web App.
 * 1. Processa Uploads (JSON payload).
 * 2. Processa Retorno de Login GIS (Form payload via Redirect Mode).
 */
function doPost(e) {
  try {
    // ⚡ CENÁRIO A: Retorno de Autenticação GIS (Modo Redirecionamento)
    // O Google envia um POST com Content-Type: application/x-www-form-urlencoded contendo 'credential'
    if (e.parameter && e.parameter.credential) {
      var token = e.parameter.credential;
      return renderPage('Portal', 'Gerenciador de Tarefas - Janio Pontes', token);
    }

    // ⚡ CENÁRIO B: Chamadas de API do Portal (Upload, etc)
    var payload = JSON.parse(e.postData.contents);
    var token = payload.token || "";
    
    if (!token) registrarLogSistema("DOPONT_TOKEN_EMPTY", "Payload recebido sem token.");
    
    var userEmail = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    
    if (!userEmail) {
       var reason = !token ? "Token Ausente" : "Token Inválido/Expirado";
       var logMsg = "Identidade não confirmada (" + reason + "). Token len: " + (token ? token.length : 0);
       registrarLogSistema("ACCESS_DENIED", logMsg);
       throw new Error("Acesso Negado: " + reason + ". Por favor, recarregue a página ou faça login novamente.");
    }
    
    // ⚡ EXTRAÇÃO DE NÍVEL DE USUÁRIO PARA WORKFLOW
    var userLevel = "USER";
    var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    for (var u = 1; u < dataU.length; u++) {
        if (String(dataU[u][0]).toLowerCase().trim() === userEmail.toLowerCase().trim()) { 
            userLevel = String(dataU[u][2]).toUpperCase().trim(); 
            break; 
        }
    }
    
    if (payload.action === "uploadBatch") {
      var resultado = processarUploadBatchInterno(payload.arquivos, payload.taskId, payload.clienteNome, payload.mensagem, !!payload.forcar, userLevel);
      return ContentService.createTextOutput(JSON.stringify(resultado))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    if (payload.action === "aprovarTarefa") {
      var resultado = aprovarTarefaRevisao(payload.taskId, userLevel);
      return ContentService.createTextOutput(JSON.stringify(resultado))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    return ContentService.createTextOutput(JSON.stringify({ success: false, message: "Ação não reconhecida" }))
        .setMimeType(ContentService.MimeType.JSON);
        
  } catch (err) {
    registrarLogSistema("DOPOST_ERROR", err.message);
    return ContentService.createTextOutput(JSON.stringify({ success: false, error: err.message }))
        .setMimeType(ContentService.MimeType.JSON);
  }
}

function getPrioridades() {
  try {
    var userEmail = Session.getActiveUser().getEmail().toLowerCase().trim();
    var cachedResult = getPrioridadesCached(userEmail);
    if (cachedResult) return cachedResult;
    var dataU = getSheetDataCached(CONFIG_SISTEMA.ABA_USUARIOS, CACHE_CONFIG.KEYS.USUARIOS);
    var userLevel = "USER";
    for (var i = 1; i < dataU.length; i++) {
      if (String(dataU[i][0]).toLowerCase().trim() === userEmail) { userLevel = String(dataU[i][2]).toUpperCase().trim(); break; }
    }
    var wsTasks = getSs().getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    if (!wsTasks) return [];
    
    // Mapa de email → nome para exibição do responsável
    var mapNomes = {};
    for (var u = 1; u < dataU.length; u++) {
       var emailKey = String(dataU[u][0]).toLowerCase().trim();
       var nomeVal = String(dataU[u][1]).trim();
       if (emailKey) mapNomes[emailKey] = nomeVal;
    }
    
    var dataProt = getSheetDataCached(CONFIG_SISTEMA.ABA_PROTOCOLOS, "DATA_PROTOCOLOS") || [];
    var mapDocLinks = {};
    for (var p = 1; p < dataProt.length; p++) {
       if (dataProt[p][7] && String(dataProt[p][7]).indexOf("http") > -1) {
          mapDocLinks[String(dataProt[p][3])] = String(dataProt[p][7]); 
       }
    }
    
    var dataT = wsTasks.getDataRange().getValues();
    var tasks = [];
    for (var j = 1; j < dataT.length; j++) {
      var statusObj = String(dataT[j][5] || "").toUpperCase().trim();
      if (statusObj !== getSafeStatus("PENDENTE") && statusObj !== getSafeStatus("REVISAO")) continue;
      var resp = String(dataT[j][8]);
      if (userLevel === "ADMIN" || isUserResponsible(resp, userEmail)) {
        var rawVcto = dataT[j][3];
        var dateObj = (rawVcto instanceof Date) ? rawVcto : new Date(rawVcto);
        var mesAnoRaw = dataT[j][0];
        var mesAnoStr = (mesAnoRaw instanceof Date) ? Utilities.formatDate(mesAnoRaw, "GMT-3", "MM/yyyy") : String(mesAnoRaw);
        tasks.push({ 
          id: dataT[j][9], 
          cliente: String(dataT[j][1]), 
          obrigacao: String(dataT[j][2]), 
          vencimentoSort: dateObj.getTime(), 
          vencimentoStr: Utilities.formatDate(dateObj, "GMT-3", "dd/MM/yyyy"), 
          mesAno: mesAnoStr, 
          depto: dataT[j][4], 
          status: String(dataT[j][5]).toUpperCase().trim(), 
          docLinks: mapDocLinks[String(dataT[j][9])] || "", 
          acao: String(dataT[j][7]).toUpperCase().trim(), 
          nivel: dataT[j][10] || "1",
          responsavel: resp.split(',').map(function(e) { 
             var ek = e.trim().toLowerCase();
             return mapNomes[ek] || ek;
          }).join(', ')
        });
      }
    }
    tasks.sort(function(a, b) {
      if (a.status !== b.status) return (a.status === "PENDENTE") ? -1 : 1;
      if (a.vencimentoSort !== b.vencimentoSort) return a.vencimentoSort - b.vencimentoSort;
      return parseInt(b.nivel || 0) - parseInt(a.nivel || 0);
    });
    var finalResult = tasks.slice(0, 7);
    setPrioridadesCache(userEmail, finalResult);
    return finalResult;
  } catch (e) { return []; }
}

function abrirSistema() { 
  var html = HtmlService.createTemplateFromFile('Painel').evaluate().setTitle('Janio Pontes NCE').setWidth(900); 
  SpreadsheetApp.getUi().showSidebar(html); 
}

function getListaClientes() { var data = getSheetDataCached(CONFIG_SISTEMA.ABA_CLIENTES, CACHE_CONFIG.KEYS.CLIENTES); return data.slice(1).map(r => r[1]).filter(n => n !== "").sort(); }
function getTiposTarefaRegras() { var data = getSheetDataCached(CONFIG_SISTEMA.ABA_REGRAS, CACHE_CONFIG.KEYS.REGRAS); return data.slice(1).map(r => String(r[7]).trim()).filter((v, i, a) => v !== "" && a.indexOf(v) === i).sort(); }

/**
 * ⚡ CONSOLIDATED PAYLOAD - PERFORMANCE BOOSTER
 * Junta múltiplas requisições em 1 única chamada de rede para inicializar o painel sub-segundos.
 */
function getPayloadInicialPainel() {
  return {
    clientes: getListaClientes(),
    tiposDemanda: getTiposTarefaRegras(),
    prioridadesUser: getPrioridades()
  };
}

function forcarAutorizacao() { 
  try { 
    var resultado = renovarTodosEscopos();
    SpreadsheetApp.getUi().alert(resultado); 
  } catch (e) {
    SpreadsheetApp.getUi().alert("⚠️ ERRO: " + e.message + "\n\nTente executar a função 'renovarTodosEscopos' diretamente pelo Editor de Scripts (Extensões → Apps Script).");
  }
  return "🛡️ Processo de autorização acionado."; 
}
function comandoSincronizarProvas() { sincronizarProvasDeEntregaAPI(); }
function comandoSincronizarHistorico() { 
  var count = sincronizarHistoricoComProtocolos(); 
  return "Sincronismo de histórico concluído: " + count + " atualizações.";
}
function comandoArquivarTarefas() { 
  var count = arquivarTarefasConcluidas(); 
  return "Arquivamento concluído: " + count + " tarefas movidas.";
}
function comandoAtualizarRisco() { 
  var count = atualizarRelatorioRisco(); 
  return "Relatório de risco atualizado: " + count + " itens identificados.";
}
function comandoLimparCache() { 
  invalidarCacheSistema(); 
  try { SpreadsheetApp.getUi().alert("⚡ Cache invalidado."); } catch (e) {}
  return "⚡ Cache invalidado com sucesso.";
}
function comandoMapearPastas() { mapearPastasClientesAutomatico(); }
function instalarGatilhoSincronismo() { removerGatilhosSincronismo(); ScriptApp.newTrigger('sincronizarProvasDeEntregaAPI').timeBased().everyHours(1).create(); SpreadsheetApp.getUi().alert("✅ Automação Ativa."); }
function removerGatilhosSincronismo() { var triggers = ScriptApp.getProjectTriggers(); for (var i = 0; i < triggers.length; i++) { if (triggers[i].getHandlerFunction() === 'sincronizarProvasDeEntregaAPI') ScriptApp.deleteTrigger(triggers[i]); } }
function abrirDashboardVisual() { SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutputFromFile('Dashboard').setWidth(1000).setHeight(750), 'DASHBOARD'); }
function comandoBackupManual() { 
  var res = executarBackupTotal(); 
  if (res) {
    try { SpreadsheetApp.getUi().alert("✅ " + res); } catch (e) {}
  }
  return res || "Falha ao executar backup.";
}
function instalarGatilhoBackup() { removerGatilhoBackup(); ScriptApp.newTrigger('executarBackupTotal').timeBased().everyDays(1).atHour(23).create(); SpreadsheetApp.getUi().alert("✅ Backup Diário Agendado."); }
function removerGatilhoBackup() { var triggers = ScriptApp.getProjectTriggers(); for (var i = 0; i < triggers.length; i++) { if (triggers[i].getHandlerFunction() === 'executarBackupTotal') ScriptApp.deleteTrigger(triggers[i]); } }
function abrirAuditorRegras() {
  var ss = getSs();
  var sheet = ss.getActiveSheet();
  if (sheet.getName() !== CONFIG_SISTEMA.ABA_CLIENTES) return;
  var row = sheet.getActiveRange().getRow();
  if (row < 2) return;
  var t = HtmlService.createTemplateFromFile('AuditorRegras');
  t.clienteIndex = row;
  SpreadsheetApp.getUi().showModalDialog(t.evaluate().setHeight(650).setWidth(900), '🔍 AUDITORIA');
}

/**
 * Lógica de Listagem para o Repositório Digital
 */
function listarArquivosRepositorioInterno(folderId) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    var files = folder.getFiles();
    var list = [];
    while (files.hasNext()) {
      var f = files.next();
      if (f.isTrashed()) continue;
      list.push({
        name: f.getName(),
        url: f.getUrl(),
        date: Utilities.formatDate(f.getLastUpdated(), "GMT-3", "dd/MM/yyyy HH:mm"),
        size: formatBytes(f.getSize())
      });
    }
    // Ordenar por data (mais recentes primeiro)
    list.sort((a,b) => {
      var d1 = a.date.split(' ')[0].split('/').reverse().join('') + a.date.split(' ')[1];
      var d2 = b.date.split(' ')[0].split('/').reverse().join('') + b.date.split(' ')[1];
      return d2.localeCompare(d1);
    });
    return list;
  } catch(e) { return []; }
}

function buscarIdPastaCliente(nome) {
  var ss = getSs();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  var data = wsCli.getDataRange().getValues();
  for(var i=1; i<data.length; i++) {
    if(String(data[i][1]).trim().toUpperCase() === String(nome).trim().toUpperCase()) {
      var url = String(data[i][12]);
      if (url.indexOf("id=") > -1) return url.split("id=")[1];
      if (url.indexOf("folders/") > -1) return url.split("folders/")[1].split("?")[0];
    }
  }
  return null;
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
/**
 * Comando para inicializar a aba de configuração da IA
 */
function comandoInicializarIA() {
  var ui = SpreadsheetApp.getUi();
  try {
    var res = garantirConfigIA();
    var msg = res.criada ? "✅ Aba DB_CONFIG_IA criada com sucesso! " : "ℹ️ A aba DB_CONFIG_IA já existe. ";
    
    var prompt = ui.prompt("🔐 CONFIGURAÇÃO DE SEGURANÇA - GEMINI", 
                           msg + "\n\nPara sua segurança, a API Key não fica visível na planilha.\n\n" +
                           "Por favor, insira sua API Key do Gemini abaixo:", 
                           ui.ButtonSet.OK_CANCEL);
    
    if (prompt.getSelectedButton() == ui.Button.OK) {
      var key = prompt.getResponseText().trim();
      if (key) {
        PropertiesService.getScriptProperties().setProperty("GEMINI_API_KEY", key);
        ui.alert("✅ API Key salva com segurança nos Script Properties!");
      } else {
        ui.alert("⚠️ Chave vazia. A configuração anterior foi mantida (se houver).");
      }
    }
  } catch (e) {
    ui.alert("❌ Erro ao inicializar configuração: " + e.message);
  }
}

/**
 * Abre o novo painel de configurações visuais da IA (Auditoria e Relatórios)
 */
function abrirPainelConfigIA() {
  var html = HtmlService.createHtmlOutputFromFile('AuditConfig')
      .setTitle('Gestor de Auditoria IA (NCE)')
      .setWidth(800)
      .setHeight(650);
  SpreadsheetApp.getUi().showModalDialog(html, '⚙️ PAINEL VIP DE AUDITORIA IA');
}

/**
 * Aprova uma tarefa que está em REVISAO, movendo-a para ENTREGUE.
 * Exclusivo para perfis ADMIN / MASTER.
 */
function aprovarTarefaRevisao(taskId, userLevel) {
  if (["ADMIN", "MASTER", "CONSULTOR"].indexOf(userLevel) === -1) {
    return { success: false, message: "Acesso Negado: Nível insuficiente para aprovação." };
  }
  
  var ss = getSs();
  var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var dataT = wsTarefas.getDataRange().getValues();
  
  for (var i = 1; i < dataT.length; i++) {
    if (String(dataT[i][9]) === String(taskId)) { // Coluna J: ID_CONTROLE
       var statusAtual = String(dataT[i][5]).toUpperCase().trim();
       if (statusAtual !== CONFIG_SISTEMA.STATUS.REVISAO) {
         return { success: false, message: "Esta tarefa não está em status de " + CONFIG_SISTEMA.STATUS.REVISAO + "." };
       }
              // 1. Coleta dados para notificação final (vindos da tarefa e do protocolo gerado anteriormente)
        var clienteNome = dataT[i][1];
        var obrig = dataT[i][2];
        var protocolo = dataT[i][6];
        var mesAno = dataT[i][0] instanceof Date ? Utilities.formatDate(dataT[i][0], "GMT-3", "MM/yyyy") : String(dataT[i][0]);
        var vctoLegal = dataT[i][11] instanceof Date ? Utilities.formatDate(dataT[i][11], "GMT-3", "dd/MM/yyyy") : (dataT[i][11] || "---");
        
        // 2. Busca e-mail do cliente e URL da pasta
        var emailCli = "";
        var folderUrl = "";
        var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
        var dataC = wsCli.getDataRange().getValues();
        for (var c = 1; c < dataC.length; c++) {
           if (norm(dataC[c][1]) === norm(clienteNome)) {
              emailCli = dataC[c][4];
              folderUrl = dataC[c][12];
              break;
           }
        }

        // 3. Busca links dos arquivos no protocolo
        var linksParaEmail = [];
        var protRowIdx = -1;
        var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
        var dataP = wsProt.getDataRange().getValues();
        for (var p = dataP.length - 1; p >= 1; p--) {
           if (String(dataP[p][2]) === String(protocolo)) {
              var linksRaw = String(dataP[p][7] || ""); // Coluna H: Arquivos/Links (Index 7)
              if (linksRaw.indexOf("http") === 0 || linksRaw.indexOf("COMUNICADO:") === -1) {
                 var urls = linksRaw.split(" | ");
                 urls.forEach(u => {
                    if (u.trim()) linksParaEmail.push({ url: u.trim(), name: "Documento Enviado" });
                 });
              }
              protRowIdx = p + 1;
              break;
           }
        }

        // 4. Move para ENTREGUE na planilha
        wsTarefas.getRange(i + 1, 6).setValue(CONFIG_SISTEMA.STATUS.ENTREGUE);
        
        // 5. Aciona o workflow de fase seguinte
        acionarWorkflowFaseSeguinte(taskId, i + 1);

        // 5b. Transfere imediatamente para DB_HISTORICO
        moverTarefaParaHistoricoImediato(i + 1);
        
        // 6. Envia as notificações finais baseadas no tipo de ação
        var acaoTarefa = dataT[i][7];
        try {
           if (!emailCli || emailCli.indexOf("@") === -1) {
              registrarLogSistema("APROVA_EMAIL_SKIP", "Email do cliente não localizado para " + clienteNome);
           } else {
              if (norm(acaoTarefa).indexOf(CONFIG_SISTEMA.ACOES.COMUNICAR) > -1) {
                 // Recupera a mensagem do protocolo se for COMUNICAR
                 var msgComunicado = "";
                 if (protRowIdx !== -1) {
                    msgComunicado = String(dataP[protRowIdx-1][7]).replace("COMUNICADO: ", ""); // Coluna H: Index 7
                 }
                 enviarComunicadoCliente(clienteNome, emailCli, obrig, protocolo, msgComunicado);
              } else if (norm(acaoTarefa) !== CONFIG_SISTEMA.ACOES.ARQUIVAR) {
                 notificarEntregaClienteRefatorada(clienteNome, obrig, protocolo, emailCli, linksParaEmail, folderUrl, protRowIdx, false, mesAno, vctoLegal);
              }
           }
        } catch(eNotif) {
           registrarLogSistema("APROVA_NOTIF_ERR", "Falha ao notificar após aprovação: " + eNotif.message);
        }

        registrarLogSistema("WORKFLOW_APROVACAO", "Tarefa " + taskId + " aprovada por Admin. Ciclo completo.");
        invalidarCacheSistema();
        
        return { success: true, message: "Tarefa aprovada e cliente notificado com sucesso." };
     }
  }
  
  return { success: false, message: "Tarefa não localizada na base de dados." };
}
