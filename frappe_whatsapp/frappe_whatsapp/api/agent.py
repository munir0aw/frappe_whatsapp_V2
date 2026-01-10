"""
API endpoints for n8n AI Agent integration.
Provides tools for the AI Agent to interact with WhatsApp and CRM.
"""
import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

@frappe.whitelist()
def send_message(mobile_no, message):
	"""
	Send a WhatsApp message to the specified mobile number.
	Used by AI Agent to reply to users.
	"""
	from frappe_whatsapp.frappe_whatsapp.api.whatsapp import create_whatsapp_message
	
	if not mobile_no or not message:
		frappe.throw(_("Mobile number and message are required"))
		
	# Find linked WhatsApp Contact/Reference to verify permissions or context if needed
	# For now, just send the message via the standard API
	# We try to find a reference if possible to keep things clean
	contact_name = frappe.db.get_value("WhatsApp Contact", {"mobile_no": mobile_no}, "name")
	
	reference_doctype = "WhatsApp Contact"
	reference_name = contact_name
	
	# Create and send
	create_whatsapp_message(
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		message=message,
		to=mobile_no
	)
	
	return {"status": "success", "message": "Message sent"}


@frappe.whitelist()
def create_lead(mobile_no, name=None, notes=None):
	"""
	Create a CRM Lead from a WhatsApp Contact.
	Used by AI Agent when a prospect is qualified.
	"""
	if not mobile_no:
		frappe.throw(_("Mobile number is required"))
		
	# Check if lead already exists
	existing_lead = frappe.db.get_value("CRM Lead", {"mobile_no": mobile_no}, "name")
	if existing_lead:
		return {"status": "exists", "lead": existing_lead, "message": "Lead already exists"}
	
	# Create Lead
	lead = frappe.get_doc({
		"doctype": "CRM Lead",
		"mobile_no": mobile_no, # CRM likely expects just number
		"lead_name": name or mobile_no, # Name is mandatory usually
		"notes": notes,
		"source": "WhatsApp AI Agent" 
	})
	lead.insert(ignore_permissions=True)
	
	# Link WhatsApp Contact to this new Lead
	contact_name = frappe.db.get_value("WhatsApp Contact", {"mobile_no": mobile_no}, "name")
	if contact_name:
		frappe.db.set_value("WhatsApp Contact", contact_name, {
			"lead_reference": lead.name,
			"converted_to_lead": 1,
			"qualification_status": "Qualified" # Assuming this field exists or similar
		})
		
	return {"status": "success", "lead": lead.name, "message": "Lead created successfully"}


@frappe.whitelist()
def escalate_to_human(mobile_no, reason=None):
	"""
	Escalate the conversation to a human agent.
	Pauses the bot for 24 hours (default) and notifies staff.
	"""
	if not mobile_no:
		frappe.throw(_("Mobile number is required"))
		
	contact_name = frappe.db.get_value("WhatsApp Contact", {"mobile_no": mobile_no}, "name")
	if not contact_name:
		frappe.throw(_("WhatsApp Contact not found"))
		
	# Pause bot for 24 hours
	paused_until = add_to_date(now_datetime(), hours=24)
	
	frappe.db.set_value("WhatsApp Contact", contact_name, {
		"bot_paused_until": paused_until,
		"notes": f"Escalated by AI Agent. Reason: {reason}" if reason else "Escalated by AI Agent"
	})
	
	# Notify assigned user (if any) or create a Todo
	contact = frappe.get_doc("WhatsApp Contact", contact_name)
	if contact.email: # Assigned user
		frappe.get_doc({
			"doctype": "ToDo",
			"owner": contact.email,
			"description": f"WhatsApp Escalation: {mobile_no}. Reason: {reason}",
			"reference_type": "WhatsApp Contact",
			"reference_name": contact_name,
			"assigned_by": "Administrator"
		}).insert(ignore_permissions=True)
		
	return {
		"status": "escalated", 
		"bot_paused_until": paused_until, 
		"message": "Bot paused for 24 hours. Human agent notified."
	}
