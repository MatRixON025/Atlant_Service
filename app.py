from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import secrets
import os
from pathlib import Path
import json
from functools import wraps
from dotenv import load_dotenv

load_dotenv()  # load .env if present

app = Flask(__name__)
# Security settings
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Admin credentials (consider using environment variables in production)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
ADMIN_PASS_HASH = generate_password_hash(ADMIN_PASS)

# Data paths
DATA_DIR = Path(__file__).resolve().parent / "data"
MESSAGES_PATH = DATA_DIR / "messages.json"
PRICES_PATH = DATA_DIR / "prices.json"

# Service center info (you can update these in templates or here)
SERVICES = [
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
        "desc": "Ремонт LCD, LED, PLASMA, CRT телевізорів.",
        "details": "Швидко усуваємо будь-які несправності: від блоків живлення до матриць.",
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
            "Поломки через перегрів або неправильну експлуатацію",
            "Відсутність чека або гарантійного талона",
            "Пошкодження через неправильну експлуатацію"
        ],
        "non_warranty_cases": [
            {"id": "crt_repair_14_17", "name": "Ремонт CRT-телевізора 14\"-17\"", "price": "від 450"},
            {"id": "crt_repair_20_21", "name": "Ремонт CRT-телевізора 20\"-21\"", "price": "від 700"},
            {"id": "crt_repair_25_32", "name": "Ремонт CRT-телевізора 25\"-32\"", "price": "від 1000"},
            {"id": "lcd_led_repair_14", "name": "Ремонт LCD/LED-TV, PLASMA-TV від 14\"", "price": "від 1000"},
            {"id": "lcd_led_repair_21", "name": "Ремонт LCD/LED-TV, PLASMA-TV від 21\"", "price": "від 1500"}
        ]
    },
    {
        "id": "stove",
        "title": "Ремонт плит і духовок",
        "desc": "Плити, духові шафи, варильні панелі.",
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

CONTACT = {
    "phones": ["+38 (067) 639-63-03", "+38 (097) 251-24-44"],
    "email": "service@atlant-kr.dp.ua",
    "address": "м. Кривий Ріг, вул. Січеславська, 3/47",
}

BRANDS = {
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
        "service_info": "Телефон гарячої лінії Samsung: 0-800-303-707"
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


def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
    if not MESSAGES_PATH.exists():
        MESSAGES_PATH.write_text("[]", encoding="utf-8")


def load_messages():
    ensure_data_dir()
    try:
        return json.loads(MESSAGES_PATH.read_text(encoding="utf-8"))
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
        # Повертаємо ціни за замовчуванням для всіх послуг та їх видів робіт
        prices = {}
        for service in SERVICES:
            service_id = service["id"]
            # Діагностика для всіх послуг
            prices[f"diagnostic_{service_id}"] = 300
            # Ціни для non_warranty_cases
            if "non_warranty_cases" in service:
                for case in service["non_warranty_cases"]:
                    if "price" in case:
                        prices[f"case_{service_id}_{case['id']}"] = case["price"]
                    else:
                        # Якщо ціни немає, ставимо 0
                        prices[f"case_{service_id}_{case['id']}"] = 0
        return prices


def save_prices(prices):
    """Save prices to JSON file with error handling"""
    try:
        ensure_data_dir()
        PRICES_PATH.write_text(json.dumps(prices, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error saving prices: {e}")
        return False


def check_auth(username, password):
    """Check if username and password are valid"""
    return username == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, password)


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
    }


@app.route("/")
def index():
    response = app.make_response(render_template("index.html", brands=BRANDS, contact=CONTACT))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/warranty")
def warranty():
    return render_template("warranty.html", brands=BRANDS, contact=CONTACT)


@app.route("/services")
def services():
    prices = load_prices()
    return render_template("services.html", services=SERVICES, prices=prices, contact=CONTACT)


@app.route("/terms")
def terms():
    return render_template("terms.html", brands=BRANDS, contact=CONTACT)


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    phone = request.form.get("phone")
    message = request.form.get("message")

    if not name or not phone or not message:
        flash("Будь ласка, заповніть всі поля форми", "warning")
        return redirect(url_for("index") + "#contact")

    # Зберігаємо повідомлення для перегляду в адмінці
    messages = load_messages()
    messages.append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "name": name.strip(),
            "phone": phone.strip(),
            "message": message.strip(),
        }
    )
    save_messages(messages)

    flash("Дякуємо! Ваше повідомлення надіслано. Ми зв'яжемося з вами найближчим часом.", "success")
    return redirect(url_for("index") + "#contact")


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


@app.route("/admin/prices", methods=["GET", "POST"])
@requires_auth
def admin_prices():
    if request.method == "POST":
        prices = {}
        
        # Отримуємо ID сервісу з форми
        service_id = request.form.get("service_id")
        
        if service_id:
            # Оновлюємо ціни тільки для цього сервісу
            # Ціна діагностики
            diagnostic_price = request.form.get(f"diagnostic_{service_id}", "300")
            try:
                prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
            except ValueError:
                prices[f"diagnostic_{service_id}"] = 300
            
            # Завантажуємо існуючі ціни
            existing_prices = load_prices()
            
            # Оновлюємо ціни для негарантійних робіт цього сервісу
            service = next((s for s in SERVICES if s["id"] == service_id), None)
            if service and "non_warranty_cases" in service:
                for case in service["non_warranty_cases"]:
                    case_price = request.form.get(f"case_{service_id}_{case['id']}", "0")
                    if case_price and case_price.strip():
                        try:
                            float(case_price)
                            prices[f"case_{service_id}_{case['id']}"] = case_price
                        except ValueError:
                            # Якщо не число, зберігаємо як є (наприклад "від 1000")
                            prices[f"case_{service_id}_{case['id']}"] = case_price
                    else:
                        # Порожне значення - зберігаємо 0
                        prices[f"case_{service_id}_{case['id']}"] = "0"
            
            # Об'єднуємо з існуючими цінами
            existing_prices.update(prices)
            save_prices(existing_prices)
        else:
            # Якщо service_id не надано, обробляємо всі сервіси (стара логіка)
            for service in SERVICES:
                service_id = service["id"]
                
                # Ціна діагностики
                diagnostic_price = request.form.get(f"diagnostic_{service_id}", "0")
                try:
                    prices[f"diagnostic_{service_id}"] = float(diagnostic_price)
                except ValueError:
                    prices[f"diagnostic_{service_id}"] = 0
                
                # Ціни для кожного типу негарантійної роботи
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
        return redirect(url_for("admin_prices"))
    
    prices = load_prices()
    return render_template("admin_prices.html", services=SERVICES, prices=prices, active_tab="prices")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
