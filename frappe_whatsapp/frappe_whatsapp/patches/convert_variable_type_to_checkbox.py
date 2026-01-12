import frappe

def execute():
    """Convert variable_type from 'Common'/'Unique' to 1/0 checkbox"""
    
    # Update all existing bulk messages
    frappe.db.sql("""
        UPDATE `tabBulk WhatsApp Message`
        SET variable_type = CASE 
            WHEN variable_type = 'Common' THEN 1
            WHEN variable_type = 'Unique' THEN 0
            ELSE 1
        END
        WHERE variable_type IN ('Common', 'Unique')
    """)
    
    frappe.db.commit()
    
    print("✅ Converted variable_type from text to checkbox")
