/**
 * 🧹 MAINTENANCE & COMPLIANCE SERVICE v131.10
 * Evolução: LockService otimizado e tratamento de contenção.
 * Blindagem: Uso de getSafeStatus() para prevenir erros de regressão global.
 */

/**
 * Padroniza o layout das abas principais conforme o Schema v131.
 */
function padronizarLayout() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var abas = [
    {
      nome: CONFIG_SISTEMA.ABA_REGRAS, 
      cols: 12, 
      cabecalho: ["ID", "OBRIGACAO", "DIA", "DEPARTAMENTO", "REGIME", "ACAO", "MESES", "TIPOS", "DESLOCA", "VENCIMENTO_LEGAL", "ANTECIPA_FDS", "GRUPO_REGRA"]
    },
    {
      nome: CONFIG_SISTEMA.ABA_CLIENTES, 
      cols: 16, 
      cabecalho: ["ID", "CLIENTE", "CNPJ", "RESPONSAVEL", "EMAIL", "TELEFONE", "REGIME", "FISCAL", "CONTABIL", "PESSOAL", "SOCIETARIO", "EXCECOES", "PASTA_DRIVE", "NIVEL", "PERFIS_ATIVOS", "STATUS"]
    },
    {
      nome: CONFIG_SISTEMA.ABA_TAREFAS, 
      cols: 12, 
      cabecalho: ["MES_ANO", "CLIENTE", "OBRIGACAO", "VENCIMENTO", "DEPARTAMENTO", "STATUS", "PROTOCOLO", "ACAO", "RESPONSAVEL", "ID_CONTROLE", "NIVEL", "VENCIMENTO_LEGAL"]
    }
  ];
  abas.forEach(function(item) {
    var sheet = ss.getSheetByName(item.nome);
    if (!sheet) return;
    sheet.getRange(1, 1, 1, item.cabecalho.length).setValues([item.cabecalho]).setBackground("#1C3051").setFontColor("white").setFontWeight("bold").setHorizontalAlignment("center");
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, sheet.getMaxRows(), item.cols).setFontFamily("Inter").setFontSize(10);
    sheet.autoResizeColumns(1, item.cols);
  });
  SpreadsheetApp.getUi().alert("✨ Layout v131.06 Padronizado!");
}

/**
 * Varre o Drive e mapeia as URLs das pastas dos clientes para a planilha.
 */
function mapearPastasClientesAutomatico() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  if (!wsCli) return;
  var dataCli = wsCli.getDataRange().getValues();
  try {
    var rootFolder = DriveApp.getFolderById(CONFIG_SISTEMA.PASTAS.CLIENTES_DIGITAL);
    var subFolders = rootFolder.getFolders();
    var mapaNomes = new Map();
    var mapaIds = new Set();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      mapaNomes.set(norm(folder.getName()), { url: folder.getUrl(), id: folder.getId() });
      mapaIds.add(folder.getId());
    }
    var criadas = 0, mapeadas = 0;
    for (var i = 1; i < dataCli.length; i++) {
      var nomeClienteOriginal = String(dataCli[i][1]).trim();
      if (!nomeClienteOriginal) continue;
      var nomeClienteNorm = norm(nomeClienteOriginal);
      var linkAtual = String(dataCli[i][12]);
      var idNoLink = linkAtual.indexOf("id=") > -1 ? linkAtual.split("id=")[1] : (linkAtual.indexOf("folders/") > -1 ? linkAtual.split("folders/")[1].split("?")[0] : "");
      if (!mapaIds.has(idNoLink)) {
        if (mapaNomes.has(nomeClienteNorm)) {
          wsCli.getRange(i + 1, 13).setValue(mapaNomes.get(nomeClienteNorm).url); mapeadas++;
        } else {
          var novaPasta = rootFolder.createFolder(nomeClienteOriginal);
          wsCli.getRange(i + 1, 13).setValue(novaPasta.getUrl()); criadas++;
          mapaNomes.set(nomeClienteNorm, { url: novaPasta.getUrl(), id: novaPasta.getId() });
          mapaIds.add(novaPasta.getId());
        }
      }
    }
    SpreadsheetApp.flush(); invalidarCacheSistema();
    SpreadsheetApp.getUi().alert("✅ Sincronização Concluída.");
  } catch (e) { SpreadsheetApp.getUi().alert("❌ Erro: " + e.message); }
}

/**
 * Envia lembretes de cobrança para solicitações pendentes no portal.
 */
function executarRotinaCobrancas() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsSol = ss.getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
  if (!wsSol) return 0;
  var dataSol = wsSol.getDataRange().getValues();
  var hoje = new Date();
  var totalEnviados = 0;
  var intervaloDias = CONFIG_SISTEMA.DIAS_INTERVALO_COBRANCA || 2;
  var STATUS_PENDENTE = getSafeStatus("PENDENTE");

  for (var i = 1; i < dataSol.length; i++) {
    var status = String(dataSol[i][6]).toUpperCase().trim();
    if (status !== STATUS_PENDENTE) continue;
    var dataSolicitacao = new Date(dataSol[i][1]); 
    var ultimaCobranca = dataSol[i][8] ? new Date(dataSol[i][8]) : null;
    var qtdAvisos = parseInt(dataSol[i][9]) || 0; 
    var dataBaseCalculo = ultimaCobranca ? ultimaCobranca : dataSolicitacao;
    var diffTime = Math.abs(hoje - dataBaseCalculo);
    var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays >= intervaloDias) {
      var idSolicitacao = dataSol[i][0], cliente = dataSol[i][2], email = dataSol[i][3], pedido = dataSol[i][4];
      enviarLembreteCobranca(cliente, email, pedido, idSolicitacao, qtdAvisos);
      wsSol.getRange(i + 1, 9).setValue(hoje); 
      wsSol.getRange(i + 1, 10).setValue(qtdAvisos + 1); 
      totalEnviados++;
    }
  }
  return totalEnviados;
}

/**
 * Move tarefas concluídas para a aba de Histórico e limpa a tabela principal.
 */
function arquivarTarefasConcluidas() {
  var lock = LockService.getScriptLock();
  try { 
    lock.waitLock(30000); 
  } catch(e) { 
    registrarLogSistema("LOCK_TIMEOUT", "arquivarTarefasConcluidas abortado.");
    return 0; 
  }
  
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
    
    if (!wsTarefas || !wsHist || !wsProt) return 0;

    var STATUS_ENTREGUE = getSafeStatus("ENTREGUE");
    var lr = wsTarefas.getLastRow();
    if (lr <= 1) return 0; 

    var dataProt = wsProt.getDataRange().getValues();
    var mapProt = {};
    for(var p=1; p<dataProt.length; p++) {
      var idT = String(dataProt[p][3]).trim();
      if(idT) {
        var cFmt = (dataProt[p][9] instanceof Date) ? Utilities.formatDate(dataProt[p][9], "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(dataProt[p][9] || "");
        mapProt[idT] = { statusEnvio: dataProt[p][8] || "MANUAL", confRecto: cFmt };
      }
    }

    var valores = wsTarefas.getRange(2, 1, lr - 1, 12).getValues();
    var tarefasAtivas = [], tarefasParaArquivar = [];

    for (var i = 0; i < valores.length; i++) {
      var statusAtual = valores[i][5] ? String(valores[i][5]).toUpperCase().trim() : "";
      if (statusAtual === STATUS_ENTREGUE) {
        var idTarefa = String(valores[i][9]).trim();
        var dadosExtras = mapProt[idTarefa] || { statusEnvio: "-", confRecto: "-" };
        tarefasParaArquivar.push(valores[i].concat([dadosExtras.statusEnvio, dadosExtras.confRecto]));
      } else { 
        tarefasAtivas.push(valores[i]);
      }
    }

    if (tarefasParaArquivar.length === 0) return 0;

    wsHist.getRange(wsHist.getLastRow() + 1, 1, tarefasParaArquivar.length, 14).setValues(tarefasParaArquivar);
    wsTarefas.getRange(2, 1, lr - 1, 12).clearContent();
    if (tarefasAtivas.length > 0) {
      wsTarefas.getRange(2, 1, tarefasAtivas.length, 12).setValues(tarefasAtivas);
    }

    SpreadsheetApp.flush(); 
    reordenarTarefasElite(); 
    invalidarCacheSistema();
    
    registrarLogSistema("ARCHIVE_SUCCESS", "Arquivadas: " + tarefasParaArquivar.length);
    return tarefasParaArquivar.length;
  } catch (e) {
    registrarLogSistema("ARCHIVE_ERR", e.message);
    throw e;
  } finally { 
    lock.releaseLock(); 
  }
}

/**
 * Identifica tarefas pendentes e atrasadas para alimentar o relatório de compliance.
 */
function atualizarRelatorioRisco() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var wsRisco = ss.getSheetByName(CONFIG_SISTEMA.ABA_RISCO);
  
  if (!wsTarefas || !wsRisco) {
    registrarLogSistema("RISK_ERR", "Abas não localizadas.");
    return;
  }

  var STATUS_PENDENTE = getSafeStatus("PENDENTE");
  var data = wsTarefas.getDataRange().getValues();
  if (data.length <= 1) return 0;

  var hoje = new Date(); 
  hoje.setHours(0,0,0,0);
  var tarefasRisco = [];

  for (var i = 1; i < data.length; i++) {
    var statusCelula = data[i][5] ? String(data[i][5]).toUpperCase().trim() : "";
    if (statusCelula === STATUS_PENDENTE) {
      var dtVcto = data[i][3];
      var dataObj = (dtVcto instanceof Date) ? dtVcto : new Date(dtVcto);
      if (isNaN(dataObj.getTime())) continue;

      if (dataObj < hoje) {
        var diasAtraso = Math.floor((hoje - dataObj) / (1000 * 60 * 60 * 24));
        var linha = [data[i][1], data[i][2], data[i][3], statusCelula, diasAtraso, data[i][8]];
        linha._nivel = parseInt(data[i][10]) || 1; 
        tarefasRisco.push(linha);
      }
    }
  }

  tarefasRisco.sort(function(a, b) {
    if (a._nivel !== b._nivel) return b._nivel - a._nivel;
    return a[2].getTime() - b[2].getTime();
  });

  var lrRisco = wsRisco.getLastRow();
  if (lrRisco > 1) wsRisco.getRange(2, 1, lrRisco - 1, 6).clearContent();

  if (tarefasRisco.length > 0) {
    var finalData = tarefasRisco.map(function(t) { return [t[0], t[1], t[2], t[3], t[4], t[5]]; });
    wsRisco.getRange(2, 1, finalData.length, 6).setValues(finalData);
  }

  registrarLogSistema("RISK_UPDATED", "Itens em risco: " + tarefasRisco.length);
  return tarefasRisco.length;
}

/**
 * Sincroniza informações de visualização do protocolo com o Histórico.
 */
function sincronizarHistoricoComProtocolos() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  if (!wsHist || !wsProt) return 0;
  var dataHist = wsHist.getDataRange().getValues();
  var dataProt = wsProt.getDataRange().getValues();
  var mapProt = {};
  for (var p = 1; p < dataProt.length; p++) {
    var idTarefa = String(dataProt[p][3]).trim();
    if (idTarefa) mapProt[idTarefa] = { status: dataProt[p][8], conf: dataProt[p][9] };
  }
  var updates = 0;
  for (var h = 1; h < dataHist.length; h++) {
    var id = String(dataHist[h][9]).trim();
    if (mapProt[id]) {
      var p = mapProt[id];
      var confStr = (p.conf instanceof Date) ? Utilities.formatDate(p.conf, "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(p.conf || "");
      var histConf = dataHist[h][13];
      var histConfStr = (histConf instanceof Date) ? Utilities.formatDate(histConf, "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(histConf || "");
      if (String(p.status) !== String(dataHist[h][12]) || confStr !== histConfStr) {
        wsHist.getRange(h + 1, 13, 1, 2).setValues([[p.status, confStr]]);
        updates++;
      }
    }
  }
  return updates;
}

/**
 * Limpa versões e implantações antigas via Google Apps Script API.
 * Limite do Google: 200 versões. A função manterá as 30 mais recentes.
 */
function limparVersoesAntigas() {
  try {
    var scriptId = ScriptApp.getScriptId();
    var token = ScriptApp.getOAuthToken();
    var qtdManter = 30;
    
    var headersAuth = {
      Authorization: "Bearer " + token
    };

    // 1. LIMPAR IMPLANTAÇÕES (Deployments)
    var urlDeps = 'https://script.googleapis.com/v1/projects/' + scriptId + '/deployments';
    var deployments = [];
    var pageTokenDeps = null;
    
    do {
      var urlFmt = urlDeps + (pageTokenDeps ? "?pageToken=" + pageTokenDeps : "");
      var res = UrlFetchApp.fetch(urlFmt, { method: 'get', headers: headersAuth, muteHttpExceptions: true });
      if (res.getResponseCode() !== 200) break;
      var json = JSON.parse(res.getContentText());
      deployments = deployments.concat(json.deployments || []);
      pageTokenDeps = json.nextPageToken;
    } while (pageTokenDeps);

    if (deployments.length > qtdManter) {
      deployments.sort(function(a, b) { return new Date(b.updateTime).getTime() - new Date(a.updateTime).getTime(); });
      var depDeletados = 0, depFalhas = 0;
      for (var i = qtdManter; i < deployments.length; i++) {
         var dep = deployments[i];
         // Se não tem versão (ex: @HEAD), não excluímos para não quebrar o acesso atual
         if (!dep.deploymentConfig || !dep.deploymentConfig.versionNumber) continue;
         
         var resDelDep = UrlFetchApp.fetch(urlDeps + '/' + dep.deploymentId, { method: 'delete', headers: headersAuth, muteHttpExceptions: true });
         if (resDelDep.getResponseCode() === 200) depDeletados++; else depFalhas++;
      }
      registrarLogSistema("DEP_CLEAN_STATUS", "Analise: " + deployments.length + " total | " + depDeletados + " deletados | " + depFalhas + " falhas.");
    }

    // 2. LIMPAR VERSÕES (Versions)
    var urlVersoes = 'https://script.googleapis.com/v1/projects/' + scriptId + '/versions';
    var versoes = [];
    var pageTokenVers = null;
    
    do {
      var vUrlFmt = urlVersoes + (pageTokenVers ? "?pageToken=" + pageTokenVers : "");
      var resV = UrlFetchApp.fetch(vUrlFmt, { method: 'get', headers: headersAuth, muteHttpExceptions: true });
      if (resV.getResponseCode() !== 200) break;
      var jsonV = JSON.parse(resV.getContentText());
      versoes = versoes.concat(jsonV.versions || []);
      pageTokenVers = jsonV.nextPageToken;
    } while (pageTokenVers);

    if (versoes.length > qtdManter) {
      versoes.sort(function(a, b) { return b.versionNumber - a.versionNumber; });
      var deletadas = 0, falhasVers = 0, lastErro = "";
      for (var j = qtdManter; j < versoes.length; j++) {
        var vNum = versoes[j].versionNumber;
        var resDel = UrlFetchApp.fetch(urlVersoes + '/' + vNum, { method: 'delete', headers: headersAuth, muteHttpExceptions: true });
        if (resDel.getResponseCode() === 200) {
          deletadas++;
        } else {
          falhasVers++;
          lastErro = resDel.getResponseCode();
        }
      }
      registrarLogSistema("VERSION_CLEAN", "Total: " + versoes.length + " | Limpas: " + deletadas + " | Bloqueadas: " + falhasVers + " (Cod: " + lastErro + ")");
    }

  } catch (e) {
    registrarLogSistema("CLEANUP_CRITICAL", e.message);
  }
}

/**
 * Instala o gatilho (Trigger) para rodar o Lixeiro de Versões todo dia às 7 da manhã.
 */
function instalarGatilhoLimpezaDiaria() {
  var nomeFuncao = 'limparVersoesAntigas';
  var triggers = ScriptApp.getProjectTriggers();
  
  // Limpa gatilhos antigos para evitar duplicação em múltiplos cliques
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === nomeFuncao) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  
  // Cria o novo
  ScriptApp.newTrigger(nomeFuncao)
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();
    
  SpreadsheetApp.getUi().alert("✅ Lixeiro Robótico Ativado!\nA rotina rodará silenciosamente todo dia perto das 07:00h da manhã.");
}
