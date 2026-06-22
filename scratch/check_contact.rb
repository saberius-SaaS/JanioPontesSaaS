contact = Contact.find_by(phone_number: '+553499721001')
if contact
  puts "Contact found: #{contact.name} (ID: #{contact.id})"
  convs = contact.conversations.where(inbox_id: 1)
  convs.each do |c|
    puts "  Conv ##{c.id} - Status: #{c.status} - Last activity: #{c.last_activity_at}"
  end
else
  puts "Contact not found"
end
