"""
Módulo mejorado para manejo de recordatorios, detección de intención y procesamiento de peticiones.
"""
import re
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# ==================== RECORDATORIO EMOJIS Y NOMBRES ====================
# Mapeo de tipos de recordatorio a emojis para mejor representación visual
REMINDER_EMOJIS = {
    "water": "💧",
    "supplement": "💊",
    "sleep": "😴",
    "meditation": "🧘",
    "exercise": "🏃",
    "appointment": "📅",
    "medicine": "🩺",
    "meal": "🍽️",
    "custom": "🔔"
}

# Lista de adjetivos y sustantivos para crear nombres de recordatorio amigables
REMINDER_ADJECTIVES = [
    "Diario", "Saludable", "Vital", "Esencial", "Importante", 
    "Regular", "Renovador", "Personal", "Favorito", "Óptimo"
]

REMINDER_NOUNS = {
    "water": ["Agua", "Hidratación", "Líquido"],
    "supplement": ["Vitamina", "Suplemento", "Nutriente"],
    "sleep": ["Descanso", "Sueño", "Reposo"],
    "meditation": ["Meditación", "Calma", "Relajación"],
    "exercise": ["Ejercicio", "Movimiento", "Actividad"],
    "appointment": ["Cita", "Compromiso", "Evento"],
    "medicine": ["Medicina", "Tratamiento", "Remedio"],
    "meal": ["Comida", "Alimentación", "Nutrición"],
    "custom": ["Recordatorio", "Aviso", "Notificación"]
}

def generate_reminder_name(reminder_type: str, supplement_name: str = None) -> str:
    """Genera un nombre amigable para un recordatorio basado en su tipo"""
    adjective = random.choice(REMINDER_ADJECTIVES)
    
    if reminder_type in REMINDER_NOUNS:
        noun = random.choice(REMINDER_NOUNS[reminder_type])
    else:
        noun = random.choice(REMINDER_NOUNS["custom"])
    
    if reminder_type == "supplement" and supplement_name:
        return f"{adjective} {supplement_name}"
    else:
        return f"{adjective} {noun}"


#def is_reminder_response_context(text: str, chat_history: List[Dict[str, str]] = None) -> bool:
#    """Detectar si el usuario está respondiendo preguntas sobre recordatorios"""
#    if not chat_history:
#        return False
#    
#    # Verificar los últimos 2 mensajes del asistente
#    recent_assistant_messages = []
#    for msg in reversed(chat_history[-4:]):  # Últimos 4 mensajes
#        if msg["role"] == "assistant":
#            recent_assistant_messages.append(msg["content"].lower())
#            if len(recent_assistant_messages) >= 2:
#                break
#    
#    # Buscar patrones que indiquen que el bot pidió información de recordatorio
#    context_indicators = [
#        "qué suplemento quieres que te recuerde",
#        "a qué hora te gustaría el recordatorio",
#        "con qué frecuencia",
#        "para configurar tu recordatorio",
#        "dime qué quieres recordar",
#        "cuándo quieres que te recuerde",
#        "qué quieres que te recuerde",
#        "necesito saber qué quieres que te recuerde"
#    ]
#    
#    for assistant_msg in recent_assistant_messages:
#        if any(indicator in assistant_msg for indicator in context_indicators):
#            logger.info(f"Detected reminder response context from recent assistant message")
#            return True
#    
#    return False
#
#def parse_reminder_response_context(text: str) -> dict:
#    """Parsear respuesta del usuario cuando está en contexto de recordatorio"""
#    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
#    
#    result = {
#        "detected": True,
#        "type": "supplement",  # Por defecto
#        "supplement_name": "",
#        "times": [],
#        "interval_minutes": None,
#        "message": "",
#        "display_name": ""
#    }
#    
#    # Analizar cada línea
#    supplement_found = False
#    time_found = False
#    
#    for line in lines:
#        line_lower = line.lower()
#        
#        # Detectar suplemento (primera línea o línea que parece nombre)
#        if not supplement_found and len(line.split()) <= 3:  # Máximo 3 palabras
#            # Verificar si parece nombre de suplemento
#            supplement_keywords = ["vitamina", "magnesio", "zinc", "omega", "hierro", "calcio", "d3", "b12", "c"]
#            if (any(keyword in line_lower for keyword in supplement_keywords) or 
#                len(line) >= 3):  # Cualquier palabra de 3+ caracteres
#                result["supplement_name"] = line.title()
#                supplement_found = True
#                continue
#        
#        # Detectar horario
#        if not time_found:
#            # Buscar patrones de tiempo
#            if (re.search(r'\d+\s*(am|pm)', line_lower) or 
#                re.search(r'\d+:\d+', line_lower) or
#                any(word in line_lower for word in ["mañana", "tarde", "noche", "am", "pm"])):
#                
#                parsed_times = parse_flexible_times(line)
#                if parsed_times:
#                    result["times"] = parsed_times
#                    result["interval_minutes"] = None
#                    time_found = True
#                    continue
#        
#        # Detectar frecuencia
#        if ("cada" in line_lower or "todos los dias" in line_lower or 
#            "diario" in line_lower or "frecuencia" in line_lower):
#            if "todos los dias" in line_lower or "diario" in line_lower:
#                # "Todos los días" = cada 24 horas pero a una hora específica
#                if not result["times"]:  # Si no hay hora específica, usar 8 AM por defecto
#                    result["times"] = ["08:00"]
#                    result["interval_minutes"] = None
#            else:
#                frequency = parse_flexible_frequency(line)
#                if frequency:
#                    result["interval_minutes"] = frequency
#                    result["times"] = []
#    
#    # Valores por defecto si no se encontró algo
#    if not result["supplement_name"]:
#        result["supplement_name"] = "Suplemento"
#    
#    if not result["times"] and result["interval_minutes"] is None:
#        result["times"] = ["08:00"]  # Por defecto a las 8 AM
#        result["interval_minutes"] = None
#    
#    # Configurar mensaje y display_name
#    result["message"] = f"💊 Es hora de tomar tu {result['supplement_name']}"
#    result["display_name"] = f"Recordatorio de {result['supplement_name']}"
#    
#    logger.info(f"Parsed reminder response context: {result}")
#    return result


# ==================== FUNCIONES MEJORADAS ====================

def convert_12h_to_24h(hour: int, minute: int, period: str) -> str:
    """Convertir formato 12h a 24h"""
    if period.lower() == "pm" and hour != 12:
        hour += 12
    elif period.lower() == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"

#def parse_flexible_times(text: str):
#    """Detectar horarios de forma ultra-flexible - VERSIÓN MEJORADA"""
#    import re
#    
#    times_found = []
#    text_lower = text.lower()
#    
#    # Patrones de horarios específicos MEJORADOS
#    time_patterns = [
#        # Horarios exactos con AM/PM
#        (r"(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)", lambda m: convert_12h_to_24h(int(m.group(1)), int(m.group(2)), m.group(3))),
#        (r"(\d{1,2})\s*(am|pm)", lambda m: convert_12h_to_24h(int(m.group(1)), 0, m.group(2))),
#        
#        # Horarios en formato 24h
#        (r"(\d{1,2}):(\d{2})", lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"),
#        (r"a\s*las\s*(\d{1,2}):?(\d{2})?", lambda m: f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"),
#        
#        # Expresiones de tiempo MEJORADAS
#        (r"mañana|desayun|por\s*la\s*mañana|en\s*la\s*mañana", lambda m: "08:00"),
#        (r"mediodía|medio\s*día|almuerz|comer|comida", lambda m: "12:00"),
#        (r"tarde|por\s*la\s*tarde|en\s*la\s*tarde", lambda m: "15:00"),
#        
#        # MEJORADO: Detección específica de "noche"
#        (r"(?:cada\s+)?noche|por\s*la\s*noche|en\s*la\s*noche|antes\s*de\s*dormir|antes\s*de\s*acostar", lambda m: "22:00"),
#        (r"cenar|cena", lambda m: "20:00"),
#        
#        # Horarios específicos en texto
#        (r"(?:a\s*las\s*)?(\d{1,2})\s*de\s*la\s*noche", lambda m: f"{int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1))}:00"),
#        (r"(?:a\s*las\s*)?(\d{1,2})\s*de\s*la\s*mañana", lambda m: f"{int(m.group(1)):02d}:00"),
#    ]
#    
#    for pattern, extractor in time_patterns:
#        if isinstance(pattern, str):
#            if re.search(pattern, text_lower):
#                time_result = extractor(None)
#                if time_result not in times_found:
#                    times_found.append(time_result)
#        else:
#            matches = re.finditer(pattern, text_lower)
#            for match in matches:
#                time_result = extractor(match)
#                if time_result and time_result not in times_found:
#                    times_found.append(time_result)
#    
#    # Si no se encontraron horarios específicos, usar defaults según contexto
#    if not times_found:
#        if any(word in text_lower for word in ["noche", "dormir", "acostar"]):
#            times_found = ["22:00"]
#        elif any(word in text_lower for word in ["mañana", "desayun"]):
#            times_found = ["08:00"]
#        else:
#            times_found = ["08:00", "20:00"]
#    
#    logger.info(f"Times detected: {times_found} from text: '{text}'")
#    return times_found

def parse_flexible_frequency(text: str):
    """Detectar frecuencia mejorada con mejor manejo de expresiones temporales"""
    import re
    
    text_lower = text.lower()
    
    # NUEVO: Detectar expresiones que NO son frecuencias sino horarios
    time_expressions = [
        r"cada\s+(noche|mañana|tarde)",
        r"por\s+la\s+(noche|mañana|tarde)", 
        r"en\s+la\s+(noche|mañana|tarde)",
        r"a\s+las\s+\d+",
        r"\d+\s*(am|pm)",
        r"antes\s+de\s+dormir",
        r"después\s+de\s+comer"
    ]
    
    # Si es una expresión de tiempo específico, no es frecuencia
    for pattern in time_expressions:
        if re.search(pattern, text_lower):
            logger.info(f"Detected time expression, not frequency: '{text}'")
            return None  # Indicar que debe usar horarios específicos
    
    # Patrones de tiempo con soporte decimal
    time_patterns = [
        # Detección de "min" o "minuto" sin número (implica 1 minuto)
        (r"cada\s*min(?:uto)?s?\b", lambda m: 1),
        (r"por\s*min(?:uto)?s?\b", lambda m: 1),
        (r"un\s*min(?:uto)?s?\b", lambda m: 1),
        (r"1\s*min(?:uto)?s?\b", lambda m: 1),

        # Segundos
        (r"(\d+(?:\.\d+)?)\s*seg(?:undo)?s?", lambda m: float(m.group(1)) / 60),
        (r"cada\s*(\d+(?:\.\d+)?)\s*seg(?:undo)?s?", lambda m: float(m.group(1)) / 60),
        (r"(\d+(?:\.\d+)?)\s*s\b", lambda m: float(m.group(1)) / 60),  # "30s", "15.5s"
        
        # Minutos - muchas variaciones con decimales
        (r"(\d+(?:\.\d+)?)\s*min(?:uto)?s?", lambda m: float(m.group(1))),
        (r"cada\s*(\d+(?:\.\d+)?)\s*min(?:uto)?s?", lambda m: float(m.group(1))),
        (r"(\d+(?:\.\d+)?)\s*m\b", lambda m: float(m.group(1))),  # "5m", "2.5m"
        (r"cada\s*minuto", lambda m: 1),
        (r"por\s*minuto", lambda m: 1),
        (r"un\s*minuto", lambda m: 1),
        (r"1\s*minuto", lambda m: 1),
        
        # Fracciones de minuto
        (r"medio\s*minuto", lambda m: 0.5),
        (r"30\s*segundos", lambda m: 0.5),
        (r"15\s*segundos", lambda m: 0.25),
        (r"45\s*segundos", lambda m: 0.75),
        
        # Horas - muchas variaciones con decimales
        (r"(\d+(?:\.\d+)?)\s*h(?:ora)?s?", lambda m: float(m.group(1)) * 60),
        (r"cada\s*(\d+(?:\.\d+)?)\s*h(?:ora)?s?", lambda m: float(m.group(1)) * 60),
        (r"(\d+(?:\.\d+)?)\s*hr?s?", lambda m: float(m.group(1)) * 60),
        (r"cada\s*hora", lambda m: 60),
        (r"por\s*hora", lambda m: 60),
        (r"una\s*hora", lambda m: 60),
        (r"1\s*hora", lambda m: 60),
        (r"cada\s*h", lambda m: 60),
        
        # Fracciones de hora
        (r"media\s*hora", lambda m: 30),
        (r"30\s*min(?:uto)?s?", lambda m: 30),
        (r"cuarto\s*de\s*hora", lambda m: 15),
        (r"15\s*min(?:uto)?s?", lambda m: 15),
        (r"tres\s*cuartos\s*de\s*hora", lambda m: 45),
        (r"45\s*min(?:uto)?s?", lambda m: 45),
        
        # Expresiones más naturales
        (r"muy\s*seguido", lambda m: 15),  # cada 15 minutos
        (r"seguido", lambda m: 30),       # cada 30 minutos
        (r"frecuente", lambda m: 30),
        (r"constantemente", lambda m: 15),
        (r"todo\s*el\s*tiempo", lambda m: 10),
        (r"siempre", lambda m: 30),
        
        # Veces por período con decimales
        (r"dos\s*veces\s*(?:por\s*)?(?:al\s*)?día", lambda m: 12 * 60),    # cada 12 horas
        (r"tres\s*veces\s*(?:por\s*)?(?:al\s*)?día", lambda m: 8 * 60),     # cada 8 horas
        (r"cuatro\s*veces\s*(?:por\s*)?(?:al\s*)?día", lambda m: 6 * 60),   # cada 6 horas
        (r"seis\s*veces\s*(?:por\s*)?(?:al\s*)?día", lambda m: 4 * 60),     # cada 4 horas
        (r"una\s*vez\s*(?:por\s*)?(?:al\s*)?día", lambda m: 24 * 60),       # cada 24 horas
        
        # Números escritos con decimales
        (r"cada\s*dos\s*h(?:ora)?s?", lambda m: 2 * 60),
        (r"cada\s*tres\s*h(?:ora)?s?", lambda m: 3 * 60),
        (r"cada\s*cuatro\s*h(?:ora)?s?", lambda m: 4 * 60),
        (r"cada\s*cinco\s*h(?:ora)?s?", lambda m: 5 * 60),
        (r"cada\s*seis\s*h(?:ora)?s?", lambda m: 6 * 60),
        
        # Casos especiales comunes
        (r"a\s*cada\s*rato", lambda m: 30),
        (r"de\s*vez\s*en\s*cuando", lambda m: 2 * 60),  # cada 2 horas
        (r"regularmente", lambda m: 60),
        (r"periódicamente", lambda m: 60),
    ]
    
    # Buscar patrones de frecuencia
    for pattern, extractor in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            result = extractor(match)
            logger.info(f"Frequency pattern matched: '{pattern}' -> {result} minutes")
            return result
    
    # Default: cada hora
    logger.info("No specific frequency found, defaulting to 60 minutes")
    return 60

def detect_reminder_type(text: str):
    """Detectar el tipo de recordatorio de forma mejorada"""
    text_lower = text.lower().strip()
    
    # Patrones para cada tipo de recordatorio
    reminder_types = {
        "water": [
            "agua", "h2o", "hidrat", "beber", "bebe", "tomar agua", "toma agua",
            "líquido", "liquido", "fluido", "sed", "hidratar", "hidratarme"
        ],
        "sleep": [
            "dormir", "sueño", "descansar", "descanso", "cama", "acostar", "acuest",
            "soñar", "hora de dormir", "ir a dormir", "ir a la cama", "hora de descansar"
        ],
        "meditation": [
            "meditar", "meditación", "meditacion", "mindfulness", "respirar", "respira",
            "relajar", "relaja", "calmar", "calma", "paz", "tranquil", "atencion plena"
        ],
        "exercise": [
            "ejercicio", "entrenar", "entreno", "entrenamient", "gimnasio", "gym", 
            "correr", "trotar", "caminar", "estirar", "estiramiento", "yoga", "pilates"
        ],
        "meal": [
            "comer", "comida", "almorzar", "almuerzo", "cenar", "cena", "desayunar", 
            "desayuno", "merienda", "refrigerio", "snack", "alimento"
        ],
        "appointment": [
            "cita", "reunión", "reunion", "consulta", "visita", "médico", "medico", 
            "doctor", "dentista", "terapia", "fisio", "trabajo", "evento"
        ]
    }
    
    # Comprobar coincidencias con cada tipo
    for reminder_type, keywords in reminder_types.items():
        if any(keyword in text_lower for keyword in keywords):
            logger.info(f"Detected reminder type: {reminder_type}")
            return reminder_type
    
    # Comprobar si es un medicamento o suplemento
    supplement_keywords = [
        "pastilla", "capsula", "tableta", "suplemento", "vitamina", "medicamento", 
        "píldora", "medicina", "dosis", "tratamiento", "medicación", "medicacion",
        "cápsula", "remedio", "jarabe", "gotas", "inyección", "inyeccion"
    ]
    
    if any(keyword in text_lower for keyword in supplement_keywords):
        logger.info(f"Detected reminder type: supplement")
        return "supplement"
    
    # Default a supplement si se menciona un nombre de suplemento específico
    supplement_names = [
        "magnesio", "zinc", "selenio", "vitamina", "omega", "hierro", "calcio",
        "ashwagandha", "probiótico", "melatonina", "b12", "d3", "c", "biotina"
    ]
    
    if any(name in text_lower for name in supplement_names):
        logger.info(f"Detected supplement name in: {text}")
        return "supplement"
    
    # Si no hay coincidencias claras pero parece un recordatorio, usar tipo personalizado
    logger.info(f"No specific reminder type detected, using custom type")
    return "custom"

# REEMPLAZAR ESTAS DOS FUNCIONES EN reminder_utils.py

def parse_flexible_times(text: str):
    """Detectar horarios de forma ultra-flexible - VERSIÓN CORREGIDA"""
    import re
    
    times_found = []
    text_lower = text.lower()
    
    # Patrones de horarios específicos CORREGIDOS
    time_patterns = [
        # Horarios exactos con AM/PM - CORREGIDOS para manejar None
        (r"(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)", "ampm_with_minutes"),
        (r"(\d{1,2})\s*(am|pm)", "ampm_only"),
        
        # Horarios en formato 24h
        (r"(\d{1,2}):(\d{2})", "24h_format"),
        (r"a\s*las\s*(\d{1,2}):?(\d{2})?", "a_las_format"),
        
        # Expresiones de tiempo MEJORADAS - usando strings simples
        (r"mañana|desayun|por\s*la\s*mañana|en\s*la\s*mañana", "morning"),
        (r"mediodía|medio\s*día|almuerz|comer|comida", "noon"),
        (r"tarde|por\s*la\s*tarde|en\s*la\s*tarde", "afternoon"),
        
        # MEJORADO: Detección específica de "noche"
        (r"(?:cada\s+)?noche|por\s*la\s*noche|en\s*la\s*noche|antes\s*de\s*dormir|antes\s*de\s*acostar", "night"),
        (r"cenar|cena", "dinner"),
        
        # Horarios específicos en texto
        (r"(?:a\s*las\s*)?(\d{1,2})\s*de\s*la\s*noche", "night_hour"),
        (r"(?:a\s*las\s*)?(\d{1,2})\s*de\s*la\s*mañana", "morning_hour"),
    ]
    
    for pattern, action_type in time_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            time_result = None
            
            if action_type == "ampm_with_minutes":
                time_result = convert_12h_to_24h(int(match.group(1)), int(match.group(2)), match.group(3))
            elif action_type == "ampm_only":
                time_result = convert_12h_to_24h(int(match.group(1)), 0, match.group(2))
            elif action_type == "24h_format":
                time_result = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
            elif action_type == "a_las_format":
                time_result = f"{int(match.group(1)):02d}:{int(match.group(2) or 0):02d}"
            elif action_type == "morning":
                time_result = "08:00"
            elif action_type == "noon":
                time_result = "12:00"
            elif action_type == "afternoon":
                time_result = "15:00"
            elif action_type == "night":
                time_result = "22:00"
            elif action_type == "dinner":
                time_result = "20:00"
            elif action_type == "night_hour":
                hour = int(match.group(1))
                time_result = f"{hour + 12 if hour < 12 else hour:02d}:00"
            elif action_type == "morning_hour":
                time_result = f"{int(match.group(1)):02d}:00"
            
            if time_result and time_result not in times_found:
                times_found.append(time_result)
    
    # Si no se encontraron horarios específicos, usar defaults según contexto
    if not times_found:
        if any(word in text_lower for word in ["noche", "dormir", "acostar"]):
            times_found = ["22:00"]
        elif any(word in text_lower for word in ["mañana", "desayun"]):
            times_found = ["08:00"]
        else:
            times_found = ["08:00", "20:00"]
    
    logger.info(f"Times detected: {times_found} from text: '{text}'")
    return times_found

def parse_flexible_supplement_improved(text: str):
    """Parser mejorado para suplementos con mejor detección - VERSIÓN CORREGIDA"""
    import re
    
    result = {
        "found": False,
        "name": "",
    }
    
    # Patrones mejorados y MÁS ESPECÍFICOS para extraer nombres de suplementos
    supplement_patterns = [
        # Patrón principal: "mi [nombre]" - el más común
        r"mi\s+([a-záéíóúüñ]{3,}(?:\s+[a-záéíóúüñ]{3,})?)",
        
        # Patrón: "tomar [nombre]" pero evitando palabras comunes
        r"tomar\s+(?:el\s+|la\s+|mi\s+)?([a-záéíóúüñ]{4,}(?:\s+[a-záéíóúüñ]{4,})?)",
        
        # Patrón: "suplemento/vitamina de [nombre]"
        r"(?:suplemento|vitamina|pastilla)\s+(?:de\s+)?([a-záéíóúüñ]{4,}(?:\s+[a-záéíóúüñ]{4,})?)",
        
        # Patrón: "[nombre] suplemento/vitamina"
        r"([a-záéíóúüñ]{4,}(?:\s+[a-záéíóúüñ]{4,})?)\s+(?:suplemento|vitamina|pastilla)",
    ]
    
    # Lista expandida de suplementos comunes - MEJORADA
    valid_supplements = [
        "magnesio", "glicinato", "vitamina", "omega", "calcio", "hierro", "zinc", "selenio",
        "b12", "d3", "c", "biotina", "colageno", "colágeno", "probiotico", "probiótico",
        "melatonina", "ashwagandha", "curcuma", "cúrcuma", "jengibre", "ajo", "proteina",
        "proteína", "creatina", "bcaa", "glutamina", "vitaminac", "vitamind", "vitaminab",
        "multivitaminico", "multivitamínico", "complejo"
    ]
    
    # Lista de palabras a EXCLUIR específicamente - AMPLIADA
    exclude_words = [
        "agua", "que", "me", "de", "el", "la", "mi", "mis", "un", "una",
        "recordar", "tomar", "beber", "hora", "horas", "minuto", "minutos",
        "dia", "día", "noche", "mañana", "tarde", "vez", "veces", "tiempo",
        "cuando", "donde", "como", "cómo", "para", "por", "con", "sin", "cada",
        "las", "los", "suplemento", "pastilla", "medicina", "medicamento",
        "a", "y", "o", "pero", "si", "no", "del", "al"
    ]
    
    for pattern in supplement_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            potential_name = match.group(1).lower().strip()
            
            # Validaciones MÁS ESTRICTAS
            if (len(potential_name) >= 3 and 
                potential_name not in exclude_words and
                potential_name.replace(" ", "").isalpha()):
                
                # Verificar si es un suplemento conocido O si tiene al menos 4 caracteres
                name_clean = potential_name.replace(" ", "").lower()
                is_valid = (
                    any(sup in name_clean for sup in valid_supplements) or
                    (len(potential_name) >= 4 and not any(exc == potential_name for exc in exclude_words))
                )
                
                if is_valid:
                    result["found"] = True
                    result["name"] = potential_name.title()
                    logger.info(f"Supplement detected: {result['name']}")
                    return result  # IMPORTANTE: salir inmediatamente al encontrar el primero válido
    
    # Si no se encontró nada específico, usar "mi suplemento" como genérico
    if "mi suplemento" in text.lower():
        result["found"] = True
        result["name"] = "Suplemento"
        logger.info(f"Generic supplement detected: {result['name']}")
    
    return result

#def parse_flexible_supplement_improved(text: str):
#    """Parser mejorado para suplementos con mejor detección"""
#    import re
#    
#    result = {
#        "found": False,
#        "name": "",
#    }
#    
#    # Patrones mejorados para extraer nombres de suplementos
#    supplement_patterns = [
#        # Patrones directos mejorados
#        r"(?:tomar|tome|beber|consume|consumir)\s+(?:el\s+|la\s+|mi\s+|mis\s+)?([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)?)",
#        r"(?:recordar|recuerda|recuérdame)\s+(?:que\s+)?(?:tome|tomar)\s+(?:el\s+|la\s+|mi\s+|mis\s+)?([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)?)",
#        r"(?:suplemento|vitamina|pastilla)\s+(?:de\s+)?([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)?)",
#        r"([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)?)\s+(?:suplemento|vitamina|pastilla)",
#        r"mi\s+([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+)?)",
#    ]
#    
#    # Lista expandida de suplementos comunes
#    valid_supplements = [
#        "magnesio", "glicinato", "vitamina", "omega", "calcio", "hierro", "zinc", "selenio",
#        "b12", "d3", "c", "biotina", "colageno", "colágeno", "probiotico", "probiótico",
#        "melatonina", "ashwagandha", "curcuma", "cúrcuma", "jengibre", "ajo", "proteina",
#        "proteína", "creatina", "bcaa", "glutamina", "vitaminac", "vitamind", "vitaminab"
#    ]
#    
#    for pattern in supplement_patterns:
#        matches = re.finditer(pattern, text, re.IGNORECASE)
#        for match in matches:
#            potential_name = match.group(1).lower().strip()
#            
#            # Filtrar palabras excluidas
#            exclude_words = [
#                "agua", "que", "me", "de", "el", "la", "mi", "mis", "un", "una",
#                "recordar", "tomar", "beber", "hora", "horas", "minuto", "minutos",
#                "dia", "día", "noche", "mañana", "tarde", "vez", "veces", "tiempo",
#                "cuando", "donde", "como", "cómo", "para", "por", "con", "sin", "cada"
#            ]
#            
#            if (len(potential_name) >= 2 and 
#                potential_name not in exclude_words and
#                potential_name.replace(" ", "").isalpha()):
#                
#                # Validar si es un suplemento conocido
#                name_clean = potential_name.replace(" ", "").lower()
#                is_valid = (
#                    any(sup in name_clean for sup in valid_supplements) or
#                    len(potential_name) >= 4  # Nombres largos probablemente son válidos
#                )
#                
#                if is_valid:
#                    result["found"] = True
#                    result["name"] = potential_name.title()
#                    logger.info(f"Supplement detected: {result['name']}")
#                    break
#    
#    return result

def is_information_request(text: str) -> bool:
    """Detectar si es una pregunta de información en lugar de un recordatorio"""
    text_lower = text.lower().strip()
    
    # Palabras específicas de suplementos que indican solicitud de información
    supplement_info_keywords = [
        "recomienda", "información", "información sobre", "beneficios", 
        "efectos", "sirve", "funciona", "mejor", "bueno para", 
        "ayuda con", "es bueno", "puedo tomar", "debo tomar",
        "que suplemento", "que me recomiendas", "que tomar para"
    ]
    
    # Verificar primero si hay palabras clave específicas de información sobre suplementos
    if any(keyword in text_lower for keyword in supplement_info_keywords):
        return True
    
    # Patrones de preguntas informativas
    info_patterns = [
        # Preguntas directas sobre suplementos, salud, etc.
        r"que (?:puedo )?(?:debo )?tomar para",
        r"que (?:me )?recomiendas",
        r"recomiendame",
        r"(?:que|cuales) (?:son|hay|existen) (?:los|las)? (?:mejores|buenos)",
        r"(?:que|cual) es (?:bueno|mejor|recomendable)",
        r"(?:donde|como) (?:puedo|debo|tengo que)",
        r"beneficios de",
        r"ventajas de",
        r"efectos de",
        r"(?:opciones|alternativas) de",
        
        # Preguntas específicas de salud
        r"(?:que|como) (?:puedo|debo) (?:hacer|tomar) para",
        r"(?:que|como) (?:me )?ayuda con",
        r"(?:que|cual) es (?:bueno|mejor|recomendable) para",
        r"que puedo tomar\??$",  # Exactamente "que puedo tomar" con o sin signo
        r"para que sirve",
        r"como funciona",
        r"efectos secundarios",
        
        # Preguntas sobre productos Epigen
        r"test (?:de|para)",
        r"prueba (?:de|para)",
        r"(?:que|cuales) (?:son|hay|existen) (?:los|las)? (?:test|pruebas)",
        r"(?:cuanto|precio|costo) (?:cuesta|vale|es)",
        r"donde (?:compro|consigo|adquiero)",
        
        # Consultas de información genéricas
        r"me\s*siento",
        r"tengo\s*(?:problemas|dificultades|síntomas)",
        r"suplementos?\s*(?:para|de)\s*",
        r"que\s*suplemento",
        r"suplementos?$",  # Solo la palabra "suplemento" o "suplementos"
        
        # Categorías generales
        r"^(?:que|quien|cuando|donde|como|por que|porque|cual|cuales|cuanto|cuanta)",
        r"me puedes (?:explicar|decir|contar|informar)",
        r"informacion (?:sobre|acerca|de)",
        r"datos (?:sobre|acerca|de)",
    ]
    
    # Si coincide con algún patrón de pregunta informativa
    for pattern in info_patterns:
        if re.search(pattern, text_lower):
            logger.info(f"Detected information request: '{text}'")
            return True
    
    return False

def is_specific_product_request(text: str) -> bool:
    """Detectar si es una consulta sobre un producto o suplemento específico"""
    text_lower = text.lower().strip()
    
    # Lista de suplementos y productos comunes
    supplement_keywords = [
        "magnesio", "glicinato", "zinc", "vitamina", "omega", "d3", "c", "b12",
        "ashwagandha", "probiotico", "probiótico", "melatonina", "hierro", "calcio",
        "selenio", "valeriana", "complejo b", "curcuma", "cúrcuma", "proteína", "proteina",
        "colágeno", "colageno", "biotina", "creatina", "bcaa", "glutamina", "antioxidante"
    ]
    
    # Lista de productos Epigen
    epigen_products = [
        "test", "prueba", "análisis", "analisis", "epigenético", "epigenetico",
        "diabetes", "intestino", "inflamación", "inflamacion", "peso", "corazón", "corazon"
    ]
    
    # Patrones para detectar consultas de productos
    product_patterns = [
        r"(?:donde|como) (?:compro|consigo|adquiero)",
        r"(?:me )?recomiendas",
        r"(?:que|cual) es (?:mejor|bueno|recomendable)",
        r"(?:opciones|alternativas) de",
        r"donde (?:hay|venden|consigo)",
        r"(?:puedo|debo) tomar",
        r"(?:para que|que) (?:sirve|es bueno)",
        r"beneficios de",
        r"efectos de",
        r"información (?:sobre|de)",
        r"más (?:información|detalles) (?:sobre|de)",
    ]
    
    # Verificar si contiene alguna palabra clave de suplementos o productos
    has_supplement = any(keyword in text_lower for keyword in supplement_keywords)
    has_epigen_product = any(keyword in text_lower for keyword in epigen_products)
    
    # Verificar si coincide con algún patrón de consulta de producto
    has_product_pattern = any(re.search(pattern, text_lower) for pattern in product_patterns)
    
    # Es una consulta de producto si tiene una palabra clave y un patrón de consulta
    if (has_supplement or has_epigen_product) and has_product_pattern:
        logger.info(f"Detected specific product request: '{text}'")
        return True
    
    return False

def parse_reminder_request(text: str, user_phone: str):
    """
    VERSIÓN MEJORADA: Analizar texto del usuario para extraer información de recordatorios.
    Solo considera solicitudes explícitas de recordatorio.
    """
    text_lower = text.lower().strip()
    
    # Primero verificamos si es una pregunta informativa en lugar de un recordatorio
    if is_information_request(text_lower) and not "recuerd" in text_lower:
        logger.info(f"Detected information request rather than reminder: '{text}'")
        return None
    
    # Verificar si es una solicitud EXPLÍCITA de recordatorio
    if not is_explicit_reminder_request(text_lower):
        logger.info(f"Not an explicit reminder request: '{text}'")
        return None
    
    # Limpiar texto de signos de puntuación innecesarios
    import string
    text_clean = text_lower.translate(str.maketrans('', '', '¿¡'))
    
    logger.info(f"Parsing EXPLICIT reminder request for {user_phone}: '{text}'")
    
    # Determinar el tipo de recordatorio
    reminder_type = detect_reminder_type(text_clean)
    
    reminder_info = {
        "type": reminder_type,
        "interval_minutes": 60,  # Default: cada hora
        "times": [],
        "supplement_name": "",
        "message": "",
        "detected": True
    }
    
    # Personalizar mensaje y comportamiento según el tipo
    if reminder_type == "water":
        reminder_info["message"] = f"{REMINDER_EMOJIS['water']} ¡Es hora de tomar agua! Mantente hidratado para tu salud."
        reminder_info["interval_minutes"] = parse_flexible_frequency(text_clean) or 60
        reminder_info["display_name"] = generate_reminder_name("water")
        
    elif reminder_type == "sleep":
        reminder_info["message"] = f"{REMINDER_EMOJIS['sleep']} Es hora de prepararte para dormir. Un buen descanso es clave para tu salud."
        # Los recordatorios de sueño normalmente son a horas específicas
        reminder_info["times"] = parse_flexible_times(text_clean)
        reminder_info["display_name"] = generate_reminder_name("sleep")
        reminder_info["interval_minutes"] = None
        
    elif reminder_type == "meditation":
        reminder_info["message"] = f"{REMINDER_EMOJIS['meditation']} Momento de meditar. Tómate unos minutos para conectar con tu respiración."
        frequency = parse_flexible_frequency(text_clean)
        if frequency is None:
            reminder_info["times"] = parse_flexible_times(text_clean)
            reminder_info["interval_minutes"] = None
        else:
            reminder_info["interval_minutes"] = frequency
        reminder_info["display_name"] = generate_reminder_name("meditation")
        
    elif reminder_type == "exercise":
        reminder_info["message"] = f"{REMINDER_EMOJIS['exercise']} ¡Es hora de moverte! Un poco de ejercicio mejorará tu día."
        frequency = parse_flexible_frequency(text_clean)
        if frequency is None:
            reminder_info["times"] = parse_flexible_times(text_clean)
            reminder_info["interval_minutes"] = None
        else:
            reminder_info["interval_minutes"] = frequency
        reminder_info["display_name"] = generate_reminder_name("exercise")
        
    elif reminder_type == "supplement":
        supplement_info = parse_flexible_supplement_improved(text_clean)
        
        if supplement_info["found"]:
            reminder_info["supplement_name"] = supplement_info["name"]
            reminder_info["message"] = f"{REMINDER_EMOJIS['supplement']} Es hora de tomar tu {supplement_info['name']}"
            reminder_info["display_name"] = f"Recordatorio de {supplement_info['name']}"
            
            # Decidir entre intervalo y horarios específicos
            frequency = parse_flexible_frequency(text_clean)
            if frequency is None:  # Es expresión de tiempo
                reminder_info["times"] = parse_flexible_times(text_clean)
                reminder_info["interval_minutes"] = None
            else:  # Es frecuencia
                reminder_info["interval_minutes"] = frequency
                reminder_info["times"] = []
        else:
            # Si no se puede determinar el suplemento específico
            reminder_info["supplement_name"] = "suplemento"  # Genérico
            reminder_info["message"] = f"{REMINDER_EMOJIS['supplement']} Es hora de tomar tu suplemento"
            reminder_info["display_name"] = "Recordatorio de Suplemento"
            frequency = parse_flexible_frequency(text_clean)
            if frequency is None:
                reminder_info["times"] = parse_flexible_times(text_clean)
                reminder_info["interval_minutes"] = None
            else:
                reminder_info["interval_minutes"] = frequency
                reminder_info["times"] = []
    
    elif reminder_type == "meal":
        reminder_info["message"] = f"{REMINDER_EMOJIS['meal']} ¡Es hora de alimentarte! Recuerda comer de forma balanceada."
        reminder_info["times"] = ["08:00", "13:00", "19:00"]  # Horarios comunes de comida
        reminder_info["display_name"] = generate_reminder_name("meal")
        reminder_info["interval_minutes"] = None
        
    elif reminder_type == "appointment":
        reminder_info["message"] = f"{REMINDER_EMOJIS['appointment']} Recordatorio de tu cita."
        reminder_info["times"] = parse_flexible_times(text_clean)
        reminder_info["display_name"] = generate_reminder_name("appointment")
        reminder_info["interval_minutes"] = None
        
    else:  # custom
        reminder_info["message"] = f"{REMINDER_EMOJIS['custom']} Recordatorio personalizado"
        reminder_info["display_name"] = generate_reminder_name("custom")
        # Intentar detectar si es basado en intervalo o en horarios específicos
        frequency = parse_flexible_frequency(text_clean)
        if frequency is None:
            reminder_info["times"] = parse_flexible_times(text_clean)
            reminder_info["interval_minutes"] = None
        else:
            reminder_info["interval_minutes"] = frequency
            reminder_info["times"] = []
    
    logger.info(f"Parsed EXPLICIT reminder info: {reminder_info}")
    return reminder_info

def parse_reminder_modification(text: str, user_phone: str):
    """NUEVA FUNCIÓN: Detectar modificaciones de recordatorios existentes"""
    text_lower = text.lower().strip()
    
    modification_patterns = [
        # Cambiar frecuencia/horario por nombre
        r"(?:cambia|modifica|actualiza|cambiame|modificame)\s+(?:mi\s+)?recordatorio\s+(?:de\s+)?([a-záéíóúüñ\s]+?)(?:\s+(?:a|cada|por)\s+(.+))?",
        
        # Cambiar por ID
        r"(?:cambia|modifica|actualiza)\s+(?:el\s+)?recordatorio\s+(?:con\s+)?(?:id\s+|#)?(\d+)(?:\s+(?:a|cada|por)\s+(.+))?",
        
        # Cambiar horario específicamente
        r"(?:cambia|modifica)\s+(?:la\s+)?hora\s+(?:del\s+)?recordatorio\s+(?:de\s+)?([a-záéíóúüñ\s]+?)(?:\s+(?:a\s+las\s+|a\s+)(.+))?",
        
        # Formato más natural
        r"recordatorio\s+(?:de\s+)?([a-záéíóúüñ\s]+?)\s+(?:ahora\s+)?(?:a\s+las\s+|cada\s+|por\s+)(.+)",
        
        # Modificación directa
        r"(?:quiero\s+)?(?:cambiar|modificar)\s+([a-záéíóúüñ\s]+?)(?:\s+(?:a|cada|por)\s+(.+))?",
    ]
    
    for pattern in modification_patterns:
        match = re.search(pattern, text_lower)
        if match:
            target = match.group(1).strip()
            new_schedule = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
            
            # Filtrar palabras que no son nombres de recordatorios
            if target not in ["mi", "el", "la", "recordatorio", "hora", "frecuencia"]:
                logger.info(f"Detected reminder modification request: '{text}' -> target: '{target}', schedule: '{new_schedule}'")
                return {
                    "action": "modify",
                    "target": target,
                    "new_schedule": new_schedule,
                    "detected": True
                }
    
    return None

def parse_reminder_query(text: str, user_phone: str):
    """Detectar consultas sobre recordatorios existentes - VERSIÓN ULTRA-FLEXIBLE"""
    text_lower = text.lower().strip()
    
    # Patrones ultra-flexibles para consultas
    query_patterns = [
        # Preguntas directas
        r"que\s*recordatorios?\s*tengo",
        r"cuales?\s*son\s*mis\s*recordatorios?",
        r"mis\s*recordatorios?",
        r"ver\s*recordatorios?",
        r"recordatorios?\s*activos?",
        r"tengo\s*recordatorios?",
        r"cuantos?\s*recordatorios?",
        r"lista\s*de\s*recordatorios?",
        
        # Variaciones más naturales
        r"que\s*(?:me\s*)?(?:estas\s*)?recordando",
        r"de\s*que\s*(?:me\s*)?(?:tienes\s*que\s*)?recordar",
        r"que\s*(?:tienes\s*)?(?:programado|configurado)",
        r"mostrar\s*recordatorios?",
        r"enseñar\s*recordatorios?",
        r"dime\s*(?:que\s*)?recordatorios?",
        r"cuales?\s*recordatorios?",
        
        # Con palabras interrogativas
        r"(?:que|cuales?|cuantos?)\s*.*recordatorios?",
        r"recordatorios?\s*(?:que\s*)?(?:tengo|hay|existen)",
        
        # Formas muy casuales
        r"recordatorios?\?",
        r"que\s*hay\s*programado",
        r"que\s*tienes\s*para\s*mi",
        r"que\s*me\s*vas\s*a\s*recordar",
        
        # Con errores tipográficos comunes
        r"recordatroios?",
        r"recrodatorios?",
        r"recordarios?",
    ]
    
    is_query = any(re.search(pattern, text_lower) for pattern in query_patterns)
    
    if is_query:
        logger.info(f"FLEXIBLE reminder query detected for {user_phone}: '{text}'")
        return True
    
    return False

def parse_reminder_removal(text: str, user_phone: str):
    """Detectar solicitudes de eliminación de recordatorios específicos"""
    text_lower = text.lower().strip()
    
    # Patrones para eliminar recordatorios específicos
    removal_patterns = [
        # Por ID
        r"(?:elimina|borra|quita|remueve|cancela|detén|detene|para|parar)\s+(?:el\s+)?recordatorio\s+(?:con\s+)?(?:id\s+|#)?(\d+)",
        r"(?:eliminar|borrar|quitar|remover|cancelar|detener|parar)\s+(?:el\s+)?recordatorio\s+(?:con\s+)?(?:id\s+|#)?(\d+)",
        r"(?:ya\s+)?no\s+(?:me\s+)?recuerdes\s+(?:el\s+)?(?:recordatorio\s+)?(?:con\s+)?(?:id\s+|#)?(\d+)",
        r"recordatorio\s+(?:con\s+)?(?:id\s+|#)?(\d+)\s+(?:eliminalo|borralo|quitalo|cancelalo)",
        
        # Por número en la lista
        r"(?:elimina|borra|quita|remueve|cancela|detén|detene|para|parar)\s+(?:el\s+)?recordatorio\s+(?:número\s+|#)?(\d+)",
        r"(?:eliminar|borrar|quitar|remover|cancelar|detener|parar)\s+(?:el\s+)?recordatorio\s+(?:número\s+|#)?(\d+)",
        
        # Directamente el número
        r"(?:elimina|borra|quita|remueve|cancela|detén|detene|para|parar|eliminar|borrar|quitar|remover|cancelar|detener|parar)\s+(?:el\s+)?(\d+)",
        r"(?:elimina|borra|quita|remueve|cancela|detén|detene|para|parar|eliminar|borrar|quitar|remover|cancelar|detener|parar)\s+recordatorio\s+(\d+)",
    ]
    
    for pattern in removal_patterns:
        match = re.search(pattern, text_lower)
        if match:
            reminder_id = int(match.group(1))
            logger.info(f"Detected reminder removal request for ID {reminder_id}")
            return reminder_id
    
    return None

def contains_reminder_keywords(text: str) -> bool:
    """Detectar si el texto contiene palabras clave relacionadas con recordatorios"""
    text_lower = text.lower().strip()
    
    # Lista más acotada de palabras clave de recordatorio (eliminando suplementos específicos)
    reminder_keywords = [
        "recordar", "recordatorio", "avisar", "notificar", "programar", 
        "recordarme", "recuérdame", "avísame", "notifícame", "programa"
    ]
    
    # Palabras clave secundarias (requieren al menos una palabra primaria)
    secondary_keywords = [
        "agua", "tomar", "dormir", "meditar", "ejercicio"
    ]
    
    # Si tiene al menos una palabra clave principal
    has_primary = any(keyword in text_lower for keyword in reminder_keywords)
    
    # Si tiene palabras secundarias sin primarias, no es un recordatorio
    if not has_primary and any(keyword in text_lower for keyword in secondary_keywords):
        return False
        
    return has_primary

def is_explicit_reminder_request(text: str) -> bool:
    """VERSIÓN MEJORADA: Detección más precisa de solicitudes explícitas"""
    text_lower = text.lower().strip()
    
    # Patrones explícitos de recordatorio
    explicit_patterns = [
        r"recuérda(?:me)?",
        r"recordar\s+(?:tomar|que|me)",
        r"(?:quiero|necesito)\s+(?:un\s+)?recordatorio",
        r"(?:configura|crea|programa|establece)(?:me)?\s+(?:un\s+)?recordatorio",
        r"(?:quiero|necesito)\s+que\s+me\s+recuerdes",
        r"ayuda(?:me)?\s+a\s+recordar",
        r"recordatorio\s+(?:de|para)",
        r"avisa(?:me)?\s+(?:cuando|que)",
        
        # Comandos manuales
        r"^/recordar",
        r"^/agua",
        r"^/dormir",
        r"^/meditar",
        
        # Patrones más naturales pero explícitos
        r"que\s+(?:me\s+)?recuerdes\s+(?:tomar|que)",
        r"recordar(?:me)?\s+(?:de\s+)?tomar",
        r"no\s+(?:se\s+me\s+)?olvide\s+(?:tomar|de)",
        r"para\s+no\s+olvidar(?:me)?\s+(?:de\s+)?tomar"
    ]
    
    # Verificar patrones explícitos
    for pattern in explicit_patterns:
        if re.search(pattern, text_lower):
            logger.info(f"Detected explicit reminder request: '{text}' (pattern: {pattern})")
            return True
    
    # Casos especiales: comandos con tomar + tiempo
    if re.search(r"tomar\s+.*\s+(?:cada|a\s+las|por\s+la|en\s+la)", text_lower):
        logger.info(f"Detected 'tomar' with timing, treating as explicit reminder: '{text}'")
        return True
    
    return False

def format_interval_text(interval_minutes: float) -> str:
    """Formatear texto de intervalo de forma legible"""
    if interval_minutes < 1:
        seconds = int(interval_minutes * 60)
        return f"cada {seconds} segundos"
    elif interval_minutes == 1:
        return "cada minuto"
    elif interval_minutes < 60:
        if interval_minutes == int(interval_minutes):
            return f"cada {int(interval_minutes)} minutos"
        else:
            return f"cada {interval_minutes} minutos"
    else:
        hours = interval_minutes / 60
        if hours == int(hours):
            return f"cada {int(hours)} horas"
        else:
            return f"cada {round(hours, 1)} horas"
