#!/usr/bin/env python3
"""Тестовый скрипт для проверки загрузки брендов"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import load_brands

def test_brands():
    print("=== Тест загрузки брендов ===")
    brands = load_brands()
    print(f"Загружено брендов: {len(brands)}")
    for brand_id, brand_info in brands.items():
        print(f"- {brand_id}: {brand_info['service_info']}")
    
    print("\n=== Проверка конкретного бренда ===")
    if 'samsung' in brands:
        print(f"Samsung: {brands['samsung']['service_info']}")
    else:
        print("Samsung не найден!")

if __name__ == "__main__":
    test_brands()
