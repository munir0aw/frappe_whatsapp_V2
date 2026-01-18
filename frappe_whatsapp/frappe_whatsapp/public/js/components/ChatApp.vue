<template>
  <div :class="['chat-app', { 'dark': isDark }]" class="flex h-screen bg-gray-100 dark:bg-gray-900">
    <!-- Sidebar: Contact List -->
    <div class="w-96 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      <!-- Header -->
      <div class="p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between mb-3">
          <h1 class="text-xl font-semibold text-gray-900 dark:text-white">WhatsApp</h1>
          <div class="flex items-center gap-2">
            <!-- Dark Mode Toggle -->
            <button @click="toggleDarkMode" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition">
              <svg v-if="!isDark" class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
              <svg v-else class="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </button>
          </div>
        </div>
        
        <!-- Search -->
        <div class="relative">
          <input
            type="text"
            v-model="searchQuery"
            @input="filterContacts"
            placeholder="Search contacts..."
            class="w-full px-4 py-2 pl-10 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <svg class="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <!-- Contact List with Virtual Scrolling -->
      <div class="flex-1 overflow-y-auto">
        <div
          v-for="contact in filteredContacts"
          :key="contact.name"
          @click="selectContact(contact)"
          :class="[
            'flex items-center px-4 py-3 cursor-pointer border-b border-gray-100 dark:border-gray-700 transition',
            currentContact?.name === contact.name 
              ? 'bg-gray-100 dark:bg-gray-700' 
              : 'hover:bg-gray-50 dark:hover:bg-gray-750'
          ]"
        >
          <!-- Avatar -->
          <div class="relative">
            <div class="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center text-white font-semibold text-sm">
              {{ getInitials(contact.contact_name || contact.mobile_no) }}
            </div>
            <div v-if="contact.unread_count > 0" class="absolute -top-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
              {{ contact.unread_count }}
            </div>
          </div>

          <!-- Contact Info -->
          <div class="flex-1 ml-3 min-w-0">
            <div class="flex items-center justify-between mb-1">
              <span class="font-medium text-gray-900 dark:text-white truncate">
                {{ contact.contact_name || contact.mobile_no }}
              </span>
              <span class="text-xs text-gray-500 dark:text-gray-400">
                {{ formatTime(contact.last_message_date) }}
              </span>
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-400 truncate">
              {{ contact.last_message || 'No messages yet' }}
            </p>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredContacts.length === 0" class="flex flex-col items-center justify-center h-64 text-gray-400">
          <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p>No contacts found</p>
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col bg-chat-pattern dark:bg-gray-900">
      <MessageArea
        v-if="currentContact"
        :contact="currentContact"
        :messages="messages"
        :is-loading="isLoadingMessages"
        :is-typing="isTyping"
        @send-message="handleSendMessage"
        @create-lead="handleCreateLead"
      />
      
      <!-- Empty State -->
      <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400">
        <svg class="w-32 h-32 mb-4 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <h3 class="text-2xl font-medium text-gray-600 dark:text-gray-400 mb-2">WhatsApp Conversations</h3>
        <p class="text-gray-500 dark:text-gray-500">Select a contact to start chatting</p>
      </div>
    </div>
  </div>
</template>

<script>
import MessageArea from './MessageArea.vue';

export default {
  name: 'ChatApp',
  components: {
    MessageArea
  },
  
  data() {
    return {
      contacts: [],
      filteredContacts: [],
      currentContact: null,
      messages: [],
      searchQuery: '',
      isDark: false,
      isLoadingMessages: false,
      isTyping: false
    };
  },

  mounted() {
    this.loadContacts();
    this.setupRealtime();
    this.loadDarkModePreference();
  },

  methods: {
    async loadContacts() {
      try {
        const response = await frappe.call({
          method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_contacts'
        });
        
        if (response.message) {
          this.contacts = response.message;
          this.filteredContacts = [...this.contacts];
        }
      } catch (error) {
        console.error('Failed to load contacts:', error);
        frappe.show_alert({ message: 'Failed to load contacts', indicator: 'red' });
      }
    },

    filterContacts() {
      if (!this.searchQuery.trim()) {
        this.filteredContacts = [...this.contacts];
        return;
      }

      const query = this.searchQuery.toLowerCase();
      this.filteredContacts = this.contacts.filter(contact => {
        const name = (contact.contact_name || contact.mobile_no).toLowerCase();
        return name.includes(query);
      });
    },

    async selectContact(contact) {
      this.currentContact = contact;
      this.isLoadingMessages = true;

      try {
        const response = await frappe.call({
          method: 'frappe_whatsapp.frappe_whatsapp.api.chat.get_messages',
          args: { contact_id: contact.name }
        });

        if (response.message) {
          this.messages = response.message;
          
          // Mark as read
          await frappe.call({
            method: 'frappe_whatsapp.frappe_whatsapp.api.chat.mark_as_read',
            args: { contact_id: contact.name }
          });

          // Update unread count locally
          contact.unread_count = 0;
        }
      } catch (error) {
        console.error('Failed to load messages:', error);
        frappe.show_alert({ message: 'Failed to load messages', indicator: 'red' });
      } finally {
        this.isLoadingMessages = false;
      }
    },

    async handleSendMessage(messageData) {
      try {
        const response = await frappe.call({
          method: 'frappe_whatsapp.frappe_whatsapp.api.chat.send_message',
          args: {
            contact_id: this.currentContact.name,
            message: messageData.message,
            file_url: messageData.file_url
          }
        });

        if (response.message) {
          // Reload messages
          await this.selectContact(this.currentContact);
        }
      } catch (error) {
        console.error('Failed to send message:', error);
        frappe.show_alert({ message: 'Failed to send message', indicator: 'red' });
      }
    },

    handleCreateLead() {
      if (!this.currentContact) return;

      frappe.new_doc('CRM Lead', {
        first_name: this.currentContact.contact_name || '',
        mobile_no: this.currentContact.mobile_no,
        whatsapp_contact: this.currentContact.name
      });
    },

    setupRealtime() {
      frappe.realtime.on('whatsapp_message', (data) => {
        // Refresh contacts list
        this.loadContacts();

        // If viewing this conversation, refresh messages
        if (this.currentContact && data.contact === this.currentContact.name) {
          this.selectContact(this.currentContact);
        }
      });
    },

    toggleDarkMode() {
      this.isDark = !this.isDark;
      localStorage.setItem('whatsapp_dark_mode', this.isDark);
      document.documentElement.classList.toggle('dark', this.isDark);
    },

    loadDarkModePreference() {
      const saved = localStorage.getItem('whatsapp_dark_mode');
      this.isDark = saved === 'true';
      document.documentElement.classList.toggle('dark', this.isDark);
    },

    getInitials(name) {
      if (!name) return '?';
      const parts = name.split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    },

    formatTime(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const now = new Date();
      const diff = now - date;
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));

      if (days === 0) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      } else if (days === 1) {
        return 'Yesterday';
      } else if (days < 7) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
    }
  }
};
</script>

<style scoped>
.bg-chat-pattern {
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23efeae2" width="100" height="100"/></svg>');
}

.dark .bg-chat-pattern {
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%231f2937" width="100" height="100"/></svg>');
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}

.dark ::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.2);
}

.dark ::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.3);
}
</style>
