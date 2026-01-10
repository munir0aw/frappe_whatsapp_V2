# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import re


class WhatsAppContact(Document):
	def autoname(self):
		"""Set name from mobile_no."""
		self.name = self.mobile_no
	
	def validate(self):
		"""Validate and extract country code."""
		if self.mobile_no:
			# Extract country code (assuming format like +966501234567 or 966501234567)
			match = re.match(r'^\+?(\d{1,4})', self.mobile_no)
			if match and not self.country_code:
				self.country_code = match.group(1)
	
	def before_save(self):
		"""Update conversion tracking."""
		if self.converted_to_lead and not self.converted_date:
			self.converted_date = frappe.utils.now()
			self.converted_by = frappe.session.user
			self.qualification_status = "Converted"
	
	@frappe.whitelist()
	def convert_to_lead(self):
		"""Convert WhatsApp Contact to CRM Lead."""
		if self.converted_to_lead and self.lead_reference:
			frappe.throw("This contact has already been converted to a lead.")
		
		# Create CRM Lead
		lead = frappe.get_doc({
			"doctype": "CRM Lead",
			"first_name": self.contact_name or self.mobile_no,
			"mobile_no": self.mobile_no,
			"source": self.source,
			"notes": self.conversation_summary or "",
			"custom_whatsapp_contact": self.name
		})
		lead.insert(ignore_permissions=True)
		
		# Update WhatsApp Contact
		self.converted_to_lead = 1
		self.lead_reference = lead.name
		self.converted_date = frappe.utils.now()
		self.converted_by = frappe.session.user
		self.qualification_status = "Converted"
		self.save(ignore_permissions=True)
		
		frappe.msgprint(f"Lead {lead.name} created successfully!")
		return lead.name
	
	@frappe.whitelist()
	def mark_as_read(self):
		"""Reset unread count."""
		self.unread_count = 0
		self.save(ignore_permissions=True)
		frappe.msgprint("Marked as read")
	
	@frappe.whitelist()
	def add_conversation_note(self, note):
		"""Append note to conversation summary."""
		if self.conversation_summary:
			self.conversation_summary += f"\n\n---\n{frappe.utils.now()}: {note}"
		else:
			self.conversation_summary = f"{frappe.utils.now()}: {note}"
		self.save(ignore_permissions=True)
