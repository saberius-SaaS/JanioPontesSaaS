/**
 * 🧹 MAINTENANCE & COMPLIANCE SERVICE v131.10
 * Evolução: LockService otimizado e tratamento de contenção.
 * Blindagem: Uso de getSafeStatus() para prevenir erros de regressão global.
 */

/**
 * Padroniza o layout das abas principais conforme o Schema v131.
 */
function padronizarLayout() {
  var ss = getSs();
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
    },
    {
      nome: CONFIG_SISTEMA.ABA_WORKFLOWS,
      cols: 6,
      cabecalho: ["FASE_ATUAL", "PROXIMA_FASE", "DIAS", "DEPARTAMENTO", "ACAO", "RESPONSAVEL_PADRAO"]
    }
  ];
  abas.forEach(function(item) {
    var sheet = ss.getSheetByName(item.nome);
    if (!sheet) return;
    var headerRange = sheet.getRange(1, 1, 1, item.cabecalho.length);
    headerRange.setDataValidation(null);
    headerRange.setValues([item.cabecalho]).setBackground("#1C3051").setFontColor("white").setFontWeight("bold").setHorizontalAlignment("center");
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
  var ss = getSs();
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
  var ss = getSs();
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
      var idSolicitacao = dataSol[i][0], 
          cliente = dataSol[i][2], 
          email = dataSol[i][3], 
          pedido = dataSol[i][4],
          infoTarefa = dataSol[i][11]; // Coluna L: META_TAREFA

      enviarLembreteCobranca(cliente, email, pedido, idSolicitacao, qtdAvisos, infoTarefa, dataSol[i][10]);
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
    var ss = getSs();
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
 * ⚡ TRANSFERÊNCIA IMEDIATA PARA HISTÓRICO
 * Move uma tarefa ENTREGUE diretamente para DB_HISTORICO e remove de DB_TAREFAS.
 * Chamada automaticamente ao concluir uma tarefa (sem depender do Robô de Arquivamento).
 * @param {number} rowIdx - Índice da linha na DB_TAREFAS (1-based, incluindo header)
 */
function moverTarefaParaHistoricoImediato(rowIdx) {
  try {
    var ss = getSs();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
    
    if (!wsTarefas || !wsHist) return;

    // 1. Lê os 12 campos da tarefa
    var rowData = wsTarefas.getRange(rowIdx, 1, 1, 12).getValues()[0];

    // 2. Cruza com DB_PROTOCOLOS para obter statusEnvio e confRecto
    var idTarefa = String(rowData[9]).trim();
    var statusEnvio = "-";
    var confRecto = "-";

    if (wsProt) {
      var dataProt = wsProt.getDataRange().getValues();
      for (var p = dataProt.length - 1; p >= 1; p--) {
        if (String(dataProt[p][3]).trim() === idTarefa) {
          statusEnvio = dataProt[p][8] || "MANUAL";
          confRecto = (dataProt[p][9] instanceof Date)
            ? Utilities.formatDate(dataProt[p][9], "GMT-3", "dd/MM/yyyy HH:mm:ss")
            : String(dataProt[p][9] || "");
          break;
        }
      }
    }

    // 3. Grava no DB_HISTORICO (14 colunas: 12 tarefa + statusEnvio + confRecto)
    var histRow = rowData.concat([statusEnvio, confRecto]);
    wsHist.getRange(wsHist.getLastRow() + 1, 1, 1, 14).setValues([histRow]);

    // 4. Remove da DB_TAREFAS
    wsTarefas.deleteRow(rowIdx);

    registrarLogSistema("ARCHIVE_INSTANT", "Tarefa " + idTarefa + " transferida imediatamente para histórico.");
  } catch (e) {
    registrarLogSistema("ARCHIVE_INSTANT_ERR", "Falha ao transferir tarefa (row " + rowIdx + "): " + e.message);
  }
}

/**
 * Identifica tarefas pendentes e atrasadas para alimentar o relatório de compliance.
 */
function atualizarRelatorioRisco() {
  var ss = getSs();
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

      if (dataObj <= hoje) {
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
 * Otimizado com Batch Operations (Regra 5.1) para evitar timeout em grandes volumes.
 */
function sincronizarHistoricoComProtocolos() {
  var ss = getSs();
  var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  if (!wsHist || !wsProt) return 0;
  var dataHist = wsHist.getDataRange().getValues();
  var dataProt = wsProt.getDataRange().getValues();
  if (dataHist.length <= 1) return 0;
  var mapProt = {};
  for (var p = 1; p < dataProt.length; p++) {
    var idTarefa = String(dataProt[p][3]).trim();
    if (idTarefa) mapProt[idTarefa] = { status: dataProt[p][8], conf: dataProt[p][9] };
  }
  // Leitura em lote das colunas M e N (13 e 14) do Histórico
  var qtdLinhas = dataHist.length - 1;
  var rangeSync = wsHist.getRange(2, 13, qtdLinhas, 2);
  var valoresSync = rangeSync.getValues();
  var updates = 0;
  for (var h = 1; h < dataHist.length; h++) {
    var id = String(dataHist[h][9]).trim();
    if (mapProt[id]) {
      var p = mapProt[id];
      var confStr = (p.conf instanceof Date) ? Utilities.formatDate(p.conf, "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(p.conf || "");
      var histConf = dataHist[h][13];
      var histConfStr = (histConf instanceof Date) ? Utilities.formatDate(histConf, "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(histConf || "");
      if (String(p.status) !== String(dataHist[h][12]) || confStr !== histConfStr) {
        valoresSync[h - 1] = [p.status, confStr];
        updates++;
      }
    }
  }
  // Gravação em lote única (somente se houve mudanças reais)
  if (updates > 0) {
    rangeSync.setValues(valoresSync);
    SpreadsheetApp.flush();
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
  SpreadsheetApp.newTrigger(nomeFuncao)
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();
    
  SpreadsheetApp.getUi().alert("✅ Lixeiro Robótico Ativado!\nA rotina rodará silenciosamente todo dia perto das 07:00h da manhã.");
}

/**
 * 🧹 SANEAMENTO GLOBAL DE AÇÕES LEGADAS
 */
function sanearAcoesGlobais() {
  var ss = getSs();
  var abasParaSanear = [
    { nome: CONFIG_SISTEMA.ABA_TAREFAS, col: 8 },
    { nome: CONFIG_SISTEMA.ABA_REGRAS, col: 6 },
    { nome: CONFIG_SISTEMA.ABA_WORKFLOWS, col: 5 }
  ];
  
  var totalCorrecoes = 0;
  
  abasParaSanear.forEach(function(item) {
    var ws = ss.getSheetByName(item.nome);
    if (!ws) return;
    
    var lr = ws.getLastRow();
    if (lr <= 1) return;
    
    var range = ws.getRange(2, item.col, lr - 1, 1);
    var valores = range.getValues();
    var alterou = false;
    
    for (var i = 0; i < valores.length; i++) {
      var acaoOriginal = valores[i][0];
      var acaoSaneada = getSafeAction(acaoOriginal);
      
      if (acaoOriginal !== acaoSaneada) {
        valores[i][0] = acaoSaneada;
        alterou = true;
        totalCorrecoes++;
      }
    }
    
    if (alterou) {
      range.setValues(valores);
    }
  });
  
  registrarLogSistema("MAINTENANCE_ACTION_SANITY", "Total de correções de ações: " + totalCorrecoes);
  return totalCorrecoes;
}

/**
 * 🧹 SANEAMENTO GLOBAL DE DEPARTAMENTOS
 */
function sanearDeptosGlobais() {
  var ss = getSs();
  var abasParaSanear = [
    { nome: CONFIG_SISTEMA.ABA_TAREFAS, col: 5 },
    { nome: CONFIG_SISTEMA.ABA_REGRAS, col: 4 },
    { nome: CONFIG_SISTEMA.ABA_WORKFLOWS, col: 4 }
  ];
  
  var totalCorrecoes = 0;
  
  abasParaSanear.forEach(function(item) {
    var ws = ss.getSheetByName(item.nome);
    if (!ws) return;
    
    var lr = ws.getLastRow();
    if (lr <= 1) return;
    
    var range = ws.getRange(2, item.col, lr - 1, 1);
    var valores = range.getValues();
    var alterou = false;
    
    for (var i = 0; i < valores.length; i++) {
      var deptoOriginal = valores[i][0];
      var deptoSaneado = getSafeDepto(deptoOriginal);
      
      if (deptoOriginal !== deptoSaneado) {
        valores[i][0] = deptoSaneado;
        alterou = true;
        totalCorrecoes++;
      }
    }
    
    if (alterou) {
      range.setValues(valores);
    }
  });
  
  registrarLogSistema("MAINTENANCE_DEPTO_SANITY", "Total de correções de departamentos: " + totalCorrecoes);
  return totalCorrecoes;
}

/**
 * ⏰ Instala o gatilho para a rotina de cobranças automáticas.
 * Roda diariamente conforme CONFIG_SISTEMA.DIAS_INTERVALO_COBRANCA.
 */
function instalarGatilhoCobrancaDiaria() {
  var nomeFuncao = 'executarRotinaCobrancas';
  var triggers = ScriptApp.getProjectTriggers();
  
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === nomeFuncao) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  
  ScriptApp.newTrigger(nomeFuncao)
    .timeBased()
    .everyDays(1)
    .atHour(8) // Rodar às 08:00 AM
    .create();
    
  registrarLogSistema("TRIGGER_INSTALLED", "Gatilho de cobrança automática ativado.");
  return "✅ Automação de solicitações ativada (Diário às 08h).";
}

/**
 * 🧹 Limpeza em Lote de Logs de Infraestrutura (DB_LOGS)
 * Recomendado para reduzir inchaço de dezenas de milhares de linhas.
 */
function limparDbLogsEmLote() {
  try {
    var ss = getSs();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    if (!wsLog) return;
    
    var data = wsLog.getDataRange().getValues();
    if (data.length <= 1) return;
    
    var cabecalho = data[0];
    var ignorar = ["CACHE_INVALIDATED", "PORTAL_AUTH", "GIS_FALLBACK_OK", "PING_SESSION"];
    var filtrados = [cabecalho];
    
    for (var i = 1; i < data.length; i++) {
      var acao = String(data[i][2]).toUpperCase().trim(); // Ação fica na coluna C (índice 2)
      if (ignorar.indexOf(acao) === -1) {
        filtrados.push(data[i]);
      }
    }
    
    // Limpa tudo (CORREÇÃO: o método na classe Sheet é clearContents)
    wsLog.clearContents();
    
    // Escreve apenas os filtrados de volta
    if (filtrados.length > 0) {
      wsLog.getRange(1, 1, filtrados.length, filtrados[0].length).setValues(filtrados);
    }
    
    SpreadsheetApp.flush();
    var msg = "✅ Limpeza Concluída!\n\nForam removidas " + (data.length - filtrados.length) + " linhas de infraestrutura.";
    try { SpreadsheetApp.getUi().alert(msg); } catch(e) { console.log(msg); }
    
  } catch (e) {
    try { SpreadsheetApp.getUi().alert("❌ Erro ao limpar logs: " + e.message); } catch(err) {}
  }
}
