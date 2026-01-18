frappe.pages['whatsapp_chat'].on_page_load = function(wrapper) {
	// Import and initialize Vue app
	import('./whatsapp_chat.bundle.js').then(module => {
		module.initWhatsAppChat(wrapper);
	});
};
