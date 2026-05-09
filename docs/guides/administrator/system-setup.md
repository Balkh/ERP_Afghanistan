# Administrator Guide

## Overview
This guide covers system administration tasks for the Pharmacy ERP system.

## Daily Operations
1. Check system status on dashboard
2. Review backup completion
3. Monitor low-stock alerts
4. Verify user activity

## System Setup

### First-Time Setup
1. Login with default credentials (admin/admin123)
2. Change default password immediately
3. Configure company information
4. Set up warehouse locations
5. Configure payment methods (Cash, Bank, Hawala, Mobile)
6. Set default currency (AFN or USD)

### User Management
- Add new users with appropriate roles
- Assign role-based permissions
- Monitor login activity

### Currency Configuration
- Set base currency (AFN - Afghani or USD)
- Configure exchange rates
- Add new currencies if needed

### Backup Configuration
- Schedule automatic backups
- Test backup restoration periodically
- Verify backup integrity

## Common Administrative Tasks

### Adding Products
1. Go to Inventory → Products
2. Click "Add Product"
3. Enter product details (name, SKU, barcode)
4. Assign category and unit
5. Set purchase and sale prices

### Managing Categories
- Create product categories for organization
- Categories help with inventory reporting

### Warehouse Setup
- Add warehouse locations
- Set default warehouse
- Configure warehouse-specific settings

## Warning Section
⚠️ **Important:**
- Never delete the admin user
- Keep backups in a safe location
- Document any system changes

## Common Mistakes to Avoid
1. Changing currency after transactions exist
2. Deleting products with historical transactions
3. Modifying posted journal entries

## Recovery Procedures

### Password Reset
If admin password is forgotten:
1. Contact system administrator
2. Database access required for reset

### System Restore
1. Go to System → Backup/Restore
2. Select restore point
3. Verify data before confirming
4. System will restart after restore