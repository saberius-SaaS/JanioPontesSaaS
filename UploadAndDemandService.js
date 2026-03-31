/**
 * 🚀 UPLOAD & DEMAND SERVICE v131.13
 * FOCO: Estabilidade total no Bypass de Permissão e Identidade DriveApp.
 */

function processarUploadBatchInterno(arquivos, taskId, clienteNome) {
  var lock = LockService.getScriptLock();
  try { 
    lock.waitLock(25000); 
  } catch(e) { 
    throw new Error("Sistema ocupado. Tente novamente."); 
  }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
    
    registrarLogSistema("UPLOAD_START", "Recebidos: " + (arquivos ? arquivos.length : 0) + " arquivos para tarefa " + taskId);
    
    // Localização da Tarefa
    // Localização da Tarefa
    var dataTf = wsTarefas.getRange(1, 10, wsTarefas.getLastRow(), 1).getValues(); 
    var rowIdx = -1;
    for(var i=1; i<dataTf.length; i++) if(String(dataTf[i][0]) === String(taskId)) { rowIdx = i + 1; break; }
    if(rowIdx === -1) throw new Error("ID da tarefa não localizado.");
    
    var rowVal = wsTarefas.getRange(rowIdx, 1, 1, 12).getValues()[0];
    var obrig = rowVal[2];
    var mesRef = rowVal[0] instanceof Date ? Utilities.formatDate(rowVal[0], "GMT-3", "MM/yyyy") : String(rowVal[0]);
    
    // Localização do Cliente
    var dadosC = wsCli.getDataRange().getValues();
    var emailCli = "", cnpj = "", pastaId = "", nomeResp = "";
    var cliRowIdx = -1;
    for(var i=1; i<dadosC.length; i++) {
      if(norm(dadosC[i][1]) === norm(clienteNome)) { 
        cnpj = String(dadosC[i][2]).replace(/[^0-9]/g, "");
        nomeResp = dadosC[i][3]; // Coluna D: RESPONSAVEL
        emailCli = dadosC[i][4]; // Coluna E: EMAIL
        var urlM = String(dadosC[i][12]);
        if (urlM.indexOf("id=") > -1) pastaId = urlM.split("id=")[1];
        else if (urlM.indexOf("folders/") > -1) pastaId = urlM.split("folders/")[1].split("?")[0];
        cliRowIdx = i + 1;
        break;
      }
    }
    
    // Gestão de Pasta com Privilégios Elevados
    var target = null;
    if (pastaId) {
       try { 
         target = DriveApp.getFolderById(pastaId);
       } catch(err) { target = null; }
    }
    
    if (!target) {
       var root = DriveApp.getFolderById(CONFIG_SISTEMA.PASTAS.CLIENTES_DIGITAL);
       var pastas = root.getFoldersByName(clienteNome);
       target = pastas.hasNext() ? pastas.next() : root.createFolder(clienteNome);
       if (cliRowIdx !== -1) wsCli.getRange(cliRowIdx, 13).setValue(target.getUrl());
    }
    
    var protocolo = gerarProtocoloEntrega();
    var linksParaEmail = [];
    var folderGlobal = DriveApp.getFolderById(CONFIG_SISTEMA.PASTAS.ENVIADOS);
    
    // Processamento de Arquivos
    arquivos.forEach(function(f, idx) {
      var nomeOriginal = f.name;
      var ext = nomeOriginal.split('.').pop();
      var nomeObrig = norm(obrig).replace(/\s+/g, "_"); 
      var marcadorProtocolo = "_[" + protocolo + "]";
      var sufixoMultiplo = (arquivos.length > 1 ? "_" + (idx+1) : "");
      var novoNome = cnpj + "." + nomeObrig + "." + mesRef.replace(/\//g, ".") + sufixoMultiplo + marcadorProtocolo + "." + ext;
      
      var blob = Utilities.newBlob(Utilities.base64Decode(f.base64), "application/octet-stream", novoNome);
      
      // Criar e Copiar (Garante acesso ao Admin e ao Usuário)
      var fileClient = target.createFile(blob);
      fileClient.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      fileClient.makeCopy(novoNome, folderGlobal);
      
      var url = fileClient.getUrl();
      linksParaEmail.push({ url: url, name: nomeOriginal });
    });

    var linksDriveStr = linksParaEmail.map(function(item) { return item.url; }).join(" | ");
    
    // --- INTEGRAÇÃO BLOCO AUDITORIA ---
    var acaoTarefa = rowVal[7];
    var statusFinal = getSafeStatus("ENTREGUE");
    var resAudit = null;

    if (norm(acaoTarefa) === CONFIG_SISTEMA.ACOES.AUDITAR) {
      if (!arquivos || arquivos.length === 0) {
        throw new Error("Arquivo obrigatório para auditoria não foi enviado.");
      }
      registrarLogSistema("AUDIT_START", "Iniciando auditoria para " + clienteNome);
      var fAudit = arquivos[0];
      var blobAudit = Utilities.newBlob(Utilities.base64Decode(fAudit.base64), "application/octet-stream", fAudit.name);
      var nomeObrigAudit = norm(obrig).replace(/\s+/g, "_");
      var extAudit = fAudit.name.split('.').pop();
      var novoNomeAudit = cnpj + "." + nomeObrigAudit + "." + mesRef.replace(/\//g, ".") + "." + extAudit;
      
      try {
        resAudit = processarAuditoriaBalancete(blobAudit, taskId, clienteNome, cnpj, novoNomeAudit);
        if (!resAudit.aprovado) {
          wsTarefas.getRange(rowIdx, 6).setValue(getSafeStatus("PENDENTE"));
          invalidarCacheSistema();
          return JSON.stringify({ success: false, audit: false, message: "REPROVADO: " + resAudit.erros.join(" | ") });
        }
      } catch(eAudit) {
        registrarLogSistema("AUDIT_FAIL_SYS", eAudit.message);
        throw new Error("Erro no motor de auditoria: " + eAudit.message);
      }
    }
    // --- FIM BLOCO AUDITORIA ---

    var protRowIdx = registrarProtocoloDB(clienteNome, protocolo, taskId, obrig, emailCli, linksDriveStr);
    wsTarefas.getRange(rowIdx, 6, 1, 2).setValues([[statusFinal, protocolo]]);
    
    acionarWorkflowFaseSeguinte(taskId, rowIdx);
    reordenarTarefasElite(); 
    invalidarCacheSistema(); 
 
    try {
      // Se não for auditoria (ex: envio comum), manda a notificação genérica "Processado com sucesso"
      if (norm(acaoTarefa) !== CONFIG_SISTEMA.ACOES.AUDITAR) {
        // Caso seja ARQUIVAR sem arquivos, não envia e-mail ao cliente (Finalização Simples Interna)
        var deveNotificar = (norm(acaoTarefa) !== CONFIG_SISTEMA.ACOES.ARQUIVAR) || (arquivos && arquivos.length > 0);
        if (deveNotificar) {
          // Passamos o protRowIdx em vez do rowIdx da tarefa para rastreio direto no DB_PROTOCOLOS
          notificarEntregaClienteRefatorada(clienteNome, obrig, protocolo, emailCli, linksParaEmail, target.getUrl(), protRowIdx || "", false);
        }
      }
      
      var dispararEmailVIP = false;
      var backgroundPayload = null;
      
      // Se houve auditoria aprovada, PREPARA o Relatório IA por E-mail APENAS se cliente for VIP
      if (resAudit && resAudit.dadosAtuais) {
        var iaConfInfo = garantirConfigIA();
        var dConf = iaConfInfo.sheet.getDataRange().getValues();
        var vips = "";
        for (var idxC = 1; idxC < dConf.length; idxC++) {
           if (dConf[idxC][0] === "CLIENTES_AUDITORIA_ATIVOS") { vips = String(dConf[idxC][1]).toUpperCase(); break; }
        }
        var authVips = vips.split(',').map(function(n) { return n.trim(); });
        
        if (authVips.indexOf(String(clienteNome).toUpperCase().trim()) > -1) {
           dispararEmailVIP = true;
           backgroundPayload = {
             emailCli: emailCli,
             nomeResp: nomeResp,
             clienteNome: clienteNome,
             obrig: obrig + " (" + mesRef + ")",
             dadosAtuais: resAudit.dadosAtuais,
             historicoDados: resAudit.historicoDados
           };
        } else {
           registrarLogSistema("AUDIT_MAIL_SKIPPED", "Cliente " + clienteNome + " auditado com sucesso mas não é VIP para e-mail.");
        }
      }
    } catch(e) { 
       registrarLogSistema("EMAIL_NOTIF_ERR", "Falha ao enviar e-mail: " + e.message);
       console.warn("Email erro: " + e.message); 
    }
    
    return { 
      success: true, 
      message: "Operação concluída com sucesso.",
      auditoriaRodou: (norm(acaoTarefa) === CONFIG_SISTEMA.ACOES.AUDITAR),
      dispararEmailVIP: dispararEmailVIP,
      backgroundPayload: backgroundPayload
    };
  } catch(e) { 
    registrarLogSistema("UPLOAD_FATAL", e.message);
    throw new Error(e.message); 
  } finally { lock.releaseLock(); }
}

// --- SERVIÇOS DE DEMANDA E SOLICITAÇÃO ---

/**
 * Cria uma nova tarefa manualmente via Painel (Demanda)
 */
function salvarTarefaDemanda(dados) {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch(e) { throw new Error("Sistema ocupado."); }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    if (!wsTarefas) throw new Error("Aba DB_TAREFAS não localizada.");

    var idControle = "DEM_" + new Date().getTime();
    var mesAno = Utilities.formatDate(new Date(), "GMT-3", "MM/yyyy");
    
    // A=MES_ANO | B=NOME | C=OBRIGACAO | D=VENCIMENTO | E=DEPARTAMENTO | F=STATUS | G=PROTOCOLO | H=ACAO | I=RESPONSAVEL | J=ID_CONTROLE | K=NIVEL | L=VENCIMENTO_LEGAL
    var novaLinha = [
      mesAno,
      dados.cliente,
      dados.tipo + (dados.compl ? " - " + dados.compl : ""),
      new Date(dados.prazo + "T12:00:00"), // Garante meio-dia para evitar problemas de fuso
      dados.depto || "GERAL",
      getSafeStatus("PENDENTE"),
      "",
      dados.acao || "ARQUIVAR",
      dados.responsavel || Session.getActiveUser().getEmail(),
      idControle,
      "3", // Nível padrão
      new Date(dados.prazo + "T12:00:00")
    ];

    wsTarefas.appendRow(novaLinha);
    wsTarefas.getRange(wsTarefas.getLastRow(), 4).setNumberFormat("dd/MM/yyyy");
    wsTarefas.getRange(wsTarefas.getLastRow(), 12).setNumberFormat("dd/MM/yyyy");

    SpreadsheetApp.flush();
    reordenarTarefasElite();
    invalidarCacheSistema();
    registrarLogSistema("DEMANDA_CREATED", "ID: " + idControle + " | Cliente: " + dados.cliente);
    
    return true;
  } finally { lock.releaseLock(); }
}

/**
 * Envia uma solicitação de documento para o cliente e registra na DB_SOLICITACOES
 */
function enviarSolicitacaoDocumento(dados) {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch(e) { throw new Error("Servidor ocupado."); }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsSol = ss.getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
    var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
    
    // 1. Busca Email do Cliente
    var emailCli = "";
    var dataCli = wsCli.getDataRange().getValues();
    for (var i = 1; i < dataCli.length; i++) {
      if (norm(dataCli[i][1]) === norm(dados.cliente)) {
        emailCli = dataCli[i][4];
        break;
      }
    }
    if (!emailCli) throw new Error("Email do cliente não localizado.");

    // 2. Registra Solicitação (Schema Rígido)
    var solId = "SOL" + new Date().getTime();
    wsSol.appendRow([
      solId,                   // A: ID
      new Date(),              // B: DATA
      dados.cliente,           // C: CLIENTE
      emailCli,                // D: EMAIL
      dados.solicitacao,       // E: PEDIDO
      dados.idTarefa || "AVULSA", // F: ID_TAREFA (Referência)
      getSafeStatus("PENDENTE"),// G: STATUS
      "",                      // H: DATA_ENVIO (Será preenchido pela rotina de cobrança se necessário)
      new Date(),              // I: ULTIMA_COBRANCA
      0,                       // J: QTD_AVISOS
      Session.getActiveUser().getEmail() // K: RESPONSAVEL
    ]);

    // 3. Dispara E-mail
    try {
      enviarSolicitacaoAoCliente(dados.cliente, emailCli, dados.solicitacao, solId);
    } catch(errMail) {
      registrarLogSistema("SOL_MAIL_FAIL", errMail.message);
    }

    invalidarCacheSistema();
    registrarLogSistema("SOLICITATION_SENT", "ID: " + solId + " -> " + dados.cliente);
    return true;
  } finally { lock.releaseLock(); }
}

// --- PORTAL DO CLIENTE (UPLOAD FRAGMENTADO) ---

/**
 * Busca dados da solicitação para exibir no portal
 */
function getDadosSolicitacao(solId) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsSol = ss.getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
  var data = wsSol.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][0]) === String(solId)) {
      return {
        cliente: data[i][2],
        pedido: data[i][4],
        status: data[i][6]
      };
    }
  }
  return null;
}

/**
 * Garante que a pasta do cliente exista e retorna o ID para o portal
 */
function prepararPastaUploadCliente(solId) {
  var dados = getDadosSolicitacao(solId);
  if (!dados) throw new Error("Solicitação inválida.");
  
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  var dataCli = wsCli.getDataRange().getValues();
  var pastaId = "";
  var cliNome = dados.cliente;

  for (var i = 1; i < dataCli.length; i++) {
    if (norm(dataCli[i][1]) === norm(cliNome)) {
      var url = String(dataCli[i][12]);
      if (url.indexOf("id=") > -1) pastaId = url.split("id=")[1];
      else if (url.indexOf("folders/") > -1) pastaId = url.split("folders/")[1].split("?")[0];
      break;
    }
  }

  if (pastaId) return pastaId;

  // Cria se não existir
  var root = DriveApp.getFolderById(CONFIG_SISTEMA.PASTAS.CLIENTES_DIGITAL);
  var folders = root.getFoldersByName(cliNome);
  var target = folders.hasNext() ? folders.next() : root.createFolder(cliNome);
  return target.getId();
}

/**
 * Processa pedaços de arquivo vindo do WebApp (Contorna limites de 10MB)
 */
function processarFragmentoUpload(folderId, fileName, fileType, chunk, currentChunk, totalChunks, solId) {
  var cache = CacheService.getScriptCache();
  var cacheKey = "SOL_UP_" + solId + "_" + fileName.replace(/[^a-zA-Z0-9]/g, "");
  
  // Acumula no cache (limite de 100KB por item, chunks de 1MB exigem sub-fragmentação ou persistência)
  // Como o HTML envia 1MB, vamos salvar direto no Drive como arquivo temporário ou persistir no Cache
  // Estratégia: Salvar cada chunk como um arquivo temporário oculto
  var folder = DriveApp.getFolderById(folderId);
  var blob = Utilities.newBlob(Utilities.base64Decode(chunk), fileType, fileName + ".part" + currentChunk);
  var partFile = folder.createFile(blob);
  
  // Registra o ID da parte no cache para junção final
  var parts = JSON.parse(cache.get(cacheKey) || "[]");
  parts.push(partFile.getId());
  cache.put(cacheKey, JSON.stringify(parts), 3600);

  if (currentChunk + 1 === totalChunks) {
    // Ultimo pedaço: Juntar tudo
    var finalBlob = juntarFragmentos(parts, fileName, fileType);
    var finalFile = folder.createFile(finalBlob);
    finalFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    
    // Limpeza
    parts.forEach(function(id) { try { DriveApp.getFileById(id).setTrashed(true); } catch(e){} });
    cache.remove(cacheKey);

    return { status: 'DONE', url: finalFile.getUrl() };
  }
  
  return { status: 'CONTINUE' };
}

function juntarFragmentos(partsIds, fileName, fileType) {
  var combinedBytes = [];
  partsIds.forEach(function(id) {
    var bytes = DriveApp.getFileById(id).getBlob().getBytes();
    combinedBytes = combinedBytes.concat(bytes);
  });
  return Utilities.newBlob(combinedBytes, fileType, fileName);
}

/**
 * Finaliza o processo de solicitação, baixa a tarefa e notifica
 */
function finalizarLoteUploadsCliente(solId, linksGerados) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsSol = ss.getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
  var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  
  var dataSol = wsSol.getDataRange().getValues();
  var solRow = -1;
  for (var i = 1; i < dataSol.length; i++) {
    if (String(dataSol[i][0]) === String(solId)) { solRow = i + 1; break; }
  }
  if (solRow === -1) throw new Error("Solicitação sumiu.");

  var cliente = dataSol[solRow-1][2];
  var pedido = dataSol[solRow-1][4];
  var idTarefa = dataSol[solRow-1][5];
  var responsavel = dataSol[solRow-1][10];

  // 1. Atualiza Solicitação
  var linksStr = linksGerados.join(" | ");
  wsSol.getRange(solRow, 7, 1, 2).setValues([[getSafeStatus("ENTREGUE"), linksStr]]);

  // 2. Se houver tarefa associada, dá baixa nela
  if (idTarefa && idTarefa !== "AVULSA") {
    var dataTf = wsTarefas.getRange(1, 10, wsTarefas.getLastRow(), 1).getValues();
    for (var j = 1; j < dataTf.length; j++) {
      if (String(dataTf[j][0]) === String(idTarefa)) {
        wsTarefas.getRange(j + 1, 6, 1, 2).setValues([[getSafeStatus("ENTREGUE"), "PORTAL-" + solId]]);
        acionarWorkflowFaseSeguinte(idTarefa, j + 1);
        break;
      }
    }
  }

  // 3. Notifica Responsável
  try {
    notificarRecebimentoAoResponsavel(cliente, pedido, responsavel, linksGerados);
  } catch(e) {}

  reordenarTarefasElite();
  invalidarCacheSistema();
  registrarLogSistema("PORTAL_UPLOAD_FINISH", "Sol: " + solId + " | Cliente: " + cliente);
  return true;
}
