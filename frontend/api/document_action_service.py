"""
Document Action Service - Handles printing and sharing of ERP documents.
Supports local printing and sharing via WhatsApp/Social Media.
"""

import webbrowser
import urllib.parse
from datetime import datetime
from typing import Dict, Any

class DocumentActionService:
    """
    Service to manage document-related actions like Printing and Sharing.
    """
    
    @staticmethod
    def share_via_whatsapp(doc_type: str, data: Dict[str, Any], phone: str = ""):
        """
        Generate a professional message and open WhatsApp.
        """
        message = DocumentActionService.generate_share_text(doc_type, data)
        encoded_msg = urllib.parse.quote(message)
        
        # Format phone if provided (ensure international format without +)
        clean_phone = "".join(filter(str.isdigit, phone))
        
        url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
        webbrowser.open(url)

    @staticmethod
    def generate_share_text(doc_type: str, data: Dict[str, Any]) -> str:
        """
        Create a formatted text for sharing.
        """
        company_name = "Pharmacy ERP" # Should come from config
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if doc_type == "invoice":
            inv_no = data.get('invoice_number', 'N/A')
            total = data.get('total_amount', '0.00')
            customer = data.get('customer_name', 'Valued Customer')
            
            msg = f"💊 *{company_name} - Invoice*\n"
            msg += f"--------------------------\n"
            msg += f"📄 *Invoice #:* {inv_no}\n"
            msg += f"👤 *Customer:* {customer}\n"
            msg += f"💰 *Total Amount:* {total} AFN\n"
            msg += f"📅 *Date:* {now}\n"
            msg += f"--------------------------\n"
            
            items = data.get('items', [])
            if items:
                msg += "*Items:*\n"
                for item in items[:5]: # Show first 5 items
                    name = item.get('product_name', 'Item')
                    qty = item.get('quantity', 0)
                    price = item.get('unit_price', 0)
                    msg += f"- {name} (x{qty}) @ {price}\n"
                
                if len(items) > 5:
                    msg += f"... and {len(items)-5} more items.\n"
            
            msg += f"\nThank you for your business!"
            return msg
            
        elif doc_type == "report":
            name = data.get('report_name', 'Financial Report')
            period = data.get('period', 'N/A')
            
            msg = f"📊 *{company_name} - {name}*\n"
            msg += f"--------------------------\n"
            msg += f"📅 *Period:* {period}\n"
            msg += f"🕒 *Generated:* {now}\n"
            
            metrics = data.get('summary', {})
            if metrics:
                msg += "\n*Key Metrics:*\n"
                for k, v in metrics.items():
                    msg += f"🔹 {k}: {v}\n"
            
            return msg
            
        return f"Document from {company_name} shared on {now}"

    @staticmethod
    def print_document(doc_type: str, data: Dict[str, Any]):
        """
        Trigger system print dialog (Simplified for now).
        In a real app, this would generate a PDF/HTML and use QPrinter.
        """
        print(f"Printing {doc_type}: {data.get('id', 'N/A')}")
        # Implementation depends on PDF generation capability
        # For now, we'll log it and prepare for PDF integration
