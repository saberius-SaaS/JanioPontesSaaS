/**
 * 🔬 DEBUG v2: Simulação COMPLETA do motor de geração para um cliente/regra específico.
 * Replica fielmente o gerarTarefasDoMes e loga cada decisão.
 * >>> Execute diagnosticarTarefa() no Editor do Apps Script <<<
 */
function diagnosticarTarefa() {
  var CLIENTE_ALVO = "MINEIROS CHINELOS LTDA";
  var REGRA_ALVO = "FOLHA_PAGTO_SAL";

  var ss = getSs();
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  var wsReg = ss.getSheetByName(CONFIG_SISTEMA.ABA_REGRAS);
  var wsTarefas = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var wsHist = ss.getSheetByName(CONFIG_SISTEMA.ABA_HISTORICO);

  var dataCli = wsCli.getDataRange().getValues();
  var dataReg = wsReg.getDataRange().getValues();
  var dataTf = wsTarefas.getDataRange().getValues();
  var dataHist = wsHist ? wsHist.getDataRange().getValues() : [[]];

  var hoje = new Date();
  var inicioMesAtual = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  var cliNormAlvo = norm(CLIENTE_ALVO);
  var regraNormAlvo = norm(REGRA_ALVO);

  console.log("═══════════════════════════════════════════════════");
  console.log("🔬 DIAGNÓSTICO v2 — SIMULAÇÃO COMPLETA DO MOTOR");
  console.log("═══════════════════════════════════════════════════");
  console.log("Cliente: " + CLIENTE_ALVO + " | Regra: " + REGRA_ALVO);
  console.log("Data: " + hoje + " | InicioMes: " + inicioMesAtual);

  // ===== ETAPA 1: VERIFICAR DUPLICATAS NA DB_REGRAS =====
  console.log("\n📌 ETAPA 1: VERIFICAR DUPLICATAS NA DB_REGRAS");
  var ocorrenciasRegra = [];
  for (var r = 1; r < dataReg.length; r++) {
    if (norm(dataReg[r][1]) === regraNormAlvo) {
      ocorrenciasRegra.push({
        linha: r + 1,
        nome: String(dataReg[r][1]).trim(),
        grupos: String(dataReg[r][11] || ""),
        regime: String(dataReg[r][4] || ""),
        dia: String(dataReg[r][2] || ""),
        desloca: String(dataReg[r][8] || "")
      });
    }
  }
  console.log("   Ocorrências encontradas: " + ocorrenciasRegra.length);
  ocorrenciasRegra.forEach(function(o) {
    console.log("   → Linha " + o.linha + ": [" + o.nome + "] Grupos=[" + o.grupos + "] Regime=[" + o.regime + "] Dia=[" + o.dia + "] Desloca=[" + o.desloca + "]");
  });
  if (ocorrenciasRegra.length > 1) {
    console.log("   ⚠️ ALERTA: REGRA DUPLICADA! A última iteração SOBRESCREVE as anteriores no mapaTarefasAtivas!");
  }

  // ===== ETAPA 2: SIMULAR CONSTRUÇÃO DO mapaClientes =====
  console.log("\n📌 ETAPA 2: VERIFICAR CLIENTE NO mapaClientes");
  var mapaClientes = {};
  for (var c = 1; c < dataCli.length; c++) {
    var cliNome = String(dataCli[c][1]); if (!cliNome) continue;
    var cliNorm = norm(cliNome);
    var excStr = String(dataCli[c][11] || "");
    var excecoes = excStr.split(',').map(function(e) { return norm(e); }).filter(function(e) { return e !== ""; });
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
  
  var cli = mapaClientes[cliNormAlvo];
  if (!cli) {
    console.log("   ❌ CLIENTE NÃO ENCONTRADO no mapaClientes (chave normalizada: " + cliNormAlvo + ")");
    return;
  }
  console.log("   ✅ Cliente encontrado. Status=" + cli.status + " | Regime=" + cli.regime + " | Perfis=[" + cli.perfis + "]");

  // ===== ETAPA 3: SIMULAR FASE DE GERAÇÃO (EXATAMENTE COMO O MOTOR) =====
  console.log("\n📌 ETAPA 3: SIMULAR FASE DE GERAÇÃO (loop triplo: meses × clientes × regras)");
  
  var mapaGlobalExistencia = {};
  for (var h = 1; h < dataHist.length; h++) {
    if (String(dataHist[h][5]).toUpperCase() === CONFIG_SISTEMA.STATUS.ENTREGUE) {
      mapaGlobalExistencia[norm(safeGetMesAnoStr(dataHist[h][0])) + "|" + norm(dataHist[h][1]) + "|" + norm(dataHist[h][2])] = true;
    }
  }

  var mapaTarefasAtivas = {};
  var countId = 0;

  for (var m = 0; m >= (CONFIG_SISTEMA.JANELA_RETROATIVA_MESES * -1); m--) {
    var competenciaDate = new Date(hoje.getFullYear(), hoje.getMonth() + m, 1);
    var mesAnoRef = Utilities.formatDate(competenciaDate, "GMT-3", "MM/yyyy");
    var mesInt = competenciaDate.getMonth() + 1;

    // Processamos TODOS os clientes e TODAS as regras (como faz o motor real)
    for (var cliKey in mapaClientes) {
      var cliLoop = mapaClientes[cliKey];
      if (cliLoop.status === "INATIVO") continue;

      for (var r = 1; r < dataReg.length; r++) {
        var obrigOriginal = String(dataReg[r][1] || "").trim();
        if (!obrigOriginal) continue;
        var obrigNorm = norm(obrigOriginal);

        var possuiTag = verificarAcessoPorTag(cliLoop.perfis, dataReg[r][11]);
        var ehExcecao = (cliLoop.excecoes.indexOf(obrigNorm) > -1);
        var regimeBate = (norm(dataReg[r][4]) === "TODOS" || norm(dataReg[r][4]) === cliLoop.regime);
        var mesesRegra = String(dataReg[r][6] || "");
        var mesBate = (mesesRegra === "" || mesesRegra.split(",").map(function(x) { return parseInt(x.trim()); }).indexOf(mesInt) > -1);

        var hash = norm(mesAnoRef) + "|" + cliKey + "|" + obrigNorm;

        // Rastreio específico para nosso alvo
        var isAlvo = (cliKey === cliNormAlvo && obrigNorm === regraNormAlvo);

        if (!possuiTag || ehExcecao || !regimeBate || !mesBate) {
          var valorAnterior = mapaTarefasAtivas[hash] ? mapaTarefasAtivas[hash].acao : "NENHUM";
          mapaTarefasAtivas[hash] = { acao: "EXCLUIR" };
          if (isAlvo) {
            console.log("   [" + mesAnoRef + "] REGRA LINHA " + (r+1) + ": EXCLUIR (Tag=" + possuiTag + " Exc=" + ehExcecao + " Reg=" + regimeBate + " Mes=" + mesBate + ") | Anterior=" + valorAnterior);
          }
          continue;
        }

        var dtPrazoInterno = calcularDataComplexa(competenciaDate, dataReg[r][2], dataReg[r][8], dataReg[r][10]);
        var dtVencimentoLegal = calcularDataComplexa(competenciaDate, dataReg[r][9], dataReg[r][8], dataReg[r][10]);

        if (!dtPrazoInterno) {
          if (isAlvo) console.log("   [" + mesAnoRef + "] REGRA LINHA " + (r+1) + ": DATA NULL → skip");
          continue;
        }

        var dep = norm(dataReg[r][3]), resp = cliLoop.responsavelGeral || "SISTEMA";
        if (dep.indexOf("FISCAL") > -1) resp = cliLoop.fiscal;
        else if (dep.indexOf("CONTABIL") > -1) resp = cliLoop.contabil;
        else if (dep.indexOf("PESSOAL") > -1) resp = cliLoop.pessoal;
        else if (dep.indexOf("SOCIETARIO") > -1) resp = cliLoop.societario;

        if (!mapaGlobalExistencia[hash]) {
          var acaoSincronismo = (dtPrazoInterno >= inicioMesAtual) ? "CRIAR_OU_SINCRONIZAR" : "SINCRONIZAR_BACKLOG";
          var valorAnterior2 = mapaTarefasAtivas[hash] ? mapaTarefasAtivas[hash].acao : "NENHUM";
          
          mapaTarefasAtivas[hash] = {
            acao: acaoSincronismo,
            dados: [
              mesAnoRef, cliLoop.nomeOriginal, obrigOriginal, dtPrazoInterno, dataReg[r][3],
              CONFIG_SISTEMA.STATUS.PENDENTE, "", dataReg[r][5], resp,
              "ID_" + new Date().getTime() + (countId++), cliLoop.nivel, dtVencimentoLegal
            ]
          };
          
          if (isAlvo) {
            console.log("   [" + mesAnoRef + "] REGRA LINHA " + (r+1) + ": " + acaoSincronismo + " | Prazo=" + Utilities.formatDate(dtPrazoInterno, "GMT-3", "dd/MM/yyyy") + " | Anterior=" + valorAnterior2);
          }
        } else {
          if (isAlvo) console.log("   [" + mesAnoRef + "] REGRA LINHA " + (r+1) + ": JÁ NO HISTÓRICO → ignorado");
        }
      }
    }
  }

  // ===== ETAPA 4: VERIFICAR ESTADO FINAL NO MAPA =====
  console.log("\n📌 ETAPA 4: ESTADO FINAL NO mapaTarefasAtivas");
  var encontrouAlgo = false;
  for (var hKey in mapaTarefasAtivas) {
    if (hKey.indexOf(cliNormAlvo) > -1 && hKey.indexOf(regraNormAlvo) > -1) {
      var entry = mapaTarefasAtivas[hKey];
      console.log("   Hash: " + hKey + " → Ação: " + entry.acao);
      if (entry.dados) {
        console.log("   Dados: MesAno=" + entry.dados[0] + " | Cliente=" + entry.dados[1] + " | Obrig=" + entry.dados[2] + " | Vcto=" + entry.dados[3]);
      }
      encontrouAlgo = true;
    }
  }
  if (!encontrouAlgo) console.log("   ❌ NENHUMA ENTRADA ENCONTRADA para este cliente/regra!");

  // ===== ETAPA 5: SIMULAR FASE DE APLICAÇÃO NA PLANILHA =====
  console.log("\n📌 ETAPA 5: SIMULAR FASE DE APLICAÇÃO (reconstrução da DB_TAREFAS)");
  var hashesProcessados = {};

  // Primeiro: processar linhas existentes
  for (var i = 1; i < dataTf.length; i++) {
    var statusAtual = String(dataTf[i][5]).toUpperCase();
    var cliNormBanco = norm(dataTf[i][1]);
    var hTf = norm(safeGetMesAnoStr(dataTf[i][0])) + "|" + cliNormBanco + "|" + norm(dataTf[i][2]);
    
    // Verificar se é nosso alvo
    if (cliNormBanco === cliNormAlvo && norm(dataTf[i][2]) === regraNormAlvo) {
      console.log("   → Encontrada em DB_TAREFAS linha " + (i+1) + ": Hash=" + hTf + " | Status=" + statusAtual);
      var decisao = mapaTarefasAtivas[hTf];
      console.log("     Decisão do mapa: " + (decisao ? decisao.acao : "NENHUMA (backlog legado)"));
    }

    // Simular marcação de hashesProcessados (mesma lógica do motor)
    if (statusAtual === CONFIG_SISTEMA.STATUS.ENTREGUE) {
      hashesProcessados[hTf] = true;
    } else {
      var cliDadosLoop = mapaClientes[cliNormBanco];
      if (statusAtual === CONFIG_SISTEMA.STATUS.PENDENTE && (!cliDadosLoop || cliDadosLoop.status === "INATIVO")) {
        continue; // Expurgado
      }
      var decisaoLoop = mapaTarefasAtivas[hTf];
      if (decisaoLoop && (decisaoLoop.acao === "CRIAR_OU_SINCRONIZAR" || decisaoLoop.acao === "SINCRONIZAR_BACKLOG")) {
        hashesProcessados[hTf] = true;
      } else if (decisaoLoop && decisaoLoop.acao === "EXCLUIR") {
        var vctoTf = dataTf[i][3];
        var dtVctoAnterior = (vctoTf instanceof Date) ? vctoTf : new Date(vctoTf);
        if (!isNaN(dtVctoAnterior.getTime()) && dtVctoAnterior < inicioMesAtual) {
          // Preservado como legado
        } else {
          continue; // Excluído
        }
      }
    }
  }

  // Segundo: verificar se as novas tarefas seriam adicionadas
  console.log("\n📌 ETAPA 6: VERIFICAR CRIAÇÃO DE NOVAS TAREFAS");
  var tarefasCriadas = 0;
  for (var hKey2 in mapaTarefasAtivas) {
    if (hKey2.indexOf(cliNormAlvo) > -1 && hKey2.indexOf(regraNormAlvo) > -1) {
      var jaProcesado = !!hashesProcessados[hKey2];
      var acaoFinal = mapaTarefasAtivas[hKey2].acao;
      
      console.log("   Hash: " + hKey2);
      console.log("   → Ação no mapa: " + acaoFinal);
      console.log("   → Já processado (existe na planilha): " + jaProcesado);
      
      if (!jaProcesado && acaoFinal === "CRIAR_OU_SINCRONIZAR") {
        console.log("   → ✅ SERIA CRIADA COMO NOVA!");
        tarefasCriadas++;
      } else if (jaProcesado) {
        console.log("   → ℹ️ Já foi sincronizada com linha existente.");
      } else if (acaoFinal === "SINCRONIZAR_BACKLOG") {
        console.log("   → ⛔ BACKLOG sem linha existente → NÃO CRIADA.");
      } else if (acaoFinal === "EXCLUIR") {
        console.log("   → ⛔ EXCLUIR — a regra foi invalidada (tag/exceção/regime/mês).");
      }
    }
  }

  console.log("\n═══════════════════════════════════════════════════");
  console.log("🔬 RESULTADO FINAL: " + tarefasCriadas + " tarefa(s) seriam criadas.");
  console.log("═══════════════════════════════════════════════════");
}
