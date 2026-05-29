import sqlite3

try:
    conn = sqlite3.connect("test.db")
    cur = conn.cursor()
    cur.execute("SELECT id, cliente, obrigacao, acao, status, responsavel, protocolo FROM tarefas ORDER BY id DESC LIMIT 5;")
    print("Tarefas:")
    for row in cur.fetchall(): print(row)
    
    cur.execute("SELECT * FROM historico_tarefas ORDER BY id DESC LIMIT 5;")
    print("\nHistorico:")
    for row in cur.fetchall(): print(row)
    
    cur.execute("SELECT id, cliente, obrigacao, acao, status_envio, protocolo, link_arquivo, email FROM protocolos ORDER BY data DESC LIMIT 5;")
    print("\nProtocolos:")
    for row in cur.fetchall(): print(row)
except Exception as e:
    print("Erro:", e)
