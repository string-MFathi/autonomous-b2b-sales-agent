import sqlite3
import os

DB_PATH = "evntown_state.db"

def init_db():
    """إنشاء قاعدة البيانات المحلية إذا لم تكن موجودة"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outbound_jobs (
                email TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

def reserve_lead(email: str) -> bool:
    """
    جدار الحماية الفولاذي: يحاول حجز الإيميل.
    - إذا كان الإيميل جديداً: يحجزه ويعيد True (اكمل العمل).
    - إذا كان موجوداً مسبقاً: يرفض الحجز ويعيد False (تخطى هذا العميل).
    """
    init_db()
    normalized_email = email.strip().lower()
    if not normalized_email:
        return False
        
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # تعليمة INSERT تمنع إدخال إيميل مكرر (ستطلق خطأ IntegrityError)
            conn.execute("""
                INSERT INTO outbound_jobs (email, status, updated_at)
                VALUES (?, 'PROCESSING', datetime('now', 'localtime'))
            """, (normalized_email,))
            return True # تم الحجز بنجاح
    except sqlite3.IntegrityError:
        # الإيميل موجود بالفعل في السجل!
        return False

def mark_lead_completed(email: str, status: str):
    """تأكيد حالة العميل بعد الانتهاء"""
    normalized_email = email.strip().lower()
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""
            UPDATE outbound_jobs 
            SET status = ?, updated_at = datetime('now', 'localtime')
            WHERE email = ?
        """, (status, normalized_email))

def release_stale_leads(max_hours_stale=1):
    """
    إدارة الحالة العالقة (Stale "In Progress" State):
    بدلاً من الحذف، نقوم بتحويل الحالة إلى 'NEEDS_RECONCILIATION'
    للمراجعة، تحسباً لأن المسودة قد تم حفظها بالفعل قبل الانقطاع.
    """
    init_db()
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.execute("""
                UPDATE outbound_jobs 
                SET status = 'NEEDS_RECONCILIATION', updated_at = datetime('now', 'localtime')
                WHERE status = 'PROCESSING' 
                AND datetime(updated_at) < datetime('now', 'localtime', '-' || ? || ' hours')
            """, (max_hours_stale,))
            
            reconciled_count = cursor.rowcount
            if reconciled_count > 0:
                print(f"⚠️ [الذاكرة المحلية]: تم تحويل {reconciled_count} عميل عالق إلى وضع 'NEEDS_RECONCILIATION' للمراجعة والمصالحة.")
    except Exception as e:
        print(f"❌ خطأ أثناء معالجة العملاء العالقين: {e}")