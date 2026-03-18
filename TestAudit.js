/**
 * Testes de Unidade para o Motor de Auditoria
 */
function testAuditFlow() {
  console.log("--- INICIANDO TESTE DE AUDITORIA ---");
  
  // 1. Simulação de um Balancete (Precisa de um PDF no Drive para teste real se desejar)
  // Por enquanto, vamos testar a lógica de extração simulada ou usar um arquivo real se houver.
  
  var query = "title contains 'Balancete' and mimeType = 'application/pdf'";
  var files = DriveApp.searchFiles(query);
  
  if (!files.hasNext()) {
    console.warn("⚠️ Nenhum PDF de balancete encontrado para teste real. Testando funções isoladas.");
    return testFuncoesIsoladas();
  }
  
  var testFile = files.next();
  console.log("📄 Usando arquivo para teste: " + testFile.getName());
  
  try {
    var blob = testFile.getBlob();
    var res = validarDadosBalancete(blob);
    
    console.log("✅ Resultado da Validação:");
    console.log(JSON.stringify(res, null, 2));
    
    if (res.aprovado) {
       console.log("🤖 Gerando Relatório IA...");
       var relIA = gerarRelatorioComportamentalIA(res.dadosAtuais, []);
       console.log("Conteúdo IA:\n" + relIA);
       
       var pdf = gerarPDFAnalise("CLIENTE TESTE", relIA);
       console.log("📄 PDF Gerado: " + pdf.getName() + " (" + pdf.getSize() + " bytes)");
    } else {
       console.log("❌ Auditoria Reprovada conforme esperado ou erro de leitura: " + res.erros.join(", "));
    }
    
  } catch (e) {
    console.error("💥 Erro no teste: " + e.message);
  }
}

function testFuncoesIsoladas() {
  console.log("--- TESTANDO FUNÇÃO DE EXTRAÇÃO DE VALORES ---");
  var textoMock = "ATIVO TOTAL: 1.250.500,75 \n PASSIVO TOTAL: 1.250.500,75 \n CAIXA: 15.000,00";
  
  function extrairValorInterno(termo, txt) {
    var regex = new RegExp(termo + "[:\\s\\.]+\\s*([\\d\\.,]+)", "i");
    var match = txt.match(regex);
    if (match) {
      var valStr = match[1].replace(/\./g, "").replace(",", ".");
      return parseFloat(valStr);
    }
    return null;
  }
  
  var ativo = extrairValorInterno("ATIVO TOTAL", textoMock);
  var passivo = extrairValorInterno("PASSIVO TOTAL", textoMock);
  var caixa = extrairValorInterno("CAIXA", textoMock);
  
  console.log("Ativo: " + ativo + " (Esperado: 1250500.75)");
  console.log("Passivo: " + passivo + " (Esperado: 1250500.75)");
  console.log("Caixa: " + caixa + " (Esperado: 15000.00)");
  
  if (ativo === 1250500.75 && passivo === 1250500.75 && caixa === 15000) {
    console.log("✅ Lógica de Regex Funcional.");
  } else {
    console.error("❌ Erro na lógica de Regex.");
  }
}

function testGetPendencias() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ws = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var data = ws.getDataRange().getValues();
  
  if (data.length < 2) {
    console.warn("Sem tarefas na planilha.");
    return;
  }
  
  var cliente = data[1][1]; // Pega o primeiro cliente
  console.log("--- TESTANDO PENDÊNCIAS PARA: " + cliente + " ---");
  var pendencias = getPendenciasCliente(cliente);
  console.log(JSON.stringify(pendencias, null, 2));
}
function testNewAuditNotifications() {
  console.log("--- TESTANDO NOVAS NOTIFICAÇÕES DE AUDITORIA ---");
  
  var cliente = "EMPRESA TESTE LTDA";
  var obrigacao = "BALANCETE MENSAL";
  var responsavel = "João Silva";
  var email = "joao.silva@exemplo.com";
  var analiseMock = "### Análise Estratégica\n* Ativo e Passivo conferem.\n* Saldo de caixa saudável.\n## Recomendações\nManter o controle de custos fixos.";
  
  try {
    console.log("1. Testando notificarAuditAdmin (Sucesso)...");
    notificarAuditAdmin(cliente, obrigacao, true, "Todos os quesitos matemáticos e de IA foram aprovados.");
    
    console.log("2. Testando notificarAuditAdmin (Falha)...");
    notificarAuditAdmin(cliente, obrigacao, false, "Divergência de R$ 50,00 entre Ativo e Passivo.");
    
    console.log("3. Testando enviarRelatorioAnaliseIA...");
    enviarRelatorioAnaliseIA(email, responsavel, cliente, obrigacao, analiseMock);
    
    console.log("✅ Ciclo de testes de e-mail concluído com sucesso (Verifique logs e caixa de saída).");
  } catch (e) {
    console.error("❌ Erro ao disparar notificações de teste: " + e.message);
  }
}
