/**
 * 🧪 TEST SERVICE v1.0
 * Funcionalidade: Testes de stress e performance da infraestrutura de IA.
 */

/**
 * Simula uma carga de trabalho pesada na IA para testar latência e limites.
 * Ideal para validar o plano de 12 usuários simultâneos.
 * @param {number} numChamadas Quantidade de chamadas sequenciais (Padrão: 12)
 */
function executarTesteStressIA(numChamadas) {
  var n = numChamadas || 12;
  var resultados = [];
  var erros = 0;
  var tempoTotal = 0;
  
  console.log("🚀 INICIANDO TESTE DE STRESS IA (GEMINI 2.5 FLASH)");
  console.log("Simulando " + n + " auditorias sequenciais...");

  // Payload de teste (Simulando um balancete real)
  var mockDados = {
    "ATIVO TOTAL": 1500000.50,
    "PASSIVO TOTAL": 1500000.50,
    "CAIXA": 50000.00,
    "DESPESAS": 120000.00,
    "RECEITAS": 300000.00
  };

  for (var i = 0; i < n; i++) {
    var inicio = new Date().getTime();
    try {
      // Usamos o prompt de auditoria (que é mais pesado/analítico)
      var res = gerarRelatorioComportamentalIA(mockDados, [], "AUDITORIA");
      var fim = new Date().getTime();
      var latencia = fim - inicio;
      
      resultados.push(latencia);
      tempoTotal += latencia;
      
      console.log("Iteração #" + (i + 1) + ": " + latencia + "ms | Status: OK");
      
    } catch (e) {
      erros++;
      console.error("Iteração #" + (i + 1) + " FALHOU: " + e.message);
    }
  }

  // Estatísticas Finais
  var media = resultados.length > 0 ? (tempoTotal / resultados.length).toFixed(0) : 0;
  var min = resultados.length > 0 ? Math.min.apply(Math, resultados) : 0;
  var max = resultados.length > 0 ? Math.max.apply(Math, resultados) : 0;

  var logFinal = "\n--- RELATÓRIO DE STRESS TEST ---" +
                 "\nTotal de Chamadas: " + n +
                 "\nSucessos: " + (n - erros) +
                 "\nFalhas: " + erros +
                 "\nTempo Médio: " + media + "ms" +
                 "\nTempo Mínimo: " + min + "ms" +
                 "\nTempo Máximo: " + max + "ms" +
                 "\nTempo Total : " + (tempoTotal/1000).toFixed(2) + "s";

  console.log(logFinal);
  registrarLogSistema("AI_STRESS_TEST", logFinal);
  
  return logFinal;
}
