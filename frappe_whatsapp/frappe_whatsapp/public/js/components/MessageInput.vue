<template>
  <div class="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
    <div class="flex items-end gap-2">
      <!-- Attachment Button -->
      <button
        @click="triggerFileUpload"
        class="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition"
        title="Attach file"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
      </button>

      <!-- Hidden file input -->
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        @change="handleFileSelect"
        accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx"
      />

      <!-- Message Input -->
      <div class="flex-1 relative">
        <textarea
          ref="messageInput"
          v-model="message"
          @keydown.enter.exact="handleEnter"
          @input="handleInput"
          placeholder="Type a message..."
          rows="1"
          class="w-full px-4 py-3 pr-12 bg-gray-100 dark:bg-gray-700 rounded-full text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none max-h-32 overflow-y-auto"
        ></textarea>

        <!-- Emoji Button -->
        <button
          @click="toggleEmojiPicker"
          class="absolute right-3 bottom-3 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
          title="Insert emoji"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>

        <!-- Simple Emoji Picker -->
        <div
          v-if="showEmojiPicker"
          class="absolute bottom-full right-0 mb-2 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 grid grid-cols-8 gap-1"
        >
          <button
            v-for="emoji in commonEmojis"
            :key="emoji"
            @click="insertEmoji(emoji)"
            class="w-8 h-8 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-xl"
          >
            {{ emoji }}
          </button>
        </div>
      </div>

      <!-- Send Button -->
      <button
        @click="sendMessage"
        :disabled="!canSend"
        :class="[
          'p-3 rounded-full transition',
          canSend
            ? 'bg-green-500 hover:bg-green-600 text-white'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
        ]"
        title="Send message"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
        </svg>
      </button>
    </div>

    <!-- File Preview (if file selected) -->
    <div v-if="selectedFile" class="mt-3 p-3 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-between">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span class="text-sm text-gray-700 dark:text-gray-300">{{ selectedFile.name }}</span>
        <span class="text-xs text-gray-500">({{ formatFileSize(selectedFile.size) }})</span>
      </div>
      <button
        @click="clearFile"
        class="text-red-500 hover:text-red-700"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Uploading Indicator -->
    <div v-if="isUploading" class="mt-2 flex items-center gap-2 text-sm text-gray-500">
      <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Uploading...
    </div>
  </div>
</template>

<script>
export default {
  name: 'MessageInput',

  data() {
    return {
      message: '',
      selectedFile: null,
      uploadedFileUrl: null,
      isUploading: false,
      showEmojiPicker: false,
      commonEmojis: [
        '😀', '😂', '❤️', '👍', '👎', '🙏', '🎉', '🔥',
        '👏', '💯', '✅', '❌', '⭐', '💪', '😊', '😢',
        '😡', '😍', '🤔', '👌', '✌️', '🤝', '💼', '📱'
      ]
    };
  },

  computed: {
    canSend() {
      return (this.message.trim().length > 0 || this.selectedFile) && !this.isUploading;
    }
  },

  methods: {
    handleEnter(event) {
      if (!event.shiftKey) {
        event.preventDefault();
        this.sendMessage();
      }
    },

    handleInput() {
      // Auto-resize textarea
      const textarea = this.$refs.messageInput;
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    },

    async sendMessage() {
      if (!this.canSend) return;

      let fileUrl = this.uploadedFileUrl;

      // Upload file if selected
      if (this.selectedFile && !fileUrl) {
        fileUrl = await this.uploadFile();
        if (!fileUrl) return; // Upload failed
      }

      this.$emit('send', {
        message: this.message.trim(),
        file_url: fileUrl
      });

      // Reset
      this.message = '';
      this.selectedFile = null;
      this.uploadedFileUrl = null;
      this.$refs.messageInput.style.height = 'auto';
    },

    triggerFileUpload() {
      this.$refs.fileInput.click();
    },

    async handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;

      this.selectedFile = file;

      // Automatically upload
      await this.uploadFile();

      // Reset file input
      event.target.value = '';
    },

    async uploadFile() {
      if (!this.selectedFile) return null;

      this.isUploading = true;

      try {
        const uploader = new frappe.ui.FileUploader({
          folder: 'Home/Attachments',
          on_success: (file) => {
            this.uploadedFileUrl = file.file_url;
            this.isUploading = false;
            frappe.show_alert({ message: 'File uploaded!', indicator: 'green' });
          }
        });

        uploader.upload_files([this.selectedFile]);

        return new Promise((resolve) => {
          const checkInterval = setInterval(() => {
            if (this.uploadedFileUrl) {
              clearInterval(checkInterval);
              resolve(this.uploadedFileUrl);
            }
            if (!this.isUploading) {
              clearInterval(checkInterval);
              resolve(null);
            }
          }, 100);
        });
      } catch (error) {
        console.error('Upload failed:', error);
        frappe.show_alert({ message: 'Upload failed', indicator: 'red' });
        this.isUploading = false;
        return null;
      }
    },

    clearFile() {
      this.selectedFile = null;
      this.uploadedFileUrl = null;
    },

    toggleEmojiPicker() {
      this.showEmojiPicker = !this.showEmojiPicker;
    },

    insertEmoji(emoji) {
      this.message += emoji;
      this.showEmojiPicker = false;
      this.$refs.messageInput.focus();
    },

    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
  }
};
</script>

<style scoped>
textarea::-webkit-scrollbar {
  width: 4px;
}

textarea::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}
</style>
