import os
import json
import re
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception
from dotenv import load_dotenv

load_dotenv()

# 🚀 التعديل الجوهري: تأخير تعريف الـ LLM لدالة، لمنع الـ Import-Time Crash
def get_llm():
    """تهيئة كائن الذكاء الاصطناعي فقط عند الحاجة الفعلية له"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ مفتاح GROQ_API_KEY مفقود من ملف .env!")
        
    return ChatGroq(
        model_name=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0.1
    )

def _is_transient_error(e: Exception) -> bool:
    """تحديد ما إذا كان الخطأ مؤقتاً عبر فحص HTTP Status Codes"""
    # 1. الفحص الدقيق عبر كود الخطأ (إذا كان متوفراً من مكتبة Groq)
    status_code = getattr(e, 'status_code', getattr(e, 'code', None))
    if status_code:
        if status_code in [429, 502, 503, 504, 408]:
            return True # أخطاء مؤقتة (ضغط، سيرفر، إنترنت)
        if status_code in [400, 401, 403, 404]:
            return False # أخطاء حتمية (صلاحيات، كود خاطئ) لا نضيع فيها المحاولات
            
    # 2. الفحص النصي كطبقة حماية ثانية
    s = str(e).lower()
    if "per day" in s or "tpd" in s or "quota" in s or "insufficient_quota" in s: 
        return False # انتهت الحصة أو الرصيد
    return any(k in s for k in ("429", "rate limit", "timeout", "502", "503", "connection"))

# محامي الدفاع: يعيد المحاولة تلقائياً بذكاء عند سقوط السيرفرات
@retry(
    retry=retry_if_exception(_is_transient_error), 
    wait=wait_random_exponential(min=2, max=60),
    stop=stop_after_attempt(4), 
    reraise=True
)
def safe_llm_invoke(prompt_text):
    # 🚀 التعديل: استدعاء الدالة هنا
    llm = get_llm()
    return llm.invoke(prompt_text).content

def generate_custom_sentence(raw_lead_name, lead_context=""):
    """
    تستخرج اسم المنظم وتؤلف جملة مخصصة بناءً على اسمه ونشاطه الموثق
    """
    prompt = f"""أنت مساعد مبيعات ذكي لمنصة EVNTOWN (منصة حجز تذاكر وإدارة فعاليات).
العميل المستهدف هو: "{raw_lead_name}"
النشاط الموثق أو التقييم: "{lead_context}"

المطلوب منك:
1. استخرج اسم المنظم بشكل احترافي (بدون ألقاب زائدة).
2. اكتب جملة افتتاحية قصيرة جداً (سطر واحد فقط) تثني على نشاطهم الموثق بذكاء. 
3. تحذير صارم: لا تخترع فعاليات وهمية لم ينظموها. إذا كان النشاط الموثق غير كافٍ، اكتب جملة ترحيبية عامة دافئة بدون تفاصيل.

يجب أن يكون الرد بصيغة JSON فقط:
{{
    "organizer_name": "الاسم المنقح",
    "custom_sentence": "الجملة المخصصة أو الترحيب العام"
}}
لا تكتب أي نص آخر خارج الـ JSON.
"""
    try:
        response = safe_llm_invoke(prompt)
        
        start_idx = response.find("{")
        end_idx = response.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = response[start_idx:end_idx+1]
            data = json.loads(json_str)
            
            # ✨ التحقق الصارم من المخطط (Schema Validation)
            if not isinstance(data, dict) or "organizer_name" not in data or "custom_sentence" not in data:
                raise ValueError("JSON لا يطابق المخطط المطلوب.")
                
            org_name = str(data["organizer_name"]).strip()
            sentence = str(data["custom_sentence"]).strip()
            
            if not org_name or not sentence:
                raise ValueError("قيم JSON فارغة.")
                
            return org_name, sentence
        else:
            raise ValueError("لم يتم العثور على صيغة JSON صحيحة.")
            
    except Exception as e:
        print(f"⚠️ [تنبيه JSON]: {e}")
        return raw_lead_name, "يسعدنا جداً تواصلنا معكم للتعاون معاً."