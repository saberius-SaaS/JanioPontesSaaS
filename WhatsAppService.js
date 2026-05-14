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

  // Lê os últimos 300 protocolos (mesmo limite do DriveActivityService)
  var numRows = Math.min(lastRow - 1, 300);
  var startRow = lastRow - numRows + 1;
  var dataProt = wsProt.getRange(startRow, 1, numRows, 13).getValues(); // A até M

  // Mapa de telefones: CLIENTE → TELEFONE
  var wsCli = ss.getSheetByName(CONFIG_SISTEMA.ABA_CLIENTES);
  if (!wsCli) return [];
  var dataCli = wsCli.getDataRange().getValues();
  var mapaTelefone = {};
  for (var c = 1; c < dataCli.length; c++) {
    var nomeNorm = norm(dataCli[c][1]);
    var telefone = String(dataCli[c][5] || "").replace(/\D/g, ""); // Coluna F: TELEFONE
    if (nomeNorm && telefone) mapaTelefone[nomeNorm] = telefone;
  }

  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var hoje = new Date();
  var intervaloMs = (cfg.DIAS_INTERVALO_RENOTIFICACAO || 3) * 24 * 60 * 60 * 1000;
  var pendentes = [];

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
    var telefoneCliente = mapaTelefone[norm(clienteNome)];
    if (!telefoneCliente || telefoneCliente.length < 12) continue;

    // ── Dados para o template ──
    var vctoLegal = dataProt[i][10];
    var vctoStr = "---";
    if (vctoLegal) {
      vctoStr = (vctoLegal instanceof Date) ? Utilities.formatDate(vctoLegal, "GMT-3", "dd/MM/yyyy") : String(vctoLegal);
    }

    pendentes.push({
      rowSheet: startRow + i,                         // Linha real na planilha (1-based)
      obrigacao: String(dataProt[i][4]),               // {{1}} [INFO1] Nome do Documento
      vencimento: vctoStr,                             // {{2}} [INFO2] Data de Vencimento Legal
      cliente: clienteNome,                           // {{3}} [INFO3] Nome do Cliente
      protocolo: String(dataProt[i][2]),                // {{4}} [INFO4] Número do Protocolo
      telefone: telefoneCliente                        // Número WhatsApp destino
    });
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
var _cacheContatosMaxbot = null;

/**
 * Baixa a lista de contatos do Maxbot e retorna um mapa whatsapp → contact_id.
 * Indexa por whatsapp, mobile_phone e phone para máxima cobertura.
 */
function _getMapaContatosMaxbot() {
  if (_cacheContatosMaxbot) return _cacheContatosMaxbot;

  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var url = "https://app.maxbot.com.br/api/v1.php";
  var mapa = {};

  try {
    var resp = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        token: cfg.API_TOKEN,
        cmd: "get_contact",
        data_ini: "2020-01-01",
        data_fim: Utilities.formatDate(new Date(), "GMT-3", "yyyy-MM-dd")
      }),
      muteHttpExceptions: true
    });
    var data = JSON.parse(resp.getContentText());

    if (data.status === 1 && data.data && data.data.length > 0) {
      for (var i = 0; i < data.data.length; i++) {
        var c = data.data[i];
        var cid = c.id;
        var nums = [
          String(c.whatsapp || ""),
          String(c.mobile_phone || ""),
          String(c.phone || "")
        ];
        for (var n = 0; n < nums.length; n++) {
          var wpp = nums[n].replace(/\D/g, "");
          if (wpp && cid) {
            mapa[wpp] = cid;
          }
        }
      }
    }
  } catch (e) {
    console.log("Erro ao buscar contatos Maxbot: " + e.message);
  }

  _cacheContatosMaxbot = mapa;
  return mapa;
}

/**
 * Busca o contact_id do Maxbot a partir de um telefone.
 * Tenta formato exato, com/sem código 55, e busca parcial pelos últimos 8 dígitos.
 * A busca parcial resolve diferenças do 9° dígito entre formatos antigo/novo.
 */
function _buscarContactId(telefone, mapaContatos) {
  var tel = String(telefone).replace(/\D/g, "");

  // Tentativa 1: formato exato
  if (mapaContatos[tel]) return mapaContatos[tel];

  // Tentativa 2: sem código de país (55)
  var semPais = tel.replace(/^55/, "");
  if (mapaContatos[semPais]) return mapaContatos[semPais];

  // Tentativa 3: com código de país
  if (mapaContatos["55" + tel]) return mapaContatos["55" + tel];

  // Tentativa 4: busca parcial (últimos 8 dígitos)
  var parcial = tel.slice(-8);
  var keys = Object.keys(mapaContatos);
  for (var k = 0; k < keys.length; k++) {
    if (keys[k].slice(-8) === parcial) {
      return mapaContatos[keys[k]];
    }
  }

  return null;
}

function _enviarMensagemWhatsApp(telefone, params) {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  var url = "https://app.maxbot.com.br/api/v1.php";

  // ── PASSO 1: Buscar contact_id ──
  var mapaContatos = _getMapaContatosMaxbot();
  var contactId = _buscarContactId(telefone, mapaContatos);

  // Se não encontrou no mapa, tenta criar o contato
  if (!contactId) {
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
      contactId = bodyContato.contact_id || bodyContato.id || null;
    } catch (e) {
      // Falha silenciosa — será tratada abaixo
    }
  }

  if (!contactId) {
    return { success: false, messageId: "", error: "Contato não encontrado no Maxbot para " + telefone };
  }

  // ── PASSO 2: Enviar template via open_followup ──
  var payload = {
    token: cfg.API_TOKEN,
    cmd: "open_followup",
    channel_token: cfg.CHANNEL_TOKEN,
    contact_id: contactId,
    template_id: cfg.TEMPLATE_ID,
    sector_id: 8454,  // Recepção
    attendant_id: 0,
    scheduled: 0,
    date_time: (function() { var d = new Date(); d.setMinutes(d.getMinutes() < 30 ? 0 : 30); d.setSeconds(0); return Utilities.formatDate(d, "GMT-3", "yyyy-MM-dd HH:mm:ss"); })(),
    body_values: [
      params.obrigacao,
      params.vencimento,
      params.cliente,
      params.protocolo
    ]
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
      var msgId = body.msg_id || body.id || body.followup_id || "OK";
      return { success: true, messageId: String(msgId), error: "" };
    } else {
      var errMsg = body.msg || body.message || body.error || ("HTTP " + code);
      return { success: false, messageId: "", error: String(errMsg) };
    }
  } catch (e) {
    return { success: false, messageId: "", error: e.message };
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
      // Grava a data de notificação na Coluna M para controle anti-spam
      wsProt.getRange(p.rowSheet, colNotif).setValue(agora);
      enviados++;
      registrarLogSistema("WPP_SENT", "Prot: " + p.protocolo + " → " + p.telefone + " (MsgID: " + resultado.messageId + ")");
    } else {
      falhas++;
      registrarLogSistema("WPP_FAIL", "Prot: " + p.protocolo + " → " + p.telefone + " | Erro: " + resultado.error);
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
 * Envia UMA mensagem de teste para um número específico.
 * Use para validar a integração com a API antes de ativar o módulo.
 * 
 * COMO USAR:
 *   1. Preencha API_TOKEN e PHONE_NUMBER_ID no Config.js
 *   2. Altere o número abaixo para o seu número pessoal
 *   3. Execute esta função pelo editor (Executar → testarWhatsAppManual)
 *   4. Verifique se recebeu a mensagem no WhatsApp
 */
function testarWhatsAppManual() {
  var cfg = CONFIG_SISTEMA.WHATSAPP;
  if (!cfg.API_TOKEN) {
    SpreadsheetApp.getUi().alert("⚠️ Preencha o API_TOKEN do Maxbot no Config.js antes de testar.");
    return;
  }

  // ── ALTERE ESTE NÚMERO PARA O SEU NÚMERO DE TESTE ──
  var NUMERO_TESTE = "5534999721001";

  var resultado = _enviarMensagemWhatsApp(NUMERO_TESTE, {
    obrigacao: "DCTF - Declaração de Débitos e Créditos",
    vencimento: "20/06/2026",
    cliente: "EMPRESA TESTE LTDA",
    protocolo: "PRT-TESTE-001"
  });

  if (resultado.success) {
    SpreadsheetApp.getUi().alert("✅ Mensagem de teste enviada com sucesso!\n\nMessage ID: " + resultado.messageId + "\nNúmero: " + NUMERO_TESTE);
    registrarLogSistema("WPP_TEST_OK", "Teste manual enviado para " + NUMERO_TESTE);
  } else {
    SpreadsheetApp.getUi().alert("❌ Falha no envio de teste.\n\nErro: " + resultado.error + "\n\nVerifique:\n1. API_TOKEN do Maxbot está correto?\n2. Template '" + cfg.TEMPLATE_NAME + "' está aprovado no Maxbot?");
    registrarLogSistema("WPP_TEST_FAIL", "Erro: " + resultado.error);
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
  } catch (e) {}
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

