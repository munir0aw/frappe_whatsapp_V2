# Bulk WhatsApp Messaging for Frappe WhatsApp
# bulk_whatsapp_messaging.py

import frappe
from frappe import _
import json
from frappe.utils import cint, get_datetime, now
from frappe.model.document import Document
from frappe.model.naming import make_autoname

# Add these files to your frappe_whatsapp app

# 1. First, create a new DocType for Bulk WhatsApp Messaging
# Save this as a Python file in your app's folder: 
# frappe_whatsapp/frappe_whatsapp/doctype/bulk_whatsapp_message/bulk_whatsapp_message.py

class BulkWhatsAppMessage(Document):
    def autoname(self):
        self.name = make_autoname("BULK-WA-.YYYY.-.#####")
    
    def validate(self):
        # self.validate_message()\n        self.validate_recipients()
        self.convert_recipient_values_to_json()  # Convert value columns to JSON
        if self.use_template:
            self.validate_template_variables()
    
    def convert_recipient_values_to_json(self):
        """Convert value1, value2, value3 columns to recipient_data JSON"""
        if not self.variable_type and self.recipients:  # Unchecked = Use recipient data
            for recipient in self.recipients:
                # Build JSON from value columns
                data = {}
                if recipient.value1:
                    data["value1"] = recipient.value1
                if recipient.value2:
                    data["value2"] = recipient.value2
                if recipient.value3:
                    data["value3"] = recipient.value3
                
                if data:
                    recipient.recipient_data = json.dumps(data)
    
    def validate_message(self):
        if not self.message_content:
            frappe.throw(_("Message content is required"))
    
    def validate_recipients(self):
        if not self.recipients and not self.recipient_list:
            frappe.throw(_("At least one recipient or a recipient list is required"))
        
        # If recipient list is provided, count recipients
        if self.recipient_type == 'Recipient List' and self.recipient_list:
            recipient_count = frappe.db.count("WhatsApp Recipient", {"parent": self.recipient_list})
            if recipient_count == 0:
                frappe.throw(_("Selected recipient list has no recipients"))
            self.recipient_count = recipient_count
        # If individual recipients are provided
        elif self.recipients:
            self.recipient_count = len(self.recipients)
    
    def validate_template_variables(self):
        """Validate template variables configuration"""
        if not self.template:
            frappe.throw(_("Please select a template"))
        
        template_doc = frappe.get_doc("WhatsApp Templates", self.template)
        
        # Check if template needs variables
        if not template_doc.sample_values:
            return  # No variables needed
        
        # Get expected number of variables
        expected_count = len(template_doc.sample_values.split(","))
        
        if self.variable_type:  # Checked = Use template values
            # Convert table to JSON format for processing
            if self.template_values:
                values_list = []
                for idx, row in enumerate(self.template_values, start=1):
                    row.position = idx  # Auto-number
                    values_list.append(row.value)
                
                # Store as JSON in hidden field
                self.template_variables = json.dumps(values_list)
                
                if len(values_list) != expected_count:
                    frappe.throw(_(f"This template requires {expected_count} variable(s), but {len(values_list)} provided"))
            elif self.template_variables:
                # Backward compatibility: JSON still works
                try:
                    variables = json.loads(self.template_variables)
                    if not isinstance(variables, list):
                        frappe.throw(_("Template Variables must be a JSON array like: [\"value1\", \"value2\"]"))
                    if len(variables) != expected_count:
                        frappe.throw(_(f"This template requires {expected_count} variable(s), but {len(variables)} provided"))
                except json.JSONDecodeError:
                    frappe.throw(_("Template Variables must be valid JSON format: [\"value1\", \"value2\"]"))
            else:
                frappe.throw(_("Template Values are required for this template"))
        
        else:  # Unchecked = Use recipient data
            # Validate that recipients have data
            if self.recipient_type == 'Individual' and self.recipients:
                for recipient in self.recipients:
                    if not recipient.recipient_data:
                        frappe.msgprint(_(f"Warning: Recipient {recipient.mobile_number} has no data. Message may fail."), indicator="orange")
    
    def on_submit(self):
        self.db_set("status", "Queued")
        self.queue_messages()
    
    def queue_messages(self):
        """Queue messages for sending"""
        if self.recipient_type == 'Recipient List' and self.recipient_list:
            # Fetch recipients from the recipient list
            recipients = frappe.get_all(
                "WhatsApp Recipient", 
                filters={"parent": self.recipient_list},
                fields=["mobile_number", "name", "recipient_name", "recipient_data"]
            )
            
            for recipient in recipients:
                frappe.enqueue_doc(
                    self.doctype, self.name,
                    "create_single_message",
                    "long", 4000,
                    recipient=recipient
                )
        else:
            # Use recipients from the current document
            for recipient in self.recipients:
                frappe.enqueue_doc(
                    self.doctype, self.name,
                    "create_single_message",
                    "long", 4000,
                    recipient=recipient
                )
    
    def create_single_message(self, recipient):
        """Create a single message in the queue"""
        # message_content = self.message_content
        
        # Replace variables in the message if any
        self.status == "In Progress"
        if recipient.get("recipient_data"):
            try:
                variables = json.loads(recipient.get("recipient_data", "{}"))
                # for var_name, var_value in variables.items():
                #     message_content = message_content.replace(f"{{{{{var_name}}}}}", str(var_value))
            except Exception as e:
                frappe.log_error(f"Error parsing recipient data: {str(e)}", "WhatsApp Bulk Messaging")
        
        # Create WhatsApp message
        wa_message = frappe.new_doc("WhatsApp Message")
        # wa_message.from_number = self.from_number
        wa_message.to = recipient.get("mobile_number")
        wa_message.type = "Outgoing"  # CRITICAL: Required to trigger send in before_insert
        wa_message.message_type = "Text"
        wa_message.content_type = "text"  # Required for non-template messages
        # wa_message.message = message_content
        wa_message.flags.custom_ref_doc = json.loads(recipient.get("recipient_data", "{}"))
        wa_message.bulk_message_reference = self.name
        if self.whatsapp_account:
            wa_message.whatsapp_account = self.whatsapp_account
        
        # If template is being used
        if self.use_template:
            wa_message.template = self.template
            wa_message.message_type = 'Template'
            wa_message.use_template = self.use_template
            # Handle template variables if needed

            if self.variable_type:  # Checked = Use template values (same for all)
                wa_message.body_param = self.template_variables
            else:  # Unchecked = Use recipient specific data
                if recipient.get("recipient_data"):
                    wa_message.body_param = recipient.get("recipient_data")
            
            if self.attach:
                wa_message.attach = self.attach
        
        # Set status to queued (will be updated when sent)
        wa_message.status = "Queued"
        try:
            wa_message.insert(ignore_permissions=True)
            frappe.db.commit()  # Commit immediately to ensure message is created
        except Exception as e:
            frappe.log_error(
                title=f"Bulk Message Failed: {recipient.get('mobile_number')}",
                message=f"Bulk Message: {self.name}\nRecipient: {recipient.get('mobile_number')}\nError: {str(e)}"
            )
            self.db_set("status", "Partially Failed")
        # Update message count
        self.db_set("sent_count", cint(self.sent_count) + 1)
        if self.recipient_count == self.sent_count:
            self.db_set("status", "Completed")

    def retry_failed(self):
        """Retry failed messages"""
        failed_messages = frappe.get_all(
            "WhatsApp Message",
            filters={
                "bulk_message_reference": self.name,
                "status": "Failed"
            },
            fields=["name"]
        )
        
        count = 0
        for msg in failed_messages:
            message_doc = frappe.get_doc("WhatsApp Message", msg.name)
            message_doc.status = "Queued"
            message_doc.save(ignore_permissions=True)
            count += 1
        
        frappe.msgprint(_("{0} messages have been requeued for sending").format(count))
        
    def get_progress(self):
        """Get sending progress for this bulk message"""
        total = self.recipient_count
        sent = frappe.db.count("WhatsApp Message", {
            "bulk_message_reference": self.name,
            "status": ["in", ["sent","delivered", "Success", "read"]]
        })
        failed = frappe.db.count("WhatsApp Message", {
            "bulk_message_reference": self.name,
            "status": "Failed"
        })
        queued = frappe.db.count("WhatsApp Message", {
            "bulk_message_reference": self.name,
            "status": "Queued"
        })
        
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "queued": queued,
            "percent": (sent / total * 100) if total else 0
        }
