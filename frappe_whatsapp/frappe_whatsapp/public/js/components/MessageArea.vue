<template>
  <div class="flex flex-col h-full">
    <!-- Chat Header -->
    <div class="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center text-white font-semibold">
          {{ getInitials(contact.contact_name || contact.mobile_no) }}
        </div>
        <div>
          <h2 class="font-medium text-gray-900 dark:text-white">
            {{ contact.contact_name || contact.mobile_no }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {{ contact.mobile_no }}
          </p>
        </div>
      </div>
      
      <div class="flex items-center gap-2">
        <!-- Create Lead Button -->
        <button
          @click="$emit('create-lead')"
          class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Create Lead
        </button>
      </div>
    </div>

    <!-- Messages Area with Virtual Scrolling -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-6 py-4 space-y-4"
      @scroll="handleScroll"
    >
      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="space-y-4">
        <div v-for="i in 5" :key="i" class="flex" :class="i % 2 === 0 ? 'justify-end' : 'justify-start'">
          <div class="w-64 h-16 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"></div>
        </div>
      </div>

      <!-- Date Grouping -->
      <div v-else v-for="(group, date) in groupedMessages" :key="date">
        <!-- Date Header (Sticky) -->
        <div class="sticky top-0 z-10 flex justify-center mb-4">
          <span class="px-3 py-1 bg-white dark:bg-gray-800 rounded-full text-xs text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 shadow-sm">
            {{ formatDate(date) }}
          </span>
        </div>

        <!-- Messages -->
        <div
          v-for="(message, index) in group"
          :key="message.name"
          :class="[
            'flex mb-2 group',
            message.type === 'Outgoing' ? 'justify-end' : 'justify-start'
          ]"
        >
          <div :class="['max-w-[65%] relative', message.type === 'Outgoing' ? 'items-end' : 'items-start']">
            <!-- Message Bubble -->
            <div
              :class="[
                'rounded-lg px-3 py-2 shadow-sm transition-all hover:shadow-md',
                message.type === 'Outgoing'
                  ? 'bg-green-100 dark:bg-green-900 text-gray-900 dark:text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white'
              ]"
            >
              <!-- Image Attachment -->
              <div v-if="message.attach && message.content_type === 'image'" class="mb-2">
                <img
                  :src="message.attach"
                  :alt="message.message || 'Image'"
                  class="rounded-lg max-w-full cursor-pointer hover:opacity-90 transition"
                  @click="openImagePreview(message.attach)"
                />
              </div>

              <!-- File Attachment -->
              <div v-else-if="message.attach" class="flex items-center gap-2 mb-2 p-2 bg-gray-50 dark:bg-gray-700 rounded">
                <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <a :href="message.attach" target="_blank" class="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                  {{ message.content_type }}
                </a>
              </div>

              <!-- Message Text -->
              <div v-if="message.message" class="text-sm leading-relaxed whitespace-pre-wrap break-words">
                {{ message.message }}
              </div>

              <!-- Message Footer -->
              <div class="flex items-center justify-end gap-1 mt-1">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ formatMessageTime(message.creation) }}
                </span>

                <!-- Message Status (for outgoing messages) -->
                <div v-if="message.type === 'Outgoing'" class="flex items-center">
                  <!-- Sent (single checkmark) -->
                  <svg v-if="message.status === 'Sent'" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  
                  <!-- Delivered (double checkmark) -->
                  <svg v-else-if="message.status === 'Delivered'" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <g>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 13l4 4L17 7" transform="translate(2,0)" />
                    </g>
                  </svg>

                  <!-- Read (blue double checkmark) -->
                  <svg v-else-if="message.status === 'Read'" class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <g>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 13l4 4L17 7" transform="translate(2,0)" />
                    </g>
                  </svg>
                </div>
              </div>

              <!-- Message Reactions -->
              <div v-if="message.reactions && message.reactions.length > 0" class="flex gap-1 mt-2">
                <span
                  v-for="reaction in message.reactions"
                  :key="reaction"
                  class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded-full text-xs"
                >
                  {{ reaction }}
                </span>
              </div>
            </div>

            <!-- Quick Actions (shown on hover) -->
            <div class="absolute top-0 -right-20 hidden group-hover:flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                @click="reactToMessage(message, '👍')"
                class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                title="React"
              >
                <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Typing Indicator -->
      <div v-if="isTyping" class="flex justify-start mb-4">
        <div class="bg-white dark:bg-gray-800 rounded-lg px-4 py-3 shadow-sm">
          <div class="flex gap-1">
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0s"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>
      </div>

      <!-- Auto-scroll anchor -->
      <div ref="scrollAnchor"></div>
    </div>

    <!-- Message Input -->
    <MessageInput @send="handleSend" />
  </div>
</template>

<script>
import MessageInput from './MessageInput.vue';

export default {
  name: 'MessageArea',
  components: {
    MessageInput
  },

  props: {
    contact: {
      type: Object,
      required: true
    },
    messages: {
      type: Array,
      default: () => []
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    isTyping: {
      type: Boolean,
      default: false
    }
  },

  computed: {
    groupedMessages() {
      const groups = {};
      
      this.messages.forEach(message => {
        const date = new Date(message.creation).toDateString();
        if (!groups[date]) {
          groups[date] = [];
        }
        groups[date].push(message);
      });

      return groups;
    }
  },

  watch: {
    messages: {
      handler() {
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      },
      deep: true
    }
  },

  mounted() {
    this.scrollToBottom();
  },

  methods: {
    handleSend(data) {
      this.$emit('send-message', data);
    },

    handleScroll(event) {
      // Implement lazy loading here if needed
      const { scrollTop, scrollHeight, clientHeight } = event.target;
      if (scrollTop === 0) {
        // Load more messages
      }
    },

    scrollToBottom() {
      if (this.$refs.scrollAnchor) {
        this.$refs.scrollAnchor.scrollIntoView({ behavior: 'smooth' });
      }
    },

    openImagePreview(url) {
      // Open in lightbox
      window.open(url, '_blank');
    },

    reactToMessage(message, emoji) {
      // Add reaction to message (implement backend support)
      if (!message.reactions) {
        message.reactions = [];
      }
      if (!message.reactions.includes(emoji)) {
        message.reactions.push(emoji);
      }
      frappe.show_alert({ message: 'Reaction added!', indicator: 'green' });
    },

    getInitials(name) {
      if (!name) return '?';
      const parts = name.split(' ');
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return name.substring(0, 2).toUpperCase();
    },

    formatDate(dateString) {
      const date = new Date(dateString);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);

      if (date.toDateString() === today.toDateString()) {
        return 'Today';
      } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }
    },

    formatMessageTime(dateString) {
      const date = new Date(dateString);
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
  }
};
</script>

<style scoped>
@keyframes bounce {
  0%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-8px);
  }
}

.animate-bounce {
  animation: bounce 1.4s infinite;
}
</style>
