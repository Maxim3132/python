// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    // Открытие кейсов
    document.querySelectorAll('.case-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const caseCard = this.closest('.case-card');
            openCase(caseCard);
        });
    });
    
    // Анимация кнопок
    document.querySelectorAll('.btn-glow').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
});

// Функция открытия кейса
function openCase(caseElement) {
    // Блокируем кнопку
    const btn = caseElement.querySelector('.case-btn');
    btn.disabled = true;
    btn.textContent = 'ОТКРЫВАЕМ...';
    
    // Анимация
    caseElement.style.animation = 'pulse 0.5s infinite';
    
    // Имитация загрузки
    setTimeout(() => {
        // Получаем случайный приз
        const prize = getRandomPrize();
        
        // Показываем результат
        showPrize(prize);
        
        // Восстанавливаем кнопку
        btn.disabled = false;
        btn.textContent = 'ОТКРЫТЬ';
        caseElement.style.animation = '';
    }, 2000);
}

// Генерация случайного приза
function getRandomPrize() {
    const prizes = [
        { name: "AK-47 | Красная линия", value: "850 🔥", rarity: "rare" },
        { name: "Нож Балисонг", value: "1200 🔥", rarity: "epic" },
        { name: "50 🔥", value: "50 🔥", rarity: "common" }
    ];
    
    // Веса для вероятностей
    const weights = [0.6, 0.3, 0.1];
    let random = Math.random();
    let weightSum = 0;
    
    for (let i = 0; i < prizes.length; i++) {
        weightSum += weights[i];
        if (random <= weightSum) {
            return prizes[i];
        }
    }
    
    return prizes[0];
}

// Показ приза
function showPrize(prize) {
    // В реальном проекте здесь будет модальное окно
    alert(`🎉 ВЫ ВЫИГРАЛИ:\n${prize.name}\nСтоимость: ${prize.value}`);
    
    // Добавляем в инвентарь (заглушка)
    console.log(`Added to inventory: ${prize.name}`);
}
