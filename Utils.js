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
 * Verifica se um e-mail está contido em uma string de responsáveis (suporta lista separada por vírgula).
 * @param {string} responsavelStr Conteúdo da coluna RESPONSAVEL
 * @param {string} emailUsuario E-mail do usuário logado
 * @returns {boolean}
 */
function isUserResponsible(responsavelStr, emailUsuario) {
  if (!responsavelStr || !emailUsuario) return false;
  var target = emailUsuario.toLowerCase().trim();
  var parts = String(responsavelStr).toLowerCase().split(',');
  for (var i = 0; i < parts.length; i++) {
    if (parts[i].trim() === target) return true;
  }
  return false;
}

/**
 * Ponto de acesso resiliente à planilha (Redundância para gatilhos).
 */
function getSs() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (ss) return ss;
  } catch (e) {
    console.warn("Acesso ativo indisponível. Usando openById.");
  }
  return SpreadsheetApp.openById(CONFIG_SISTEMA.ID_PLANILHA);
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

function adicionarDiasUteis(dataInicial, qtdDiasUteis) {
  var data = new Date(dataInicial.getTime());
  var diasAdicionados = 0;
  
  if (qtdDiasUteis === 0) {
    while (!isDiaUtil(data)) {
      data.setDate(data.getDate() + 1);
    }
    return data;
  }
  
  while (diasAdicionados < qtdDiasUteis) {
    data.setDate(data.getDate() + 1);
    if (isDiaUtil(data)) {
      diasAdicionados++;
    }
  }
  return data;
}

/**
 * Validador JWT do Google Identity Services (GIS).
 * Comprova a assinatura via API e extrai o e-mail verificado.
 * @param {string} token 
 * @returns {string|null} email verificado
 */
function validarTokenGIS(token) {
  if (!token) return null;
  token = String(token).trim();
  
  var parts = token.split('.');
  if (parts.length !== 3 || !token.startsWith("ey")) return null;
  
  // OTIMIZAÇÃO: Cache de Token para evitar chamadas excessivas ao Google Auth API
  var cacheKey = "GIS_" + Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, token).map(b => (b < 0 ? b + 256 : b).toString(16).padStart(2, '0')).join('');
  var cachedEmail = CacheService.getScriptCache().get(cacheKey);
  if (cachedEmail) return cachedEmail;

  try {
    var response = UrlFetchApp.fetch("https://www.googleapis.com/oauth2/v3/tokeninfo?id_token=" + encodeURIComponent(token), {
       muteHttpExceptions: true
    });
    
    var respCode = response.getResponseCode();
    if (respCode === 200) {
       var payload = JSON.parse(response.getContentText());
       if (payload && payload.email && (payload.email_verified === true || payload.email_verified === "true")) {
           var email = String(payload.email).toLowerCase().trim();
           CacheService.getScriptCache().put(cacheKey, email, 1800); // 30 minutos de cache
           return email;
       }
    }
  } catch (e) {
    registrarLogSistema("GIS_VALIDATION_FATAL", e.message);
  }
  return null;
}

function isDiaUtil(data) {
  var dow = data.getDay();
  if (dow === 0 || dow === 6) return false; 
  var diaMes = Utilities.formatDate(data, "GMT-3", "dd/MM");
  return CONFIG_SISTEMA.FERIADOS.indexOf(diaMes) === -1;
}

function registrarLogSistema(acao, detalhe) {
  try {
    var ss = getSs();
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
function registrarProtocoloDB(clienteNome, protocolo, idTarefa, obrigacao, emailCli, linksDrive, vctoLegal, acaoTarefa) {
  try {
    var ss = getSs();
    var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
    if (!wsProt) return;

    // A = DATA | B = CLIENTE | C = PROTOCOLO | D = ID_TAREFA | E = OBRIGACAO | F = EMAIL | G = RESPONSAVEL | H = LINKS | I = STATUS_ENVIO | J = CONF_RECTO | K = VCTO_LEGAL | L = ACAO
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
      "",                      // J: CONF_RECTO (Vazio inicialmente)
      vctoLegal || "",         // K: VCTO_LEGAL
      acaoTarefa || ""         // L: ACAO_TAREFA
    ]);
    
    SpreadsheetApp.flush();
    return wsProt.getLastRow(); // Retorna o index da linha para rastreio direto
  } catch(e) {
    registrarLogSistema("PROTO_SAVE_ERR", e.message);
    return null;
  }
}

/**
 * Extrai texto de um PDF ou Imagem usando OCR do Google Drive.
 * REQUER: Serviço Avançado 'Drive' ativado.
 */
function extrairTextoOCR(blob) {
  try {
    var resource = {
      title: "OCR_TEMP_" + new Date().getTime(),
      mimeType: blob.getContentType()
    };
    
    // Insere o arquivo no Drive com OCR ativado (Gera um Google Doc temporário)
    var tempFile = Drive.Files.insert(resource, blob, { ocr: true, ocrLanguage: "pt" });
    
    // Abre o documento gerado e lê o texto
    var doc = DocumentApp.openById(tempFile.id);
    var text = doc.getBody().getText();
    
    // Deleta o arquivo temporário imediatamente
    Drive.Files.remove(tempFile.id);
    
    return text;
  } catch (e) {
    registrarLogSistema("OCR_ERROR", e.message);
    return "";
  }
}

/**
 * Busca o CNPJ do cliente na aba DB_CLIENTES (Coluna C)
 */
function obterCnpjCliente(clienteNome) {
  try {
    var ss = getSs();
    var ws = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
    if (!ws) return "";
    
    var data = ws.getDataRange().getValues();
    var nomeNorm = norm(clienteNome);
    
    for (var i = 1; i < data.length; i++) {
      if (norm(data[i][1]) === nomeNorm) {
        return String(data[i][2] || "").replace(/\D/g, ""); // Apenas números
      }
    }
  } catch (e) {
    registrarLogSistema("GET_CNPJ_ERR", e.message);
  }
  return "";
}

/**
 * Limpa o texto do OCR para comparação de dados sensíveis (CNPJ, valores).
 * Trata erros comuns de reconhecimento (ex: O -> 0, I -> 1).
 */
function limparTextoOcrParaComparacao(texto) {
  if (!texto) return "";
  return String(texto).toUpperCase()
    .replace(/O/g, "0")
    .replace(/[IL|]/g, "1")
    .replace(/S/g, "5")
    .replace(/B/g, "8")
    .replace(/\D/g, ""); // Remove tudo que não for dígito após a normalização
}