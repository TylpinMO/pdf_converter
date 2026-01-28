import logging
from PIL import Image
from io import BytesIO
import os
from typing import List, Tuple
try:
    import fitz  # PyMuPDF
    PDF_BACKEND = "pymupdf"
except ImportError:
    try:
        from pdf2image import convert_from_path
        PDF_BACKEND = "pdf2image"
    except ImportError:
        PDF_BACKEND = None

logger = logging.getLogger(__name__)


async def photos_to_pdf(photo_paths: List[str], output_path: str) -> bool:
    """
    Конвертация списка изображений в PDF
    
    Args:
        photo_paths: Список путей к изображениям (JPG)
        output_path: Путь для сохранения PDF
        
    Returns:
        True если успешно, False если ошибка
    """
    try:
        images = []
        
        for photo_path in photo_paths:
            try:
                # Открываем изображение
                img = Image.open(photo_path)
                
                # Конвертируем RGBA в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Создаем белый фон
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                images.append(img)
                logger.info(f"Фото загружено: {photo_path}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке фото {photo_path}: {e}")
                return False
        
        if not images:
            logger.error("Нет изображений для конвертации")
            return False
        
        # Сохраняем как PDF
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            quality=90,
            format='PDF'
        )
        
        logger.info(f"PDF создан успешно: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании PDF: {e}", exc_info=True)
        return False


def check_file_size(file_size_bytes: int, max_size_mb: int) -> bool:
    """
    Проверка размера файла
    
    Args:
        file_size_bytes: Размер файла в байтах
        max_size_mb: Максимальный размер в МБ
        
    Returns:
        True если размер в пределах, False если превышен
    """
    max_bytes = max_size_mb * 1024 * 1024
    return file_size_bytes <= max_bytes


def get_file_size_mb(file_size_bytes: int) -> float:
    """Конвертация байтов в МБ"""
    return round(file_size_bytes / (1024 * 1024), 2)


def cleanup_temp_files(file_paths: List[str]):
    """Удаление временных файлов"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Временный файл удален: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")


async def pdf_to_photos(pdf_path: str, output_dir: str) -> Tuple[bool, List[str]]:
    """
    Конвертация PDF в изображения JPG (одно изображение на страницу)
    
    Args:
        pdf_path: Путь к PDF файлу
        output_dir: Директория для сохранения JPG файлов
        
    Returns:
        Кортеж (успешность, список путей к созданным файлам)
    """
    try:
        # Проверяем доступность PDF backend
        if PDF_BACKEND is None:
            logger.error("PDF конвертер не установлен. Установите PyMuPDF: pip install PyMuPDF")
            return False, []
        
        # Проверяем, существует ли PDF
        if not os.path.exists(pdf_path):
            logger.error(f"PDF файл не найден: {pdf_path}")
            return False, []
        
        # Создаем output директорию
        os.makedirs(output_dir, exist_ok=True)
        
        photo_paths = []
        
        if PDF_BACKEND == "pymupdf":
            # Используем PyMuPDF (fitz) - быстрее и без зависимостей
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Рендерим страницу в изображение (zoom=2 для хорошего качества)
                mat = fitz.Matrix(2, 2)  # 2x zoom = примерно 144 DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Сохраняем как JPG
                output_path = os.path.join(output_dir, f"page_{page_num + 1:03d}.jpg")
                
                # Конвертируем pixmap в PIL Image для сохранения с качеством
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Ограничиваем размеры для Telegram (макс 10000px, оптимально 4096px)
                max_size = 4096
                if img.width > max_size or img.height > max_size:
                    # Пропорциональное уменьшение
                    ratio = min(max_size / img.width, max_size / img.height)
                    new_width = int(img.width * ratio)
                    new_height = int(img.height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.info(f"Изображение уменьшено: {pix.width}x{pix.height} → {new_width}x{new_height}")
                
                img.save(output_path, format='JPEG', quality=85, optimize=True)
                
                photo_paths.append(output_path)
                logger.info(f"Страница {page_num + 1} сохранена: {output_path}")
            
            doc.close()
            
        else:  # pdf2image
            # Конвертируем PDF в изображения через poppler
            images = convert_from_path(pdf_path, dpi=150)
            
            if not images:
                logger.error(f"Не удалось конвертировать PDF: {pdf_path}")
                return False, []
            
            for idx, image in enumerate(images, start=1):
                # Конвертируем в RGB если нужно
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Ограничиваем размеры для Telegram (макс 10000px, оптимально 4096px)
                max_size = 4096
                if image.width > max_size or image.height > max_size:
                    # Пропорциональное уменьшение
                    ratio = min(max_size / image.width, max_size / image.height)
                    new_width = int(image.width * ratio)
                    new_height = int(image.height * ratio)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.info(f"Изображение уменьшено до {new_width}x{new_height}")
                
                # Сохраняем как JPG
                output_path = os.path.join(output_dir, f"page_{idx:03d}.jpg")
                image.save(output_path, format='JPEG', quality=85, optimize=True)
                photo_paths.append(output_path)
                logger.info(f"Страница {idx} сохранена: {output_path}")
        
        logger.info(f"PDF конвертирован в {len(photo_paths)} изображений (backend: {PDF_BACKEND})")
        return True, photo_paths
        
    except Exception as e:
        logger.error(f"Ошибка при конвертации PDF: {e}", exc_info=True)
        return False, []
