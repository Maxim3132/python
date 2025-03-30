const Admin = {
    data: {
        selectedUser: null,
        selectedCase: null,
        selectedWithdrawal: null
    },
    
    init() {
        this.loadUsers();
        this.loadCases();
        this.loadWithdrawals();
        this.setupEventListeners();
    },
    
    // Загрузка пользователей
    loadUsers() {
        // Загрузка и отображение
    },
    
    // Управление пользователями
    manageUser(action, userId, data) {
        // Блокировка, изменение баланса и т.д.
    },
    
    // Управление кейсами
    manageCase(action, caseId, data) {
        // Добавление/редактирование/удаление
    },
    
    // Управление выводами
    processWithdrawal(withdrawalId, action) {
        // Одобрение/отклонение
    },
    
    // Настройка событий
    setupEventListeners() {
        // Все обработчики админ-панели
    }
};

// Запуск админки
document.addEventListener('DOMContentLoaded', () => Admin.init());
