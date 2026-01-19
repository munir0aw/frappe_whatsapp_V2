// Frappe API utility for ES modules
// Uses fetch() instead of window.frappe for compatibility

export const frappeCall = async (method, args = {}) => {
  try {
    const response = await fetch(`/api/method/${method}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': getCsrfToken(),
      },
      credentials: 'include',
      body: JSON.stringify(args),
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Frappe API call failed:', error);
    throw error;
  }
};

export const showAlert = (message, indicator = 'blue') => {
  // Fallback to console if frappe.show_alert not available
  if (window.frappe?.show_alert) {
    window.frappe.show_alert({ message, indicator });
  } else {
    console.log(`[${indicator.toUpperCase()}] ${message}`);
  }
};

export const newDoc = (doctype, doc = {}) => {
  if (window.frappe?.new_doc) {
    window.frappe.new_doc(doctype, doc);
  } else {
    // Fallback: navigate to new doc form
    window.location.href = `/app/${doctype.toLowerCase().replace(/ /g, '-')}/new`;
  }
};

export const setupRealtime = (event, callback) => {
  if (window.frappe?.realtime?.on) {
    window.frappe.realtime.on(event, callback);
  } else {
    console.warn('Realtime not available');
  }
};

// Get CSRF token from cookie or meta tag
const getCsrfToken = () => {
  // First try window.frappe (when available)
  if (typeof window !== 'undefined' && window.frappe && window.frappe.csrf_token) {
    return window.frappe.csrf_token;
  }
  
  // Try to get from cookie
  if (typeof document !== 'undefined') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrf_token') {
        return decodeURIComponent(value);
      }
    }
    
    // Try to get from meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
      return meta.getAttribute('content');
    }
  }
  
  return '';
};

export const FileUploader = window.frappe?.ui?.FileUploader || class {
  constructor(options) {
    console.warn('File uploader not available');
    this.options = options;
  }
  
  upload_files(files) {
    console.warn('Upload functionality not available');
  }
};
