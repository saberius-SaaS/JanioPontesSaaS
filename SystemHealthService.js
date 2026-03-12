/**
 * 🛡️ SYSTEM HEALTH SERVICE (SENTINEL) v1.0
 * Objetivo: Validar a integridade das referências globais, abas e colunas.
 * Previne erros de regressão e falhas de carregamento (Runtime Errors).
 */

/**
 * Executa um check-up completo no sistema.
 * Pode ser chamado no onOpen ou antes de funções críticas.
 * @return {Object} Resultado com status e logs de erros.
 */
function executarCheckUpSistema() {
  var relatorio = {
    integro: true,
    falhas: [],
    avisos: []
  };

  try {
    // 1. VALIDAÇÃO DO OBJETO DE CONFIGURAÇÃO (Prevenção de Undefined)
    if (typeof CONFIG_SISTEMA === 'undefined' || !CONFIG_SISTEMA.STATUS) {
      relatorio.integro = false;
      relatorio.falhas.push("Objeto CONFIG_SISTEMA não carregado ou incompleto.");
    }

    // 2. VALIDAÇÃO DE EXISTÊNCIA DE ABAS CRÍTICAS
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var abasObrigatorias = [
      CONFIG_SISTEMA.ABA_USUARIOS,
      CONFIG_SISTEMA.ABA_CLIENTES,
      CONFIG_SISTEMA.ABA_REGRAS,
      CONFIG_SISTEMA.ABA_WORKFLOWS,
      CONFIG_SISTEMA.ABA_TAREFAS,
      CONFIG_SISTEMA.ABA_SOLICITACOES,
      CONFIG_SISTEMA.ABA_PROTOCOLOS,
      CONFIG_SISTEMA.ABA_HISTORICO,
      CONFIG_SISTEMA.ABA_RISCO,
      CONFIG_SISTEMA.ABA_LOGS,
    ];

    abasObrigatorias.forEach(function(nomeAba) {
      if (!ss.getSheetByName(nomeAba)) {
        relatorio.integro = false;
        relatorio.falhas.push("Aba obrigatória não localizada: " + nomeAba);
      }
    });

    // 3. VALIDAÇÃO DE SCHEMA (Posição de Colunas Críticas)
    if (relatorio.integro) {
      validarSchemaColunas(ss, relatorio);
    }

    // 4. REGISTRO E FEEDBACK
    if (!relatorio.integro) {
      var msgErro = "🚨 ERRO DE INTEGRIDADE: \n" + relatorio.falhas.join("\n");
      registrarLogSistema("HEALTH_CHECK_FAIL", msgErro);
      console.error(msgErro);
    } else {
      console.log("✅ Sistema Íntegro: Check-up concluído com sucesso.");
    }

    return relatorio;

  } catch (e) {
    registrarLogSistema("HEALTH_CHECK_CRASH", e.message);
    return { integro: false, falhas: [e.message] };
  }
}

/**
 * Valida se as colunas principais estão onde o código espera que estejam.
 */
function validarSchemaColunas(ss, relatorio) {
  var sheetTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var cabecalho = sheetTarefas.getRange(1, 1, 1, 12).getValues()[0];
  
  // Verificação da Coluna F (Índice 5) - STATUS
  if (norm(cabecalho[5]) !== "STATUS") {
    relatorio.integro = false;
    relatorio.falhas.push("Schema DB_TAREFAS violado: Coluna F esperava 'STATUS', encontrou '" + cabecalho[5] + "'");
  }
  
  // Verificação da Coluna J (Índice 9) - ID_CONTROLE
  if (norm(cabecalho[9]) !== "ID_CONTROLE") {
    relatorio.integro = false;
    relatorio.falhas.push("Schema DB_TAREFAS violado: Coluna J esperava 'ID_CONTROLE', encontrou '" + cabecalho[9] + "'");
  }
}

/**
 * Handler para o menu ou gatilhos.
 */
function comandoValidarSaudeSistema() {
  var check = executarCheckUpSistema();
  if (check.integro) {
    SpreadsheetApp.getUi().alert("✅ SISTEMA ÍNTEGRO\n\nTodas as abas, colunas e configurações globais foram validadas com sucesso.");
  } else {
    SpreadsheetApp.getUi().alert("🚨 FALHA DETECTADA\n\n" + check.falhas.join("\n") + "\n\nO sistema pode apresentar erros de execução.");
  }
}

/**
 * Função Segura para obter Status (Getter de Segurança)
 * Substitui o acesso direto a CONFIG_SISTEMA.STATUS.X
 */
function getSafeStatus(tipo) {
  var padrao = {
    'PENDENTE': 'PENDENTE',
    'ENTREGUE': 'ENTREGUE',
    'ABERTA': 'ABERTA'
  };
  
  try {
    if (CONFIG_SISTEMA && CONFIG_SISTEMA.STATUS && CONFIG_SISTEMA.STATUS[tipo]) {
      return CONFIG_SISTEMA.STATUS[tipo];
    }
  } catch(e) {}
  
  return padrao[tipo] || tipo;
}