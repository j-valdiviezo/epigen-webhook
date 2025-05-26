"""
WhatsApp Webhook Server for Epigen Chatbot with Ultra-Flexible Smart Reminders
This server receives webhook events from WhatsApp via Green API,
processes them using Google's Gemini AI model, and sends responses
back to the user. Features ULTRA-FLEXIBLE intelligent reminder setup with DECIMAL support.
"""
import os
import time
import sys
import re
from typing import Dict, List, Any, Optional
import requests
from flask import Flask, request, jsonify
from loguru import logger
from dotenv import load_dotenv

# Imports para recordatorios
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz
import atexit
from supabase import create_client, Client

# Importar módulos propios
import knowledge_base
import reminder_utils
import db_utils

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# ==================== CONFIGURATION ====================
# Get API credentials from environment variables
GREEN_API_ID = os.environ.get("GREEN_API_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

logger.info(f"GREEN_API_ID={GREEN_API_ID}, GREEN_API_TOKEN={GREEN_API_TOKEN}")
logger.info(f"SUPABASE_URL={SUPABASE_URL}")

# Check if required environment variables are set
if not GREEN_API_ID or not GREEN_API_TOKEN:
    logger.warning("WhatsApp API credentials not set. Webhook will not be able to send messages.")
if not GOOGLE_API_KEY:
    logger.warning("Google API key not set. AI responses will not work.")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logger.warning("Supabase credentials not set. Reminders will not work.")

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO")

# ==================== INITIALIZATION ====================
# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Initialize scheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone('America/Mexico_City'))
scheduler.start()

# Ensure scheduler shuts down properly
atexit.register(lambda: scheduler.shutdown())

# ==================== RECORDATORIO FUNCIONES MEJORADAS ====================

def send_reminder(user_phone: str, message: str):
    """Enviar un mensaje de recordatorio"""
    try:
        send_result = send_whatsapp_message(user_phone, f"{message}")
        logger.info(f"Reminder sent to {user_phone}: {message}")
        return send_result
    except Exception as e:
        logger.error(f"Error sending reminder to {user_phone}: {str(e)}")
        return None

def modify_existing_reminder(user_phone: str, modification_info: dict):
    """NUEVA FUNCIÓN: Modificar recordatorios existentes"""
    try:
        target = modification_info["target"]
        new_schedule = modification_info.get("new_schedule")
        
        # Obtener recordatorios actuales del usuario
        existing_reminders = db_utils.get_user_reminders_supabase(supabase, user_phone)
        
        if not existing_reminders:
            return "❌ No tienes recordatorios activos para modificar."
        
        # Buscar recordatorio que coincida
        target_reminder = None
        for reminder in existing_reminders:
            # Buscar por ID si es número
            if target.isdigit() and reminder["id"] == int(target):
                target_reminder = reminder
                break
            # Buscar por nombre/tipo
            elif (target in reminder.get("nickname", "").lower() or 
                  target in reminder.get("display_name", "").lower() or
                  target == reminder["reminder_type"]):
                target_reminder = reminder
                break
        
        if not target_reminder:
            return f"❌ No encontré un recordatorio que coincida con '{target}'. Usa 'que recordatorios tengo' para ver la lista."
        
        # Si no se especifica nuevo horario, preguntar
        if not new_schedule:
            reminder_name = target_reminder.get("nickname", target_reminder["reminder_type"])
            return f"¿A qué horario o frecuencia quieres cambiar el recordatorio de *{reminder_name}*?\n\nEjemplos:\n• 'cada 2 horas'\n• 'a las 8 pm'\n• 'cada noche'"
        
        # Procesar nuevo horario
        frequency = reminder_utils.parse_flexible_frequency(new_schedule)
        
        if frequency is None:  # Es horario específico
            new_times = reminder_utils.parse_flexible_times(new_schedule)
            return update_reminder_to_times(user_phone, target_reminder, new_times)
        else:  # Es frecuencia
            return update_reminder_to_interval(user_phone, target_reminder, frequency)
            
    except Exception as e:
        logger.error(f"Error modifying reminder: {str(e)}")
        return f"❌ Error al modificar recordatorio: {str(e)}"

def update_reminder_to_times(user_phone: str, reminder: dict, new_times: List[str]):
    """Actualizar recordatorio a horarios específicos"""
    try:
        # Desactivar recordatorio actual
        db_utils.deactivate_reminder_supabase(supabase, user_phone, reminder["id"])
        
        # Eliminar job del scheduler
        try:
            for job in scheduler.get_jobs():
                if f"_{user_phone}_{reminder['id']}" in job.id:
                    scheduler.remove_job(job.id)
        except:
            pass
        
        # Crear nuevos recordatorios para cada horario
        created_count = 0
        created_names = []
        
        for time_str in new_times:
            try:
                hour, minute = map(int, time_str.split(':'))
                
                # Crear nombre único para cada hora
                base_name = reminder.get("nickname", reminder["reminder_type"])
                time_display_name = f"{base_name} ({time_str})"
                
                new_reminder_id = db_utils.save_reminder_supabase(
                    supabase=supabase,
                    user_phone=user_phone,
                    reminder_type=reminder["reminder_type"],
                    message=reminder["message"],
                    display_name=time_display_name,
                    cron_expression=f"{minute} {hour} * * *",
                    nickname=f"{base_name} {time_str}"
                )
                
                if new_reminder_id:
                    scheduler.add_job(
                        func=send_reminder,
                        trigger=CronTrigger(hour=hour, minute=minute),
                        args=[user_phone, reminder["message"]],
                        id=f"{reminder['reminder_type']}_{user_phone}_{new_reminder_id}",
                        replace_existing=True
                    )
                    created_count += 1
                    created_names.append(time_display_name)
                    
            except Exception as e:
                logger.error(f"Error creating reminder at {time_str}: {str(e)}")
                continue
        
        if created_count > 0:
            times_text = ", ".join(new_times)
            emoji = reminder_utils.REMINDER_EMOJIS.get(reminder["reminder_type"], "🔔")
            return f"✅ ¡Recordatorio actualizado! Ahora te recordaré a las {times_text}.\n\n{emoji} Nuevos recordatorios: {created_count}"
        else:
            return "❌ No pude actualizar el recordatorio con los nuevos horarios."
            
    except Exception as e:
        logger.error(f"Error updating reminder to times: {str(e)}")
        return f"❌ Error al actualizar recordatorio: {str(e)}"

def update_reminder_to_interval(user_phone: str, reminder: dict, new_interval: float):
    """Actualizar recordatorio a intervalo"""
    try:
        # Desactivar recordatorio actual
        db_utils.deactivate_reminder_supabase(supabase, user_phone, reminder["id"])
        
        # Eliminar job del scheduler
        try:
            for job in scheduler.get_jobs():
                if f"_{user_phone}_{reminder['id']}" in job.id:
                    scheduler.remove_job(job.id)
        except:
            pass
        
        # Crear nuevo recordatorio con intervalo
        base_name = reminder.get("nickname", reminder["reminder_type"])
        
        new_reminder_id = db_utils.save_reminder_supabase(
            supabase=supabase,
            user_phone=user_phone,
            reminder_type=reminder["reminder_type"],
            message=reminder["message"],
            display_name=f"Recordatorio de {base_name}",
            interval_minutes=new_interval,
            nickname=base_name
        )
        
        if new_reminder_id:
            scheduler.add_job(
                func=send_reminder,
                trigger=IntervalTrigger(minutes=new_interval),
                args=[user_phone, reminder["message"]],
                id=f"{reminder['reminder_type']}_{user_phone}_{new_reminder_id}",
                replace_existing=True
            )
            
            freq_text = reminder_utils.format_interval_text(new_interval)
            emoji = reminder_utils.REMINDER_EMOJIS.get(reminder["reminder_type"], "🔔")
            return f"✅ ¡Recordatorio actualizado! Ahora te recordaré {freq_text}.\n\n{emoji} Recordatorio: *{base_name}*"
        else:
            return "❌ No pude actualizar el recordatorio con la nueva frecuencia."
            
    except Exception as e:
        logger.error(f"Error updating reminder to interval: {str(e)}")
        return f"❌ Error al actualizar recordatorio: {str(e)}"

def create_timed_supplement_reminder(sender: str, supplement_name: str, times: List[str]) -> str:
    """Crear recordatorio de suplemento con horarios específicos"""
    created_count = 0
    created_names = []
    
    for time_str in times:
        try:
            hour, minute = map(int, time_str.split(':'))
            time_display_name = f"{supplement_name} ({time_str})"
            
            reminder_id = db_utils.save_reminder_supabase(
                supabase=supabase,
                user_phone=sender,
                reminder_type="supplement",
                message=f"💊 Es hora de tomar tu {supplement_name}",
                display_name=time_display_name,
                cron_expression=f"{minute} {hour} * * *",
                nickname=f"{supplement_name} {time_str}"
            )
            
            if reminder_id:
                scheduler.add_job(
                    func=send_reminder,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    args=[sender, f"💊 Es hora de tomar tu {supplement_name}"],
                    id=f"supplement_{sender}_{reminder_id}",
                    replace_existing=True
                )
                created_count += 1
                created_names.append(time_display_name)
                
        except Exception as e:
            logger.error(f"Error creating reminder at {time_str}: {str(e)}")
            continue
    
    if created_count > 0:
        times_text = ", ".join(times)
        names_text = ", ".join([f"*{name}*" for name in created_names])
        return f"✅ ¡Listo! Recordatorio para *{supplement_name}* configurado a las {times_text}.\n\n💊 Te recordaré tomarlo puntualmente.\n\n🔍 Recordatorios: {names_text}"
    else:
        return "❌ No pude configurar el recordatorio con los horarios especificados."

def create_interval_supplement_reminder(sender: str, supplement_name: str, interval_minutes: float) -> str:
    """Crear recordatorio de suplemento con intervalo"""
    display_name = f"Recordatorio de {supplement_name}"
    
    reminder_id = db_utils.save_reminder_supabase(
        supabase=supabase,
        user_phone=sender,
        reminder_type="supplement", 
        message=f"💊 Es hora de tomar tu {supplement_name}",
        display_name=display_name,
        interval_minutes=interval_minutes,
        nickname=supplement_name
    )
    
    if reminder_id:
        scheduler.add_job(
            func=send_reminder,
            trigger=IntervalTrigger(minutes=interval_minutes),
            args=[sender, f"💊 Es hora de tomar tu {supplement_name}"],
            id=f"supplement_{sender}_{reminder_id}",
            replace_existing=True
        )
        
        freq_text = reminder_utils.format_interval_text(interval_minutes)
        return f"✅ ¡Listo! Recordatorio para *{supplement_name}* configurado {freq_text}.\n\n💊 Te recordaré tomarlo regularmente.\n\n🔍 Recordatorio: *{display_name}*"
    else:
        return "❌ Error al crear recordatorio."

def create_intelligent_reminder(user_phone: str, reminder_info: dict):
    """VERSIÓN MEJORADA: Crear recordatorio con mejor manejo"""
    logger.info(f"Creating IMPROVED reminder for {user_phone}: {reminder_info}")
    
    try:
        reminder_type = reminder_info["type"]
        message = reminder_info["message"]
        display_name = reminder_info.get("display_name", "")
        
        if not display_name or display_name == "None":
            if reminder_type == "supplement" and reminder_info.get("supplement_name"):
                display_name = f"Recordatorio de {reminder_info['supplement_name']}"
            else:
                display_name = reminder_utils.generate_reminder_name(reminder_type)
        
        # Gestionar recordatorio basado en intervalo
        if reminder_info.get("interval_minutes") is not None:
            interval_minutes = float(reminder_info["interval_minutes"])
            
            if interval_minutes < 0.0167:
                return "❌ El intervalo mínimo es 1 segundo. Por favor elige un intervalo mayor."
            
            logger.info(f"Creating {reminder_type} reminder: {interval_minutes} minutes interval")
            
            nickname = None
            if reminder_type == "supplement" and reminder_info.get("supplement_name"):
                nickname = reminder_info["supplement_name"]
            
            # Llamada a la función save_reminder_supabase sin pasar nickname si es None
            if nickname:
                reminder_id = db_utils.save_reminder_supabase(
                    supabase=supabase,
                    user_phone=user_phone,
                    reminder_type=reminder_type,
                    message=message,
                    display_name=display_name,
                    interval_minutes=interval_minutes,
                    nickname=nickname
                )
            else:
                reminder_id = db_utils.save_reminder_supabase(
                    supabase=supabase,
                    user_phone=user_phone,
                    reminder_type=reminder_type,
                    message=message,
                    display_name=display_name,
                    interval_minutes=interval_minutes
                )
            
            if reminder_id:
                scheduler.add_job(
                    func=send_reminder,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    args=[user_phone, message],
                    id=f"{reminder_type}_{user_phone}_{reminder_id}",
                    replace_existing=True
                )
                
                emoji = reminder_utils.REMINDER_EMOJIS.get(reminder_type, "🔔")
                freq_text = reminder_utils.format_interval_text(interval_minutes)
                
                if reminder_type == "water":
                    return f"✅ ¡Perfecto! He configurado tu recordatorio de agua {freq_text}.\n\n{emoji} Te recordaré mantenerte hidratado regularmente.\n\n🔍 Recordatorio: *{display_name}*"
                elif reminder_type == "supplement":
                    supplement_name = reminder_info.get("supplement_name", "suplemento")
                    return f"✅ ¡Listo! He configurado tu recordatorio para *{supplement_name}* {freq_text}.\n\n{emoji} Te recordaré tomarlo regularmente.\n\n🔍 Recordatorio: *{display_name}*"
                else:
                    return f"✅ ¡Listo! He configurado tu recordatorio de {reminder_type} {freq_text}.\n\n{emoji} Te lo recordaré puntualmente.\n\n🔍 Recordatorio: *{display_name}*"
            else:
                return "❌ Error al guardar recordatorio en la base de datos."
        
        # Gestionar recordatorio basado en horarios específicos
        elif reminder_info.get("times"):
            times = reminder_info["times"]
            logger.info(f"Creating {reminder_type} reminder with specific times: {times}")
            
            created_count = 0
            created_names = []
            
            for time_str in times:
                try:
                    hour, minute = map(int, time_str.split(':'))
                    
                    if reminder_type == "supplement" and reminder_info.get("supplement_name"):
                        time_display_name = f"{reminder_info['supplement_name']} ({time_str})"
                        nickname = f"{reminder_info['supplement_name']} {time_str}"
                    else:
                        base_name = display_name.split(" (")[0]
                        time_display_name = f"{base_name} ({time_str})"
                        nickname = None
                    
                    # Llamada a la función save_reminder_supabase sin pasar nickname si es None
                    if nickname:
                        reminder_id = db_utils.save_reminder_supabase(
                            supabase=supabase,
                            user_phone=user_phone,
                            reminder_type=reminder_type,
                            message=message,
                            display_name=time_display_name,
                            cron_expression=f"{minute} {hour} * * *",
                            nickname=nickname
                        )
                    else:
                        reminder_id = db_utils.save_reminder_supabase(
                            supabase=supabase,
                            user_phone=user_phone,
                            reminder_type=reminder_type,
                            message=message,
                            display_name=time_display_name,
                            cron_expression=f"{minute} {hour} * * *"
                        )
                    
                    if reminder_id:
                        scheduler.add_job(
                            func=send_reminder,
                            trigger=CronTrigger(hour=hour, minute=minute),
                            args=[user_phone, message],
                            id=f"{reminder_type}_{user_phone}_{reminder_id}",
                            replace_existing=True
                        )
                        created_count += 1
                        created_names.append(time_display_name)
                        
                except Exception as e:
                    logger.error(f"Error creating reminder at {time_str}: {str(e)}")
                    continue
            
            if created_count > 0:
                emoji = reminder_utils.REMINDER_EMOJIS.get(reminder_type, "🔔")
                times_text = ", ".join(times)
                names_text = ", ".join([f"*{name}*" for name in created_names])
                
                if reminder_type == "sleep":
                    return f"✅ ¡Perfecto! He configurado tu recordatorio para dormir a las {times_text}.\n\n{emoji} Te ayudaré a mantener un buen hábito de sueño.\n\n🔍 Recordatorios: {names_text}"
                elif reminder_type == "supplement":
                    supplement_name = reminder_info.get("supplement_name", "suplemento")
                    return f"✅ ¡Listo! He configurado tu recordatorio para *{supplement_name}* a las {times_text}.\n\n{emoji} Te recordaré tomarlo puntualmente.\n\n🔍 Recordatorios: {names_text}"
                else:
                    return f"✅ ¡Configurado! Tu recordatorio de {reminder_type} a las {times_text}.\n\n{emoji} Te lo recordaré puntualmente.\n\n🔍 Recordatorios: {names_text}"
            else:
                return "❌ No pude configurar los recordatorios con los horarios especificados."
        
        else:
            return "❌ No pude entender los horarios para tu recordatorio. Por favor especifica cuándo quieres que te recuerde."
        
    except Exception as e:
        logger.error(f"Error creating IMPROVED reminder: {str(e)}")
        return f"❌ Hubo un error al configurar el recordatorio: {str(e)}"

def list_user_reminders_intelligent(user_phone: str):
    """Listar recordatorios con mejor formato para decimales y tipos"""
    try:
        reminders = db_utils.get_user_reminders_supabase(supabase, user_phone)
        logger.info(f"Found {len(reminders)} reminders for {user_phone}")
        
        if not reminders:
            return "📝 No tienes recordatorios activos.\n\n💡 Dime qué quieres recordar y yo lo configuro automáticamente."
        
        response = "📝 *Tus recordatorios activos:*\n\n"
        
        # Agrupar recordatorios por tipo para mejor visualización
        reminder_groups = {}
        for i, reminder in enumerate(reminders, 1):
            reminder_type = reminder["reminder_type"]
            if reminder_type not in reminder_groups:
                reminder_groups[reminder_type] = []
            reminder_groups[reminder_type].append(reminder)
        
        # Mostrar recordatorios organizados por tipo
        count = 1
        for reminder_type, group in reminder_groups.items():
            emoji = reminder_utils.REMINDER_EMOJIS.get(reminder_type, "🔔")
            
            for reminder in group:
                # MODIFICACIÓN: Obtener nombre descriptivo del recordatorio
                # Priorizar: nickname > display_name > tipo capitalizado
                display_name = reminder.get("nickname", "")
                if not display_name or display_name == "None":
                    display_name = reminder.get("display_name", "")
                if not display_name or display_name == "None":
                    # Fallback a un nombre basado en el tipo
                    if reminder_type == "water":
                        display_name = "Agua"
                    elif reminder_type == "supplement":
                        display_name = "Suplemento"
                    elif reminder_type == "sleep":
                        display_name = "Dormir"
                    elif reminder_type == "meditation":
                        display_name = "Meditación"
                    elif reminder_type == "exercise":
                        display_name = "Ejercicio"
                    else:
                        display_name = reminder_type.capitalize()
                
                if reminder["interval_minutes"]:
                    interval = float(reminder["interval_minutes"])
                    freq_text = reminder_utils.format_interval_text(interval)
                    response += f"{count}. {emoji} {display_name}: {freq_text} (ID: {reminder['id']})\n"
                else:
                    # Extraer hora del cron si está disponible
                    time_str = "horario específico"
                    if reminder["cron_expression"]:
                        parts = reminder["cron_expression"].split()
                        if len(parts) >= 2:
                            minute, hour = parts[0], parts[1]
                            time_str = f"{hour}:{minute.zfill(2)}"
                    
                    response += f"{count}. {emoji} {display_name}: {time_str} (ID: {reminder['id']})\n"
                count += 1
        
        response += "\n💡 Para detener todos los recordatorios, escribe: */borrar_todo*"
        response += "\n💡 Para eliminar uno específico, escribe: *Elimina recordatorio [ID]*" 
        return response
        
    except Exception as e:
        logger.error(f"Error listing user reminders: {str(e)}")
        return "❌ Error al obtener tus recordatorios. Inténtalo de nuevo."

# ==================== MESSAGE PROCESSING MEJORADO ====================

def process_message(sender: str, message_text: str) -> str:
    """VERSIÓN MEJORADA: Procesamiento de mensajes con mejor detección"""
    try:
        logger.info(f"Processing IMPROVED message from {sender}: '{message_text}'")
        
        # 1. Comandos manuales (prioridad máxima)
        if message_text.lower().startswith('/'):
            logger.info("Processing as manual command")
            return handle_reminder_command(sender, message_text)
        
        # Obtener historial de chat
        chat_history = db_utils.get_chat_history_from_supabase(supabase, sender, limit=20)
        if not chat_history:
            chat_history = db_utils.initialize_user_chat(supabase, sender)
        
        # Guardar mensaje del usuario
        user_message_id = db_utils.save_message_to_supabase(supabase, sender, "user", message_text)
        logger.info(f"User message saved with ID: {user_message_id}")
        
        # 2. Consultas sobre recordatorios existentes
        if reminder_utils.parse_reminder_query(message_text, sender):
            logger.info("DETECTED REMINDER QUERY")
            response = list_user_reminders_intelligent(sender)
            db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
            return response
        
        # 3. Eliminación de recordatorio específico
        reminder_id_to_remove = reminder_utils.parse_reminder_removal(message_text, sender)
        if reminder_id_to_remove is not None:
            logger.info(f"DETECTED REMINDER REMOVAL - ID {reminder_id_to_remove}")
            success = db_utils.deactivate_reminder_supabase(supabase, sender, reminder_id_to_remove)
            
            if success:
                # Detener job en scheduler
                try:
                    for job in scheduler.get_jobs():
                        if f"_{sender}_{reminder_id_to_remove}" in job.id:
                            scheduler.remove_job(job.id)
                            logger.info(f"Removed scheduler job for reminder ID {reminder_id_to_remove}")
                except Exception as e:
                    logger.error(f"Error removing scheduler job: {str(e)}")
                
                response = f"✅ Recordatorio #{reminder_id_to_remove} eliminado correctamente."
            else:
                response = f"❌ No pude eliminar el recordatorio con ID {reminder_id_to_remove}. ¿Seguro que es correcto?"
            
            db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
            return response
        
        # 4. NUEVA: Modificación de recordatorios
        modification_info = reminder_utils.parse_reminder_modification(message_text, sender)
        if modification_info:
            logger.info("DETECTED REMINDER MODIFICATION")
            response = modify_existing_reminder(sender, modification_info)
            db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
            return response
        
        # 5. Solicitudes de información sobre productos
        if (reminder_utils.is_information_request(message_text) or 
            reminder_utils.is_specific_product_request(message_text)):
            logger.info("DETECTED INFORMATION REQUEST")
            
            current_history = chat_history.copy()
            current_history.append({"role": "user", "content": message_text})
            
            response = generate_ai_response_with_context(current_history, message_text, sender)
            db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
            return response
        
        # 6. Creación de recordatorios explícitos
        reminder_info = reminder_utils.parse_reminder_request(message_text, sender)
        if reminder_info and reminder_info.get("detected"):
            logger.info("DETECTED EXPLICIT REMINDER REQUEST")
            response = create_intelligent_reminder(sender, reminder_info)
            db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
            return response
        
        # 7. Conversación normal
        logger.info("Processing as normal conversation")
        current_history = chat_history.copy()
        current_history.append({"role": "user", "content": message_text})
        
        response = generate_ai_response_with_context(current_history, message_text, sender)
        db_utils.save_message_to_supabase(supabase, sender, "assistant", response)
        return response
        
    except Exception as e:
        logger.error(f"Error in IMPROVED message processing: {str(e)}")
        return "Lo siento, tuve un problema procesando tu mensaje. Por favor intenta de nuevo."




def generate_ai_response_with_context(chat_history: List[Dict[str, str]], user_message: str, user_phone: str) -> str:
    """Generate a response using the Google Gemini model with enhanced context."""
    import google.generativeai as genai
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 1000,
    }
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-05-20", 
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    
    # Format conversation history
    formatted_history = []
    for message in chat_history:
        role = "user" if message["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [message["content"]]})
    
    # Obtener estadísticas del usuario para personalización
    user_stats = db_utils.get_user_stats(supabase, user_phone)
    active_reminders = db_utils.get_user_reminders_supabase(supabase, user_phone)
    
    user_context = ""
    if user_stats.get("total_messages", 0) > 5:
        user_context = f"Este usuario ha tenido {user_stats['total_messages']} mensajes contigo, así que ya te conoce."
    
    reminders_context = ""
    if active_reminders:
        reminder_types = [r['reminder_type'] for r in active_reminders]
        reminders_context = f"Este usuario tiene {len(active_reminders)} recordatorios activos: {', '.join(reminder_types)}"
    
    # Obtener el mensaje del sistema desde el módulo de knowledge_base
    system_message = knowledge_base.get_system_message(
        user_context=user_context,
        reminders_context=reminders_context
    )
    
    formatted_history.insert(0, {"role": "model", "parts": [system_message]})
    
    # Generate response
    chat = model.start_chat(history=formatted_history)
    response = chat.send_message(user_message)
    
    return response.text

def handle_reminder_command(sender: str, command: str) -> str:
    """VERSIÓN MEJORADA: Comandos con mejor parsing de horarios"""
    parts = command.lower().strip().split(' ')
    main_command = parts[0]
    
    if main_command == '/ayuda' or main_command == '/help':
        return """🤖 *Comandos de Recordatorios Mejorados:*

*Crear recordatorios:*
- */recordar suplemento [nombre] [horario/frecuencia]*
  Ejemplos: 
  • `/recordar suplemento magnesio 8 pm`
  • `/recordar suplemento vitamina cada 2 horas`
  • `/recordar suplemento omega cada noche`

*Gestionar recordatorios:*
- */mis_recordatorios* - Ver recordatorios activos
- */borrar [ID]* - Eliminar recordatorio específico  
- */borrar_todo* - Detener todos los recordatorios

*Comandos rápidos:*
- */agua* - Recordatorio de agua cada hora
- */dormir* - Recordatorio para dormir a las 10pm

*Modificar recordatorios:*
Ahora puedes decir naturalmente:
• "Cambia mi recordatorio de magnesio a las 9 pm"
• "Modifica mi recordatorio de agua cada 30 minutos"

¡También funciona con lenguaje natural sin comandos! 😊"""
    
    elif main_command == '/recordar':
        if len(parts) < 3:
            return "❌ Formato: */recordar suplemento [nombre] [horario]*\n\nEjemplos:\n• `/recordar suplemento magnesio 8 pm`\n• `/recordar suplemento omega cada noche`"
        
        reminder_type = parts[1].lower()
        
        if reminder_type == "suplemento":
            if len(parts) < 4:
                return "❌ Formato: */recordar suplemento [nombre] [horario]*"
            
            supplement_name = parts[2].title()
            schedule_text = ' '.join(parts[3:])
            
            # Usar las funciones mejoradas
            frequency = reminder_utils.parse_flexible_frequency(schedule_text)
            
            if frequency is None:  # Es horario específico  
                times = reminder_utils.parse_flexible_times(schedule_text)
                return create_timed_supplement_reminder(sender, supplement_name, times)
            else:  # Es frecuencia
                return create_interval_supplement_reminder(sender, supplement_name, frequency)
        
        # Otros tipos de recordatorio...
        else:
            return f"❌ Tipo '{reminder_type}' no soportado aún. Usa: suplemento"
    
    elif main_command == '/borrar':
        if len(parts) < 2:
            return "❌ Formato: */borrar [ID]*\nEjemplo: `/borrar 25`"
        
        try:
            reminder_id = int(parts[1])
            success = db_utils.deactivate_reminder_supabase(supabase, sender, reminder_id)
            
            if success:
                try:
                    for job in scheduler.get_jobs():
                        if f"_{sender}_{reminder_id}" in job.id:
                            scheduler.remove_job(job.id)
                except:
                    pass
                return f"✅ Recordatorio #{reminder_id} eliminado correctamente."
            else:
                return f"❌ No encontré el recordatorio con ID {reminder_id}."
        except ValueError:
            return "❌ El ID debe ser un número. Ejemplo: `/borrar 25`"
    
    elif main_command == '/mis_recordatorios':
        return list_user_reminders_intelligent(sender)
    
    elif main_command == '/borrar_todo':
        count = db_utils.deactivate_all_reminders_supabase(supabase, sender)
        
        # Eliminar todos los jobs del scheduler
        for job in scheduler.get_jobs():
            if sender in job.id:
                scheduler.remove_job(job.id)
        
        return f"✅ Se han eliminado {count} recordatorios."
    
    # Comandos rápidos existentes
    elif main_command == '/agua':
        reminder_info = {
            "type": "water",
            "message": "💧 ¡Es hora de tomar agua! Mantente hidratado para tu salud.",
            "interval_minutes": 60,
            "display_name": "Recordatorio de Agua",
            "detected": True
        }
        return create_intelligent_reminder(sender, reminder_info)
    
    elif main_command == '/dormir':
        reminder_info = {
            "type": "sleep", 
            "message": "😴 Es hora de prepararte para dormir. Un buen descanso es clave para tu salud.",
            "times": ["22:00"],
            "display_name": "Recordatorio para Dormir",
            "detected": True
        }
        return create_intelligent_reminder(sender, reminder_info)
    
    elif main_command == '/meditar':
        reminder_info = {
            "type": "meditation",
            "message": "🧘 Momento de meditar. Tómate unos minutos para conectar con tu respiración.",
            "times": ["08:00"],
            "display_name": "Recordatorio de Meditación",
            "detected": True
        }
        return create_intelligent_reminder(sender, reminder_info)
    
    elif main_command == '/ejercicio':
        reminder_info = {
            "type": "exercise",
            "message": "🏃 ¡Es hora de moverte! Un poco de ejercicio mejorará tu día.",
            "times": ["17:00"],
            "display_name": "Recordatorio de Ejercicio",
            "detected": True
        }
        return create_intelligent_reminder(sender, reminder_info)
    
    else:
        return "❌ Comando no reconocido. Usa */ayuda* para ver comandos disponibles."

def load_and_schedule_reminders():
    """Cargar y programar todos los recordatorios desde Supabase con soporte decimal"""
    try:
        reminders = db_utils.load_reminders_supabase(supabase)
        scheduled_count = 0
        
        for reminder in reminders:
            try:
                user_phone = reminder["user_phone"]
                reminder_type = reminder["reminder_type"]
                message = reminder["message"]
                reminder_id = reminder["id"]
                
                if reminder["interval_minutes"]:
                    interval_minutes = float(reminder["interval_minutes"])  # Convertir a float
                    
                    scheduler.add_job(
                        func=send_reminder,
                        trigger=IntervalTrigger(minutes=interval_minutes),
                        args=[user_phone, message],
                        id=f"{reminder_type}_{user_phone}_{reminder_id}",
                        replace_existing=True
                    )
                    scheduled_count += 1
                    logger.info(f"Scheduled interval reminder: {interval_minutes} minutes")
                    
                elif reminder["cron_expression"]:
                    parts = reminder["cron_expression"].split()
                    if len(parts) >= 2:
                        minute, hour = int(parts[0]), int(parts[1])
                        
                        scheduler.add_job(
                            func=send_reminder,
                            trigger=CronTrigger(minute=minute, hour=hour),
                            args=[user_phone, message],
                            id=f"{reminder_type}_{user_phone}_{reminder_id}",
                            replace_existing=True
                        )
                        scheduled_count += 1
                        logger.info(f"Scheduled cron reminder: {hour}:{minute:02d}")
                        
            except Exception as e:
                logger.error(f"Error scheduling reminder {reminder.get('id', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Successfully scheduled {scheduled_count} reminders from Supabase")
        return scheduled_count
        
    except Exception as e:
        logger.error(f"Error loading reminders from Supabase: {str(e)}")
        return 0

def initialize_system():
    """Inicializar sistema completo"""
    logger.info("Initializing complete system with ULTRA-FLEXIBLE intelligent reminders and DECIMAL support...")
    
    if not supabase:
        logger.warning("Supabase not configured - persistent features will not work")
        return False
    
    try:
        reminders_test = supabase.table("reminders").select("count", count="exact").execute()
        chat_test = supabase.table("chat_history").select("count", count="exact").execute()
        
        logger.info(f"Connected to Supabase successfully")
        logger.info(f"Reminders in DB: {reminders_test.count}")
        logger.info(f"Chat messages in DB: {chat_test.count}")
        
        scheduled_count = load_and_schedule_reminders()
        
        logger.info(f"System initialized successfully. Scheduled {scheduled_count} reminders.")
        logger.info("ULTRA-FLEXIBLE reminder parsing with DECIMAL support enabled!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {str(e)}")
        return False

# ==================== WHATSAPP INTEGRATION ====================

def send_whatsapp_message(recipient: str, message: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.green-api.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    
    payload = {
        "chatId": f"{recipient}@c.us",
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("idMessage"):
            logger.info(f"Message sent to {recipient}: {message[:50]}...")
        else:
            logger.error(f"Error sending message: {response_data}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"Exception when sending message: {str(e)}")
        return None

# ==================== ROUTE HANDLERS ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Epigen WhatsApp webhook server with ULTRA-FLEXIBLE intelligent reminders and DECIMAL support",
        "version": "8.0.0",
        "features": [
            "AI Chat with Persistent History", 
            "ULTRA-FLEXIBLE Reminder Detection", 
            "DECIMAL Interval Support",
            "Smart Reminder Queries",
            "Natural Language Processing",
            "Manual Reminder Commands",
            "Supabase Integration",
            "Multiple Reminder Types",
            "Better Intent Detection",
            "User-Friendly Reminder Names",
            "Modular Code Structure",
            "Reminder Modification Support",
            "AM/PM Time Format Support",
            "Expression Time Detection",
            "Improved Natural Language Understanding"
        ]
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    logger.info(f"Webhook called with method: {request.method}")
    
    if request.method == 'GET':
        logger.info("Received webhook verification request")
        return jsonify({"status": "webhook is active"}), 200
    
    try:
        raw_data = request.get_data(as_text=True)
        data = request.get_json()
        
        if data.get("typeWebhook") == "incomingMessageReceived":
            message_data = data.get("messageData", {})
            
            if message_data.get("typeMessage") == "textMessage":
                sender = data["senderData"]["sender"].split("@")[0]
                message_text = message_data["textMessageData"]["textMessage"]
                logger.info(f"Received message from {sender}: {message_text}")
                
                ai_response = process_message(sender, message_text)
                logger.info(f"Generated response: {ai_response[:100]}...")
                
                send_result = send_whatsapp_message(sender, ai_response)
                logger.info(f"Send result: {send_result}")
                
        return jsonify({"status": "message processed"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    green_api_status = "configured" if GREEN_API_ID and GREEN_API_TOKEN else "not configured"
    google_api_status = "configured" if GOOGLE_API_KEY else "not configured"
    supabase_status = "configured" if supabase else "not configured"
    
    supabase_stats = {}
    if supabase:
        try:
            reminders_result = supabase.table("reminders").select("count", count="exact").execute()
            messages_result = supabase.table("chat_history").select("count", count="exact").execute()
            
            supabase_stats = {
                "total_reminders": reminders_result.count,
                "total_messages": messages_result.count,
                "connection": "healthy"
            }
        except Exception as e:
            supabase_stats = {
                "connection": "error",
                "error": str(e)
            }
    
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "green_api": green_api_status,
            "google_ai": google_api_status,
            "supabase": supabase_status
        },
        "scheduled_jobs": len(scheduler.get_jobs()) if scheduler else 0,
        "supabase_stats": supabase_stats,
        "features": {
            "ultra_flexible_reminders": True,
            "decimal_interval_support": True,
            "intelligent_queries": True,
            "persistent_chat": True,
            "manual_commands": True,
            "natural_language_processing": True,
            "multiple_reminder_types": True,
            "better_intent_detection": True,
            "friendly_reminder_names": True,
            "modular_code_structure": True,
            "reminder_modification": True,
            "am_pm_time_support": True,
            "expression_time_detection": True
        }
    }), 200

@app.route('/active_reminders', methods=['GET'])
def get_active_reminders():
    try:
        if not supabase:
            return jsonify({"status": "error", "message": "Supabase not configured"}), 500
            
        result = supabase.table("reminders").select("user_phone, nickname, reminder_type, message, interval_minutes, is_active, created_at").order("created_at", desc=True).limit(20).execute()
        
        jobs = scheduler.get_jobs()
        active_jobs = [{"id": job.id, "next_run": str(job.next_run_time)} for job in jobs]
        
        return jsonify({
            "status": "success",
            "reminders_in_db": len(result.data) if result.data else 0,
            "active_jobs": len(active_jobs),
            "jobs": active_jobs[:10],
            "reminders": [
                {
                    "user": r["user_phone"],
                    "display_name": r.get("nickname", "Sin nombre"),
                    "type": r["reminder_type"],
                    "message": r["message"][:50] + "..." if len(r["message"]) > 50 else r["message"],
                    "interval": r["interval_minutes"],
                    "active": r["is_active"],
                    "created": r["created_at"]
                } for r in (result.data[:10] if result.data else [])
            ]
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat_stats/<phone>', methods=['GET'])
def get_chat_stats(phone):
    try:
        stats = db_utils.get_user_stats(supabase, phone)
        recent_messages = db_utils.get_chat_history_from_supabase(supabase, phone, limit=5)
        active_reminders = db_utils.get_user_reminders_supabase(supabase, phone)
        
        return jsonify({
            "status": "success",
            "user_phone": phone,
            "stats": stats,
            "recent_messages_count": len(recent_messages),
            "active_reminders_count": len(active_reminders),
            "reminders": [r["reminder_type"] for r in active_reminders],
            "reminder_names": [r.get("nickname", "Sin nombre") for r in active_reminders]
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    import uvicorn
    
    initialize_system()
    
    port = int(os.environ.get('PORT', 7860))
    
    logger.info(f"Starting server on port {port}")
    logger.info("🤖 ULTRA-FLEXIBLE Reminder System with DECIMAL Support Ready!")
    logger.info("Users can now request reminders with precise intervals:")
    logger.info("  • 'Recuérdame tomar agua cada 30 segundos'")
    logger.info("  • 'Mi magnesio cada 1.5 horas'")
    logger.info("  • 'Vitamina D cada 45 minutos'")
    logger.info("  • 'Recordatorio para dormir a las 10 pm'")
    logger.info("  • 'Recuérdame meditar por la mañana'")
    logger.info("  • Y MUCHAS más formas naturales con precisión decimal!")
    
    uvicorn.run("app:app", host="0.0.0.0", port=port, interface="wsgi")
