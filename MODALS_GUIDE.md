# Справочник - Работа с модальными окнами

## 📋 Общие функции (в `/static/js/modals.js`)

### Открыть модальное окно
```javascript
openModal('modalId')
// Пример: openModal('brandModal')
```

### Закрыть модальное окно
```javascript
closeModal('modalId')
// Пример: closeModal('brandModal')
```

**Автоматически закрывается при:**
- Клике вне модального окна
- Нажатии кнопки **ESC**

---

## 🎯 Админ-панель - Управление брендами

**Файл:** `templates/admin_brands.html`

### Добавить новый бренд
```html
<button onclick="openAddBrandModal()">Додати новий бренд</button>
```

### Редактировать бренд
```javascript
testEditBrand('samsung')  // ID бренда
```

### Удалить бренд
```javascript
testDeleteBrand('samsung')  // ID бренда
```

### Закрыть модальное окно
```javascript
closeBrandModal()
```

---

## 📦 Админ-панель - Управление вакансиями

**Файл:** `templates/admin_vacancies.html`

### Добавить вакансию
```html
<button class="btn btn--primary" onclick="showAddVacancyModal()">
  Додати вакансію
</button>
```

### Редактировать вакансию
```javascript
editVacancy('1')  // ID вакансии
```

### Удалить вакансию
```javascript
deleteVacancy('1')  // ID вакансии
```

### Закрыть модальное окно
```javascript
closeVacancyModal()
```

---

## ⚙️ Админ-панель - Управление услугами

**Файл:** `templates/admin_services.html`

### Открыть модальное окно добавления/редактирования
```javascript
openModal('serviceId')  // null для добавления, ID услуги для редактирования
```

### Закрыть модальное окно
```javascript
closeModal()
```

---

## 📨 Контактная форма

**Файл:** `templates/contact.html`

### Переключение между вкладками
```javascript
switchTab('contact')  // Вкладка повідомлення
switchTab('resume')   // Вкладка резюме
```

### Формы автоматически отправляют данные:
- **Контактная форма** → `/contact` (POST)
- **Форма резюме** → `/submit-resume` (POST)

---

## 🎨 CSS классы для модальных окон

### Базовая структура модального окна
```html
<div class="modal" id="myModal">
  <div class="modal__content">
    <div class="modal__header">
      <h3>Заголовок</h3>
      <button class="modal__close" onclick="closeModal('myModal')">&times;</button>
    </div>
    
    <div class="modal__body">
      <!-- Контент -->
    </div>
    
    <div class="modal__footer">
      <button onclick="closeModal('myModal')">Закрыть</button>
      <button type="submit">Сохранить</button>
    </div>
  </div>
</div>
```

### Классы стилей
- `.modal` - контейнер модального окна
- `.modal--open` - класс для видимости (добавляется функцией)
- `.modal__content` - основной контент
- `.modal__header` - заголовок
- `.modal__body` - тело
- `.modal__footer` - подвал
- `.modal__close` - кнопка закрытия (×)

---

## ⚡ Примеры использования

### Пример 1: Простое модальное окно
```html
<button onclick="openModal('confirmModal')">Подтвердить</button>

<div class="modal" id="confirmModal">
  <div class="modal__content">
    <div class="modal__header">
      <h3>Подтверждение</h3>
      <button class="modal__close" onclick="closeModal('confirmModal')">&times;</button>
    </div>
    <div class="modal__body">
      <p>Вы уверены?</p>
    </div>
    <div class="modal__footer">
      <button onclick="closeModal('confirmModal')">Отмена</button>
      <button onclick="doAction(); closeModal('confirmModal')">Да</button>
    </div>
  </div>
</div>
```

### Пример 2: Форма в модальном окне
```html
<div class="modal" id="formModal">
  <div class="modal__content">
    <div class="modal__header">
      <h3>Новые данные</h3>
      <button class="modal__close" onclick="closeModal('formModal')">&times;</button>
    </div>
    
    <form class="modal__body" onsubmit="handleSubmit(event)">
      <div class="form-group">
        <label for="name">Имя</label>
        <input type="text" id="name" name="name" required>
      </div>
      <div class="form-group">
        <label for="email">Email</label>
        <input type="email" id="email" name="email" required>
      </div>
      
      <div class="modal__footer">
        <button type="button" onclick="closeModal('formModal')">Отмена</button>
        <button type="submit">Отправить</button>
      </div>
    </form>
  </div>
</div>
```

---

## 🐛 Решение типичных проблем

### Модальное окно не открывается
**Проверить:**
1. ID окна совпадает? `<div id="myModal">` и `openModal('myModal')`
2. Скрипт подключен? `<script src="/static/js/modals.js"></script>`
3. Нет ошибок в console (F12)

### Модальное окно открывается, но не видно
**Решение:**
- Вручную добавить класс `.modal--open`:
```javascript
document.getElementById('myModal').classList.add('modal--open');
```

### Форма не отправляется
**Проверить:**
1. Action атрибут в форме указан
2. Нет JavaScript перехватов (e.preventDefault)
3. Валидация полей пройдена

---

## 📞 Поддержка

Для вопросов или ошибок:
1. Проверьте консоль браузера (F12)
2. Посмотрите сетевые запросы
3. Проверьте пути файлов и ID элементов
