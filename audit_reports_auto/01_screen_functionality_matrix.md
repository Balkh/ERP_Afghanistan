# Screen Functionality Matrix (automated scan)

File | Connects | Found | Missing | Connect Status | Loads
---|---:|---:|---:|---
frontend\ui\accounting\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\accounting\account_ledger_screen.py | 3 | 3 | 0 | CONNECTED | load_accounts, load_ledger
frontend\ui\accounting\chart_of_accounts_screen.py | 8 | 8 | 0 | CONNECTED | load_accounts
frontend\ui\accounting\components\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\accounting\components\account_form_dialog.py | 3 | 2 | 1 | PARTIAL | load_account, load_parent_accounts
frontend\ui\accounting\components\journal_entry_detail.py | 1 | 0 | 1 | CRITICAL | load_data
frontend\ui\accounting\components\journal_entry_form.py | 8 | 7 | 1 | PARTIAL | load_accounts
frontend\ui\accounting\components\report_preview_dialog.py | 4 | 3 | 1 | PARTIAL | 
frontend\ui\accounting\financial_audit_log_screen.py | 3 | 3 | 0 | CONNECTED | load_logs
frontend\ui\accounting\financial_integrity_screen.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\accounting\journal_entry_screen.py | 9 | 9 | 0 | CONNECTED | load_entries
frontend\ui\accounting\report_browser.py | 8 | 8 | 0 | CONNECTED | 
frontend\ui\auth\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\auth\login_screen.py | 4 | 4 | 0 | CONNECTED | load_session
frontend\ui\auth\totp_setup_dialog.py | 3 | 2 | 1 | PARTIAL | 
frontend\ui\autonomous\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\causal_scoring\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\causal_scoring\causal_scoring_engine.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\causal_scoring\causal_strength_panel.py | 1 | 1 | 0 | CONNECTED | load_data
frontend\ui\causal_scoring\decision_impact_engine.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\causal_scoring\decision_ranking_dashboard.py | 1 | 1 | 0 | CONNECTED | load_data
frontend\ui\causal_scoring\decision_workspace.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\common\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\common\barcode_scanner.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\common\barcode_search.py | 4 | 4 | 0 | CONNECTED | 
frontend\ui\common\batch_selection.py | 5 | 4 | 1 | PARTIAL | load_batches
frontend\ui\common\printable_invoice.py | 6 | 4 | 2 | PARTIAL | 
frontend\ui\common\product_selection_dialog.py | 5 | 3 | 2 | PARTIAL | 
frontend\ui\components\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\components\base_widgets.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\components\buttons.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\components\dialogs.py | 7 | 2 | 5 | PARTIAL | 
frontend\ui\components\document_action_dialog.py | 3 | 2 | 1 | PARTIAL | 
frontend\ui\components\forms.py | 14 | 12 | 2 | PARTIAL | 
frontend\ui\components\kpi_cards.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\components\loading_spinner.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\components\navigation_header.py | 3 | 0 | 3 | CRITICAL | 
frontend\ui\components\notifications.py | 2 | 1 | 1 | PARTIAL | 
frontend\ui\components\operator_safety.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\components\skeleton_loader.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\components\state_helper.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\components\tables.py | 9 | 8 | 1 | PARTIAL | 
frontend\ui\constants.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\control_tower\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\control_tower\financial_control_tower_screen.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\control_tower\operations_dashboard.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\control_tower\system_health_screen.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\control_tower\workflow_engine.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\control_tower\workflow_execution_screen.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\dashboard.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\finance\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\finance\budgeting_screen.py | 2 | 2 | 0 | CONNECTED | load_data
frontend\ui\finance\cashflow_screen.py | 1 | 1 | 0 | CONNECTED | load_data
frontend\ui\finance\cost_centers_screen.py | 5 | 4 | 1 | PARTIAL | load_data
frontend\ui\finance\customer_payment_workspace.py | 4 | 4 | 0 | CONNECTED | load_workspace
frontend\ui\finance\expense_screen.py | 6 | 4 | 2 | PARTIAL | load_expenses
frontend\ui\finance\financial_operations_console.py | 1 | 1 | 0 | CONNECTED | load_dashboard
frontend\ui\finance\journal_reversal_explorer.py | 1 | 1 | 0 | CONNECTED | load_reversals
frontend\ui\finance\mixed_payment_builder.py | 6 | 5 | 1 | PARTIAL | 
frontend\ui\finance\payment_allocation_explorer.py | 3 | 3 | 0 | CONNECTED | load_allocations
frontend\ui\finance\payment_screen.py | 2 | 2 | 0 | CONNECTED | load_data, load_payments
frontend\ui\finance\returns_explainability.py | 2 | 2 | 0 | CONNECTED | load_returns
frontend\ui\finance\supplier_payment_workspace.py | 4 | 4 | 0 | CONNECTED | load_workspace
frontend\ui\finance\tax_screen.py | 1 | 1 | 0 | CONNECTED | load_data
frontend\ui\governance\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\governance\approval_screen.py | 4 | 4 | 0 | CONNECTED | load_data
frontend\ui\governance\audit_scanner.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\governance\auto_fixer.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\governance\consistency_audit.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\governance\registry.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\governance\ux_governor.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\hr\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\hr\attendance_screen.py | 2 | 2 | 0 | CONNECTED | load_attendance
frontend\ui\hr\employee_screen.py | 8 | 6 | 2 | PARTIAL | load_employees
frontend\ui\hr\leave_screen.py | 2 | 2 | 0 | CONNECTED | load_leave
frontend\ui\hr\payroll_screen.py | 5 | 4 | 1 | PARTIAL | load_data
frontend\ui\hr\payslip_dialog.py | 5 | 3 | 2 | PARTIAL | 
frontend\ui\inventory\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\inventory\base_screen.py | 5 | 2 | 3 | PARTIAL | 
frontend\ui\inventory\batch_screen.py | 7 | 7 | 0 | CONNECTED | load_batches
frontend\ui\inventory\category_screen.py | 7 | 7 | 0 | CONNECTED | load_categories
frontend\ui\inventory\components\batch_form_dialog.py | 3 | 2 | 1 | PARTIAL | load_batch_data
frontend\ui\inventory\components\category_form_dialog.py | 3 | 2 | 1 | PARTIAL | load_category_data
frontend\ui\inventory\components\product_form.py | 3 | 2 | 1 | PARTIAL | load_product_data
frontend\ui\inventory\components\warehouse_form_dialog.py | 3 | 2 | 1 | PARTIAL | load_warehouse_data
frontend\ui\inventory\product_screen.py | 7 | 7 | 0 | CONNECTED | load_products
frontend\ui\inventory\warehouse_screen.py | 7 | 7 | 0 | CONNECTED | load_warehouses
frontend\ui\investigation\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\investigation\anomaly_investigation_screen.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\investigation\event_investigation_screen.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\licensing\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\licensing\activation_screen.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\licensing\dialogs.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\licensing\license_manager_dialog.py | 3 | 2 | 1 | PARTIAL | 
frontend\ui\licensing\license_status_screen.py | 4 | 3 | 1 | PARTIAL | load_license_details
frontend\ui\main_window.py | 30 | 30 | 0 | CONNECTED | 
frontend\ui\navigation\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\navigation\navigation_manager.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\observability\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\observability\base_view_model.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\observability\dashboards.py | 23 | 23 | 0 | CONNECTED | 
frontend\ui\observability\observability_console.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\observability\observability_screen.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\observability\replay_screen.py | 3 | 2 | 1 | PARTIAL | load_data
frontend\ui\observability\widgets.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\pos\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\pos\pos_screen.py | 11 | 11 | 0 | CONNECTED | load_customers, load_data
frontend\ui\purchases\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\purchases\purchase_invoice_screen.py | 25 | 23 | 2 | PARTIAL | load_data, load_suppliers, load_workflow_status
frontend\ui\purchases\supplier_screen.py | 9 | 8 | 1 | PARTIAL | load_suppliers
frontend\ui\returns\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\returns\reconciliation_screen.py | 9 | 9 | 0 | CONNECTED | 
frontend\ui\returns\returns_screen.py | 17 | 15 | 2 | PARTIAL | 
frontend\ui\role_manager.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\role_renderer.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\sales\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\sales\credit_warning_dialog.py | 3 | 1 | 2 | PARTIAL | 
frontend\ui\sales\customer_screen.py | 9 | 8 | 1 | PARTIAL | load_customer_data, load_customers
frontend\ui\sales\fifo_allocation_dialog.py | 2 | 1 | 1 | PARTIAL | load_data
frontend\ui\sales\sales_invoice_screen.py | 29 | 27 | 2 | PARTIAL | load_customers, load_data, load_workflow_status
frontend\ui\screen_registry.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\screens\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\screens\base_screen.py | 1 | 1 | 0 | CONNECTED | load_data
frontend\ui\sidebar.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\system\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\system\analytics_workspace.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\system\audit_screen.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\system\backup_screen.py | 11 | 9 | 2 | PARTIAL | 
frontend\ui\system\company_profile_screen.py | 4 | 4 | 0 | CONNECTED | 
frontend\ui\system\control_center_screen.py | 5 | 5 | 0 | CONNECTED | 
frontend\ui\system\correlation_screen.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\system\drift_intelligence_screen.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\system\email_config_dialog.py | 3 | 2 | 1 | PARTIAL | 
frontend\ui\system\entity_management_screen.py | 1 | 1 | 0 | CONNECTED | load_entities
frontend\ui\system\fixed_assets_screen.py | 5 | 4 | 1 | PARTIAL | 
frontend\ui\system\integrity_screen.py | 5 | 5 | 0 | CONNECTED | 
frontend\ui\system\intelligence_hub_screen.py | 1 | 1 | 0 | CONNECTED | 
frontend\ui\system\invoice_template_manager.py | 4 | 4 | 0 | CONNECTED | 
frontend\ui\system\licensing_screen.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\system\role_management_screen.py | 9 | 8 | 1 | PARTIAL | load_data
frontend\ui\system\settings_screen.py | 2 | 2 | 0 | CONNECTED | 
frontend\ui\system\user_management_screen.py | 6 | 5 | 1 | PARTIAL | load_roles, load_users
frontend\ui\system\workflow_intelligence_screen.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\truth\__init__.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\truth\event_store_screen.py | 2 | 2 | 0 | CONNECTED | load_data
frontend\ui\utils\debounce.py | 3 | 3 | 0 | CONNECTED | 
frontend\ui\utils\lazy_loader.py | 0 | 0 | 0 | NO_CONNECTS | loaded
frontend\ui\utils\profiler.py | 0 | 0 | 0 | NO_CONNECTS | load_data
frontend\ui\utils\table_diff.py | 0 | 0 | 0 | NO_CONNECTS | 
frontend\ui\utils\validation.py | 0 | 0 | 0 | NO_CONNECTS | 