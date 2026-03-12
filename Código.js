/**
 * 🛡️ SISTEMA DE GESTÃO CONTÁBIL | ELITE ARCHITECT
 * 🔧 STATUS: UNIFICADO v130.04 (Cache Performance)
 */

/**
 * Gatilho de Edição para Invalidação de Cache
 */
function onEdit(e) {
  if (!e) return;
  monitorarEdicaoParaCache(e);
}

/**
 * Reparar Layout de todas as abas conforme padrão Elite
 */
function padronizarLayout() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var abas = Object.values(CONFIG_SISTEMA).filter(v => typeof v === "string" && v.startsWith("DB_"));
  
  abas.forEach(function(n) {
    var s = ss.getSheetByName(n); if (!s) return;
    var lc = s.getLastColumn(), lr = s.getLastRow();
    
    s.getRange(1, 1, s.getMaxRows() || 100, s.getMaxColumns() || 20).setBackground("#ffffff").setFontColor("#1e293b").setFontFamily("Inter").setFontSize(10);
    
    if (lc > 0) {
      s.getRange(1, 1, 1, lc).setBackground("#1C3051").setFontColor("white").setFontWeight("bold").setHorizontalAlignment("center").setVerticalAlignment("middle");
      s.setFrozenRows(1);
      s.autoResizeColumns(1, lc);
      if(lr > 1) {
        for (var i = 2; i <= lr; i++) {
          s.getRange(i, 1, 1, lc).setBackground(i % 2 === 0 ? "#F8FAFC" : "#FFFFFF");
        }
      }
    }
  });
}