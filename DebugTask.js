function checkTaskData() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ws = ss.getSheetByName(CONFIG_SISTEMA.ABA_TAREFAS);
  var data = ws.getDataRange().getValues();
  
  console.log("--- DB_TAREFAS CONTENT ---");
  for (var i = 0; i < Math.min(data.length, 10); i++) {
     console.log("Row " + (i+1) + ": " + JSON.stringify(data[i]));
  }
  
  var cache = CacheService.getScriptCache();
  var cachedData = cache.get("DATA_TAREFAS");
  console.log("--- CACHE STATUS ---");
  if (cachedData) {
     console.log("Cache exists (length: " + cachedData.length + ")");
     // We can't easily parse it if it's compressed/split, but we can check if it exists
  } else {
     console.log("Cache is EMPTY");
  }
}
