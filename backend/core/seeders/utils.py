"""Utility functions for seeders."""
import random
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone


class SeederUtils:
    """Common utilities for seeding data."""
    
    @staticmethod
    def random_date(start_days=365, end_days=0):
        """Generate random date within range.
        start_days: how far in the past (negative) or future (positive)
        end_days: closer boundary
        """
        # Handle case where start > end
        if start_days > end_days:
            start_days, end_days = end_days, start_days
        days = random.randint(start_days, end_days)
        return timezone.now() + timedelta(days=days)
    
    @staticmethod
    def random_decimal(min_val=100, max_val=10000, decimals=2):
        """Generate random decimal amount."""
        return Decimal(str(random.randint(min_val * 100, max_val * 100) / 100))
    
    @staticmethod
    def random_choice(choices):
        """Random choice from list."""
        return random.choice(choices)
    
    @staticmethod
    def afghan_names():
        """Common Afghan names."""
        return [
            'Ahmad', 'Mohammad', 'Ali', 'Rahim', 'Faris', 'Zahra', 'Fatima',
            'Mariam', 'Noor', 'Sami', 'Khalid', 'Yusuf', 'Tariq', 'Samir',
            'Hassan', 'Hussain', 'Abbas', 'Qadir', 'Nazar', 'Bashir'
        ]
    
    @staticmethod
    def afghan_last_names():
        """Common Afghan last names."""
        return [
            'Ahmadi', 'Mohammadi', 'Rahimi', 'Karimi', 'Haqiqi', 'Stanikzai',
            'Nazar', 'Safi', 'Wardak', 'Kabuli', 'Mazar', 'Herawi', 'Panjshiri'
        ]
    
    @staticmethod
    def company_names():
        """Afghan business names."""
        return [
            'Afghan Medical Corp', 'Kabul Pharmacy', 'Mazar Food Distributors',
            'Herat Trading Co', 'Kandahar Logistics', 'Balkh Pharmaceuticals',
            'Nangarhar Suppliers', 'Parwan Agriculture', 'Khost Electronics',
            'Paktia Auto Parts', 'Kabul Business Center', 'Afghan Import Export',
            'Durable Medical', 'International Trading', 'Gulf Star Suppliers'
        ]
    
    @staticmethod
    def product_names():
        """Pharmaceutical product names."""
        return [
            'Panadol 500mg', 'Aspirin 100mg', 'Ibuprofen 400mg', 'Amoxicillin 500mg',
            'Augmentin 625mg', 'Ceftriaxone 1g', 'Metronidazole 400mg', ' Ciprofloxacin 500mg',
            'Azithromycin 250mg', 'Paracetamol 500ml', 'ORS Powder', 'Saline Solution',
            'Glucose 5%', 'Ringer Lactate', 'Hydrocortisone 100mg', 'Dexamethasone 8mg',
            'Epinephrine 1mg', 'Atropine 1mg', 'Adrenaline 1ml', 'Insulin 100IU',
            'Metformin 500mg', 'Glibenclamide 5mg', 'Amlodipine 5mg', 'Enalapril 10mg',
            'Losartan 50mg', 'Omeprazole 20mg', 'Pantoprazole 40mg', 'Ranitidine 150mg',
            'Cetirizine 10mg', 'Loratadine 10mg', 'Diclofenac 50mg', 'Tramadol 50mg',
            'Codeine 30mg', 'Morphine 10mg', 'Bupivacaine 0.5%', 'Lidocaine 2%',
            'Diazepam 10mg', 'Phenobarbital 100mg', 'Carbamazepine 200mg', 'Sodium Valproate 500mg',
        ]
    
    @staticmethod
    def afghan_cities():
        """Afghan cities."""
        return ['Kabul', 'Mazar-i-Sharif', 'Herat', 'Kandahar', 'Jalalabad', 'Khost', 'Gardez']
    
    @staticmethod
    def generate_phone():
        """Generate Afghan phone number."""
        prefixes = ['070', '072', '073', '074', '079']
        return f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"
    
    @staticmethod
    def generate_code(prefix, length=8):
        """Generate unique code."""
        return f"{prefix}-{''.join([str(random.randint(0, 9)) for _ in range(length)])}"
    
    @staticmethod
    def status_weights():
        """Return weighted status distribution."""
        return {
            'PAID': 0.50,
            'PARTIAL': 0.25,
            'OVERDUE': 0.15,
            'CANCELLED': 0.10,
        }
    
    @staticmethod
    def pick_by_weight(weights):
        """Pick item based on weights."""
        r = random.random()
        cumulative = 0
        for key, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return key
        return list(weights.keys())[-1]
    
    @staticmethod
    def fiscal_year():
        """Get current fiscal year."""
        now = timezone.now()
        if now.month >= 4:
            return now.year
        return now.year - 1
    
    @staticmethod
    def get_or_create_company(company_name='Pharmacy Corp Afghanistan'):
        """Get or create default company."""
        from core.models.system import Company
        company, _ = Company.objects.get_or_create(
            code='PCA-001',
            defaults={
                'name': company_name,
                'address': 'Kabul, Afghanistan',
                'phone': '+93701234567',
                'email': 'info@pharmacycorp.af',
                'tax_number': 'TAX-001',
                'is_active': True,
                'default_currency': 'AFN',
                'secondary_currency': 'USD',
            }
        )
        return company