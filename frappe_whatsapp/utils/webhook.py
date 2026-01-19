"""Webhook."""
import frappe
import json
import requests
import time
from werkzeug.wrappers import Response
import frappe.utils
import traceback

from frappe_whatsapp.utils import get_whatsapp_account


@frappe.whitelist(allow_guest=True)
def webhook():
	"""Meta webhook."""
	if frappe.request.method == "GET":
		return get()
	return post()


def get():
	"""Get."""
	hub_challenge = frappe.form_dict.get("hub.challenge")
	verify_token = frappe.form_dict.get("hub.verify_token")
	webhook_verify_token = frappe.db.get_value(
		'WhatsApp Account',
		{"webhook_verify_token": verify_token},
		'webhook_verify_token'
	)
	if not webhook_verify_token:
		frappe.throw("No matching WhatsApp account")

	if frappe.form_dict.get("hub.verify_token") != webhook_verify_token:
		frappe.throw("Verify token does not match")

	return Response(hub_challenge, status=200)

def post():
	"""Post."""
	try:
		data = frappe.local.form_dict
		
		# Load WhatsApp Settings for configuration
		settings = frappe.get_single("WhatsApp Settings")
		
		# CONDITIONAL WEBHOOK PAYLOAD LOGGING
		if settings.get("enable_webhook_payload_logs"):
			try:
				frappe.log_error(title="WhatsApp Webhook Payload", message=json.dumps(data, indent=2))
			except:
				pass

		# Log to doc
		try:
			frappe.get_doc({
				"doctype": "WhatsApp Notification Log",
				"template": "Webhook",
				"meta_data": json.dumps(data)
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error("Failed to log WhatsApp Notification")

		messages = []
		phone_id = None
		try:
			entry = data.get("entry", [{}])[0]
			changes = entry.get("changes", [{}])[0]
			value = changes.get("value", {})
			
			messages = value.get("messages", [])
			phone_id = value.get("metadata", {}).get("phone_number_id")
			
			if not messages and not phone_id:
				messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
		except (KeyError, IndexError):
			pass

		# CONDITIONAL DEBUG LOGGING
		if settings.get("enable_debug_logs"):
			frappe.log_error(title="WhatsApp Debug", message=f"Messages found: {len(messages)}, Phone ID: {phone_id}")

		sender_profile_name = next(
			(
				contact.get("profile", {}).get("name")
				for entry in data.get("entry", [])
				for change in entry.get("changes", [])
				for contact in change.get("value", {}).get("contacts", [])
			),
			None,
		)

		whatsapp_account = get_whatsapp_account(phone_id) if phone_id else None
		if not whatsapp_account:
			try:
				default_account = frappe.db.get_value("WhatsApp Account", {"is_default_incoming": 1}, "name")
				if default_account:
					whatsapp_account = frappe.get_doc("WhatsApp Account", default_account)
				else:
					whatsapp_account = frappe.get_doc("WhatsApp Account", "Main Offile Number")
			except Exception as e:
				frappe.log_error(f"WhatsApp Webhook - No Account Found: {str(e)}")
				return
		
		# Route to custom webhook if configured
		if whatsapp_account and whatsapp_account.custom_webhook_url:
			route_to_custom_webhook(whatsapp_account, data, settings)

		if messages:
			for message in messages:
				sender_phone = message.get('from')
				if not sender_phone:
					frappe.log_error("Skipping message: No 'from' field")
					continue
					
				try:
					whatsapp_contact = get_or_create_whatsapp_contact(
						mobile_no=sender_phone,
						contact_name=sender_profile_name,
						whatsapp_account=whatsapp_account.name
					)
				except Exception as e:
					frappe.log_error(title="Contact Creation Failed", message=str(traceback.format_exc()))
					continue

				message_type = message.get('type')
				is_reply = True if message.get('context') and 'forwarded' not in message.get('context') else False
				reply_to_message_id = message['context']['id'] if is_reply else None
				
				# Check if contact is linked to a CRM Lead
				lead_name = whatsapp_contact.lead_reference if whatsapp_contact.lead_reference else find_crm_lead_by_phone(sender_phone)
				
				# DUAL LINKING: Link to Lead (for CRM) AND WhatsApp Contact (for chat widget)
				# DUAL LINKING: Link to Lead (for CRM) if found
				if lead_name:
					reference_doctype = "CRM Lead"
					reference_name = lead_name
				else:
					reference_doctype = None
					reference_name = None
				
				msg_dict = {
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": sender_phone,
					"message_id": message.get('id'),
					"reply_to_message_id": reply_to_message_id,
					"is_reply": is_reply,
					"profile_name": sender_profile_name,
					"whatsapp_account": whatsapp_account.name,
					"reference_doctype": reference_doctype,
					"reference_name": reference_name,
					"whatsapp_contact": whatsapp_contact.name  # Always link to WhatsApp Contact
				}

				try:
					if message_type == 'text':
						msg_dict.update({
							"message": message['text']['body'],
							"content_type": message_type
						})
						msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, message['text']['body'], msg_doc.name)

					elif message_type == 'reaction':
						msg_dict.update({
							"message": message['reaction']['emoji'],
							"reply_to_message_id": message['reaction']['message_id'],
							"content_type": "reaction"
						})
						msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, None, msg_doc.name)

					elif message_type == 'interactive':
						interactive_data = message['interactive']
						interactive_type = interactive_data.get('type')

						if interactive_type == 'button_reply':
							msg_dict.update({
								"message": interactive_data['button_reply']['id'],
								"content_type": "button"
							})
							msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name, None, msg_doc.name)
							
						elif interactive_type == 'list_reply':
							msg_dict.update({
								"message": interactive_data['list_reply']['id'],
								"content_type": "button"
							})
							msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name, None, msg_doc.name)
							
						elif interactive_type == 'nfm_reply':
							nfm_reply = interactive_data['nfm_reply']
							response_json_str = nfm_reply.get('response_json', '{}')
							try:
								flow_response = json.loads(response_json_str)
							except json.JSONDecodeError:
								flow_response = {}

							summary_parts = []
							for key, value in flow_response.items():
								if value:
									summary_parts.append(f"{key}: {value}")
							summary_message = ", ".join(summary_parts) if summary_parts else "Flow completed"

							msg_dict.update({
								"message": summary_message,
								"content_type": "flow",
								"flow_response": json.dumps(flow_response)
							})
							msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name, summary_message, msg_doc.name)

							frappe.publish_realtime(
								"whatsapp_flow_response",
								{
									"phone": sender_phone,
									"message_id": message['id'],
									"flow_response": flow_response,
									"whatsapp_account": whatsapp_account.name
								}
							)

					elif message_type in ["image", "audio", "video", "document"]:
						token = whatsapp_account.get_password("token")
						url = f"{whatsapp_account.url}/{whatsapp_account.version}/"
						media_id = message[message_type]["id"]
						headers = {'Authorization': 'Bearer ' + token}
						
						try:
							response = requests.get(f'{url}{media_id}/', headers=headers)
							if response.status_code == 200:
								media_data = response.json()
								media_url = media_data.get("url")
								mime_type = media_data.get("mime_type")
								file_extension = mime_type.split('/')[1] if mime_type else "bin"

								media_response = requests.get(media_url, headers=headers)
								if media_response.status_code == 200:
									file_data = media_response.content
									file_name = f"{frappe.generate_hash(length=10)}.{file_extension}"

									msg_dict.update({
										"message": message[message_type].get("caption", ""),
										"content_type": message_type
									})
									message_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)

									file = frappe.get_doc({
										"doctype": "File",
										"file_name": file_name,
										"attached_to_doctype": "WhatsApp Message",
										"attached_to_name": message_doc.name,
										"content": file_data,
										"attached_to_field": "attach"
									}).save(ignore_permissions=True)

									message_doc.attach = file.file_url
									message_doc.save(ignore_permissions=True)
									update_whatsapp_contact_stats(whatsapp_contact.name, message[message_type].get("caption", ""), message_doc.name)
						except Exception as e:
							frappe.log_error(f"Media download failed: {str(e)}")

					elif message_type == "button":
						msg_dict.update({
							"message": message['button']['text'],
							"content_type": message_type
						})
						msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, message['button']['text'], msg_doc.name)
						
					else:
						msg_content = message.get(message_type, {}).get("body", str(message.get(message_type, "")))
						if isinstance(message.get(message_type), dict) and "body" not in message[message_type]:
							msg_content = json.dumps(message[message_type])

						msg_dict.update({
							"message": msg_content,
							"content_type": message_type
						})
						msg_doc = frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, None, msg_doc.name)
				except Exception as e:
					frappe.log_error(title=f"Message Insert Failed: {message_type}", message=str(traceback.format_exc()))

		else:
			changes = None
			try:
				changes = data["entry"][0]["changes"][0]
			except (KeyError, IndexError):
				try:
					changes = data["entry"]["changes"][0]
				except (KeyError, IndexError):
					pass
			if changes:
				update_status(changes)

	except Exception as e:
		frappe.log_error(title="WhatsApp Webhook FATAL", message=str(traceback.format_exc()))
	
	return Response("OK", status=200)


def update_status(data):
	"""Update status hook."""
	if data.get("field") == "message_template_status_update":
		update_template_status(data['value'])

	elif data.get("field") == "messages":
		update_message_status(data['value'])

def update_template_status(data):
	"""Update template status."""
	frappe.db.sql(
		"""UPDATE `tabWhatsApp Templates`
		SET status = %(event)s
		WHERE id = %(message_template_id)s""",
		data
	)

def update_message_status(data):
	"""Update message status using direct DB update to avoid race conditions."""
	try:
		status_data = data['statuses'][0]
		message_id = status_data['id']
		status = status_data['status']
		conversation = status_data.get('conversation', {}).get('id')
		
		name = frappe.db.get_value("WhatsApp Message", filters={"message_id": message_id})

		if name:
			# Use set_value to avoid TimestampMismatchError
			update_dict = {"status": status}
			if conversation:
				update_dict["conversation_id"] = conversation
			
			frappe.db.set_value("WhatsApp Message", name, update_dict, update_modified=False)
			frappe.db.commit()
	except (KeyError, IndexError):
		pass
	except Exception as e:
		frappe.log_error(f"update_message_status error: {str(e)}")


def find_crm_lead_by_phone(phone_number):
	"""Find CRM Lead by phone number, trying multiple formats."""
	phone_variants = [phone_number]
	if phone_number.startswith('+'):
		phone_variants.append(phone_number[1:])
	else:
		phone_variants.append('+' + phone_number)
	
	for phone in phone_variants:
		lead_name = frappe.db.get_value("CRM Lead", {"mobile_no": phone}, "name")
		if lead_name:
			return lead_name
	return None


def get_or_create_whatsapp_contact(mobile_no, contact_name, whatsapp_account):
	"""Get existing or create new WhatsApp Contact."""
	
	# Check exact match
	existing_name = frappe.db.exists("WhatsApp Contact", mobile_no)
	
	# Try adding/removing '+'
	if not existing_name:
		if mobile_no.startswith('+'):
			existing_name = frappe.db.exists("WhatsApp Contact", mobile_no[1:])
		else:
			existing_name = frappe.db.exists("WhatsApp Contact", "+" + mobile_no)

	if existing_name:
		contact = frappe.get_doc("WhatsApp Contact", existing_name)
		changed = False
		
		# Update name if we have new info
		if contact_name and (not contact.contact_name or contact.contact_name == contact.mobile_no):
			contact.contact_name = contact_name
			changed = True
		
		# Check if there's a matching CRM Lead and link it
		if not contact.lead_reference:
			lead_name = find_crm_lead_by_phone(mobile_no)
			if lead_name:
				contact.lead_reference = lead_name
				contact.converted_to_lead = 1
				changed = True
		
		if changed:
			contact.save(ignore_permissions=True)
		return contact
	
	# Create new contact
	lead_name = find_crm_lead_by_phone(mobile_no)
	
	try:
		contact_doc = {
			"doctype": "WhatsApp Contact",
			"mobile_no": mobile_no,
			"contact_name": contact_name or mobile_no,
			"whatsapp_account": whatsapp_account,
			"first_message_date": frappe.utils.now(),
			"last_message_date": frappe.utils.now(),
			"source": "WhatsApp Incoming"
		}
		
		# Link to CRM Lead if found
		if lead_name:
			contact_doc["lead_reference"] = lead_name
			contact_doc["converted_to_lead"] = 1
		
		contact = frappe.get_doc(contact_doc).insert(ignore_permissions=True)
		return contact
	except frappe.DuplicateEntryError:
		existing_name = frappe.db.exists("WhatsApp Contact", mobile_no)
		if existing_name:
			return frappe.get_doc("WhatsApp Contact", existing_name)
		raise


def update_whatsapp_contact_stats(contact_name, message_text=None, message_name=None):
	"""Update conversation statistics and publish real-time events."""
	try:

		# Use direct DB update to avoid TimestampMismatchError
		now = frappe.utils.now()
		updates = {
			"last_message_date": now,
			"is_read": 0
		}
		if message_text:
			updates["last_message"] = message_text[:500]
			
		frappe.db.set_value("WhatsApp Contact", contact_name, updates, update_modified=False)
		
		# Increment stats safely
		frappe.db.sql("""
			UPDATE `tabWhatsApp Contact`
			SET total_messages = total_messages + 1, unread_count = unread_count + 1
			WHERE name = %(name)s
		""", {"name": contact_name})
		
		# Fetch only needed fields without loading full document (avoids timestamp conflicts)
		contact_data = frappe.db.get_value("WhatsApp Contact", contact_name, 
			["email", "lead_reference", "contact_name", "mobile_no"], as_dict=True)
		
		# Build message data for real-time updates
		message_data = {
			"name": message_name,
			"content": message_text or '',
			"creation": frappe.utils.now(),
			"room": contact_name,
			"contact_name": contact_data.get("contact_name") if contact_data else contact_name,
			"sender_user_no": contact_data.get("mobile_no") if contact_data else "",
			"user": "Guest"
		}
		
		# BROADCAST to all users viewing this contact's chat
		# REMOVED: Duplicated in message.py > last_message hook
		# frappe.publish_realtime(
		# 	contact.name,
		# 	message_data,
		# 	after_commit=True
		# )
		
		# Broadcast to latest_chat_updates for chat list updates
		# REMOVED: Duplicated in message.py > last_message hook
		# frappe.publish_realtime(
		# 	"latest_chat_updates",
		# 	message_data,
		# 	after_commit=True
		# )
		
		# If contact is assigned to a specific user, also notify them directly
		if contact_data and contact_data.get("email"):
			frappe.publish_realtime(
				"chat-notification",
				message_data,
				user=contact_data.get("email"),
				after_commit=True
			)
		
		# Always publish realtime event for frontend updates
		frappe.publish_realtime(
			"whatsapp_message",
			{
				"lead": contact_data.get("lead_reference"),
				"contact": contact_name,
				"message": message_text,
				"message_name": message_name
			},
			after_commit=True
		)
			
			
	except Exception:
		frappe.log_error(f"Failed to update stats for contact {contact_name}")


def route_to_custom_webhook(whatsapp_account, data, settings=None):
	"""Route webhook data to custom webhook URL if configured."""
	if not whatsapp_account.custom_webhook_url:
		return False
	
	# Filter service messages if configured
	if settings and settings.get("filter_service_messages"):
		# Check if this webhook contains actual messages (not just status updates)
		try:
			entry = data.get("entry", [{}])[0]
			changes = entry.get("changes", [{}])[0]
			value = changes.get("value", {})
			
			# Only send to custom webhook if there are actual messages
			# Skip if it's just status updates (read, delivered, etc.)
			messages = value.get("messages", [])
			if not messages:
				# This is a service/status message, skip routing to custom webhook
				if settings.get("enable_debug_logs"):
					frappe.log_error(
						title="WhatsApp Webhook - Service Message Filtered",
						message=f"Skipped routing service message to custom webhook: {json.dumps(data, indent=2)[:500]}"
					)
				return False
		except (KeyError, IndexError):
			# If we can't parse the structure, skip it to be safe
			return False
	
	try:
		# Determine Bot Status
		bot_status = "Active"
		try:
			# Extract sender phone from payload to check permissions
			entry = data.get("entry", [{}])[0]
			changes = entry.get("changes", [{}])[0]
			value = changes.get("value", {})
			messages = value.get("messages", [])
			
			if messages:
				sender_phone = messages[0].get('from')
				if sender_phone:
					contact_name = frappe.db.get_value("WhatsApp Contact", {"mobile_no": sender_phone}, "name")
					if contact_name:
						paused_until = frappe.db.get_value("WhatsApp Contact", contact_name, "bot_paused_until")
						if paused_until:
							from frappe.utils import get_datetime, now_datetime
							if get_datetime(paused_until) > now_datetime():
								bot_status = "Paused"
		except Exception:
			pass # Fail safe, default to Active

		headers = {
			'Content-Type': 'application/json',
			'X-Frappe-Bot-Status': bot_status
		}

		response = requests.post(
			whatsapp_account.custom_webhook_url,
			json=data,
			headers=headers,
			timeout=5 
		)
		if response.status_code >= 400:
			frappe.log_error(
				title=f"Custom Webhook Error {response.status_code}",
				message=f"URL: {whatsapp_account.custom_webhook_url}\nResponse: {response.text[:500]}"
			)
		return True
	except Exception as e:
		frappe.log_error(
			title=f"Custom Webhook Failed - {whatsapp_account.name}",
			message=f"URL: {whatsapp_account.custom_webhook_url}\nError: {str(e)}"
		)
	return False
