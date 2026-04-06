/**
 * ReadLogs.js | Leitor de Logs do Sistema
 * Responsável por retornar registros de DB_LOGS para o portal web.
 */

function readRecentLogs() {
  var ss = getSs();
  var wsLogs = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
  if (!wsLogs) {
    console.log("Aba DB_LOGS não encontrada.");
    return;
  }
  var data = wsLogs.getDataRange().getValues();
  console.log("--- ÚLTIMOS 20 LOGS ---");
  var startRow = Math.max(1, data.length - 20);
  for (var i = startRow; i < data.length; i++) {
    console.log(JSON.stringify(data[i]));
  }
}

/**
 * Retorna todos os logs do sistema para o portal web (Admin only).
 * Colunas DB_LOGS: A=DATA | B=USUARIO | C=ACAO | D=DETALHE
 * Retorna em ordem reversa (do mais recente para o mais antigo).
 */
function getDadosLogsWeb(token) {
  try {
    // Validação de segurança: apenas ADMIN pode acessar
    var ss = getSs();
    var wsUsers = ss.getSheetByName(CONFIG_SISTEMA.ABA_USUARIOS);
    var userEmail = "";
    var userLevel = "";

    if (token) {
      try {
        var payload = JSON.parse(Utilities.newBlob(Utilities.base64Decode(token.split('.')[1])).getDataAsString());
        userEmail = (payload.email || "").toLowerCase();
      } catch(e) {}
    }

    if (userEmail && wsUsers) {
      var usersData = wsUsers.getDataRange().getValues();
      for (var u = 1; u < usersData.length; u++) {
        if (String(usersData[u][0]).toLowerCase().trim() === userEmail) {
          userLevel = String(usersData[u][2]).toUpperCase().trim();
          break;
        }
      }
    }

    if (userLevel !== "ADMIN") {
      return { success: false, error: "Acesso restrito ao administrador." };
    }

    var wsLogs = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    if (!wsLogs) {
      return { success: false, error: "Aba DB_LOGS não encontrada." };
    }

    var data = wsLogs.getDataRange().getValues();
    if (data.length <= 1) {
      return { success: true, data: [] };
    }

    // Pula o cabeçalho (linha 0), converte e reverte a ordem
    var logs = [];
    for (var i = 1; i < data.length; i++) {
      var dataRaw = data[i][0];
      var dataFormatada = "";
      if (dataRaw instanceof Date) {
        dataFormatada = Utilities.formatDate(dataRaw, Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm:ss");
      } else {
        dataFormatada = String(dataRaw);
      }

      logs.push({
        data: dataFormatada,
        usuario: String(data[i][1] || ""),
        acao: String(data[i][2] || ""),
        detalhe: String(data[i][3] || "")
      });
    }

    logs.reverse(); // Último para o primeiro

    return { success: true, data: logs };

  } catch (e) {
    return { success: false, error: e.message };
  }
}
