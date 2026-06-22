conv = Conversation.find(14)
conv.update!(status: 'resolved')
puts "Conv #14 resolvida com sucesso! Status: #{conv.status}"
