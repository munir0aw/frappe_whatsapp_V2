import { createApp } from 'vue';
import ChatApp from './components/ChatApp.vue';

// Initialize Vue 3 app for WhatsApp Chat
// Initialize Vue 3 app for WhatsApp Chat
window.initWhatsAppChat = function(wrapper) {
	const app = createApp(ChatApp);
	
	// Mount Vue app to the wrapper
	const mountPoint = document.createElement('div');
	mountPoint.id = 'whatsapp-chat-app';
	wrapper.appendChild(mountPoint);
	
	app.mount(mountPoint);
	
	return app;
}
