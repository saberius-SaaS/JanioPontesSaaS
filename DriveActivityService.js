/**
 * 🛰️ MOTOR DE ATIVIDADE DRIVE (Drive Activity API) v127.6
 * Evolução: Controle de Cota (Rate Limit), Throttle e Timeout Elegante.
 */
function sincronizarProvasDeEntregaAPI() {
  var startTime = new Date().getTime();
  var MAX_EXECUTION_TIME = 1000 * 60 * 4; // 4 minutos de limite de segurança
  var MAX_API_CALLS = 45; // Limite rígido por execução para não estourar a cota (45 arquivos/hora = 1.080/dia)
  var apiCallsCount = 0;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  if (!wsProt) return 0;

  var dataProt = wsProt.getDataRange().getValues();
  var atualizacoes = 0;
  var emailDono = Session.getEffectiveUser().getEmail().toLowerCase();
  
  // Lê os últimos 300 protocolos para economizar memória
  var startRow = Math.max(1, dataProt.length - 300);

  for (var i = startRow; i < dataProt.length; i++) {
    // Válvula de Segurança 1: Tempo limite
    if (new Date().getTime() - startTime > MAX_EXECUTION_TIME) {
      registrarLogSistema("SYNC_DRIVE_PAUSED", "Timeout de segurança atingido. Continua na próxima hora.");
      break;
    }
    // Válvula de Segurança 2: Cota de API atingida
    if (apiCallsCount >= MAX_API_CALLS) {
      registrarLogSistema("SYNC_DRIVE_PAUSED", "Limite de API (" + MAX_API_CALLS + ") atingido neste ciclo.");
      break;
    }

    var linksBrutos = String(dataProt[i][7]); // Coluna H (LINK_DRIVE)
    var protocolo = String(dataProt[i][2]); 
    var dataConfirmacao = dataProt[i][9]; // Coluna J (CONF_RECTO)

    if (!dataConfirmacao || dataConfirmacao === "" || dataConfirmacao === "AGUARDANDO") {
      var linksArray = linksBrutos.split("|").map(l => l.trim());
      var provaEncontrada = null;

      for (var j = 0; j < linksArray.length; j++) {
        var fileId = extrairIdDoLink(linksArray[j]);
        if (!fileId) continue;

        try {
          var request = { itemName: "items/" + fileId, pageSize: 10 };
          
          // Incrementa contador e aplica o "Respiro" para não assustar o servidor do Google
          apiCallsCount++;
          Utilities.sleep(700); 

          var response = DriveActivity.Activity.query(request);
          
          if (response.activities) {
            for (var k = 0; k < response.activities.length; k++) {
              var act = response.activities[k];
              var isView = act.primaryActionDetail && act.primaryActionDetail.view;
              
              if (isView) {
                var atores = act.actors || [];
                var visualizadoPorTerceiro = atores.some(function(ator) {
                  var emailAtor = (ator.user && ator.user.knownUser && ator.user.knownUser.personName) ? ator.user.knownUser.personName.replace("people/", "") : "";
                  return emailAtor !== emailDono; 
                });
                if (visualizadoPorTerceiro || atores.length > 0) {
                  provaEncontrada = act.timestamp || new Date();
                  break;
                }
              }
            }
          }
        } catch (e) { 
          console.warn("Erro no arquivo " + fileId + ": " + e.message);
          
          // Válvula de Segurança 3: Se o Google der bloqueio de cota antecipado (Erro 429), aborta imediatamente
          if (e.message.indexOf("Rate Limit") > -1 || e.message.indexOf("exceeded") > -1) {
             registrarLogSistema("SYNC_DRIVE_QUOTA", "Cota estourada prematuramente pelo Google. Abortando loop.");
             return atualizacoes;
          }
        }
        if (provaEncontrada) break;
      }

      if (provaEncontrada) {
        wsProt.getRange(i + 1, 10).setValue(provaEncontrada); // Coluna J
        wsProt.getRange(i + 1, 9).setValue(CONFIG_SISTEMA.STATUS.ENTREGUE); // Coluna I
        atualizacoes++;
        
        try {
          // Usa a função de baixa do sistema caso ela exista no escopo global
          if (typeof marcarComoEntregueNasTasksEHistorico === "function") {
             marcarComoEntregueNasTasksEHistorico(protocolo);
          } else if (typeof registrarInteracaoEmail === "function") {
             registrarInteracaoEmail(protocolo, "DRIVE_ACTIVITY", i + 1);
          }
        } catch(err) {
          console.warn("Falha ao propagar status: " + err.message);
        }
      }
    }
  }
  return atualizacoes;
}

function extrairIdDoLink(url) {
  var match = url.match(/[-\w]{25,}/);
  return match ? match[0] : null;
}