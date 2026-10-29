"""Configuración solo desde variables de entorno. Sin secretos en código."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}
DATABASE_PATH = os.getenv("DATABASE_PATH", "conecta.db")
FREE_DAILY_LIKES = 20
SUPPORTED_LANGUAGES = ("es", "en", "pt", "it")
