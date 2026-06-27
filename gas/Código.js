/**
 * 🛡️ SISTEMA DE GESTÃO CONTÁBIL | ELITE ARCHITECT
 * 🔧 STATUS: UNIFICADO v130.04 (Cache Performance)
 */

/**
 * Gatilho de Edição para Invalidação de Cache e Segurança
 */
function onEdit(e) {
  if (!e) return;

  // 🔒 MODO LEITURA: Bloqueia qualquer edição durante a migração
  if (CONFIG_SISTEMA.MODO_LEITURA) {
    if (e.range) e.range.setValue(e.oldValue || "");
    SpreadsheetApp.getUi().alert("🔒 SISTEMA TEMPORARIAMENTE SUSPENSO\n\nEstamos realizando uma atualização importante.\nNão utilize a planilha nem o sistema até que seja liberado pela administração.");
    return;
  }
  
  // Trava de Segurança: impede edição por usuários não cadastrados
  var userEmail = Session.getActiveUser().getEmail().toLowerCase().trim();
  var isAuthorized = false;
  var ss = getSs();
  var wsUsr = ss.getSheetByName("DB_USUARIOS");
  if (wsUsr) {
    var dataU = wsUsr.getDataRange().getValues();
    for (var i = 1; i < dataU.length; i++) {
        if (String(dataU[i][0]).toLowerCase().trim() === userEmail) { isAuthorized = true; break; }
    }
  }

  // Se o usuário não for autorizado e não for o proprietário (vazio na primeira execução ou gatilho comum)
  if (!isAuthorized && userEmail !== "") {
    SpreadsheetApp.getUi().alert("⛔ EDIÇÃO BLOQUEADA\nSeu acesso não está autorizado para realizar alterações diretas neste arquivo.");
    if (e.range) e.range.setValue(e.oldValue || "");
    return;
  }

  monitorarEdicaoParaCache(e);
}
