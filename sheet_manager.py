import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
import sys

load_dotenv()

# منح صلاحية القراءة والكتابة الكاملة
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

class SheetsConnectionError(Exception):
    """خطأ مخصص يوقف النظام فوراً إذا فشل الاتصال بالشيت"""
    pass

def sanitize_for_sheets(text: str) -> str:
    """
    تنظيف النصوص القادمة من الإنترنت لمنع (Formula Injection)
    يمنع أي نص يبدأ بعلامات المعادلات في إكسيل وجوجل شيت.
    """
    if not text:
        return ""
    text = str(text).strip()
    if text.startswith(('=', '+', '-', '@')):
        text = "'" + text
    return text

def get_google_sheets_service():
    """تهيئة الاتصال بجوجل شيت بشكل آمن مع حماية بيئة الـ Cron (Headless Protection)"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise SheetsConnectionError(f"❌ فشل تجديد الجلسة تلقائياً: {e}. يرجى مسح token.json والتشغيل يدوياً.")
        else:
            # 🛡️ الحماية من التجمد في الخلفية (Zombie Process Protection)
            if not sys.stdout.isatty():
                raise SheetsConnectionError("❌ [أمان النظام]: المصادقة مفقودة والإيجنت يعمل في الخلفية (Cron). يرجى التشغيل يدوياً أولاً لتسجيل الدخول.")
                
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("❌ ملف credentials.json مفقود! لا يمكن الاتصال.")
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        raise SheetsConnectionError(f"❌ فشل بناء خدمة جوجل شيت: {e}")

def get_valid_leads():
    """يجلب المنظمين الذين حالتهم 'جديد' ولديهم إيميل"""
    service = get_google_sheets_service()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'"
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return []
            
        headers = values[0]
        data = values[1:]
        
        padded_data = [row + [""] * (len(headers) - len(row)) for row in data]
        df = pd.DataFrame(padded_data, columns=headers)
        
        valid_leads = []
        for index, row in df.iterrows():
            if str(row.get('حالة الإرسال', '')).strip() == 'جديد' and str(row.get('الايميل', '')).strip():
                lead_dict = row.to_dict()
                lead_dict['_row'] = index + 2
                valid_leads.append(lead_dict)
                
        return valid_leads
        
    except Exception as e:
        raise SheetsConnectionError(f"فشل جلب البيانات من الشيت: {e}")
    

# ==========================================
# 🚀 التعديل الجوهري: التحديث برقم الإيميل بدلاً من رقم الصف
# ==========================================
# ==========================================
# 🚀 التعديل الجوهري: التحديث برقم الإيميل بدلاً من رقم الصف (مع معالجة التكرار)
# ==========================================
def update_lead_status_by_email(email, status):
    """
    يبحث عن العميل باستخدام إيميله (معرف فريد) ويحدث حالته.
    - تم التعديل: يقوم بتحديث *جميع* الصفوف التي تحتوي على نفس الإيميل 
    لمنع بقاء أي نسخ مكررة في حالة 'جديد'.
    """
    service = get_google_sheets_service()
    
    try:
        # جلب الشيت بالكامل
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'"
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            raise Exception("الشيت فارغ.")
            
        headers = rows[0]
        if "الايميل" not in headers or "حالة الإرسال" not in headers:
            raise Exception("عمود 'الايميل' أو 'حالة الإرسال' غير موجود في الشيت.")
            
        email_idx = headers.index("الايميل")
        status_idx = headers.index("حالة الإرسال")
        
        # تحويل رقم عمود الحالة إلى حرف (A, B, C, D...)
        status_col_letter = chr(65 + status_idx) 
        
        updated_count = 0
        
        # البحث عن الإيميل في جميع الصفوف
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > email_idx and row[email_idx].strip().lower() == email.strip().lower():
                # وجدنا العميل! نحدث حالته
                range_name = f"'{SHEET_NAME}'!{status_col_letter}{i}"
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_name,
                    valueInputOption="RAW",
                    body={"values": [[status]]},
                ).execute()
                updated_count += 1
                
        if updated_count == 0:
            raise Exception(f"لم يتم العثور على الإيميل {email} في الشيت لتحديث حالته.")
        elif updated_count > 1:
            print(f"⚠️ [تنبيه أمان]: تم العثور على الإيميل ({email}) مكرراً {updated_count} مرات في الشيت. تم تحديثها جميعاً إلى '{status}' لمنع تكرار الإرسال.")
            
    except Exception as exc:
        raise SheetsConnectionError(f"❌ فشل تحديث حالة الإيميل {email} إلى '{status}'") from exc

def append_new_leads(new_leads_dicts):
    """
    استقبال المنظمين الجدد من الصياد وإضافتهم للشيت دفعة واحدة.
    FAIL-CLOSED: يرفع خطأ إذا فشل الحفظ لمنع فقدان البيانات.
    """
    if not new_leads_dicts:
        return
        
    service = get_google_sheets_service()
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!1:1"
        ).execute()
        
        headers = result.get('values', [[]])[0]
        if not headers:
            raise SheetsConnectionError("❌ لم أتمكن من قراءة أسماء الأعمدة من الشيت.")

        rows_to_append = []
        for lead in new_leads_dicts:
            row = []
            for header in headers:
                value = sanitize_for_sheets(lead.get(header, ""))
                row.append(value)
            rows_to_append.append(row)

        body = {'values': rows_to_append}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        print(f"✅ [الشيت]: تم إضافة {len(rows_to_append)} منظم جديد لغرفة الحجر الصحي (للمراجعة).")
        
    except Exception as e:
        # رفع الخطأ بقوة لمنع الكود من إكمال العمل وكأن شيئاً لم يكن
        raise SheetsConnectionError(f"❌ [الشيت]: فشل إضافة المنظمين الجدد: {e}")


def get_all_existing_data():
    """
    تسحب كل البيانات من الشيت وتستخرج الأسماء، الإيميلات، والنطاقات.
    FAIL-CLOSED: إذا فشل الاتصال، نوقف العملية تماماً لمنع التكرار.
    """
    print("⚡ [الكاش المركزي]: جاري سحب الذاكرة من شيت جوجل...")
    try:
        service = get_google_sheets_service() 
        range_name = f"'{SHEET_NAME}'" # قراءة الشيت بالكامل لضمان عدم تفويت أي عمود
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=range_name
        ).execute()
        
        rows = result.get('values', [])
        
        existing_names = set()
        existing_emails = set()
        existing_domains = set()
        
        public_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
        
        if rows:
            headers = rows[0]
            # تحديد أماكن الأعمدة ديناميكياً بدلاً من تخمينها
            name_idx = headers.index("الاسم") if "الاسم" in headers else -1
            email_idx = headers.index("الايميل") if "الايميل" in headers else -1
            
            for row in rows[1:]:
                name = str(row[name_idx]).strip().lower() if name_idx != -1 and len(row) > name_idx else ""
                email = str(row[email_idx]).strip().lower() if email_idx != -1 and len(row) > email_idx else ""
                
                if name: existing_names.add(name)
                if email: 
                    existing_emails.add(email)
                    if "@" in email:
                        domain = email.split("@")[1].strip()
                        if domain not in public_domains:
                            existing_domains.add(domain)
                            
        return existing_names, existing_emails, existing_domains
        
    except Exception as e:
        raise SheetsConnectionError(f"❌ فشل الاتصال بالشيت لبناء الكاش المركزي: {e}")