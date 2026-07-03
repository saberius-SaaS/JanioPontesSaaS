# Implementação: Roteamento de Email por Tarefa (Override)

## 1. Banco de Dados
- [ ] Editar `app/models/cliente.py` e adicionar:
      `regras_roteamento = Column(Text, nullable=True, comment="JSON: {'Obrigacao': 'email@destino.com'}")`
- [ ] Gerar nova revisão Alembic: `alembic revision --autogenerate -m "Add regras_roteamento to clientes"`
- [ ] Aplicar migração (local e em produção via script posterior).

## 2. Backend (Lógica de Disparo)
- [ ] Localizar a função de disparo de email (provavelmente em `app/routers/tarefa.py` ao concluir tarefa, ou `app/routers/protocolo.py`, ou `app/core/services.py`).
- [ ] Atualizar o fallback de seleção de email:
      ```python
      email_destino = None
      # 1. Verifica regra customizada
      if cliente.regras_roteamento:
          regras = json.loads(cliente.regras_roteamento)
          if tarefa.obrigacao in regras:
              email_destino = regras[tarefa.obrigacao]
      
      # 2. Fallback normal se não encontrou regra customizada
      if not email_destino:
          email_destino = email_departamental or cliente.email
      ```

## 3. Frontend / UI
- [ ] Em `app/routers/cliente.py` e nos templates de edição, expor o campo `regras_roteamento` para edição como texto livre (JSON formatado) na aba de configurações.

## 4. Testes
- [ ] Testar fluxo: criar regra para DP e confirmar se ao finalizar a tarefa, o sistema pega o email customizado.
