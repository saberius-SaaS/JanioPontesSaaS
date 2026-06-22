conv = Conversation.last
puts "Last conv ID: #{conv.id}, Status: #{conv.status}, Assignee: #{conv.assignee_id}, Team: #{conv.team_id}"
puts "Auto-assignment on Inbox 1: enable_auto_assignment=#{Inbox.find(1).enable_auto_assignment}"
