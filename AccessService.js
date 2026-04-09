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
    // Check Cache first
    var cacheKey = "TEAM_REPORT_JSON";
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
    
    if (wsUsuarios) {
       var du = wsUsuarios.getDataRange().getValues();
       for(var u=1; u<du.length; u++) {
          var emailU = String(du[u][0]).trim().toLowerCase();
          if (emailU) {
             mapaUsuarios[emailU] = { email: emailU, nome: String(du[u][1]), primeiroAcesso: null, ultimoAcesso: null, pings: 0, tempoTotalMin: 0, isOnline: false };
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
           mapaUsuarios[email] = { email: email, nome: email.split("@")[0].toUpperCase(), primeiroAcesso: null, ultimoAcesso: null, pings: 0, tempoTotalMin: 0, isOnline: false };
        }
        var user = mapaUsuarios[email];
        user.pings++;
        if (!user.ultimoAcesso || data > user.ultimoAcesso) user.ultimoAcesso = data;
        if (!user.primeiroAcesso || data < user.primeiroAcesso) user.primeiroAcesso = data;
      }
    }

    var resultado = [];
    for (var key in mapaUsuarios) {
      var u = mapaUsuarios[key];
      if (u.primeiroAcesso && u.ultimoAcesso) {
        var duracaoMs = u.ultimoAcesso.getTime() - u.primeiroAcesso.getTime();
        u.tempoTotalMin = Math.round(duracaoMs / 60000);
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
 * Gera um relatório consolidado do MÊS ATUAL.
 * OTIMIZADO: Busca o início do mês na planilha e agrega por usuário.
 */
function getRelatorioEquipeMensal() {
  try {
    var agora = new Date();
    var cacheKey = "TEAM_MONTHLY_REPORT_" + agora.getMonth() + "_" + agora.getFullYear();
    var cached = CacheService.getScriptCache().get(cacheKey);
    if (cached) return JSON.parse(cached);

    var ss = getSs();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    if (!wsLog) return { success: false, error: "Aba de logs não encontrada." };

    var lastRow = wsLog.getLastRow();
    if (lastRow <= 1) return { success: true, usuarios: [] };

    // Define o limite: Início do mês atual
    var dataLimite = new Date();
    dataLimite.setDate(1);
    dataLimite.setHours(0, 0, 0, 0);

    // Busca ampliada para 5000 linhas para o Mês
    var numRows = Math.min(lastRow - 1, 5000);
    var startRow = lastRow - numRows + 1;
    var dataLog = wsLog.getRange(startRow, 1, numRows, 3).getValues();

    var mapaMensal = {};
    
    for (var i = 0; i < dataLog.length; i++) {
        var data = dataLog[i][0];
        if (!(data instanceof Date)) data = new Date(data);
        if (data < dataLimite) continue;

        var email = String(dataLog[i][1]).toLowerCase().trim();
        var acao = String(dataLog[i][2]);
        if (acao.indexOf("ACESSO_") !== 0) continue;

        var diaKey = Utilities.formatDate(data, "GMT-3", "yyyy-MM-dd");
        
        if (!mapaMensal[email]) mapaMensal[email] = { totalMin: 0, diasAtivos: {}, nome: email.split("@")[0].toUpperCase() };
        if (!mapaMensal[email].diasAtivos[diaKey]) mapaMensal[email].diasAtivos[diaKey] = { min: data, max: data };
        
        var dia = mapaMensal[email].diasAtivos[diaKey];
        if (data < dia.min) dia.min = data;
        if (data > dia.max) dia.max = data;
    }

    var resultado = [];
    for (var email in mapaMensal) {
        var user = mapaMensal[email];
        var totalMin = 0;
        var qtdDias = 0;

        for (var d in user.diasAtivos) {
            var diff = user.diasAtivos[d].max.getTime() - user.diasAtivos[d].min.getTime();
            var minDia = Math.round(diff / 60000);
            totalMin += (minDia === 0 ? 1 : minDia); 
            qtdDias++;
        }

        resultado.push({
            email: email,
            nome: user.nome,
            tempoTotal: totalMin,
            dias: qtdDias,
            mediaDiaria: Math.round(totalMin / qtdDias)
        });
    }

    var response = { 
      success: true, 
      usuarios: resultado.sort((a, b) => b.tempoTotal - a.tempoTotal),
      mesFmt: Utilities.formatDate(dataLimite, "GMT-3", "MMMM/yyyy")
    };

    CacheService.getScriptCache().put(cacheKey, JSON.stringify(response), 3600); // 1 hora de cache
    return response;

  } catch (e) {
    return { success: false, error: e.message };
  }
}
