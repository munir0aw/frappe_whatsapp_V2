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
		# DEBUG LOGGING
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
			# Safer extraction of message and phone_id
			entry = data.get("entry", [{}])[0]
			changes = entry.get("changes", [{}])[0]
			value = changes.get("value", {})
			
			messages = value.get("messages", [])
			phone_id = value.get("metadata", {}).get("phone_number_id")
			
			if not messages and not phone_id:
				# Fallback for different structure if needed
				messages = data["entry"]["changes"][0]["value"].get("messages", [])
		except (KeyError, IndexError):
			pass

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
			# Fallback to default account or hardcoded backup
			try:
				# Try finding any default incoming account
				default_account = frappe.db.get_value("WhatsApp Account", {"is_default_incoming": 1}, "name")
				if default_account:
					whatsapp_account = frappe.get_doc("WhatsApp Account", default_account)
				else:
					# Last resort fallback matching user data
					whatsapp_account = frappe.get_doc("WhatsApp Account", "Main Offile Number")
			except Exception as e:
				frappe.log_error(f"WhatsApp Webhook - No Account Found: {str(e)}")
				return
		
		# Route to custom webhook if configured (Requirement 1)
		if whatsapp_account and whatsapp_account.custom_webhook_url:
			route_to_custom_webhook(whatsapp_account, data)

		if messages:
			for message in messages:
				sender_phone = message.get('from')
				if not sender_phone:
					frappe.log_error("Skipping message: No 'from' field")
					continue
					
				# Get or create WhatsApp Contact (Requirement 2)
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
				
				# Prepare common message fields
				msg_dict = {
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": sender_phone,
					"message_id": message.get('id'),
					"reply_to_message_id": reply_to_message_id,
					"is_reply": is_reply,
					"profile_name": sender_profile_name,
					"whatsapp_account": whatsapp_account.name,
					"reference_doctype": "WhatsApp Contact",
					"reference_name": whatsapp_contact.name
				}

				try:
					if message_type == 'text':
						msg_dict.update({
							"message": message['text']['body'],
							"content_type": message_type
						})
						frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, message['text']['body'])

					elif message_type == 'reaction':
						msg_dict.update({
							"message": message['reaction']['emoji'],
							"reply_to_message_id": message['reaction']['message_id'],
							"content_type": "reaction"
						})
						frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name)

					elif message_type == 'interactive':
						interactive_data = message['interactive']
						interactive_type = interactive_data.get('type')

						if interactive_type == 'button_reply':
							msg_dict.update({
								"message": interactive_data['button_reply']['id'],
								"content_type": "button"
							})
							frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name)
							
						elif interactive_type == 'list_reply':
							msg_dict.update({
								"message": interactive_data['list_reply']['id'],
								"content_type": "button"
							})
							frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name)
							
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
							frappe.get_doc(msg_dict).insert(ignore_permissions=True)
							update_whatsapp_contact_stats(whatsapp_contact.name, summary_message)

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
									update_whatsapp_contact_stats(whatsapp_contact.name, message[message_type].get("caption", ""))
						except Exception as e:
							frappe.log_error(f"Media download failed: {str(e)}")

					elif message_type == "button":
						msg_dict.update({
							"message": message['button']['text'],
							"content_type": message_type
						})
						frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name, message['button']['text'])
						
					else:
						# Generic handling
						msg_content = message.get(message_type, {}).get("body", str(message.get(message_type, "")))
						# Fallback if body not found or structure varies
						if isinstance(message.get(message_type), dict) and "body" not in message[message_type]:
							# Just dump the dict if we can't find body
							msg_content = json.dumps(message[message_type])

						msg_dict.update({
							"message": msg_content,
							"content_type": message_type
						})
						frappe.get_doc(msg_dict).insert(ignore_permissions=True)
						update_whatsapp_contact_stats(whatsapp_contact.name)
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
	"""Update message status."""
	try:
		status_data = data['statuses'][0]
		id = status_data['id']
		status = status_data['status']
		conversation = status_data.get('conversation', {}).get('id')
		name = frappe.db.get_value("WhatsApp Message", filters={"message_id": id})

		if name:
			doc = frappe.get_doc("WhatsApp Message", name)
			doc.status = status
			if conversation:
				doc.conversation_id = conversation
			doc.save(ignore_permissions=True)
	except (KeyError, IndexError):
		pass


def get_or_create_whatsapp_contact(mobile_no, contact_name, whatsapp_account):
	"""Get existing or create new WhatsApp Contact."""
	
	# Try to find existing contact by mobile_no
	# Check exact match
	existing_name = frappe.db.exists("WhatsApp Contact", mobile_no)
	
	# If not found, try adding/removing '+'
	if not existing_name:
		if mobile_no.startswith('+'):
			existing_name = frappe.db.exists("WhatsApp Contact", mobile_no[1:])
		else:
			existing_name = frappe.db.exists("WhatsApp Contact", "+" + mobile_no)

	if existing_name:
		contact = frappe.get_doc("WhatsApp Contact", existing_name)
		# Update name if we have new info and old one fallback
		if contact_name and (not contact.contact_name or contact.contact_name == contact.mobile_no):
			contact.contact_name = contact_name
			contact.save(ignore_permissions=True)
		return contact
	
	# Create new contact
	language = detect_language(contact_name or mobile_no)
	# Check against Doctype options in case of mismatch
	# The Doctype seems to have strict validation on options: "Arabic", "English", "Mixed"
	
	try:
		contact = frappe.get_doc({
			"doctype": "WhatsApp Contact",
			"mobile_no": mobile_no,
			"contact_name": contact_name or mobile_no,
			"whatsapp_account": whatsapp_account,
			"first_message_date": frappe.utils.now(),
			"last_message_date": frappe.utils.now(),
			"qualification_status": "New",
			"source": "WhatsApp Incoming",
			"detected_language": language
		}).insert(ignore_permissions=True)
		return contact
	except frappe.DuplicateEntryError:
		# Race condition or inconsistent DB state; try fetching again
		existing_name = frappe.db.exists("WhatsApp Contact", mobile_no)
		if existing_name:
			return frappe.get_doc("WhatsApp Contact", existing_name)
		raise


def update_whatsapp_contact_stats(contact_name, message_text=None):
	"""Update conversation statistics and chat fields."""
	try:
		contact = frappe.get_doc("WhatsApp Contact", contact_name)
		contact.last_message_date = frappe.utils.now()
		contact.total_messages = (contact.total_messages or 0) + 1
		contact.unread_count = (contact.unread_count or 0) + 1
		
		# Chat-specific updates
		if message_text:
			contact.last_message = message_text[:500]  # Truncate for preview
		contact.is_read = 0  # Mark as unread for chat UI
		
		# Detect language from message
		if message_text and not contact.detected_language:
			contact.detected_language = detect_language(message_text)
		
		contact.save(ignore_permissions=True)
		
		# Publish real-time event for chat UI
		if contact.email:
			message_data = {
				"content": message_text or '',
				"creation": frappe.utils.now(),
				"room": contact.name,
				"contact_name": contact.contact_name,
				"sender_user_no": contact.mobile_no,
				"user": "Guest"
			}
			# Notify chat list
			frappe.publish_realtime(
				"latest_chat_updates",
				message_data,
				user=contact.email
			)
			# Notify open chat room
			frappe.publish_realtime(
				contact.name,
				message_data,
				user=contact.email
			)
	except Exception:
		frappe.log_error(f"Failed to update stats for contact {contact_name}")


def detect_language(text):
	"""Simple language detection."""
	if not text:
		return "English"
	
	# Simple detection
	arabic_chars = len([c for c in text if '\u0600' <= c <= '\u06FF'])
	return "Arabic" if arabic_chars > len(text) * 0.3 else "English"
