import re
import html
import os

# التحكم المركزي في وضع الحماية
DRY_RUN = os.getenv("DRY_RUN", "True").lower() in ('true', '1', 't')

# 1. قاموس الأرقام والحقائق (يُعدل من هنا فقط)
COMPANY_FACTS = {
    "commission_rate": "5%",
    "starter_boost_value_egp": "699",
    "launch_urgency": "الإطلاق الرسمي قريباً",
    "is_free_registration": "مجاني تماماً وبدون أي رسوم خفية"
}

def clean_name(raw: str) -> str:
    """تنظيف اسم المنظم لمنع أي أكواد خبيثة (HTML Injection)"""
    name = re.sub(r"\(.*?\)", "", raw or "")
    name = re.sub(r"[<>\"'=@]", "", name)
    return html.escape(re.sub(r"\s+", " ", name).strip()[:60])

def mask_email(email: str) -> str:
    """تشفير الإيميل لحماية الخصوصية (مثال: te***@gmail.com)"""
    if not email or "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    # نأخذ أول حرفين فقط من الاسم ونخفي الباقي
    masked_name = name[:2] + "***" if len(name) > 2 else name[:1] + "***"
    return f"{masked_name}@{domain}"