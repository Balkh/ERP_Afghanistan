with open('ui/finance/budgeting_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    def _create_budget(self):
        AlertDialog.info("Create Budget", "Budget creation dialog would open here.")
    
    def on_show(self):
        self.load_data()'''

new = '''    def _create_budget(self):
        dialog = BudgetDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_data()

    def _edit_budget(self):
        selected = self.budgets_table.get_selected_data()
        if not selected:
            AlertDialog.warning(self, "No Selection", "Please select a budget to edit.", self)
            return
        dialog = BudgetDialog(self, api_client=self.api_client, budget=selected[0])
        if dialog.exec():
            self.load_data()

    def _delete_budget(self):
        selected = self.budgets_table.get_selected_data()
        if not selected:
            AlertDialog.warning(self, "No Selection", "Please select a budget to delete.", self)
            return
        if ConfirmDialog.confirm(self, "Delete Budget", f"Are you sure you want to delete budget {selected[0].get('name', '')}?"):
            try:
                endpoint = f"/api/budgets/budgets/{selected[0].get('id')}/"
                response = self.api_client.delete(endpoint)
                if response and response.get('success'):
                    AlertDialog.info(self, "Success", "Budget deleted.", self)
                    self.load_data()
                else:
                    AlertDialog.error(self, "Error", "Failed to delete budget.", self)
            except Exception as e:
                AlertDialog.error(self, "Error", f"Failed to delete: {e}", self)

    def on_show(self):
        self.load_data()'''

content = content.replace(
    '''    def _create_budget(self):
        AlertDialog.info("Create Budget", "Budget creation dialog would open here.")
    
    def on_show(self):
        self.load_data()''',
    '''    def _create_budget(self):
        dialog = BudgetDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_data()

    def _edit_budget(self):
        selected = self.budgets_table.get_selected_data()
        if not selected:
            AlertDialog.warning(self, "No Selection", "Please select a budget to edit.", self)
            return
        dialog = BudgetDialog(self, api_client=self.api_client, budget=selected[0])
        if dialog.exec():
            self.load_data()

    def _delete_budget(self):
        selected = self.budgets_table.get_selected_data()
        if not selected:
            AlertDialog.warning(self, "No Selection", "Please select a budget to delete.", self)
            return
        if ConfirmDialog.confirm(self, "Delete Budget", f"Are you sure you want to delete budget {selected[0].get('name', '')}?"):
            try:
                endpoint = f"/api/budgets/budgets/{selected[0].get('id')}/"
                response = self.api_client.delete(endpoint)
                if response and response.get('success'):
                    AlertDialog.info(self, "Success", "Budget deleted.", self)
                    self.load_data()
                else:
                    AlertDialog.error(self, "Error", "Failed to delete budget.", self)
            except Exception as e:
                AlertDialog.error(self, "Error", f"Failed to delete: {e}", self)

    def on_show(self):
        self.load_data()''')

with open('ui/finance/budgeting_screen.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')