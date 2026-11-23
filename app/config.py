"""Configuration is server-side; secrets are never included in the public config."""
import os
from dotenv import load_dotenv

load_dotenv()
DEMO = os.getenv('DEMO_MODE', 'true').lower() == 'true'
ORIGIN = os.getenv('APP_ORIGIN', 'http://127.0.0.1:8000').rstrip('/')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./Pawgress.db')
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')
CHAT_MODEL = os.getenv('CHAT_MODEL', 'gpt-5.4-nano')
PLAN_MODEL = os.getenv('PLAN_MODEL', 'gpt-5.4-mini')
BUDGET = round(float(os.getenv('MONTHLY_AI_BUDGET_USD', '5')) * 1_000_000)
DAILY_CHAT_LIMIT = int(os.getenv('DAILY_CHAT_LIMIT', '30'))
ADMINS = {s.strip().lower() for s in os.getenv('ADMIN_EMAILS', '').split(',') if s.strip()}
