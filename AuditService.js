/**
 * 🕵️ AUDIT SERVICE v1.0
 * Funcionalidade: Validação de Balancetes, Análise de Tendências (3 meses) e Geração de Relatórios.
 */

/**
 * Ponto de Entrada Principal para Auditoria
 */
function processarAuditoriaBalancete(fileBlob, taskId, clienteNome, cnpj, obrigacao) {
  registrarLogSistema("AUDIT_PROCESS_START", "Cliente: " + clienteNome + " | Tarefa: " + taskId);
  
  try {
    // 1. Extração e Validação (Matemática + OCR)
    var resultadoAudit = validarDadosBalancete(fileBlob);
    
    // 2. Buscar histórico estruturado para contextualizar a IA
    var historicoDados = buscarHistoricoBalancetes(clienteNome, cnpj, obrigacao);
    
    // 3. Chamada 1: Auditoria Interna (Regras de Negócio)
    var analiseInterna = gerarRelatorioComportamentalIA(resultadoAudit.dadosAtuais, historicoDados, "AUDITORIA");
    var reprovadoIA = analiseInterna.indexOf("[REPROVADO]") > -1;
    
    if (!resultadoAudit.aprovado || reprovadoIA) {
      var errosFinais = resultadoAudit.erros || [];
      if (reprovadoIA) {
        var partsIA = analiseInterna.split("[REPROVADO]");
        var motivoIA = partsIA.length > 1 ? partsIA[1].trim().split("\n")[0] : "Motivo não identificado";
        errosFinais.push("REPROVAÇÃO IA: " + motivoIA);
      }
      // Notifica o Admin sobre a reprovação com detalhes
      notificarAuditAdmin(clienteNome, obrigacao, false, (resultadoAudit.erros ? resultadoAudit.erros.join("\n") + "\n" : "") + analiseInterna);
      return { aprovado: false, erros: errosFinais };
    }
    
    // Se aprovado, notifica o Admin sobre o sucesso da auditoria
    notificarAuditAdmin(clienteNome, obrigacao, true, analiseInterna);

    // 4. Chamada 2: Relatório do Cliente (Se aprovado em tudo)
    var analiseCliente = gerarRelatorioComportamentalIA(resultadoAudit.dadosAtuais, historicoDados, "RELATORIO");
    
    // 5. Retorno apenas dos dados necessários (PDF removido conforme solicitação)
    return { aprovado: true, analise: analiseCliente };
    
  } catch (e) {
    registrarLogSistema("AUDIT_FATAL_ERR", e.message);
    throw e;
  }
}

/**
 * Busca os últimos 3 balancetes na pasta do cliente
 */
function buscarHistoricoBalancetes(clienteNome, cnpj, obrigacao) {
  var pastaId = "";
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  var dataCli = wsCli.getDataRange().getValues();
  
  for (var i = 1; i < dataCli.length; i++) {
    if (norm(dataCli[i][1]) === norm(clienteNome)) {
      var url = String(dataCli[i][12]);
      if (url.indexOf("id=") > -1) pastaId = url.split("id=")[1];
      else if (url.indexOf("folders/") > -1) pastaId = url.split("folders/")[1].split("?")[0];
      break;
    }
  }
  
  if (!pastaId) return [];
  
  var folder = DriveApp.getFolderById(pastaId);
  var files = folder.getFiles();
  var pattern = cnpj + "." + norm(obrigacao).replace(/\s+/g, "_");
  var matchedFiles = [];
  
  while (files.hasNext()) {
    var file = files.next();
    if (file.getName().indexOf(pattern) > -1) {
      matchedFiles.push({
        date: file.getDateCreated(),
        blob: file.getBlob(),
        name: file.getName()
      });
    }
  }
  
  // Ordenar por data (mais recentes primeiro) e pegar os 3 primeiros
  matchedFiles.sort((a, b) => b.date - a.date);
  var tops = matchedFiles.slice(0, 3);
  
  return tops.map(f => {
    try {
      var texto = extrairTextoOCR(f.blob);
      var extraido = extrairDadosApenas(texto);
      return {
        arquivo: f.name,
        data: Utilities.formatDate(f.date, "GMT-3", "dd/MM/yyyy"),
        valores: extraido
      };
    } catch(e) {
      return { arquivo: f.name, erro: "Falha na leitura" };
    }
  });
}

/**
 * Validação Lógica e Matemática via OCR
 */
function validarDadosBalancete(blobAtual) {
  try {
    var texto = extrairTextoOCR(blobAtual);
    var dadosAtuais = extrairDadosApenas(texto);
    var erros = [];
    
    // Regex para capturar o nome da empresa
    var regexNome = /(?:EMPRESA|RAZÃO SOCIAL|NOME)[:\s]+([^\n\r]+)/i;
    var matchNome = texto.match(regexNome);
    var nomeDoc = matchNome ? matchNome[1].trim() : "Não Identificado";

    var ativo = dadosAtuais["ATIVO TOTAL"] || dadosAtuais["TOTAL DO ATIVO"] || dadosAtuais["ATIVO"];
    var passivo = dadosAtuais["PASSIVO TOTAL"] || dadosAtuais["TOTAL DO PASSIVO"] || dadosAtuais["PASSIVO"];
    var caixa = dadosAtuais["CAIXA"];
    
    registrarLogSistema("AUDIT_EXTRACT", "Quesitos: " + JSON.stringify(dadosAtuais) + " | Nome: " + nomeDoc);

    if (ativo === null || passivo === null) {
      erros.push("Não foi possível localizar os totais de Ativo ou Passivo no documento.");
    } else if (Math.abs(ativo - passivo) > 0.05) { 
      erros.push("Diferença entre Ativo (" + ativo.toFixed(2) + ") e Passivo (" + passivo.toFixed(2) + ") localizada.");
    }
    
    if (caixa !== null && caixa < 0) {
      erros.push("Saldo da conta Caixa está credor (invertido): " + caixa.toFixed(2));
    }
    
    dadosAtuais.nomeNoDocumento = nomeDoc;
    
    return {
      aprovado: erros.length === 0,
      erros: erros,
      dadosAtuais: dadosAtuais,
      textoCompleto: texto
    };
  } catch (e) {
    registrarLogSistema("OCR_ERR", e.message);
    throw new Error("Falha na extração de dados via OCR: " + e.message);
  }
}

/**
 * Helper para extrair dados a partir de um texto já obtido via OCR
 */
function extrairDadosApenas(texto) {
  function extrairValor(termo, txt) {
    if (!termo) return null;
    var regex = new RegExp(termo + "[:\\s\\.]+\\s*([\\d\\.,]+)", "i");
    var match = txt.match(regex);
    if (match) {
      var valStr = match[1].replace(/\./g, "").replace(",", ".");
      return parseFloat(valStr);
    }
    return null;
  }

  var resConfig = garantirConfigIA();
  var dataConfig = resConfig.sheet.getDataRange().getValues();
  var quesitosStr = "ATIVO TOTAL, PASSIVO TOTAL, CAIXA";
  for(var i=1; i<dataConfig.length; i++) {
    if(dataConfig[i][0] === "AUDIT_QUESITOS") quesitosStr = dataConfig[i][1];
  }
  
  var quesitosLista = quesitosStr.split(',').map(q => q.trim()).filter(q => q !== "");
  var dados = {};
  quesitosLista.forEach(q => {
    dados[q] = extrairValor(q, texto);
  });
  
  return dados;
}

/**
 * Converte PDF/Imagem em texto usando o Drive API (OCR)
 */
function extrairTextoOCR(blob) {
  var resource = {
    title: "TEMP_OCR_" + new Date().getTime(),
    mimeType: blob.getContentType()
  };
  
  // Requer Serviço Avançado "Drive" (v2) habilitado
  var file = Drive.Files.insert(resource, blob, { ocr: true, ocrLanguage: "pt" });
  var doc = DocumentApp.openById(file.id);
  var texto = doc.getBody().getText();
  
  // Limpeza imediata
  try { Drive.Files.remove(file.id); } catch(e) {}
  
  return texto;
}

/**
 * Gera análise via IA usando o AIService
 */
function gerarAnaliseComportamentalIA(atual, historico) {
  var prompt = "Aja como um analista contábil sênior. Analise os seguintes dados do balancete atual: " + 
               JSON.stringify(atual) + ". Compare com o histórico: " + JSON.stringify(historico) + 
               ". Gere um relatório de comportamento financeiro, operacional e de resultados em markdown.";
               
  // Note: Precisa de implementação real no AIService para chamar a API externa
  return "### Análise de Performance Contábil\n\nO balancete apresenta equilíbrio patrimonial...";
}

// Funções legadas removidas conforme nova diretriz de e-mail formatado (EmailService.js)
