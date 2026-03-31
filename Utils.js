/**
 * 🛠️ UTILITÁRIOS E FERRAMENTAS GLOBAIS v131.00
 */

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function norm(str) {
  if (!str) return "";
  return String(str).normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toUpperCase();
}

/**
 * Verifica se uma regra deve ser aplicada ao cliente baseado em Tags (Whitelist)
 * @param {String} tagsClienteStr Tags do cliente (Coluna O da DB_CLIENTES)
 * @param {String} gruposRegraStr Grupos da regra (Coluna L da DB_REGRAS)
 * @return {Boolean}
 */
function verificarAcessoPorTag(tagsClienteStr, gruposRegraStr) {
  var gruposRegra = String(gruposRegraStr || "").split(',').map(t => norm(t)).filter(t => t !== "");
  
  // Se a regra for GLOBAL ou TODOS, ela passa direto (respeitando apenas Regime/Exceção)
  if (gruposRegra.indexOf("GLOBAL") > -1 || gruposRegra.indexOf("TODOS") > -1) return true;
  
  // Se a regra não tem grupo definido, ela não é gerada para ninguém (segurança)
  if (gruposRegra.length === 0) return false;

  var tagsCliente = String(tagsClienteStr || "").split(',').map(t => norm(t)).filter(t => t !== "");
  
  // Verifica se existe pelo menos uma tag em comum (Interseção)
  return gruposRegra.some(grupo => tagsCliente.indexOf(grupo) > -1);
}

function calcularDataComplexa(competenciaDate, regraDia, mesesDesloca, antecipaFds) {
  try {
    if (!competenciaDate || isNaN(competenciaDate.getTime())) {
      competenciaDate = new Date();
      competenciaDate.setDate(1);
    }
    var deslocaInt = parseInt(mesesDesloca) || 0;
    var anoDestino = competenciaDate.getFullYear();
    var mesDestino = competenciaDate.getMonth() + deslocaInt;
    var dataBase = new Date(anoDestino, mesDestino, 1);
    var ano = dataBase.getFullYear();
    var mes = dataBase.getMonth();
    var diaRaw = String(regraDia || "").toUpperCase().trim();
    if (diaRaw === "") return null;
    var dataFinal;
    if (diaRaw.indexOf("U") > -1) {
      var nDiaUtil = parseInt(diaRaw.replace("U", "")) || 1;
      dataFinal = obterEnesimoDiaUtil(ano, mes, nDiaUtil);
    } else {
      var diaFixo = parseInt(diaRaw) || 1;
      dataFinal = new Date(ano, mes, diaFixo);
      if (norm(antecipaFds) === "S") {
        var dow = dataFinal.getDay();
        if (dow === 0) dataFinal.setDate(dataFinal.getDate() - 2); 
        else if (dow === 6) dataFinal.setDate(dataFinal.getDate() - 1); 
      }
    }
    return (dataFinal && !isNaN(dataFinal.getTime())) ? dataFinal : null;
  } catch (e) { return null; }
}

function obterEnesimoDiaUtil(ano, mes, n) {
  var count = 0;
  var data = new Date(ano, mes, 1);
  while (data.getMonth() === mes) {
    if (isDiaUtil(data)) {
      count++;
      if (count === n) return new Date(data);
    }
    data.setDate(data.getDate() + 1);
  }
  data.setDate(data.getDate() - 1);
  while (!isDiaUtil(data) && data.getDate() > 1) { data.setDate(data.getDate() - 1); }
  return data;
}

function isDiaUtil(data) {
  var dow = data.getDay();
  if (dow === 0 || dow === 6) return false; 
  var diaMes = Utilities.formatDate(data, "GMT-3", "dd/MM");
  return CONFIG_SISTEMA.FERIADOS.indexOf(diaMes) === -1;
}

function registrarLogSistema(acao, detalhe) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsLog = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
    if (wsLog) wsLog.appendRow([new Date(), Session.getActiveUser().getEmail() || "SISTEMA", acao, detalhe]);
  } catch (e) {}
}

function gerarProtocoloEntrega() {
  return "PRT" + new Date().getTime() + Math.floor(Math.random() * 100);
}

/**
 * Registra a entrega de documento na aba DB_PROTOCOLOS
 */
function registrarProtocoloDB(clienteNome, protocolo, idTarefa, obrigacao, emailCli, linksDrive) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
    if (!wsProt) return;

    // A = DATA | B = CLIENTE | C = PROTOCOLO | D = ID_TAREFA | E = OBRIGACAO | F = EMAIL | G = RESPONSAVEL | H = LINKS | I = STATUS_ENVIO | J = CONF_RECTO
    var hoje = new Date();
    var responsavel = Session.getActiveUser().getEmail() || "SISTEMA";
    
    wsProt.appendRow([
      hoje,                    // A: DATA
      clienteNome,             // B: CLIENTE
      protocolo,               // C: PROTOCOLO
      idTarefa,                // D: ID_TAREFA
      obrigacao,               // E: OBRIGACAO
      emailCli || "-",         // F: EMAIL
      responsavel,             // G: RESPONSAVEL
      linksDrive || "-",       // H: LINK_ARQUIVO
      "ENVIADO",               // I: STATUS_ENVIO
      ""                       // J: CONF_RECTO (Vazio inicialmente)
    ]);
    
    SpreadsheetApp.flush();
    return wsProt.getLastRow(); // Retorna o index da linha para rastreio direto
  } catch(e) {
    registrarLogSistema("PROTO_SAVE_ERR", e.message);
    return null;
  }
}