"""
API endpoints for n8n AI Agent integration.
Provides tools for the AI Agent to interact with WhatsApp and CRM.
"""
import frappe
import json
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
def escalate_to_human(mobile_no, reason=None, pause_hours=24):
	"""
	Escalate the conversation to a human agent.
	Pauses the bot for specified hours (default 24).
	"""
	if not mobile_no:
		frappe.throw(_("Mobile number is required"))
		
	contact_name = frappe.db.get_value("WhatsApp Contact", {"mobile_no": mobile_no}, "name")
	if not contact_name:
		frappe.throw(_("WhatsApp Contact not found"))
		
	# Pause bot
	paused_until = add_to_date(now_datetime(), hours=int(pause_hours))
	
	frappe.db.set_value("WhatsApp Contact", contact_name, {
		"bot_paused_until": paused_until,
		"notes": f"Escalated by AI Agent. Reason: {reason}" if reason else "Escalated by AI Agent"
	})
	
	# Notify assigned user (if any) or create a Todo
	contact = frappe.get_doc("WhatsApp Contact", contact_name)
	if contact.email:
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
		"pause_hours": pause_hours
	}



@frappe.whitelist()
def call_tool(tool_name, **kwargs):
	"""
	Generic endpoint to call custom tools defined in WhatsApp Agent Tool DocType.
	URL: /api/method/frappe_whatsapp.frappe_whatsapp.api.agent.call_tool
	
	Example:
	POST /api/method/frappe_whatsapp.frappe_whatsapp.api.agent.call_tool
	{
		"tool_name": "get_product_price",
		"product_id": "PROD-001"
	}
	"""
	# Get tool definition from cache or database
	cache_key = f"agent_tool_{tool_name}"
	tool = frappe.cache().get_value(cache_key)
	
	if not tool:
		tool = frappe.get_doc("WhatsApp Agent Tool", tool_name)
		if not tool:
			frappe.throw(_(f"Tool '{tool_name}' not found"))
		frappe.cache().set_value(cache_key, tool.as_dict(), expires_in_sec=300)
	
	# Check if tool is enabled
	if not tool.get("enabled"):
		frappe.throw(_(f"Tool '{tool_name}' is disabled"))
	
	# Validate parameters
	params = {}
	for param in tool.get("parameters", []):
		param_name = param.get("parameter_name")
		param_value = kwargs.get(param_name)
		
		# Check required parameters
		if param.get("required") and (param_value is None or param_value == ""):
			frappe.throw(_(f"Parameter '{param_name}' is required"))
		
		# Use default if not provided
		if param_value is None and param.get("default_value"):
			param_value = param.get("default_value")
		
		# Type conversion
		param_type = param.get("parameter_type", "string")
		if param_value is not None:
			try:
				if param_type == "number":
					param_value = float(param_value)
				elif param_type == "boolean":
					param_value = bool(param_value)
				elif param_type == "dict" and isinstance(param_value, str):
					param_value = json.loads(param_value)
				elif param_type == "list" and isinstance(param_value, str):
					param_value = json.loads(param_value)
			except Exception as e:
				frappe.throw(_(f"Invalid type for parameter '{param_name}': {str(e)}"))
		
		params[param_name] = param_value
	
	# Execute the tool code
	try:
		# Create safe execution context
		context = {
			"frappe": frappe,
			"json": json,
			"params": params,
			"_": _,
			"result": None
		}
		
		# Execute the Python code
		exec(tool.get("python_code"), context)
		
		# Get result
		result = context.get("result")
		
		# Return based on return_type
		return_type = tool.get("return_type", "dict")
		if return_type == "dict" and not isinstance(result, dict):
			return {"result": result}
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Error executing tool '{tool_name}': {str(e)}")
		frappe.throw(_(f"Error executing tool: {str(e)}"))


@frappe.whitelist()
def list_tools():
	"""List all enabled tools available for n8n."""
	tools = frappe.get_all(
		"WhatsApp Agent Tool",
		filters={"enabled": 1},
		fields=["tool_name", "description", "parameters"]
	)
	
	result = []
	for tool in tools:
		params = frappe.get_all(
			"WhatsApp Agent Tool Parameter",
			filters={"parent": tool.tool_name},
			fields=["parameter_name", "parameter_type", "required", "description"]
		)
		tool["parameters"] = params
		result.append(tool)
	
	return result
