"""
Permission helpers for WhatsApp Portal.
"""
import frappe


def has_permission(doc, ptype, user):
	"""Custom permission check for portal users.
	
	Ensures portal users can only access their own WhatsApp data.
	"""
	if not user or user == "Guest":
		return False
	
	# System Manager has full access
	if "System Manager" in frappe.get_roles(user):
		return True
	
	doctype = doc.doctype if hasattr(doc, 'doctype') else doc.get('doctype')
	
	# WhatsApp Contact permission
	if doctype == "WhatsApp Contact":
		portal_user = doc.portal_user if hasattr(doc, 'portal_user') else doc.get('portal_user')
		allow_access = doc.allow_portal_access if hasattr(doc, 'allow_portal_access') else doc.get('allow_portal_access')
		
		return portal_user == user and allow_access
	
	# WhatsApp Message permission
	if doctype == "WhatsApp Message":
		# Get user's WhatsApp contacts
		user_contacts = frappe.get_all(
			"WhatsApp Contact",
			filters={
				"portal_user": user,
				"allow_portal_access": 1
			},
			fields=["mobile_no"]
		)
		
		if not user_contacts:
			return False
		
		# Get phone number variants
		phone_variants = []
		for contact in user_contacts:
			phone_variants.append(contact.mobile_no)
			if contact.mobile_no.startswith('+'):
				phone_variants.append(contact.mobile_no[1:])
			else:
				phone_variants.append('+' + contact.mobile_no)
		
		# Check if message belongs to user's contacts
		msg_from = doc.get('from') if hasattr(doc, 'get') else getattr(doc, 'from', None)
		msg_to = doc.to if hasattr(doc, 'to') else doc.get('to')
		
		return msg_from in phone_variants or msg_to in phone_variants
	
	return False


def get_user_whatsapp_contact(user=None):
	"""Get WhatsApp Contact for a user.
	
	Args:
		user: User email, defaults to current user
		
	Returns:
		WhatsApp Contact name or None
	"""
	if not user:
		user = frappe.session.user
	
	if user == "Guest":
		return None
	
	contact = frappe.db.get_value(
		"WhatsApp Contact",
		{
			"portal_user": user,
			"allow_portal_access": 1
		},
		"name"
	)
	
	return contact
