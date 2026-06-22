# Verifica o status da ultima conversa e o comportamento do bot
conv = Conversation.where(inbox_id: 1).order(created_at: :desc).first
puts "Last conv: ID=#{conv.id}, Status=#{conv.status}, Created=#{conv.created_at}"

# Verifica se o AgentBot esta disparando webhook para incoming messages
# O Chatwoot so dispara webhook do AgentBot quando conversation status = 'pending'
# Vamos verificar se a conversa nasce como 'pending' ou 'open'

# Verifica agent_bot_inbox
abi = AgentBotInbox.where(inbox_id: 1).first
puts "AgentBotInbox: bot_id=#{abi.agent_bot_id}, status=#{abi.status}"

# Verifica se existem webhooks globais que podem estar interferindo
webhooks = Webhook.all
puts "Global webhooks: #{webhooks.count}"
webhooks.each do |w|
  puts "  Webhook: #{w.url} - events: #{w.subscriptions}"
end

# Verifica as ultimas 3 conversas
Conversation.where(inbox_id: 1).order(created_at: :desc).limit(3).each do |c|
  msgs = c.messages.where(message_type: 0).count
  puts "Conv ##{c.id}: status=#{c.status}, incoming_msgs=#{msgs}, assignee=#{c.assignee_id}, team=#{c.team_id}"
end
