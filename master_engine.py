import os
from filelock import FileLock, Timeout
from facts import DRY_RUN
from state_ledger import release_stale_leads
from lead_hunter import run_super_hunter
from main import run_outbound_campaign

LOCK_FILE = "evntown_agent.lock"

# 🚀 الدالة الجديدة: إرسال إشعار لنظام الماك
def notify_mac(title, message, sound="Ping"):
    """يرسل إشعاراً لسطح مكتب الماك"""
    try:
        os.system(f"""osascript -e 'display notification "{message}" with title "{title}" sound name "{sound}"'""")
    except:
        pass

def master_run():
    print("===========================================")
    print("🤖 [EVNTOWN Master Engine]: بدء التشغيل...")
    if DRY_RUN:
        print("⚠️ [تنبيه]: وضع التجربة (DRY_RUN) مفعل بالكامل من الـ .env")

    # 1. القفل الذري (Atomic Lock) 
    lock = FileLock(LOCK_FILE, timeout=0)
    
    try:
        with lock:
            print("🔒 تم تأمين قفل التشغيل (Atomic Lock). لا يوجد تداخل.")
            
            # 2. المصالحة وتحرير الحالات العالقة
            release_stale_leads(max_hours_stale=1)
            
            # 3. تشغيل وحش الصيد 
            print("\n[المرحلة 1]: اكتشاف منظمين جدد...")
            run_super_hunter()
            
            # 4. تشغيل محرك المراسلة
            print("\n[المرحلة 2]: المراسلة وتجهيز المسودات...")
            run_outbound_campaign()
            
            print("\n✅ [المايسترو]: تمت دورة التشغيل بالكامل بنجاح وأمان.")
            
            # 🔔 إطلاق الإشعار بالنجاح!
            notify_mac(
                title="EVNTOWN Agent 🚀", 
                message="✅ تمت دورة الصيد والمراسلة بنجاح! راجع مجلد المسودات.",
                sound="Glass" # صوت إشعار مميز
            )
            
    except Timeout:
        print("🛑 [تنبيه طارئ]: هناك نسخة أخرى من الإيجنت تعمل حالياً!")
    except Exception as e:
        print(f"❌ [خطأ في النظام المركزي]: {e}")
        # 🔔 إطلاق إشعار في حالة حدوث كارثة
        notify_mac(
            title="EVNTOWN Agent - خطأ طارئ ⚠️", 
            message="حدث خطأ أدى لتوقف الإيجنت، راجع ملف agent_run.log",
            sound="Basso"
        )

if __name__ == "__main__":
    master_run()