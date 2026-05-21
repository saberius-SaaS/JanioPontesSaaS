/**
 * 📱 WHATSAPP NOTIFICATION SERVICE v1.1 — MÓDULO DORMANT
 * 
 * STATUS: INATIVO (Aguardando aprovação para ativação)
 * BSP: Maxbot (app.maxbot.com.br)
 * 
 * Este módulo é 100% isolado do sistema principal. Nenhuma função existente
 * o referencia. Ele só será ativado quando:
 *   1. CONFIG_SISTEMA.WHATSAPP.ATIVO = true
 *   2. API_TOKEN do Maxbot preenchido
 *   3. Template aprovado no Maxbot/Meta (Título: DOCUMENTO PRONTO)
 *   4. Gatilho instalado manualmente via instalarGatilhoWhatsApp()
 * 
 * SCHEMA DB_PROTOCOLOS (colunas usadas):
 *   A(0)=DATA | B(1)=CLIENTE | C(2)=PROTOCOLO | D(3)=ID_TAREFA
 *   E(4)=OBRIGACAO | F(5)=EMAIL | G(6)=RESPONSAVEL | H(7)=LINK_ARQUIVO
 *   I(8)=STATUS_ENVIO | J(9)=CONF_RECTO | K(10)=VCTO_LEGAL | L(11)=ACAO
 *   M(12)=WPP_NOTIF (Nova — rastreio de notificação WhatsApp)
 * 
 * SCHEMA DB_CLIENTES (colunas usadas):
 *   B(1)=CLIENTE | F(5)=TELEFONE (formato: 5534999999999)
 */

// ═══════════════════════════════════════════════════════════════════════
// 🔒 VALIDAÇÃO DE PRÉ-REQUISITOS
// ═══════════════════════════════════════════════════════════════════════

/**
 * Verifica se todos os pré-requisitos estão atendidos para o módulo operar.
 * @returns {{ ok: boolean, motivo: string }}
 */
function _validarPreRequisitosWpp() {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  if (!cfg) return { ok: false, motivo: "Bloco WHATSAPP ausente no CONFIG_SISTEMA." };
  if (!cfg.ATIVO) return { ok: false, motivo: "Módulo WHATSAPP está DESATIVADO (ATIVO=false)." };
  if (!cfg.API_TOKEN) return { ok: false, motivo: "API_TOKEN do Maxbot não configurado." };
  if (!cfg.TEMPLATE_NAME) return { ok: false, motivo: "TEMPLATE_NAME não configurado." };
  return { ok: true, motivo: "" };
}

// ═══════════════════════════════════════════════════════════════════════
// 📋 IDENTIFICAÇÃO DE PROTOCOLOS PENDENTES
// ═══════════════════════════════════════════════════════════════════════

/**
 * Identifica protocolos elegíveis para notificação WhatsApp.
 * Replica EXATAMENTE a lógica de "não lido" do DashboardService.js (linha 153),
 * adicionando o filtro anti-spam da Coluna M.
 * 
 * @returns {Array<Object>} Lista de protocolos pendentes com dados para envio
 */
function _getProtocolosPendentesWpp() {
  var ss = getSs();
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  if (!wsProt) return [];

  var lastRow = wsProt.getLastRow();
  if (lastRow <= 1) return [];

  // Lê os últimos 3000 protocolos para cobrir todo o histórico recente
  var numRows = Math.min(lastRow - 1, 3000);
  var startRow = lastRow - numRows + 1;
  var dataProt = wsProt.getRange(startRow, 1, numRows, 13).getValues(); // A até M

  // Mapa de telefones: CLIENTE → TELEFONE
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  if (!wsCli) return [];
  var dataCli = wsCli.getDataRange().getValues();
  var mapaTelefone = {};
  for (var c = 1; c < dataCli.length; c++) {
    var nomeNorm = norm(dataCli[c][1]);
    var telefonesRaw = String(dataCli[c][5] || ""); // Coluna F: TELEFONE
    if (nomeNorm && telefonesRaw) {
      var partes = telefonesRaw.split(/[,;\/]/);
      var telsLimpados = [];
      for (var p = 0; p < partes.length; p++) {
        var limpo = partes[p].replace(/\D/g, "");
        if (limpo.length >= 10) telsLimpados.push(limpo);
      }
      if (telsLimpados.length > 0) mapaTelefone[nomeNorm] = telsLimpados;
    }
  }

  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var hoje = new Date();
  var intervaloMs = (cfg.DIAS_INTERVALO_RENOTIFICACAO || 3) * 24 * 60 * 60 * 1000;
  var pendentesMap = {};

  for (var i = 0; i < dataProt.length; i++) {
    var statusEnvio = String(dataProt[i][8]).toUpperCase().trim();   // Coluna I
    var confRecto = String(dataProt[i][9]).toUpperCase().trim();     // Coluna J
    var acaoProt = String(dataProt[i][11] || "").toUpperCase().trim(); // Coluna L
    var linkBruto = String(dataProt[i][7]).toUpperCase().trim();     // Coluna H

    // ── Filtro 1: Apenas ações ENVIAR (COMUNICAR é auto-lido, não notificamos) ──
    if (acaoProt.indexOf("ENVIAR") === -1) continue;

    // ── Filtro 2: Ignorar justificativas (SEM_ENVIO:) ──
    if (linkBruto.indexOf("SEM_ENVIO:") === 0) continue;

    // ── Filtro 3: Apenas protocolos NÃO LIDOS ──
    // Lógica idêntica ao DashboardService: isLido = !(ENVIADO && confRecto vazio)
    var isLido = !(statusEnvio === "ENVIADO" && (confRecto === "" || confRecto === "---" || confRecto === "AGUARDANDO"));
    if (isLido) continue;

    // ── Filtro 4: Anti-Spam (Coluna M — última notificação WhatsApp) ──
    var ultimaNotifWpp = dataProt[i][12]; // Coluna M (índice 12)
    if (ultimaNotifWpp) {
      var dataUltimaNotif = (ultimaNotifWpp instanceof Date) ? ultimaNotifWpp : new Date(ultimaNotifWpp);
      if (!isNaN(dataUltimaNotif.getTime()) && (hoje.getTime() - dataUltimaNotif.getTime()) < intervaloMs) {
        continue; // Ainda dentro do intervalo de renotificação
      }
    }

    // ── Filtro 5: Cliente possui telefone cadastrado ──
    var clienteNome = String(dataProt[i][1]);
    var telefonesCliente = mapaTelefone[norm(clienteNome)];
    if (!telefonesCliente || telefonesCliente.length === 0) continue;

    // ── Dados para o template ──
    var vctoLegal = dataProt[i][10];
    var vctoStr = "---";
    if (vctoLegal) {
      vctoStr = (vctoLegal instanceof Date) ? Utilities.formatDate(vctoLegal, "GMT-3", "dd/MM/yyyy") : String(vctoLegal);
    }

    var chaveAgrupamento = norm(clienteNome);
    if (!pendentesMap[chaveAgrupamento]) {
      pendentesMap[chaveAgrupamento] = {
        cliente: clienteNome,
        telefones: telefonesCliente,
        protocolos: []
      };
    }

    var obrigacaoNome = String(dataProt[i][4]);
    var obrigacaoNorm = norm(obrigacaoNome);
    var protocoloAtual = String(dataProt[i][2]);
    var rowAtual = startRow + i;

    // Deduplicação: Agrupa protocolos da mesma obrigação para não spammar (mesmo documento reenviado)
    var jaExiste = false;
    for (var p = 0; p < pendentesMap[chaveAgrupamento].protocolos.length; p++) {
      if (norm(pendentesMap[chaveAgrupamento].protocolos[p].obrigacao) === obrigacaoNorm) {
        jaExiste = true;
        pendentesMap[chaveAgrupamento].protocolos[p].rowSheet.push(rowAtual);
        pendentesMap[chaveAgrupamento].protocolos[p].listaProts.push(protocoloAtual);
        break;
      }
    }

    if (!jaExiste) {
      pendentesMap[chaveAgrupamento].protocolos.push({
        obrigacao: obrigacaoNome,
        vencimento: vctoStr,
        protocolo: protocoloAtual,
        rowSheet: [rowAtual],
        listaProts: [protocoloAtual]
      });
    }
  }

  // ── Consolidar lista agrupada ──
  var pendentes = [];
  for (var k in pendentesMap) {
    var ag = pendentesMap[k];

    var obrigacaoTexto = "";
    var vencimentoTexto = "";
    var protocoloTexto = "";

    if (ag.protocolos.length === 1) {
      obrigacaoTexto = ag.protocolos[0].obrigacao;
      vencimentoTexto = ag.protocolos[0].vencimento;
      protocoloTexto = ag.protocolos[0].protocolo;
    } else {
      var limitText = ag.protocolos[0].obrigacao;
      if (limitText.length > 35) limitText = limitText.substring(0, 35) + "...";
      obrigacaoTexto = limitText + " (+ " + (ag.protocolos.length - 1) + " docs)";
      vencimentoTexto = "Diversos";
      protocoloTexto = "Múltiplos (" + ag.protocolos.length + ")";
    }

    // Consolida arrays internos de linhas e IDs de protocolo
    var linhasPlanilhaConsolidadas = [];
    var listaProtsConsolidada = [];
    for (var pIdx = 0; pIdx < ag.protocolos.length; pIdx++) {
      linhasPlanilhaConsolidadas = linhasPlanilhaConsolidadas.concat(ag.protocolos[pIdx].rowSheet);
      listaProtsConsolidada = listaProtsConsolidada.concat(ag.protocolos[pIdx].listaProts);
    }

    // Se o cliente tem vários números, insere um envio agrupado para cada um
    for (var telIdx = 0; telIdx < ag.telefones.length; telIdx++) {
      pendentes.push({
        telefone: ag.telefones[telIdx],
        cliente: ag.cliente,
        obrigacao: obrigacaoTexto,
        vencimento: vencimentoTexto,
        protocolo: protocoloTexto,
        linhasPlanilha: linhasPlanilhaConsolidadas, // Array flat para atualizar todos de uma vez
        listaProts: listaProtsConsolidada.join(", ") // Para o log
      });
    }
  }

  return pendentes;
}

// ═══════════════════════════════════════════════════════════════════════
// 📤 ENVIO VIA META GRAPH API
// ═══════════════════════════════════════════════════════════════════════

/**
 * Envia uma mensagem de template WhatsApp via API do Maxbot (BSP).
 * 
 * Template aprovado: "DOCUMENTO PRONTO" (4 variáveis, sem botão):
 *   {{1}} = [INFO1] Nome do Documento (Obrigação)
 *   {{2}} = [INFO2] Data de Vencimento Legal
 *   {{3}} = [INFO3] Nome do Cliente
 *   {{4}} = [INFO4] Número do Protocolo
 * 
 * @param {string} telefone - Número no formato 5534999999999
 * @param {Object} params - { obrigacao, vencimento, cliente, protocolo }
 * @returns {{ success: boolean, messageId: string, error: string }}
 */
// Cache de contatos do Maxbot (preenchido uma vez por ciclo)
// Removido cache massivo. Busca individual via API para máxima performance e segurança.

/**
 * Busca o contact_id do Maxbot a partir de um telefone diretamente na API.
 * Tenta buscar o número exato fornecido. Se não encontrar e o número tiver DDI 55,
 * tenta buscar sem o DDI para garantir máxima cobertura de contatos antigos.
 * @param {string} telefone - Número do WhatsApp
 * @returns {string|null} contact_id ou null se não encontrado
 */
function _buscarContactIdNaApi(telefone) {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var url = "https://app.maxbot.com.br/api/v1.php";

  var telNum = String(telefone).replace(/\D/g, "");
  if (!telNum) return null;

  // Função interna para disparar a consulta
  function consultar(num) {
    try {
      var resp = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify({
          token: cfg.API_TOKEN,
          cmd: "get_contact",
          whatsapp: num
        }),
        muteHttpExceptions: true
      });
      var data = JSON.parse(resp.getContentText());
      if (data.status === 1 && data.data && data.data.length > 0) {
        return data.data[0].id;
      }
    } catch (e) {
      console.log("Erro na consulta get_contact: " + e.message);
    }
    return null;
  }

  // Tentativa 1: Formato exato enviado
  var contactId = consultar(telNum);
  if (contactId) return contactId;

  // Tentativa 2: Se tem 55, tenta sem o 55 (contatos salvos sem DDI no Maxbot)
  if (telNum.indexOf("55") === 0) {
    var semDdi = telNum.substring(2);
    contactId = consultar(semDdi);
    if (contactId) return contactId;
  }

  // Tentativa 3 e 4: Cobertura para números salvos sem o 9º dígito
  // Se o número tem 13 dígitos e o 5º caractere é '9' (ex: 5534'9'99998888)
  if (telNum.length === 13 && telNum.charAt(4) === '9') {
    // 3. Sem o 9, mas com DDI (ex: 553499998888)
    var semNonoComDdi = telNum.substring(0, 4) + telNum.substring(5);
    contactId = consultar(semNonoComDdi);
    if (contactId) return contactId;

    // 4. Sem o 9 e sem o DDI (ex: 3499998888)
    if (telNum.indexOf("55") === 0) {
      var semNonoSemDdi = telNum.substring(2, 4) + telNum.substring(5);
      contactId = consultar(semNonoSemDdi);
      if (contactId) return contactId;
    }
  }

  return null;
}

function _enviarMensagemWhatsApp(telefone, params) {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var url = "https://app.maxbot.com.br/api/v1.php";
  var _debugInfo = { telefoneInput: telefone, contactId: null, metodo: "" };

  // ── PASSO 1: Buscar contact_id ──
  var contactId = _buscarContactIdNaApi(telefone);

  if (contactId) {
    _debugInfo.metodo = "api_existente";
  } else {
    // Se não encontrou, cria o contato
    try {
      var respContato = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify({
          token: cfg.API_TOKEN,
          cmd: "put_contact",
          name: params.cliente,
          surname: ".",
          whatsapp: telefone
        }),
        muteHttpExceptions: true
      });
      var bodyContato = JSON.parse(respContato.getContentText());

      // Validação mais estrita do retorno de criação
      if (bodyContato.status === 1) {
        contactId = bodyContato.contact_id || bodyContato.id || null;
        _debugInfo.metodo = "criado_novo";
        console.log("WPP put_contact response: " + JSON.stringify(bodyContato));
      } else {
        throw new Error(bodyContato.msg || "Erro na API put_contact");
      }
    } catch (e) {
      return { success: false, messageId: "", error: "Falha ao criar contato (" + e.message + ")", _debug: _debugInfo };
    }
  }

  _debugInfo.contactId = contactId;
  console.log("WPP _debugInfo: " + JSON.stringify(_debugInfo));

  if (!contactId) {
    return { success: false, messageId: "", error: "Contato não pôde ser criado para " + telefone, _debug: _debugInfo };
  }

  // ── PASSO 2: Preencher tag_info no contato (variáveis do template) ──
  // A API Maxbot injeta variáveis [INFO1]-[INFO6] a partir dos campos tag_info
  // do contato. Elas devem ser populadas via set_contact ANTES do open_followup.
  try {
    var respSetContact = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        token: cfg.API_TOKEN,
        cmd: "set_contact",
        for_contact_id: String(contactId),
        tag_info1: String(params.obrigacao || ""),
        tag_info2: String(params.vencimento || ""),
        tag_info3: String(params.cliente || ""),
        tag_info4: String(params.protocolo || "")
      }),
      muteHttpExceptions: true
    });
    var bodySet = JSON.parse(respSetContact.getContentText());
    if (bodySet.status !== 1) {
      return { success: false, messageId: "", error: "set_contact falhou: " + (bodySet.msg || "Erro desconhecido"), _debug: _debugInfo };
    }
    console.log("WPP set_contact OK para contact_id: " + contactId);
  } catch (e) {
    return { success: false, messageId: "", error: "Exceção em set_contact: " + e.message, _debug: _debugInfo };
  }

  // ── PASSO 3: Enviar template via open_followup ──
  var payload = {
    token: cfg.API_TOKEN,
    cmd: "open_followup",
    channel_token: cfg.CHANNEL_TOKEN,
    contact_id: contactId,
    template_id: cfg.TEMPLATE_ID,
    sector_id: cfg.SECTOR_ID || 8454,
    attendant_id: 0,
    scheduled: 0,
    date_time: (function () { var d = new Date(); d.setMinutes(d.getMinutes() < 30 ? 0 : 30); d.setSeconds(0); return Utilities.formatDate(d, "GMT-3", "yyyy-MM-dd HH:mm:ss"); })()
  };

  try {
    var response = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    var code = response.getResponseCode();
    var body = JSON.parse(response.getContentText());

    if (code === 200 && (body.status === 1 || body.status === "success")) {
      var msgId = body.prot_id || body.protocol || body.msg_id || body.id || "OK";
      return { success: true, messageId: String(msgId), error: "", _debug: _debugInfo };
    } else {
      var errMsg = body.msg || body.message || body.error || ("HTTP " + code);
      
      // Fallback para quando já existe um protocolo em andamento para o contato
      if (String(errMsg).toLowerCase().indexOf("already a protocol in progress") > -1 || String(errMsg).toLowerCase().indexOf("protocolo em andamento") > -1) {
        console.log("WPP: Protocolo em andamento para " + telefone + ". Tentando fallback via send_text...");
        try {
          var textoMsg = "📢 *JANIO PONTES CONTABILIDADE*\n" +
                         "Aviso de Documento Pronto\n\n" +
                         "Prezado(a) *" + String(params.cliente).trim() + "*,\n\n" +
                         "Informamos que o seu documento está pronto para acesso:\n\n" +
                         "📄 *Documento:* " + String(params.obrigacao).trim() + "\n" +
                         "📅 *Vencimento:* " + String(params.vencimento).trim() + "\n" +
                         "🔑 *Protocolo:* " + String(params.protocolo).trim() + "\n\n" +
                         "Por favor, acesse seu email para visualizar e realizar o download.";

          var payloadText = {
            token: cfg.API_TOKEN,
            cmd: "send_text",
            channel_token: cfg.CHANNEL_TOKEN,
            ct_whatsapp: String(telefone),
            msg: textoMsg
          };

          var respText = UrlFetchApp.fetch(url, {
            method: "post",
            contentType: "application/json",
            payload: JSON.stringify(payloadText),
            muteHttpExceptions: true
          });

          var bodyText = JSON.parse(respText.getContentText());
          if (respText.getResponseCode() === 200 && (bodyText.status === 1 || bodyText.status === "success")) {
            var msgIdText = bodyText.msg_id || bodyText.id || "OK_FALLBACK";
            console.log("WPP: Fallback send_text enviado com sucesso para " + telefone + " (ID: " + msgIdText + ")");
            return { success: true, messageId: String(msgIdText) + " (Fallback)", error: "", _debug: _debugInfo };
          } else {
            var errMsgText = bodyText.msg || bodyText.message || bodyText.error || ("HTTP " + respText.getResponseCode());
            return { success: false, messageId: "", error: "open_followup falhou (Protocolo em andamento) e fallback send_text falhou: " + errMsgText, _debug: _debugInfo };
          }
        } catch (eText) {
          return { success: false, messageId: "", error: "open_followup falhou (Protocolo em andamento) e fallback send_text gerou exceção: " + eText.message, _debug: _debugInfo };
        }
      }

      return { success: false, messageId: "", error: String(errMsg), _debug: _debugInfo };
    }
  } catch (e) {
    return { success: false, messageId: "", error: e.message, _debug: _debugInfo };
  }
}

// ═══════════════════════════════════════════════════════════════════════
// 🚀 FUNÇÃO PRINCIPAL (Executada pelo Gatilho Diário)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Rotina principal de notificação WhatsApp para protocolos não lidos.
 * 
 * IMPORTANTE: Esta função NÃO faz nada se:
 *   - CONFIG_SISTEMA.WHATSAPP.ATIVO === false
 *   - API_TOKEN ou PHONE_NUMBER_ID estiverem vazios
 *   - Não houver protocolos pendentes elegíveis
 * 
 * @returns {number} Total de mensagens enviadas com sucesso
 */
function executarNotificacaoWhatsApp() {
  // ── Validação de dias úteis e feriados ──
  var hojeObj = new Date();
  var diaSemana = hojeObj.getDay(); // 0 = Domingo, 6 = Sábado
  if (diaSemana === 0 || diaSemana === 6) {
    registrarLogSistema("WPP_SKIP", "Envio suspenso (Fim de semana).");
    return 0;
  }

  var hojeFmt = Utilities.formatDate(hojeObj, "GMT-3", "dd/MM");
  var feriados = CONFIG_SISTEMA.FERIADOS || [];
  if (feriados.indexOf(hojeFmt) > -1) {
    registrarLogSistema("WPP_SKIP", "Envio suspenso (Feriado: " + hojeFmt + ").");
    return 0;
  }

  // ── Validação de pré-requisitos ──
  var check = _validarPreRequisitosWpp();
  if (!check.ok) {
    registrarLogSistema("WPP_SKIP", check.motivo);
    return 0;
  }

  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var maxEnvios = cfg.MAX_ENVIOS_POR_CICLO || 30;

  // ── Identificar protocolos pendentes ──
  var pendentes = _getProtocolosPendentesWpp();
  if (pendentes.length === 0) {
    registrarLogSistema("WPP_CYCLE", "Nenhum protocolo pendente elegível para notificação.");
    return 0;
  }

  registrarLogSistema("WPP_CYCLE_START", "Encontrados: " + pendentes.length + " protocolos. Limite: " + maxEnvios);

  var ss = getSs();
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  var colNotif = cfg.COL_NOTIF_WPP || 13; // Coluna M
  var enviados = 0;
  var falhas = 0;
  var agora = new Date();

  for (var i = 0; i < pendentes.length && enviados < maxEnvios; i++) {
    var p = pendentes[i];

    var resultado = _enviarMensagemWhatsApp(p.telefone, {
      obrigacao: p.obrigacao,
      vencimento: p.vencimento,
      cliente: p.cliente,
      protocolo: p.protocolo
    });

    if (resultado.success) {
      // Grava a data de notificação na Coluna M para TODOS os protocolos desse envio agrupado
      for (var r = 0; r < p.linhasPlanilha.length; r++) {
        wsProt.getRange(p.linhasPlanilha[r], colNotif).setValue(agora);
      }
      enviados++;
      registrarLogSistema("WPP_SENT", "Prots: [" + p.listaProts + "] → " + p.telefone + " (MsgID: " + resultado.messageId + ")");
    } else {
      falhas++;
      registrarLogSistema("WPP_FAIL", "Prots: [" + p.listaProts + "] → " + p.telefone + " | Erro: " + resultado.error);
    }

    // Respiro entre envios para não estourar rate limit da API
    Utilities.sleep(500);
  }

  if (enviados > 0) SpreadsheetApp.flush();
  registrarLogSistema("WPP_CYCLE_END", "Enviados: " + enviados + " | Falhas: " + falhas + " | Total elegível: " + pendentes.length);
  return enviados;
}

// ═══════════════════════════════════════════════════════════════════════
// 🧪 TESTE MANUAL (Executar pelo Editor do Apps Script)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Envia UMA mensagem de teste usando DADOS REAIS da base.
 * Busca o cliente associado ao número de teste em DB_CLIENTES
 * e localiza um protocolo pendente real em DB_PROTOCOLOS.
 * 
 * COMO USAR:
 *   1. Execute esta função pelo editor (Executar → testarWhatsAppManual)
 *   2. Verifique se recebeu a mensagem no WhatsApp com as variáveis preenchidas
 */
function testarWhatsAppManual() {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  if (!cfg.API_TOKEN) {
    SpreadsheetApp.getUi().alert("⚠️ Preencha o API_TOKEN do Maxbot no Config.js antes de testar.");
    return;
  }

  var NUMERO_TESTE = "5534999721001";
  var ss = getSs();

  // ── PASSO 1: Localizar o cliente pelo telefone em DB_CLIENTES ──
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  if (!wsCli) { SpreadsheetApp.getUi().alert("❌ Aba DB_CLIENTES não encontrada."); return; }

  var dataCli = wsCli.getDataRange().getValues();
  var nomeCliente = null;

  for (var c = 1; c < dataCli.length; c++) {
    var telefonesRaw = String(dataCli[c][5] || ""); // Coluna F = TELEFONE
    if (telefonesRaw.indexOf(NUMERO_TESTE.replace(/^55/, "")) > -1 || telefonesRaw.indexOf(NUMERO_TESTE) > -1) {
      nomeCliente = String(dataCli[c][1]); // Coluna B = CLIENTE
      break;
    }
  }

  if (!nomeCliente) {
    SpreadsheetApp.getUi().alert("❌ Nenhum cliente encontrado com o telefone " + NUMERO_TESTE + " na aba DB_CLIENTES.");
    return;
  }

  console.log("WPP TESTE — Cliente localizado: " + nomeCliente);

  // ── PASSO 2: Buscar um protocolo pendente real para esse cliente ──
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  if (!wsProt) { SpreadsheetApp.getUi().alert("❌ Aba DB_PROTOCOLOS não encontrada."); return; }

  var lastRow = wsProt.getLastRow();
  var protocoloReal = null;

  if (lastRow > 1) {
    var numRows = Math.min(lastRow - 1, 300);
    var startRow = lastRow - numRows + 1;
    var dataProt = wsProt.getRange(startRow, 1, numRows, 13).getValues();

    for (var i = dataProt.length - 1; i >= 0; i--) {
      var clienteProt = String(dataProt[i][1]); // Coluna B = CLIENTE
      if (norm(clienteProt) === norm(nomeCliente)) {
        var statusEnvio = String(dataProt[i][8]).toUpperCase().trim();   // Coluna I
        var confRecto = String(dataProt[i][9]).toUpperCase().trim();     // Coluna J
        var acaoProt = String(dataProt[i][11] || "").toUpperCase().trim(); // Coluna L
        var linkBruto = String(dataProt[i][7]).toUpperCase().trim();     // Coluna H

        // Aplica as mesmas regras de "pendente" da rotina principal
        if (acaoProt.indexOf("ENVIAR") === -1) continue;
        if (linkBruto.indexOf("SEM_ENVIO:") === 0) continue;

        var isLido = !(statusEnvio === "ENVIADO" && (confRecto === "" || confRecto === "---" || confRecto === "AGUARDANDO"));
        if (isLido) continue;

        var vctoLegal = dataProt[i][10];
        var vctoStr = "---";
        if (vctoLegal) {
          vctoStr = (vctoLegal instanceof Date) ? Utilities.formatDate(vctoLegal, "GMT-3", "dd/MM/yyyy") : String(vctoLegal);
        }
        protocoloReal = {
          obrigacao: String(dataProt[i][4]),   // Coluna E
          vencimento: vctoStr,                  // Coluna K
          cliente: clienteProt,              // Coluna B
          protocolo: String(dataProt[i][2])    // Coluna C
        };
        break;
      }
    }
  }

  if (!protocoloReal) {
    SpreadsheetApp.getUi().alert("⚠️ Cliente '" + nomeCliente + "' localizado, mas sem protocolo recente em DB_PROTOCOLOS.\n\nUsando dados de exemplo para o teste.");
    protocoloReal = {
      obrigacao: "OBRIGACAO TESTE",
      vencimento: Utilities.formatDate(new Date(), "GMT-3", "dd/MM/yyyy"),
      cliente: nomeCliente,
      protocolo: "PRT-TESTE-001"
    };
  }

  // ── PASSO 3: Exibir dados que serão enviados e solicitar confirmação ──
  var ui = SpreadsheetApp.getUi();
  var confirmacao = ui.alert(
    "📱 TESTE WHATSAPP — Dados Reais",
    "Cliente: " + protocoloReal.cliente +
    "\nObrigação: " + protocoloReal.obrigacao +
    "\nVencimento: " + protocoloReal.vencimento +
    "\nProtocolo: " + protocoloReal.protocolo +
    "\nTelefone: " + NUMERO_TESTE +
    "\n\nConfirma o envio do teste?",
    ui.ButtonSet.YES_NO
  );

  if (confirmacao !== ui.Button.YES) {
    ui.alert("Teste cancelado pelo usuário.");
    return;
  }

  // ── PASSO 4: Executar o envio ──
  var contactIdResolvido = _buscarContactIdNaApi(NUMERO_TESTE);
  console.log("WPP TESTE — Número: " + NUMERO_TESTE + " → contact_id resolvido: " + contactIdResolvido);

  var resultado = _enviarMensagemWhatsApp(NUMERO_TESTE, protocoloReal);

  var debugStr = resultado._debug ? "\ncontact_id: " + resultado._debug.contactId + " (" + resultado._debug.metodo + ")" : "";

  if (resultado.success) {
    ui.alert("✅ Mensagem de teste enviada com sucesso!\n\nMessage ID: " + resultado.messageId + "\nCliente: " + protocoloReal.cliente + "\nNúmero: " + NUMERO_TESTE + debugStr);
    registrarLogSistema("WPP_TEST_OK", "Teste real → " + protocoloReal.cliente + " | " + protocoloReal.obrigacao + " | Tel: " + NUMERO_TESTE + " | contact_id: " + (resultado._debug ? resultado._debug.contactId : "?"));
  } else {
    ui.alert("❌ Falha no envio de teste.\n\nErro: " + resultado.error + debugStr + "\n\nVerifique:\n1. API_TOKEN do Maxbot está correto?\n2. Template '" + cfg.TEMPLATE_NAME + "' está aprovado no Maxbot?\n3. O contato com número " + NUMERO_TESTE + " existe no Maxbot?");
    registrarLogSistema("WPP_TEST_FAIL", "Erro: " + resultado.error + " | contact_id: " + (resultado._debug ? resultado._debug.contactId : "?"));
  }
}

// ═══════════════════════════════════════════════════════════════════════
// ⚙️ GESTÃO DE GATILHOS (Trigger Management)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Instala o gatilho diário para executar as notificações WhatsApp.
 * ⚠️ SÓ EXECUTE QUANDO TODAS AS CONDIÇÕES ESTIVEREM APROVADAS:
 *   - Template aprovado na Meta
 *   - API_TOKEN e PHONE_NUMBER_ID preenchidos
 *   - ATIVO = true
 *   - Teste manual (testarWhatsAppManual) bem-sucedido
 */
function instalarGatilhoWhatsApp() {
  var check = _validarPreRequisitosWpp();
  if (!check.ok) {
    SpreadsheetApp.getUi().alert("⛔ Não é possível instalar o gatilho.\n\nMotivo: " + check.motivo);
    return;
  }

  var nomeFuncao = "executarNotificacaoWhatsApp";
  var triggers = ScriptApp.getProjectTriggers();

  // Remove gatilhos anteriores para evitar duplicação
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === nomeFuncao) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  // Cria gatilho diário às 08:30h
  ScriptApp.newTrigger(nomeFuncao)
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .nearMinute(30)
    .create();

  registrarLogSistema("WPP_TRIGGER_ON", "Gatilho diário instalado (08:30h).");
  SpreadsheetApp.getUi().alert("✅ Gatilho WhatsApp Ativado!\n\nA rotina de notificação rodará diariamente às 08:30h.\nProtocolos não lidos serão notificados respeitando o intervalo de " + CONFIG_SISTEMA.WHATSAPP.DIAS_INTERVALO_RENOTIFICACAO + " dias.");
}

/**
 * Remove o gatilho de notificações WhatsApp (Desligamento de emergência).
 */
function removerGatilhoWhatsApp() {
  var nomeFuncao = "executarNotificacaoWhatsApp";
  var triggers = ScriptApp.getProjectTriggers();
  var removidos = 0;

  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === nomeFuncao) {
      ScriptApp.deleteTrigger(triggers[i]);
      removidos++;
    }
  }

  registrarLogSistema("WPP_TRIGGER_OFF", "Gatilho(s) removido(s): " + removidos);
  SpreadsheetApp.getUi().alert("🛑 Gatilho WhatsApp Removido.\n\nNenhuma notificação será enviada automaticamente.\nGatilhos removidos: " + removidos);
}

// ═══════════════════════════════════════════════════════════════════════
// 📊 DIAGNÓSTICO (Verificação sem enviar nada)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Exibe um relatório de quantos protocolos SERIAM notificados, sem enviar nada.
 * Use para validar a lógica de filtragem antes de ativar o módulo.
 */
function diagnosticoWhatsApp() {
  var pendentes = _getProtocolosPendentesWpp();

  var msg = "📊 DIAGNÓSTICO WHATSAPP\n\n";
  msg += "Protocolos elegíveis: " + pendentes.length + "\n\n";

  if (pendentes.length > 0) {
    var max = Math.min(pendentes.length, 10);
    msg += "Primeiros " + max + " protocolos:\n";
    for (var i = 0; i < max; i++) {
      var p = pendentes[i];
      msg += "  • " + p.cliente + " | " + p.obrigacao + " | Vcto: " + p.vencimento + " | Tel: " + p.telefone + "\n";
    }
    if (pendentes.length > 10) msg += "  ... e mais " + (pendentes.length - 10) + " protocolos.\n";
  }

  msg += "\n── Configuração ──\n";
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  msg += "ATIVO: " + cfg.ATIVO + "\n";
  msg += "API_TOKEN: " + (cfg.API_TOKEN ? "✅ Preenchido" : "❌ Vazio") + "\n";
  msg += "TEMPLATE: " + cfg.TEMPLATE_NAME + "\n";
  msg += "Intervalo: " + cfg.DIAS_INTERVALO_RENOTIFICACAO + " dias\n";
  msg += "Limite/ciclo: " + cfg.MAX_ENVIOS_POR_CICLO + " mensagens\n";

  try {
    SpreadsheetApp.getUi().alert(msg);
  } catch (e) {
    console.log(msg);
  }
}

// ═════════════════════════════════════════════════════════════════════
// 🔍 DIAGNÓSTICO MAXBOT (Descobrir IDs e comandos)
// ═════════════════════════════════════════════════════════════════════

/**
 * Consulta a API do Maxbot para listar templates e canais disponíveis.
 * Execute esta função no editor do Apps Script para descobrir:
 *   - template_id (necessário para open_followup)
 *   - channel_token (necessário para open_followup)
 *   - Nomes exatos dos templates aprovados
 */
function diagnosticoMaxbot() {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  if (!cfg.API_TOKEN) {
    SpreadsheetApp.getUi().alert("⚠️ Preencha o API_TOKEN do Maxbot primeiro.");
    return;
  }

  var url = "https://app.maxbot.com.br/api/v1.php";
  var msg = "🔍 DIAGNÓSTICO MAXBOT\n\n";

  // ── 1. Listar Templates (apenas ID + Título) ──
  try {
    var respTemplates = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ token: cfg.API_TOKEN, cmd: "get_template" }),
      muteHttpExceptions: true
    });
    var dataTemplates = JSON.parse(respTemplates.getContentText());
    msg += "── TEMPLATES ──\n";
    if (dataTemplates.template && dataTemplates.template.length > 0) {
      for (var i = 0; i < dataTemplates.template.length; i++) {
        var t = dataTemplates.template[i];
        msg += "  ID: " + t.id + " | " + t.title + " | Tipo: " + t.type + " | WABA: " + (t.waba_status || "N/A") + "\n";
      }
    } else {
      msg += "  Nenhum template encontrado.\n";
    }
  } catch (e) {
    msg += "Erro ao buscar templates: " + e.message + "\n";
  }

  msg += "\n";

  // ── 2. Listar Canais ──
  try {
    var respCanais = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ token: cfg.API_TOKEN, cmd: "get_channel" }),
      muteHttpExceptions: true
    });
    var dataCanais = JSON.parse(respCanais.getContentText());
    msg += "── CANAIS ──\n";
    if (dataCanais.data && dataCanais.data.length > 0) {
      for (var j = 0; j < dataCanais.data.length; j++) {
        var c = dataCanais.data[j];
        msg += "  Token: " + c.token + " | " + c.title + "\n";
      }
    }
  } catch (e) {
    msg += "Erro ao buscar canais: " + e.message + "\n";
  }

  console.log(msg);

  // ── 3. Listar Setores ──
  try {
    var respSetores = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ token: cfg.API_TOKEN, cmd: "get_sector" }),
      muteHttpExceptions: true
    });
    msg += "\n── SETORES ──\n";
    msg += respSetores.getContentText().substring(0, 500) + "\n";
  } catch (e) {
    msg += "Erro ao buscar setores: " + e.message + "\n";
  }

  console.log(msg);
  try {
    SpreadsheetApp.getUi().alert(msg);
  } catch (e) { }
}

/**
 * Lista os setores disponíveis no Maxbot. Execute para descobrir o sector_id correto.
 */
function listarSetoresMaxbot() {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var resp = UrlFetchApp.fetch("https://app.maxbot.com.br/api/v1.php", {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ token: cfg.API_TOKEN, cmd: "get_service_sector" }),
    muteHttpExceptions: true
  });
  var data = JSON.parse(resp.getContentText());
  var msg = "SETORES DE ATENDIMENTO:\n\n";
  if (data.service_sector && data.service_sector.length > 0) {
    for (var i = 0; i < data.service_sector.length; i++) {
      var s = data.service_sector[i];
      msg += "ID: " + s.id + " | " + s.code + " | " + s.name + "\n";
    }
  } else {
    msg += JSON.stringify(data);
  }
  console.log(msg);
  SpreadsheetApp.getUi().alert(msg);
}

