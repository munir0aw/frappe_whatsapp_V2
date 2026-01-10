// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Contact', {
	refresh: function(frm) {
		// Add custom buttons
		if (!frm.is_new()) {
			// Convert to Lead button
			if (!frm.doc.converted_to_lead) {
				frm.add_custom_button(__('Convert to Lead'), function() {
					frappe.confirm(
						'Are you sure you want to convert this contact to a CRM Lead?',
						function() {
							frm.call({
								method: 'convert_to_lead',
								doc: frm.doc,
								callback: function(r) {
									if (r.message) {
										frm.reload_doc();
										frappe.set_route('Form', 'CRM Lead', r.message);
									}
								}
							});
						}
					);
				}, __('Actions'));
			}
			
			// Mark as Read button
			if (frm.doc.unread_count > 0) {
				frm.add_custom_button(__('Mark as Read'), function() {
					frm.call({
						method: 'mark_as_read',
						doc: frm.doc,
						callback: function() {
							frm.reload_doc();
						}
					});
				}, __('Actions'));
			}
			
			// View Messages button
			frm.add_custom_button(__('View Messages'), function() {
				frappe.set_route('List', 'WhatsApp Message', {
					'reference_doctype': 'WhatsApp Contact',
					'reference_name': frm.doc.name
				});
			}, __('Actions'));
		}
		
		// Highlight unread count
		if (frm.doc.unread_count > 0) {
			frm.dashboard.add_indicator(__('Unread: {0}', [frm.doc.unread_count]), 'orange');
		}
		
		// Show conversion status
		if (frm.doc.converted_to_lead && frm.doc.lead_reference) {
			frm.dashboard.add_indicator(__('Converted to Lead'), 'green');
		}
	},
	
	mobile_no: function(frm) {
		// Format mobile number
		if (frm.doc.mobile_no) {
			// Remove spaces and special characters except +
			let cleaned = frm.doc.mobile_no.replace(/[^\d+]/g, '');
			if (cleaned !== frm.doc.mobile_no) {
				frm.set_value('mobile_no', cleaned);
			}
		}
	},
	
	qualification_status: function(frm) {
		// Set qualified date when status changes to Qualified
		if (frm.doc.qualification_status === 'Qualified' && !frm.doc.qualified_date) {
			frm.set_value('qualified_date', frappe.datetime.now_datetime());
		}
	}
});
