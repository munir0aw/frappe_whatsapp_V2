"""
WhatsApp API endpoints for CRM integration.
This module provides API endpoints that can be called by Frappe CRM
to get WhatsApp messages for Leads/Deals.
"""
import frappe


@frappe.whitelist()
def get_whatsapp_messages(reference_doctype=None, reference_name=None, mobile_no=None):
    """Get WhatsApp messages for a reference document or phone number.
    
    This endpoint is designed to work with Frappe CRM's WhatsApp panel.
    It queries messages by:
    1. Phone number (from any linked contact or the Lead/Deal itself)
    2. Reference document (if messages are directly linked)
    
    Args:
        reference_doctype: The DocType (e.g., "CRM Lead")
        reference_name: The document name (e.g., "CRM-LEAD-2026-00001")
        mobile_no: Optional phone number to query directly
        
    Returns:
        List of WhatsApp messages
    """
    phone_numbers = []
    
    # If mobile_no provided directly, use it
    if mobile_no:
        phone_numbers.append(mobile_no)
    
    # Get phone number from the reference document
    if reference_doctype and reference_name:
        # Try CRM Lead
        if reference_doctype == "CRM Lead":
            lead_mobile = frappe.db.get_value("CRM Lead", reference_name, "mobile_no")
            if lead_mobile:
                phone_numbers.append(lead_mobile)
        # Try CRM Deal
        elif reference_doctype == "CRM Deal":
            deal_mobile = frappe.db.get_value("CRM Deal", reference_name, "mobile_no")
            if not deal_mobile:
                 # Try to get from linked Contact (common in CRM)
                 # Check for 'contact', 'primary_contact', or 'contact_person' fields
                 contact_name = frappe.db.get_value("CRM Deal", reference_name, ["contact", "primary_contact", "contact_person"])
                 # contact_name returns a dict, get first non-null value
                 if contact_name:
                     c_name = next((v for v in contact_name.values() if v), None)
                     if c_name:
                         deal_mobile = frappe.db.get_value("Contact", c_name, "mobile_no")

            if deal_mobile:
                phone_numbers.append(deal_mobile)
        # Try Contact
        elif reference_doctype == "Contact":
            contact_mobile = frappe.db.get_value("Contact", reference_name, "mobile_no")
            if contact_mobile:
                phone_numbers.append(contact_mobile)
        
        # Also check if there's a WhatsApp Contact linked to this Lead
        if reference_doctype == "CRM Lead":
            wa_contacts = frappe.get_all(
                "WhatsApp Contact",
                filters={"lead_reference": reference_name},
                fields=["mobile_no"]
            )
            for wc in wa_contacts:
                if wc.mobile_no:
                    phone_numbers.append(wc.mobile_no)
    
    if not phone_numbers:
        return []
    
    # Add phone number variants (with/without +)
    all_variants = []
    for phone in phone_numbers:
        all_variants.append(phone)
        if phone.startswith('+'):
            all_variants.append(phone[1:])
        else:
            all_variants.append('+' + phone)
    
    # Remove duplicates
    all_variants = list(set(all_variants))
    
    # Query messages
    messages = frappe.db.sql("""
        SELECT 
            name,
            creation,
            modified,
            `type`,
            `from`,
            `to`,
            message,
            attach,
            content_type,
            status,
            message_id,
            profile_name,
            whatsapp_account,
            reference_doctype,
            reference_name
        FROM `tabWhatsApp Message` 
        WHERE (`to` IN %(phones)s OR `from` IN %(phones)s)
        ORDER BY creation ASC
    """, {"phones": all_variants}, as_dict=True)
    
    return messages


@frappe.whitelist()
def create_whatsapp_message(reference_doctype, reference_name, message, to, attach=None, reply_to=None):
    """Create and send a WhatsApp message.
    
    Args:
        reference_doctype: The DocType this message relates to
        reference_name: The document name
        message: Message content
        to: Recipient phone number
        attach: Optional attachment URL
        reply_to: Optional message ID to reply to
        
    Returns:
        The created WhatsApp Message name
    """
    content_type = "text"
    if attach:
        # Determine content type from attachment
        import mimetypes
        file_type = mimetypes.guess_type(attach)[0] or ""
        if file_type.startswith("image/"):
            content_type = "image"
        elif file_type.startswith("video/"):
            content_type = "video"
        elif file_type.startswith("audio/"):
            content_type = "audio"
        elif file_type:
            content_type = "document"
    
    doc = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "type": "Outgoing",
        "to": to,
        "message": message,
        "attach": attach,
        "content_type": content_type,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "reply_to_message_id": reply_to
    })
    doc.insert(ignore_permissions=True)
    
    return doc.name


@frappe.whitelist()
def send_template(to, template, reference_doctype=None, reference_name=None):
    """Send a WhatsApp template message.
    
    Args:
        to: Recipient phone number
        template: WhatsApp Template name
        reference_doctype: Optional reference DocType
        reference_name: Optional reference name
        
    Returns:
        The created WhatsApp Message name
    """
    from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_message.whatsapp_message import send_template as _send_template
    return _send_template(to=to, template=template, reference_doctype=reference_doctype, reference_name=reference_name)


@frappe.whitelist()
def get_whatsapp_contact_for_lead(lead_name):
    """Get or create WhatsApp Contact for a CRM Lead.
    
    Args:
        lead_name: CRM Lead document name
        
    Returns:
        WhatsApp Contact name or None
    """
    # Check if WhatsApp Contact already linked
    wa_contact = frappe.db.get_value(
        "WhatsApp Contact",
        {"lead_reference": lead_name},
        "name"
    )
    if wa_contact:
        return wa_contact
    
    # Find by phone number
    mobile_no = frappe.db.get_value("CRM Lead", lead_name, "mobile_no")
    if not mobile_no:
        return None
    
    # Try exact match or with/without +
    phone_variants = [mobile_no]
    if mobile_no.startswith('+'):
        phone_variants.append(mobile_no[1:])
    else:
        phone_variants.append('+' + mobile_no)
    
    for phone in phone_variants:
        wa_contact = frappe.db.exists("WhatsApp Contact", phone)
        if wa_contact:
            # Link to Lead
            frappe.db.set_value("WhatsApp Contact", wa_contact, {
                "lead_reference": lead_name,
                "converted_to_lead": 1
            })
            return wa_contact
    
    return None
