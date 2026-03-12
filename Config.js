/**
 * ⚙️ CONFIGURAÇÕES GLOBAIS - ELITE ARCHITECT v131.06
 * Evolução: Motor de Workflows adaptado para 12 colunas e Cache v1.1.
 */

var CONFIG_SISTEMA = {
  VERSAO: "v131.06",
  URL_WEBAPP: "https://script.google.com/macros/s/AKfycbxYiLeMSoqTl-myvYIwzt2zs5jCRgpiBnpnAnJVPHZb4QVrJr4f8Pgihg9t1std2M46Tg/exec", 

  DIAS_INTERVALO_COBRANCA: 2,
  TURNOS_PARA_CHECKPOINT: 5,
  DIAS_RETENCAO_BACKUP: 30,
  JANELA_RETROATIVA_MESES: 3,

  ABA_USUARIOS: "DB_USUARIOS",
  ABA_TAREFAS: "DB_TAREFAS",
  ABA_REGRAS: "DB_REGRAS",
  ABA_SOLICITACOES: "DB_SOLICITACOES",
  ABA_CLIENTES: "DB_CLIENTES",
  ABA_HISTORICO: "DB_HISTORICO",
  ABA_PROTOCOLOS: "DB_PROTOCOLOS",
  ABA_RISCO: "DB_RISCO",
  ABA_LOGS: "DB_LOGS",
  ABA_WORKFLOWS: "DB_WORKFLOWS",
 
  STATUS: {
    ABERTA: "ABERTA",
    PENDENTE: "PENDENTE",
    ENTREGUE: "ENTREGUE"
  },

  FERIADOS: ["01/01", "21/04", "01/05", "07/09", "12/10", "02/11", "15/11", "20/11", "25/12"]
};

/**
 * Identifica o ambiente verificando se a planilha está dentro da Pasta Base de Operação ou Desenvolvimento.
 */
function getAmbiente() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ssId = ss.getId();
  
  var ID_PASTA_BASE_PROD = "19f-w65G1jROg78UUmn6zGUIpAAg6i3wX";
  var ID_PASTA_BASE_DEV  = "1BeiB4aS8zLmAJUeAP6SSHbB3LhponoSF";

  var pastaPaiId = "";
  try {
    var parents = DriveApp.getFileById(ssId).getParents();
    if (parents.hasNext()) {
      pastaPaiId = parents.next().getId();
    }
  } catch (e) {
    console.error("Erro ao identificar pasta pai: " + e.message);
  }

  if (pastaPaiId === ID_PASTA_BASE_PROD || ssId === ID_PASTA_BASE_PROD) {
    return {
      NOME: "OPERACIONAL",
      BASE: "19f-w65G1jROg78UUmn6zGUIpAAg6i3wX",
      BACKUPS: "1gFvKQhakxFtEWQTv5vzeI92wegeGfmdj",
      CLIENTES_DIGITAL: "1RfP4l6po0g46YYjdzh1EmJDkgSP8lFVo",
      ENVIADOS: "1DqR1Zg6_ASKXux80UxYJ_6FWGrV4MvYn"
    };
  } else {
    return {
      NOME: "DESENVOLVIMENTO",
      BASE: "1BeiB4aS8zLmAJUeAP6SSHbB3LhponoSF",
      BACKUPS: "13Lqx_66hL-SZWO59Ej9ifQMGWaDCaj52",
      CLIENTES_DIGITAL: "1z4jUorGF_pMJ5o0jR7jGc2QUmpD7c3l6",
      ENVIADOS: "1dRgbz_FkqWUazrjaNNwCFFi4NkLTc1N-"
    };
  }
}

/**
 * Retorna a URL do WebApp configurada para o frontend usar no fetch.
 * Permite que o frontend evite usar google.script.run em chamadas de alto privilégio.
 */
function getUrlParaFetch() {
  return CONFIG_SISTEMA.URL_WEBAPP;
}