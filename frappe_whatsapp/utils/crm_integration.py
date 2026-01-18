import frappe

def link_whatsapp_contact_to_lead(doc, method):
	"""
	Auto-link WhatsApp Contact to CRM Lead based on mobile number
	Triggered on 'validate' of CRM Lead
	"""
	if not doc.mobile_no:
		return

	# If already linked, skip
	if doc.whatsapp_contact:
		return

	# Clean phone number (basic) - remove spaces and hyphens
	phone = doc.mobile_no.replace(" ", "").replace("-", "")
	
	# Try to find matching WhatsApp Contact
	# 1. Exact match
	contact = frappe.db.get_value("WhatsApp Contact", {"mobile_no": phone}, "name")
	
	# 2. Try with/without + prefix if not found
	if not contact:
		if phone.startswith("+"):
			contact = frappe.db.get_value("WhatsApp Contact", {"mobile_no": phone[1:]}, "name")
		else:
			contact = frappe.db.get_value("WhatsApp Contact", {"mobile_no": "+" + phone}, "name")

	if contact:
		doc.whatsapp_contact = contact
		# Optional: Add a comment or log? No need to spam.
