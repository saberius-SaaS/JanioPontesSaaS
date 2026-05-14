/**
 * ⚙️ CONFIGURAÇÕES GLOBAIS - ELITE ARCHITECT v131.06
 * Evolução: Motor de Workflows adaptado para 12 colunas e Cache v1.1.
 */

var CONFIG_SISTEMA = {
  ID_PLANILHA: "1gey_Q16UVbihSRSLFvD6a7JZtwFaYzLXtTwVKySEijw",
  VERSAO: "v131.12",
  // 🌐 URLs E CONEXÕES
  URL_WEBAPP: "https://script.google.com/macros/s/AKfycby828QsUFLVmtQ1WegcdkaNVMtW4s3xQvhRFcrK0hEiw62xwE-Cqq3SwHMEw5521Euelw/exec",

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
  ABA_CONFIG_IA: "DB_CONFIG_IA",

  PASTAS: {
    NOME: "OPERACIONAL",
    BASE: "19f-w65G1jROg78UUmn6zGUIpAAg6i3wX",
    BACKUPS: "1gFvKQhakxFtEWQTv5vzeI92wegeGfmdj",
    CLIENTES_DIGITAL: "1RfP4l6po0g46YYjdzh1EmJDkgSP8lFVo",
    ENVIADOS: "1DqR1Zg6_ASKXux80UxYJ_6FWGrV4MvYn"
  },

  STATUS: {
    PENDENTE: "PENDENTE",
    ENTREGUE: "ENTREGUE",
    REVISAO: "REVISAO",
    REPROVADO: "REPROVADO"
  },

  ACOES: {
    ENVIAR: "ENVIAR",
    ARQUIVAR: "ARQUIVAR",
    AUDITAR: "AUDITAR",
    COMUNICAR: "COMUNICAR"
  },

  DEPARTAMENTOS: {
    CONTABIL: "CONTABIL",
    FISCAL: "FISCAL",
    PESSOAL: "PESSOAL",
    SOCIETARIO: "SOCIETARIO"
  },

  EMAILS: {
    ADMIN_AUDITORIA: "contabil@janiopontes.com.br", // Email padrão para alertas de auditoria
    REMETENTE: "sac@janiopontes.com.br"             // Alias de envio (Gmail → Contas e Importação)
  },

  FERIADOS: ["01/01", "21/04", "01/05", "15/08", "07/09", "12/10", "02/11", "15/11", "20/11", "25/12"],

  // 📱 WHATSAPP — MÓDULO DORMANT (BSP: Maxbot)
  // Preencha os dados do Maxbot (Configuração > API Maxbot) antes de instalar o gatilho.
  WHATSAPP: {
    ATIVO: true,                                                           // Chave-mestra: false = módulo 100% inerte
    API_TOKEN: "W1I2W4A1B0U3T5O3J4E2B7E7Y9A6Y1I71770330388",               // Token do Maxbot (Configuração > API Maxbot)
    CHANNEL_TOKEN: "20260198DDC3338A09-45ABA6-463B1A",                      // Token do canal WhatsApp (obtido via diagnosticoMaxbot)
    TEMPLATE_ID: 52950,                                                    // ID numérico do template "DOCUMENTO PRONTO"
    TEMPLATE_NAME: "DOCUMENTO PRONTO",                                     // Nome do template (apenas referência)
    TEMPLATE_LANG: "pt_BR",                                                // Idioma do template
    DIAS_INTERVALO_RENOTIFICACAO: 2,                                       // Mínimo de dias entre notificações do mesmo protocolo
    MAX_ENVIOS_POR_CICLO: 30,                                              // Limite de mensagens por execução (controle de custo)
    COL_NOTIF_WPP: 13                                                      // Coluna M da DB_PROTOCOLOS (rastreio de envio)
  }
};



/**
 * Retorna a URL do WebApp configurada para o frontend usar no fetch.
 * Permite que o frontend evite usar google.script.run em chamadas de alto privilégio.
 */
function getUrlParaFetch() {
  return ScriptApp.getService().getUrl();
}