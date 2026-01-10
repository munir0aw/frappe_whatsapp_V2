"""Webhook."""
import frappe
import json
import requests
import time
from werkzeug.wrappers import Response
import frappe.utils

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
	data = frappe.local.form_dict
	frappe.get_doc({
		"doctype": "WhatsApp Notification Log",
		"template": "Webhook",
		"meta_data": json.dumps(data)
	}).insert(ignore_permissions=True)

	messages = []
	phone_id = None
	try:
		messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
		phone_id = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("metadata", {}).get("phone_number_id")
	except KeyError:
		messages = data["entry"]["changes"][0]["value"].get("messages", [])
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
		frappe.log_error(
			title="WhatsApp Webhook - No Account Found",
			message=f"phone_id: {phone_id}\nPayload: {json.dumps(data, indent=2)}"
		)
		# Fallback to default account
		try:
			whatsapp_account = frappe.get_doc("WhatsApp Account", "Main Offile Number")
		except:
			return
	
	# Route to custom webhook if configured
	if whatsapp_account and whatsapp_account.custom_webhook_url:
		route_to_custom_webhook(whatsapp_account, data)

	if messages:
		for message in messages:
			sender_phone = message['from']
			
			# Get or create WhatsApp Contact
			whatsapp_contact = get_or_create_whatsapp_contact(
				mobile_no=sender_phone,
				contact_name=sender_profile_name,
				whatsapp_account=whatsapp_account.name
			)
			
			message_type = message['type']
			is_reply = True if message.get('context') and 'forwarded' not in message.get('context') else False
			reply_to_message_id = message['context']['id'] if is_reply else None
			if message_type == 'text':
				frappe.get_doc({
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": message['from'],
					"message": message['text']['body'],
					"message_id": message['id'],
					"reply_to_message_id": reply_to_message_id,
					"is_reply": is_reply,
					"content_type":message_type,
					"profile_name":sender_profile_name,
					"whatsapp_account":whatsapp_account.name,
					"reference_doctype": "WhatsApp Contact",
					"reference_name": whatsapp_contact.name
				}).insert(ignore_permissions=True)
				
				# Update WhatsApp Contact stats
				update_whatsapp_contact_stats(whatsapp_contact.name, message['text']['body'])
			elif message_type == 'reaction':
				frappe.get_doc({
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": message['from'],
					"message": message['reaction']['emoji'],
					"reply_to_message_id": message['reaction']['message_id'],
					"message_id": message['id'],
					"content_type": "reaction",
					"profile_name":sender_profile_name,
					"whatsapp_account":whatsapp_account.name,
					"reference_doctype": "WhatsApp Contact",
					"reference_name": whatsapp_contact.name
				}).insert(ignore_permissions=True)
				
				# Update WhatsApp Contact stats
				update_whatsapp_contact_stats(whatsapp_contact.name)
			elif message_type == 'interactive':
				interactive_data = message['interactive']
				interactive_type = interactive_data.get('type')

				# Handle button reply
				if interactive_type == 'button_reply':
					frappe.get_doc({
						"doctype": "WhatsApp Message",
						"type": "Incoming",
						"from": message['from'],
						"message": interactive_data['button_reply']['id'],
						"message_id": message['id'],
						"reply_to_message_id": reply_to_message_id,
						"is_reply": is_reply,
						"content_type": "button",
						"profile_name": sender_profile_name,
						"whatsapp_account": whatsapp_account.name,
						"reference_doctype": "WhatsApp Contact",
						"reference_name": whatsapp_contact.name
					}).insert(ignore_permissions=True)
					update_whatsapp_contact_stats(whatsapp_contact.name)
				# Handle list reply
				elif interactive_type == 'list_reply':
					frappe.get_doc({
						"doctype": "WhatsApp Message",
						"type": "Incoming",
						"from": message['from'],
						"message": interactive_data['list_reply']['id'],
						"message_id": message['id'],
						"reply_to_message_id": reply_to_message_id,
						"is_reply": is_reply,
						"content_type": "button",
						"profile_name": sender_profile_name,
						"whatsapp_account": whatsapp_account.name,
						"reference_doctype": "WhatsApp Contact",
						"reference_name": whatsapp_contact.name
					}).insert(ignore_permissions=True)
					update_whatsapp_contact_stats(whatsapp_contact.name)
				# Handle WhatsApp Flows (nfm_reply)
				elif interactive_type == 'nfm_reply':
					nfm_reply = interactive_data['nfm_reply']
					response_json_str = nfm_reply.get('response_json', '{}')

					# Parse the response JSON
					try:
						flow_response = json.loads(response_json_str)
					except json.JSONDecodeError:
						flow_response = {}

					# Create a summary message from the flow response
					summary_parts = []
					for key, value in flow_response.items():
						if value:
							summary_parts.append(f"{key}: {value}")
					summary_message = ", ".join(summary_parts) if summary_parts else "Flow completed"

					msg_doc = frappe.get_doc({
						"doctype": "WhatsApp Message",
						"type": "Incoming",
						"from": message['from'],
						"message": summary_message,
						"message_id": message['id'],
						"reply_to_message_id": reply_to_message_id,
						"is_reply": is_reply,
						"content_type": "flow",
						"flow_response": json.dumps(flow_response),
						"profile_name": sender_profile_name,
						"whatsapp_account": whatsapp_account.name,
						"reference_doctype": "WhatsApp Contact",
						"reference_name": whatsapp_contact.name
					}).insert(ignore_permissions=True)
					
					# Update WhatsApp Contact stats
					update_whatsapp_contact_stats(whatsapp_contact.name, summary_message)

					# Publish realtime event for flow response
					frappe.publish_realtime(
						"whatsapp_flow_response",
						{
							"phone": message['from'],
							"message_id": message['id'],
							"flow_response": flow_response,
							"whatsapp_account": whatsapp_account.name
						}
					)
			elif message_type in ["image", "audio", "video", "document"]:
				token = whatsapp_account.get_password("token")
				url = f"{whatsapp_account.url}/{whatsapp_account.version}/"

				media_id = message[message_type]["id"]
				headers = {
					'Authorization': 'Bearer ' + token

				}
				response = requests.get(f'{url}{media_id}/', headers=headers)

				if response.status_code == 200:
					media_data = response.json()
					media_url = media_data.get("url")
					mime_type = media_data.get("mime_type")
					file_extension = mime_type.split('/')[1]

					media_response = requests.get(media_url, headers=headers)
					if media_response.status_code == 200:

						file_data = media_response.content
						file_name = f"{frappe.generate_hash(length=10)}.{file_extension}"

						message_doc = frappe.get_doc({
							"doctype": "WhatsApp Message",
							"type": "Incoming",
							"from": message['from'],
							"message_id": message['id'],
							"reply_to_message_id": reply_to_message_id,
							"is_reply": is_reply,
							"message": message[message_type].get("caption", ""),
							"content_type" : message_type,
							"profile_name":sender_profile_name,
							"whatsapp_account":whatsapp_account.name,
							"reference_doctype": "WhatsApp Contact",
							"reference_name": whatsapp_contact.name
						}).insert(ignore_permissions=True)

						file = frappe.get_doc(
							{
								"doctype": "File",
								"file_name": file_name,
								"attached_to_doctype": "WhatsApp Message",
								"attached_to_name": message_doc.name,
								"content": file_data,
								"attached_to_field": "attach"
							}
						).save(ignore_permissions=True)


						message_doc.attach = file.file_url
						message_doc.save()
						
						# Update WhatsApp Contact stats
						update_whatsapp_contact_stats(whatsapp_contact.name, message[message_type].get("caption", ""))
			elif message_type == "button":
				frappe.get_doc({
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": message['from'],
					"message": message['button']['text'],
					"message_id": message['id'],
					"reply_to_message_id": reply_to_message_id,
					"is_reply": is_reply,
					"content_type": message_type,
					"profile_name":sender_profile_name,
					"whatsapp_account":whatsapp_account.name,
					"reference_doctype": "WhatsApp Contact",
					"reference_name": whatsapp_contact.name
				}).insert(ignore_permissions=True)
				update_whatsapp_contact_stats(whatsapp_contact.name, message['button']['text'])
			else:
				frappe.get_doc({
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": message['from'],
					"message_id": message['id'],
					"message": message[message_type].get(message_type),
					"content_type" : message_type,
					"profile_name":sender_profile_name,
					"whatsapp_account":whatsapp_account.name,
					"reference_doctype": "WhatsApp Contact",
					"reference_name": whatsapp_contact.name
				}).insert(ignore_permissions=True)
				update_whatsapp_contact_stats(whatsapp_contact.name)

	else:
		changes = None
		try:
			changes = data["entry"][0]["changes"][0]
		except KeyError:
			changes = data["entry"]["changes"][0]
		update_status(changes)
	return

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
	id = data['statuses'][0]['id']
	status = data['statuses'][0]['status']
	conversation = data['statuses'][0].get('conversation', {}).get('id')
	name = frappe.db.get_value("WhatsApp Message", filters={"message_id": id})

	doc = frappe.get_doc("WhatsApp Message", name)
	doc.status = status
	if conversation:
		doc.conversation_id = conversation
	doc.save(ignore_permissions=True)


def get_or_create_whatsapp_contact(mobile_no, contact_name, whatsapp_account):
	"""Get existing or create new WhatsApp Contact."""
	
	# Check if contact exists
	existing = frappe.db.exists("WhatsApp Contact", {"mobile_no": mobile_no})
	
	if existing:
		contact = frappe.get_doc("WhatsApp Contact", existing)
		# Update name if we have new info
		if contact_name and not contact.contact_name:
			contact.contact_name = contact_name
			contact.save(ignore_permissions=True)
		return contact
	
	# Create new contact
	contact = frappe.get_doc({
		"doctype": "WhatsApp Contact",
		"mobile_no": mobile_no,
		"contact_name": contact_name or mobile_no,
		"whatsapp_account": whatsapp_account,
		"first_message_date": frappe.utils.now(),
		"last_message_date": frappe.utils.now(),
		"qualification_status": "New",
		"source": "WhatsApp Incoming",
		"detected_language": detect_language(contact_name or mobile_no)
	}).insert(ignore_permissions=True)
	
	return contact


def update_whatsapp_contact_stats(contact_name, message_text=None):
	"""Update conversation statistics and chat fields."""
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



def detect_language(text):
	"""Simple language detection."""
	if not text:
		return "English"
	
	arabic_chars = len([c for c in text if '\u0600' <= c <= '\u06FF'])
	return "Arabic" if arabic_chars > len(text) * 0.3 else "English"


def route_to_custom_webhook(whatsapp_account, data):
	"""Route webhook data to custom webhook URL if configured."""
	if not whatsapp_account.custom_webhook_url:
		return False
	
	try:
		response = requests.post(
			whatsapp_account.custom_webhook_url,
			json=data,
			headers={'Content-Type': 'application/json'},
			timeout=10
		)
		
		frappe.log_error(
			title=f"Custom Webhook Routed - {whatsapp_account.name}",
			message=f"URL: {whatsapp_account.custom_webhook_url}\nStatus: {response.status_code}\nResponse: {response.text[:500]}"
		)
		return True
	except Exception as e:
		frappe.log_error(
			title=f"Custom Webhook Failed - {whatsapp_account.name}",
			message=f"URL: {whatsapp_account.custom_webhook_url}\nError: {str(e)}"
		)
		return False

