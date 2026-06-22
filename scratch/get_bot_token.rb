bot = AgentBot.find_by(name: 'Typebot')
puts "BOT_TOKEN: #{bot.access_token.token}"
