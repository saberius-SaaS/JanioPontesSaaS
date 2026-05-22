/**
 * 🕵️ ACCESS & TELEMETRY SERVICE v1.0
 * Responsável por monitorar atividade, tempo de uso e presença online.
 */

/**
 * Registra atividade no portal (Entrada ou Heartbeat).
 */
function registrarAtividadePortal(token, tipoAtividade) {
  try {
    var email = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!email) return { success: false, error: "AUTH_REQUIRED" };

    var tipo = tipoAtividade || "HEARTBEAT"; // ENTRADA, HEARTBEAT, SAIDA
    var ss = getSs();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    
    if (wsLog) {
      wsLog.appendRow([new Date(), email, "ACESSO_" + tipo, "Frequência Portal"]);
    }
    
    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Processa os logs para gerar relatório de acessos e tempo.
 * OTIMIZADO: Lê apenas as últimas 2000 linhas e usa cache de 60s.
 */
function getRelatorioEquipe() {
  try {
    // Check Cache first - Updated prefix to v3 to force refresh
    var cacheKey = "TEAM_REPORT_JSON_V3";
    var cached = CacheService.getScriptCache().get(cacheKey);
    if (cached) return JSON.parse(cached);

    var ss = getSs();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    var wsUsuarios = ss.getSheetByName(CONFIG_SISTEMA.ABA_USUARIOS);
    
    if (!wsLog) return { success: false, error: "Aba de logs não encontrada." };
    
    var lastRow = wsLog.getLastRow();
    if (lastRow <= 1) return { success: true, usuarios: [], stats: { online: 0, totalAtivos: 0 } };

    // Busca ampliada para 2000 linhas para garantir cobertura de logs do dia
    var numRows = Math.min(lastRow - 1, 2000);
    var startRow = lastRow - numRows + 1;
    var dataLog = wsLog.getRange(startRow, 1, numRows, 3).getValues();
    
    var dataLimit = new Date();
    dataLimit.setHours(0, 0, 0, 0);
    
    var agora = new Date();
    var mapaUsuarios = {};
    var onlineAgora = 0;
    
    // Mapeia todos os usuários cadastrados para garantir o Nome correto
    var masterNomes = {};
    if (wsUsuarios) {
       var du = wsUsuarios.getDataRange().getValues();
       for(var u=1; u<du.length; u++) {
          var emailU = String(du[u][0]).trim().toLowerCase();
          var nomeU = String(du[u][1]).trim();
          if (emailU) {
             masterNomes[emailU] = nomeU;
             mapaUsuarios[emailU] = { email: emailU, nome: nomeU, primeiroAcesso: null, ultimoAcesso: null, pings: 0, tempoTotalMin: 0, isOnline: false, logs: [] };
          }
       }
    }

    for (var i = dataLog.length - 1; i >= 0; i--) {
      var data = dataLog[i][0];
      if (!(data instanceof Date)) data = new Date(data);
      if (data < dataLimit) continue; 

      var email = String(dataLog[i][1]).toLowerCase().trim();
      var acao = String(dataLog[i][2]);
      
      if (acao.indexOf("ACESSO_") === 0) {
        if (!mapaUsuarios[email]) {
           var nomeFallback = masterNomes[email] || email.split("@")[0].toUpperCase();
           mapaUsuarios[email] = { email: email, nome: nomeFallback, primeiroAcesso: null, ultimoAcesso: null, pings: 0, tempoTotalMin: 0, isOnline: false, logs: [] };
        }
        var user = mapaUsuarios[email];
        user.pings++;
        var timeVal = data.getTime();
        user.logs.push(timeVal);

        if (!user.ultimoAcesso || data > user.ultimoAcesso) user.ultimoAcesso = data;
        if (!user.primeiroAcesso || data < user.primeiroAcesso) user.primeiroAcesso = data;
      }
    }

    var resultado = [];
    for (var key in mapaUsuarios) {
      var u = mapaUsuarios[key];
      if (u.logs && u.logs.length > 0) {
        // Ordena logs cronologicamente para calcular intervalos
        u.logs.sort(function(a, b) { return a - b; });
        
        var totalMs = 0;
        var thresholdMs = 720000; // 12 minutos (2.4x o intervalo de 5min do heartbeat)
        
        for (var l = 1; l < u.logs.length; l++) {
          var gap = u.logs[l] - u.logs[l-1];
          if (gap <= thresholdMs) {
            totalMs += gap;
          }
        }
        
        u.tempoTotalMin = Math.round(totalMs / 60000);
        if (u.tempoTotalMin === 0 && u.pings > 0) u.tempoTotalMin = 1;

        var diffAgora = agora.getTime() - u.ultimoAcesso.getTime();
        if (diffAgora < 720000) { 
           u.isOnline = true;
           onlineAgora++;
        }
      }
      if (u.pings > 0) {
        resultado.push({
           email: u.email, nome: u.nome,
           primeiro: Utilities.formatDate(u.primeiroAcesso, "GMT-3", "HH:mm"),
           ultimo: Utilities.formatDate(u.ultimoAcesso, "GMT-3", "HH:mm"),
           tempo: u.tempoTotalMin, online: u.isOnline, pings: u.pings
        });
      }
    }

    var response = { 
      success: true, 
      usuarios: resultado.sort((a, b) => b.tempo - a.tempo),
      stats: { online: onlineAgora, totalAtivos: resultado.length }
    };

    // Salva em cache por 60 segundos
    CacheService.getScriptCache().put(cacheKey, JSON.stringify(response), 60);

    return response;
  } catch (e) {
    registrarLogSistema("REPORT_ACCESS_ERR", e.message);
    return { success: false, error: e.message };
  }
}

/**
 * Gera um relatório consolidado do MÊS ATUAL lendo a DB_FREQUENCIA + DB_LOGS (Hoje).
 */
function getRelatorioEquipeMensal() {
  try {
    var agora = new Date();
    var cacheKey = "TEAM_MONTHLY_REPORT_V4_" + agora.getMonth() + "_" + agora.getFullYear();
    var cached = CacheService.getScriptCache().get(cacheKey);
    if (cached) return JSON.parse(cached);

    var ss = getSs();
    var wsFreq = ss.getSheetByName("DB_FREQUENCIA");
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    var wsUsuarios = ss.getSheetByName(CONFIG_SISTEMA.ABA_USUARIOS);

    var mapaMensal = {};
    var masterNomes = {};
    if (wsUsuarios) {
       var du = wsUsuarios.getDataRange().getValues();
       for(var u=1; u<du.length; u++) {
          if (du[u][0]) masterNomes[String(du[u][0]).trim().toLowerCase()] = String(du[u][1]).trim();
       }
    }

    // 1. DADOS CONSOLIDADOS (DB_FREQUENCIA)
    if (wsFreq) {
      var dataFreq = wsFreq.getDataRange().getValues();
      var mesAtual = String(agora.getMonth() + 1).padStart(2, '0');
      var anoAtual = String(agora.getFullYear());
      var filtroMesAno = "/" + mesAtual + "/" + anoAtual;

      for (var i = 1; i < dataFreq.length; i++) {
         var dtRaw = dataFreq[i][0];
         var dtStr = (dtRaw instanceof Date) ? Utilities.formatDate(dtRaw, "GMT-3", "dd/MM/yyyy") : String(dtRaw);
         if (dtStr.indexOf(filtroMesAno) > -1) {
            var email = String(dataFreq[i][1]).toLowerCase().trim();
            var min = parseInt(dataFreq[i][3]) || 0;
            if (!mapaMensal[email]) {
               mapaMensal[email] = { totalMin: 0, dias: 0, nome: masterNomes[email] || dataFreq[i][2] };
            }
            mapaMensal[email].totalMin += min;
            mapaMensal[email].dias++;
         }
      }
    }

    // 2. DADOS DE HOJE (DB_LOGS)
    if (wsLog) {
      var dataLog = wsLog.getDataRange().getValues();
      var hojeLimit = new Date();
      hojeLimit.setHours(0,0,0,0);
      var pingsHoje = {};

      var maxL = Math.min(dataLog.length - 1, 2000);
      for (var j = dataLog.length - 1; j >= dataLog.length - maxL; j--) {
         if (!dataLog[j]) continue;
         var dataLogD = dataLog[j][0];
         if (!(dataLogD instanceof Date)) dataLogD = new Date(dataLogD);
         if (dataLogD < hojeLimit) continue; 

         var acaoLog = String(dataLog[j][2]);
         if (acaoLog.indexOf("ACESSO_") === 0) {
            var em = String(dataLog[j][1]).toLowerCase().trim();
            if (!pingsHoje[em]) pingsHoje[em] = [];
            pingsHoje[em].push(dataLogD.getTime());
         }
      }

      var thresholdMs = 720000;
      for (var userHoje in pingsHoje) {
         var pingsUser = pingsHoje[userHoje].sort(function(a,b){return a-b;});
         var msHoje = 0;
         for (var k = 1; k < pingsUser.length; k++) {
            var diff = pingsUser[k] - pingsUser[k-1];
            if (diff <= thresholdMs) msHoje += diff;
         }
         var minHoje = Math.round(msHoje / 60000);
         if (minHoje === 0 && pingsUser.length > 0) minHoje = 1;

         if (!mapaMensal[userHoje]) {
            mapaMensal[userHoje] = { totalMin: 0, dias: 0, nome: masterNomes[userHoje] || userHoje.split("@")[0].toUpperCase() };
         }
         mapaMensal[userHoje].totalMin += minHoje;
         mapaMensal[userHoje].dias++;
      }
    }

    var resultado = [];
    for (var emailMap in mapaMensal) {
        var u = mapaMensal[emailMap];
        resultado.push({
            email: emailMap,
            nome: u.nome,
            tempoTotal: u.totalMin,
            dias: u.dias,
            mediaDiaria: u.dias > 0 ? Math.round(u.totalMin / u.dias) : 0
        });
    }

    var response = { 
      success: true, 
      usuarios: resultado.sort((a, b) => b.tempoTotal - a.tempoTotal),
      mesFmt: Utilities.formatDate(agora, "GMT-3", "MMMM/yyyy")
    };

    CacheService.getScriptCache().put(cacheKey, JSON.stringify(response), 1800);
    return response;

  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * 🧹 Consolida os acessos do dia anterior, salva em DB_FREQUENCIA e limpa os logs
 */
function consolidarFrequenciaDiaria() {
  try {
    var ss = getSs();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    var wsFreq = ss.getSheetByName("DB_FREQUENCIA");
    
    // Cria a aba se não existir
    if (!wsFreq) {
      wsFreq = ss.insertSheet("DB_FREQUENCIA");
      wsFreq.appendRow(["DATA", "EMAIL", "NOME", "TEMPO_MINUTOS", "PINGS"]);
      wsFreq.getRange(1, 1, 1, 5).setBackground("#1C3051").setFontColor("white").setFontWeight("bold").setHorizontalAlignment("center");
      wsFreq.setFrozenRows(1);
    }
    
    if (!wsLog) return;
    
    var dataLog = wsLog.getDataRange().getValues();
    if (dataLog.length <= 1) return;
    
    var limite = new Date();
    limite.setHours(0, 0, 0, 0); // Tudo antes de HOJE (00:00) será consolidado
    
    var masterNomes = {};
    var wsUsuarios = ss.getSheetByName(CONFIG_SISTEMA.ABA_USUARIOS);
    if (wsUsuarios) {
       var du = wsUsuarios.getDataRange().getValues();
       for(var u=1; u<du.length; u++) {
          if (du[u][0]) masterNomes[String(du[u][0]).trim().toLowerCase()] = String(du[u][1]).trim();
       }
    }

    var mapa = {}; 
    var linhasManter = [dataLog[0]]; // Mantém o Cabeçalho

    for (var i = 1; i < dataLog.length; i++) {
       var data = dataLog[i][0];
       if (!(data instanceof Date)) data = new Date(data);
       var acao = String(dataLog[i][2]);

       if (data < limite && acao.indexOf("ACESSO_") === 0) {
          var email = String(dataLog[i][1]).toLowerCase().trim();
          if (!mapa[email]) mapa[email] = [];
          mapa[email].push(data.getTime());
       } else {
          // Mantém logs de HOJE ou logs vitais de negócio (ARCHIVE, SEND, etc)
          if (acao.indexOf("ACESSO_") === 0 && data < limite) {
             // Descarta (já foi pro mapa)
          } else {
             linhasManter.push(dataLog[i]);
          }
       }
    }

    // Grava consolidação do dia anterior
    var registrosFreq = [];
    var ontem = new Date();
    ontem.setDate(ontem.getDate() - 1);
    var dataStr = Utilities.formatDate(ontem, "GMT-3", "dd/MM/yyyy");

    for (var em in mapa) {
       var logsUser = mapa[em].sort(function(a,b){return a-b;});
       var totalMs = 0;
       var thresholdMs = 720000;
       for (var l = 1; l < logsUser.length; l++) {
          var gap = logsUser[l] - logsUser[l-1];
          if (gap <= thresholdMs) totalMs += gap;
       }
       var minDia = Math.round(totalMs / 60000);
       if (minDia === 0 && logsUser.length > 0) minDia = 1;
       
       var nome = masterNomes[em] || em.split("@")[0].toUpperCase();
       registrosFreq.push([dataStr, em, nome, minDia, logsUser.length]);
    }

    if (registrosFreq.length > 0) {
       wsFreq.getRange(wsFreq.getLastRow() + 1, 1, registrosFreq.length, 5).setValues(registrosFreq);
    }

    // Repõe DB_LOGS apenas com o residual (Hoje + Negócios)
    wsLog.clearContents();
    if (linhasManter.length > 0) {
       wsLog.getRange(1, 1, linhasManter.length, linhasManter[0].length).setValues(linhasManter);
    }

    SpreadsheetApp.flush();
    registrarLogSistema("SYSTEM_MAINTENANCE", "Consolidação D-1: " + registrosFreq.length + " usuários (" + dataStr + ")");
    
  } catch(e) {
    registrarLogSistema("CONSOLIDATE_ERR", e.message);
  }
}

/**
 * ⏰ Instala o gatilho para a consolidação noturna (DB_FREQUENCIA).
 */
function instalarGatilhoConsolidacaoDiaria() {
  var nomeFuncao = 'consolidarFrequenciaDiaria';
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === nomeFuncao) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  ScriptApp.newTrigger(nomeFuncao)
    .timeBased()
    .everyDays(1)
    .atHour(2) // Rodar às 02:00 AM
    .create();
    
  registrarLogSistema("TRIGGER_INSTALLED", "Gatilho de consolidação D-1 ativado.");
  return "✅ Automação de Frequência ativada (Diário às 02:00h).";
}
