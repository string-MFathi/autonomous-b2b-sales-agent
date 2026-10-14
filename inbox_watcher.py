import os
import imaplib
import email
import time
import re
from email.message import EmailMessage
from email.header import decode_header
from email import policy
from dotenv import load_dotenv

# 🚀 التعديلات الجديدة: استيراد الأدوات الصحيحة بعد التحديث المعماري
from facts import COMPANY_FACTS, mask_email
from llm_utils import safe_llm_invoke

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.hostinger.com")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# 1. فلتر الحماية: كلمات تدل على أن المرسل "بوت" أو نظام آلي وليس إنساناً
SKIP_FROM = re.compile(r"(mailer-daemon|postmaster|no-?reply|donotreply|bounce)", re.I)

def decode_str(s):
    """فك تشفير عناوين الإيميلات العربية"""
    if not s: return ""
    decoded_list = decode_header(s)
    result = ""
    for content, encoding in decoded_list:
        if isinstance(content, bytes):
            result += content.decode(encoding or 'utf-8', errors='ignore')
        else:
            result += str(content)
    return result

def should_skip_email(msg, sender_email):
    """جدار حماية: هل نتجاهل هذه الرسالة؟"""
    # تجاهل إيميلات الرد الآلي والفشل
    if SKIP_FROM.search(sender_email):
        return True
    # تجاهل رسائل الإجازات (Out of office) والردود التلقائية
    if msg.get("Auto-Submitted", "no").lower() != "no":
        return True
    # تجاهل النشرات البريدية (Newsletters)
    if msg.get("Precedence", "").lower() in {"bulk", "junk", "list"}:
        return True
    return False

def check_inbox_and_draft_replies():
    print("📥 [Inbox Agent]: جاري فحص صندوق الوارد (بوضعية الخلسة PEEK)...")
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(SENDER_EMAIL, SENDER_PASSWORD)
        mail.select("INBOX")
        
        status, messages = mail.search(None, '(UNSEEN)')
        if status != 'OK':
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("💤 صندوق الوارد نظيف، لا توجد ردود جديدة.")
            mail.logout()
            return

        print(f"🔍 تم العثور على {len(email_ids)} رسائل غير مقروءة. جاري الفحص...")

        # 🚀 تجهيز الحقائق كنص مقروء للذكاء الاصطناعي ديناميكياً من القاموس
        facts_text = "\n".join([f"- {k}: {v}" for k, v in COMPANY_FACTS.items()])

        for e_id in email_ids:
            # 🚨 التعديل الجوهري P0: استخدام (BODY.PEEK) لكي تظل الرسالة "غير مقروءة" في الإيميل
            res, msg_data = mail.fetch(e_id, '(BODY.PEEK[])')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1], policy=policy.default)
                    subject = decode_str(msg["Subject"])
                    from_addr = decode_str(msg["From"])
                    match_email = email.utils.parseaddr(from_addr)[1]

                    # تطبيق جدار الحماية (هل هو إنسان أم بوت؟)
                    if should_skip_email(msg, match_email):
                        print(f"🚫 تم تجاهل رسالة آلية/مزعجة من: {mask_email(match_email)}")
                        continue

                    # استخراج نص الرسالة بطريقة آمنة
                    body = ""
                    part = msg.get_body(preferencelist=("plain", "html"))
                    if part:
                        body = part.get_content()
                        if part.get_content_type() == "text/html":
                            body = re.sub(r"<[^>]+>", " ", body) # تنظيف كود HTML

                    print(f"\n----------------------------------------")
                    print(f"📩 رسالة حقيقية من: {mask_email(match_email)}")
                    print(f"📌 الموضوع: {subject}")
                    
                    # صياغة الرد الذكي المعتمد على "وزارة الحقيقة" فقط
                    print("🤖 الذكاء الاصطناعي يقرأ ويصيغ الرد...")
                    prompt_text = f"""أنت مدير مبيعات EVNTOWN. 
أرسل لك هذا المنظم استفساراً: "{body[:1000]}"

تعليمات الرد الصارمة:
1. استخدم هذه الحقائق فقط للإجابة:
<حقائق>
{facts_text}
</حقائق>
2. إذا سأل عن شيء غير موجود في الحقائق، أخبره أنك ستحول استفساره للفريق التقني وسيتم التواصل معه.
3. لا تخترع أي أرقام، أسعار، أو وعود من عندك.
4. اجعل الرد دافئاً واحترافياً.
"""
                    # 🚀 استخدام الدالة الآمنة (التي تعيد المحاولة عند الفشل)
                    reply_body = safe_llm_invoke(prompt_text)

                    # حفظ المسودة
                    reply_msg = EmailMessage()
                    reply_msg.set_content(reply_body, subtype='html')
                    reply_msg["Subject"] = f"Re: {subject}"
                    reply_msg["From"] = SENDER_EMAIL
                    reply_msg["To"] = match_email

                    status, _ = mail.append('INBOX.Drafts', '\\Draft', imaplib.Time2Internaldate(time.time()), reply_msg.as_bytes())
                    if status == "OK":
                        print(f"✅ تم صياغة الرد وحفظه بنجاح كمسودة للمنظم {mask_email(match_email)}!")
                        
        mail.logout()
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء فحص صندوق الوارد: {e}")

if __name__ == "__main__":
    check_inbox_and_draft_replies()