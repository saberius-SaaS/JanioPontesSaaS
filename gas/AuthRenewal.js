/**
 * 🔑 AUTH RENEWAL SERVICE
 * Arquivo dedicado para forçar a reautorização de todos os escopos do projeto.
 * Cada chamada "pro-forma" ativa um escopo diferente no manifesto (appsscript.json).
 */
function renovarTodosEscopos() {
  // Escopo: spreadsheets
  var ss = getSs();
  
  // Escopo: drive
  var root = DriveApp.getRootFolder();
  
  // Escopo: documents (OCR)
  var doc = DocumentApp.create("TEMP_AUTH_CHECK_" + new Date().getTime());
  DriveApp.getFileById(doc.getId()).setTrashed(true);
  
  // Escopo: script.send_mail
  var email = Session.getActiveUser().getEmail();
  
  // Escopo: script.external_request
  var test = UrlFetchApp.fetch("https://www.google.com", { muteHttpExceptions: true });
  
  return "✅ Todos os escopos foram autorizados com sucesso!";
}
