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
    var dataTf = wsTarefas.getRange(1, 10, wsTarefas.getLastRow(), 1).getValues(); 
    var rowIdx = -1;
    for(var i=1; i<dataTf.length; i++) if(String(dataTf[i][0]) === String(taskId)) { rowIdx = i + 1; break; }
    if(rowIdx === -1) throw new Error("ID da tarefa não localizado.");
    
    var rowVal = wsTarefas.getRange(rowIdx, 1, 1, 12).getValues()[0];
    var obrig = rowVal[2];
    var mesRef = rowVal[0] instanceof Date ? Utilities.formatDate(rowVal[0], "GMT-3", "MM/yyyy") : String(rowVal[0]);
    
    // Localização do Cliente
    var dadosC = wsCli.getDataRange().getValues();
    var email = "", cnpj = "", pastaId = "";
    var cliRowIdx = -1;
    for(var i=1; i<dadosC.length; i++) {
      if(norm(dadosC[i][1]) === norm(clienteNome)) { 
        cnpj = String(dadosC[i][2]).replace(/[^0-9]/g, "");
        email = dadosC[i][4]; 
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
    
    var linksParaEmail = [];
    var folderGlobal = DriveApp.getFolderById(CONFIG_SISTEMA.PASTAS.ENVIADOS);
    
    // Processamento de Arquivos
    arquivos.forEach(function(f, idx) {
      var nomeOriginal = f.name;
      var ext = nomeOriginal.split('.').pop();
      var nomeObrig = norm(obrig).replace(/\s+/g, "_"); 
      var novoNome = cnpj + "." + nomeObrig + "." + mesRef.replace(/\//g, ".") + (arquivos.length > 1 ? "_" + (idx+1) : "") + "." + ext;
      
      var blob = Utilities.newBlob(Utilities.base64Decode(f.base64), "application/octet-stream", novoNome);
      
      // Criar e Copiar (Garante acesso ao Admin e ao Usuário)
      var fileClient = target.createFile(blob);
      fileClient.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      fileClient.makeCopy(novoNome, folderGlobal);
      
      var url = fileClient.getUrl();
      linksParaEmail.push({ url: url, name: nomeOriginal });
    });

    var protocolo = gerarProtocoloEntrega();
    var linksDriveStr = linksParaEmail.map(function(item) { return item.url; }).join(" | ");
    registrarProtocoloDB(clienteNome, protocolo, taskId, obrig, email, linksDriveStr);
    
    wsTarefas.getRange(rowIdx, 6, 1, 2).setValues([[getSafeStatus("ENTREGUE"), protocolo]]);
    
    acionarWorkflowFaseSeguinte(taskId, rowIdx);
    reordenarTarefasElite(); 
    invalidarCacheSistema(); 

    try {
      notificarEntregaClienteRefatorada(clienteNome, obrig, protocolo, email, linksParaEmail, target.getUrl(), rowIdx);
    } catch(e) { console.warn("Email erro: " + e.message); }
    
    return true;
  } catch(e) { 
    registrarLogSistema("UPLOAD_FATAL", e.message);
    throw new Error(e.message); 
  } finally { lock.releaseLock(); }
}

// ... manter as outras funções de apoio inalteradas (prepararPastaUploadCliente, etc)
