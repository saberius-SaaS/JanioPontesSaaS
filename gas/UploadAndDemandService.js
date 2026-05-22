/**
 * 🚀 UPLOAD & DEMAND SERVICE v131.13
 * FOCO: Estabilidade total no Bypass de Permissão e Identidade DriveApp.
 */

/**
 * Ponto de entrada exclusivo do Painel (Sidebar)
 * Diferente do Portal, aqui usamos a identidade local do container nativo do G. Workspace
 */
function processarUploadViaPainel(payload) {
  var userEmail = Session.getActiveUser().getEmail();
  if (!userEmail) throw new Error("Acesso Negado: Sessão expirada.");
  userEmail = userEmail.toLowerCase().trim();
  
  var userLevel = "USER";
  var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
  if (dataU) {
    for (var u = 1; u < dataU.length; u++) {
        if (String(dataU[u][0]).toLowerCase().trim() === userEmail) { 
            userLevel = String(dataU[u][2]).toUpperCase().trim(); 
            break; 
        }
    }
  }
  return processarUploadBatchInterno(payload.arquivos, payload.taskId, payload.clienteNome, payload.mensagem, !!payload.forcar, userLevel, payload.justificativaSemEnvio || "", payload.anotacao || "");
}

function processarUploadBatchInterno(arquivos, taskId, clienteNome, mensagem, forcar, userLevel, justificativaSemEnvio, anotacao) {
  var lock = LockService.getScriptLock();
  try { 
    lock.waitLock(25000); 
  } catch(e) { 
    throw new Error("Sistema ocupado. Tente novamente."); 
  }

  try {
    var ss = getSs();
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
        emailCli = obterEmailDirecionado(dadosC[i], rowVal[4]); // Roteamento por Departamento c/ Fallback Col E
        var urlM = String(dadosC[i][12]);
        if (urlM.indexOf("id=") > -1) pastaId = urlM.split("id=")[1];
        else if (urlM.indexOf("folders/") > -1) pastaId = urlM.split("folders/")[1].split("?")[0];
        cliRowIdx = i + 1;
        break;
      }
    }
    
    // Gestão de Pasta com Privilégios Elevados
    var acaoTarefa = rowVal[7];
    var protocolo = gerarProtocoloEntrega();
    
    // --- LÓGICA DE STATUS: REVISAO VS ENTREGUE ---
    var statusFinal = getSafeStatus("ENTREGUE");
    var dataR = getSheetDataCached("DB_REGRAS", "DATA_REGRAS");
    var exigeRevisao = false;
    for (var r = 1; r < dataR.length; r++) {
        if (norm(dataR[r][1]) === norm(obrig)) { // Coluna B: Obrigação
            exigeRevisao = String(dataR[r][12] || "").toUpperCase().trim() === "S"; // Coluna M: REVISAO?
            break;
        }
    }
    
    // Somente exige revisão se a regra pedir E se o usuário for nível USER
    if (exigeRevisao && userLevel === "USER") {
       if (!arquivos || arquivos.length === 0) {
          throw new Error("Esta tarefa requer validação de arquivo. Por favor, anexe o documento necessário.");
       }
       statusFinal = getSafeStatus("REVISAO");
       registrarLogSistema("WORKFLOW_REVISAO", "Tarefa movida para REVISAO (Executor: " + userLevel + ")");
    }

    // --- BLOCO OCR: VALIDAÇÃO DE CNPJ (Amostragem: Apenas 1º arquivo) ---
    if (!forcar && arquivos && arquivos.length > 0 && norm(acaoTarefa).indexOf(CONFIG_SISTEMA.ACOES.COMUNICAR) === -1) {
      try {
        var f1 = arquivos[0];
        var ext1 = String(f1.name || "").toLowerCase().split('.').pop();
        var tiposSuportados = ["pdf", "jpg", "jpeg", "png"];
        
        if (tiposSuportados.indexOf(ext1) > -1 && cnpj) {
          registrarLogSistema("OCR_VALIDATION", "Validando CNPJ p/ " + clienteNome);
          var blob1 = Utilities.newBlob(Utilities.base64Decode(f1.base64), "application/octet-stream", f1.name);
          var textoExtraido = extrairTextoOCR(blob1);
          var textoLimpo = limparTextoOcrParaComparacao(textoExtraido);
          
          var cnpjBase = cnpj.substring(0, 8);
          if (textoLimpo.indexOf(cnpj) === -1 && textoLimpo.indexOf(cnpjBase) === -1) {
             registrarLogSistema("OCR_MISMATCH", "CNPJ Esperado: " + cnpj + " (ou Raiz " + cnpjBase + ") | Texto: " + textoLimpo.substring(0, 50));
             return {
               success: false,
               needsConfirmation: true,
               message: "⚠️ O CNPJ do cliente (" + cnpj + ") não foi localizado no documento '" + f1.name + "'.\n\nDeseja confirmar o envio mesmo assim?"
             };
          }
        }
      } catch(eOcr) {
        registrarLogSistema("OCR_VAL_SKIP", "Falha ou OCR não ativo: " + eOcr.message);
        // Em caso de falha no OCR (ex: serviço não ativo), seguimos sem travar
      }
    }
    // --- FIM BLOCO OCR ---

    // INTERCEPTAÇÃO: AÇÃO COMUNICAR
    if (norm(acaoTarefa).indexOf(CONFIG_SISTEMA.ACOES.COMUNICAR) > -1) {
        var vctoLegal = typeof rowVal[11] === 'object' && rowVal[11] instanceof Date ? Utilities.formatDate(rowVal[11], "GMT-3", "dd/MM/yyyy") : (rowVal[11] || "---");
        
        // COMUNICAR sem mensagem (com justificativa)
        var semMensagem = !mensagem || mensagem.trim() === "";
        var descricaoProtocolo = semMensagem ? "SEM_COMUNICADO: " + (justificativaSemEnvio || "Sem detalhes") : "COMUNICADO: " + mensagem;
        
        var protRowIdx = registrarProtocoloDB(clienteNome, protocolo, taskId, obrig, emailCli, descricaoProtocolo, vctoLegal, acaoTarefa);
        wsTarefas.getRange(rowIdx, 6, 1, 2).setValues([[statusFinal, protocolo]]);
        
        if (statusFinal !== getSafeStatus("REVISAO")) {
           acionarWorkflowFaseSeguinte(taskId, rowIdx);
           moverTarefaParaHistoricoImediato(rowIdx);
        }
        reordenarTarefasElite(); 
        invalidarCacheSistema(); 
        
        try {
            // Só envia e-mail se houver mensagem real e não estiver em REVISAO
            if (statusFinal !== getSafeStatus("REVISAO") && !semMensagem) {
               enviarComunicadoCliente(clienteNome, emailCli, obrig, protocolo, mensagem, rowVal[8]);
            }
        } catch(eMailCom) {
            registrarLogSistema("EMAIL_COM_ERR", "Falha comunicado: " + eMailCom.message);
        }

        if (semMensagem) {
            registrarLogSistema("COMUNICAR_SEM_MSG", "Tarefa: " + taskId + " | Cliente: " + clienteNome + " | Justificativa: " + (justificativaSemEnvio || "N/A"));
        }

        return { 
          success: true, 
          message: semMensagem ? "Tarefa conclu\u00edda sem comunicado (justificativa registrada)." : "Comunicado enviado com sucesso.",
          auditoriaRodou: false,
          dispararEmailVIP: false,
          backgroundPayload: null
        };
    }

    // INTERCEPTAÇÃO: ENVIAR SEM ARQUIVO (com justificativa)
    if (justificativaSemEnvio && (!arquivos || arquivos.length === 0) && norm(acaoTarefa).indexOf(CONFIG_SISTEMA.ACOES.ENVIAR) > -1) {
        var vctoLegal = typeof rowVal[11] === 'object' && rowVal[11] instanceof Date ? Utilities.formatDate(rowVal[11], "GMT-3", "dd/MM/yyyy") : (rowVal[11] || "---");
        var protRowIdx = registrarProtocoloDB(clienteNome, protocolo, taskId, obrig, emailCli, "SEM_ENVIO: " + justificativaSemEnvio, vctoLegal, acaoTarefa);
        wsTarefas.getRange(rowIdx, 6, 1, 2).setValues([[statusFinal, protocolo]]);
        
        if (statusFinal !== getSafeStatus("REVISAO")) {
           acionarWorkflowFaseSeguinte(taskId, rowIdx);
           moverTarefaParaHistoricoImediato(rowIdx);
        }
        reordenarTarefasElite(); 
        invalidarCacheSistema();
        registrarLogSistema("ENVIO_SEM_ARQUIVO", "Tarefa: " + taskId + " | Cliente: " + clienteNome + " | Justificativa: " + justificativaSemEnvio);
        
        return { 
          success: true, 
          message: "Tarefa conclu\u00edda sem envio de arquivo (justificativa registrada).",
          auditoriaRodou: false,
          dispararEmailVIP: false,
          backgroundPayload: null
        };
    }

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
    
    // Se for ARQUIVAR e houver anotação, grava na coluna H como registro interno
    var acaoTarefaVerif = String(rowVal[7]).toUpperCase().trim();
    if (acaoTarefaVerif.indexOf(CONFIG_SISTEMA.ACOES.ARQUIVAR) > -1 && anotacao && anotacao.trim() !== "") {
      linksDriveStr = linksDriveStr ? linksDriveStr + " | NOTA: " + anotacao.trim() : "NOTA: " + anotacao.trim();
    }
    
    // --- INTEGRAÇÃO BLOCO AUDITORIA ---
    var acaoTarefa = rowVal[7];
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

    var vctoLegal = typeof rowVal[11] === 'object' && rowVal[11] instanceof Date ? Utilities.formatDate(rowVal[11], "GMT-3", "dd/MM/yyyy") : (rowVal[11] || "---");
    var protRowIdx = registrarProtocoloDB(clienteNome, protocolo, taskId, obrig, emailCli, linksDriveStr, vctoLegal, acaoTarefa);
    
    // --- BLOCO TRANSACIONAL: E-MAIL E COMUNICAÇÃO PRIMEIRO ---
    // Se falhar o envio de email, vai abortar o cadastro do Status na esteira da planilha para evitar "baixas fantasmas"
    var dispararEmailVIP = false;
    var backgroundPayload = null;
    
    // Se for REVISAO, não envia e-mail agora (aguarda aprovação do Admin)
    if (statusFinal !== getSafeStatus("REVISAO")) {
       // Se não for auditoria (ex: envio comum), manda a notificação genérica "Processado com sucesso"
       if (norm(acaoTarefa) !== CONFIG_SISTEMA.ACOES.AUDITAR) {
         // Caso seja ARQUIVAR, não envia e-mail ao cliente (Finalização Simples Interna)
         var deveNotificar = (norm(acaoTarefa) !== CONFIG_SISTEMA.ACOES.ARQUIVAR);
         if (deveNotificar) {
           // Passamos o protRowIdx em vez do rowIdx da tarefa para rastreio direto no DB_PROTOCOLOS
           // PROTEÇÃO: Falha no e-mail NÃO deve abortar a finalização da tarefa.
           try {
             notificarEntregaClienteRefatorada(clienteNome, obrig, protocolo, emailCli, linksParaEmail, target.getUrl(), protRowIdx || "", false, mesRef, vctoLegal, rowVal[8]);
           } catch(eMailNotif) {
             registrarLogSistema("EMAIL_NOTIF_ERR", "Tarefa finalizada mas e-mail falhou: " + eMailNotif.message);
           }
         }
       }
    }
  
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
    // --- FIM BLOCO TRANSACIONAL DE COMUNICAÇÃO ---

    // COMUNICAÇÃO OK? DAR BAIXA FÍSICA E WORKFLOW (Commit da Transação)
    wsTarefas.getRange(rowIdx, 6, 1, 2).setValues([[statusFinal, protocolo]]);
    
    // Só aciona fase seguinte se NÃO for revisão
    if (statusFinal !== getSafeStatus("REVISAO")) {
       acionarWorkflowFaseSeguinte(taskId, rowIdx);
       moverTarefaParaHistoricoImediato(rowIdx);
    }
    reordenarTarefasElite(); 
    invalidarCacheSistema();
    
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
function salvarTarefaDemanda(dados, token) {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch(e) { throw new Error("Sistema ocupado."); }

  try {
    var userEmail = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!userEmail) throw new Error("Não foi possível autenticar sua identidade via GIS.");

    var ss = getSs();
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
      getSafeAction(dados.acao || "ARQUIVAR"),
      dados.responsavel || userEmail,
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
function enviarSolicitacaoDocumento(dados, token) {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch(e) { throw new Error("Servidor ocupado."); }

  try {
    var userEmail = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!userEmail) throw new Error("Não foi possível autenticar sua identidade via GIS.");

    var ss = getSs();
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

    // 2. Busca Dados da Tarefa Vinculada (Se houver)
    var infoTarefa = "";
    if (dados.idTarefa && dados.idTarefa !== "AVULSA") {
      var wsTf = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
      if (wsTf) {
        var dataTf = wsTf.getDataRange().getValues();
        var idProcurado = String(dados.idTarefa).trim();
        
        for (var i = 1; i < dataTf.length; i++) {
          var idBanco = String(dataTf[i][9]).trim();
          if (idBanco === idProcurado) { // Coluna J: ID_CONTROLE
            var obrigTf = dataTf[i][2];
            // Tenta formatar a data, se falhar ou se for string, usa o valor puro
            var refTf = "";
            try {
              refTf = (dataTf[i][0] instanceof Date) ? Utilities.formatDate(dataTf[i][0], "GMT-3", "MM/yyyy") : String(dataTf[i][0]);
            } catch(eRef) { refTf = String(dataTf[i][0]); }
            
            infoTarefa = obrigTf + " (" + refTf + ")";
            break;
          }
        }
      }
      
      if (!infoTarefa) {
        registrarLogSistema("SOL_TASK_NOT_FOUND", "Tarefa '" + dados.idTarefa + "' não encontrada na DB_TAREFAS para o cliente " + dados.cliente);
      }
    }

    // 3. Registra Solicitação (Schema Rígido)
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
      1,                       // J: QTD_AVISOS
      userEmail,               // K: RESPONSAVEL
      infoTarefa               // L: META_TAREFA (Obrigado por info da tarefa vinculada)
    ]);

    // 4. Dispara E-mail
    try {
      enviarSolicitacaoAoCliente(dados.cliente, emailCli, dados.solicitacao, solId, infoTarefa, userEmail);
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
  var ss = getSs();
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
  
  var ss = getSs();
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
function finalizarLoteUploadsCliente(solId, linksGerados, textoResposta) {
  var ss = getSs();
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
  var valorColunaLink = linksStr;
  
  if (textoResposta && textoResposta.trim() !== "") {
    if (linksGerados.length > 0) {
      valorColunaLink = "RESPOSTA: " + textoResposta.trim() + " | ARQUIVOS: " + linksStr;
    } else {
      valorColunaLink = "RESPOSTA: " + textoResposta.trim();
    }
  }

  wsSol.getRange(solRow, 7, 1, 2).setValues([[getSafeStatus("ENTREGUE"), valorColunaLink]]);

  // 2. Se houver tarefa associada, dá baixa nela
  if (idTarefa && idTarefa !== "AVULSA") {
    var dataTf = wsTarefas.getRange(1, 10, wsTarefas.getLastRow(), 1).getValues();
    for (var j = 1; j < dataTf.length; j++) {
      if (String(dataTf[j][0]) === String(idTarefa)) {
        wsTarefas.getRange(j + 1, 6, 1, 2).setValues([[getSafeStatus("ENTREGUE"), "PORTAL-" + solId]]);
        acionarWorkflowFaseSeguinte(idTarefa, j + 1);
        moverTarefaParaHistoricoImediato(j + 1);
        break;
      }
    }
  }

  // 3. Notifica Responsável
  try {
    notificarRecebimentoAoResponsavel(cliente, pedido, responsavel, linksGerados, textoResposta);
  } catch(e) {}

  reordenarTarefasElite();
  invalidarCacheSistema();
  registrarLogSistema("PORTAL_UPLOAD_FINISH", "Sol: " + solId + " | Cliente: " + cliente);
  return true;
}
