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
    sucessos: [],
    avisos: []
  };

  try {
    // 1. VALIDAÇÃO DO OBJETO DE CONFIGURAÇÃO GLOBAl (Prevenção de Undefined)
    if (typeof CONFIG_SISTEMA === 'undefined' || !CONFIG_SISTEMA.STATUS) {
      relatorio.integro = false;
      relatorio.falhas.push("Objeto CONFIG_SISTEMA não carregado ou incompleto.");
    } else {
      relatorio.sucessos.push("Objeto CONFIG_SISTEMA carregado perfeitamente.");
    }

    // 2. VALIDAÇÃO DINÂMICA DE EXISTÊNCIA DE ABAS CRÍTICAS
    var ss = getSs();
    var keysConfig = Object.keys(CONFIG_SISTEMA);
    var qtdAbasValidadas = 0;
    
    keysConfig.forEach(function(key) {
      if (key.indexOf("ABA_") === 0) {
        var nomeAba = CONFIG_SISTEMA[key];
        if (!ss.getSheetByName(nomeAba)) {
          relatorio.integro = false;
          relatorio.falhas.push("Aba obrigatória NÃO localizada: " + nomeAba + " (Ref: " + key + ")");
        } else {
          qtdAbasValidadas++;
        }
      }
    });
    
    if (qtdAbasValidadas > 0) {
      relatorio.sucessos.push(qtdAbasValidadas + " Abas validadas com sucesso.");
    }

    // 3. VALIDAÇÃO DINÂMICA DE TODAS AS FUNÇÕES GLOBAIS
    // Identifica e conta dinamicamente quantas funções exclusivas existem no escopo atual.
    var funcoesEncontradas = 0;
    var funcoesFilaParaIgnorar = [
      "executarCheckUpSistema", "validarSchemaColunas", "comandoValidarSaudeSistema", 
      "getSafeStatus", "eval", "parseInt", "parseFloat", "isNaN", "isFinite", 
      "decodeURI", "decodeURIComponent", "encodeURI", "encodeURIComponent", "escape", "unescape"
    ]; // Ignora as funções deste próprio arquivo ou utilitárias JS para não sujar o count do usuário.
    
    var funcoesAusentes = false;
    
    try {
      var globais = Object.keys(this);
      globais.forEach(function(key) {
        if (typeof this[key] === 'function' && funcoesFilaParaIgnorar.indexOf(key) === -1) {
          // Garante que é uma função de usuário (não nativa complexa sem ser stringificável normal)
          funcoesEncontradas++;
        }
      });
      
      if (funcoesEncontradas > 20) { 
         // Assumindo um limite mínimo seguro de que o sistema possui dezenas de funções em seus packages 
         relatorio.sucessos.push("Rastreio Reflexivo Ativo: " + funcoesEncontradas + " funções operacionais identificadas na memória global.");
      } else {
         relatorio.integro = false;
         relatorio.falhas.push("Apenas " + funcoesEncontradas + " funções detectadas (possível falha de compilação de scripts).");
      }
    } catch(errFunc) {
      relatorio.integro = false;
      relatorio.falhas.push("Falha ao analisar funções do motor: " + errFunc.message);
    }

    // 4. VALIDAÇÃO DE SCHEMA (Posição de Colunas Críticas)
    if (relatorio.integro) {
      validarSchemaColunas(ss, relatorio);
    }

    // 5. REGISTRO E FEEDBACK
    if (!relatorio.integro) {
      var msgErro = "🚨 DETECÇÃO DE FALHAS: \n" + relatorio.falhas.join(" | ");
      registrarLogSistema("HEALTH_CHECK_FAIL", msgErro);
      console.error(msgErro);
    } else {
      console.log("✅ Sistema Íntegro: Check-up concluído com sucesso.");
    }

    return relatorio;

  } catch (e) {
    registrarLogSistema("HEALTH_CHECK_CRASH", e.message);
    return { integro: false, falhas: [e.message], sucessos: [], avisos: [] };
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
  
  // Verificação de REVISAO? na DB_REGRAS (Coluna M - Índice 12)
  var sheetRegras = ss.getSheetByName(CONFIG_SISTEMA.ABA_REGRAS);
  if (sheetRegras) {
    var rawReg = sheetRegras.getRange(1, 13).getValue();
    if (norm(rawReg) !== "REVISAO") {
       sheetRegras.getRange(1, 13).setValue("REVISAO?").setFontWeight("bold").setBackground("#f3f3f3");
       relatorio.avisos.push("Coluna M da DB_REGRAS corrigida para 'REVISAO?'");
    }
  }
  
  // Verificação da Coluna J (Índice 9) - ID_CONTROLE
  if (norm(cabecalho[9]) !== "ID_CONTROLE") {
    relatorio.integro = false;
    relatorio.falhas.push("Schema DB_TAREFAS violado: Coluna J esperava 'ID_CONTROLE', encontrou '" + cabecalho[9] + "'");
  }

  // Verificação de ACAO na DB_REGRAS (Coluna F ou H dependendo da versão, MaintenanceService usa F/índice 5)
  if (sheetRegras) {
    var capReg = sheetRegras.getRange(1, 1, 1, 12).getValues()[0];
    if (norm(capReg[5]) !== "ACAO") {
       relatorio.avisos.push("Aviso: Coluna F da DB_REGRAS não é 'ACAO'. Verifique o Schema do MaintenanceService.");
    }
  }

  // Verificação de ABA_WORKFLOWS
  var sheetWf = ss.getSheetByName(CONFIG_SISTEMA.ABA_WORKFLOWS);
  if (sheetWf) {
    var capWf = sheetWf.getRange(1, 1, 1, 4).getValues()[0]; 
    if (norm(capWf[0]) !== "FASE_ATUAL" || norm(capWf[1]) !== "PROXIMA_FASE") {
       relatorio.falhas.push("Schema DB_WORKFLOWS violado: Colunas A ou B inconsistentes.");
    }
    
    // Verificação de DEPARTAMENTO na DB_WORKFLOWS (Coluna D - Índice 3)
    if (norm(capWf[3]) !== "DEPARTAMENTO") {
      relatorio.falhas.push("Schema DB_WORKFLOWS violado: Coluna D esperava 'DEPARTAMENTO', encontrou '" + capWf[3] + "'");
    }
  }
}

/**
 * Handler para o menu ou gatilhos.
 */
function comandoValidarSaudeSistema() {
  var check = executarCheckUpSistema();
  var ui = SpreadsheetApp.getUi();
  
  if (check.integro) {
    var msgSucesso = "✅ TODAS AS CAMADAS ÍNTEGRAS\n\n";
    check.sucessos.forEach(function(suc) { msgSucesso += "✔️ " + suc + "\n"; });
    msgSucesso += "\nO sistema está 100% operacional para rodar rotinas pesadas e receber demandas de usuários.";
    ui.alert("🛡️ SAÚDE DO SISTEMA", msgSucesso, ui.ButtonSet.OK);
  } else {
    var msgErro = "🚨 FALHA CRÍTICA DETECTADA\n\n";
    check.falhas.forEach(function(falha) { msgErro += "❌ " + falha + "\n"; });
    msgErro += "\nO sistema pode apresentar erros graves de execução. Bloqueie as operações até que o problema seja resolvido.";
    ui.alert("🛡️ SAÚDE DO SISTEMA", msgErro, ui.ButtonSet.OK);
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
    'REVISAO': 'REVISAO',
    'REPROVADO': 'REPROVADO'
  };
  
  try {
    if (CONFIG_SISTEMA && CONFIG_SISTEMA.STATUS && CONFIG_SISTEMA.STATUS[tipo]) {
      return CONFIG_SISTEMA.STATUS[tipo];
    }
  } catch(e) {}
  
  return padrao[tipo] || tipo;
}

/**
 * Função Segura para obter Ação (Getter de Segurança)
 */
function getSafeAction(tipo) {
  var padrao = {
    'ENVIAR': 'ENVIAR',
    'ARQUIVAR': 'ARQUIVAR',
    'AUDITAR': 'AUDITAR',
    'COMUNICAR': 'COMUNICAR'
  };
  
  try {
    if (CONFIG_SISTEMA && CONFIG_SISTEMA.ACOES && CONFIG_SISTEMA.ACOES[tipo]) {
      return CONFIG_SISTEMA.ACOES[tipo];
    }
  } catch(e) {}
  
  var tUpper = String(tipo || "").toUpperCase().trim();
  if (tUpper.indexOf("ENVIAR") > -1) return padrao.ENVIAR;
  if (tUpper.indexOf("ARQUIVAR") > -1 || tUpper.indexOf("PROCESSAR") > -1) return padrao.ARQUIVAR;
  if (tUpper.indexOf("AUDITAR") > -1) return padrao.AUDITAR;
  if (tUpper.indexOf("COMUNICAR") > -1) return padrao.COMUNICAR;

  return padrao[tUpper] || padrao.ARQUIVAR;
}

/**
 * Função Segura para obter Departamento (Getter de Segurança)
 */
function getSafeDepto(tipo) {
  var padrao = {
    'CONTABIL': 'CONTABIL',
    'FISCAL': 'FISCAL',
    'PESSOAL': 'PESSOAL',
    'SOCIETARIO': 'SOCIETARIO'
  };
  
  try {
    if (CONFIG_SISTEMA && CONFIG_SISTEMA.DEPARTAMENTOS && CONFIG_SISTEMA.DEPARTAMENTOS[tipo]) {
      return CONFIG_SISTEMA.DEPARTAMENTOS[tipo];
    }
  } catch(e) {}
  
  var tUpper = String(tipo || "").toUpperCase().trim();
  if (tUpper.indexOf("CONTABIL") > -1) return padrao.CONTABIL;
  if (tUpper.indexOf("FISCAL") > -1) return padrao.FISCAL;
  if (tUpper.indexOf("PESSOAL") > -1 || tUpper.indexOf("RH") > -1) return padrao.PESSOAL;
  if (tUpper.indexOf("SOCIETARIO") > -1 || tUpper.indexOf("LEGAL") > -1) return padrao.SOCIETARIO;

  return padrao[tUpper] || padrao.CONTABIL; // Fallback para CONTABIL se for indefinido
}