/**
 * ⚡ CACHE & PERFORMANCE SERVICE v1.2 (Fragmentado)
 * Gerencia o armazenamento em memória para reduzir chamadas ao SpreadsheetApp.
 * Evolução: Algoritmo de fragmentação para burlar o limite de 100KB do Google.
 */

var CACHE_CONFIG = {
  EXPIRACAO: 21600, // 6 horas
  EXPIRACAO_PRIO: 600, // 10 minutos
  CHUNK_SIZE: 45000, // Margem super segura (Abaixo de 100KB)
  KEYS: {
    CLIENTES: "DATA_CLIENTES",
    REGRAS: "DATA_REGRAS",
    USUARIOS: "DATA_USUARIOS",
    VERSION: "CACHE_VERSION",
    PRIO_PREFIX: "PRIO_USER_"
  }
};

function getSheetDataCached(abaNome, cacheKey) {
  var cache = CacheService.getScriptCache();
  var props = PropertiesService.getScriptProperties();
  var version = props.getProperty(CACHE_CONFIG.KEYS.VERSION) || "0";
  var masterKey = cacheKey + "_" + version;
  
  // 1. TENTA LER O CACHE FRAGMENTADO
  var chunkCountStr = cache.get(masterKey + "_chunks");
  
  if (chunkCountStr) {
    var chunkCount = parseInt(chunkCountStr, 10);
    var fullString = "";
    var cacheValido = true;
    
    for (var i = 0; i < chunkCount; i++) {
      var chunk = cache.get(masterKey + "_" + i);
      if (chunk) {
        fullString += chunk;
      } else {
        cacheValido = false; // Faltou um pedaço, invalida o cache
        break; 
      }
    }
    
    if (cacheValido && fullString.length > 0) {
      try {
        return JSON.parse(fullString);
      } catch (e) {
        registrarLogSistema("CACHE_PARSE_ERR", abaNome);
      }
    }
  }

  // 2. SE NÃO ACHOU OU CACHE CORROMPIDO, BUSCA NA PLANILHA
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(abaNome);
  if (!sheet) return [];
  
  var data = sheet.getDataRange().getValues();
  
  // 3. GRAVA NO CACHE USANDO FRAGMENTAÇÃO
  try {
    var stringData = JSON.stringify(data);
    var totalChunks = Math.ceil(stringData.length / CACHE_CONFIG.CHUNK_SIZE);
    
    // Salva a quantidade de pedaços mestre
    cache.put(masterKey + "_chunks", totalChunks.toString(), CACHE_CONFIG.EXPIRACAO);
    
    // Salva cada fragmento independentemente
    for (var j = 0; j < totalChunks; j++) {
      var startIdx = j * CACHE_CONFIG.CHUNK_SIZE;
      var endIdx = startIdx + CACHE_CONFIG.CHUNK_SIZE;
      var chunkData = stringData.substring(startIdx, endIdx);
      
      cache.put(masterKey + "_" + j, chunkData, CACHE_CONFIG.EXPIRACAO);
    }
  } catch (e) {
    registrarLogSistema("CACHE_SET_ERR", e.message);
  }

  return data;
}

function invalidarCacheSistema() {
  var props = PropertiesService.getScriptProperties();
  var novaVersao = new Date().getTime().toString();
  props.setProperty(CACHE_CONFIG.KEYS.VERSION, novaVersao);
  registrarLogSistema("CACHE_INVALIDATED", "Versão: " + novaVersao);
}

function getPrioridadesCached(userEmail) {
  var cache = CacheService.getScriptCache();
  var props = PropertiesService.getScriptProperties();
  var version = props.getProperty(CACHE_CONFIG.KEYS.VERSION) || "0";
  var key = CACHE_CONFIG.KEYS.PRIO_PREFIX + userEmail.replace(/[^a-zA-Z0-9]/g, "") + "_" + version;
  
  var cached = cache.get(key);
  return cached ? JSON.parse(cached) : null;
}

function setPrioridadesCache(userEmail, data) {
  var cache = CacheService.getScriptCache();
  var props = PropertiesService.getScriptProperties();
  var version = props.getProperty(CACHE_CONFIG.KEYS.VERSION) || "0";
  var key = CACHE_CONFIG.KEYS.PRIO_PREFIX + userEmail.replace(/[^a-zA-Z0-9]/g, "") + "_" + version;
  
  // Como são apenas as 7 prioridades, nunca atingirá 100KB, não requer fragmentação aqui
  cache.put(key, JSON.stringify(data), CACHE_CONFIG.EXPIRACAO_PRIO);
}

function monitorarEdicaoParaCache(e) {
  var abaNome = e.source.getActiveSheet().getName();
  var abasMestres = [
    CONFIG_SISTEMA.ABA_CLIENTES, 
    CONFIG_SISTEMA.ABA_REGRAS, 
    CONFIG_SISTEMA.ABA_USUARIOS,
    CONFIG_SISTEMA.ABA_WORKFLOWS,
    CONFIG_SISTEMA.ABA_TAREFAS 
  ];
  if (abasMestres.indexOf(abaNome) > -1) {
    invalidarCacheSistema();
  }
}