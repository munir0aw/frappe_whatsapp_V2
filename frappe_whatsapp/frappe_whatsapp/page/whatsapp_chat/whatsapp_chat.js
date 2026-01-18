frappe.pages['whatsapp_chat'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'WhatsApp Conversations',
		single_column: false
	});

	page.whatsapp_chat = new WhatsAppChat(page);
};

class WhatsAppChat {
	constructor(page) {
		this.page = page;
		this.current_contact = null;
		this.contacts = [];
		this.messages = [];
		
		this.setup_layout();
		this.setup_realtime();
		this.load_contacts();
	}

	setup_layout() {
		// Inject CSS directly to bypass asset loading issues
		this.inject_styles();
		
		// Create main container using page.body wrapped in jQuery
		const $container = $(this.page.body);
		$container.html(`
			<div class="whatsapp-container">
				<!-- Left Panel - Contacts List -->
				<div class="whatsapp-sidebar">
					<div class="whatsapp-search">
						<input type="text" 
							class="form-control" 
							placeholder="Search contacts..." 
							id="contact-search">
					</div>
					<div class="whatsapp-contacts" id="contacts-list">
						<!-- Contacts will be loaded here -->
					</div>
				</div>

				<!-- Right Panel - Chat Area -->
				<div class="whatsapp-chat-area">
					<div class="whatsapp-chat-header" id="chat-header">
						<div class="empty-state">
							<div class="empty-icon">💬</div>
							<h3>WhatsApp Conversations</h3>
							<p>Select a contact to start chatting</p>
						</div>
					</div>
					<div class="whatsapp-messages" id="messages-container">
						<!-- Messages will be loaded here -->
					</div>
					<div class="whatsapp-input-area" id="input-area" style="display: none;">
						<button class="btn btn-default btn-sm" id="attach-btn" title="Attach file">
							📎
						</button>
						<input type="text" 
							class="form-control" 
							placeholder="Type a message..." 
							id="message-input">
						<button class="btn btn-primary btn-sm" id="send-btn">
							Send
						</button>
					</div>
				</div>
			</div>
		`);

		// Add event listeners
		this.setup_events();
	}

	setup_events() {
		const me = this;

		// Contact search
		$('#contact-search').on('input', function() {
			me.filter_contacts($(this).val());
		});

		// Send message button
		$('#send-btn').on('click', () => this.send_message());

		// Enter key to send
		$('#message-input').on('keypress', function(e) {
			if (e.which === 13 && !e.shiftKey) {
				e.preventDefault();
				me.send_message();
			}
		});

		// Attach file
		$('#attach-btn').on('click', () => this.attach_file());
	}

	load_contacts() {
		const me = this;
		
		frappe.call({
			method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_contacts',
			callback: function(r) {
				if (r.message) {
					me.contacts = r.message;
					me.render_contacts(r.message);
				}
			}
		});
	}

	render_contacts(contacts) {
		const me = this;
		const html = contacts.map(contact => {
			const name = contact.contact_name || contact.mobile_no;
			const initials = this.get_initials(name);
			const lastMsg = contact.last_message || 'No messages yet';
			const time = contact.last_message_date ? 
				moment(contact.last_message_date).fromNow() : '';
			const unread = contact.unread_count > 0 ? 
				`<span class="badge badge-primary">${contact.unread_count}</span>` : '';

			return `
				<div class="contact-item" data-contact="${contact.name}">
					<div class="contact-avatar">${initials}</div>
					<div class="contact-info">
						<div class="contact-header">
							<span class="contact-name">${name}</span>
							<span class="contact-time">${time}</span>
						</div>
						<div class="contact-message">
							${lastMsg}
							${unread}
						</div>
					</div>
				</div>
			`;
		}).join('');

		$('#contacts-list').html(html);

		// Attach click events
		$('.contact-item').on('click', function() {
			const contactId = $(this).data('contact');
			$('.contact-item').removeClass('active');
			$(this).addClass('active');
			me.load_conversation(contactId);
		});
	}

	filter_contacts(query) {
		if (!query) {
			this.render_contacts(this.contacts);
			return;
		}

		const filtered = this.contacts.filter(c => {
			const name = (c.contact_name || c.mobile_no).toLowerCase();
			return name.includes(query.toLowerCase());
		});

		this.render_contacts(filtered);
	}

	load_conversation(contactId) {
		const me = this;
		me.current_contact = me.contacts.find(c => c.name === contactId);

		// Update header
		const name = me.current_contact.contact_name || me.current_contact.mobile_no;
		$('#chat-header').html(`
			<div class="chat-header-content">
				<div class="chat-avatar">${this.get_initials(name)}</div>
				<div class="chat-info">
					<div class="chat-name">${name}</div>
					<div class="chat-phone">${me.current_contact.mobile_no}</div>
				</div>
				<div class="chat-actions">
					<button class="btn btn-sm btn-default" onclick="window.whatsapp_chat.create_lead()" title="Create Lead">
						👤 Create Lead
					</button>
				</div>
			</div>
		`);

		// Show input area
		$('#input-area').show();

		// Load messages
		frappe.call({
			method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_messages',
			args: { contact_id: contactId },
			callback: function(r) {
				if (r.message) {
					me.messages = r.message;
					me.render_messages(r.message);
					me.mark_as_read(contactId);
				}
			}
		});
	}

	render_messages(messages) {
		if (messages.length === 0) {
			$('#messages-container').html(`
				<div class="empty-state">
					<div class="empty-icon">💬</div>
					<p>No messages yet</p>
				</div>
			`);
			return;
		}

		const html = messages.map(msg => {
			const type = msg.type === 'Incoming' ? 'incoming' : 'outgoing';
			const time = moment(msg.creation).format('HH:mm');
			
			let content = '';
			if (msg.attach && msg.content_type === 'image') {
				content = `<img src="${msg.attach}" class="message-image" alt="Image">`;
			} else if (msg.attach) {
				content = `<a href="${msg.attach}" target="_blank">📎 ${msg.content_type}</a>`;
			}
			
			if (msg.message) {
				content += `<div class="message-text">${frappe.utils.escape_html(msg.message)}</div>`;
			}

			return `
				<div class="message ${type}">
					<div class="message-bubble">
						${content}
						<div class="message-time">${time}</div>
					</div>
				</div>
			`;
		}).join('');

		$('#messages-container').html(html);
		
		// Scroll to bottom
		const container = document.getElementById('messages-container');
		container.scrollTop = container.scrollHeight;
	}

	send_message() {
		const message = $('#message-input').val().trim();
		if (!message || !this.current_contact) return;

		const me = this;

		frappe.call({
			method: 'frappe_whatsapp.frappe_whatsapp.api.chat.send_message',
			args: {
				contact_id: me.current_contact.name,
				message: message
			},
			callback: function(r) {
				if (r.message) {
					$('#message-input').val('');
					me.load_conversation(me.current_contact.name);
				}
			}
		});
	}

	attach_file() {
		const me = this;
		
		new frappe.ui.FileUploader({
			folder: 'Home/Attachments',
			on_success: (file) => {
				frappe.call({
					method: 'frappe_whatsapp.frappe_whatsapp.api.chat.send_message',
					args: {
						contact_id: me.current_contact.name,
						message: '',
						file_url: file.file_url
					},
					callback: function(r) {
						if (r.message) {
							me.load_conversation(me.current_contact.name);
						}
					}
				});
			}
		});
	}

	mark_as_read(contactId) {
		frappe.call({
			method: 'frappe_whatsapp.frappe_whatsapp.api.chat.mark_as_read',
			args: { contact_id: contactId }
		});
	}

	create_lead() {
		if (!this.current_contact) return;

		frappe.new_doc('CRM Lead', {
			first_name: this.current_contact.contact_name || '',
			mobile_no: this.current_contact.mobile_no,
			whatsapp_contact: this.current_contact.name
		});
	}

	setup_realtime() {
		const me = this;
		
		frappe.realtime.on('whatsapp_message', function(data) {
			// Refresh contacts list
			me.load_contacts();
			
			// If viewing this conversation, refresh messages
			if (me.current_contact && data.contact === me.current_contact.name) {
				me.load_conversation(me.current_contact.name);
			}
		});
	}

	get_initials(name) {
		if (!name) return '?';
		const parts = name.split(' ');
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return name.substring(0, 2).toUpperCase();
	}

	inject_styles() {
		// Inject CSS directly to avoid asset loading issues
		const css = `
			.whatsapp-container { display: flex; height: calc(100vh - 120px); background: #f0f2f5; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); }
			.whatsapp-sidebar { width: 350px; background: white; border-right: 1px solid #e9edef; display: flex; flex-direction: column; }
			.whatsapp-search { padding: 12px; background: white; border-bottom: 1px solid #e9edef; }
			.whatsapp-search input { border-radius: 8px; padding: 8px 12px; border: 1px solid #e9edef; }
			.whatsapp-contacts { flex: 1; overflow-y: auto; }
			.contact-item { display: flex; align-items: center; padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f0f2f5; transition: background 0.2s; }
			.contact-item:hover { background: #f5f6f6; }
			.contact-item.active { background: #e9edef; }
			.contact-avatar { width: 49px; height: 49px; border-radius: 50%; background: linear-gradient(135deg, #25d366 0%, #128c7e 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 16px; flex-shrink: 0; margin-right: 12px; }
			.contact-info { flex: 1; min-width: 0; }
			.contact-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
			.contact-name { font-weight: 500; font-size: 15px; color: #111b21; }
			.contact-time { font-size: 12px; color: #667781; }
			.contact-message { font-size: 14px; color: #667781; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: flex; justify-content: space-between; align-items: center; }
			.contact-message .badge { background: #25d366; margin-left: 8px; }
			.whatsapp-chat-area { flex: 1; display: flex; flex-direction: column; background: #efeae2; }
			.whatsapp-chat-header { background: #f0f2f5; padding: 12px 20px; border-bottom: 1px solid #e9edef; min-height: 60px; }
			.chat-header-content { display: flex; align-items: center; gap: 12px; }
			.chat-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #25d366 0%, #128c7e 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; }
			.chat-info { flex: 1; }
			.chat-name { font-weight: 500; font-size: 16px; color: #111b21; }
			.chat-phone { font-size: 13px; color: #667781; }
			.chat-actions { display: flex; gap: 8px; }
			.whatsapp-messages { flex: 1; overflow-y: auto; padding: 20px; background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23efeae2" width="100" height="100"/></svg>'); }
			.message { display: flex; margin-bottom: 12px; animation: fadeIn 0.3s; }
			@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
			.message.incoming { justify-content: flex-start; }
			.message.outgoing { justify-content: flex-end; }
			.message-bubble { max-width: 65%; padding: 6px 7px 8px 9px; border-radius: 7.5px; position: relative; box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13); }
			.message.incoming .message-bubble { background: white; }
			.message.outgoing .message-bubble { background: #d9fdd3; }
			.message-text { font-size: 14.2px; line-height: 19px; color: #111b21; word-wrap: break-word; }
			.message-image { max-width: 100%; border-radius: 4px; margin-bottom: 4px; }
			.message-time { font-size: 11px; color: #667781; text-align: right; margin-top: 4px; padding-left: 8px; }
			.whatsapp-input-area { background: #f0f2f5; padding: 10px 16px; display: flex; align-items: center; gap: 8px; }
			.whatsapp-input-area input { flex: 1; border-radius: 21px; padding: 9px 12px; border: 1px solid transparent; background: white; }
			.whatsapp-input-area input:focus { border-color: #25d366; outline: none; }
			.whatsapp-input-area button { border-radius: 50%; min-width: 42px; height: 42px; }
			#send-btn { background: #25d366; border-color: #25d366; }
			#send-btn:hover { background: #20ba5a; }
			.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #667781; }
			.empty-icon { font-size: 64px; margin-bottom: 20px; opacity: 0.5; }
			.empty-state h3 { font-size: 24px; margin-bottom: 8px; color: #41525d; }
			.empty-state p { font-size: 14px; }
			.whatsapp-contacts::-webkit-scrollbar, .whatsapp-messages::-webkit-scrollbar { width: 6px; }
			.whatsapp-contacts::-webkit-scrollbar-thumb, .whatsapp-messages::-webkit-scrollbar-thumb { background-color: rgba(0, 0, 0, 0.2); border-radius: 3px; }
			.whatsapp-contacts::-webkit-scrollbar-thumb:hover, .whatsapp-messages::-webkit-scrollbar-thumb:hover { background-color: rgba(0, 0, 0, 0.3); }
			@media (max-width: 768px) {
				.whatsapp-sidebar { width: 100%; }
				.whatsapp-chat-area { display: none; }
				.whatsapp-sidebar.hidden { display: none; }
				.whatsapp-chat-area.active { display: flex; }
			}
		`;
		$('<style>').text(css).appendTo('head');
	}
}

// Make it globally accessible
frappe.provide('whatsapp_chat');
window.whatsapp_chat = null;

frappe.pages['whatsapp_chat'].on_page_show = function(wrapper) {
	window.whatsapp_chat = wrapper.page.whatsapp_chat;
};
