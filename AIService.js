/**
 * 🧠 MOTOR DE INTELIGÊNCIA ARTIFICIAL & CONTEXTO v1.0
 * Responsável por gerenciar a memória, contar tokens e preparar o payload.
 * Dependências: Utils.gs (calcularEstimativaTokens), Config.gs (CONFIG_SISTEMA)
 */

/**
 * Prepara o histórico de mensagens para envio à API, injetando
 * instruções de controle de contexto (Turno 5, 10, etc).
 * * @param {Array} historico Array de objetos {role: "user"|"assistant", content: "..."}
 * @return {Object} Payload tratado com metadados de uso.
 */
function prepararContextoIA(historico) {
  if (!historico || historico.length === 0) return null;

  var intervaloCheck = CONFIG_SISTEMA.TURNOS_PARA_CHECKPOINT || 5;
  
  // 1. Contagem de Turnos (Consideramos cada par User+Assistant como 1 turno completo)
  // Se o histórico só tem mensagens soltas, contamos quantas vezes o 'user' falou.
  var turnosUsuario = historico.filter(function(m) { return m.role === 'user'; }).length;
  
  // 2. Cálculo de Tokens (Usando a heurística do Utils.gs)
  var totalTokens = 0;
  var ultimoTurnoTokens = 0;
  
  historico.forEach(function(msg) {
    var tokens = calcularEstimativaTokens(msg.content);
    totalTokens += tokens;
    // Salva o custo da última mensagem para análise rápida
    if (msg === historico[historico.length - 1]) {
      ultimoTurnoTokens = tokens;
    }
  });

  // 3. Lógica do Gatilho (Cenário A)
  var acionarCheckpoint = (turnosUsuario > 0 && turnosUsuario % intervaloCheck === 0);
  var mensagemSistema = "";

  if (acionarCheckpoint) {
    // INJEÇÃO DE COMANDO: Modificamos a última mensagem do usuário ou adicionamos sistema
    // Estratégia: Adicionar uma instrução explícita ao final da última mensagem do usuário.
    // Isso garante que a IA leia a instrução junto com o prompt atual.
    
    var tagAlerta = "\n\n" +
      "[🚨 SYSTEM ALERT: STATUS DO SISTEMA]\n" +
      "- Turno Atual: " + turnosUsuario + " (Ciclo de Checkpoint)\n" +
      "- Uso de Contexto (Estimado): " + totalTokens + " tokens\n" +
      "- INSTRUÇÃO OBRIGATÓRIA: Gere um resumo dos pontos-chave discutidos até agora e analise se precisamos ser mais breves.";
      
    // Modifica a última entrada do histórico 
    // (Nota: Em produção, clone o objeto se precisar preservar o original intacto)
    var ultimaMsg = historico[historico.length - 1];
    
    if (ultimaMsg.role === 'user') {
      ultimaMsg.content += tagAlerta;
      mensagemSistema = "Checkpoint injetado na mensagem do usuário.";
    } else {
      // Fallback: Se a última msg for do assistente (raro no envio de prompt), forçamos um append de sistema
      historico.push({ role: "system", content: tagAlerta });
      mensagemSistema = "Checkpoint adicionado como System Message.";
    }
  }

  // Retorna o objeto pronto para ser enviado ao seu conector de API
  return {
    messages: historico,
    metadata: {
      turnos: turnosUsuario,
      tokensTotal: totalTokens,
      tokensUltimaMsg: ultimoTurnoTokens,
      checkpointAtivado: acionarCheckpoint,
      logSistema: mensagemSistema
    }
  };
}

/**
 * Gera análise comportamental de balancetes via Gemini
 */
function gerarRelatorioComportamentalIA(dadosAtuais, historico, tipoPrompt) {
  var resConfig = garantirConfigIA();
  if (resConfig.criada) return "Configuração da IA inicializada na aba DB_CONFIG_IA. Por favor, preencha a API Key.";

  var wsConfig = resConfig.sheet;
  var dataConfig = wsConfig.getDataRange().getValues();
  var apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  var promptBase = "", model = "gemini-2.5-flash", quesitos = "";
  
  var chavePrompt = tipoPrompt === "RELATORIO" ? "PROMPT_RELATORIO" : "PROMPT_AUDITORIA";

  for (var i = 1; i < dataConfig.length; i++) {
    if (dataConfig[i][0] === chavePrompt) promptBase = dataConfig[i][1];
    if (dataConfig[i][0] === "GEMINI_MODEL") model = dataConfig[i][1];
    if (dataConfig[i][0] === "AUDIT_QUESITOS") quesitos = dataConfig[i][1];
  }

  if (!apiKey) return "API Key do Gemini não configurada nos Script Properties.";
  if (!promptBase) return "Prompt " + chavePrompt + " não localizado na configuração.";

  var promptFinal = promptBase
    .replace("{{ATUAL}}", JSON.stringify(dadosAtuais))
    .replace("{{HISTORICO}}", JSON.stringify(historico || []))
    .replace("{{QUESITOS}}", quesitos);

  return chamarGeminiAPI(apiKey, promptFinal, model);
}

/**
 * Chamada direta à API do Gemini
 */
function chamarGeminiAPI(apiKey, prompt, model) {
  var modelName = model || "gemini-2.5-flash";
  var url = "https://generativelanguage.googleapis.com/v1beta/models/" + modelName + ":generateContent?key=" + apiKey;
  
  var payload = {
    contents: [{
      parts: [{ text: prompt }]
    }]
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    var resJson = JSON.parse(response.getContentText());
    
    if (resJson.candidates && resJson.candidates[0].content.parts[0].text) {
      return resJson.candidates[0].content.parts[0].text;
    } else {
      registrarLogSistema("AI_API_ERR", response.getContentText());
      return "Erro na resposta da IA: " + (resJson.error ? resJson.error.message : "Formato inválido");
    }
  } catch (e) {
    registrarLogSistema("AI_FETCH_FATAL", e.message);
    return "Erro crítico na chamada da IA.";
  }
}

/**
 * Função de Teste para Validar o Middleware
 * Execute esta função no Editor para ver o log de execução.
 */
function testarGerenciadorContexto() {
  // Simulação de um histórico com 5 interações do usuário (Gatilho)
  var mockHistory = [
    {role: "user", content: "Olá, vamos começar o projeto."},
    {role: "assistant", content: "Claro, sou o Eng. Sênior. O que precisa?"},
    {role: "user", content: "Crie a função X."},
    {role: "assistant", content: "Aqui está: function X()..."},
    {role: "user", content: "Agora melhore a performance."},
    {role: "assistant", content: "Feito. Otimizado."},
    {role: "user", content: "E sobre o banco de dados?"},
    {role: "assistant", content: "Use o DB_TAREFAS."},
    {role: "user", content: "Ok, vamos revisar tudo."} // 5ª mensagem do usuário
  ];

  console.log("--- INICIANDO TESTE DO AIService.gs ---");
  var contexto = prepararContextoIA(mockHistory);
  
  console.log("--- METADADOS GERADOS ---");
  console.log(JSON.stringify(contexto.metadata, null, 2));
  
  console.log("--- ÚLTIMA MENSAGEM (PAYLOAD MODIFICADO) ---");
  var lastMsg = contexto.messages[contexto.messages.length - 1];
  console.log("Role: " + lastMsg.role);
  console.log("Content: " + lastMsg.content);
  
  if (contexto.metadata.checkpointAtivado) {
    console.log("✅ SUCESSO: Gatilho de Checkpoint ativado corretamente.");
  } else {
    console.log("❌ FALHA: Gatilho não ativado.");
  }
}

/**
 * Garante a existência da aba de configuração da IA
 */
function garantirConfigIA() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsConfig = ss.getSheetByName(CONFIG_SISTEMA.ABA_CONFIG_IA);
  var criada = false;
  
  if (!wsConfig) {
    wsConfig = ss.insertSheet(CONFIG_SISTEMA.ABA_CONFIG_IA);
    wsConfig.appendRow(["CHAVE", "VALOR"]);
    wsConfig.appendRow(["GEMINI_MODEL", "gemini-2.5-flash"]);
    wsConfig.appendRow(["AUDIT_QUESITOS", "EQUILÍBRIO: Ativo deve ser igual ao Passivo.\nCAIXA: Saldo não pode ser negativo (credor).\nDESPESAS: Variação mensal não deve exceder 30%.\nRAZÃO SOCIAL: Nome no documento deve bater com o cadastro."]);
    wsConfig.appendRow(["PROMPT_AUDITORIA", "Aja como um auditor interno sênior. Sua tarefa é avaliar o balancete {{ATUAL}} com base na lista de {{QUESITOS}}.\n\nRegras de Resposta:\n1. Para cada quesito fornecido, avalie se foi [OK] ou [FALHA].\n2. Se houver falha, descreva o motivo brevemente.\n3. Se o balancete não passar em critérios críticos (Equilíbrio ou Caixa), comece a resposta com [REPROVADO].\n4. Caso contrário, finalize com [APROVADO].\n5. Use o {{HISTORICO}} para avaliar tendências se necessário.\n\nFormato de Saída:\nLISTA DE VERIFICAÇÃO:\n- [STATUS] Item: Motivo (se houver)"]);
    wsConfig.appendRow(["PROMPT_RELATORIO", "Aja como Consultor Estratégico Sênior em Inteligência Contábil. Sua missão é diagnosticar o cenário do cliente sem usar jargões espantosos. O texto gerado será transformado em um e-mail elegante de apresentação.\n\nUse português impecável do Brasil, de forma clara, motivacional e segura.\nDADOS:\n- OBRIGAÇÃO: {{ATUAL}}\n- HISTÓRICO: {{HISTORICO}}\n\nENTREGA (Use sintaxe Markdown):\n1. Uma saudação ausente (não coloque 'Prezado Cliente', pois o sistema já vai inserir nativamente o header).\n2. Crie uma seção de \"🎯 Diagnóstico Executivo\" de 1 parágrafo contendo o desempenho geral.\n3. Crie uma seção de \"📊 Análise de Caixa e Resultado\" listando os números centrais em tópicos ou pequena tabela Markdown, avaliando o ativo/passivo e caixa de maneira positiva, ou construtiva se houver atenção requirida.\n4. Crie uma seção \"💡 Insights e Ações Práticas\" com 2 a 3 conselhos diretos pro-negócio.\n\nImportante: NÃO entregue código HTML nativo, apenas o conteúdo Markdown incrivelmente bem formatado. O motor de email irá encapsular este texto dentro da estética VIP automaticamente. NUNCA diga [aprovado] ou gírias internas."]);
    wsConfig.appendRow(["CLIENTES_AUDITORIA_ATIVOS", ""]);
    
    // Aplicar layout básico
    wsConfig.getRange("A1:B1").setBackground("#1C3051").setFontColor("white").setFontWeight("bold");
    wsConfig.setFrozenRows(1);
    wsConfig.autoResizeColumns(1, 2);
    
    SpreadsheetApp.flush();
    criada = true;
  }
  
  return { sheet: wsConfig, criada: criada };
}

/**
 * Função consumida pelo Front-End (AuditConfig.html) para hidratar o Painel
 */
function obterConfigIACompl() {
  var resConfig = garantirConfigIA();
  var wsConfig = resConfig.sheet;
  var dataConfig = wsConfig.getDataRange().getValues();
  
  var retorno = {
    promptAuditoria: "",
    promptRelatorio: "",
    auditQuesitos: "",
    clientesAtivos: "",
    listaClientesAll: []
  };
  
  for (var i = 1; i < dataConfig.length; i++) {
    if (dataConfig[i][0] === "PROMPT_AUDITORIA") retorno.promptAuditoria = String(dataConfig[i][1]);
    if (dataConfig[i][0] === "PROMPT_RELATORIO") retorno.promptRelatorio = String(dataConfig[i][1]);
    if (dataConfig[i][0] === "AUDIT_QUESITOS") retorno.auditQuesitos = String(dataConfig[i][1]);
    if (dataConfig[i][0] === "CLIENTES_AUDITORIA_ATIVOS") retorno.clientesAtivos = String(dataConfig[i][1]);
  }
  
  // Obter a lista completa de clientes cadastrados para o checkbox
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  if (wsCli) {
    var dataCli = wsCli.getDataRange().getValues();
    for (var j = 1; j < dataCli.length; j++) {
      var nomeTemp = String(dataCli[j][1]).trim();
      if (nomeTemp) retorno.listaClientesAll.push(nomeTemp);
    }
  }
  retorno.listaClientesAll.sort();
  
  return retorno;
}

/**
 * Função consumida pelo Front-End (AuditConfig.html) para atualizar as Configurações
 */
function salvarConfigIACompl(payload) {
  var resConfig = garantirConfigIA();
  var wsConfig = resConfig.sheet;
  var dataConfig = wsConfig.getDataRange().getValues();
  
  if (payload.prop === "PROMPTS") {
    var encontrouAud = false, encontrouRel = false, encontrouQue = false;
    for (var i = 1; i < dataConfig.length; i++) {
      if (dataConfig[i][0] === "PROMPT_AUDITORIA") { wsConfig.getRange(i + 1, 2).setValue(payload.pa); encontrouAud = true; }
      if (dataConfig[i][0] === "PROMPT_RELATORIO") { wsConfig.getRange(i + 1, 2).setValue(payload.pr); encontrouRel = true; }
      if (dataConfig[i][0] === "AUDIT_QUESITOS")   { wsConfig.getRange(i + 1, 2).setValue(payload.qt); encontrouQue = true; }
    }
    if (!encontrouAud) wsConfig.appendRow(["PROMPT_AUDITORIA", payload.pa]);
    if (!encontrouRel) wsConfig.appendRow(["PROMPT_RELATORIO", payload.pr]);
    if (!encontrouQue) wsConfig.appendRow(["AUDIT_QUESITOS", payload.qt]);
  } 
  else if (payload.prop === "CLIENTES") {
    var encontrouCli = false;
    for (var k = 1; k < dataConfig.length; k++) {
      if (dataConfig[k][0] === "CLIENTES_AUDITORIA_ATIVOS") {
        wsConfig.getRange(k + 1, 2).setValue(payload.lista);
        encontrouCli = true;
      }
    }
    if (!encontrouCli) wsConfig.appendRow(["CLIENTES_AUDITORIA_ATIVOS", payload.lista]);
  }
  SpreadsheetApp.flush();
  return true;
}