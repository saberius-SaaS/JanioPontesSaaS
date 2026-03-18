function readRecentLogs() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var wsLogs = ss.getSheetByName(CONFIG_SISTEMA.ABA_LOGS);
  if (!wsLogs) {
    console.log("Aba DB_LOGS não encontrada.");
    return;
  }
  var data = wsLogs.getDataRange().getValues();
  console.log("--- ÚLTIMOS 20 LOGS ---");
  var startRow = Math.max(1, data.length - 20);
  for (var i = startRow; i < data.length; i++) {
    console.log(JSON.stringify(data[i]));
  }
}
