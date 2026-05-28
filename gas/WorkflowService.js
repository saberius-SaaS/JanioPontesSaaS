/**
 * 🔄 WORKFLOW SERVICE v131.06
 * Motor de encadeamento automático de tarefas (Esteiras de Produção).
 * Adaptado para o Schema de 12 colunas e Tags Modulares.
 */

function acionarWorkflowFaseSeguinte(idTarefaAnterior, rowIdxTarefaAnterior) {
  try {
    var ss = getSs();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsWf = ss.getSheetByName(CONFIG_SISTEMA.ABA_WORKFLOWS);
    var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
    
    if (!wsWf || !wsCli || !wsTarefas) return;

    // 1. Captura dados da tarefa que acabou de ser concluída (12 colunas)
    var dadosTarefa = wsTarefas.getRange(rowIdxTarefaAnterior, 1, 1, 12).getValues()[0];
    var mesAnoRef = dadosTarefa[0];
    var cliente = dadosTarefa[1];
    var obrigacaoOriginal = String(dadosTarefa[2]).trim();
    var obrigacaoAtualNorm = norm(obrigacaoOriginal);
    var nivel = dadosTarefa[10]; // Mantém a prioridade do cliente

    var dataWf = wsWf.getDataRange().getValues();
    var wfRules = [];
    
    for (var w = 1; w < dataWf.length; w++) {
      if(String(dataWf[w][0]).trim() !== "") {
         wfRules.push({
            faseAtual: String(dataWf[w][0]).trim(),
            faseAtualNorm: norm(String(dataWf[w][0])),
            proximaFase: String(dataWf[w][1]).trim(),
            diasPrazo: parseInt(dataWf[w][2]) || 1,
            prazoIsUtil: String(dataWf[w][2]).trim().toUpperCase().indexOf("U") > -1,
            departamento: String(dataWf[w][3]).trim(),
            acao: getSafeAction(String(dataWf[w][4]).trim()),
            respOriginal: String(dataWf[w][5]).trim(),
            respUpper: String(dataWf[w][5]).trim().toUpperCase()
         });
      }
    }
    
    // Ordenação por especificidade (mais longas primeiro)
    wfRules.sort((a, b) => b.faseAtual.length - a.faseAtual.length);

    var faseSeguinte = null;
    var complementoExtraido = "";

    // 2. Busca a regra de transição
    for (var i = 0; i < wfRules.length; i++) {
      var regra = wfRules[i];
      var baseNorm = regra.faseAtualNorm;
      
      if (obrigacaoAtualNorm === baseNorm) {
        faseSeguinte = regra;
        complementoExtraido = "";
        break;
      } else if (obrigacaoAtualNorm.indexOf(baseNorm) === 0) {
        // Verifica se logo após a base há um separador (espaço, hífen, underline)
        var charAfter = obrigacaoAtualNorm.charAt(baseNorm.length);
        if (charAfter === ' ' || charAfter === '-') {
            faseSeguinte = regra;
            var sobra = obrigacaoOriginal.substring(regra.faseAtual.length).trim();
            if (sobra.indexOf("-") === 0) sobra = sobra.substring(1).trim();
            complementoExtraido = sobra;
            break;
        }
      }
    }

    if (!faseSeguinte || !faseSeguinte.proximaFase) return; 

    // 3. Cálculo de Datas para a Próxima Fase
    var hoje = new Date();
    var novoPrazoInterno;
    
    if (faseSeguinte.prazoIsUtil) {
      novoPrazoInterno = adicionarDiasUteis(hoje, faseSeguinte.diasPrazo);
    } else {
      novoPrazoInterno = new Date(hoje.getTime() + (faseSeguinte.diasPrazo * 24 * 60 * 60 * 1000));
    }
    // Para workflows, o vencimento legal costuma ser o mesmo do prazo interno, 
    // a menos que a tarefa gerada seja uma obrigação fiscal principal.
    var novoVencimentoLegal = new Date(novoPrazoInterno); 

    // 4. Identificação do Responsável
    var responsavel = "SISTEMA";
    var dataCli = getSheetDataCached(CONFIG_SISTEMA.ABA_CLIENTES, CACHE_CONFIG.KEYS.CLIENTES);
    for (var c = 1; c < dataCli.length; c++) {
      if (norm(dataCli[c][1]) === norm(cliente)) {
        if (faseSeguinte.respUpper.indexOf("FISCAL") > -1) responsavel = dataCli[c][7] || "SISTEMA";
        else if (faseSeguinte.respUpper.indexOf("CONTABIL") > -1) responsavel = dataCli[c][8] || "SISTEMA";
        else if (faseSeguinte.respUpper.indexOf("PESSOAL") > -1) responsavel = dataCli[c][9] || "SISTEMA";
        else if (faseSeguinte.respUpper.indexOf("SOCIETARIO") > -1) responsavel = dataCli[c][10] || "SISTEMA";
        else responsavel = faseSeguinte.respOriginal; 
        break;
      }
    }

    var novoId = "WF_" + new Date().getTime();
    var nomeNovaObrigacao = faseSeguinte.proximaFase + (complementoExtraido !== "" ? " - " + complementoExtraido : "");
    
    // 5. Injeção da Nova Fase (12 Colunas)
    wsTarefas.appendRow([
      mesAnoRef,              // A: MES_ANO
      cliente,                // B: CLIENTE
      nomeNovaObrigacao,      // C: OBRIGACAO
      novoPrazoInterno,       // D: VENCIMENTO
      faseSeguinte.departamento, // E: DEPARTAMENTO
      CONFIG_SISTEMA.STATUS.PENDENTE, // F: STATUS
      "",                     // G: PROTOCOLO
      faseSeguinte.acao,      // H: ACAO
      responsavel,            // I: RESPONSAVEL
      novoId,                 // J: ID_CONTROLE
      nivel,                  // K: NIVEL
      novoVencimentoLegal     // L: VENCIMENTO_LEGAL
    ]);
    
    wsTarefas.getRange(wsTarefas.getLastRow(), 4).setNumberFormat("dd/MM/yyyy");
    wsTarefas.getRange(wsTarefas.getLastRow(), 12).setNumberFormat("dd/MM/yyyy");
    
    SpreadsheetApp.flush();
    reordenarTarefasElite();
    invalidarCacheSistema(); // Garante que a nova fase apareça nas Prioridades
    
    registrarLogSistema("WORKFLOW_TRIGGER", "De: " + obrigacaoOriginal + " -> Para: " + nomeNovaObrigacao);

  } catch (e) {
    registrarLogSistema("WORKFLOW_ERR", e.message);
  }
}