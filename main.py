import os
import sys
import imaplib
import time
import random
import logging
import email
from email.message import EmailMessage
from dotenv import load_dotenv

# الاستيرادات الجديدة بعد التعديل الهيكلي
from sheet_manager import get_valid_leads, update_lead_status_by_email
# 🚀 استيراد DRY_RUN وقاموس الحقائق المركزي
from facts import clean_name, mask_email, DRY_RUN, COMPANY_FACTS 
from llm_utils import generate_custom_sentence
from email_template import EMAIL_TEMPLATE
from state_ledger import reserve_lead, mark_lead_completed

load_dotenv()

# إعداد نظام المراقبة والسجلات (Observability)
logging.basicConfig(
    filename='agent_run.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.hostinger.com")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
BATCH_SIZE = 50

# ==========================================
# 🛡️ طبقة الحماية الجديدة: IMAP Reconciliation
# ==========================================
def draft_exists_for_email(target_email: str) -> bool:
    """
    تدخل لمجلد المسودات (Drafts) وتبحث هل توجد مسودة مسبقة لهذا الإيميل؟
    تمنع تكرار المسودات للعملاء الذين انقطعت عنهم الكهرباء أثناء المعالجة.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(SENDER_EMAIL, SENDER_PASSWORD)
        mail.select('INBOX.Drafts', readonly=True)
        
        # البحث عن أي رسالة موجهة لهذا الإيميل في المسودات
        search_criteria = f'(TO "{target_email}")'
        status, messages = mail.search(None, search_criteria)
        
        mail.logout()
        
        if status == "OK" and messages[0]:
            return True # المسودة موجودة بالفعل
        return False
    except Exception as e:
        logging.error(f"IMAP Reconciliation failed for {target_email}: {e}")
        return False # في حالة خطأ الاتصال، نفترض عدم وجودها لنحاول مجدداً

def save_draft_to_imap(to_email, subject, body_html):
    """حفظ المسودة مع التأكد الحقيقي من استجابة خادم البريد"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
    mail.login(SENDER_EMAIL, SENDER_PASSWORD)
    
    msg = EmailMessage()
    msg.set_content("هذه الرسالة بصيغة HTML. يرجى تفعيل عرض HTML في بريدك.", subtype='plain')
    msg.add_alternative(body_html, subtype='html')
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    
    # التأكد من الحفظ الفعلي
    status, _ = mail.append('INBOX.Drafts', '\\Draft', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    mail.logout()
    
    if status != "OK":
        raise RuntimeError("❌ رفض خادم هوستنجر حفظ المسودة!")

def run_outbound_campaign():
    print(f"\n🚀 تشغيل نظام المبيعات الآلي (EVNTOWN Outbound Engine)...")
    if DRY_RUN:
        print("⚠️ [وضع التجربة DRY_RUN مفعل]: لن يتم حفظ مسودات أو تعديل الشيت.")

    # 1. جلب المنظمين
    try:
        leads = get_valid_leads()
    except Exception as e:
        print(f"❌ توقف طارئ: {e}")
        logging.error(f"Failed to fetch leads: {e}")
        return

    if not leads:
        print("💤 لا يوجد منظمون جدد بانتظار المراسلة.")
        return

    leads_to_process = leads[:BATCH_SIZE]
    print(f"🎯 سيتم معالجة الدفعة الحالية: {len(leads_to_process)} منظمين...\n")

    for lead in leads_to_process:
        raw_name = lead.get("الاسم", "")
        to_email = lead.get("الايميل", "")
        lead_status = str(lead.get("حالة الإرسال", "")).strip()
        
        clean_lead_name = clean_name(raw_name)
        print(f"----------------------------------------")
        print(f"👤 معالجة المنظم: {clean_lead_name} ({mask_email(to_email)})")
        
        # الفحص الفولاذي
        if not DRY_RUN and not reserve_lead(to_email):
            print(f"🛡️ تم تخطي المنظم ({mask_email(to_email)}) - موجود مسبقاً في الذاكرة الفولاذية لمنع التكرار.")
            continue 

        try:
            # ==========================================
            # 🛡️ تطبيق المصالحة (Reconciliation Check)
            # ==========================================
            # 🚀 التعديل الجوهري: إضافة الأقواس لحماية عملية الـ or من تجاوز DRY_RUN
            if not DRY_RUN and (lead_status == "قيد المعالجة" or draft_exists_for_email(to_email)):
                print(f"✅ [المصالحة]: تم العثور على مسودة سابقة للعميل {mask_email(to_email)}. جاري إنقاذه وتحديث الشيت فقط لتجنب التكرار.")
                update_lead_status_by_email(to_email, "مسودة جاهزة")
                mark_lead_completed(to_email, "DRAFTED")
                logging.info(f"RECONCILED: Draft already exists for {mask_email(to_email)}")
                continue # تخطي الخطوات القادمة والذهاب للعميل التالي

            # إذا لم تكن المسودة موجودة، نكمل الدورة الطبيعية
            if not DRY_RUN:
                update_lead_status_by_email(to_email, "قيد المعالجة")
            
            # 2. الاستدعاء الذكي مع تمرير سياق/تقييم المنظم لمنع الهلوسة
            lead_context = lead.get("التقييم", "") 
            print("✍️ جاري توليد الجملة الافتتاحية بناءً على السياق الموثق...")
            
            # استدعاء واحد فقط يحمل السياق
            org_name, custom_sent = generate_custom_sentence(clean_lead_name, lead_context)
            
            # 3. حقن القالب الثابت بالبيانات المستخرجة + الحقائق التسويقية المؤكدة
            raw_text = EMAIL_TEMPLATE.format(
                organizer_name=org_name, 
                custom_sentence=custom_sent, 
                **COMPANY_FACTS
            )
            
            # 4. القص الذكي وفصل العنوان عن النص
            if "---SEPARATOR---" in raw_text:
                subject, body = raw_text.split("---SEPARATOR---", 1)
            else:
                subject = f"دعوة خاصة لـ {org_name} 🚀"
                body = raw_text
                
            subject = subject.replace("Subject:", "").replace("الموضوع:", "").replace("**", "").strip()
            body = body.strip()
            
            # 5. الحفظ في المسودات والتأكيد النهائي
            if DRY_RUN:
                print(f"✅ [نجاح وهمي - تجربة] العنوان: {subject}")
                logging.info(f"DRY RUN SUCCESS: {mask_email(to_email)}")
            else:
                print("📥 جاري حفظ المسودة في هوستنجر...")
                save_draft_to_imap(to_email, subject, body)
                
                # تحديث الحالة النهائية
                update_lead_status_by_email(to_email, "مسودة جاهزة")
                mark_lead_completed(to_email, "DRAFTED") 
                print("✅ اكتملت المهمة بنجاح تام! (تم الدمج، وحفظ المسودة، وتحديث الشيت).")
                logging.info(f"SUCCESS: Draft saved for {mask_email(to_email)}")
            
            # حماية الإيميل من الحظر (استراحة طبيعية من 30 لـ 50 ثانية)
            sleep_time = random.randint(30, 50)
            print(f"⏳ استراحة {sleep_time} ثوانٍ للحماية...")
            time.sleep(sleep_time)

        except Exception as e:
            error_msg = f"❌ حدث خطأ مع {clean_lead_name}: {e}"
            print(error_msg)
            # تسجيل الخطأ في السجل المعماري
            logging.error(f"Failed processing lead {mask_email(to_email)}: {str(e)}")
            
            if not DRY_RUN:
                # تحديث حالة الخطأ
                update_lead_status_by_email(to_email, "يحتاج مراجعة")
            
            # 🛡️ فترة راحة إضافية عند الفشل لمنع حظر الـ API
            error_sleep = random.randint(25, 40)
            print(f"⚠️ راحة إجبارية {error_sleep} ثانية لتهدئة السيرفر بعد الخطأ...")
            time.sleep(error_sleep)

if __name__ == "__main__":
    run_outbound_campaign()