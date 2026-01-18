no_cache = 1

def get_context(context):
	"""Set context for WhatsApp portal page."""
	import frappe
	
	# Check if user is logged in
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/whatsapp"
		raise frappe.Redirect
	
	# Get user's WhatsApp contact
	contact = frappe.db.get_value(
		"WhatsApp Contact",
		{
			"portal_user": frappe.session.user,
			"allow_portal_access": 1
		},
		["name", "contact_name", "mobile_no"],
		as_dict=True
	)
	
	if not contact:
		context.no_access = True
		context.message = "You don't have access to WhatsApp Portal. Please contact your administrator."
	else:
		context.contact = contact
		context.has_access = True
