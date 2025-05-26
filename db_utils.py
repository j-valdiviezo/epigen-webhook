"""
Módulo para manejar las interacciones con la base de datos Supabase.
Contiene funciones para chat, recordatorios y otras operaciones de persistencia.
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger
from supabase import Client

# ==================== CHAT HISTORY FUNCTIONS ====================

def save_message_to_supabase(supabase: Client, user_phone: str, role: str, content: str, session_id: str = None):
    """Guardar mensaje en el historial de Supabase"""
    if not supabase:
        logger.error("Supabase not initialized")
        return None
        
    try:
        result = supabase.table("chat_history").select("message_order").eq("user_phone", user_phone).order("message_order", desc=True).limit(1).execute()
        
        next_order = 1
        if result.data:
            next_order = result.data[0]["message_order"] + 1
        
        message_data = {
            "user_phone": user_phone,
            "role": role,
            "content": content,
            "message_order": next_order,
            "session_id": session_id or f"session_{user_phone}_{int(time.time())}"
        }
        
        insert_result = supabase.table("chat_history").insert(message_data).execute()
        
        if insert_result.data:
            logger.info(f"Message saved for {user_phone}: {role} - {content[:50]}...")
            return insert_result.data[0]["id"]
        else:
            logger.error(f"Failed to save message: {insert_result}")
            return None
            
    except Exception as e:
        logger.error(f"Error saving message to Supabase: {str(e)}")
        return None

def get_chat_history_from_supabase(supabase: Client, user_phone: str, limit: int = 20):
    """Obtener historial de chat desde Supabase"""
    if not supabase:
        return []
        
    try:
        result = supabase.table("chat_history").select("role, content, timestamp, message_order").eq("user_phone", user_phone).order("message_order", desc=True).limit(limit).execute()
        
        if result.data:
            messages = result.data[::-1]
            formatted_history = []
            for msg in messages:
                formatted_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            logger.info(f"Loaded {len(formatted_history)} messages for {user_phone}")
            return formatted_history
        else:
            logger.info(f"No chat history found for {user_phone}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading chat history from Supabase: {str(e)}")
        return []

def initialize_user_chat(supabase: Client, user_phone: str):
    """Inicializar chat para nuevo usuario"""
    existing_history = get_chat_history_from_supabase(supabase, user_phone, limit=1)
    
    if not existing_history:
        welcome_message = "¡Hola! Soy Noa, tu asistente personal de Epigen. ¿Cómo puedo ayudarte hoy? 🧬\n\nTambién puedo configurar recordatorios automáticamente. Solo dime qué quieres recordar y yo me encargo del resto."
        
        save_message_to_supabase(supabase, user_phone, "assistant", welcome_message)
        logger.info(f"Initialized new chat for {user_phone}")
        
        return [{"role": "assistant", "content": welcome_message}]
    else:
        return existing_history

def get_user_stats(supabase: Client, user_phone: str):
    """Obtener estadísticas del usuario"""
    if not supabase:
        return {}
        
    try:
        message_count_result = supabase.table("chat_history").select("id", count="exact").eq("user_phone", user_phone).execute()
        first_message_result = supabase.table("chat_history").select("created_at").eq("user_phone", user_phone).order("message_order", desc=False).limit(1).execute()
        last_message_result = supabase.table("chat_history").select("created_at").eq("user_phone", user_phone).order("message_order", desc=True).limit(1).execute()
        
        stats = {
            "total_messages": message_count_result.count or 0,
            "first_interaction": first_message_result.data[0]["created_at"] if first_message_result.data else None,
            "last_interaction": last_message_result.data[0]["created_at"] if last_message_result.data else None
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        return {}

# ==================== REMINDERS FUNCTIONS ====================

#def save_reminder_supabase(supabase: Client, user_phone: str, reminder_type: str, message: str, 
#                          display_name: str = "", interval_minutes: float = None, 
#                          cron_expression: str = None):
#    """Guardar recordatorio en Supabase - VERSIÓN COMPATIBLE con bases de datos existentes"""
#    if not supabase:
#        logger.error("Supabase not initialized")
#        return None
#        
#    try:
#        # Convertir a float y validar
#        if interval_minutes is not None:
#            interval_minutes = float(interval_minutes)
#            # Validar que el intervalo sea razonable
#            if interval_minutes <= 0:
#                logger.error(f"Invalid interval_minutes: {interval_minutes}")
#                return None
#            # Redondear a 2 decimales para evitar problemas de precisión
#            interval_minutes = round(interval_minutes, 2)
#        
#        # Preparar datos básicos
#        data = {
#            "user_phone": user_phone,
#            "reminder_type": reminder_type,
#            "message": message,
#            "interval_minutes": interval_minutes,
#            "cron_expression": cron_expression,
#            "is_active": True,
#            "timezone": "America/Mexico_City"
#        }
#        
#        # Intentar añadir nickname/display_name si la columna existe
#        try:
#            # Solo verificamos si podemos hacer una consulta básica
#            check_column = supabase.table("reminders").select("count(*)").limit(1).execute()
#            if display_name:
#                # Intentar añadir el nombre del recordatorio usando nickname
#                data["nickname"] = display_name
#        except Exception as column_error:
#            logger.warning(f"Nickname column might not exist, continuing without it: {column_error}")
#        
#        logger.info(f"Attempting to save reminder with interval_minutes: {interval_minutes} (type: {type(interval_minutes)})")
#        
#        result = supabase.table("reminders").insert(data).execute()
#        
#        if result.data:
#            logger.info(f"Reminder saved successfully for {user_phone}: {reminder_type} - {interval_minutes} minutes")
#            return result.data[0]["id"]
#        else:
#            logger.error(f"Failed to save reminder - Supabase response: {result}")
#            return None
#            
#    except Exception as e:
#        logger.error(f"Error saving reminder to Supabase: {str(e)}")
#        logger.error(f"Data attempted to save: {data if 'data' in locals() else 'N/A'}")
#        return None

def save_reminder_supabase(supabase: Client, user_phone: str, reminder_type: str, message: str, 
                          display_name: str = "", interval_minutes: float = None, 
                          cron_expression: str = None, nickname: str = None):
    """Guardar recordatorio en Supabase - VERSIÓN COMPATIBLE con bases de datos existentes"""
    if not supabase:
        logger.error("Supabase not initialized")
        return None
        
    try:
        # Convertir a float y validar
        if interval_minutes is not None:
            interval_minutes = float(interval_minutes)
            # Validar que el intervalo sea razonable
            if interval_minutes <= 0:
                logger.error(f"Invalid interval_minutes: {interval_minutes}")
                return None
            # Redondear a 2 decimales para evitar problemas de precisión
            interval_minutes = round(interval_minutes, 2)
        
        # Preparar datos básicos
        data = {
            "user_phone": user_phone,
            "reminder_type": reminder_type,
            "message": message,
            "interval_minutes": interval_minutes,
            "cron_expression": cron_expression,
            "is_active": True,
            "timezone": "America/Mexico_City"
        }
        
        # Añadir nickname si se proporciona
        if nickname:
            data["nickname"] = nickname
        
        # Intentar añadir display_name si la columna existe
        if display_name:
            try:
                # Comprobar si la columna display_name existe
                check_column = supabase.table("reminders").select("count(*)").limit(1).execute()
                data["display_name"] = display_name
            except Exception as column_error:
                logger.warning(f"display_name column might not exist, continuing without it: {column_error}")
        
        logger.info(f"Attempting to save reminder with interval_minutes: {interval_minutes} (type: {type(interval_minutes)})")
        logger.info(f"Reminder data: {data}")
        
        result = supabase.table("reminders").insert(data).execute()
        
        if result.data:
            logger.info(f"Reminder saved successfully for {user_phone}: {reminder_type} - {interval_minutes} minutes")
            return result.data[0]["id"]
        else:
            logger.error(f"Failed to save reminder - Supabase response: {result}")
            return None
            
    except Exception as e:
        logger.error(f"Error saving reminder to Supabase: {str(e)}")
        logger.error(f"Data attempted to save: {data if 'data' in locals() else 'N/A'}")
        return None

#def get_user_reminders_supabase(supabase: Client, user_phone: str):
#    """Obtener recordatorios de un usuario específico"""
#    if not supabase:
#        return []
#        
#    try:
#        result = supabase.table("reminders").select("*").eq("user_phone", user_phone).eq("is_active", True).execute()
#        
#        if result.data:
#            return result.data
#        else:
#            return []
#            
#    except Exception as e:
#        logger.error(f"Error getting user reminders: {str(e)}")
#        return []

def get_user_reminders_supabase(supabase: Client, user_phone: str):
    """Obtener recordatorios activos de un usuario específico"""
    if not supabase:
        return []
        
    try:
        # Verificación explícita de que solo se obtienen recordatorios activos
        result = supabase.table("reminders").select("*").eq("user_phone", user_phone).eq("is_active", True).execute()
        
        if result.data:
            logger.info(f"Found {len(result.data)} active reminders for {user_phone}")
            return result.data
        else:
            logger.info(f"No active reminders found for {user_phone}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting user reminders: {str(e)}")
        return []

def deactivate_reminder_supabase(supabase: Client, user_phone: str, reminder_id: int):
    """Desactivar un recordatorio específico por ID"""
    if not supabase:
        return False
        
    try:
        # Modificar esta función para asegurar que estamos intentando eliminar el recordatorio correcto
        result = supabase.table("reminders").update({"is_active": False}).eq("user_phone", user_phone).eq("id", reminder_id).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"Deactivated reminder ID {reminder_id} for {user_phone}")
            return True
        else:
            logger.warning(f"No reminder found to deactivate with ID {reminder_id} for {user_phone}")
            return False
            
    except Exception as e:
        logger.error(f"Error deactivating reminder: {str(e)}")
        return False

def deactivate_all_reminders_supabase(supabase: Client, user_phone: str):
    """Desactivar todos los recordatorios de un usuario"""
    if not supabase:
        return 0
        
    try:
        result = supabase.table("reminders").update({"is_active": False}).eq("user_phone", user_phone).eq("is_active", True).execute()
        
        count = len(result.data) if result.data else 0
        logger.info(f"Deactivated {count} reminders for {user_phone}")
        return count
            
    except Exception as e:
        logger.error(f"Error deactivating all reminders: {str(e)}")
        return 0

def load_reminders_supabase(supabase: Client):
    """Cargar todos los recordatorios activos desde Supabase"""
    if not supabase:
        return []
        
    try:
        result = supabase.table("reminders").select("*").eq("is_active", True).execute()
        
        if result.data:
            logger.info(f"Loaded {len(result.data)} active reminders from Supabase")
            return result.data
        else:
            logger.info("No active reminders found in Supabase")
            return []
            
    except Exception as e:
        logger.error(f"Error loading reminders from Supabase: {str(e)}")
        return []
