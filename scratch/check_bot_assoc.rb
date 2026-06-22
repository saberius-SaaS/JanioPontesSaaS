bot = AgentBot.find_by(name: 'Typebot')
if bot
  puts "Bot: #{bot.name} (ID: #{bot.id})"
  puts "Outgoing URL: #{bot.outgoing_url}"
  
  assocs = AgentBotInbox.where(agent_bot_id: bot.id)
  assocs.each do |a|
    puts "  Associated with Inbox ID: #{a.inbox_id}, Status: #{a.status}"
  end
  
  if assocs.empty?
    puts "  WARNING: Bot is NOT associated with any inbox!"
  end
else
  puts "Bot 'Typebot' not found!"
  puts "All bots: #{AgentBot.all.pluck(:id, :name)}"
end
