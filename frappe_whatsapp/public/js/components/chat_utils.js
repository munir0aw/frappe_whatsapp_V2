import moment from 'moment';

function get_time(time) {
  let current_time;
  if (time) {
    current_time = moment(time);
  } else {
    current_time = moment();
  }
  return current_time.format('h:mm A');
}

function get_date_from_now(dateObj, type) {
  const sameDay = type === 'space' ? '[Today]' : 'h:mm A';
  const elseDay = type === 'space' ? 'MMM D, YYYY' : 'DD/MM/YYYY';
  const result = moment(dateObj).calendar(null, {
    sameDay: sameDay,
    lastDay: '[Yesterday]',
    lastWeek: elseDay,
    sameElse: elseDay,
  });
  return result;
}

function is_date_change(dateObj, prevObj) {
  const curDate = moment(dateObj).format('DD/MM/YYYY');
  const prevDate = moment(prevObj).format('DD/MM/YYYY');
  return curDate !== prevDate;
}

function scroll_to_bottom($element) {
  $element.animate(
    {
      scrollTop: $element[0].scrollHeight,
    },
    300
  );
}

function is_image(filename) {
  const allowedExtensions = /(\.jpg|\.jpeg|\.png|\.gif|\.webp)$/i;
  if (!allowedExtensions.exec(filename)) {
    return false;
  }
  return true;
}

async function get_rooms(email) {
  const res = await frappe.call({
    type: 'GET',
    method: 'frappe_whatsapp.frappe_whatsapp.api.contacts.get',
    args: {
      email: email,
    },
  });
  return await res.message;
}

async function get_messages(room, user_no) {
  const res = await frappe.call({
    method: 'frappe_whatsapp.frappe_whatsapp.api.message.get_all',
    args: {
      room: room,
      user_no: user_no,
    },
  });
  return await res.message;
}

async function send_message(content, user, room, user_no, attachment) {
  try {
    await frappe.call({
      method: 'frappe_whatsapp.frappe_whatsapp.api.message.send',
      args: {
        content: content,
        user: user,
        room: room,
        user_no: user_no,
        attachment: attachment
      },
    });
  } catch (error) {
    frappe.msgprint({
      title: __('Error'),
      message: __('Something went wrong. Please refresh and try again.'),
    });
  }
}

async function get_settings(token) {
  const res = await frappe.call({
    type: 'GET',
    method: 'frappe_whatsapp.frappe_whatsapp.api.config.settings',
    args: {
      token: token,
    },
  });
  return await res.message;
}

async function mark_message_read(room) {
  try {
    await frappe.call({
      method: 'frappe_whatsapp.frappe_whatsapp.api.message.mark_as_read',
      args: {
        room: room,
      },
    });
  } catch (error) {
    //pass
  }
}


async function create_guest({ email, full_name, message }) {
  const res = await frappe.call({
    method: 'frappe_whatsapp.frappe_whatsapp.api.user.get_guest_room',
    args: {
      email: email,
      full_name: full_name,
      message: message,
    },
  });
  return await res.message;
}

async function set_typing(room, user, is_typing, is_guest) {
  try {
    await frappe.call({
      method: 'frappe_whatsapp.frappe_whatsapp.api.message.set_typing',
      args: {
        room: room,
        user: user,
        is_typing: is_typing,
        is_guest: is_guest,
      },
    });
  } catch (error) {
    //pass
  }
}

async function create_private_room(contact_name, mobile_no, email) {
  await frappe.call({
    method: 'frappe_whatsapp.frappe_whatsapp.api.contacts.create',
    args: {
      contact_name: contact_name,
      mobile_no: mobile_no,
      email: email
    },
  });
}

async function set_user_settings(settings) {
  await frappe.call({
    method: 'frappe_whatsapp.frappe_whatsapp.api.config.user_settings',
    args: {
      settings: settings,
    },
  });
}

function get_avatar_html(room_type, user_email, room_name) {
  let avatar_html;
  if (room_type === 'Direct' && 'desk' in frappe) {
    avatar_html = frappe.avatar(user_email, 'avatar-medium');
  } else {
    avatar_html = frappe.get_avatar('avatar-medium', room_name);
  }
  return avatar_html;
}

function set_notification_count(type) {
  const current_count = frappe.Chat.settings.unread_count;
  const $badge = $('#chat-notification-count');
  
  if (type === 'increment') {
    const new_count = current_count + 1;
    $badge.text(new_count).show();
    frappe.Chat.settings.unread_count = new_count;
  } else {
    const new_count = Math.max(0, current_count - 1);
    if (new_count === 0) {
      $badge.text('').hide();
    } else {
      $badge.text(new_count).show();
    }
    frappe.Chat.settings.unread_count = new_count;
  }
}


export {
  get_time,
  scroll_to_bottom,
  get_rooms,
  get_messages,
  get_settings,
  create_guest,
  send_message,
  get_date_from_now,
  is_date_change,
  mark_message_read,
  set_typing,
  is_image,
  create_private_room,
  set_user_settings,
  get_avatar_html,
  set_notification_count,
};
