# Screenshot Naming Conventions

## Purpose
This document defines the screenshot file naming system for consistent documentation.

## Naming Format
```
{Section}-{Page}-{Action}-{Description}.png
```

## Examples
- `sales-invoice-new-basic.png` - New invoice page, basic view
- `inventory-product-list-filter.png` - Product list with filter
- `accounting-reports-pl-view.png` - P&L report view
- `dashboard-alerts-lowstock.png` - Dashboard with low stock alerts
- `settings-company-edit.png` - Company settings edit

## Section Codes
- `login` - Login screens
- `dashboard` - Dashboard
- `sales` - Sales module
- `purchase` - Purchase module
- `inventory` - Inventory module
- `accounting` - Accounting module
- `reports` - Reports section
- `settings` - Settings screens

## Action Codes
- `new` - Create new
- `edit` - Edit mode
- `list` - List view
- `detail` - Detail view
- `search` - Search functionality
- `filter` - Filter options
- `print` - Print preview
- `save` - Save confirmation

## Screenshot Sizes
- Standard width: 1200px (max)
- Include full UI element
- Minimum clear readable text

## Organization
```
screenshots/
├── login/
├── dashboard/
├── sales/
├── purchase/
├── inventory/
├── accounting/
├── reports/
└── settings/
```

## Placeholder Use
- Use `[SCREENSHOT: filename.png]` in documentation
- Replace with actual screenshot later
- Maintain naming consistency

## Print Guidelines
- Use PNG format
- 300 DPI for print
- Include page context in image
- Hide sensitive data (blur passwords)