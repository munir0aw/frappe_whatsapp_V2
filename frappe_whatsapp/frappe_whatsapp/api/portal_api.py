"""
Portal API endpoints for WhatsApp customer portal.
Provides API methods for portal users to access their conversations,
search messages, view media, and create leads.
"""
import frappe
from frappe import _


@frappe.whitelist()
def get_my_conversations():
	"""Get all WhatsApp conversations for the logged-in portal user.
	
	Returns:
		List of WhatsApp Contacts with conversation data
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to view conversations"), frappe.PermissionError)
	
	# Get WhatsApp Contact linked to this user
	contacts = frappe.get_all(
		"WhatsApp Contact",
		filters={
			"portal_user": user,
			"allow_portal_access": 1
		},
		fields=[
			"name",
			"mobile_no",
			"contact_name",
			"last_message",
			"last_message_date",
			"unread_count",
			"is_read",
			"total_messages",
			"qualification_status",
			"converted_to_lead",
			"lead_reference",
			"whatsapp_account"
		],
		order_by="last_message_date desc"
	)
	
	return contacts


@frappe.whitelist()
def get_conversation_messages(contact_id):
	"""Get all messages for a specific conversation.
	
	Args:
		contact_id: WhatsApp Contact name (mobile number)
		
	Returns:
		List of WhatsApp Messages
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to view messages"), frappe.PermissionError)
	
	# Verify user has access to this contact
	contact = frappe.get_doc("WhatsApp Contact", contact_id)
	if contact.portal_user != user or not contact.allow_portal_access:
		frappe.throw(_("You don't have permission to view this conversation"), frappe.PermissionError)
	
	# Get messages for this contact's mobile number
	mobile_no = contact.mobile_no
	
	# Get all phone number variants (with/without +)
	phone_variants = [mobile_no]
	if mobile_no.startswith('+'):
		phone_variants.append(mobile_no[1:])
	else:
		phone_variants.append('+' + mobile_no)
	
	# Query messages
	messages = frappe.get_all(
		"WhatsApp Message",
		filters=[
			["type", "in", ["Incoming", "Outgoing"]],
			["or", [
				["to", "in", phone_variants],
				["from", "in", phone_variants]
			]]
		],
		fields=[
			"name",
			"creation",
			"type",
			"from as sender",
			"to as receiver",
			"message",
			"attach",
			"content_type",
			"status",
			"message_id",
			"is_starred",
			"profile_name"
		],
		order_by="creation asc"
	)
	
	return messages


@frappe.whitelist()
def search_messages(query):
	"""Search through all messages for the logged-in user.
	
	Args:
		query: Search term
		
	Returns:
		List of matching WhatsApp Messages with context
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to search messages"), frappe.PermissionError)
	
	# Get user's contacts
	contacts = frappe.get_all(
		"WhatsApp Contact",
		filters={
			"portal_user": user,
			"allow_portal_access": 1
		},
		fields=["mobile_no"]
	)
	
	if not contacts:
		return []
	
	# Get all phone number variants
	phone_variants = []
	for contact in contacts:
		phone_variants.append(contact.mobile_no)
		if contact.mobile_no.startswith('+'):
			phone_variants.append(contact.mobile_no[1:])
		else:
			phone_variants.append('+' + contact.mobile_no)
	
	# Search messages
	messages = frappe.db.sql("""
		SELECT 
			name,
			creation,
			type,
			`from` as sender,
			`to` as receiver,
			message,
			attach,
			content_type,
			is_starred,
			whatsapp_contact
		FROM `tabWhatsApp Message`
		WHERE (
			(`to` IN %(phones)s OR `from` IN %(phones)s)
			AND (
				message LIKE %(query)s
				OR label LIKE %(query)s
			)
		)
		ORDER BY creation DESC
		LIMIT 50
	""", {
		"phones": phone_variants,
		"query": f"%{query}%"
	}, as_dict=True)
	
	return messages


@frappe.whitelist()
def get_media_gallery(media_type=None):
	"""Get all media files from conversations.
	
	Args:
		media_type: Optional filter (image, video, document, audio)
		
	Returns:
		List of WhatsApp Messages with media attachments
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to view media"), frappe.PermissionError)
	
	# Get user's contacts
	contacts = frappe.get_all(
		"WhatsApp Contact",
		filters={
			"portal_user": user,
			"allow_portal_access": 1
		},
		fields=["mobile_no"]
	)
	
	if not contacts:
		return []
	
	# Get all phone number variants
	phone_variants = []
	for contact in contacts:
		phone_variants.append(contact.mobile_no)
		if contact.mobile_no.startswith('+'):
			phone_variants.append(contact.mobile_no[1:])
		else:
			phone_variants.append('+' + contact.mobile_no)
	
	# Build filters
	filters = [
		["or", [
			["to", "in", phone_variants],
			["from", "in", phone_variants]
		]],
		["attach", "is", "set"],
		["content_type", "in", ["image", "video", "document", "audio"]]
	]
	
	if media_type:
		filters.append(["content_type", "=", media_type])
	
	# Query media messages
	messages = frappe.get_all(
		"WhatsApp Message",
		filters=filters,
		fields=[
			"name",
			"creation",
			"type",
			"attach",
			"content_type",
			"message",
			"whatsapp_contact"
		],
		order_by="creation desc",
		limit=100
	)
	
	return messages


@frappe.whitelist()
def get_starred_messages():
	"""Get all starred messages for the logged-in user.
	
	Returns:
		List of starred WhatsApp Messages
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to view starred messages"), frappe.PermissionError)
	
	# Get user's contacts
	contacts = frappe.get_all(
		"WhatsApp Contact",
		filters={
			"portal_user": user,
			"allow_portal_access": 1
		},
		fields=["mobile_no"]
	)
	
	if not contacts:
		return []
	
	# Get all phone number variants
	phone_variants = []
	for contact in contacts:
		phone_variants.append(contact.mobile_no)
		if contact.mobile_no.startswith('+'):
			phone_variants.append(contact.mobile_no[1:])
		else:
			phone_variants.append('+' + contact.mobile_no)
	
	# Query starred messages
	messages = frappe.get_all(
		"WhatsApp Message",
		filters=[
			["or", [
				["to", "in", phone_variants],
				["from", "in", phone_variants]
			]],
			["is_starred", "=", 1]
		],
		fields=[
			"name",
			"creation",
			"type",
			"from as sender",
			"to as receiver",
			"message",
			"attach",
			"content_type",
			"whatsapp_contact"
		],
		order_by="creation desc"
	)
	
	return messages


@frappe.whitelist()
def toggle_star_message(message_id):
	"""Toggle star status of a message.
	
	Args:
		message_id: WhatsApp Message name
		
	Returns:
		New star status (0 or 1)
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)
	
	# Get message
	message = frappe.get_doc("WhatsApp Message", message_id)
	
	# Verify user has access (check if phone number belongs to user's contacts)
	phone_to_check = message.get("from") if message.type == "Incoming" else message.to
	
	contact_exists = frappe.db.exists(
		"WhatsApp Contact",
		{
			"mobile_no": ["in", [phone_to_check, phone_to_check.lstrip('+'), '+' + phone_to_check]],
			"portal_user": user,
			"allow_portal_access": 1
		}
	)
	
	if not contact_exists:
		frappe.throw(_("You don't have permission to star this message"), frappe.PermissionError)
	
	# Toggle star
	new_status = 0 if message.is_starred else 1
	message.is_starred = new_status
	message.save(ignore_permissions=True)
	
	return {"starred": new_status}


@frappe.whitelist()
def create_lead_from_portal(contact_id, first_name=None, email=None, company=None, notes=None):
	"""Create a CRM Lead from WhatsApp Contact in the portal.
	
	Args:
		contact_id: WhatsApp Contact ID
		first_name: Optional first name override
		email: Optional email
		company: Optional company name
		notes: Optional additional notes
		
	Returns:
		Created Lead name
	"""
	user = frappe.session.user
	
	if user == "Guest":
		frappe.throw(_("Please log in to create a lead"), frappe.PermissionError)
	
	# Get and verify contact
	contact = frappe.get_doc("WhatsApp Contact", contact_id)
	
	# Verify user has access
	if contact.portal_user != user or not contact.allow_portal_access:
		frappe.throw(_("You don't have permission to create a lead from this contact"), frappe.PermissionError)
	
	# Check if already converted
	if contact.converted_to_lead and contact.lead_reference:
		frappe.throw(_("This contact has already been converted to a lead: {0}").format(contact.lead_reference))
	
	# Create CRM Lead
	lead = frappe.get_doc({
		"doctype": "CRM Lead",
		"first_name": first_name or contact.contact_name or contact.mobile_no,
		"mobile_no": contact.mobile_no,
		"email": email,
		"organization": company,
		"source": "WhatsApp Portal",
		"notes": notes or contact.conversation_summary or "",
		"custom_whatsapp_contact": contact.name
	})
	lead.insert(ignore_permissions=True)
	
	# Update WhatsApp Contact
	contact.converted_to_lead = 1
	contact.lead_reference = lead.name
	contact.converted_date = frappe.utils.now()
	contact.converted_by = user
	contact.qualification_status = "Converted"
	contact.save(ignore_permissions=True)
	
	return {
		"lead_name": lead.name,
		"message": _("Lead created successfully!")
	}


@frappe.whitelist()
def get_user_whatsapp_contact():
	"""Get WhatsApp Contact for logged-in user.
	
	Returns:
		WhatsApp Contact details or None
	"""
	user = frappe.session.user
	
	if user == "Guest":
		return None
	
	contact = frappe.db.get_value(
		"WhatsApp Contact",
		{
			"portal_user": user,
			"allow_portal_access": 1
		},
		["name", "mobile_no", "contact_name", "converted_to_lead", "lead_reference"],
		as_dict=True
	)
	
	return contact
