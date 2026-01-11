// frappe.Chat
// Author - Nihal Mittal <nihal@erpnext.com>

import {
  ChatBubble,
  ChatList,
  ChatSpace,
  ChatWelcome,
  get_settings,
  scroll_to_bottom,
} from './components';

frappe.provide('frappe.Chat');
frappe.provide('frappe.Chat.settings');

/** Spawns a chat widget on any web page */
frappe.Chat = class {
  constructor() {
    this.setup_app();
  }

  /** Create all the required elements for chat widget */
  create_app() {
    this.$app_element = $(document.createElement('div'));
    this.$app_element.addClass('chat-app');
    this.$chat_container = $(document.createElement('div'));
    this.$chat_container.addClass('chat-container');
    $('body').append(this.$app_element);
    this.is_open = false;

    this.$chat_element = $(document.createElement('div'))
      .addClass('chat-element')
      .hide();

    this.$chat_element.append(`
			<span class="chat-cross-button">
				${frappe.utils.icon('close', 'lg')}
			</span>
		`);
    this.$chat_element.append(this.$chat_container);
    this.$chat_element.appendTo(this.$app_element);

    this.chat_bubble = new ChatBubble(this);
    this.chat_bubble.render();

    const navbar_icon_html = `
        <li class='nav-item dropdown dropdown-notifications 
          dropdown-mobile chat-navbar-icon' title="Show Chats" >
          ${frappe.utils.icon('small-message', 'md')}
          <span class="badge" id="chat-notification-count"></span>
        </li>
    `;

    if (this.is_desk === true) {
      $('header.navbar > .container > .navbar-collapse > ul').prepend(
        navbar_icon_html
      );
    }
    this.setup_events();
  }

  /** Load dependencies and fetch the settings */
  async setup_app() {
    try {
      const token = localStorage.getItem('guest_token') || '';
      const res = await get_settings(token);
      this.is_admin = res.is_admin;
      this.is_desk = 'desk' in frappe;

      if (res.enable_chat === false || (!this.is_desk && this.is_admin)) {
        return;
      }

      // Check if user has WhatsApp Agent role
      if (!frappe.user_roles.includes('WhatsApp Agent') && !frappe.user_roles.includes('System Manager')) {
        console.log('User does not have WhatsApp Agent role');
        return;
      }

      this.create_app();
      await frappe.socketio.init(res.socketio_port);

      frappe.Chat.settings = {};
      frappe.Chat.settings.user = res.user_settings;
      frappe.Chat.settings.unread_count = 0;

      if (res.is_admin) {
        // If the user is admin, render everthing
        this.chat_list = new ChatList({
          $wrapper: this.$chat_container,
          user: res.user,
          user_email: res.user_email,
          is_admin: res.is_admin,
        });
        this.chat_list.render();
      } else if (res.is_verified) {
        // If the token and ip address matches, directly render the chat space
        this.chat_space = new ChatSpace({
          $wrapper: this.$chat_container,
          profile: {
            room_name: res.guest_title,
            room: res.room,
            is_admin: res.is_admin,
            user: res.user,
            user_email: res.user_email,
          },
        });
      } else {
        //Render the welcome screen if the user is not verified
        this.chat_welcome = new ChatWelcome({
          $wrapper: this.$chat_container,
          profile: {
            name: res.guest_title,
            is_admin: res.is_admin,
            chat_status: res.chat_status,
          },
        });
        this.chat_welcome.render();
      }
    } catch (error) {
      console.error(error);
    }
  }

  /** Shows the chat widget */
  show_chat_widget() {
    this.is_open = true;
    this.$chat_element.fadeIn(250);
    if (typeof this.chat_space !== 'undefined') {
      scroll_to_bottom(this.chat_space.$chat_space_container);
    }
  }

  /** Hides the chat widget */
  hide_chat_widget() {
    this.is_open = false;
    this.$chat_element.fadeOut(300);
  }

  should_close(e) {
    const chat_app = $('.chat-app');
    const navbar = $('.navbar');
    const modal = $('.modal');
    return (
      !chat_app.is(e.target) &&
      chat_app.has(e.target).length === 0 &&
      !navbar.is(e.target) &&
      navbar.has(e.target).length === 0 &&
      !modal.is(e.target) &&
      modal.has(e.target).length === 0
    );
  }

  setup_events() {
    const me = this;
    $('.chat-navbar-icon').on('click', function () {
      me.chat_bubble.change_bubble();
    });

    $(document).mouseup(function (e) {
      if (me.should_close(e) && me.is_open === true) {
        me.chat_bubble.change_bubble();
      }
    });
  }
};

$(function () {
  new frappe.Chat();
});


// Existing Frappe WhatsApp Functionality (Send To WhatsApp Menu)
$(document).on('app_ready', function () {
	// waiting for page to load completely
	frappe.router.on("change", () => {
		var route = frappe.get_route();
		// all form's menu add the 'Send To Telegram' funcationality
		if (route && route[0] == "Form") {
			frappe.ui.form.on(route[1], {
				refresh: function (frm) {
					frm.page.add_menu_item(__("Send To Whatsapp"), function () {
						var user_name = frappe.user.name;
						var user_full_name = frappe.session.user_fullname;
						var reference_doctype = frm.doctype;
						var reference_name = frm.docname;
						var dialog = new frappe.ui.Dialog({
							'fields': [
								{ 'fieldname': 'ht', 'fieldtype': 'HTML' },
								{ 'label': 'Select Template', 'fieldname': 'template', 'reqd': 1, 'fieldtype': 'Link', 'options': 'WhatsApp Templates' },
								{ 'label': 'Send to', 'fieldname': 'contact', 'reqd': 1, 'fieldtype': 'Link', 'options': 'Contact', change() {
					                let contact_name = dialog.get_value('contact');
					                if (contact_name) {
					                    frappe.call({
					                        method: 'frappe.client.get_value',
					                        args: {
					                            doctype: 'Contact',
					                            filters: { name: contact_name },
					                            fieldname: ['mobile_no']
					                        },
					                        callback: function (r) {
					                        	console.log(r)
					                            if (r.message) {
					                                dialog.set_value('mobile_no', r.message.mobile_no);
					                            } else {
					                                dialog.set_value('mobile_no', '');
					                                frappe.msgprint('Mobile number not found for the selected contact.');
					                            }
					                        }
					                    });
					                } else {
					                    d.set_value('mobile_no', '');
					                }
					            }},
								{ 'label': 'Mobile no', 'fieldname': 'mobile_no', 'fieldtype': 'Data' },

							],
							'primary_action_label': 'Send',
							'title': 'Send a Telegram Message',
							primary_action: function () {
								var values = dialog.get_values();
								if (values) {
									var space = "\n" + "\n";
									// var the_message = "From : " + user_full_name + space + values.subject + space + values.message;

									// send telegram msg
									frappe.call({
										method: "frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_message.whatsapp_message.send_template",
										args: {
											to: values.mobile_no,
											template: values.template,
											reference_doctype: frm.doc.doctype,
											reference_name: frm.doc.name
										},
										freeze: true,
										callback: (r) => {
											frappe.msgprint(__("Successfully Sent to: " + values.mobile_no));
											dialog.hide();
										}
									});

									// add comment
									var comment_message = 'To : ' + values.mobile_no + space + "Whatsapp Template:" + values.template;
									frappe.call({
										method: "frappe.desk.form.utils.add_comment",
										args: {
											reference_doctype: reference_doctype,
											reference_name: reference_name,
											content: comment_message,
											comment_by: frappe.session.user_fullname,
											comment_email: frappe.session.user
										},
									});
								}

							},
							no_submit_on_enter: true,
						});
						let template = dialog.fields_dict.template;
	                    if (template) {
	                        // Dynamically set the get_query function for the user field
	                        template.get_query = function() {
	                            return {
	                                filters: { "for_doctype": frm.doc.doctype },
	                                doctype: "WhatsApp Templates"
	                            };
	                        };
	                        // Refresh the field to apply the new query
	                        template.refresh();
	                    }
						dialog.show();
					});
				}
			});
		};
	})
});
