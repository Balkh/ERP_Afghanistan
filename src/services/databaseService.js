// Service for handling database operations via Electron IPC
class DatabaseService {
  // Products
  async getProducts() {
    return await window.electronAPI.dbQuery('getProducts');
  }
  
  async getProductById(id) {
    // This would need to be implemented in the IPC handler
    // For now, we'll return a placeholder
    return null;
  }
  
  async createProduct(productData) {
    // Implementation would go here
    // For now, return placeholder
    return { id: Date.now(), ...productData };
  }
  
  async updateProduct(id, productData) {
    // Implementation would go here
    return { id, ...productData };
  }
  
  async deleteProduct(id) {
    // Implementation would go here
    return { id };
  }
  
  // Suppliers
  async getSuppliers() {
    return await window.electronAPI.dbQuery('getSuppliers');
  }
  
  // Customers
  async getCustomers() {
    return await window.electronAPI.dbQuery('getCustomers');
  }
}

// Create a singleton instance
const databaseService = new DatabaseService();

// Expose to window for use in React components
window.databaseService = databaseService;

export default databaseService;