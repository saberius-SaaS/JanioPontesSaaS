/**
 * ⚙️ TASK CORE SERVICE v131.10
 * Motor de Geração Híbrido: Whitelist (Tags) + Blacklist (Exceções) + Sincronismo Total.
 */

function safeGetMesAnoStr(valor) {
  if (valor instanceof Date) return Utilities.formatDate(valor, "GMT-3", "MM/yyyy");
  return String(valor).trim();
}

function gerarTarefasDoMes() {
  var lock = LockService.getScriptLock();
  try { 
    lock.waitLock(30000); 
  } catch (e) { 
    SpreadsheetApp.getUi().alert("⏳ Sistema ocupado. Tente novamente em instantes.");
    return;
  }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
    var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);
    
    // Cache de dados para performance
    var dataCli = getSheetDataCached(CONFIG_SISTEMA.ABA_CLIENTES, CACHE_CONFIG.KEYS.CLIENTES);
    var dataReg = getSheetDataCached(CONFIG_SISTEMA.ABA_REGRAS, CACHE_CONFIG.KEYS.REGRAS);
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
        perfis: String(dataCli[c][14] || "") 
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
    var novasTarefas = [];
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
          
          if (!dtPrazoInterno || dtPrazoInterno < inicioMesAtual) continue;

          // Definir Responsável atual
          var dep = norm(dataReg[r][3]), resp = "SISTEMA";
          if (dep.indexOf("FISCAL") > -1) resp = cli.fiscal;
          else if (dep.indexOf("CONTABIL") > -1) resp = cli.contabil;
          else if (dep.indexOf("PESSOAL") > -1) resp = cli.pessoal;
          else if (dep.indexOf("SOCIETARIO") > -1) resp = cli.societario;

          // Verificar se já existe no mapa global (Histórico ou já processado)
          if (mapaGlobalExistencia[hash]) continue;

          // Adicionamos ao mapa de processamento
          mapaTarefasAtivas[hash] = {
            acao: "MANTER_OU_SINCRONIZAR",
            dados: [
              mesAnoRef, cli.nomeOriginal, obrigOriginal, dtPrazoInterno, dataReg[r][3],
              CONFIG_SISTEMA.STATUS.PENDENTE, "", dataReg[r][5], resp,
              "ID_" + new Date().getTime() + (countId++), cli.nivel, dtVencimentoLegal
            ]
          };
        }
      }
    }

    // 4. APLICAÇÃO NA PLANILHA (RECONSTRUÇÃO DA DB_TAREFAS)
    var novasLinhasDB = [dataTf[0]]; // Cabeçalho
    var hashesProcessados = {};

    // Primeiro, analisamos o que já estava na planilha
    for (var i = 1; i < dataTf.length; i++) {
      var h = norm(safeGetMesAnoStr(dataTf[i][0])) + "|" + norm(dataTf[i][1]) + "|" + norm(dataTf[i][2]);
      var statusAtual = String(dataTf[i][5]).toUpperCase();
      
      // Se a tarefa está ENTREGUE, mantemos como está
      if (statusAtual === CONFIG_SISTEMA.STATUS.ENTREGUE) {
        novasLinhasDB.push(dataTf[i]);
        hashesProcessados[h] = true;
        continue;
      }

      // Se é PENDENTE, verificamos o que o motor decidiu
      var decisao = mapaTarefasAtivas[h];
      if (decisao && decisao.acao === "MANTER_OU_SINCRONIZAR") {
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
      } else {
        // Se a decisão foi EXCLUIR ou se a regra não existe mais, a tarefa some da lista
        tarefasExcluidasCount++;
      }
    }

    // Segundo, adicionamos as que são realmente novas (não estavam na planilha)
    for (var hKey in mapaTarefasAtivas) {
      if (!hashesProcessados[hKey] && mapaTarefasAtivas[hKey].acao === "MANTER_OU_SINCRONIZAR") {
        novasLinhasDB.push(mapaTarefasAtivas[hKey].dados);
      }
    }

    // 5. SALVAMENTO E ORDENAÇÃO
    wsTarefas.getDataRange().clearContent();
    wsTarefas.getRange(1, 1, novasLinhasDB.length, 12).setValues(novasLinhasDB);
    
    SpreadsheetApp.flush();
    reordenarTarefasElite();
    registrarLogSistema("SYNC_V131.10", "Atualizadas: " + tarefasAtualizadasCount + " | Expurgos: " + tarefasExcluidasCount);

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