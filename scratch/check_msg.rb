last_msg = Inbox.find(1).messages.last
puts "Last message id: #{last_msg.id}"
puts "Content: #{last_msg.content}"
puts "Created at: #{last_msg.created_at}"
puts "Sender: #{last_msg.sender.name if last_msg.sender}"
puts "Conversation ID: #{last_msg.conversation_id}"
