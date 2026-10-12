// supplier-invoices.js - SIMS Dedicated Supplier Invoices View (Phase 3)

App.pages['supplier-invoices'] = {
    render() {
        // Delegate rendering to App.pages['payments'] with invoices tab selected
        App.pages['payments'].currentTab = 'invoices';
        return App.pages['payments'].render();
    },

    async init() {
        App.pages['payments'].currentTab = 'invoices';
        await App.pages['payments'].init();
    }
};
