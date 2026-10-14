import os
import re
import json
import sqlite3
import random
import requests
from dotenv import load_dotenv
from tavily import TavilyClient
from facts import clean_name
from llm_utils import safe_llm_invoke
from sheet_manager import append_new_leads, get_all_existing_data
from facts import DRY_RUN

load_dotenv()

TAVILY_KEY = os.getenv("TAVILY_API_KEY")
DB_PATH = "hunter_memory.db"

# ==========================================
# 1. ترسانة الكلمات المفتاحية (EVNTOWN Master Taxonomy)
# ==========================================
EVNTOWN_KEYWORDS = [
    # 🔴 مصطلحات التشغيل والبوابات الشاملة
    ("Sold Out", "القاعة كاملة العدد"), ("Early Bird", "التذاكر المبكرة"),
    ("No-Show Rate", "نسبة الغياب"), ("Guest List", "قائمة الضيوف"),
    ("Door Selection", "الفلترة على الباب"), ("Check-in", "تسكين الحضور"),
    ("Overbooking", "الحجز المزدوج"), ("Run of Show", "جدول الإيفنت"),
    ("Sound Check", "تجربة الصوت"), ("Venue", "مقر الإيفنت"),
    ("Capacity", "السعة الاستيعابية"), ("Gate Management", "إدارة البوابات"),
    ("Lineup", "جدول الفنانين"), ("Event Pass", "تصريح الدخول"),
    ("Official Sponsor", "الراعي الرسمي"), ("Media Partnership", "الشريك الإعلامي"),
    ("Pitch Deck", "العرض التقديمي للإيفنت"), ("Stage Manager", "مدير المسرح"),
    ("Ushering", "فريق الاستقبال"), ("Offline Scanner", "الماسح بدون إنترنت"),
    ("Organizer Dashboard", "لوحة تحكم المنظم"), ("Venue Deposit", "عربون القاعة"),
    ("Security Clearance", "التصاريح الأمنية"), ("Promotional Package", "باقة الترويج"),
    ("Logistics Setup", "التجهيزات اللوجستية"),
    
    # 🎵 1. قطاع الترفيه والموسيقى
    ("Live Concert", "حفلة لايف"), ("Stand-up Comedy", "ستاند أب كوميدي"),
    ("Warm-up DJ", "دي جي الافتتاحية"), ("Backstage Pass", "كواليس المسرح"),
    ("Acoustic Night", "سهرة أكوستيك"), ("Jam Session", "ارتجال موسيقي"),
    
    # 🎨 2. قطاع الفن والثقافة
    ("Open Mic", "المايك المفتوح"), ("Zar Folklore", "سهرة طرب"),
    ("Art Exhibition", "معرض فني"), ("Silent Reading Club", "نادي القراءة الصامتة"),
    ("Dramatic Arts", "ورشة دراما مسرحية"), ("Book Signing", "حفل توقيع كتاب"),
    
    # 🎓 3. قطاع التعليم والتدريب
    ("Workshop", "ورشة عمل"), ("Masterclass", "محاضرة احترافية"),
    ("Bootcamp", "معسكر تدريبي"), ("Certificate of Attendance", "شهادات الحضور"),
    ("Hands-on Experience", "التطبيق العملي"), ("Instructor", "المحاضر"),
    
    # 🧘‍♀️ 4. قطاع الصحة واللياقة
    ("Yoga Retreat", "جلسات يوجا"), ("Marathon", "سباق جري ماراثون"),
    ("Sound Healing", "الاستشفاء بالصوت"), ("Fitness Challenge", "تحدي اللياقة"),
    ("Wellness Camp", "كامب النقاهة"), ("Endurance Race", "سباقات التحمل"),
    
    # 🍔 5. قطاع الطعام ونمط الحياة
    ("Food Tasting", "تذوق المأكولات"), ("Fashion Bazaar", "بازار وسوق الموضة"),
    ("Pop-up Market", "سوق مؤقت"), ("Yard Sale", "جراج سيل"),
    ("Catering Setup", "بوفيه الفعالية"), ("Fashion Show", "عرض أزياء"),
    
    # 🏕️ 6. قطاع السفر والمغامرات
    ("Desert Camp", "كامب وتخييم"), ("Safari Trip", "رحلة سفاري"),
    ("Hiking", "مسار مشي جبلي"), ("Stargazing", "رصد النجوم"),
    ("Cycling Ride", "رايد عجل جماعي"), ("Gathering Point", "نقطة التجمع"),
    
    # 🎮 7. قطاع الألعاب والتكنولوجيا
    ("Hackathon", "هاكاثون برمجية"), ("Esports Tournament", "بطولة ألعاب إلكترونية"),
    ("Tech Summit", "قمة تكنولوجية"), ("VR Arcade Night", "ليلة الواقع الافتراضي"),
    ("Creative Coding", "البرمجة الإبداعية"), ("LAN Party", "شبكة ألعاب محلية"),
    
    # 🤝 8. قطاع بناء العلاقات والمجتمعات
    ("Networking Event", "ملتقى تعارف مهني"), ("Speed Networking", "تعارف سريع"),
    ("Co-working Community", "مجتمع مساحات العمل"), ("Founder Talk", "لقاء المؤسسين"),
    ("Community Vibe", "الأجواء المجتمعية"), ("Meetup", "تجمع دوري"),
    
    # 👨‍👩‍👧‍👦 9. قطاع العائلة والأطفال
    ("Kids Camp", "معسكر أطفال صيفي"), ("Family Day", "يوم عائلي"),
    ("Puppet Show", "مسرح العرائس"), ("Art & Craft for Kids", "ورش أعمال يدوية للأطفال"),
    ("School Break Event", "فعاليات الإجازات"), ("Circus Show", "عروض السيرك"),
    
    # 🤝 10. قطاع العمل الخيري
    ("Charity Event", "فعالية خيرية"), ("Fundraising Concert", "حفل جمع تبرعات"),
    ("Sufi Chanting", "سهرة إنشاد وصوفية"), ("Volunteer Recruitment", "يوم المتطوعين"),
    ("Charity Market", "معرض خيري"), ("Community Service", "خدمة مجتمعية"),
    
    # 🟢 المصطلحات المالية والإستراتيجية
    ("Event Organizer", "منظم فعاليات"), ("Event Planner", "مخطط فعاليات"),
    ("CAC", "تكلفة الاستحواذ على العميل"), ("Conversion Rate", "معدل إتمام الشراء"),
    ("B2B Dashboard", "لوحة تحكم المنظمين"), ("Payout Settlement", "تسوية المستحقات"),
    ("Dynamic QR Code", "كود التذكرة المشفر"), ("Early Access", "الدخول المسبق"),
    ("MoSCoW Prioritization", "ترتيب أولويات الفعالية"), ("Merchant of Record", "وكيل التحصيل المالي"),
    ("SLA Contract", "عقد اتفاقية الخدمة"), ("Event ROI", "العائد على الاستثمار للفعالية"),
    ("Sold Out Soon", "التذاكر توشك على النفاد"), ("Event Strategy Guide", "دليل استراتيجية الفعالية")
]

PLATFORMS = [
    "site:instagram.com", 
    "site:linkedin.com/in", 
    "site:linkedin.com/company", 
    "site:facebook.com", 
    "" 
]

LOCATIONS = ["Egypt", "Cairo", "Alexandria", "مصر", "القاهرة"]

# 🚀 [التعديل 1]: فلاتر التأطير الزمني واستهداف المنافسين (Predatory Dorking)
YEARS_FILTER = '("2026" OR "2027")'
COMPETITORS_FILTER = '("TicketsMarche" OR "Paymob" OR "TicketEgypt" OR "Collard Tickets" OR "Tazkarti")'

def generate_dynamic_queries(num_queries=8):
    """يولد استعلامات بحث عشوائية متوحشة ومحصورة زمنياً"""
    queries = []
    for _ in range(num_queries):
        en_term, ar_term = random.choice(EVNTOWN_KEYWORDS)
        platform = random.choice(PLATFORMS)
        location = random.choice(LOCATIONS)
        
        # 🎲 تنويع الهجوم: 50% استعلامات تستهدف عملاء المنافسين، و50% استعلامات زمنية عامة
        is_predatory = random.choice([True, False])
        
        if is_predatory:
            dork = f'{platform} ("{en_term}" OR "{ar_term}") {YEARS_FILTER} {COMPETITORS_FILTER} "{location}" email'
        else:
            dork = f'{platform} ("{en_term}" OR "{ar_term}") {YEARS_FILTER} "{location}" email'
            
        # تنظيف المسافات الزائدة
        dork = re.sub(r'\s+', ' ', dork).strip()
        queries.append(dork)
    return queries

# ==========================================
# 2. الذاكرة، الاستخراج، والتقييم
# ==========================================
def init_hunter_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS seen_leads (url TEXT PRIMARY KEY, email TEXT)")

def is_seen(url, email=""):
    with sqlite3.connect(DB_PATH) as conn:
        if url and conn.execute("SELECT 1 FROM seen_leads WHERE url=?", (url,)).fetchone():
            return True
        if email and conn.execute("SELECT 1 FROM seen_leads WHERE email=?", (email,)).fetchone():
            return True
    return False

def mark_seen(url, email=""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO seen_leads (url, email) VALUES (?, ?)", (url, email))

def extract_emails(text):
    if not text: return []
    matches = re.findall(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", text)
    return list(set([m.lower() for m in matches if "wixpress" not in m and "sentry" not in m]))

def resolve_linktree(url):
    try:
        r = requests.get(url, timeout=5)
        return extract_emails(r.text)
    except:
        return []

def prefilter_score(text):
    t = str(text).lower()
    good = ["تنظيم", "فعاليات", "مؤتمرات", "حفلات", "معارض", "planner", "organizer", "agency", "management"]
    bad = ["حضرت", "ابحث عن", "عايز تذكرة", "attended", "looking for tickets", "سأحضر"]
    return sum(1 for w in good if w in t) - sum(2 for w in bad if w in t)

# 🚀 [التعديل 2]: حقن مؤشرات الاستمرارية في عقل الذكاء الاصطناعي
def qualify_with_ai(name, text):
    prompt = f"""أنت خبير في تقييم منظمي الفعاليات (B2B) في مصر، مهمتك كشف المنظمين النشطين والمحترفين.
اقرأ هذه البيانات:
الاسم: {name}
الوصف: {text}

تعليمات التقييم الصارمة:
1. ابحث عن "مؤشرات الاستمرارية" (مثل: الموسم الثاني، النسخة، Vol، السنوي، مستمر، عودة، 2026، 2027). إذا وجدتها، ارفع نسبة الثقة (confidence) فوق 85%.
2. ابحث عن أي تعاون مع بوابات تذاكر أو رعاية. هذا صيد ثمين، ارفع الثقة.
3. تأكد أنه "ينظم" الفعالية وليس مجرد "حاضر" أو "مشارك".

أخرج النتيجة في صيغة JSON فقط:
{{"is_organizer": true, "type": "agency او freelancer", "confidence": 90, "evidence": "جملة قصيرة كدليل يثبت نشاطه واستمراريته"}}"""
    try:
        res = safe_llm_invoke(prompt)
        start, end = res.find('{'), res.rfind('}') + 1
        return json.loads(res[start:end])
    except:
        return None

# ==========================================
# 3. المايسترو الخاص بالصياد
# ==========================================
def run_super_hunter():
    print("===========================================")
    print("🕸️ [وحش الصيد]: استيقظ وبدأ بمسح السوشيال ميديا (Tavily)...")
    if not TAVILY_KEY:
        print("❌ [الوحش]: مفتاح Tavily مفقود!")
        return False
        
    tavily = TavilyClient(api_key=TAVILY_KEY)
    init_hunter_db()
    
    # --- بناء الكاش المركزي (الذاكرة) مرة واحدة قبل البحث ---
    existing_names, existing_emails, existing_domains = get_all_existing_data()
    print(f"✅ تم تحميل ذاكرة الشيت: ({len(existing_emails)} إيميل، {len(existing_domains)} شركة)")
    # --------------------------------------------------------

    # قائمة النطاقات العامة لفلتر الدومين
    public_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}

    queries = generate_dynamic_queries(num_queries=8)
    discovered_leads = []
    seen_emails_this_run = set() # ✨ فلتر تفادي التكرار في نفس الجلسة
    
    for q in queries:
        if len(discovered_leads) >= 25:
            print(f"🛑 [الوحش]: وصلت للحد الأقصى المطلوب (25 منظم). سأتوقف للتوفير.")
            break
            
        print(f"\n📡 إطلاق رادار البحث عن: [{q}]")
        try:
            res = tavily.search(query=q, search_depth="advanced", max_results=15)
            
            for r in res.get("results", []):
                if len(discovered_leads) >= 25: break
                
                url, content, title = r.get("url", ""), r.get("content", ""), r.get("title", "")
                
                if is_seen(url): continue
                if prefilter_score(content) < 1:
                    mark_seen(url)
                    continue
                    
                emails = extract_emails(content)
                if not emails and ("linktr.ee" in url or "bio.link" in url):
                    emails = resolve_linktree(url)
                    
                if not emails:
                    mark_seen(url)
                    continue
                    
                email = emails[0].strip().lower()

                # ✨ الفلتر الجديد: هل رأينا هذا الإيميل في الدورة الحالية؟
                if email in seen_emails_this_run:
                    continue
                seen_emails_this_run.add(email)

                safe_name = clean_name(title[:50]).strip().lower()

                if is_seen(url="", email=email): continue

                # --- الفلترة المبكرة الصارمة ---
                if safe_name in existing_names:
                    print(f"🚫 [فلتر مبكر]: تخطي '{safe_name}' (الاسم موجود بالشيت).")
                    mark_seen(url, email)
                    continue

                if email in existing_emails:
                    print(f"🚫 [فلتر مبكر]: تخطي '{safe_name}' (الإيميل موجود بالشيت).")
                    mark_seen(url, email)
                    continue
                
                if "@" in email:
                    domain = email.split("@")[1].strip()
                    if domain not in public_domains and domain in existing_domains:
                        print(f"🚫 [فلتر مبكر]: تخطي '{safe_name}' (نطاق {domain} موجود بالشيت).")
                        mark_seen(url, email)
                        continue
                # ---------------------------------
                    
                print(f"🔍 تقييم ذكي لمرشح: {title[:40]}...")
                ai_decision = qualify_with_ai(title, content)
                
                if ai_decision and ai_decision.get("is_organizer") and ai_decision.get("confidence", 0) > 70:
                    final_name = clean_name(title[:50])
                    print(f"🎯 صيد ثمين رقم ({len(discovered_leads)+1})! ({email})")
                    
                    discovered_leads.append({
                        "الاسم": final_name,
                        "الايميل": email,
                        "حالة الإرسال": "للمراجعة",
                        "التقييم": f"{ai_decision.get('type')} | يقين: {ai_decision.get('confidence')}%",
                        "اللينك": url
                    })
                    # ⚠️ التعديل الجوهري: تم إزالة mark_seen(url, email) من هنا تماماً لحمايته حتى يتم الحفظ!
                else:
                    # تسجيل النتائج غير المؤهلة لعدم الرجوع إليها
                    mark_seen(url, email)
                    
        except Exception as e:
            print(f"⚠️ خطأ أثناء البحث في ({q}): {e}")
            
    # --- الخاتمة: إضافة المنظمين الجدد للشيت بضمان الحفظ ---
    if discovered_leads:
        if DRY_RUN:
            print("⚠️ [DRY_RUN]: تم إيقاف إضافة الصيود للشيت والذاكرة (وضع التجربة).")
            return True # ✨ تعديل: يجب إرجاع قيمة للـ Master Engine
        
        print(f"\n🎉 [الوحش]: تم العثور على {len(discovered_leads)} منظم مؤهل. جاري الحفظ...")
        try:
            # 1. نحاول الحفظ في الشيت أولاً
            append_new_leads(discovered_leads)
            
            # 2. إذا نجح الحفظ (لم يضرب Exception)، نقوم بتسجيلهم في الذاكرة المحلية
            for lead in discovered_leads:
                mark_seen(lead.get("اللينك", ""), lead.get("الايميل", ""))
                
            print("✅ تم تسجيل المنظمين الجدد في الشيت وفي ذاكرة الوحش بنجاح.")
            return True
        except Exception as e:
            # إذا فشل الحفظ، لن يتم تسجيلهم بالذاكرة وسنصطادهم غداً!
            print(f"❌ الكارثة تم تجنبها: فشل الحفظ في الشيت، لذلك لم نضعهم في الذاكرة لتجنب ضياعهم. ({e})")
            return False
    else:
        print("\n💤 [الوحش]: لم أجد صيوداً جديدة مؤهلة اليوم.")
        return False

if __name__ == "__main__":
    run_super_hunter()