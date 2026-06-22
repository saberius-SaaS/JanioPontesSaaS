inbox = Inbox.find(1)
inbox.update!(enable_auto_assignment: false)
puts "Auto-assignment DESATIVADO na caixa de entrada: #{inbox.name}"
