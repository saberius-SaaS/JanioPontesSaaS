/**
 * ⚙️ TASK CORE SERVICE v131.10
 * Motor de Geração Híbrido: Whitelist (Tags) + Blacklist (Exceções) + Sincronismo Total.
 */

function safeGetMesAnoStr(valor) {
  if (valor instanceof Date) {
    var m = valor.getMonth() + 1;
    var y = valor.getFullYear();
    return (m < 10 ? "0" + m : m) + "/" + y;
  }
  return String(valor).trim();
}

function gerarTarefasDoMes() {
  var lock = LockService.getScriptLock();
  try { 
    lock.waitLock(30000); 
  } catch (e) { 
    try {
      SpreadsheetApp.getUi().alert("⏳ Sistema ocupado. Tente novamente em instantes.");
    } catch (uiErr) {}
    return "⏳ Sistema ocupado. Tente novamente em instantes.";
  }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    
    // Busca dados ORIGINAIS da planilha (sem cache) para garantir sincronismo real
    var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
    var wsReg = ss.getSheetByName(CONFIG_SISTEMA.ABA_REGRAS);
    if (!wsCli || !wsReg) return "Erro: Abas mestres não encontradas.";

    var dataCli = wsCli.getDataRange().getValues();
    var dataReg = wsReg.getDataRange().getValues();
    var dataTf = wsTarefas.getDataRange().getValues();
    var dataHist = wsHist ? wsHist.getDataRange().getValues() : [[]];
    
    var hoje = new Date();
    var inicioMesAtual = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    
    // 1. MAPEAMENTO DOS CLIENTES (Regime, Responsáveis, Tags e Exceções)
    var mapaClientes = {};
    for(var c=1; c<dataCli.length; c++) {
      var cliNome = String(dataCli[c][1]); if (!cliNome) continue;
      var cliNorm = norm(cliNome);
      
      var excStr = String(dataCli[c][11] || "");
      var excecoes = excStr.split(',').map(e => norm(e)).filter(e => e !== "");
      
      mapaClientes[cliNorm] = {
        nomeOriginal: cliNome,
        regime: norm(dataCli[c][6]),
        fiscal: dataCli[c][7] || "SISTEMA",
        contabil: dataCli[c][8] || "SISTEMA",
        pessoal: dataCli[c][9] || "SISTEMA",
        societario: dataCli[c][10] || "SISTEMA",
        excecoes: excecoes,
        nivel: dataCli[c][13] || "1",
        perfis: String(dataCli[c][14] || ""),
        responsavelGeral: String(dataCli[c][3] || "SISTEMA").toLowerCase().trim(),
        status: String(dataCli[c][15] || "ATIVO").toUpperCase().trim()
      };
    }

    // 2. FILTRO DE EXISTÊNCIA E MAPA DE TAREFAS ATUAIS
    var mapaTarefasAtivas = {}; // Para gerenciar linhas da DB_TAREFAS
    var mapaGlobalExistencia = {}; // Para evitar duplicidade (inclui histórico)

    // Lendo Histórico (Apenas Entregues)
    for(var h=1; h<dataHist.length; h++) {
      if (String(dataHist[h][5]).toUpperCase() === CONFIG_SISTEMA.STATUS.ENTREGUE) {
        mapaGlobalExistencia[norm(safeGetMesAnoStr(dataHist[h][0])) + "|" + norm(dataHist[h][1]) + "|" + norm(dataHist[h][2])] = true;
      }
    }

    // 3. VARREDURA RETROATIVA E GERAÇÃO/SINCRONISMO
    var novasTarefasCount = 0;
    var tarefasExcluidasCount = 0;
    var tarefasAtualizadasCount = 0;
    var countId = 0;

    // Processamos os meses da janela
    for (var m = 0; m >= (CONFIG_SISTEMA.JANELA_RETROATIVA_MESES * -1); m--) {
      var competenciaDate = new Date(hoje.getFullYear(), hoje.getMonth() + m, 1);
      var mesAnoRef = Utilities.formatDate(competenciaDate, "GMT-3", "MM/yyyy");
      var mesInt = competenciaDate.getMonth() + 1;
      
      for (var cliKey in mapaClientes) {
        var cli = mapaClientes[cliKey];
        
        // ⚡ REGRA MESTRA DE INATIVOS: Se o cliente está inativo, ele não gera NENHUMA tarefa nova retroativa
        if (cli.status === "INATIVO") continue;
        
        for (var r = 1; r < dataReg.length; r++) {
          var obrigOriginal = String(dataReg[r][1] || "").trim();
          if (!obrigOriginal) continue;
          var obrigNorm = norm(obrigOriginal);
          
          // --- VALIDAÇÃO HÍBRIDA (TAGS + EXCEÇÕES + REGIME) ---
          var possuiTag = verificarAcessoPorTag(cli.perfis, dataReg[r][11]);
          var ehExcecao = (cli.excecoes.indexOf(obrigNorm) > -1);
          var regimeBate = (norm(dataReg[r][4]) === "TODOS" || norm(dataReg[r][4]) === cli.regime);
          var mesesRegra = String(dataReg[r][6] || "");
          var mesBate = (mesesRegra === "" || mesesRegra.split(",").map(x => parseInt(x.trim())).indexOf(mesInt) > -1);

          var hash = norm(mesAnoRef) + "|" + cliKey + "|" + obrigNorm;

          // Se a tarefa não deve existir (perdeu tag ou virou exceção ou regime mudou)
          if (!possuiTag || ehExcecao || !regimeBate || !mesBate) {
            // Se ela estiver na DB_TAREFAS como Pendente, marcamos para remoção no final
            mapaTarefasAtivas[hash] = { acao: "EXCLUIR" };
            continue; 
          }

          // Se a tarefa deve existir, calculamos os dados atuais da regra
          var dtPrazoInterno = calcularDataComplexa(competenciaDate, dataReg[r][2], dataReg[r][8], dataReg[r][10]);
          var dtVencimentoLegal = calcularDataComplexa(competenciaDate, dataReg[r][9], dataReg[r][8], dataReg[r][10]);
          
          if (!dtPrazoInterno) continue;

          // Definir Responsável atual (Com Fallback para Responsável Geral do Cliente)
          var dep = norm(dataReg[r][3]), resp = cli.responsavelGeral || "SISTEMA";
          if (dep.indexOf("FISCAL") > -1) resp = cli.fiscal;
          else if (dep.indexOf("CONTABIL") > -1) resp = cli.contabil;
          else if (dep.indexOf("PESSOAL") > -1) resp = cli.pessoal;
          else if (dep.indexOf("SOCIETARIO") > -1) resp = cli.societario;

          if (!mapaGlobalExistencia[hash]) {
            // A regra mestre: só geramos NOVAS tarefas se o vencimento é de agora em diante (ou neste mês)
            var acaoSincronismo = (dtPrazoInterno >= inicioMesAtual) ? "CRIAR_OU_SINCRONIZAR" : "SINCRONIZAR_BACKLOG";

            // Adicionamos ao mapa de processamento
            mapaTarefasAtivas[hash] = {
              acao: acaoSincronismo,
              dados: [
                mesAnoRef, cli.nomeOriginal, obrigOriginal, dtPrazoInterno, dataReg[r][3],
                CONFIG_SISTEMA.STATUS.PENDENTE, "", dataReg[r][5], resp,
                "ID_" + new Date().getTime() + (countId++), cli.nivel, dtVencimentoLegal
              ]
            };
          }
        }
      }
    }

    // 4. APLICAÇÃO NA PLANILHA (RECONSTRUÇÃO DA DB_TAREFAS)
    var novasLinhasDB = [dataTf[0]]; // Cabeçalho
    var hashesProcessados = {};

    // Primeiro, analisamos o que já estava na planilha
    for (var i = 1; i < dataTf.length; i++) {
      var statusAtual = String(dataTf[i][5]).toUpperCase();
      var cliNormBanco = norm(dataTf[i][1]);
      var cliDados = mapaClientes[cliNormBanco];
      
      // EXCLUSÃO INCONDICIONAL: Clientes Inativos ou Removidos da base perdem suas pendências instantaneamente
      if (statusAtual === CONFIG_SISTEMA.STATUS.PENDENTE && (!cliDados || cliDados.status === "INATIVO")) {
        tarefasExcluidasCount++;
        continue; // Ignora TODA E QUALQUER proteção de legado, expulsando a tarefa do vetor
      }

      var h = norm(safeGetMesAnoStr(dataTf[i][0])) + "|" + cliNormBanco + "|" + norm(dataTf[i][2]);
      
      // Se a tarefa está ENTREGUE, mantemos como está
      if (statusAtual === CONFIG_SISTEMA.STATUS.ENTREGUE) {
        novasLinhasDB.push(dataTf[i]);
        hashesProcessados[h] = true;
        continue;
      }

      // Se é PENDENTE, verificamos o que o motor decidiu
      var decisao = mapaTarefasAtivas[h];
      if (decisao && (decisao.acao === "CRIAR_OU_SINCRONIZAR" || decisao.acao === "SINCRONIZAR_BACKLOG")) {
        var d = decisao.dados;
        // SINCRONISMO: Atualizamos os campos da linha existente com os dados frescos
        var linhaSincronizada = [...dataTf[i]];
        linhaSincronizada[3] = d[3];  // Vencimento
        linhaSincronizada[4] = d[4];  // Departamento
        linhaSincronizada[7] = d[7];  // Ação
        linhaSincronizada[8] = d[8];  // Responsável
        linhaSincronizada[10] = d[10]; // Nível
        linhaSincronizada[11] = d[11]; // Vencimento Legal

        // Verificamos se houve mudança real para o log
        if (linhaSincronizada.join("|") !== dataTf[i].join("|")) tarefasAtualizadasCount++;

        novasLinhasDB.push(linhaSincronizada);
        hashesProcessados[h] = true;
      } else if (decisao && decisao.acao === "EXCLUIR") {
        // PROTEÇÃO CONTRA DELEÇÃO DE BACKLOG VENCIDO:
        var vctoTf = dataTf[i][3];
        var dtVctoAnterior = (vctoTf instanceof Date) ? vctoTf : new Date(vctoTf);
        if (!isNaN(dtVctoAnterior.getTime()) && dtVctoAnterior < inicioMesAtual) {
          // Se estava ativa no banco e o vencimento já passou há muito tempo,
          // preservamos ela, mas atualizamos o Responsável se estiver Pendente/Revisão
          var linhaPreservada = [...dataTf[i]];
          if (cliDados && (statusAtual === CONFIG_SISTEMA.STATUS.PENDENTE || statusAtual === CONFIG_SISTEMA.STATUS.REVISAO)) {
            var depT = norm(linhaPreservada[4]);
            var nResp = cliDados.responsavelGeral || "SISTEMA";
            if (depT.indexOf("FISCAL") > -1) nResp = cliDados.fiscal;
            else if (depT.indexOf("CONTABIL") > -1) nResp = cliDados.contabil;
            else if (depT.indexOf("PESSOAL") > -1) nResp = cliDados.pessoal;
            else if (depT.indexOf("SOCIETARIO") > -1) nResp = cliDados.societario;
            
            if (linhaPreservada[8] !== nResp) {
              linhaPreservada[8] = nResp;
              tarefasAtualizadasCount++;
            }
          }
          novasLinhasDB.push(linhaPreservada);
        } else {
          tarefasExcluidasCount++;
        }
      } else {
        // Se não há decisão (fora da janela ou regra removida), preservamos o Backlog Legado
        // MAS atualizamos o responsável se for PENDENTE ou REVISÃO
        var linhaLegada = [...dataTf[i]];
        if (cliDados && (statusAtual === CONFIG_SISTEMA.STATUS.PENDENTE || statusAtual === CONFIG_SISTEMA.STATUS.REVISAO)) {
          var depL = norm(linhaLegada[4]);
          var nRespL = cliDados.responsavelGeral || "SISTEMA";
          if (depL.indexOf("FISCAL") > -1) nRespL = cliDados.fiscal;
          else if (depL.indexOf("CONTABIL") > -1) nRespL = cliDados.contabil;
          else if (depL.indexOf("PESSOAL") > -1) nRespL = cliDados.pessoal;
          else if (depL.indexOf("SOCIETARIO") > -1) nRespL = cliDados.societario;
          
          if (linhaLegada[8] !== nRespL) {
             linhaLegada[8] = nRespL;
             tarefasAtualizadasCount++;
          }
        }
        novasLinhasDB.push(linhaLegada);
      }
    }

    // Segundo, adicionamos as que são realmente novas (não estavam na planilha)
    for (var hKey in mapaTarefasAtivas) {
      // ⚡ APENAS cria tarefas novas do ciclo atual ou de ciclos que vencem agora
      if (!hashesProcessados[hKey] && mapaTarefasAtivas[hKey].acao === "CRIAR_OU_SINCRONIZAR") {
        novasLinhasDB.push(mapaTarefasAtivas[hKey].dados);
        novasTarefasCount++;
      }
    }

    // 5. SALVAMENTO E ORDENAÇÃO
    wsTarefas.getDataRange().clearContent();
    wsTarefas.getRange(1, 1, novasLinhasDB.length, 12).setValues(novasLinhasDB);
    
    SpreadsheetApp.flush();
    reordenarTarefasElite();
    registrarLogSistema("SYNC_V131.10", "Sinc: " + tarefasAtualizadasCount + " | Novas: " + novasTarefasCount + " | Expurgos: " + tarefasExcluidasCount);
    invalidarCacheSistema(); // ⚡ Garante visibilidade imediata no Portal
    return "Sincronização concluída: " + tarefasAtualizadasCount + " atualizadas, " + novasTarefasCount + " novas, " + tarefasExcluidasCount + " expurgos.";

  } finally { 
    lock.releaseLock();
  }
}

/**
 * Ordenação conforme Seção 4.1: Status -> Vencimento -> Nível
 */
function reordenarTarefasElite() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ws = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  if (!ws) return;
  var lr = ws.getLastRow();
  if (lr <= 1) return;
  
  var range = ws.getRange(2, 1, lr - 1, 12);
  var data = range.getValues();
  
  data.sort(function(a, b) {
    // 1. Status (PENDENTE antes de ENTREGUE)
    var sA = String(a[5]).toUpperCase();
    var sB = String(b[5]).toUpperCase();
    if (sA !== sB) return (sA === "PENDENTE") ? -1 : 1;
    
    // 2. Vencimento (Crescente)
    var tA = (a[3] instanceof Date) ? a[3].getTime() : 0;
    var tB = (b[3] instanceof Date) ? b[3].getTime() : 0;
    if (tA !== tB) return tA - tB;
    
    // 3. Nível (Decrescente: 5 -> 1)
    var nA = parseInt(a[10]) || 0;
    var nB = parseInt(b[10]) || 0;
    return nB - nA;
  });
  
  range.setValues(data);
}

/**
 * Busca ultrarrápida das tarefas pendentes de um cliente via Cache
 */
function getPendenciasCliente(clienteNome) {
  try {
    // Busca do Cache para não onerar o banco de dados e evitar Timeout
    var data = getSheetDataCached(CONFIG_SISTEMA.ABA_TAREFAS, "DATA_TAREFAS");
    
    var clienteNorm = norm(clienteNome);
    var resultados = [];
    
    for (var i = 1; i < data.length; i++) {
      if (String(data[i][5]).toUpperCase() === CONFIG_SISTEMA.STATUS.PENDENTE && norm(data[i][1]) === clienteNorm) {
        
        var rawVcto = data[i][3];
        var vencFmt = (rawVcto instanceof Date) ? Utilities.formatDate(rawVcto, "GMT-3", "dd/MM/yyyy") : String(rawVcto);
        
        resultados.push({ 
          id: data[i][9], 
          nome: data[i][2], 
          vencimento: vencFmt, 
          acao: data[i][7] 
        });
      }
    }
    return resultados;
  } catch (e) {
    registrarLogSistema("GET_PEND_ERR", e.message);
    return [];
  }
}