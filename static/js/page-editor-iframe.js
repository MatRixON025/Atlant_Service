// JavaScript для редактирования контента в iframe
class IframeEditor {
  constructor() {
    this.isEditMode = false;
    this.pageContent = {};
    this.editableElements = new Map();
    
    // Определяем режим редактирования из URL
    const urlParams = new URLSearchParams(window.location.search);
    this.isEditMode = urlParams.get('edit_mode') === 'true';
    
    // Инициализируем только в режиме редактирования
    if (this.isEditMode) {
      console.log('IframeEditor initialized');
      this.init();
    }
  }
  
  init() {
    // Слушаем сообщения от родительского окна
    window.addEventListener('message', (e) => {
      console.log('Message received:', e.data);
      this.handleMessage(e.data);
    });
    
    console.log('Edit mode:', this.isEditMode);
    
    if (this.isEditMode) {
      this.setupEditMode();
    }
  }
  
  handleMessage(data) {
    console.log('Handling message:', data);
    const { type, pageContent, isEditMode } = data;
    
    switch(type) {
      case 'init_editor':
        console.log('Init editor received, pageContent:', pageContent);
        this.pageContent = pageContent || {};
        this.isEditMode = isEditMode || false;
        
        if (this.isEditMode) {
          this.setupEditMode();
        }
        break;
        
      case 'update_content':
        this.updateContent(data.elementId, data.newText);
        break;
        
      case 'update_element':
        this.updateElement(data.elementId, data.text, data.classes);
        break;
    }
  }
  
  setupEditMode() {
    console.log('Setting up edit mode');
    if (!this.isEditMode) return;
    
    // Находим все редактируемые элементы
    this.findEditableElements();
    
    // Добавляем обработчики кликов
    this.setupClickHandlers();
    
    // Добавляем визуальные индикаторы
    this.addVisualIndicators();
    
    console.log('Edit mode setup complete, found elements:', this.editableElements.size);
  }
  
  findEditableElements() {
    // Ищем элементы с data-editable атрибутом или стандартные контентные элементы
    const selectors = [
      '[data-editable]',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'span', 'a', 'button', 'li',
      '.title', '.subtitle', '.description', '.text'
    ];
    
    selectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(element => {
        if (this.isElementEditable(element)) {
          this.makeElementEditable(element);
        }
      });
    });
  }
  
  isElementEditable(element) {
    // Пропускаем элементы в формах, скрипты, скрытые элементы
    if (element.closest('form, script, style, noscript')) {
      return false;
    }
    
    // Пропускаем элементы без текста
    if (!element.textContent.trim()) {
      return false;
    }
    
    // Пропускаем слишком маленькие элементы
    const rect = element.getBoundingClientRect();
    if (rect.width < 20 || rect.height < 10) {
      return false;
    }
    
    return true;
  }
  
  makeElementEditable(element) {
    const elementId = this.getElementId(element);
    
    // Сохраняем оригинальный текст
    if (!this.pageContent.elements) {
      this.pageContent.elements = {};
    }
    
    if (!this.pageContent.elements[elementId]) {
      this.pageContent.elements[elementId] = element.textContent.trim();
    }
    
    // Применяем сохраненный контент
    const savedText = this.pageContent.elements[elementId];
    if (savedText && savedText !== element.textContent.trim()) {
      element.textContent = savedText;
    }
    
    // Добавляем данные элемента
    this.editableElements.set(element, {
      id: elementId,
      tag: element.tagName.toLowerCase(),
      text: element.textContent.trim(),
      classes: element.className,
      originalText: element.textContent.trim()
    });
    
    // Добавляем класс для стилизации
    element.classList.add('editable-element');
  }
  
  getElementId(element) {
    // Ищем data-editable-id
    let id = element.getAttribute('data-editable-id');
    if (id) return id;
    
    // Генерируем ID на основе структуры
    const tagName = element.tagName.toLowerCase();
    const text = element.textContent.trim().substring(0, 20);
    const hash = this.simpleHash(text + element.className);
    
    return `${tagName}-${hash}`;
  }
  
  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(36);
  }
  
  setupClickHandlers() {
    document.addEventListener('click', (e) => {
      if (!this.isEditMode) return;
      
      const element = e.target.closest('.editable-element');
      if (element) {
        e.preventDefault();
        e.stopPropagation();
        this.handleElementClick(element);
      }
    });
  }
  
  handleElementClick(element) {
    const elementData = this.editableElements.get(element);
    const rect = element.getBoundingClientRect();
    
    // Отправляем в родительское окно
    window.parent.postMessage({
      type: 'element_click',
      data: {
        ...elementData,
        rect: {
          left: rect.left + window.scrollX,
          top: rect.top + window.scrollY,
          width: rect.width,
          height: rect.height
        }
      }
    }, '*');
    
    // Двойной клик для редактирования
    if (e.detail === 2) {
      this.handleElementEdit(element);
    }
  }
  
  handleElementEdit(element) {
    const elementData = this.editableElements.get(element);
    const rect = element.getBoundingClientRect();
    
    window.parent.postMessage({
      type: 'element_edit',
      data: {
        elementId: elementData.id,
        currentText: elementData.text,
        rect: {
          left: rect.left + window.scrollX,
          top: rect.top + window.scrollY,
          width: Math.max(rect.width, 200),
          height: Math.max(rect.height, 30)
        }
      }
    }, '*');
  }
  
  updateContent(elementId, newText) {
    const element = this.findElementById(elementId);
    if (element) {
      element.textContent = newText;
      
      // Обновляем данные элемента
      const elementData = this.editableElements.get(element);
      if (elementData) {
        elementData.text = newText;
        this.editableElements.set(element, elementData);
      }
      
      // Отправляем уведомление об изменении
      window.parent.postMessage({
        type: 'content_change',
        data: { elementId, newText }
      }, '*');
    }
  }
  
  updateElement(elementId, text, classes) {
    const element = this.findElementById(elementId);
    if (element) {
      if (text !== undefined) {
        element.textContent = text;
      }
      
      if (classes !== undefined) {
        element.className = classes;
        // Добавляем класс редактируемости обратно
        element.classList.add('editable-element');
      }
      
      // Обновляем данные элемента
      const elementData = this.editableElements.get(element);
      if (elementData) {
        elementData.text = element.textContent.trim();
        elementData.classes = element.className;
        this.editableElements.set(element, elementData);
      }
    }
  }
  
  findElementById(elementId) {
    for (const [element, data] of this.editableElements) {
      if (data.id === elementId) {
        return element;
      }
    }
    return null;
  }
  
  addVisualIndicators() {
    // Добавляем стили для редактируемых элементов
    if (!document.getElementById('editor-styles')) {
      const style = document.createElement('style');
      style.id = 'editor-styles';
      style.textContent = `
        .editable-element {
          position: relative;
        }
        
        .editable-element:hover {
          outline: 2px dashed #007bff !important;
          outline-offset: 2px !important;
        }
        
        .editable-element.editing {
          outline: 2px solid #007bff !important;
          outline-offset: 2px !important;
          background: rgba(0, 123, 255, 0.05) !important;
        }
        
        .editable-element::before {
          content: '';
          position: absolute;
          top: -2px;
          left: -2px;
          right: -2px;
          bottom: -2px;
          border: 1px solid transparent;
          pointer-events: none;
          transition: all 0.2s ease;
        }
        
        .editable-element:hover::before {
          border-color: rgba(0, 123, 255, 0.3);
        }
      `;
      document.head.appendChild(style);
    }
  }
  
  // Включение/выключение режима редактирования
  toggleEditMode(enable) {
    this.isEditMode = enable;
    
    if (enable) {
      this.setupEditMode();
    } else {
      // Убираем индикаторы редактирования
      document.querySelectorAll('.editable-element').forEach(element => {
        element.classList.remove('editable-element');
      });
    }
  }
}

// Инициализация только если есть элементы для редактирования
document.addEventListener('DOMContentLoaded', function() {
  // Проверяем есть ли на странице редактируемые элементы
  const editableElements = document.querySelectorAll('[data-editable-id]');
  if (editableElements.length > 0) {
    const iframeEditor = new IframeEditor();
  }
});
