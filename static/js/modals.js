/**
 * Универсальный скрипт для работы с модальными окнами
 * Поддерживает открытие и закрытие любых модалей
 */

// Открыть модальное окно  
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) {
    console.warn(`Modal with id "${modalId}" not found`);
    return;
  }
  
  modal.style.display = 'flex';
  modal.classList.add('modal--open');
  document.body.style.overflow = 'hidden';
  document.body.style.paddingRight = getScrollbarWidth() + 'px';
}

// Закрыть модальное окно
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  modal.style.display = 'none';
  modal.classList.remove('modal--open');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
}

// Получить ширину скроллбара
function getScrollbarWidth() {
  const outer = document.createElement('div');
  outer.style.visibility = 'hidden';
  outer.style.overflow = 'scroll';
  document.body.appendChild(outer);
  
  const inner = document.createElement('div');
  outer.appendChild(inner);
  
  const scrollbarWidth = outer.offsetWidth - inner.offsetWidth;
  outer.parentNode.removeChild(outer);
  
  return scrollbarWidth;
}

// Закрытие модальных окон при клике вне их
document.addEventListener('click', function(event) {
  // Проверяем, был ли клик на backdrop
  if (event.target.classList && event.target.classList.contains('modal')) {
    const modalId = event.target.id;
    closeModal(modalId);
  }
  
  // Поддержка backdrop для старых модалей
  if (event.target.classList && event.target.classList.contains('modal-backdrop')) {
    const modal = event.target.closest('.modal');
    if (modal) {
      closeModal(modal.id);
    }
  }
});

// Закрытие модальных окон при нажатии ESC
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    // Закрываем все открытые модали
    const openModals = document.querySelectorAll('.modal--open, .modal[style*="display: flex"]');
    openModals.forEach(modal => {
      const modalId = modal.id;
      if (modalId) {
        closeModal(modalId);
      }
    });
  }
});

// Зафиксировать фокус внутри модального окна (для доступности)
function trapFocus(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  const focusableElements = modal.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  
  modal.addEventListener('keydown', function(event) {
    if (event.key !== 'Tab') return;
    
    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        lastElement.focus();
        event.preventDefault();
      }
    } else {
      if (document.activeElement === lastElement) {
        firstElement.focus();
        event.preventDefault();
      }
    }
  });
}
