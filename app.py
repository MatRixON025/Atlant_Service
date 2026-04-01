from datetime import datetime, timedelta
import uuid
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import json
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()  # load .env if present

app = Flask(__name__)
# Security settings
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CSP headers to allow JavaScript execution
@app.after_request
def add_security_headers(response):
    # Remove any existing CSP headers
    response.headers.pop('Content-Security-Policy', None)
    response.headers.pop('X-Content-Security-Policy', None)
    response.headers.pop('X-WebKit-CSP', None)
    
    # For testing: completely disable CSP
    # response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-src 'self'; media-src 'self'; object-src 'none';"
    
    return response

# Email configuration
EMAIL_SERVER = os.environ.get("EMAIL_SERVER", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.environ.get("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"

# Admin credentials (consider using environment variables in production)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
ADMIN_PASS_HASH = generate_password_hash(ADMIN_PASS)

# Admin email for notifications
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")

# Data paths
DATA_DIR = Path(__file__).resolve().parent / "data"
MESSAGES_PATH = DATA_DIR / "messages.json"
PRICES_PATH = DATA_DIR / "prices.json"
VACANCIES_PATH = DATA_DIR / "vacancies.json"
RESUMES_PATH = DATA_DIR / "resumes.json"

# Service center info (you can update these in templates or here)
SERVICES_DATA = [
    {
        "id": "fridge",
        "title": "Ремонт холодильників",
        "desc": "Заправка фреоном, ремонт компресорів, усунення витоків.",
        "details": "Працюємо з різними моделями: вбудовані, окремо стоячі, side-by-side.",
        "warranty": [
            "Виявлення заводського браку (неохолодження, замерзання комірки)",
            "Заміну компресора в межах гарантійного терміну",
            "Гарантійний ремонт системи охолодження",
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Заміна несправних компонентів за рахунок виробника"
        ],
        "non_warranty": [
            "Пошкодження через нестабільність електроживлення або перепади напруги",
            "Механічні пошкодження корпусу при транспортуванні",
            "Проблеми, викликані неправильним встановленням або експлуатацією",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильне підключення"
        ],
        "non_warranty_cases": [
            {"id": "technical_act", "name": "Оформлення акту технічного стану апаратури (за одиницю техніки)", "price": 300},
            {"id": "motor_replacement", "name": "Заміна мотор-компресора (з заміною фільтра осушувача, заправка фреоном)", "price": 5000},
            {"id": "evaporator_replacement", "name": "Заміна випарника", "price": 2000},
            {"id": "control_board_repair", "name": "Ремонт/заміна плати керування", "price": "3000/1500"},
            {"id": "fan_replacement", "name": "Заміна вентилятора випарника", "price": 800},
            {"id": "wiring_repair", "name": "Ремонт електропроводки", "price": 700},
            {"id": "condenser_replacement", "name": "Заміна конденсатора", "price": 2000},
            {"id": "thermostat_replacement", "name": "Заміна термостата", "price": 1000},
            {"id": "rtc_replacement", "name": "Заміна РТК", "price": 1000},
            {"id": "heater_replacement", "name": "Заміна нагрівача випарника", "price": 1200},
            {"id": "door_replacement", "name": "Перевес дверей/Side-by-side", "price": "1000/1500"},
            {"id": "accessories_replacement", "name": "Заміна аксесуарів", "price": 800},
            {"id": "system_repair", "name": "Ремонт холодильної системи, не пов'язаний з заміною мотор-компресора і випарника", "price": 3500},
            {"id": "false_call", "name": "Хибний виклик", "price": 300},
            {"id": "timer_replacement", "name": "Заміна таймера відтайки", "price": 1000},
            {"id": "capillary_repair", "name": "Усунення засору капілярної трубки випарника", "price": 3500},
            {"id": "leak_repair", "name": "Усунення витоку в запененій частині", "price": "5000-8000"}
        ]
    },
    {
        "id": "washing",
        "title": "Ремонт пральних машин",
        "desc": "Діагностика, заміна підшипників, ремонт електроніки.",
        "details": "Ми діагностуємо, усуваємо несправності та відновлюємо роботу пральної машини будь-якої складності.",
        "warranty": [
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Гарантія Round - 1 або 2 роки",
            "Безкоштовне усунення заводських дефектів"
        ],
        "non_warranty": [
            "Пошкодження внаслідок використання нерекомендованих миючих засобів",
            "Протікання через неправильно вставлені люльки або шланги",
            "Поломки, спричинені засміченням каналізаційних шлангів",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "technical_act", "name": "Оформлення акту технічного стану апаратури (за одиницю техніки)", "price": 300},
            {"id": "false_call", "name": "Хибний виклик", "price": 300},
            {"id": "dryer_repair", "name": "Ремонт пральних машин з сушкою", "price": 2500},
            {"id": "handle_replacement", "name": "Заміна ручки", "price": 1200},
            {"id": "leak_repair", "name": "Усунення протікання", "price": 1200},
            {"id": "belt_replacement", "name": "Заміна ременя", "price": 1200},
            {"id": "door_replacement", "name": "Заміна люка", "price": 1200},
            {"id": "motor_replacement", "name": "Заміна двигуна", "price": 1200},
            {"id": "heater_replacement", "name": "Заміна ТЕНу", "price": 1200},
            {"id": "control_board_repair", "name": "Заміна/ремонт модуля керування", "price": "1500/3000"},
            {"id": "sensor_replacement", "name": "Заміна датчиків", "price": 1200},
            {"id": "pump_replacement", "name": "Заміна зливного насоса", "price": 1200},
            {"id": "shock_absorber_replacement", "name": "Заміна амортизаторів", "price": 1200},
            {"id": "valve_replacement", "name": "Заміна клапанів", "price": 1200},
            {"id": "door_lock_replacement", "name": "Заміна пристрою блокування люка", "price": 1200},
            {"id": "foreign_item_removal", "name": "Вилучення стороннього предмета (автоматична пральна машина)", "price": "1000-1200"},
            {"id": "foreign_item_removal_with_disassembly", "name": "Вилучення стороннього предмета з розбиранням бака", "price": 3000},
            {"id": "bearing_replacement", "name": "Заміна підшипників", "price": 3000},
            {"id": "tub_replacement", "name": "Заміна бака, барабана", "price": 3000},
            {"id": "gasket_replacement", "name": "Заміна ущільнювача (манжети)", "price": 1200}
        ]
    },
    {
        "id": "tv",
        "title": "Ремонт телевізорів",
        "desc": "Ремонт LCD, PLASMA, LED телевізорів.",
        "details": "Швидко усуваємо будь-які несправності: від блоків живлення до матриць.",
        "warranty": [
            "Гарантійний ремонт електронного модуля та сенсорів",
            "Заміна дефектних деталей",
            "Налаштування та калібрування"
        ],
        "non_warranty": [
            "Пошкодження внаслідок перепадів напруги, які не були захищені стабілізатором",
            "Механічні пошкодження при самостійному ремонті",
            "Поломки через перегрів або неправильну експлуатацію",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "lcd_led_repair_14", "name": "Ремонт LCD/LED-TV, PLASMA-TV від 14\"", "price": "від 1000"},
            {"id": "lcd_led_repair_21", "name": "Ремонт LCD/LED-TV, PLASMA-TV від 21\"", "price": "від 1500"}
        ]
    },
    {
        "id": "stove",
        "title": "Ремонт плит і духовок",
        "desc": "Плити, духові шафи, варильні поверхні.",
        "details": "Швидко усуваємо будь-які несправності: від датчиків до електронних плат.",
        "warranty": [
            "Гарантійний ремонт електронного модуля та сенсорів",
            "Відновлення роботи вбудованої техніки протягом гарантійного терміну",
            "Вирішення заводських дефектів управління та безпеки",
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Заміна несправних компонентів за рахунок виробника"
        ],
        "non_warranty": [
            "Пошкодження внаслідок перепадів напруги, які не були захищені стабілізатором",
            "Механічні пошкодження при самостійному ремонті",
            "Поломки через перегрів або переповнення (рідкаковий режим)",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "partial_repair", "name": "Регулювання, ремонт з частковим розбиранням техніки", "price": 500},
            {"id": "full_repair", "name": "Заміна/ремонт деталей з повною/частковим розбиранням техніки. Заміна перемикачів, ТЕНів, проводів, електроконфорок", "price": 800},
            {"id": "oven_replacement", "name": "Заміна духової шафи, термоізоляції духової шафи, заміна скла духовки, ремонт плати керування", "price": "від 800"}
        ]
    },
    {
        "id": "vacuum",
        "title": "Ремонт пилососів",
        "details": "Швидко усуваємо будь-які несправності пилососів.",
        "warranty": [
            "Гарантійний ремонт електронного модуля та сенсорів",
            "Відновлення роботи вбудованої техніки протягом гарантійного терміну",
            "Вирішення заводських дефектів управління та безпеки",
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Заміна несправних компонентів за рахунок виробника"
        ],
        "non_warranty": [
            "Пошкодження внаслідок неправильного використання",
            "Механічні пошкодження при самостійному ремонті",
            "Поломки через неправильну експлуатацію",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "repair", "name": "Ремонт пилососа", "price": "від 1000"}
        ]
    },
    {
        "id": "microwave",
        "title": "Ремонт СВЧ-печей",
        "desc": "Мікрохвильовки всіх виробників.",
        "details": "Швидко усуваємо будь-які несправності мікрохвильових печей.",
        "warranty": [
            "Гарантійний ремонт електронного модуля та сенсорів",
            "Відновлення роботи вбудованої техніки протягом гарантійного терміну",
            "Вирішення заводських дефектів управління та безпеки",
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Заміна несправних компонентів за рахунок виробника"
        ],
        "non_warranty": [
            "Пошкодження внаслідок неправильного використання",
            "Механічні пошкодження при самостійному ремонті",
            "Поломки через неправильну експлуатацію",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "magnetron_replacement", "name": "Заміна магнетрона", "price": 900},
            {"id": "panel_repair", "name": "Ремонт/заміна панелі керування", "price": "1300/від 900"},
            {"id": "mica_replacement", "name": "Заміна слюди", "price": 650},
            {"id": "other_repair", "name": "Інші види ремонту", "price": "за узгодженням"}
        ]
    },
    {
        "id": "water_heater",
        "title": "Ремонт водонагрівачів",
        "desc": "Бойлери, проточні водонагрівачі.",
        "details": "Швидко усуваємо будь-які несправності водонагрівачів.",
        "warranty": [
            "Гарантійний ремонт електронного модуля та сенсорів",
            "Відновлення роботи вбудованої техніки протягом гарантійного терміну",
            "Вирішення заводських дефектів управління та безпеки",
            "Гарантійний ремонт при наявності чека та гарантійного талона (корешок обов'язково)",
            "Заміна несправних компонентів за рахунок виробника"
        ],
        "non_warranty": [
            "Пошкодження внаслідок неправильного використання",
            "Механічні пошкодження при самостійному ремонті",
            "Поломки через неправильну експлуатацію",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "heater_replacement", "name": "Заміна нагрівального елемента", "price": 1500},
            {"id": "thermostat_replacement", "name": "Заміна терморегулятора", "price": 800},
            {"id": "valve_replacement", "name": "Заміна запобіжного клапана", "price": 700},
            {"id": "lamp_replacement", "name": "Заміна сигнальної лампочки, індикаторних елементів", "price": 700},
            {"id": "anode_replacement", "name": "Заміна магнієвого анода", "price": 1500},
            {"id": "flange_replacement", "name": "Заміна фланца/заміна прокладки", "price": "1500/1500"},
            {"id": "control_board_repair", "name": "Заміна модуля керування/ремонт", "price": "800/від 1100"},
            {"id": "maintenance", "name": "Профілактика (чистка водонагрівача)", "price": 1500},
            {"id": "false_call", "name": "Хибний виклик", "price": 300},
            {"id": "leak_diagnostic", "name": "Діагностика по течі бака у разі відмови від гарантії заводу виробника", "price": 300}
        ]
    }
]


def ensure_data_dir():
    """Create data directory and initialize files if they don't exist"""
    DATA_DIR.mkdir(exist_ok=True)
    
    # Initialize messages file
    if not MESSAGES_PATH.exists():
        MESSAGES_PATH.write_text("[]", encoding="utf-8")
    
    # Initialize prices file
    if not PRICES_PATH.exists():
        PRICES_PATH.write_text("{}", encoding="utf-8")
    
    # Initialize vacancies file
    if not VACANCIES_PATH.exists():
        VACANCIES_PATH.write_text("[]", encoding="utf-8")
    
    # Initialize resumes directory and file
    resumes_dir = Path("data/resumes")
    resumes_dir.mkdir(exist_ok=True)
    
    if not RESUMES_PATH.exists():
        RESUMES_PATH.write_text("[]", encoding="utf-8")


def load_messages():
    ensure_data_dir()
    try:
        messages = json.loads(MESSAGES_PATH.read_text(encoding="utf-8"))
        
        # Sort messages: new messages first (by position), then archived
        active_messages = [msg for msg in messages if not msg.get('archived', False)]
        archived_messages = [msg for msg in messages if msg.get('archived', False)]
        
        # Sort active messages by position (newest first)
        active_messages.sort(key=lambda x: x.get('position', 0), reverse=True)
        
        # Sort archived messages by archived date (newest first)
        archived_messages.sort(key=lambda x: x.get('archived_date', ''), reverse=True)
        
        return active_messages + archived_messages
        
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_messages(messages):
    ensure_data_dir()
    MESSAGES_PATH.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prices():
    ensure_data_dir()
    try:
        return json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_prices(prices):
    """Save prices to JSON file with error handling"""
    try:
        ensure_data_dir()
        PRICES_PATH.write_text(json.dumps(prices, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error saving prices: {e}")
        return False


def load_contact():
    """Load contact info from JSON file"""
    ensure_data_dir()
    try:
        contact_path = DATA_DIR / "contact.json"
        if contact_path.exists():
            return json.loads(contact_path.read_text(encoding="utf-8"))
        else:
            # Create default contact file
            default_contact = {
                "phones": ["+38 (067) 639-63-03", "+38 (097) 251-24-44"],
                "email": "service@atlant-kr.dp.ua",
                "address": "м. Кривий Ріг, вул. Січеславська, 3/47"
            }
            contact_path.write_text(json.dumps(default_contact, ensure_ascii=False, indent=2), encoding="utf-8")
            return default_contact
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "phones": ["+38 (067) 639-63-03", "+38 (097) 251-24-44"],
            "email": "service@atlant-kr.dp.ua",
            "address": "м. Кривий Ріг, вул. Січеславська, 3/47"
        }


def load_pages_content():
    """Load pages content from JSON file"""
    ensure_data_dir()
    try:
        pages_path = DATA_DIR / "pages_content.json"
        if pages_path.exists():
            return json.loads(pages_path.read_text(encoding="utf-8"))
        else:
            # Create default pages content
            default_content = {
                "index": {
                    "title": "Atlant Service — Сервіс побутової техніки",
                    "elements": {
                        "hero-title": "Професійний ремонт побутової техніки у Кривому Розі",
                        "hero-subtitle": "Сервісний центр Atlant Service пропонує гарантійний та не гарантійний ремонт побутової техніки всіх брендів",
                        "hero-cta": "Замовити виклик майстра"
                    }
                }
            }
            pages_path.write_text(json.dumps(default_content, ensure_ascii=False, indent=2), encoding="utf-8")
            return default_content
    except Exception as e:
        print(f"Error loading pages content: {e}")
        return {}

def save_pages_content(content):
    """Save pages content to JSON file"""
    try:
        ensure_data_dir()
        pages_path = DATA_DIR / "pages_content.json"
        pages_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error saving pages content: {e}")
        return False

def load_brands():
    """Load brands from JSON file"""
    ensure_data_dir()
    try:
        brands_path = DATA_DIR / "brands.json"
        if brands_path.exists():
            brands = json.loads(brands_path.read_text(encoding="utf-8"))
            print(f"DEBUG: Loaded brands from file: {brands}")  # Отладка
            return brands
        else:
            # Create default brands file with dictionary structure
            default_brands = {
                "ventolux": {
                    "service_info": "Телефон гарячої лінії VENTOLUX: 0-800-33-97-57 / 0-800-33-61-69"
                },
                "scandix": {
                    "service_info": "Телефон гарячої лінії SCANDILUX (SCANDIX): 0-800-217-697"
                },
                "vestfrost": {
                    "service_info": "Телефон гарячої лінії VESTFROST: 0-800-21-33-53"
                },
                "daewoo": {
                    "service_info": "Телефон гарячої лінії DAEWOO: 0-800-757-257"
                },
                "atlantic": {
                    "service_info": "Телефон гарячої лінії ATLANTIC та ROUND: 0-800-500-885"
                },
                "round": {
                    "service_info": "Телефон гарячої лінії ROUND та ATLANTIC: 0-800-500-885"
                },
                "beko": {
                    "service_info": "Телефон гарячої лінії BEKO та ALTUS: 0-800-500-432"
                },
                "altus": {
                    "service_info": "Телефон гарячої лінії ALTUS та BEKO: 0-800-500-432"
                },
                "gorenje": {
                    "service_info": "Телефон гарячої лінії GORENJE та Hisense: 0-800-300-024"
                },
                "hisense": {
                    "service_info": "Телефон гарячої лінії Hisense та GORENJE: 0-800-300-024"
                },
                "candy": {
                    "service_info": "Телефон гарячої лінії CANDY: 0-800-501-509"
                },
                "teka": {
                    "service_info": "Телефон гарячої лінії TEKA: 0-800-503-015"
                },
                "samsung": {
                    "service_info": "Телефон гарячої лінії Samsung: 0-800-503-081"
                },
                "quartz": {
                    "service_info": "Телефон гарячої лінії Quartz: +38 (067) 505-44-99"
                },
                "eleyus": {
                    "service_info": "Телефон гарячої лінії Eleyus: +38 (067) 653-50-51 / +38 (050) 437-90-04"
                },
                "hansa": {
                    "service_info": "Телефон гарячої лінії Hansa: 0-800-300-835"
                },
                "termex": {
                    "service_info": "Телефон гарячої лінії Termex: 0-800-500-610"
                },
                "edler": {
                    "service_info": "Телефон гарячої лінії Edler: (097) 77-236-77"
                },
                "greta": {
                    "service_info": "Телефон гарячої лінії Greta: 0-800-21-00-20"
                },
                "haier": {
                    "service_info": "Телефон гарячої лінії Haier: +38 (044) 299-98-80"
                },
                "interlux": {
                    "service_info": "Телефон гарячої лінії Interlux: 0-800-217-697"
                },
                "lg": {
                    "service_info": "Телефон гарячої лінії LG: 0-800-303-000"
                },
                "sharp": {
                    "service_info": "Телефон гарячої лінії Sharp: 0-800-60-10-22"
                }
            }
            brands_path.write_text(json.dumps(default_brands, ensure_ascii=False, indent=2), encoding="utf-8")
            return default_brands
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "ventolux": {
                "service_info": "Телефон гарячої лінії VENTOLUX: 0-800-33-97-57 / 0-800-33-61-69"
            },
            "scandix": {
                "service_info": "Телефон гарячої лінії SCANDILUX (SCANDIX): 0-800-217-697"
            },
            "vestfrost": {
                "service_info": "Телефон гарячої лінії VESTFROST: 0-800-21-33-53"
            },
            "daewoo": {
                "service_info": "Телефон гарячої лінії DAEWOO: 0-800-757-257"
            },
            "atlantic": {
                "service_info": "Телефон гарячої лінії ATLANTIC та ROUND: 0-800-500-885"
            },
            "round": {
                "service_info": "Телефон гарячої лінії ROUND та ATLANTIC: 0-800-500-885"
            },
            "beko": {
                "service_info": "Телефон гарячої лінії BEKO та ALTUS: 0-800-500-432"
            },
            "altus": {
                "service_info": "Телефон гарячої лінії ALTUS та BEKO: 0-800-500-432"
            },
            "gorenje": {
                "service_info": "Телефон гарячої лінії GORENJE та Hisense: 0-800-300-024"
            },
            "hisense": {
                "service_info": "Телефон гарячої лінії Hisense та GORENJE: 0-800-300-024"
            },
            "candy": {
                "service_info": "Телефон гарячої лінії CANDY: 0-800-501-509"
            },
            "teka": {
                "service_info": "Телефон гарячої лінії TEKA: 0-800-503-015"
            },
            "samsung": {
                "service_info": "Телефон гарячої лінії Samsung: 0-800-503-081"
            },
            "quartz": {
                "service_info": "Телефон гарячої лінії Quartz: +38 (067) 505-44-99"
            },
            "eleyus": {
                "service_info": "Телефон гарячої лінії Eleyus: +38 (067) 653-50-51 / +38 (050) 437-90-04"
            },
            "hansa": {
                "service_info": "Телефон гарячої лінії Hansa: 0-800-300-835"
            },
            "termex": {
                "service_info": "Телефон гарячої лінії Termex: 0-800-500-610"
            },
            "edler": {
                "service_info": "Телефон гарячої лінії Edler: (097) 77-236-77"
            },
            "greta": {
                "service_info": "Телефон гарячої лінії Greta: 0-800-21-00-20"
            },
            "haier": {
                "service_info": "Телефон гарячої лінії Haier: +38 (044) 299-98-80"
            },
            "interlux": {
                "service_info": "Телефон гарячої лінії Interlux: 0-800-217-697"
            },
            "lg": {
                "service_info": "Телефон гарячої лінії LG: 0-800-303-000"
            },
            "sharp": {
                "service_info": "Телефон гарячої лінії Sharp: 0-800-60-10-22"
            }
        }


def load_services():
    """Load services from JSON file"""
    ensure_data_dir()
    try:
        services_path = DATA_DIR / "services.json"
        if services_path.exists():
            services = json.loads(services_path.read_text(encoding="utf-8"))
            return services
        else:
            # Create default services file
            services_path.write_text(json.dumps(SERVICES_DATA, ensure_ascii=False, indent=2), encoding="utf-8")
            return SERVICES_DATA
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return SERVICES_DATA


# Initialize data from files
CONTACT = load_contact()
BRANDS = load_brands()
SERVICES = load_services()


def load_vacancies():
    """Load vacancies from JSON file"""
    ensure_data_dir()
    try:
        return json.loads(VACANCIES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_vacancies(vacancies):
    """Save vacancies to JSON file"""
    ensure_data_dir()
    VACANCIES_PATH.write_text(json.dumps(vacancies, ensure_ascii=False, indent=2), encoding="utf-8")


def check_auth(username, password):
    """Check if username and password are valid"""
    return username == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, password)


def send_email_notification(subject, message, to_email=None):
    """Send email notification to admin"""
    try:
        print(f"[DEBUG] Starting email notification process...", flush=True)
        
        # Load email settings from file
        ensure_data_dir()
        email_settings_path = DATA_DIR / "email_settings.json"
        
        print(f"[DEBUG] Email settings path: {email_settings_path}", flush=True)
        print(f"[DEBUG] Email settings file exists: {email_settings_path.exists()}", flush=True)
        
        if not email_settings_path.exists():
            print("Email settings file not found, skipping notification", flush=True)
            return False
        
        settings = json.loads(email_settings_path.read_text(encoding="utf-8"))
        print(f"[DEBUG] Email settings loaded: {list(settings.keys())}", flush=True)
        
        email_username = settings.get("email_username", "")
        email_password = settings.get("email_password", "")
        email_server = settings.get("email_server", "smtp.gmail.com")
        email_port = settings.get("email_port", 587)
        email_use_tls = settings.get("email_use_tls", True)
        admin_email = settings.get("admin_email", "")
        
        print(f"[DEBUG] Email username: {email_username}", flush=True)
        print(f"[DEBUG] Email password configured: {bool(email_password)}", flush=True)
        print(f"[DEBUG] Admin email: {admin_email}", flush=True)
        
        if not email_username or not email_password or not (to_email or admin_email):
            print("Email credentials not configured, skipping notification", flush=True)
            return False
        
        print(f"[DEBUG] Attempting to connect to SMTP server: {email_server}:{email_port}", flush=True)
        
        msg = MIMEMultipart()
        msg['From'] = email_username
        msg['To'] = to_email or admin_email
        msg['Subject'] = subject
        
        # Create HTML email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                <h2 style="color: #007bff; margin-top: 0;">{subject}</h2>
                <div style="color: #333; line-height: 1.6;">
                    {message}
                </div>
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                <p style="color: #6c757d; font-size: 14px; margin-bottom: 0;">
                    Це автоматичне сповіщення від системи адміністрування Atlant Service.<br>
                    Будь ласка, не відповідайте на цей лист.
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Send email
        server = smtplib.SMTP(email_server, email_port)
        print(f"[DEBUG] Connected to SMTP server", flush=True)
        
        if email_use_tls:
            print(f"[DEBUG] Starting TLS...", flush=True)
            server.starttls()
            print(f"[DEBUG] TLS started", flush=True)
        
        print(f"[DEBUG] Attempting login...", flush=True)
        server.login(email_username, email_password)
        print(f"[DEBUG] Login successful", flush=True)
        
        server.send_message(msg)
        print(f"[DEBUG] Message sent", flush=True)
        
        server.quit()
        
        print(f"Email notification sent to {to_email or admin_email}", flush=True)
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def send_contact_email(name, phone, message):
    """Send contact form email to admin"""
    try:
        print(f"[DEBUG] Starting contact email process...", flush=True)
        
        # Load email settings from file
        ensure_data_dir()
        email_settings_path = DATA_DIR / "email_settings.json"
        
        if not email_settings_path.exists():
            print("Email settings file not found, skipping contact email", flush=True)
            return False
        
        settings = json.loads(email_settings_path.read_text(encoding="utf-8"))
        
        email_username = settings.get("email_username", "")
        email_password = settings.get("email_password", "")
        email_server = settings.get("email_server", "smtp.gmail.com")
        email_port = settings.get("email_port", 587)
        email_use_tls = settings.get("email_use_tls", True)
        admin_email = settings.get("admin_email", "")
        
        if not email_username or not email_password or not admin_email:
            print("Email credentials not configured, skipping contact email", flush=True)
            return False
        
        print(f"[DEBUG] Attempting to connect to SMTP server: {email_server}:{email_port}", flush=True)
        
        msg = MIMEMultipart()
        msg['From'] = email_username
        msg['To'] = admin_email
        msg['Subject'] = f"Нове звернення з сайту Atlant Service - {name}"
        
        # Create HTML body for contact email
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #007bff; margin-bottom: 20px;">Нове звернення з контактної форми</h2>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #333; margin-bottom: 10px;">Інформація про клієнта:</h3>
                    <p style="margin: 5px 0;"><strong>Ім'я:</strong> {name}</p>
                    <p style="margin: 5px 0;"><strong>Телефон:</strong> {phone}</p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #333; margin-bottom: 10px;">Повідомлення:</h3>
                    <p style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 0;">{message}</p>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px;">
                    <p style="margin: 0;">Це повідомлення було автоматично надіслано з контактної форми сайту Atlant Service.</p>
                    <p style="margin: 5px 0;">Будь ласка, зв'яжіться з клієнтом якомога швидше.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Send email
        server = smtplib.SMTP(email_server, email_port)
        print(f"[DEBUG] Connected to SMTP server", flush=True)
        
        if email_use_tls:
            print(f"[DEBUG] Starting TLS...", flush=True)
            server.starttls()
            print(f"[DEBUG] TLS started", flush=True)
        
        print(f"[DEBUG] Attempting login...", flush=True)
        server.login(email_username, email_password)
        print(f"[DEBUG] Login successful", flush=True)
        
        server.send_message(msg)
        print(f"[DEBUG] Contact email sent", flush=True)
        
        server.quit()
        
        print(f"Contact email sent to admin for {name}", flush=True)
        return True
        
    except Exception as e:
        print(f"Error sending contact email: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def authenticate():
    """Return authentication response"""
    return Response(
        "Увійдіть для доступу", 401, {"WWW-Authenticate": "Basic realm=\"Atlant Service Admin\""}
    )


def requires_auth(f):
    """Decorator to require authentication for admin routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if user is authenticated via session
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        
        if check_auth(username, password):
            session['admin_authenticated'] = True
            session['admin_login_time'] = datetime.now().isoformat()
            session.permanent = remember
            
            flash("Вхід успішний! Ласкаво просимо до адмін-панелі.", "success")
            return redirect(url_for("admin_messages"))
        else:
            flash("Неправильний логін або пароль. Спробуйте ще раз.", "error")
            return redirect(url_for("admin_login"))
    
    # If already authenticated, redirect to admin panel
    if session.get('admin_authenticated'):
        return redirect(url_for("admin_messages"))
    
    return render_template("admin_login.html")


@app.route("/admin/messages/delete/<int:message_index>", methods=["POST"])
@requires_auth
def admin_delete_message(message_index):
    """Delete a message by index"""
    try:
        messages = load_messages()
        
        # Validate index
        if message_index < 0 or message_index >= len(messages):
            return jsonify({"success": False, "error": "Невірний індекс повідомлення"})
        
        # Delete the message
        deleted_message = messages.pop(message_index)
        save_messages(messages)
        
        return jsonify({"success": True, "message": "Заявку успішно видалено"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/messages/status/<int:message_index>", methods=["POST"])
@requires_auth
def admin_update_status(message_index):
    """Update message status"""
    try:
        messages = load_messages()
        
        # Validate index
        if message_index < 0 or message_index >= len(messages):
            return jsonify({"success": False, "error": "Невірний індекс повідомлення"})
        
        # Get status data
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"success": False, "error": "Відсутні дані статусу"})
        
        new_status = data['status']
        valid_statuses = ['new', 'in_progress', 'completed', 'failed']
        
        if new_status not in valid_statuses:
            return jsonify({"success": False, "error": "Недійсний статус"})
        
        # Update message status
        old_status = messages[message_index]['status']
        messages[message_index]['status'] = new_status
        messages[message_index]['status_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # If status is completed or failed, move to archive position
        if new_status in ['completed', 'failed']:
            messages[message_index]['archived'] = True
            messages[message_index]['archived_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif old_status in ['completed', 'failed'] and new_status in ['new', 'in_progress']:
            messages[message_index]['archived'] = False
            if 'archived_date' in messages[message_index]:
                del messages[message_index]['archived_date']
        
        save_messages(messages)
        
        return jsonify({
            "success": True, 
            "message": f"Статус змінено на {new_status}",
            "status": new_status,
            "status_updated": messages[message_index]['status_updated']
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/messages/comment/<int:message_index>", methods=["POST"])
@requires_auth
def admin_update_comment(message_index):
    """Update or add comment to a message"""
    try:
        messages = load_messages()
        
        # Validate index
        if message_index < 0 or message_index >= len(messages):
            return jsonify({"success": False, "error": "Невірний індекс повідомлення"})
        
        # Get comment data
        data = request.get_json()
        if not data or 'comment' not in data:
            return jsonify({"success": False, "error": "Відсутні дані коментаря"})
        
        # Update message with comment
        messages[message_index]['comment'] = data['comment']
        messages[message_index]['comment_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        save_messages(messages)
        
        return jsonify({
            "success": True, 
            "message": "Коментар успішно збережено",
            "comment_date": messages[message_index]['comment_date']
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/logout")
def admin_logout():
    """Admin logout"""
    session.clear()
    flash("Ви успішно вийшли з системи.", "success")
    return redirect(url_for("admin_login"))


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now().year,
        "contact": CONTACT,
        "brands": BRANDS,
        "services": SERVICES,
        "vacancies": load_vacancies(),
    }


@app.route("/test-page-editor")
def test_page_editor():
    """Test page editor"""
    return render_template("test_page_editor.html")

@app.route("/test")
def test():
    """Simple test route"""
    return "Server is working! Time: " + str(datetime.now())

@app.route("/")
def index():
    brands = load_brands()  # Загружаем актуальные данные брендов
    pages_content = load_pages_content()
    page_data = pages_content.get('index', {})
    
    response = app.make_response(render_template("index.html", brands=brands, contact=CONTACT, page_content=page_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/test-iframe")
def test_iframe():
    """Test iframe loading"""
    brands = load_brands()
    pages_content = load_pages_content()
    page_data = pages_content.get('index', {})
    
    response = app.make_response(render_template("test_iframe.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/warranty")
def warranty():
    brands = load_brands()  # Загружаем актуальные данные брендов
    pages_content = load_pages_content()
    page_data = pages_content.get('warranty', {})
    response = app.make_response(render_template("warranty.html", brands=brands, contact=CONTACT, page_content=page_data))
    return response


@app.route("/admin/page-editor")
@requires_auth
def admin_page_editor():
    """Visual page editor"""
    return render_template("admin_page_editor.html", active_tab="editor")

@app.route("/api/pages-content", methods=["GET", "POST"])
def api_pages_content():
    """API for pages content management"""
    if request.method == "GET":
        return jsonify(load_pages_content())
    
    elif request.method == "POST":
        try:
            content = request.get_json()
            if save_pages_content(content):
                return jsonify({"success": True, "message": "Контент збережено успішно"})
            else:
                return jsonify({"success": False, "error": "Помилка збереження"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

@app.route("/test-form")
def test_form():
    return render_template("test_form.html")

@app.route("/test-brands")
def test_brands():
    brands = load_brands()
    print(f"DEBUG: Test brands route loaded: {brands}")  # Отладка
    return render_template("test_brands.html", brands=brands)

@app.route("/services")
def services():
    services = load_services()  # Загружаем актуальные данные из файла
    prices = load_prices()
    brands = load_brands()  # Загружаем актуальные данные брендов
    pages_content = load_pages_content()
    page_data = pages_content.get('services', {})
    
    # Убедимся, что все данные в UTF-8
    response = app.make_response(render_template("services.html", services=services, prices=prices, brands=brands, contact=CONTACT, page_content=page_data))
    # Отключаем кеширование для этой страницы
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/terms")
def terms():
    brands = load_brands()  # Загружаем актуальные данные брендов
    pages_content = load_pages_content()
    page_data = pages_content.get('terms', {})
    
    response = app.make_response(render_template("terms.html", brands=brands, contact=CONTACT, page_content=page_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        message = request.form.get("message")

        if not name or not phone or not message:
            flash("Будь ласка, заповніть всі поля форми", "warning")
            return redirect(url_for("contact"))

        try:
            # Сохранение заявки в систему
            messages = load_messages()
            new_message = {
                "id": len(messages) + 1,
                "name": name,
                "phone": phone,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "new",
                "type": "contact",
                "position": len(messages)  # Позиция для сортировки
            }
            messages.append(new_message)
            save_messages(messages)
            
            # Отправка email
            send_contact_email(name, phone, message)
            flash("Дякуємо за ваше звернення! Ми зв'яжемося з вами найближчим часом.", "success")
        except Exception as e:
            flash(f"Помилка відправки: {e}", "error")

        return redirect(url_for("index") + "#contact")
    
    # GET запрос - показываем страницу контактов
    brands = load_brands()
    pages_content = load_pages_content()
    page_data = pages_content.get('contact', {})
    response = app.make_response(render_template("contact.html", brands=brands, contact=CONTACT, page_content=page_data))
    return response


@app.route("/admin/messages")
@requires_auth
def admin_messages():
    messages_list = load_messages()
    return render_template("admin_messages.html", messages_list=messages_list, active_tab="messages")


@app.route("/admin/prices/update", methods=["POST"])
@requires_auth
def update_price():
    prices = {}
    for key, value in request.form.items():
        if value and value.strip():
            try:
                float(value)
                prices[key] = value
            except ValueError:
                prices[key] = value
        else:
            prices[key] = "0"
    
    # Завантажуємо існуючі ціни
    existing_prices = load_prices()
    existing_prices.update(prices)
    save_prices(existing_prices)
    
    return {"success": True, "message": "Ціну оновлено"}


@app.route("/admin/vacancies")
@requires_auth
def admin_vacancies():
    vacancies_list = load_vacancies()
    return render_template("admin_vacancies.html", vacancies_list=vacancies_list, active_tab="vacancies")

@app.route("/admin/vacancies/add", methods=["POST"])
@requires_auth
def admin_add_vacancy():
    """Add new vacancy"""
    try:
        vacancies = load_vacancies()
        
        # Get JSON data
        data = request.get_json()
        
        # Get form data
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        requirements = data.get("requirements", [])
        if isinstance(requirements, str):
            requirements = requirements.strip()
        salary = data.get("salary", "").strip()
        contact = data.get("contact", "").strip()
        status = data.get("status", "active").strip()
        
        # Validate required fields
        if not title or not description:
            return jsonify({"success": False, "error": "Назва та опис обов'язкові"})
        
        # Create new vacancy
        new_vacancy = {
            "id": len(vacancies) + 1,
            "title": title,
            "description": description,
            "requirements": requirements,
            "salary": salary,
            "contact": contact,
            "status": status,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        vacancies.append(new_vacancy)
        save_vacancies(vacancies)
        
        return jsonify({
            "success": True, 
            "message": "Вакансію успішно додано",
            "vacancy": new_vacancy
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/admin/vacancies/update/<int:vacancy_id>", methods=["POST"])
@requires_auth
def admin_update_vacancy(vacancy_id):
    """Update existing vacancy"""
    try:
        vacancies = load_vacancies()
        
        # Find vacancy by ID
        vacancy_index = None
        for i, vacancy in enumerate(vacancies):
            if vacancy["id"] == vacancy_id:
                vacancy_index = i
                break
        
        if vacancy_index is None:
            return jsonify({"success": False, "error": "Вакансію не знайдено"})
        
        # Get JSON data
        data = request.get_json()
        
        # Get form data
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        requirements = data.get("requirements", [])
        if isinstance(requirements, str):
            requirements = requirements.strip()
        salary = data.get("salary", "").strip()
        contact = data.get("contact", "").strip()
        status = data.get("status", "active").strip()
        
        # Update vacancy
        vacancies[vacancy_index].update({
            "title": title,
            "description": description,
            "requirements": requirements,
            "salary": salary,
            "contact": contact,
            "status": status,
            "updated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        save_vacancies(vacancies)
        
        return jsonify({
            "success": True,
            "message": "Вакансію успішно оновлено",
            "vacancy": vacancies[vacancy_index]
        })
    except Exception as e:
        print(f"Error submitting resume: {e}")
        return jsonify({'success': False, 'error': 'Помилка при обробці резюме'})

@app.route("/submit-resume", methods=["POST"])
def submit_resume():
    """Handle resume submission"""
    try:
        import uuid  # Import uuid at the beginning of the function
        
        print(f"Resume submission attempt: {request.form}")
        
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        position = request.form.get('position', '').strip()
        experience = request.form.get('experience', '').strip()
        skills = request.form.get('skills', '').strip()
        message = request.form.get('message', '').strip()
        
        print(f"Form data received - Name: {name}, Email: {email}, Phone: {phone}")
        
        # Validate required fields
        if not name or not email:
            error_msg = "Ім'я та email є обов'язковими полями"
            print(f"Validation error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            error_msg = 'Некоректний формат email'
            print(f"Email validation error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})
        
        # Handle file upload (optional)
        resume_file = request.files.get('resume_file')
        resume_filename = None
        
        print(f"File upload attempt: {resume_file}")
        
        # Check if file was actually uploaded and has content
        if resume_file and resume_file.filename and resume_file.filename != '':
            print(f"Processing file: {resume_file.filename}")
            
            # Check file extension
            allowed_extensions = {'.pdf', '.doc', '.docx'}
            file_ext = os.path.splitext(resume_file.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                error_msg = 'Дозволені тільки файли PDF, DOC, DOCX'
                print(f"File extension error: {error_msg}")
                return jsonify({'success': False, 'error': error_msg})
            
            # Check file size (5MB limit) - read content to check size
            try:
                file_content = resume_file.read()
                file_size = len(file_content)
                
                if file_size > 5 * 1024 * 1024:
                    error_msg = 'Розмір файлу не повинен перевищувати 5MB'
                    print(f"File size error: {error_msg}, size: {file_size}")
                    return jsonify({'success': False, 'error': error_msg})
                
                # Generate unique filename
                unique_id = str(uuid.uuid4())
                file_ext = os.path.splitext(resume_file.filename)[1].lower()
                resume_filename = f"resume_{unique_id}{file_ext}"
                
                # Create resumes directory if it doesn't exist
                resume_dir = Path("data/resumes")
                resume_dir.mkdir(exist_ok=True)
                
                # Reset file pointer and save file
                from io import BytesIO
                file_stream = BytesIO(file_content)
                with open(resume_dir / resume_filename, 'wb') as f:
                    f.write(file_content)
                
                print(f"File saved successfully: {resume_filename}")
                
            except Exception as file_error:
                error_msg = f'Помилка обробки файлу: {str(file_error)}'
                print(f"File processing error: {error_msg}")
                return jsonify({'success': False, 'error': error_msg})
        else:
            print("No file uploaded or file is empty - proceeding without file")
        
        # Load existing resumes
        resumes = load_resumes()
        
        # Create new resume entry
        new_resume = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": phone,
            "position": position,
            "experience": experience,
            "skills": skills,
            "message": message,
            "resume_file": resume_filename,
            "created_date": datetime.now().strftime("%d.%m.%Y"),
            "status": "new"
        }
        
        print(f"Creating resume entry: {new_resume['id']}")
        
        # Add to resumes list
        resumes.append(new_resume)
        save_resumes(resumes)
        
        # Відправляємо email сповіщення адміну
        try:
            email_message = f"""
            <p><strong>Нове резюме від кандидата!</strong></p>
            <p><strong>Ім'я:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Телефон:</strong> {phone}</p>
            <p><strong>Бажана посада:</strong> {position}</p>
            <p><strong>Досвід:</strong></p>
            <p style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{experience}</p>
            <p><strong>Навички:</strong></p>
            <p style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{skills}</p>
            <p><strong>Повідомлення:</strong></p>
            <p style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">{message}</p>
            <p><strong>Час:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            <p><strong>Файл резюме:</strong> {resume_filename or 'Не завантажено'}</p>
            <p><a href="{request.host_url}admin/resumes" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Переглянути в адмін панелі</a></p>
            """
            send_email_notification("📄 Нове резюме від кандидата", email_message)
        except Exception as e:
            print(f"Error sending resume email notification: {e}")
        
        print("Resume saved successfully")
        
        # Check if request is AJAX (has X-Requested-With header)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Резюме успішно надіслано'})
        else:
            return redirect(url_for('contact') + '?resume_success=true#resume-tab')
        
    except Exception as e:
        error_msg = f'Помилка при обробці резюме: {str(e)}'
        print(f"General error: {error_msg}")
        
        # Check if request is AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': error_msg})
        else:
            flash(error_msg, 'error')
            return redirect(url_for('contact') + '#resume-tab')

@app.route("/admin/resumes")
@requires_auth
def admin_resumes():
    """Admin page for viewing resumes"""
    resumes_list = load_resumes()
    return render_template("admin_resumes.html", resumes_list=resumes_list, active_tab="resumes")

@app.route("/download-resume/<filename>")
@requires_auth
def download_resume(filename):
    """Download resume file"""
    try:
        resume_dir = Path("data/resumes")
        file_path = resume_dir / filename
        
        if not file_path.exists():
            return "Файл не знайдено", 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Error downloading resume: {e}")
        return "Помилка при завантаженні файлу", 500

@app.route("/admin/resumes/update-status", methods=["POST"])
@requires_auth
def update_resume_status():
    """Update resume status"""
    try:
        data = request.get_json()
        resume_id = data.get('resume_id')
        new_status = data.get('status')
        
        if not resume_id:
            return jsonify({'success': False, 'error': 'Відсутні обов\'язкові поля'})
        
        resumes = load_resumes()
        
        # Find and update resume
        updated = False
        for resume in resumes:
            if resume['id'] == resume_id:
                if new_status:
                    resume['status'] = new_status
                else:
                    # Toggle status if no new status provided
                    resume['status'] = 'processed' if resume['status'] == 'new' else 'new'
                updated = True
                break
        
        if not updated:
            return jsonify({'success': False, 'error': 'Резюме не знайдено'})
        
        save_resumes(resumes)
        
        return jsonify({
            'success': True, 
            'message': 'Статус успішно оновлено',
            'status': resume['status']
        })
        
    except Exception as e:
        print(f"Error updating resume status: {e}")
        return jsonify({'success': False, 'error': 'Помилка при оновленні статусу'})

@app.route("/admin/resumes/delete", methods=["POST"])
@requires_auth
def delete_resume():
    """Delete resume"""
    try:
        data = request.get_json()
        resume_id = data.get('resume_id')
        
        if not resume_id:
            return jsonify({'success': False, 'error': 'Відсутні обов\'язкові поля'})
        
        resumes = load_resumes()
        
        # Find and remove resume
        initial_count = len(resumes)
        resumes = [r for r in resumes if r['id'] != resume_id]
        
        if len(resumes) == initial_count:
            return jsonify({'success': False, 'error': 'Резюме не знайдено'})
        
        save_resumes(resumes)
        
        return jsonify({
            'success': True,
            'message': 'Резюме успішно видалено'
        })
        
    except Exception as e:
        print(f"Error deleting resume: {e}")
        return jsonify({'success': False, 'error': 'Помилка при видаленні резюме'})

def load_resumes():
    """Load resumes from JSON file"""
    ensure_data_dir()
    try:
        if RESUMES_PATH.exists():
            return json.loads(RESUMES_PATH.read_text(encoding="utf-8"))
        return []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_resumes(resumes):
    """Save resumes to JSON file"""
    ensure_data_dir()
    RESUMES_PATH.write_text(json.dumps(resumes, ensure_ascii=False, indent=2), encoding="utf-8")

@app.route("/admin/vacancies/delete/<int:vacancy_id>", methods=["POST"])
def admin_delete_vacancy(vacancy_id):
    """Delete vacancy"""
    try:
        vacancies = load_vacancies()
        
        # Find and remove vacancy by ID
        updated_vacancies = []
        deleted_vacancy = None
        
        for vacancy in vacancies:
            if vacancy["id"] == vacancy_id:
                deleted_vacancy = vacancy
            else:
                updated_vacancies.append(vacancy)
        
        if not deleted_vacancy:
            return jsonify({"success": False, "error": "Вакансію не знайдено"})
        
        save_vacancies(updated_vacancies)
        
        return jsonify({
            "success": True,
            "message": "Вакансію успішно видалено",
            "vacancy": deleted_vacancy
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/vacancies")
def vacancies():
    """Public vacancies page"""
    all_vacancies = load_vacancies()
    # Show only active vacancies
    active_vacancies = [v for v in all_vacancies if v.get("status") == "active"]
    
    # Load page content
    pages_content = load_pages_content()
    page_data = pages_content.get('vacancies', {})
    
    return render_template("vacancies.html", vacancies=active_vacancies, page_content=page_data)

@app.route("/admin/email-settings", methods=["GET", "POST"])
@requires_auth
def admin_email_settings():
    """Admin email settings management page"""
    if request.method == "POST":
        try:
            # Get form data
            admin_email = request.form.get("admin_email", "").strip()
            email_username = request.form.get("email_username", "").strip()
            email_password = request.form.get("email_password", "").strip()
            email_server = request.form.get("email_server", "").strip()
            email_port = request.form.get("email_port", "").strip()
            email_use_tls = request.form.get("email_use_tls", "true").lower() == "true"
            
            # Validate required fields
            if not admin_email or not email_username or not email_password:
                flash("Заповніть всі обов'язкові поля!", "error")
                return redirect(url_for("admin_email_settings"))
            
            # Create email settings
            email_settings = {
                "admin_email": admin_email,
                "email_username": email_username,
                "email_password": email_password,
                "email_server": email_server or "smtp.gmail.com",
                "email_port": int(email_port) if email_port else 587,
                "email_use_tls": email_use_tls
            }
            
            # Save to file
            ensure_data_dir()
            email_settings_path = DATA_DIR / "email_settings.json"
            email_settings_path.write_text(json.dumps(email_settings, ensure_ascii=False, indent=2), encoding="utf-8")
            
            flash("Email налаштування успішно збережено!", "success")
            
        except Exception as e:
            flash(f"Помилка збереження налаштувань: {e}", "error")
        
        return redirect(url_for("admin_email_settings"))
    
    # Load current settings
    try:
        ensure_data_dir()
        email_settings_path = DATA_DIR / "email_settings.json"
        if email_settings_path.exists():
            settings = json.loads(email_settings_path.read_text(encoding="utf-8"))
        else:
            settings = {}
    except:
        settings = {}
    
    return render_template("admin_email_settings.html", settings=settings, active_tab="email")


@app.route("/admin/brands", methods=["GET", "POST"])
@requires_auth
def admin_brands():
    """Admin brands management page"""
    if request.method == "POST":
        try:
            # Handle JSON requests (AJAX)
            if request.is_json:
                data = request.get_json()
            else:
                # Handle form requests (including file uploads)
                data = request.form.to_dict()
            
            brand_id = data.get("brand_id", "").strip().lower()
            brand_name = data.get("brand_name", "").strip()
            service_info = data.get("service_info", "").strip()
            requirements = data.get("requirements", "").strip()
            original_brand_id = data.get("original_brand_id", "").strip().lower()
            
            if not brand_id or not brand_name or not service_info:
                if request.is_json:
                    return jsonify({"success": False, "error": "Заповніть обов'язкові поля!"})
                flash("Заповніть обов'язкові поля!", "error")
                return redirect(url_for("admin_brands"))
            
            # Load current brands
            brands = load_brands()
            
            # Handle brand rename (if original_id exists and is different)
            if original_brand_id and original_brand_id != brand_id:
                if original_brand_id in brands:
                    # Remove old brand
                    brands.pop(original_brand_id)
            
            # Update or add brand with new structure
            brands[brand_id] = {
                "name": brand_name,
                "service_info": service_info,
                "requirements": requirements.split('\n') if requirements else []
            }
            
            # Handle logo file upload
            if 'logo_file' in request.files:
                logo_file = request.files['logo_file']
                if logo_file and logo_file.filename:
                    # Create brands directory if it doesn't exist
                    brands_dir = Path('static/img/brands')
                    brands_dir.mkdir(exist_ok=True)
                    
                    # Save logo as brand_id.png
                    logo_filename = f"{brand_id}.png"
                    logo_path = brands_dir / logo_filename
                    logo_file.save(logo_path)
                    print(f"Logo saved: {logo_path}")
            
            # Save to file
            ensure_data_dir()
            brands_path = DATA_DIR / "brands.json"
            brands_path.write_text(json.dumps(brands, ensure_ascii=False, indent=2), encoding="utf-8")
            
            if request.is_json:
                return jsonify({"success": True, "message": "Інформацію про бренд успішно збережено!"})
            flash("Інформацію про бренд успішно збережено!", "success")
            
        except Exception as e:
            if request.is_json:
                return jsonify({"success": False, "error": str(e)})
            flash(f"Помилка збереження: {e}", "error")
        
        if not request.is_json:
            return redirect(url_for("admin_brands"))
    
    brands = load_brands()
    return render_template("admin_brands.html", brands=brands, active_tab="brands")

@app.route("/admin/brands/delete/<brand_id>", methods=["POST"])
@requires_auth
def admin_delete_brand(brand_id):
    """Delete a brand by ID"""
    try:
        brands = load_brands()
        
        # Validate brand exists
        if brand_id not in brands:
            return jsonify({"success": False, "error": "Бренд не знайдено"})
        
        # Delete the brand
        deleted_brand = brands.pop(brand_id)
        
        # Save to file
        ensure_data_dir()
        brands_path = DATA_DIR / "brands.json"
        brands_path.write_text(json.dumps(brands, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return jsonify({"success": True, "message": f"Бренд {brand_id.upper()} успішно видалено"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/admin/services", methods=["GET", "POST"])
@requires_auth
def admin_services():
    """Admin services management page with prices"""
    try:
        if request.method == 'POST':
            # Handle JSON requests (AJAX)
            if request.is_json:
                data = request.get_json()
            else:
                # Handle form requests
                data = request.form.to_dict()
            
            # Check if this is price submission or service management
            if 'price_update' in data or 'service_id' not in data:
                # Handle price updates (old logic)
                prices = {}
                existing_prices = load_prices()
                
                if 'price_update' in data:
                    # Handle single service update
                    service_id = data.get("service_id", "").strip()
                    if service_id:
                        diagnostic_price = data.get(f"diagnostic_{service_id}", "0")
                        try:
                            prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
                        except ValueError:
                            prices[f"diagnostic_{service_id}"] = diagnostic_price
                        
                        # Load services to get non_warranty_cases
                        services = load_services()
                        service = next((s for s in services if s.get("id") == service_id), None)
                        
                        if service and "non_warranty_cases" in service:
                            for case in service["non_warranty_cases"]:
                                case_price = data.get(f"case_{service_id}_{case['id']}", "0")
                                try:
                                    float(case_price)
                                    prices[f"case_{service_id}_{case['id']}"] = case_price
                                except ValueError:
                                    prices[f"case_{service_id}_{case['id']}"] = case_price
                            else:
                                prices[f"case_{service_id}_{case['id']}"] = "0"
                    
                    # Merge with existing prices
                    existing_prices.update(prices)
                    save_prices(existing_prices)
                else:
                    # Handle all services (old logic)
                    services = load_services()
                    for service in services:
                        service_id = service["id"]
                        
                        diagnostic_price = request.form.get(f"diagnostic_{service_id}", "0")
                        try:
                            prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
                        except ValueError:
                            prices[f"diagnostic_{service_id}"] = 0
                        
                        if "non_warranty_cases" in service:
                            for case in service["non_warranty_cases"]:
                                case_price = request.form.get(f"case_{service_id}_{case['id']}", "0")
                                try:
                                    float(case_price)
                                    prices[f"case_{service_id}_{case['id']}"] = case_price
                                except ValueError:
                                    prices[f"case_{service_id}_{case['id']}"] = case_price
                
                save_prices(prices)
                
                flash("Ціни успішно оновлено!", "success")
                return redirect(url_for("admin_services"))
            
            # Handle service management (new functionality)
            service_id = data.get("service_id", "").strip()
            service_title = data.get("service_title", "").strip()
            service_desc = data.get("service_desc", "").strip()
            service_details = data.get("service_details", "").strip()
            service_items = data.get("items", [])
            
            if not service_id or not service_title:
                if request.is_json:
                    return jsonify({"success": False, "error": "Заповніть обов'язкові поля!"})
                flash("Заповніть обов'язкові поля!", "error")
                return redirect(url_for("admin_services"))
            
            # Load current services
            services = load_services()
            
            # Find service by ID or create new
            service_found = False
            for service in services:
                if service.get("id") == service_id:
                    service["title"] = service_title
                    service["desc"] = service_desc
                    service["details"] = service_details
                    service["items"] = service_items
                    service_found = True
                    break
            
            if not service_found:
                # Add new service
                new_service = {
                    "id": service_id,
                    "title": service_title,
                    "desc": service_desc,
                    "details": service_details,
                    "items": service_items,
                    "warranty": [],
                    "non_warranty": [],
                    "non_warranty_cases": []
                }
                services.append(new_service)
            
            # Save services to file
            ensure_data_dir()
            services_path = DATA_DIR / "services.json"
            services_path.write_text(json.dumps(services, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Saved services to {services_path}")
            print(f"Updated service: {service_id} -> {service_title}")
            
            # Handle prices for both JSON and form requests
            # Save diagnostic price
            diagnostic_price = data.get("diagnostic_price", "300")
            try:
                prices = {}
                existing_prices = load_prices()
                prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
            except ValueError:
                prices[f"diagnostic_{service_id}"] = diagnostic_price
            
            # Save case prices
            for key, value in data.items():
                if key.startswith(f"case_{service_id}_"):
                    try:
                        float(value)
                        prices[key] = value
                    except ValueError:
                        prices[key] = value
            
            # Merge with existing prices
            existing_prices.update(prices)
            save_prices(existing_prices)
            
            if request.is_json:
                return jsonify({"success": True, "message": "Послугу та ціни успішно збережено!"})
            flash("Послугу успішно збережено!", "success")
        
    except Exception as e:
        if request.is_json:
            return jsonify({"success": False, "error": str(e)})
        flash(f"Помилка збереження: {e}", "error")
        if not request.is_json:
            return redirect(url_for("admin_services"))
    
    services = load_services()
    prices = load_prices()
    return render_template("admin_services.html", services=services, prices=prices, active_tab="services")


@app.route("/admin/services/add", methods=["POST"])
@requires_auth
def admin_services_add():
    """Add new service"""
    return admin_services()


@app.route("/admin/services/update/<service_id>", methods=["POST"])
@requires_auth
def admin_services_update(service_id):
    """Update existing service"""
    try:
        # Handle JSON requests (AJAX)
        if request.is_json:
            data = request.get_json()
        else:
            # Handle form requests
            data = request.form.to_dict()
        
        # Get service data
        service_title = data.get("service_title", "").strip()
        service_desc = data.get("service_desc", "").strip()
        service_details = data.get("service_details", "").strip()
        
        if not service_title:
            return jsonify({"success": False, "error": "Заповніть обов'язкові поля!"})
        
        # Load and update service
        services = load_services()
        service_found = False
        
        for service in services:
            if service.get("id") == service_id:
                service["title"] = service_title
                service["desc"] = service_desc
                service["details"] = service_details
                service_found = True
                break
        
        if not service_found:
            return jsonify({"success": False, "error": "Послугу не знайдено!"})
        
        # Save services
        ensure_data_dir()
        services_path = DATA_DIR / "services.json"
        services_path.write_text(json.dumps(services, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Handle prices
        prices = {}
        existing_prices = load_prices()
        
        # Save diagnostic price
        diagnostic_price = data.get("diagnostic_price", "300")
        try:
            prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
        except ValueError:
            prices[f"diagnostic_{service_id}"] = diagnostic_price
        
        # Save case prices
        for key, value in data.items():
            if key.startswith(f"case_{service_id}_"):
                try:
                    float(value)
                    prices[key] = value
                except ValueError:
                    prices[key] = value
        
        # Merge and save prices
        existing_prices.update(prices)
        save_prices(existing_prices)
        
        return jsonify({"success": True, "message": "Послугу та ціни успішно збережено!"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/services/delete/<service_id>", methods=["POST"])
@requires_auth
def admin_services_delete(service_id):
    """Delete service"""
    try:
        services = load_services()
        
        # Remove service
        services = [s for s in services if s.get("id") != service_id]
        
        # Save to file
        ensure_data_dir()
        services_path = DATA_DIR / "services.json"
        services_path.write_text(json.dumps(services, ensure_ascii=False, indent=2), encoding="utf-8")
        
        return jsonify({"success": True, "message": "Послугу видалено!"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/admin/test-email", methods=["POST"])
@requires_auth
def test_email():
    """Test email settings"""
    try:
        # Load email settings
        ensure_data_dir()
        email_settings_path = DATA_DIR / "email_settings.json"
        if not email_settings_path.exists():
            return jsonify({"success": False, "error": "Email налаштування не знайдено"})
        
        settings = json.loads(email_settings_path.read_text(encoding="utf-8"))
        
        # Send test email
        msg = MIMEMultipart()
        msg['From'] = settings['email_username']
        msg['To'] = settings['admin_email']
        msg['Subject'] = "Тестове повідомлення з Atlant Service"
        
        body = "Це тестове повідомлення для перевірки налаштувань Email."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(settings['email_server'], settings['email_port'])
        if settings.get('email_use_tls', True):
            server.starttls()
        server.login(settings['email_username'], settings['email_password'])
        server.send_message(msg)
        server.quit()
        
        return jsonify({"success": True, "message": "Тестовий лист успішно відправлено!"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
