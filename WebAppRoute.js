/**
 * 🛡️ SISTEMA DE GESTÃO CONTÁBIL | JANIO PONTES SaaS
 * Módulo: WebApp Route Controller (Ponte Planilha -> Web)
 * Finalidade: Servir o Portal de Trabalho Externo
 */

/**
 * Função unificada para gerar as páginas web a partir do Apps Script
 * O Prompt.md obriga o uso da MetaTag 'viewport'
 */
function renderPage(templateFile, title, initialToken) {
  const template = HtmlService.createTemplateFromFile(templateFile);
  var gisId = PropertiesService.getScriptProperties().getProperty("GOOGLE_CLIENT_ID");
  template.GOOGLE_CLIENT_ID = gisId ? gisId : "";
  template.INITIAL_TOKEN = initialToken || "";
  template.SCRIPT_URL = ScriptApp.getService().getUrl();
  
  return template.evaluate()
    .setTitle(title)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL) // Permite iframe se necessário no futuro
    .setSandboxMode(HtmlService.SandboxMode.IFRAME); // Obrigatório para scripts mais modernos
}

/**
 * Função Utilitária para Injeção de Dependências CSS/JS
 * Habilita o uso de <?!= include('Arquivo_CSS'); ?> no HTML
 * @param {string} filename 
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * ⚡ CORE DATA FETCH (Portal Web)
 * Busca consolidada para extrema performance no carregamento inicial da SPA.
 */
function getDadosPortalWeb(token) {
  try {
    var hoje = new Date();
    // 1. Dados Básicos do Dashboard (Mês Atual)
    var dashMes = getDashboardData("ESTE_MES");
    
    // 2. Calcula Risco Legal (Atrasados Pendentes globais)
    var wsTarefas = getSs().getSheetByName("DB_TAREFAS");
    var totalRisco = 0;
    if (wsTarefas) {
       var dados = wsTarefas.getDataRange().getValues();
       var hojeNormal = new Date();
       hojeNormal.setHours(0,0,0,0);
       
       for (var i = 1; i < dados.length; i++) {
         if (String(dados[i][5]).toUpperCase() === "PENDENTE") {
           var vcto = dados[i][3];
           if (vcto && (vcto instanceof Date || !isNaN(new Date(vcto).getTime()))) {
              var dataV = new Date(vcto);
              dataV.setHours(0,0,0,0);
              if (dataV <= hojeNormal) {
                totalRisco++;
              }
           }
         }
       }
    }
    
    // ⚡ CAPTURA DE CONTEXTO DE USUÁRIO (GIS Token como prioridade, com Fallback para DevMode)
    var emailFinal = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();

    // TRAVA DE SEGURANÇA: Bloqueia acessos anônimos absolutos  
    if (!emailFinal || emailFinal === "") {
        return { 
          success: false, 
          error: "LOGIN_REQUERIDO", 
          message: "⚠️ LOGIN CORPORATIVO NECESSÁRIO\n\nNenhuma credencial válida foi identificada. Por favor, autentique-se no portal principal." 
        };
    }

    // 2. Calcula o UserLevel Real baseado na Aba Usuários
    var userLevel = null; // Inicia nulo para forçar validação
    var userName = "";
    var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    for (var u = 1; u < dataU.length; u++) {
       if (String(dataU[u][0]).toLowerCase().trim() === emailFinal.toLowerCase().trim()) { 
           userLevel = String(dataU[u][2]).toUpperCase().trim(); 
           userName = String(dataU[u][1]).trim();
           break; 
       }
    }

    // LOG DE DIAGNÓSTICO: Confirmar resolução do nível de acesso
    registrarLogSistema("PORTAL_AUTH", "Email: " + emailFinal + " | Nível Resolvido: " + userLevel);

    // TRAVA DE SEGURANÇA: Se não estiver na lista, bloqueia tudo
    if (userLevel === null) {
       return { 
         success: false, 
         error: "SISTEMA_BLOQUEADO", 
         message: "Acesso não autorizado. Seu e-mail (" + emailFinal + ") não consta na lista de usuários permitidos. Entre em contato com o administrador." 
       };
    }

    // 3. Fila de Prioridades Exclusiva do WebApp (Usa o email final + nível autenticado)
    var prioridades = getPrioridadesPortal(emailFinal, userLevel);
    
    // 4. Listas de Metadados para o Módulo de Comunicação
    var clientes = getListaClientes();
    var tiposDemanda = getTiposTarefaRegras();
    
    return {
      success: true,
      userEmail: emailFinal,
      userName: userName,
      userLevel: userLevel,
      dash: {
        pendentes: (dashMes && !dashMes.error) ? dashMes.pendentes : 0,
        entregues: (dashMes && !dashMes.error) ? dashMes.entregues : 0,
        risco: totalRisco,
        departamentos: (dashMes && !dashMes.error) ? dashMes.departamentos : {},
        usuarios: (dashMes && !dashMes.error) ? dashMes.usuarios : {}
      },
      prioridades: prioridades,
      clientes: clientes,
      tiposDemanda: tiposDemanda
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/**
 * ⚡ WORKFLOW DEDICADO DO PORTAL
 * Semelhante ao getPrioridades() legado, mas aceita injeção do E-mail Efetivo
 * para contornar o anonimato de execução do WebApp.
 */
function getPrioridadesPortal(activeEmail, userLevelOverride) {
  try {
    var userEmail = activeEmail.toLowerCase().trim();
    // Usa o nível já validado pelo caller (getDadosPortalWeb) para evitar inconsistência
    var userLevel = userLevelOverride || "USER";
    if (!userLevelOverride) {
      var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
      for (var i = 1; i < dataU.length; i++) {
         if (String(dataU[i][0]).toLowerCase().trim() === userEmail) { 
             userLevel = String(dataU[i][2]).toUpperCase().trim(); 
             break; 
         }
      }
    }
    
    var wsTasks = getSs().getSheetByName("DB_TAREFAS");
    if (!wsTasks) return [];
    
    // Mapa de email → nome para exibição do responsável
    var dataUsuarios = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    var mapNomes = {};
    for (var u = 1; u < dataUsuarios.length; u++) {
       var emailKey = String(dataUsuarios[u][0]).toLowerCase().trim();
       var nomeVal = String(dataUsuarios[u][1]).trim();
       if (emailKey) mapNomes[emailKey] = nomeVal;
    }
    
    var dataProt = getSheetDataCached(CONFIG_SISTEMA.ABA_PROTOCOLOS, "DATA_PROTOCOLOS") || [];
    var mapDocLinks = {};
    for (var p = 1; p < dataProt.length; p++) {
       if (dataProt[p][7] && String(dataProt[p][7]).indexOf("http") > -1) {
          mapDocLinks[String(dataProt[p][3])] = String(dataProt[p][7]); 
       }
    }
    
    
    var dataT = wsTasks.getDataRange().getValues();
    var dataRegras = getSheetDataCached("DB_REGRAS", "DATA_REGRAS");
    var mapRegrasRevisao = {};
    for (var r = 1; r < dataRegras.length; r++) {
        var nRegra = norm(dataRegras[r][1]);
        if (nRegra) mapRegrasRevisao[nRegra] = String(dataRegras[r][12] || "").toUpperCase().trim() === "S";
    }

    var tasks = [];
    for (var j = 1; j < dataT.length; j++) {
       var statusObj = norm(dataT[j][5]);
       if (statusObj !== "PENDENTE" && statusObj !== "REVISAO") continue;
       
       var respRaw = String(dataT[j][8]);
       if (userLevel === "ADMIN" || isUserResponsible(respRaw, userEmail)) {
         var rawVcto = dataT[j][3];
         var dateObj = (rawVcto instanceof Date) ? rawVcto : new Date(rawVcto);
         
         var mesAnoRaw = dataT[j][0];
         var mesAnoStr = (mesAnoRaw instanceof Date) ? Utilities.formatDate(mesAnoRaw, "GMT-3", "MM/yyyy") : String(mesAnoRaw);
         var obrigNome = dataT[j][2];
         var exigeRevisao = mapRegrasRevisao[norm(obrigNome)] || false;

         tasks.push({ 
            id: dataT[j][9], 
            cliente: String(dataT[j][1]), 
            obrigacao: String(obrigNome), 
            vencimentoSort: dateObj.getTime(), 
            vencimentoStr: Utilities.formatDate(dateObj, "GMT-3", "dd/MM/yyyy"), 
            mesAno: mesAnoStr,
            depto: String(dataT[j][4]), 
            status: String(dataT[j][5]).toUpperCase().trim(),
            docLinks: mapDocLinks[String(dataT[j][9])] || "",
            acao: String(dataT[j][7]).toUpperCase().trim(), 
            nivel: dataT[j][10] || "1",
            responsavel: respRaw.split(',').map(function(e) { 
               var ek = e.trim().toLowerCase();
               return mapNomes[ek] || ek;
            }).join(', ') || "Não Atribuído",
            exigeRevisao: exigeRevisao
         });
       }
    }
    
    tasks.sort((a, b) => (a.nivel !== b.nivel) ? b.nivel - a.nivel : a.vencimentoSort - b.vencimentoSort);
    return tasks; // Retorna 100% da esteira do usuário logado sem limitar a 7
  } catch (e) {
    return [];
  }
}

/**
 * ⚡ RISK FETCH (Portal Web)
 * Busca tarefas vencidas para montar o painel de Compliance.
 */
function getDadosRiscoWeb(token) {
  try {
    var emailFinal = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!emailFinal) return { success: false, error: "AUTENTICACAO_REQUERIDA" };

    // ⚡ CACHE: Tenta retornar resultado cacheado específico por usuário
    var cached = getViewCached(CACHE_CONFIG.KEYS.RISCO_RESULT + "_" + emailFinal.replace(/[^a-zA-Z0-9]/g, ""));
    if (cached) return cached;

    // 2. Calcula o UserLevel Real
    var userLevel = "USER";
    var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    for (var u = 1; u < dataU.length; u++) {
       if (String(dataU[u][0]).toLowerCase().trim() === emailFinal) { 
           userLevel = String(dataU[u][2]).toUpperCase().trim(); 
           break; 
       }
    }

    var wsTasks = getSs().getSheetByName("DB_TAREFAS");
    if (!wsTasks) return { success: false, error: "Tabela não encontrada" };
    
    var lastRow = wsTasks.getLastRow();
    if (lastRow <= 1) return { success: true, data: [] };
    
    // OTIMIZAÇÃO: Lê apenas até a coluna I (Índice 8) para economizar memória e banda
    var dataT = wsTasks.getRange(1, 1, lastRow, 9).getValues();
    var hoje = new Date();
    hoje.setHours(0,0,0,0);
    var riskList = [];
    
    var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    var mapUsuarios = {};
    for(var u=1; u<dataU.length; u++) {
       mapUsuarios[String(dataU[u][0]).toLowerCase().trim()] = String(dataU[u][1]);
    }

    for (var i = 1; i < dataT.length; i++) {
       if (norm(dataT[i][5]) !== "PENDENTE") continue;
       
       var respEmailRaw = String(dataT[i][8]);
       // FILTRO DE SEGURANÇA: Usuários comuns só vêem seu próprio risco
       if (userLevel !== "ADMIN" && !isUserResponsible(respEmailRaw, emailFinal)) continue;

       var vctoRaw = dataT[i][3];
       if (!vctoRaw) continue;
       
       var dataVcto = (vctoRaw instanceof Date) ? vctoRaw : new Date(vctoRaw);
       if (isNaN(dataVcto.getTime())) continue;
       dataVcto.setHours(0,0,0,0);
       
       if (dataVcto <= hoje) {
          var diffTime = Math.abs(hoje - dataVcto);
          var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
          
          var respDisplay = respEmailRaw.split(',').map(function(e) {
             var ek = e.trim().toLowerCase();
             return mapUsuarios[ek] || ek;
          }).join(', ') || "Não Atribuído";
          
          riskList.push({
             cliente: String(dataT[i][1]),
             obrigacao: String(dataT[i][2]),
             depto: String(dataT[i][4]),
             vencimento: Utilities.formatDate(dataVcto, "GMT-3", "dd/MM/yyyy"),
             atraso: diffDays,
             responsavel: respDisplay
          });
       }
    }
    
    riskList.sort((a,b) => b.atraso - a.atraso);
    var resultado = { success: true, data: riskList };
    
    // ⚡ CACHE: Grava resultado processado com chave de usuário
    setViewCache(CACHE_CONFIG.KEYS.RISCO_RESULT + "_" + emailFinal.replace(/[^a-zA-Z0-9]/g, ""), resultado);
    
    return resultado;
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/**
 * ⚡ HISTORIC FETCH (Portal Web)
 * Busca os ultimos 70 registros.
 */
/**
 * ⚡ SOLICITAÇÕES TAB FETCH (Portal Web)
 * Busca as solicitações com filtro RBAC: ADMIN vê tudo, USER vê só as próprias.
 */
function getDadosSolicitacoesTabWeb(token) {
  try {
    var emailFinal = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!emailFinal) return { success: false, error: "AUTENTICACAO_REQUERIDA" };

    // Resolve nível do usuário
    var userLevel = "USER";
    var dataU = getSheetDataCached("DB_USUARIOS", "DATA_USUARIOS");
    for (var u = 1; u < dataU.length; u++) {
       if (String(dataU[u][0]).toLowerCase().trim() === emailFinal) { 
           userLevel = String(dataU[u][2]).toUpperCase().trim(); 
           break; 
       }
    }

    var wsSol = getSs().getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
    if (!wsSol) return { success: false, error: "Aba DB_SOLICITACOES não encontrada." };

    var lastRow = wsSol.getLastRow();
    if (lastRow <= 1) return { success: true, data: [] };

    var dataSol = wsSol.getDataRange().getValues();
    var solList = [];

    // Mapa de email → nome para exibição do responsável
    var mapNomes = {};
    for (var n = 1; n < dataU.length; n++) {
       var emailKey = String(dataU[n][0]).toLowerCase().trim();
       var nomeVal = String(dataU[n][1]).trim();
       if (emailKey) mapNomes[emailKey] = nomeVal;
    }

    for (var i = 1; i < dataSol.length; i++) {
       var respEmailRaw = String(dataSol[i][10] || ""); // K = RESPONSAVEL
       
       // FILTRO RBAC: USER vê apenas suas solicitações
       if (userLevel !== "ADMIN" && !isUserResponsible(respEmailRaw, emailFinal)) continue;

       var dataRaw = dataSol[i][1]; // B = DATA
       var dataStr = (dataRaw instanceof Date) ? Utilities.formatDate(dataRaw, "GMT-3", "dd/MM/yyyy HH:mm") : String(dataRaw || "---");

       var statusSol = String(dataSol[i][6] || "").toUpperCase().trim(); // G = STATUS
       var qtdAvisos = dataSol[i][9] || 0; // J = QTD_AVISOS

       solList.push({
          id: String(dataSol[i][0]),           // A = ID
          data: dataStr,                        // B = DATA
          cliente: String(dataSol[i][2]),       // C = CLIENTE
          email: String(dataSol[i][3]),         // D = EMAIL
          pedido: String(dataSol[i][4]),        // E = PEDIDO
          idTarefa: String(dataSol[i][5] || "AVULSA"), // F = ID_TAREFA
          status: statusSol,                    // G = STATUS
          linkArquivo: String(dataSol[i][7] || ""),    // H = LINK_ARQUIVO
          qtdAvisos: qtdAvisos,                 // J = QTD_AVISOS
          responsavel: respEmailRaw.split(',').map(function(e) {
             var ek = e.trim().toLowerCase();
             return mapNomes[ek] || ek;
          }).join(', ') || "Não Atribuído", // K = RESPONSAVEL (nome)
          metaTarefa: String(dataSol[i][11] || "")     // L = META_TAREFA
       });
    }

    // Ordena: PENDENTES primeiro, depois por data decrescente
    solList.sort(function(a, b) {
       if (a.status === "PENDENTE" && b.status !== "PENDENTE") return -1;
       if (a.status !== "PENDENTE" && b.status === "PENDENTE") return 1;
       return 0; // Mantém ordem original (cronológica da planilha)
    });

    return { success: true, data: solList };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/**
 * ⚡ COBRAR SOLICITAÇÃO (Manual via Portal)
 * Dispara um lembrete imediato para uma solicitação específica.
 */
function cobrarSolicitacaoUnica(token, solId) {
  try {
    var emailFinal = validarTokenGIS(token) || Session.getActiveUser().getEmail().toLowerCase().trim();
    if (!emailFinal) return { success: false, error: "AUTENTICACAO_REQUERIDA" };

    var ss = getSs();
    var wsSol = ss.getSheetByName(CONFIG_SISTEMA.ABA_SOLICITACOES);
    var dataSol = wsSol.getDataRange().getValues();
    var rowIdx = -1;

    for (var i = 1; i < dataSol.length; i++) {
       if (String(dataSol[i][0]) === String(solId)) {
          rowIdx = i + 1;
          break;
       }
    }

    if (rowIdx === -1) return { success: false, error: "Solicitação não encontrada." };

    var cliente = dataSol[rowIdx-1][2];
    var email = dataSol[rowIdx-1][3];
    var pedido = dataSol[rowIdx-1][4];
    var status = String(dataSol[rowIdx-1][6]).toUpperCase().trim();
    var qtdAvisos = parseInt(dataSol[rowIdx-1][9]) || 0;
    var infoTarefa = dataSol[rowIdx-1][11];

    if (status !== "PENDENTE") return { success: false, error: "Apenas solicitações PENDENTES podem ser cobradas." };

    // Dispara via EmailService
    enviarLembreteCobranca(cliente, email, pedido, solId, qtdAvisos, infoTarefa);

    // Atualiza Planilha
    wsSol.getRange(rowIdx, 9).setValue(new Date()); // Column I: DATA_COBRANCA
    wsSol.getRange(rowIdx, 10).setValue(qtdAvisos + 1); // Column J: QTD_AVISOS

    invalidarCacheSistema();
    registrarLogSistema("MANUAL_COBRANCA", "Manual resend for ID: " + solId + " (Aviso #" + (qtdAvisos+1) + ")");

    return { success: true, message: "Lembrete enviado com sucesso!" };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/**
 * ⚡ HISTORIC FETCH (Portal Web)
 * Busca os ultimos 70 registros.
 */
function getDadosHistoricoWeb() {
  try {
    // ⚡ CACHE: Tenta retornar resultado cacheado
    var cached = getViewCached(CACHE_CONFIG.KEYS.HISTORICO_RESULT);
    if (cached) return cached;

    var wsHist = getSs().getSheetByName("DB_HISTORICO");
    if (!wsHist) return { success: false, error: "Aba Historico não encontrada." };
    
    var lastRow = wsHist.getLastRow();
    if (lastRow <= 1) return { success: true, data: [] };
    
    var lastCol = wsHist.getLastColumn();
    var rangeSize = 100;
    var startRow = Math.max(1, lastRow - rangeSize + 1);
    var numRows = lastRow - startRow + 1;
    var dataH = wsHist.getRange(startRow, 1, numRows, lastCol).getValues();
    
    var histList = [];
    var limit = 70; 
    
    // Varredura Inversa
    var stopIndex = (startRow === 1) ? 1 : 0;
    for (var i = dataH.length - 1; i >= stopIndex && limit > 0; i--) {
        var vctoRaw = dataH[i][3];
        var vctoStr = (vctoRaw instanceof Date) ? Utilities.formatDate(vctoRaw, "GMT-3", "dd/MM/yyyy") : String(vctoRaw);
        
        var mesAnoRaw = dataH[i][0];
        var mesAnoStr = (mesAnoRaw instanceof Date) ? Utilities.formatDate(mesAnoRaw, "GMT-3", "MM/yyyy") : String(mesAnoRaw);
        
        var statusEnvio = String(dataH[i][12] || "---");
        
        var leituraRaw = dataH[i][13];
        var leituraStr = (leituraRaw instanceof Date) ? Utilities.formatDate(leituraRaw, "GMT-3", "dd/MM/yyyy HH:mm:ss") : String(leituraRaw || "---");

        histList.push({
           mesAno: mesAnoStr,
           cliente: String(dataH[i][1]),
           obrigacao: String(dataH[i][2]),
           vencimento: vctoStr,
           depto: String(dataH[i][4]),
           statusEnvio: statusEnvio,
           leitura: leituraStr
        });
        limit--;
    }
    var resultado = { success: true, data: histList };
    
    // ⚡ CACHE: Grava resultado processado
    setViewCache(CACHE_CONFIG.KEYS.HISTORICO_RESULT, resultado);
    
    return resultado;
  } catch(err) {
    return { success: false, error: err.message };
  }
}

