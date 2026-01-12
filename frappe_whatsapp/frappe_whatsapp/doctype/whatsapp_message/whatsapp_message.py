# Copyright (c) 2022, Shridhar Patil and contributors
# For license information, please see license.txt
import json
import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request

from frappe_whatsapp.utils import get_whatsapp_account, format_number

class WhatsAppMessage(Document):
    def validate(self):
        self.set_whatsapp_account()
        
        # Ensure message is linked to WhatsApp Contact
        if not self.whatsapp_contact:
            # Determine phone number
            phone = self.to if self.type == "Outgoing" else self.get("from")
            if phone:
                # Find or create contact
                contact_name = self.get_contact_name(phone)
                if contact_name:
                    self.whatsapp_contact = contact_name

    def get_contact_name(self, mobile_no):
        """Find existing contact or return None."""
        # Check exact match
        existing_name = frappe.db.exists("WhatsApp Contact", mobile_no)
        if existing_name: return existing_name
        
        # Check with/without +
        if mobile_no.startswith('+'):
            existing_name = frappe.db.exists("WhatsApp Contact", mobile_no[1:])
        else:
            existing_name = frappe.db.exists("WhatsApp Contact", "+" + mobile_no)
        
        if existing_name: return existing_name
        
        # If outgoing, we might want to create the contact if it doesn't exist?
        # For now, let's just create it to be safe so the chat works
        try:
             # Import here to avoid circular import issues if any
            from frappe.utils import now
            contact = frappe.get_doc({
                "doctype": "WhatsApp Contact",
                "mobile_no": mobile_no,
                "contact_name": mobile_no,
                "whatsapp_account": self.whatsapp_account,
                "first_message_date": now(),
                "last_message_date": now(),
                "source": "WhatsApp Outgoing" if self.type == "Outgoing" else "WhatsApp Incoming"
            }).insert(ignore_permissions=True)
            return contact.name
        except Exception:
            return None

    def on_update(self):
        self.update_profile_name()

    def update_profile_name(self):
        number = self.get("from")
        if not number:
            return
        from_number = format_number(number)

        if (
            self.has_value_changed("profile_name")
            and self.profile_name
            and from_number
            and frappe.db.exists("WhatsApp Profiles", {"number": from_number})
        ):
            profile_id = frappe.get_value("WhatsApp Profiles", {"number": from_number}, "name")
            frappe.db.set_value("WhatsApp Profiles", profile_id, "profile_name", self.profile_name)

    def create_whatsapp_profile(self):
        number = format_number(self.get("from") or self.to)
        if not frappe.db.exists("WhatsApp Profiles", {"number": number}):
            frappe.get_doc({
                "doctype": "WhatsApp Profiles",
                "profile_name": self.profile_name,
                "number": number,
                "whatsapp_account": self.whatsapp_account
            }).insert(ignore_permissions=True)

    def set_whatsapp_account(self):
        """Set whatsapp account to default if missing"""
        if not self.whatsapp_account:
            account_type = 'outgoing' if self.type == 'Outgoing' else 'incoming'
            default_whatsapp_account = get_whatsapp_account(account_type=account_type)
            if not default_whatsapp_account:
                throw(_("Please set a default outgoing WhatsApp Account or Select available WhatsApp Account"))
            else:
                self.whatsapp_account = default_whatsapp_account.name

    """Send whats app messages."""
    def before_insert(self):
        """Send message."""
        self.set_whatsapp_account()
        if self.type == "Outgoing" and self.message_type != "Template":
            if self.attach and not self.attach.startswith("http"):
                link = frappe.utils.get_url() + "/" + self.attach
            else:
                link = self.attach

            data = {
                "messaging_product": "whatsapp",
                "to": format_number(self.to),
                "type": self.content_type,
            }
            if self.is_reply and self.reply_to_message_id:
                data["context"] = {"message_id": self.reply_to_message_id}
            if self.content_type in ["document", "image", "video"]:
                data[self.content_type.lower()] = {
                    "link": link,
                    "caption": self.message,
                }
            elif self.content_type == "reaction":
                data["reaction"] = {
                    "message_id": self.reply_to_message_id,
                    "emoji": self.message,
                }
            elif self.content_type == "text":
                data["text"] = {"preview_url": True, "body": self.message}

            elif self.content_type == "audio":
                data["audio"] = {"link": link}

            elif self.content_type == "interactive":
                # Interactive message (buttons or list)
                data["type"] = "interactive"
                buttons_data = json.loads(self.buttons) if isinstance(self.buttons, str) else self.buttons

                if isinstance(buttons_data, list) and len(buttons_data) > 3:
                    # Use list message for more than 3 options (max 10)
                    data["interactive"] = {
                        "type": "list",
                        "body": {"text": self.message},
                        "action": {
                            "button": "Select Option",
                            "sections": [{
                                "title": "Options",
                                "rows": [
                                    {"id": btn["id"], "title": btn["title"], "description": btn.get("description", "")}
                                    for btn in buttons_data[:10]
                                ]
                            }]
                        }
                    }
                else:
                    # Use button message for 3 or fewer options
                    data["interactive"] = {
                        "type": "button",
                        "body": {"text": self.message},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": btn["id"], "title": btn["title"]}
                                }
                                for btn in buttons_data[:3]
                            ]
                        }
                    }

            elif self.content_type == "flow":
                # WhatsApp Flow message
                if not self.flow:
                    frappe.throw(_("WhatsApp Flow is required for flow content type"))

                flow_doc = frappe.get_doc("WhatsApp Flow", self.flow)

                if not flow_doc.flow_id:
                    frappe.throw(_("Flow must be created on WhatsApp before sending"))

                # Determine flow mode - draft flows can be tested with mode: "draft"
                flow_mode = None
                if flow_doc.status != "Published":
                    flow_mode = "draft"
                    frappe.msgprint(_("Sending flow in draft mode (for testing only)"), indicator="orange")

                # Get first screen if not specified
                flow_screen = self.flow_screen
                if not flow_screen and flow_doc.screens:
                    flow_screen = flow_doc.screens[0].screen_id

                data["type"] = "interactive"
                data["interactive"] = {
                    "type": "flow",
                    "body": {"text": self.message or "Please fill out the form"},
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_id": flow_doc.flow_id,
                            "flow_cta": self.flow_cta or flow_doc.flow_cta or "Open",
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": flow_screen
                            }
                        }
                    }
                }

                # Add draft mode for testing unpublished flows
                if flow_mode:
                    data["interactive"]["action"]["parameters"]["mode"] = flow_mode

                # Add flow token - generate one if not provided (required by WhatsApp)
                flow_token = self.flow_token or frappe.generate_hash(length=16)
                data["interactive"]["action"]["parameters"]["flow_token"] = flow_token

            try:
                self.notify(data)
                self.status = "Success"
            except Exception as e:
                self.status = "Failed"
                frappe.throw(f"Failed to send message {str(e)}")
        elif self.type == "Outgoing" and self.message_type == "Template" and not self.message_id:
            self.send_template()

        self.create_whatsapp_profile()

    def send_template(self):
        """Send template."""
        template = frappe.get_doc("WhatsApp Templates", self.template)
        data = {
            "messaging_product": "whatsapp",
            "to": format_number(self.to),
            "type": "template",
            "template": {
                "name": template.actual_name or template.template_name,
                "language": {"code": template.language_code},
                "components": [],
            },
        }

        if template.sample_values:
            field_names = template.field_names.split(",") if template.field_names else template.sample_values.split(",")
            parameters = []
            template_parameters = []

            if self.body_param is not None:
                parsed_param = json.loads(self.body_param)
                
                # Handle both list format ["value1", "value2"] and dict format {"key1": "value1"}
                if isinstance(parsed_param, list):
                    # Direct list of values from bulk messaging Common variables
                    params = parsed_param
                elif isinstance(parsed_param, dict):
                    # Dictionary format from Unique variables or CRM
                    params = list(parsed_param.values())
                else:
                    params = [parsed_param]
                
                for param in params:
                    parameters.append({"type": "text", "text": str(param)})
                    template_parameters.append(param)
            elif self.flags.custom_ref_doc:
                custom_values = self.flags.custom_ref_doc
                for field_name in field_names:
                    value = custom_values.get(field_name.strip())
                    parameters.append({"type": "text", "text": value})
                    template_parameters.append(value)                    

            else:
                ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
                for field_name in field_names:
                    value = ref_doc.get_formatted(field_name.strip())
                    parameters.append({"type": "text", "text": value})
                    template_parameters.append(value)

            self.template_parameters = json.dumps(template_parameters)
            data["template"]["components"].append(
                {
                    "type": "body",
                    "parameters": parameters,
                }
            )

        if template.header_type:
            if self.attach:
                if template.header_type == 'IMAGE':

                    if self.attach.startswith("http"):
                        url = f'{self.attach}'
                    else:
                        url = f'{frappe.utils.get_url()}{self.attach}'
                    data['template']['components'].append({
                        "type": "header",
                        "parameters": [{
                            "type": "image",
                            "image": {
                                "link": url
                            }
                        }]
                    })

            elif template.sample:
                if template.header_type == 'IMAGE':
                    if template.sample.startswith("http"):
                        url = f'{template.sample}'
                    else:
                        url = f'{frappe.utils.get_url()}{template.sample}'
                    data['template']['components'].append({
                        "type": "header",
                        "parameters": [{
                            "type": "image",
                            "image": {
                                "link": url
                            }
                        }]
                    })

        if template.buttons:
            button_parameters = []
            for idx, btn in enumerate(template.buttons):
                if btn.button_type == "Quick Reply":
                    button_parameters.append({
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": str(idx),
                        "parameters": [{"type": "payload", "payload": btn.button_label}]
                    })
                # Only send URL button parameter if it's Dynamic
                elif btn.button_type == "Visit Website" and btn.url_type == "Dynamic":
                    ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
                    url = ref_doc.get_formatted(btn.website_url)
                    button_parameters.append({
                        "type": "button",
                        "sub_type": "url",
                        "index": str(idx),
                        "parameters": [{"type": "text", "text": url}]
                    })
                # Static phone and static URL buttons: NO parameters needed!
                # WhatsApp gets these from the approved template itself

            if button_parameters:
                data['template']['components'].extend(button_parameters)

        self.notify(data)

    def notify(self, data):
        """Notify."""
        whatsapp_account = frappe.get_doc(
            "WhatsApp Account",
            self.whatsapp_account,
        )
        token = whatsapp_account.get_password("token")

        headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
        }
        try:
            response = make_post_request(
                f"{whatsapp_account.url}/{whatsapp_account.version}/{whatsapp_account.phone_id}/messages",
                headers=headers,
                data=json.dumps(data),
            )
            
            if response and "messages" in response:
                self.message_id = response["messages"][0]["id"]
            else:
                 # Message likely sent (200 OK) but response structure unexpected
                 frappe.log_error(title="WhatsApp Send - Unexpected Response", message=str(response))
                 self.status = "Sent (ID Missing)"

        except Exception as e:
            res = {}
            error_message = str(e)
            try:
                if frappe.flags.integration_request:
                    res = frappe.flags.integration_request.json().get("error", {})
                    error_message = res.get("Error", res.get("message"))
            except:
                pass
            
            # Truncate error message to prevent database constraint violations
            data_str = json.dumps(data)
            error_str = str(error_message)
            
            # Limit meta_data to 5000 characters to avoid database constraints
            meta_data_content = f"Data: {data_str}\nError: {error_str}"
            if len(meta_data_content) > 5000:
                meta_data_content = meta_data_content[:4950] + "... (truncated)"
            
            # Log full error for debugging
            frappe.log_error(
                title=f"WhatsApp Send Failed: {self.to}",
                message=f"Full Data: {data_str}\n\nFull Error: {error_str}"
            )
                
            frappe.get_doc(
                {
                    "doctype": "WhatsApp Notification Log",
                    "template": "Text Message",
                    "meta_data": meta_data_content,
                }
            ).insert(ignore_permissions=True)

            frappe.throw(msg=error_message, title=res.get("error_user_title", "Error"))


    def format_number(self, number):
        """Format number."""
        if number.startswith("+"):
            number = number[1 : len(number)]

        return number

    @frappe.whitelist()
    def send_read_receipt(self):
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": self.message_id
        }

        settings = frappe.get_doc(
            "WhatsApp Account",
            self.whatsapp_account,
        )

        token = settings.get_password("token")

        headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
        }
        try:
            response = make_post_request(
                f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
                headers=headers,
                data=json.dumps(data),
            )

            if response.get("success"):
                self.status = "marked as read"
                self.save()
                return response.get("success")

        except Exception as e:
            res = frappe.flags.integration_request.json().get("error", {})
            error_message = res.get("Error", res.get("message"))
            frappe.log_error("WhatsApp API Error", f"{error_message}\n{res}")


def on_doctype_update():
    frappe.db.add_index("WhatsApp Message", ["reference_doctype", "reference_name"])


@frappe.whitelist()
def send_template(to, reference_doctype, reference_name, template):
    try:
        doc = frappe.get_doc({
            "doctype": "WhatsApp Message",
            "to": to,
            "type": "Outgoing",
            "message_type": "Template",
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "content_type": "text",
            "template": template
        })

        doc.save()
    except Exception as e:
        raise e
