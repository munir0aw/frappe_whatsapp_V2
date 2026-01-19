<template>
  <div :class="['chat-app', { 'dark': isDark }]" class="flex h-screen bg-white dark:bg-gray-900 overflow-hidden">
    <!-- Sidebar -->
    <div class="w-[400px] bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full relative z-10 shadow-sm">
      <!-- Sidebar Header -->
      <div class="p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">Messages</h1>
          <div class="flex gap-2">
            <!-- New Chat Button -->
            <button class="p-2 text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors" title="New Chat">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
            </button>
            <button @click="toggleDarkMode" class="p-2 text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors" :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'">
              <svg v-if="!isDark" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
              <svg v-else class="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
            </button>
          </div>
        </div>

        <!-- Search Bar -->
        <div class="relative group">
          <input 
            type="text" 
            v-model="searchQuery" 
            @input="filterContacts" 
            placeholder="Search or start new chat" 
            class="w-full pl-10 pr-4 py-2.5 bg-gray-100 dark:bg-gray-700 border-none rounded-xl text-sm focus:ring-2 focus:ring-green-500/50 transition-all dark:text-gray-200 placeholder-gray-500"
          >
          <svg class="w-5 h-5 text-gray-400 absolute left-3 top-2.5 transition-colors group-focus-within:text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </div>
      </div>

      <!-- Contact List -->
      <div class="flex-1 overflow-y-auto custom-scrollbar">
        <div v-if="filteredContacts.length > 0" class="flex flex-col">
          <div 
            v-for="contact in filteredContacts" 
            :key="contact.name"
            @click="selectContact(contact)"
            :class="[
              'group flex items-center p-3 mx-2 my-1 rounded-xl cursor-pointer transition-all duration-200',
              currentContact?.name === contact.name 
                ? 'bg-green-50 dark:bg-green-900/20' 
                : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'
            ]"
          >
            <!-- Avatar -->
            <div class="relative flex-shrink-0">
              <div class="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold bg-gradient-to-br from-gray-300 to-gray-400 dark:from-gray-600 dark:to-gray-700 shadow-sm group-hover:shadow-md transition-shadow">
                {{ getInitials(contact.contact_name || contact.mobile_no) }}
              </div>
              <div v-if="contact.unread_count > 0" class="absolute -top-1 -right-1 w-5 h-5 bg-green-500 border-2 border-white dark:border-gray-800 rounded-full flex items-center justify-center">
                <span class="text-[10px] font-bold text-white">{{ contact.unread_count }}</span>
              </div>
            </div>

            <!-- Content -->
            <div class="flex-1 ml-3 min-w-0">
              <div class="flex justify-between items-baseline mb-0.5">
                <span :class="['font-semibold truncate text-[15px]', currentContact?.name === contact.name ? 'text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-200']">
                  {{ contact.contact_name || contact.mobile_no }}
                </span>
                <span :class="['text-[11px]', contact.unread_count > 0 ? 'text-green-600 font-semibold' : 'text-gray-400']">
                  {{ formatTime(contact.last_message_date) }}
                </span>
              </div>
              <p :class="['truncate text-[13px] leading-5', contact.unread_count > 0 ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-500 dark:text-gray-400']">
                {{ contact.last_message || 'Start a conversation' }}
              </p>
            </div>
          </div>
        </div>
        
        <!-- No Results -->
        <div v-else class="flex flex-col items-center justify-center h-64 text-gray-400 px-6 text-center">
          <div class="w-16 h-16 bg-gray-50 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          </div>
          <p class="text-sm font-medium text-gray-500">No contacts found</p>
          <p class="text-xs text-gray-400 mt-1">Try searching for a name or number</p>
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col h-full bg-[#efeae2] dark:bg-[#0b141a] relative">
      <!-- Background Pattern -->
      <div class="absolute inset-0 bg-chat-pattern opacity-[0.06] pointer-events-none"></div>

      <MessageArea
        v-if="currentContact"
        :contact="currentContact"
        :messages="messages"
        :is-loading="isLoadingMessages"
        :is-typing="isTyping"
        @send-message="handleSendMessage"
        @create-lead="handleCreateLead"
        class="relative z-10 h-full"
      />
      
      <!-- Empty State -->
      <div v-else class="relative z-10 flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/50 dark:bg-[#0b141a]/95 backdrop-blur-sm">
        <div class="max-w-md">
          <img src="https://static.whatsapp.net/rsrc.php/v3/y6/r/wa669ae.svg" alt="WhatsApp Web" class="w-24 h-24 mx-auto mb-8 opacity-60 dark:opacity-40">
          <h1 class="text-3xl font-light text-gray-700 dark:text-gray-200 mb-4">WhatsApp for Frappe</h1>
          <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed max-w-sm mx-auto">
            Send and receive messages without keeping your phone online.<br>
            Use WhatsApp on up to 4 linked devices and 1 phone.
          </p>
          <div class="mt-8 flex items-center justify-center gap-2 text-xs text-gray-400">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9v-2h2v2zm0-4H9V7h2v5z"/></svg>
            End-to-end encrypted
          </div>
        </div>
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
