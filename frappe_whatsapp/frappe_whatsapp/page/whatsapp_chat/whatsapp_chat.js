frappe.pages['whatsapp_chat'].on_page_load = function(wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'WhatsApp Conversations',
		single_column: true
	});

	// Remove default padding
	page.$body.css('padding', '0');
	
	page.whatsapp_chat = new WhatsAppChatApp(page);
};

class WhatsAppChatApp {
	constructor(page) {
		this.page = page;
		this.contacts = [];
		this.currentContact = null;
		this.messages = [];
		this.isDark = localStorage.getItem('whatsapp_dark_mode') === 'true';
		
		this.injectStyles();
		this.setupLayout();
		this.setupEvents();
		this.loadContacts();
		this.setupRealtime();
	}

	injectStyles() {
		const styles = `
			<style>
				/* Professional WhatsApp-Style Chat Interface */
				.wa-container { display: flex; height: calc(100vh - 120px); background: #f0f2f5; }
				.wa-sidebar { width: 350px; background: white; border-right: 1px solid #e9edef; display: flex; flex-direction: column; }
				.wa-header { padding: 16px; background: #f0f2f5; border-bottom: 1px solid #e9edef; }
				.wa-header-flex { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
				.wa-title { font-size: 20px; font-weight: 600; color: #111b21; }
				.wa-search { position: relative; }
				.wa-search input { width: 100%; padding: 10px 12px 10px 40px; background: #f0f2f5; border: none; border-radius: 8px; font-size: 14px; }
				.wa-search input:focus { outline: 2px solid #25d366; }
				.wa-search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #54656f; }
				.wa-contacts { flex: 1; overflow-y: auto; }
				.wa-contact { display: flex; align-items: center; padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f0f2f5; transition: background 0.2s; }
				.wa-contact:hover { background: #f5f6f6; }
				.wa-contact.active { background: #e9edef; }
				.wa-avatar { width: 49px; height: 49px; border-radius: 50%; background: linear-gradient(135deg, #25d366 0%, #128c7e 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 16px; margin-right: 12px; position: relative; }
				.wa-badge { position: absolute; top: -2px; right: -2px; min-width: 20px; height: 20px; background: #25d366; color: white; border-radius: 10px; font-size: 11px; font-weight: 600; display: flex; align-items: center; justify-content: center; padding: 0 5px; }
				.wa-contact-info { flex: 1; min-width: 0; }
				.wa-contact-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
				.wa-contact-name { font-weight: 500; font-size: 15px; color: #111b21; }
				.wa-contact-time { font-size: 12px; color: #667781; }
				.wa-contact-msg { font-size: 14px; color: #667781; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
				
				.wa-chat { flex: 1; display: flex; flex-direction: column; background: #efeae2; }
				.wa-chat-header { padding: 12px 20px; background: #f0f2f5; border-bottom: 1px solid #e9edef; display: flex; align-items: center; justify-content: space-between; }
				.wa-chat-info { display: flex; align-items: center; gap: 12px; }
				.wa-chat-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #25d366 0%, #128c7e 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; }
				.wa-chat-details h2 { font-size: 16px; font-weight: 500; color: #111b21; margin: 0; }
				.wa-chat-details p { font-size: 13px; color: #667781; margin: 0; }
				.wa-chat-actions button { padding: 8px 16px; background: #25d366; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.2s; }
				.wa-chat-actions button:hover { background: #20ba5a; }
				
				.wa-messages { flex: 1; overflow-y: auto; padding: 20px; }
				.wa-date-divider { display: flex; justify-content: center; margin: 16px 0; }
				.wa-date-badge { background: white; padding: 6px 12px; border-radius: 7.5px; font-size: 12px; color: #667781; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13); }
				.wa-message { display: flex; margin-bottom: 8px; }
				.wa-message.incoming { justify-content: flex-start; }
				.wa-message.outgoing { justify-content: flex-end; }
				.wa-bubble { max-width: 65%; padding: 6px 7px 8px 9px; border-radius: 7.5px; box-shadow: 0 1px 0.5px rgba(0,0,0,0.13); }
				.wa-message.incoming .wa-bubble { background: white; }
				.wa-message.outgoing .wa-bubble { background: #d9fdd3; }
				.wa-msg-text { font-size: 14.2px; line-height: 19px; color: #111b21; word-wrap: break-word; white-space: pre-wrap; }
				.wa-msg-img { max-width: 100%; border-radius: 4px; margin-bottom: 4px; cursor: pointer; }
				.wa-msg-file { display: flex; align-items: center; gap: 8px; padding: 8px; background: #f0f2f5; border-radius: 4px; margin-bottom: 4px; }
				.wa-msg-footer { display: flex; align-items: center; justify-content: flex-end; gap: 4px; margin-top: 4px; }
				.wa-msg-time { font-size: 11px; color: #667781; }
				.wa-check { width: 16px; height: 16px; }
				.wa-check.read { color: #53bdeb; }
				.wa-check.sent { color: #667781; }
				
				.wa-typing { display: flex; gap: 4px; padding: 12px; }
				.wa-typing-dot { width: 8px; height: 8px; background: #667781; border-radius: 50%; animation: typing 1.4s infinite; }
				.wa-typing-dot:nth-child(2) { animation-delay: 0.2s; }
				.wa-typing-dot:nth-child(3) { animation-delay: 0.4s; }
				@keyframes typing { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-10px); } }
				
				.wa-input { padding: 10px 16px; background: #f0f2f5; border-top: 1px solid #e9edef; display: flex; align-items: center; gap: 8px; }
				.wa-input-btn { width: 40px; height: 40px; border: none; background: transparent; color: #54656f; cursor: pointer; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
				.wa-input-btn:hover { background: #e9edef; }
				.wa-input textarea { flex: 1; padding: 10px 12px; background: white; border: 1px solid #e9edef; border-radius: 21px; font-size: 15px; color: #111b21; resize: none; max-height: 100px; font-family: inherit; }
				.wa-input textarea:focus { outline: none; border-color: #25d366; }
				.wa-send-btn { width: 40px; height: 40px; border: none; background: #25d366; color: white; cursor: pointer; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
				.wa-send-btn:hover { background: #20ba5a; }
				.wa-send-btn:disabled { background: #e9edef; cursor: not-allowed; }
				
				.wa-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #667781; }
				.wa-empty-icon { font-size: 64px; margin-bottom: 16px; opacity: 0.5; }
				.wa-empty h3 { font-size: 24px; margin-bottom: 8px; color: #41525d; }
				
				.wa-dark-toggle { width: 40px; height: 40px; border: none; background: transparent; cursor: pointer; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
				.wa-dark-toggle:hover { background: #e9edef; }
				
				/* Dark Mode */
				.wa-container.dark { background: #111b21; }
				.wa-container.dark .wa-sidebar { background: #111b21; border-color: #2a3942; }
				.wa-container.dark .wa-header { background: #1f2c33; border-color: #2a3942; }
				.wa-container.dark .wa-title { color: #e9edef; }
				.wa-container.dark .wa-search input { background: #2a3942; color: #e9edef; }
				.wa-container.dark .wa-contact { border-color: #2a3942; }
				.wa-container.dark .wa-contact:hover { background: #1f2c33; }
				.wa-container.dark .wa-contact.active { background: #2a3942; }
				.wa-container.dark .wa-contact-name { color: #e9edef; }
				.wa-container.dark .wa-chat { background: #0b141a; }
				.wa-container.dark .wa-chat-header { background: #1f2c33; border-color: #2a3942; }
				.wa-container.dark .wa-chat-details h2 { color: #e9edef; }
				.wa-container.dark .wa-message.incoming .wa-bubble { background: #1f2c33; }
				.wa-container.dark .wa-message.outgoing .wa-bubble { background: #005c4b; }
				.wa-container.dark .wa-msg-text { color: #e9edef; }
				.wa-container.dark .wa-date-badge { background: #1f2c33; }
				.wa-container.dark .wa-input { background: #1f2c33; border-color: #2a3942; }
				.wa-container.dark .wa-input textarea { background: #2a3942; border-color: #2a3942; color: #e9edef; }
				
				/* Scrollbar */
				.wa-contacts::-webkit-scrollbar, .wa-messages::-webkit-scrollbar { width: 6px; }
				.wa-contacts::-webkit-scrollbar-thumb, .wa-messages::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.2); border-radius: 3px; }
			</style>
		`;
		$(styles).appendTo('head');
	}

	setupLayout() {
		const darkClass = this.isDark ? 'dark' : '';
		$(this.page.body).html(`
			<div class="wa-container ${darkClass}" id="wa-app">
				<div class="wa-sidebar">
					<div class="wa-header">
						<div class="wa-header-flex">
							<div class="wa-title">WhatsApp</div>
							<button class="wa-dark-toggle" id="dark-toggle">
								${this.isDark ? '☀️' : '🌙'}
							</button>
						</div>
						<div class="wa-search">
							<span class="wa-search-icon">🔍</span>
							<input type="text" placeholder="Search contacts..." id="contact-search">
						</div>
					</div>
					<div class="wa-contacts" id="contacts-list"></div>
				</div>
				<div class="wa-chat" id="chat-area">
					<div class="wa-empty">
						<div class="wa-empty-icon">💬</div>
						<h3>WhatsApp Conversations</h3>
						<p>Select a contact to start chatting</p>
					</div>
				</div>
			</div>
		`);
	}

	setupEvents() {
		$('#contact-search').on('input', (e) => this.filterContacts($(e.target).val()));
		$('#dark-toggle').on('click', () => this.toggleDarkMode());
	}

	async loadContacts() {
		try {
			const res = await frappe.call({ method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_contacts' });
			if (res.message) {
				this.contacts = res.message;
				this.renderContacts(res.message);
			}
		} catch (err) {
			console.error('Failed to load contacts:', err);
		}
	}

	renderContacts(contacts) {
		const html = contacts.map(c => {
			const name = c.contact_name || c.mobile_no;
			const initials = this.getInitials(name);
			const time = c.last_message_date ? moment(c.last_message_date).fromNow() : '';
			const badge = c.unread_count > 0 ? `<span class="wa-badge">${c.unread_count}</span>` : '';
			return `
				<div class="wa-contact" data-id="${c.name}">
					<div class="wa-avatar">${initials}${badge}</div>
					<div class="wa-contact-info">
						<div class="wa-contact-header">
							<span class="wa-contact-name">${name}</span>
							<span class="wa-contact-time">${time}</span>
						</div>
						<div class="wa-contact-msg">${c.last_message || 'No messages yet'}</div>
					</div>
				</div>
			`;
		}).join('');
		
		$('#contacts-list').html(html);
		$('.wa-contact').on('click', (e) => {
			const id = $(e.currentTarget).data('id');
			this.selectContact(id);
		});
	}

	filterContacts(query) {
		if (!query) {
			this.renderContacts(this.contacts);
			return;
		}
		const filtered = this.contacts.filter(c => 
			(c.contact_name || c.mobile_no).toLowerCase().includes(query.toLowerCase())
		);
		this.renderContacts(filtered);
	}

	async selectContact(id) {
		$('.wa-contact').removeClass('active');
		$(`.wa-contact[data-id="${id}"]`).addClass('active');
		
		this.currentContact = this.contacts.find(c => c.name === id);
		if (!this.currentContact) return;

		const name = this.currentContact.contact_name || this.currentContact.mobile_no;
		const initials = this.getInitials(name);

		$('#chat-area').html(`
			<div class="wa-chat-header">
				<div class="wa-chat-info">
					<div class="wa-chat-avatar">${initials}</div>
					<div class="wa-chat-details">
						<h2>${name}</h2>
						<p>${this.currentContact.mobile_no}</p>
					</div>
				</div>
				<div class="wa-chat-actions">
					<button id="create-lead-btn">👤 Create Lead</button>
				</div>
			</div>
			<div class="wa-messages" id="messages-area"></div>
			<div class="wa-input">
				<button class="wa-input-btn" id="attach-btn">📎</button>
				<textarea placeholder="Type a message..." id="msg-input" rows="1"></textarea>
				<button class="wa-send-btn" id="send-btn">➤</button>
			</div>
		`);

		$('#create-lead-btn').on('click', () => this.createLead());
		$('#send-btn').on('click', () => this.sendMessage());
		$('#attach-btn').on('click', () => this.attachFile());
		$('#msg-input').on('keydown', (e) => {
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				this.sendMessage();
			}
		});

		await this.loadMessages(id);
	}

	async loadMessages(contactId) {
		try {
			const res = await frappe.call({
				method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_messages',
				args: { contact_id: contactId }
			});
			
			if (res.message) {
				this.messages = res.message;
				this.renderMessages(res.message);
				
				await frappe.call({
					method: 'frappe_whatsapp.frappe_whatsapp.api.chat.mark_as_read',
					args: { contact_id: contactId }
				});
			}
		} catch (err) {
			console.error('Failed to load messages:', err);
		}
	}

	renderMessages(messages) {
		const grouped = {};
		messages.forEach(m => {
			const date = new Date(m.creation).toDateString();
			if (!grouped[date]) grouped[date] = [];
			grouped[date].push(m);
		});

		let html = '';
		Object.keys(grouped).forEach(date => {
			html += `<div class="wa-date-divider"><span class="wa-date-badge">${this.formatDate(date)}</span></div>`;
			grouped[date].forEach(m => {
				const type = m.type === 'Incoming' ? 'incoming' : 'outgoing';
				const time = moment(m.creation).format('HH:mm');
				let content = '';
				
				if (m.attach && m.content_type === 'image') {
					content = `<img src="${m.attach}" class="wa-msg-img">`;
				} else if (m.attach) {
					content = `<div class="wa-msg-file">📄 <a href="${m.attach}" target="_blank">${m.content_type}</a></div>`;
				}
				
				if (m.message) {
					content += `<div class="wa-msg-text">${frappe.utils.escape_html(m.message)}</div>`;
				}

				const checkmark = type === 'outgoing' ? '<span class="wa-check sent">✓✓</span>' : '';
				
				html += `
					<div class="wa-message ${type}">
						<div class="wa-bubble">
							${content}
							<div class="wa-msg-footer">
								<span class="wa-msg-time">${time}</span>
								${checkmark}
							</div>
						</div>
					</div>
				`;
			});
		});

		$('#messages-area').html(html);
		$('#messages-area').scrollTop($('#messages-area')[0].scrollHeight);
	}

	async sendMessage() {
		const text = $('#msg-input').val().trim();
		if (!text || !this.currentContact) return;

		try {
			await frappe.call({
				method: 'frappe_whatsapp.frappe_whatsapp.api.chat.send_message',
				args: {
					contact_id: this.currentContact.name,
					message: text
				}
			});

			$('#msg-input').val('');
			await this.loadMessages(this.currentContact.name);
		} catch (err) {
			frappe.show_alert({ message: 'Failed to send message', indicator: 'red' });
		}
	}

	attachFile() {
		new frappe.ui.FileUploader({
			folder: 'Home/Attachments',
			on_success: async (file) => {
				try {
					await frappe.call({
						method: 'frappe_whatsapp.frappe_whatsapp.api.chat.send_message',
						args: {
							contact_id: this.currentContact.name,
							message: '',
							file_url: file.file_url
						}
					});
					await this.loadMessages(this.currentContact.name);
				} catch (err) {
					frappe.show_alert({ message: 'Failed to send file', indicator: 'red' });
				}
			}
		});
	}

	createLead() {
		if (!this.currentContact) return;
		frappe.new_doc('CRM Lead', {
			first_name: this.currentContact.contact_name || '',
			mobile_no: this.currentContact.mobile_no,
			whatsapp_contact: this.currentContact.name
		});
	}

	setupRealtime() {
		frappe.realtime.on('whatsapp_message', (data) => {
			this.loadContacts();
			if (this.currentContact && data.contact === this.currentContact.name) {
				this.loadMessages(this.currentContact.name);
			}
		});
	}

	toggleDarkMode() {
		this.isDark = !this.isDark;
		localStorage.setItem('whatsapp_dark_mode', this.isDark);
		$('#wa-app').toggleClass('dark', this.isDark);
		$('#dark-toggle').html(this.isDark ? '☀️' : '🌙');
	}

	getInitials(name) {
		if (!name) return '?';
		const parts = name.split(' ');
		if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
		return name.substring(0, 2).toUpperCase();
	}

	formatDate(dateStr) {
		const date = new Date(dateStr);
		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		if (date.toDateString() === today.toDateString()) return 'Today';
		if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
}
