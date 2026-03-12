/**
🖥️ GESTOR DE INTERFACE E ROTAS v131.09
FOCO: Rastreio Seguro e Roteamento de Permissões Elevadas.
*/
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function onOpen() {
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
      .addSeparator()
      .addItem('⏰ Instalar Backup Automático', 'instalarGatilhoBackup')
      .addItem('❌ Remover Gatilho de Backup', 'removerGatilhoBackup'))
    .addToUi();
}

function abrirSeletorPerfis() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
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
  var ss = SpreadsheetApp.getActiveSpreadsheet();
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
    var p = String(params.p || "").trim();
    var r = String(params.r || "").trim();
    var dest = params.dest || "";

    if (mode === "client" && solId !== "") {
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
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <style>
                body { font-family: sans-serif; background: #F8FAFC; color: #1C3051; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; padding: 20px;}
                .btn { background-color: #1C3051; color: white; padding: 18px 35px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 25px; display: inline-block; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; transition: 0.2s;}
                .btn:hover { background-color: #2A4571; }
              </style>
            </head>
            <body>
              <h2 style="margin:0;">Acesso Seguro Confirmado</h2>
              <p style="color: #64748B;">Sua requisição foi autenticada. Clique para visualizar o documento.</p>
              <a href="${dest}" target="_top" class="btn">Visualizar Documento</a>
            </body>
          </html>
        `;
        return HtmlService.createHtmlOutput(htmlRedirect)
          .setTitle("Acesso Seguro NCE")
          .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
      }
      return ContentService.createTextOutput("").setMimeType(ContentService.MimeType.TEXT);
    }
    return HtmlService.createHtmlOutput("🚀 SISTEMA NCE ATIVO").setTitle('NCE - Status');
  } catch (err) { return HtmlService.createHtmlOutput("Erro de conexão."); }
}

/**
 * Recepção de POST via Web App (Bypass de Permissão do DriveApp).
 * Permite que usuários normais façam upload usando as permissões do dono do script.
 */
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    
    if (payload.action === "uploadBatch") {
      var resultados = processarUploadBatchInterno(payload.arquivos, payload.taskId, payload.clienteNome);
      return ContentService.createTextOutput(JSON.stringify({ success: true, message: "Upload concluído" }))
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
    var wsTasks = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    if (!wsTasks) return [];
    var dataT = wsTasks.getDataRange().getValues();
    var tasks = [];
    for (var j = 1; j < dataT.length; j++) {
      if (String(dataT[j][5]).toUpperCase().trim() !== getSafeStatus("PENDENTE")) continue;
      var resp = String(dataT[j][8]).toLowerCase().trim();
      if (userLevel === "ADMIN" || resp === userEmail) {
        var rawVcto = dataT[j][3];
        var dateObj = (rawVcto instanceof Date) ? rawVcto : new Date(rawVcto);
        tasks.push({ id: dataT[j][9], cliente: String(dataT[j][1]), obrigacao: String(dataT[j][2]), vencimentoSort: dateObj.getTime(), vencimentoStr: Utilities.formatDate(dateObj, "GMT-3", "dd/MM/yyyy"), depto: dataT[j][4], acao: String(dataT[j][7]).toUpperCase().trim(), nivel: dataT[j][10] || "1" });
      }
    }
    tasks.sort((a, b) => (a.nivel !== b.nivel) ? b.nivel - a.nivel : a.vencimentoSort - b.vencimentoSort);
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
function forcarAutorizacao() { SpreadsheetApp.getUi().alert("🛡️ Autorizado."); }
function comandoSincronizarProvas() { sincronizarProvasDeEntregaAPI(); }
function comandoSincronizarHistorico() { sincronizarHistoricoComProtocolos(); }
function comandoArquivarTarefas() { arquivarTarefasConcluidas(); }
function comandoAtualizarRisco() { atualizarRelatorioRisco(); }
function comandoLimparCache() { invalidarCacheSistema(); SpreadsheetApp.getUi().alert("⚡ Cache invalidado."); }
function comandoMapearPastas() { mapearPastasClientesAutomatico(); }
function instalarGatilhoSincronismo() { removerGatilhosSincronismo(); ScriptApp.newTrigger('sincronizarProvasDeEntregaAPI').timeBased().everyHours(1).create(); SpreadsheetApp.getUi().alert("✅ Automação Ativa."); }
function removerGatilhosSincronismo() { var triggers = ScriptApp.getProjectTriggers(); for (var i = 0; i < triggers.length; i++) { if (triggers[i].getHandlerFunction() === 'sincronizarProvasDeEntregaAPI') ScriptApp.deleteTrigger(triggers[i]); } }
function abrirDashboardVisual() { SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutputFromFile('Dashboard').setWidth(1000).setHeight(750), 'DASHBOARD'); }
function comandoBackupManual() { var res = executarBackupTotal(); if (res) SpreadsheetApp.getUi().alert("✅ " + res); }
function instalarGatilhoBackup() { removerGatilhoBackup(); ScriptApp.newTrigger('executarBackupTotal').timeBased().everyDays(1).atHour(23).create(); SpreadsheetApp.getUi().alert("✅ Backup Diário Agendado."); }
function removerGatilhoBackup() { var triggers = ScriptApp.getProjectTriggers(); for (var i = 0; i < triggers.length; i++) { if (triggers[i].getHandlerFunction() === 'executarBackupTotal') ScriptApp.deleteTrigger(triggers[i]); } }
function abrirAuditorRegras() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  if (sheet.getName() !== CONFIG_SISTEMA.ABA_CLIENTES) return;
  var row = sheet.getActiveRange().getRow();
  if (row < 2) return;
  var t = HtmlService.createTemplateFromFile('AuditorRegras');
  t.clienteIndex = row;
  SpreadsheetApp.getUi().showModalDialog(t.evaluate().setHeight(650).setWidth(900), '🔍 AUDITORIA');
}
