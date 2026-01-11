# Copyright (c) 2026, Shridhar Patil and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WhatsAppAgentTool(Document):
	def validate(self):
		# Validate tool_name is valid identifier
		if not self.tool_name.replace("_", "").isalnum():
			frappe.throw("Tool name must be alphanumeric (underscores allowed)")
	
	def on_update(self):
		# Clear cache when tool is updated
		frappe.cache().delete_value(f"agent_tool_{self.tool_name}")
