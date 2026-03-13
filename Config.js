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
  
  PASTAS: {
    NOME: "OPERACIONAL",
    BASE: "19f-w65G1jROg78UUmn6zGUIpAAg6i3wX",
    BACKUPS: "1gFvKQhakxFtEWQTv5vzeI92wegeGfmdj",
    CLIENTES_DIGITAL: "1RfP4l6po0g46YYjdzh1EmJDkgSP8lFVo",
    ENVIADOS: "1DqR1Zg6_ASKXux80UxYJ_6FWGrV4MvYn"
  },
 
  STATUS: {
    ABERTA: "ABERTA",
    PENDENTE: "PENDENTE",
    ENTREGUE: "ENTREGUE"
  },

  FERIADOS: ["01/01", "21/04", "01/05", "07/09", "12/10", "02/11", "15/11", "20/11", "25/12"]
};



/**
 * Retorna a URL do WebApp configurada para o frontend usar no fetch.
 * Permite que o frontend evite usar google.script.run em chamadas de alto privilégio.
 */
function getUrlParaFetch() {
  return CONFIG_SISTEMA.URL_WEBAPP;
}