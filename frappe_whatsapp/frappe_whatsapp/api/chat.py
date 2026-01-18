"""
WhatsApp Chat API
Backend API for the WhatsApp chat interface
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_contacts():
	"""Get all WhatsApp contacts with last message preview."""
	
	contacts = frappe.db.sql("""
		SELECT 
			wc.name,
			wc.mobile_no,
			wc.contact_name,
			wc.last_message,
			wc.last_message_date,
			wc.unread_count,
			wc.qualification_status,
			wc.converted_to_lead,
			wc.lead_reference
		FROM `tabWhatsApp Contact` wc
		ORDER BY wc.last_message_date DESC
	""", as_dict=True)
	
	return contacts


@frappe.whitelist()
def get_messages(contact_id):
	"""Get all messages for a specific contact."""
	
	# Verify contact exists
	if not frappe.db.exists("WhatsApp Contact", contact_id):
		frappe.throw(_("Contact not found"))
	
	messages = frappe.db.sql("""
		SELECT 
			name,
			type,
			message,
			message_type,
			content_type,
			attach,
			creation,
			status
		FROM `tabWhatsApp Message`
		WHERE whatsapp_contact = %s
		ORDER BY creation ASC
	""", contact_id, as_dict=True)
	
	return messages


@frappe.whitelist()
def send_message(contact_id, message=None, file_url=None):
	"""Send a WhatsApp message to a contact."""
	
	# Get contact
	contact = frappe.get_doc("WhatsApp Contact", contact_id)
	
	# Determine content type
	content_type = "text"
	if file_url:
		# Detect file type from extension
		if any(file_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
			content_type = "image"
		elif any(file_url.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov']):
			content_type = "video"
		elif any(file_url.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
			content_type = "document"
		else:
			content_type = "document"
	
	# Create WhatsApp Message
	whatsapp_msg = frappe.get_doc({
		"doctype": "WhatsApp Message",
		"type": "Outgoing",
		"to": contact.mobile_no,
		"message": message or "",
		"content_type": content_type,
		"attach": file_url,
		"whatsapp_contact": contact_id,
		"whatsapp_account": contact.whatsapp_account
	})
	
	whatsapp_msg.insert(ignore_permissions=True)
	
	# Try to send via WhatsApp API
	try:
		from frappe_whatsapp.utils import send_whatsapp_message
		send_whatsapp_message(
			to=contact.mobile_no,
			message=message,
			media_url=file_url,
			account=contact.whatsapp_account
		)
		
		whatsapp_msg.status = "Sent"
		whatsapp_msg.save(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Failed to send WhatsApp message: {str(e)}")
		whatsapp_msg.status = "Failed"
		whatsapp_msg.save(ignore_permissions=True)
		frappe.throw(_("Failed to send message: {0}").format(str(e)))
	
	# Emit realtime event
	frappe.publish_realtime('whatsapp_message', {
		'contact': contact_id,
		'message': whatsapp_msg.name
	})
	
	return {
		"success": True,
		"message": whatsapp_msg.name
	}


@frappe.whitelist()
def mark_as_read(contact_id):
	"""Mark all messages from a contact as read."""
	
	contact = frappe.get_doc("WhatsApp Contact", contact_id)
	contact.unread_count = 0
	contact.is_read = 1
	contact.save(ignore_permissions=True)
	
	return {"success": True}


@frappe.whitelist()
def search_contacts(query):
	"""Search contacts by name or mobile number."""
	
	contacts = frappe.db.sql("""
		SELECT 
			name,
			mobile_no,
			contact_name,
			last_message,
			last_message_date,
			unread_count
		FROM `tabWhatsApp Contact`
		WHERE contact_name LIKE %s 
			OR mobile_no LIKE %s
		ORDER BY last_message_date DESC
		LIMIT 50
	""", (f"%{query}%", f"%{query}%"), as_dict=True)
	
	return contacts
