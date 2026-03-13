/**
 * 💾 MOTOR DE BACKUP E SEGURANÇA v130.09
 */

function executarBackupTotal() {
  var lock = LockService.getScriptLock();
  try { lock.waitLock(30000); } catch (e) { return; }

  try {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
    var idPastaBackup = CONFIG_SISTEMA.PASTAS.BACKUPS;
    var envNome = CONFIG_SISTEMA.PASTAS.NOME;
    
    var pastaDestino = DriveApp.getFolderById(idPastaBackup);
    var agora = new Date();
    var carimbo = Utilities.formatDate(agora, "GMT-3", "yyyy-MM-dd HH'h'mm");
    var nomeArquivo = "[" + envNome + "-BKP] " + ss.getName() + " - " + carimbo;

    var arquivoCopia = DriveApp.getFileById(ss.getId()).makeCopy(nomeArquivo, pastaDestino);
    registrarLogSistema("BACKUP_SUCCESS", "Ambiente: " + envNome + " | ID: " + arquivoCopia.getId());
    
    limparBackupsAntigos(pastaDestino);
    return "Backup concluído (" + envNome + "): " + nomeArquivo;

  } catch (e) {
    registrarLogSistema("BACKUP_ERROR", e.message);
    throw e;
  } finally { lock.releaseLock(); }
}

function limparBackupsAntigos(pasta) {
  try {
    var diasRetencao = CONFIG_SISTEMA.DIAS_RETENCAO_BACKUP || 30;
    var dataLimite = new Date();
    dataLimite.setDate(dataLimite.getDate() - diasRetencao);
    var arquivos = pasta.getFiles();
    while (arquivos.hasNext()) {
      var arquivo = arquivos.next();
      if (arquivo.getName().indexOf("-BKP]") > -1 && arquivo.getDateCreated() < dataLimite) {
        arquivo.setTrashed(true);
      }
    }
  } catch (e) { console.warn(e.message); }
}