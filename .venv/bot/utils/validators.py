"""Валидаторы для проверки данных"""
import re
from typing import Optional, Tuple


def validate_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация поискового запроса
    
    Args:
        query: Поисковый запрос
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not query:
        return False, "Запрос не может быть пустым"
    
    if len(query.strip()) < 2:
        return False, "Запрос слишком короткий (минимум 2 символа)"
    
    if len(query) > 200:
        return False, "Запрос слишком длинный (максимум 200 символов)"
    
    # Проверка на наличие только спецсимволов
    if not re.search(r'[a-zA-Zа-яА-Я0-9]', query):
        return False, "Запрос должен содержать хотя бы одну букву или цифру"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от недопустимых символов
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        str: Очищенное имя файла
    """
    # Удаляем недопустимые символы для Windows/Linux
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Удаляем пробелы в начале и конце
    sanitized = sanitized.strip()
    
    # Ограничиваем длину
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized if sanitized else "unnamed"

