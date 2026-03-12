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