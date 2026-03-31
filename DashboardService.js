/**
 * 📊 DASHBOARD & REPORTING SERVICE v130.06
 * Responsável por alimentar as interfaces visuais com suporte a Vencimento Legal.
 */

function getDashboardData(filtroPeriodo) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    var wsUsuarios = ss.getSheetByName(CONFIG_SISTEMA.ABA_USUARIOS);
    if (!wsTarefas) return { error: "Aba de tarefas não encontrada." };
    
    var dataInicio = null;
    var dataFim = null;
    var hoje = new Date();
    var periodo = filtroPeriodo || "ESTE_MES";

    if (periodo === "ESTE_MES") {
      dataInicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
      dataFim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0); 
    } else if (periodo === "MES_ANTERIOR") {
      dataInicio = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
      dataFim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
    } else if (periodo === "ANO_ATUAL") {
      dataInicio = new Date(hoje.getFullYear(), 0, 1);
      dataFim = new Date(hoje.getFullYear(), 11, 31);
    }

    var mapUsuarios = {};
    if (wsUsuarios) {
      var dataU = wsUsuarios.getDataRange().getValues();
      for (var u = 1; u < dataU.length; u++) {
        var emailU = String(dataU[u][0]).trim().toUpperCase();
        var nomeU = String(dataU[u][1]).trim().toUpperCase();  
        if (emailU) mapUsuarios[emailU] = nomeU; 
      }
    }

    var stats = { total: 0, pendentes: 0, entregues: 0, departamentos: {}, usuarios: {} };
    
    function processarLinhas(values) {
      if (values.length <= 1) return;
      for (var i = 1; i < values.length; i++) {
        if (dataInicio && dataFim) {
          var dataRow = values[i][3];
          var dataRef = (dataRow instanceof Date) ? dataRow : new Date(dataRow);
          if (isNaN(dataRef.getTime())) continue; 
          if (dataRef < dataInicio || dataRef > dataFim) continue;
        }

        var depto = String(values[i][4] || "SEM DEPARTAMENTO").toUpperCase().trim();
        var status = String(values[i][5] || "").toUpperCase().trim();
        var respEmail = String(values[i][8] || "SEM RESPONSAVEL").toUpperCase().trim();
        var respNome = mapUsuarios[respEmail] || respEmail;
        if (!status) continue;

        stats.total++;
        if (!stats.departamentos[depto]) stats.departamentos[depto] = { total: 0, pendentes: 0, entregues: 0 };
        stats.departamentos[depto].total++;

        if (!stats.usuarios[respNome]) stats.usuarios[respNome] = { total: 0, pendentes: 0, entregues: 0 };
        stats.usuarios[respNome].total++;
        
        if (status === CONFIG_SISTEMA.STATUS.ENTREGUE) {
          stats.entregues++;
          stats.departamentos[depto].entregues++;
          stats.usuarios[respNome].entregues++;
        } else {
          stats.pendentes++;
          stats.departamentos[depto].pendentes++;
          stats.usuarios[respNome].pendentes++;
        }
      }
    }

    processarLinhas(wsTarefas.getDataRange().getValues());
    if (wsHist) processarLinhas(wsHist.getDataRange().getValues());

    return stats;
  } catch (e) { 
    return { error: e.message };
  }
}

/**
 * Busca protocolos pendentes de leitura e cruza com as tarefas para obter o Vencimento Legal.
 */
function getProtocolosPendentes() {
  try {
    // ⚡ CACHE: Tenta retornar resultado cacheado
    var cached = getViewCached(CACHE_CONFIG.KEYS.PROTOCOLOS_RESULT);
    if (cached) return cached;

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    
    if (!wsProt) return [];
    
    // 1. Criar Mapa de Vencimento Legal (ID_CONTROLE -> VENCIMENTO_LEGAL)
    var mapVctoLegal = {};
    
    function mapearVctos(sheet) {
      if (!sheet) return;
      var lastR = sheet.getLastRow();
      if (lastR <= 1) return;
      // OTIMIZAÇÃO: Lê apenas até a coluna L (Índice 11) que é o Vencimento Legal
      var data = sheet.getRange(1, 1, lastR, 12).getValues();
      for (var i = 1; i < data.length; i++) {
        var id = String(data[i][9]).trim(); // Coluna J
        var vctoLegal = data[i][11];        // Coluna L
        var acao = String(data[i][7]).toUpperCase().trim(); // Coluna H
        if (id) mapVctoLegal[id] = { vctoLegal: vctoLegal, acao: acao };
      }
    }
    
    mapearVctos(wsTarefas);
    // mapearVctos(wsHist); // As arquivadas não precisam de acompanhamento

    // 2. Processar Protocolos
    var dataP = wsProt.getDataRange().getValues();
    var pendentes = [];
    
    for (var j = 1; j < dataP.length; j++) {
      var statusEnvio = String(dataP[j][8]).toUpperCase().trim();
      var confRecto = String(dataP[j][9]).toUpperCase().trim();
      
      // Filtro: Enviado mas ainda não lido/confirmado
      if (statusEnvio === "ENVIADO" && (confRecto === "" || confRecto === "AGUARDANDO")) {
        var idTarefa = String(dataP[j][3]).trim();
        var infoTarefa = mapVctoLegal[idTarefa];
        
        // NOVO FILTRO: Deve existir em DB_TAREFAS e ter ação ENVIAR
        if (!infoTarefa || infoTarefa.acao !== "ENVIAR") continue;

        var vctoLegalRaw = infoTarefa.vctoLegal;
        var vctoLegalFmt = (vctoLegalRaw instanceof Date) ? Utilities.formatDate(vctoLegalRaw, "GMT-3", "dd/MM/yyyy") : "---";
        
        var dataEnvioRaw = dataP[j][0];
        var dataEnvioFmt = (dataEnvioRaw instanceof Date) ? Utilities.formatDate(dataEnvioRaw, "GMT-3", "dd/MM/yyyy HH:mm") : String(dataEnvioRaw);
        
        var linkBruto = String(dataP[j][7]);
        var primeiroLink = linkBruto.split("|")[0].trim();
        
        pendentes.push({
          data: dataEnvioFmt,
          cliente: String(dataP[j][1]),
          protocolo: String(dataP[j][2]),
          obrigacao: String(dataP[j][4]),
          vencimentoLegal: vctoLegalFmt, 
          link: primeiroLink
        });
      }
    }
    
    var resultado = pendentes.reverse();
    
    // ⚡ CACHE: Grava resultado processado
    setViewCache(CACHE_CONFIG.KEYS.PROTOCOLOS_RESULT, resultado);
    
    return resultado; 
  } catch (e) {
    registrarLogSistema("GET_PROTO_DASH_ERR", e.message);
    return [];
  }
}

function getRelatorioAuditoria(clienteIdx) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  var wsRegras = ss.getSheetByName(CONFIG_SISTEMA.ABA_REGRAS);
  var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);

  if (!wsCli || !wsRegras) return [];
  
  var dataCli = wsCli.getDataRange().getValues();
  if (clienteIdx > dataCli.length) return [];
  var c = clienteIdx - 1; 
  var clienteNome = dataCli[c][1];
  var cliNorm = norm(clienteNome);
  var regCli = norm(dataCli[c][6]);
  var excStr = String(dataCli[c][11]);
  var excecoes = excStr ? excStr.split(',').map(e => norm(e)) : [];

  var dataReg = wsRegras.getDataRange().getValues();
  var dataTf = wsTarefas.getDataRange().getValues();
  var dataHist = wsHist ? wsHist.getDataRange().getValues() : [];
  
  var agora = new Date();
  var mesAnoRef = Utilities.formatDate(agora, "GMT-3", "MM/yyyy");
  var mesAtualInt = parseInt(Utilities.formatDate(agora, "GMT-3", "MM"), 10);

  var mapaTf = {};
  for(var i=1; i<dataTf.length; i++) {
    var key = norm(safeGetMesAnoStr(dataTf[i][0])) + "|" + norm(dataTf[i][1]) + "|" + norm(dataTf[i][2]);
    mapaTf[key] = String(dataTf[i][5]);
  }
  
  var mapaHist = {};
  for(var h=1; h<dataHist.length; h++) {
    if (String(dataHist[h][5]).toUpperCase() === CONFIG_SISTEMA.STATUS.ENTREGUE) {
      var hKey = norm(safeGetMesAnoStr(dataHist[h][0])) + "|" + norm(dataHist[h][1]) + "|" + norm(dataHist[h][2]);
      mapaHist[hKey] = true;
    }
  }

  var relatorio = [];
  for (var r = 1; r < dataReg.length; r++) {
    var nomeRegra = String(dataReg[r][1]).trim();
    if (!nomeRegra) continue;
    var status = "OK", detalhe = "Geraria Tarefa Hoje", cor = "green";
    var regraNorm = norm(nomeRegra);
    
    if (excecoes.indexOf(regraNorm) > -1) {
      status = "BLOQUEADO"; detalhe = "Cliente possui Exceção"; cor = "red";
    }
    
    var mesesPermitidos = String(dataReg[r][6]).trim();
    if (status === "OK" && mesesPermitidos !== "") {
      var mesesArray = mesesPermitidos.split(",").map(m => parseInt(m.trim(), 10));
      if (mesesArray.indexOf(mesAtualInt) === -1) {
        status = "BLOQUEADO"; detalhe = "Mês fora da regra"; cor = "orange";
      }
    }

    var regRegra = norm(dataReg[r][4]);
    if (status === "OK" && regRegra && regRegra !== "TODOS" && regRegra !== regCli) {
      status = "BLOQUEADO"; detalhe = "Regime Divergente"; cor = "red";
    }

    var hash = norm(mesAnoRef) + "|" + cliNorm + "|" + regraNorm;
    if (status === "OK") {
        if (mapaHist[hash]) { status = "CONCLUÍDO"; detalhe = "Já no Histórico"; cor = "blue"; }
        else if (mapaTf[hash]) { status = "EXISTENTE"; detalhe = "Já em Tarefas"; cor = "blue"; }
    }

    relatorio.push({ regra: nomeRegra, status: status, detalhe: detalhe, cor: cor });
  }
  return relatorio;
}