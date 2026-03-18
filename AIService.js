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
  var promptBase = "", model = "gemini-2.5-flash";
  
  var chavePrompt = tipoPrompt === "RELATORIO" ? "PROMPT_RELATORIO" : "PROMPT_AUDITORIA";

  for (var i = 1; i < dataConfig.length; i++) {
    if (dataConfig[i][0] === chavePrompt) promptBase = dataConfig[i][1];
    if (dataConfig[i][0] === "GEMINI_MODEL") model = dataConfig[i][1];
  }

  if (!apiKey) return "API Key do Gemini não configurada nos Script Properties.";
  if (!promptBase) return "Prompt " + chavePrompt + " não localizado na configuração.";

  var promptFinal = promptBase
    .replace("{{ATUAL}}", JSON.stringify(dadosAtuais))
    .replace("{{HISTORICO}}", JSON.stringify(historico || []));

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
    wsConfig.appendRow(["AUDIT_QUESITOS", "ATIVO TOTAL, PASSIVO TOTAL, CAIXA, LUCRO/PREJUÍZO"]);
    wsConfig.appendRow(["PROMPT_AUDITORIA", "Aja como um auditor interno. Verifique se o balancete {{ATUAL}} segue as regras: 1. Ativo=Passivo. 2. Caixa positivo. 3. Se houver variação >30% em despesas comparado a {{HISTORICO}}, responda [REPROVADO] seguido do motivo. Caso contrário, responda [APROVADO]."]);
    wsConfig.appendRow(["PROMPT_RELATORIO", "Aja como um analista contábil sênior. Gere um relatório Markdown profissional para o cliente sobre o balancete {{ATUAL}}. Compare com histórico {{HISTORICO}} e destaque pontos positivos e de atenção. Não mencione códigos técnicos de auditoria interna."]);
    
    // Aplicar layout básico
    wsConfig.getRange("A1:B1").setBackground("#1C3051").setFontColor("white").setFontWeight("bold");
    wsConfig.setFrozenRows(1);
    wsConfig.autoResizeColumns(1, 2);
    
    SpreadsheetApp.flush();
    criada = true;
  }
  
  return { sheet: wsConfig, criada: criada };
}