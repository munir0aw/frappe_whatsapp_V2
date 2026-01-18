no_cache = 1

def get_context(context):
	"""Set context for conversation detail page."""
	import frappe
	from frappe import _
	
	# Check if user is logged in
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/whatsapp"
		raise frappe.Redirect
	
	# Get contact parameter from URL
	contact_id = frappe.form_dict.get("contact")
	
	if not contact_id:
		context.no_access = True
		context.message = "No conversation specified"
		return
	
	# Get and verify WhatsApp Contact
	try:
		contact = frappe.get_doc("WhatsApp Contact", contact_id)
		
		# Verify user has access
		if contact.portal_user != frappe.session.user or not contact.allow_portal_access:
			context.no_access = True
			context.message = "You don't have permission to view this conversation"
			return
		
		context.contact = contact
		context.has_access = True
		
	except Exception as e:
		context.no_access = True
		context.message = str(e)
