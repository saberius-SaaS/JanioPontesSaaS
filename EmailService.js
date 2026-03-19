/**
 * 📧 MOTOR DE E-MAIL v128.12 (Cobrança Automática + Padronização + Rastreio Anti-Bot)
 */

function getPublicWebAppUrl() {
  if (CONFIG_SISTEMA.URL_WEBAPP && CONFIG_SISTEMA.URL_WEBAPP.length > 20) {
    var manualUrl = CONFIG_SISTEMA.URL_WEBAPP.trim();
    return manualUrl.endsWith('/') ? manualUrl.slice(0, -1) : manualUrl;
  }
  return ScriptApp.getService().getUrl();
}

/**
 * Notificação de Entrega ao Cliente (ENVIO DE DOCUMENTOS)
 */
/**
 * Notificação de Entrega ao Cliente (Ajustado p/ NÃO enviar links diretos se o user preferir)
 */
function notificarEntregaClienteRefatorada(cliente, obrigacao, protocolo, emailCli, linksArquivo, pastaLink, rowIdx, incluirLinks) {
  if(!emailCli || emailCli.indexOf("@") === -1) return;
  try {
    var webAppUrl = getPublicWebAppUrl();
    var connector = webAppUrl.indexOf('?') > -1 ? '&' : '?';
    var urlTrackRepo = webAppUrl + connector + "mode=repo&p=" + protocolo + "&r=" + rowIdx;
    
    // linksArquivo agora é um Array
    var links = Array.isArray(linksArquivo) ? linksArquivo : (linksArquivo ? [linksArquivo] : []);
    var htmlLinks = "";

    // Só gera o bloco de links se explicitamente solicitado (Padrão: Off para Auditoria)
    if (incluirLinks && links.length > 0) {
      if (links.length === 1) {
        var linkObj = links[0];
        var url = typeof linkObj === 'object' ? linkObj.url : linkObj;
        var nomeExibicao = typeof linkObj === 'object' ? linkObj.name : "Documento";
        var urlTrack = webAppUrl + connector + "mode=track&p=" + protocolo + "&r=" + rowIdx + "&dest=" + encodeURIComponent(url);
        htmlLinks = `
          <div style="margin-bottom:25px;">
            <a href="${urlTrack}" target="_blank" style="display:inline-block; background-color:#1C3051; color:#ffffff; padding:20px 40px; border-radius:12px; text-decoration:none; font-size:13px; font-weight:900; text-transform:uppercase; width:100%; box-sizing:border-box; letter-spacing:1px; box-shadow: 0 4px 6px -1px rgba(28, 48, 81, 0.2);">ABRIR: ${nomeExibicao.toUpperCase()}</a>
          </div>
        `;
      } else {
        htmlLinks = '<div style="margin-bottom:25px; text-align:left;">';
        links.forEach(function(linkObj, index) {
          var url = typeof linkObj === 'object' ? linkObj.url : linkObj;
          var nomeExibicao = typeof linkObj === 'object' ? linkObj.name : ("DOCUMENTO " + (index + 1));
          var urlTrack = webAppUrl + connector + "mode=track&p=" + protocolo + "&r=" + rowIdx + "&dest=" + encodeURIComponent(url);
          htmlLinks += `
            <div style="margin-bottom:12px;">
              <a href="${urlTrack}" target="_blank" style="display:flex; align-items:center; background-color:#ffffff; color:#1C3051; border:1px solid #e2e8f0; padding:18px; border-radius:12px; text-decoration:none; font-size:13px; font-weight:700; width:100%; box-sizing:border-box;">
                <span style="margin-right:12px; font-size:18px;">📄</span>
                <div style="flex-grow:1;">${nomeExibicao}</div>
              </a>
            </div>
          `;
        });
        htmlLinks += '</div>';
      }
    }

    var html = `
      <div style="margin:0; padding:0; background-color:#f8fafc; font-family:'Inter', sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:550px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);">
          <tr><td style="padding:25px; background-color:#1C3051; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.8; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">ENVIO DE DOCUMENTOS</div>
          </td></tr>
          <tr><td style="padding:45px 35px; text-align:center;">
              <h2 style="color:#1e293b; margin:0 0 10px 0; font-size:20px; font-weight:700;">Olá, ${cliente}</h2>
              <p style="color:#64748b; font-size:14px; margin-bottom:35px; line-height:1.5;">O documento <b>${obrigacao}</b> foi processado com sucesso.</p>
              
              ${htmlLinks}
              
              <div style="font-size:9px; color:#94a3b8; margin-bottom:25px; font-weight:700; text-transform:uppercase;">Protocolo de Entrega: ${protocolo}</div>
              
              <div style="margin-top:20px; border-top:1px solid #f1f5f9; padding-top:30px;">
                <p style="color:#94a3b8; font-size:11px; margin-bottom:15px; font-weight:600;">Acesse seu repositório digital para ver este e outros documentos:</p>
                <a href="${urlTrackRepo}" target="_blank" style="display:inline-block; background-color:transparent; border:2px solid #1C3051; color:#1C3051; padding:14px; border-radius:12px; text-decoration:none; font-size:11px; font-weight:800; text-transform:uppercase; width:100%; box-sizing:border-box;">📂 REPOSITÓRIO DE ARQUIVOS</a>
              </div>
          </td></tr>

          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b; font-weight:400; line-height:1.4;">Monitoramento legal de abertura de mensagem.</div>
          </td></tr>
        </table>
      </div>
    `;

    MailApp.sendEmail({ to: emailCli, subject: "📄 DOCUMENTO DISPONÍVEL: " + obrigacao + " [" + protocolo + "]", htmlBody: html });
    registrarLogSistema("EMAIL_SENT", "Prot: " + protocolo);
  } catch (e) { registrarLogSistema("EMAIL_SEND_FAIL", e.message); }
}

/**
 * 🛡️ Notificação de Solicitação (SOLICITAR DOCUMENTOS)
 */
function enviarSolicitacaoAoCliente(cliente, emailCli, solicitacao, idSolicitacao) {
  if(!emailCli || emailCli.indexOf("@") === -1) return;
  var baseUrl = getPublicWebAppUrl(); 
  var portalLink = baseUrl + (baseUrl.indexOf('?') > -1 ? '&' : '?') + "mode=client&sol=" + String(idSolicitacao).trim();
  
  try {
    var html = `
      <div style="margin:0; padding:0; background-color:#f8fafc; font-family:sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:550px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);">
          <tr><td style="padding:25px; background-color:#1C3051; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.8; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">SOLICITAÇÃO DE DOCUMENTOS</div>
          </td></tr>
          <tr><td style="padding:45px 35px; text-align:center;">
              <h2 style="color:#1e293b; margin:0 0 10px 0; font-size:20px; font-weight:700;">Olá, ${cliente}</h2>
              <p style="color:#64748b; font-size:14px; margin-bottom:25px; line-height:1.6;">Para darmos continuidade aos seus processos contábeis, necessitamos que nos envie o seguinte documento:</p>
              <div style="background-color:#fff5f5; border-left:4px solid #ef4444; padding:20px; margin-bottom:30px; text-align:left; border-radius:4px;">
                <div style="font-size:10px; color:#b91c1c; font-weight:800; text-transform:uppercase; margin-bottom:8px;">Documento/Informação Solicitada:</div>
                <div style="font-size:14px; font-weight:600; color:#7f1d1d; line-height:1.5;">${solicitacao}</div>
              </div>
              <div style="margin-bottom:10px;">
                <a href="${portalLink}" target="_blank" style="display:inline-block; background-color:#1C3051; color:#ffffff; padding:20px 40px; border-radius:12px; text-decoration:none; font-size:13px; font-weight:900; text-transform:uppercase; width:100%; box-sizing:border-box; letter-spacing:1px;">ENVIAR ARQUIVOS AGORA</a>
              </div>
              <p style="font-size:11px; color:#94a3b8; font-weight:500;">Ao clicar no botão acima, você será direcionado ao nosso portal de envio seguro.</p>
          </td></tr>
          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b; font-weight:400; line-height:1.4;">Esta é uma mensagem automática. A visualização deste e-mail é monitorada para fins de prova de entrega legal.</div>
          </td></tr>
        </table>
      </div>
    `;
    MailApp.sendEmail({ to: emailCli, subject: "⚠️ SOLICITAÇÃO DE DOCUMENTO: " + cliente, htmlBody: html });
    registrarLogSistema("SOLICITATION_EMAIL_SENT", "Cliente: " + cliente);
  } catch (e) { registrarLogSistema("EMAIL_REQ_FAIL", e.message); }
}

/**
 * 📢 LEMBRETE DE COBRANÇA (Novo!) - PADRÃO ELITE
 */
function enviarLembreteCobranca(cliente, emailCli, solicitacao, idSolicitacao, qtdAvisos) {
  if(!emailCli || emailCli.indexOf("@") === -1) return;
  var baseUrl = getPublicWebAppUrl(); 
  var portalLink = baseUrl + (baseUrl.indexOf('?') > -1 ? '&' : '?') + "mode=client&sol=" + String(idSolicitacao).trim();
  
  try {
    var html = `
      <div style="margin:0; padding:0; background-color:#f8fafc; font-family:sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:550px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);">
          <tr><td style="padding:25px; background-color:#b91c1c; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.9; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">LEMBRETE DE PENDÊNCIA</div>
          </td></tr>
          
          <tr><td style="padding:45px 35px; text-align:center;">
              <h2 style="color:#1e293b; margin:0 0 10px 0; font-size:20px; font-weight:700;">Olá, ${cliente}</h2>
              <p style="color:#64748b; font-size:14px; margin-bottom:25px; line-height:1.6;">Verificamos em nosso sistema que a solicitação abaixo ainda consta como <b>PENDENTE</b>.</p>
              
              <div style="background-color:#fff5f5; border:1px solid #fee2e2; padding:20px; margin-bottom:30px; text-align:left; border-radius:8px;">
                <div style="font-size:10px; color:#991b1b; font-weight:800; text-transform:uppercase; margin-bottom:8px;">Item Pendente (Aviso #${qtdAvisos + 1}):</div>
                <div style="font-size:14px; font-weight:600; color:#7f1d1d; line-height:1.5;">${solicitacao}</div>
              </div>

              <div style="margin-bottom:10px;">
                <a href="${portalLink}" target="_blank" style="display:inline-block; background-color:#b91c1c; color:#ffffff; padding:20px 40px; border-radius:12px; text-decoration:none; font-size:13px; font-weight:900; text-transform:uppercase; width:100%; box-sizing:border-box; letter-spacing:1px;">RESOLVER PENDÊNCIA AGORA</a>
              </div>
              <p style="font-size:11px; color:#94a3b8; font-weight:500;">Evite multas e atrasos. Envie o documento solicitado o quanto antes.</p>
          </td></tr>
          
          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b; font-weight:400; line-height:1.4;">Esta é uma mensagem automática. A visualização deste e-mail é monitorada para fins de prova de entrega legal.</div>
          </td></tr>
        </table>
      </div>
    `;

    MailApp.sendEmail({ to: emailCli, subject: "🔴 PENDÊNCIA: " + cliente + " (Aviso " + (qtdAvisos + 1) + ")", htmlBody: html });
    registrarLogSistema("COBRANCA_AUTO_SENT", "Cliente: " + cliente + " | Aviso #" + (qtdAvisos + 1));
  } catch (e) { registrarLogSistema("EMAIL_COB_FAIL", e.message); }
}

function registrarInteracaoEmail(protocolo, acao, rowIdx) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsProt = ss.getSheetByName(CONFIG_SISTEMA.ABA_PROTOCOLOS);
  var agora = new Date();
  if (!protocolo) return;
  var pSearch = String(protocolo).trim().toUpperCase();
  try {
    if (wsProt) {
      var targetRow = -1;
      var directRow = parseInt(rowIdx);
      if (!isNaN(directRow) && directRow > 1) {
        var protNaLinha = String(wsProt.getRange(directRow, 3).getValue()).trim().toUpperCase();
        if (protNaLinha === pSearch) targetRow = directRow;
      }
      if (targetRow === -1) {
        var dataP = wsProt.getDataRange().getValues();
        for (var k = 0; k < dataP.length; k++) { 
          if (String(dataP[k][2]).trim().toUpperCase() === pSearch) { targetRow = k + 1; break; } 
        }
      }
      if (targetRow !== -1) {
        wsProt.getRange(targetRow, 9).setValue(CONFIG_SISTEMA.STATUS.ENTREGUE);
        wsProt.getRange(targetRow, 10).setValue(agora);
      }
    }
    SpreadsheetApp.flush();
  } catch (e) { registrarLogSistema("TRACKING_ERR", e.message); }
}

function notificarRecebimentoAoResponsavel(cliente, pedido, responsavel, links) {
  try {
    var listItems = links.map(function(l) {
       return '<li style="margin-bottom:8px;"><a href="' + l + '" target="_blank" style="color:#1C3051; font-weight:700; text-decoration:none;">📄 Visualizar Arquivo</a></li>';
    }).join('');
    var html = `
      <div style="margin:0; padding:0; background-color:#f8fafc; font-family:sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:550px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);">
          <tr><td style="padding:25px; background-color:#1C3051; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.8; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">RECEBIMENTO DE ARQUIVOS</div>
          </td></tr>
          <tr><td style="padding:45px 35px;">
              <h2 style="color:#1e293b; margin:0 0 15px 0; font-size:18px; font-weight:700;">Nova entrega realizada</h2>
              <p style="color:#64748b; font-size:14px; margin-bottom:25px; line-height:1.5;">O cliente <strong>${cliente}</strong> acabou de enviar documentos via Portal, referentes à solicitação:</p>
              <div style="background-color:#f1f5f9; border-left:4px solid #1C3051; padding:15px; margin-bottom:25px; border-radius:4px;">
                <div style="font-size:13px; font-weight:600; color:#334155;">"${pedido}"</div>
              </div>
              <div style="margin-bottom:10px; font-size:12px; font-weight:800; color:#1C3051; text-transform:uppercase;">Arquivos Disponíveis:</div>
              <ul style="padding-left:20px; font-size:13px; color:#1C3051;">
                ${listItems}
              </ul>
          </td></tr>
          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b; font-weight:400; line-height:1.4;">Esta é uma mensagem automática de controle interno.</div>
          </td></tr>
        </table>
      </div>
    `;
    MailApp.sendEmail({ to: responsavel, subject: "✅ ARQUIVOS RECEBIDOS: " + cliente, htmlBody: html });
  } catch (e) { registrarLogSistema("NOTIF_RESP_FAIL", e.message); }
}

/**
 * Envia o Relatório de Análise Gerado pela IA para o Responsável do Cliente (E-mail Formatado)
 * Agora recebe TEXTO (Markdown de preferência) em vez de PDF.
 */
function enviarRelatorioAnaliseIA(emailResponsavel, nomeResponsavel, cliente, obrigacao, analiseTexto) {
  if (!emailResponsavel || emailResponsavel.indexOf("@") === -1) return;
  
  try {
    var analiseHtml;
    var trimTexto = analiseTexto.trim();

    // Detecção Inteligente: Se começar com < e tiver tags HTML, tratamos como HTML puro
    if (trimTexto.startsWith("<") && (trimTexto.indexOf("</div>") > -1 || trimTexto.indexOf("</table>") > -1 || trimTexto.indexOf("</p>") > -1)) {
       analiseHtml = analiseTexto; 
    } else {
       // Backup: Conversor Markdown mais robusto que o anterior
       analiseHtml = analiseTexto
        .replace(/^### (.*$)/gim, '<h3 style="color:#1C3051; margin-top:20px; border-left: 4px solid #1C3051; padding-left:10px;">$1</h3>')
        .replace(/^## (.*$)/gim, '<h2 style="color:#1C3051; margin-top:25px;">$1</h2>')
        .replace(/^# (.*$)/gim, '<h1 style="color:#1C3051;">$1</h1>')
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        .replace(/^\* (.*$)/gim, '<li style="margin-bottom:8px;">$1</li>');

       // Só aplica <br> se NÃO for HTML (para evitar espaçamento duplo em tabelas/divs)
       analiseHtml = analiseHtml.replace(/\n/g, '<br>');
    }

    var html = `
      <div style="margin:0; padding:0; background-color:#f8fafc; font-family:'Inter', sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:650px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);">
          <tr><td style="padding:25px; background-color:#1C3051; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.8; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">ANÁLISE DE PERFORMANCE</div>
          </td></tr>
          <tr><td style="padding:45px 35px;">
              <h2 style="color:#1e293b; margin:0 0 10px 0; font-size:20px; font-weight:700;">Olá, ${nomeResponsavel || cliente}</h2>
              <p style="color:#64748b; font-size:14px; margin-bottom:30px; line-height:1.5;">Com base no balancete de <b>${obrigacao}</b> da empresa <b>${cliente}</b>, geramos a seguinte análise estratégica:</p>
              
              <div style="background-color:#ffffff; border:1px solid #f1f5f9; padding:25px; border-radius:12px; color:#334155; font-size:14px; line-height:1.6;">
                ${analiseHtml}
              </div>

              <div style="margin-top:30px; text-align:center;">
                <p style="color:#94a3b8; font-size:12px;">Dúvidas sobre esta análise? Entre em contato com seu consultor.</p>
              </div>
          </td></tr>
          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b; font-weight:400;">Monitoramento legal de abertura de mensagem.</div>
          </td></tr>
        </table>
      </div>
    `;

    MailApp.sendEmail({
      to: emailResponsavel,
      subject: "📊 ANÁLISE ESTRATÉGICA: " + cliente + " (" + obrigacao + ")",
      htmlBody: html
    });
    
    registrarLogSistema("EMAIL_AI_REPORT_SENT", "Cliente: " + cliente);
  } catch (e) {
    registrarLogSistema("EMAIL_AI_REPORT_FAIL", e.message);
  }
}

/**
 * Notifica o Administrador sobre o Resultado da Auditoria (Aprovação ou Reprovação)
 */
function notificarAuditAdmin(cliente, obrigacao, aprovado, detalhes) {
  var emailAdmin = CONFIG_SISTEMA.EMAILS.ADMIN_AUDITORIA;
  if (!emailAdmin) return;

  var statusCor = aprovado ? "#10b981" : "#ef4444";
  var statusTexto = aprovado ? "APROVADO" : "REPROVADO";
  var objetivo = "AVISO DE CONFORMIDADE";

  var html = `
    <div style="margin:0; padding:0; background-color:#f8fafc; font-family:'Inter', sans-serif; padding:40px 20px;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width:550px; margin:0 auto; background-color:#ffffff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden;">
          <tr><td style="padding:25px; background-color:#1C3051; color:#ffffff; text-align:center;">
            <div style="font-size:16px; font-weight:900; letter-spacing:1px; line-height:1.2;">JANIO PONTES CONTABILIDADE</div>
            <div style="font-size:10px; font-weight:700; opacity:0.8; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">${objetivo}</div>
          </td></tr>
          <tr><td style="padding:40px 35px;">
              <div style="text-align:center; margin-bottom:30px;">
                <span style="display:inline-block; background-color:${statusCor}; color:white; padding:8px 16px; border-radius:30px; font-size:12px; font-weight:900;">AUDITORIA: ${statusTexto}</span>
              </div>
              <p style="color:#1e293b; font-size:14px; margin-bottom:20px;">O balancete do cliente <b>${cliente}</b> (${obrigacao}) foi auditado pelo motor de IA.</p>
              
              <div style="background-color:#ffffff; border:1px solid #e2e8f0; padding:25px; border-radius:12px; color:#334155; font-size:14px; line-height:1.6;">
                <strong style="color:#1C3051; display:block; margin-bottom:15px; border-bottom:1px solid #f1f5f9; padding-bottom:10px;">DETALHAMENTO DA AUDITORIA</strong>
                ${formatarDetalhesAudit(detalhes)}
              </div>
          </td></tr>
          <tr><td style="padding:25px; background-color:#f8fafc; border-top:1px solid #e2e8f0; text-align:center;">
              <div style="font-size:11px; color:#1C3051; font-weight:800; text-transform:uppercase; margin-bottom:4px;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</div>
              <div style="font-size:9px; color:#64748b;">Monitoramento legal de abertura de mensagem.</div>
          </td></tr>
        </table>
      </div>
  `;

  MailApp.sendEmail({
    to: emailAdmin,
    subject: (aprovado ? "✅" : "🚨") + " AUDITORIA " + statusTexto + ": " + cliente,
    htmlBody: html
  });
}

/**
 * Auxiliar para converter o texto bruto da IA em um checklist HTML bonito
 */
function formatarDetalhesAudit(texto) {
  if (!texto) return '<p>Sem detalhes disponíveis.</p>';
  
  var linhas = texto.split('\n');
  var html = '<div style="margin-top:10px;">';
  var emLista = false;

  linhas.forEach(function(linha) {
    var trimL = linha.trim();
    if (!trimL) return;

    // Detectar itens de checklist da IA: - [OK] ou - [FALHA]
    if (trimL.startsWith('- [OK]') || trimL.startsWith('- [FALHA]')) {
      if (!emLista) {
        html += '<ul style="list-style:none; padding:0; margin:0;">';
        emLista = true;
      }
      var status = trimL.indexOf('[OK]') > -1 ? 'OK' : 'FALHA';
      var cor = status === 'OK' ? '#10b981' : '#ef4444';
      var icone = status === 'OK' ? '✅' : '❌';
      var conteudo = trimL.replace('- [OK]', '').replace('- [FALHA]', '').trim();
      
      html += `
        <li style="display:flex; align-items:flex-start; margin-bottom:12px; padding:10px; background:#f8fafc; border-radius:8px; border-left:4px solid ${cor};">
          <span style="margin-right:10px; font-size:16px;">${icone}</span>
          <span style="font-size:13px; color:#1e293b;">${conteudo}</span>
        </li>
      `;
    } else if (trimL.startsWith('LISTA DE VERIFICAÇÃO') || trimL.startsWith('**') || trimL.indexOf('REPROVADO') > -1 || trimL.indexOf('APROVADO') > -1) {
      if (emLista) { html += '</ul>'; emLista = false; }
      html += `<p style="margin: 15px 0 10px 0; font-size:12px; font-weight:800; text-transform:uppercase; color:#64748b; letter-spacing:0.5px;">${trimL}</p>`;
    } else {
      if (emLista) { html += '</ul>'; emLista = false; }
      html += `<p style="margin-bottom:8px; font-size:13px; color:#475569;">${trimL}</p>`;
    }
  });

  if (emLista) html += '</ul>';
  html += '</div>';
  return html;
}