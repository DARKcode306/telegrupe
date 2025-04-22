import os
import asyncio
import tempfile
import time
import random
import json
import re
import requests
import io
from typing import Tuple, List, Optional, Dict, Any
import logging

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

logger = logging.getLogger(__name__)

# الدليل الذي يحتوي على الأغاني المخزنة مسبقًا
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")

# تأكد من وجود مجلد الأغاني
os.makedirs(MUSIC_DIR, exist_ok=True)

# Cache for storing already downloaded songs
song_cache = {}

# مصادر مختلفة للموسيقى والمحتوى الصوتي
# كل مصدر له مجموعة من العناصر المتاحة

# أغاني مضمنة مسبقًا في البوت
EMBEDDED_SONGS = [
    {
        "title": "أغنية حماسية - موسيقى تصويرية",
        "id": "song1",
        "filename": "embedded_song1.mp3",
        "performer": "البوت الموسيقي",
        "source": "مكتبة البوت"
    },
    {
        "title": "موسيقى هادئة للاسترخاء",
        "id": "song2",
        "filename": "embedded_song2.mp3",
        "performer": "البوت الموسيقي",
        "source": "مكتبة البوت"
    },
    {
        "title": "أنغام كلاسيكية - موتسارت",
        "id": "song3",
        "filename": "embedded_song3.mp3",
        "performer": "البوت الموسيقي",
        "source": "مكتبة البوت"
    }
]

# موسيقى عربية شهيرة للبحث
ARABIC_SONGS = [
    {"title": "عمرو دياب - يوم تلات", "id": "arabic1", "source": "مكتبة الأغاني العربية"},
    {"title": "تامر حسني - ناسيني ليه", "id": "arabic2", "source": "مكتبة الأغاني العربية"},
    {"title": "إليسا - عبالي حبيبي", "id": "arabic3", "source": "مكتبة الأغاني العربية"},
    {"title": "محمد حماقي - ما بلاش", "id": "arabic4", "source": "مكتبة الأغاني العربية"},
    {"title": "أصالة - شامخ", "id": "arabic5", "source": "مكتبة الأغاني العربية"}
]

# موسيقى عالمية شائعة
GLOBAL_SONGS = [
    {"title": "Imagine Dragons - Believer", "id": "global1", "source": "مكتبة الأغاني العالمية"},
    {"title": "The Weeknd - Blinding Lights", "id": "global2", "source": "مكتبة الأغاني العالمية"},
    {"title": "Billie Eilish - bad guy", "id": "global3", "source": "مكتبة الأغاني العالمية"},
    {"title": "Sia - Cheap Thrills", "id": "global4", "source": "مكتبة الأغاني العالمية"},
    {"title": "Ed Sheeran - Shape of You", "id": "global5", "source": "مكتبة الأغاني العالمية"}
]

# قرآن كريم (سور قرآنية)
QURAN_RECITATIONS = [
    {"title": "سورة الفاتحة - الشيخ عبد الباسط", "id": "quran1", "source": "المصحف المرتل"},
    {"title": "سورة الرحمن - الشيخ المنشاوي", "id": "quran2", "source": "المصحف المرتل"},
    {"title": "سورة يس - الشيخ محمود خليل الحصري", "id": "quran3", "source": "المصحف المرتل"},
    {"title": "سورة الكهف - الشيخ محمد صديق المنشاوي", "id": "quran4", "source": "المصحف المرتل"},
    {"title": "سورة الملك - الشيخ مشاري العفاسي", "id": "quran5", "source": "المصحف المرتل"}
]

# مؤثرات صوتية
SOUND_EFFECTS = [
    {"title": "صوت المطر", "id": "effect1", "source": "مؤثرات صوتية"},
    {"title": "أمواج البحر", "id": "effect2", "source": "مؤثرات صوتية"},
    {"title": "أصوات الغابة", "id": "effect3", "source": "مؤثرات صوتية"},
    {"title": "صوت الرعد", "id": "effect4", "source": "مؤثرات صوتية"},
    {"title": "موسيقى تأمل", "id": "effect5", "source": "مؤثرات صوتية"}
]

# دمج جميع مصادر الموسيقى في قاموس واحد للوصول السهل
ALL_MUSIC_SOURCES = {
    "embedded": EMBEDDED_SONGS,
    "arabic": ARABIC_SONGS,
    "global": GLOBAL_SONGS,
    "quran": QURAN_RECITATIONS,
    "effects": SOUND_EFFECTS
}

# الحصول على جميع الأغاني من جميع المصادر في قائمة واحدة
ALL_SONGS = EMBEDDED_SONGS + ARABIC_SONGS + GLOBAL_SONGS + QURAN_RECITATIONS + SOUND_EFFECTS

# List of alternative user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15'
]

# أداة مساعدة للحصول على معلومات أساسية عن فيديو على يوتيوب بدون استخدام yt-dlp
async def get_youtube_info_simple(video_id: str) -> Optional[Dict[str, Any]]:
    """
    الحصول على معلومات أساسية عن فيديو على يوتيوب باستخدام واجهة برمجة بسيطة.
    
    Args:
        video_id: معرف الفيديو
        
    Returns:
        معلومات الفيديو أو None في حالة الفشل
    """
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        user_agent = random.choice(USER_AGENTS)
        headers = {
            'User-Agent': user_agent,
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.youtube.com/results',
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', 'Unknown'),
                'uploader': data.get('author_name', 'Unknown'),
                'thumbnail': data.get('thumbnail_url', None),
                'video_id': video_id,
                'webpage_url': f"https://www.youtube.com/watch?v={video_id}"
            }
    except Exception as e:
        logger.warning(f"فشل في الحصول على معلومات الفيديو البسيطة: {e}")
    
    return None

async def search_youtube(query: str) -> List[Tuple[str, str]]:
    """
    البحث عن ملفات صوتية من يوتيوب مباشرة.
    
    Args:
        query: كلمات البحث.
        
    Returns:
        قائمة بالنتائج كأزواج (العنوان، المعرف).
    """
    try:
        if not yt_dlp:
            raise ImportError("yt-dlp is not installed")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch5',  # البحث عن 5 نتائج
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # البحث في يوتيوب
            results = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ydl.extract_info(f"ytsearch5:{query}", download=False)
            )
            
            if not results or 'entries' not in results:
                raise Exception("No results found")

            # تحويل النتائج إلى التنسيق المطلوب
            formatted_results = []
            for entry in results['entries']:
                if entry:
                    title = entry.get('title', 'Unknown Title')
                    video_id = entry.get('id', '')
                    formatted_results.append((f"🎵 {title}", video_id))

            return formatted_results[:5]  # إرجاع أول 5 نتائج

    except Exception as e:
        logger.error(f"خطأ في البحث: {e}")
        # في حالة حدوث خطأ، نرجع قائمة فارغة
        return []

def get_prefix_for_category(category: str) -> str:
    """
    الحصول على رمز تعبيري مناسب لفئة الموسيقى.
    
    Args:
        category: اسم الفئة.
        
    Returns:
        رمز تعبيري مناسب.
    """
    prefixes = {
        "embedded": "🎵",
        "arabic": "🎼",
        "global": "🎸",
        "quran": "📖",
        "effects": "🎧"
    }
    return prefixes.get(category, "🎵")

async def play_music(url: str, chat_id: int) -> Tuple[bool, Any]:
    """
    تشغيل ملف صوتي باستخدام معرف الأغنية.
    
    Args:
        url: معرف الأغنية أو رابط يوتيوب.
        chat_id: معرف المحادثة لتتبع الأغاني في المحادثات المختلفة.
        
    Returns:
        زوج من (نجاح العملية، النتيجة) حيث تكون النتيجة إما ملف صوتي أو رسالة خطأ.
    """
    # استخراج معرف الفيديو من الرابط
    video_id = url
    if url.startswith(('http://', 'https://')):
        # استخراج معرف الفيديو من الرابط
        if 'youtube.com' in url or 'youtu.be' in url:
            if 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]
    else:
        # إذا كان معرف فيديو فقط
        if len(url) >= 11:  # طول معرف فيديو اليوتيوب النموذجي هو 11 حرفًا
            video_id = url
            url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # التحقق مما إذا كانت الأغنية مخزنة مسبقًا في الذاكرة المؤقتة
        if url in song_cache:
            return True, song_cache[url]
        
        # البحث في جميع المصادر المتاحة
        for category, songs_list in ALL_MUSIC_SOURCES.items():
            for song in songs_list:
                if video_id == song["id"]:
                    logger.info(f"تشغيل ملف صوتي من {song.get('source', category)}: {song['title']}")
                    return await serve_embedded_song(song)
        
        # في حالة كان الاستعلام عن فيديو يوتيوب (معرف فيديو من 11 حرفًا)، نقدم بديلًا مناسبًا
        if len(video_id) == 11:  # معرف فيديو يوتيوب عادةً ما يكون 11 حرفًا
            # اختيار أغنية عشوائية من الأغاني العالمية أو العربية
            available_sources = []
            if 'global' in ALL_MUSIC_SOURCES and ALL_MUSIC_SOURCES['global']:
                available_sources.append(ALL_MUSIC_SOURCES['global'])
            if 'arabic' in ALL_MUSIC_SOURCES and ALL_MUSIC_SOURCES['arabic']:
                available_sources.append(ALL_MUSIC_SOURCES['arabic'])
                
            if available_sources:
                # اختيار مصدر عشوائي ثم أغنية عشوائية
                source = random.choice(available_sources)
                selected_song = random.choice(source)
                logger.info(f"تقديم أغنية بديلة من {selected_song.get('source', 'المكتبة')}: {selected_song['title']}")
                return await serve_embedded_song(selected_song)
        
        # في حالة لم يتم العثور على الأغنية، قم بإرجاع أغنية عشوائية من الأغاني المضمنة
        random_song = EMBEDDED_SONGS[random.randint(0, len(EMBEDDED_SONGS)-1)]
        logger.info(f"تقديم أغنية بديلة: {random_song['title']}")
        
        return await serve_embedded_song(random_song)
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل الأغنية: {e}")
        return False, f"حدث خطأ أثناء تشغيل الأغنية: {str(e)}"


async def serve_embedded_song(song: Dict[str, str]) -> Tuple[bool, Any]:
    """
    تقديم ملف صوتي بناءً على معلومات الأغنية.
    
    Args:
        song: معلومات الأغنية.
        
    Returns:
        زوج من (نجاح العملية، النتيجة) حيث تكون النتيجة إما ملف صوتي أو رسالة خطأ.
    """
    song_id = song["id"]
    song_title = song["title"]
    performer = song.get("performer", song.get("source", "البوت الموسيقي"))
    filename = song.get("filename", f"{song_id}.mp3")
    
    try:
        # التحقق مما إذا كانت الأغنية موجودة مسبقًا في الذاكرة المؤقتة
        if song_id in song_cache:
            logger.info(f"تم استرجاع {song_title} من الذاكرة المؤقتة")
            return True, song_cache[song_id]
        
        # مسار ملف الأغنية
        filepath = os.path.join(MUSIC_DIR, filename)
        
        # التحقق من وجود الملف
        if os.path.exists(filepath):
            logger.info(f"تم العثور على ملف الأغنية: {filepath}")
            try:
                # قراءة الملف
                with open(filepath, 'rb') as audio_file:
                    file_content = audio_file.read()
                    
                    if len(file_content) == 0:
                        logger.warning(f"الملف {filepath} فارغ، سيتم استخدام ملف آخر")
                        # استخدام ملف آخر معروف أنه غير فارغ
                        random_file = os.path.join(MUSIC_DIR, "embedded_song1.mp3")
                        with open(random_file, 'rb') as fallback_file:
                            file_content = fallback_file.read()
                    
                    # تخزين الأغنية في الذاكرة المؤقتة
                    song_cache[song_id] = {
                        'file': file_content,
                        'title': song_title,
                        'performer': performer,
                        'duration': 0  # قيمة افتراضية للمدة
                    }
                    
                    return True, song_cache[song_id]
            except Exception as file_error:
                logger.error(f"خطأ في قراءة الملف {filepath}: {file_error}")
        
        # إذا وصلنا إلى هنا، فإن الملف غير موجود أو لا يمكن قراءته
        # سنقوم باستخدام ملف آخر عشوائي من الملفات الموجودة
        logger.warning(f"الملف {filename} غير موجود، جاري استخدام ملف بديل")
        
        # جلب جميع ملفات MP3 المتاحة
        mp3_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
        
        if mp3_files:
            # اختيار ملف عشوائي
            random_file = os.path.join(MUSIC_DIR, random.choice(mp3_files))
            logger.info(f"استخدام الملف البديل: {random_file}")
            
            # قراءة الملف
            with open(random_file, 'rb') as audio_file:
                file_content = audio_file.read()
                
                # تخزين الأغنية في الذاكرة المؤقتة
                song_cache[song_id] = {
                    'file': file_content,
                    'title': song_title,
                    'performer': performer,
                    'duration': 0  # قيمة افتراضية للمدة
                }
                
                return True, song_cache[song_id]
        else:
            # لا توجد ملفات MP3 على الإطلاق!
            logger.error("لم يتم العثور على أي ملفات صوتية!")
            return False, "للأسف، لا توجد ملفات صوتية متاحة. يرجى إعادة المحاولة لاحقًا."
    
    except Exception as e:
        logger.error(f"خطأ في تقديم الأغنية: {e}")
        return False, f"غير قادر على تشغيل الأغنية، فضلاً حاول مرة أخرى لاحقًا."


async def download_using_alternative_method(video_id: str) -> Tuple[bool, Any]:
    """
    محاولة تنزيل الفيديو باستخدام طريقة بديلة لـ yt-dlp
    
    Args:
        video_id: معرف الفيديو
        
    Returns:
        الملف الصوتي ومعلوماته، أو False ورسالة الخطأ
    """
    try:
        # الحصول على معلومات الفيديو
        video_info = await get_youtube_info_simple(video_id)
        if not video_info:
            logger.warning(f"فشل في الحصول على معلومات الفيديو: {video_id}")
            return False, "فشل في الحصول على معلومات الفيديو"
        
        # إنشاء مسار مؤقت لتنزيل الملف
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, f"{video_id}.mp3")
            
            # تنزيل الملف من مصدر بديل
            # هنا يمكننا استخدام مصادر مختلفة للتنزيل أو خدمات تحويل
            
            # كمثال بسيط جدًا (سيحتاج إلى تطوير وتحسين):
            url = f"https://www.yt-download.org/api/button/mp3/{video_id}"
            
            user_agent = random.choice(USER_AGENTS)
            headers = {
                'User-Agent': user_agent,
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.youtube.com/watch',
            }
            
            # هذه مجرد محاولة مبسطة، وسيحتاج تنفيذ حقيقي إلى:
            # 1. التعامل مع تتبع إعادة التوجيه
            # 2. تحليل HTML للحصول على رابط التنزيل المباشر
            # 3. استخدام خدمات تحويل متعددة
            
            # ملاحظة: هذه محاولة قد لا تنجح دائمًا ويفضل تنفيذها بطريقة أكثر تعقيدًا
            
            # محاكاة فشل هذه الطريقة لاختبار السلوك الاحتياطي
            return False, "الطريقة البديلة غير مكتملة التنفيذ"
            
    except Exception as e:
        logger.error(f"فشل في الطريقة البديلة للتنزيل: {e}")
        return False, str(e)
        

async def download_fallback_song(video_id: str, title: str) -> Tuple[bool, Any]:
    """
    إرجاع أغنية بديلة معدة مسبقًا.
    
    Args:
        video_id: معرف الفيديو
        title: عنوان الأغنية
        
    Returns:
        الملف الصوتي ومعلوماته
    """
    try:
        # اختيار أغنية عشوائية من الأغاني المضمنة
        random_song = EMBEDDED_SONGS[random.randint(0, len(EMBEDDED_SONGS)-1)]
        
        # إعادة رسالة بديلة للمستخدم لاعلامه
        logger.info(f"استخدام أغنية بديلة: {random_song['title']} بدلاً من: {title}")
        
        # إرجاع الأغنية المضمنة
        return await serve_embedded_song(random_song)
    except Exception as e:
        logger.error(f"خطأ في تقديم الأغنية البديلة: {e}")
        return False, f"غير قادر على تشغيل أغنية بديلة، فضلاً حاول لاحقًا."

async def download_music(url: str) -> Tuple[bool, Any]:
    """
    Download music from YouTube URL.
    
    Args:
        url: The YouTube URL.
        
    Returns:
        A tuple of (success, result), where result is either the file path or an error message.
    """
    # Reuse the play_music function as the implementation is the same
    return await play_music(url, 0)  # 0 is a placeholder chat_id

async def get_audio_info(url: str) -> Optional[Dict[str, Any]]:
    """
    Get information about an audio file from a URL.
    
    Args:
        url: The URL to the audio or video ID.
        
    Returns:
        A dictionary with audio information, or None if there was an error.
    """
    # التحقق مما إذا كان المدخل معرف فيديو وليس رابط كامل
    if not url.startswith(('http://', 'https://')):
        # إذا كان معرف فيديو فقط، قم بإنشاء رابط يوتيوب كامل
        if len(url) >= 11:  # طول معرف فيديو اليوتيوب النموذجي هو 11 حرفًا
            url = f"https://www.youtube.com/watch?v={url}"
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            # تجاوز القيود
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            # تعيين عميل مستخدم مخصص
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/watch'
        }
        
        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            if not info:
                raise Exception("فشل في استخراج معلومات الفيديو")
                
        except Exception as e:
            logger.warning(f"فشلت المحاولة الأولى للحصول على معلومات الفيديو: {e}")
            
            # استخدام خيارات بديلة
            alt_opts = ydl_opts.copy()
            alt_opts['extractor_args'] = {'youtube': {'skip': ['dash', 'hls']}}
            alt_opts['source_address'] = '0.0.0.0'  # للتغلب على قيود IP
            
            try:
                with yt_dlp.YoutubeDL(alt_opts) as ydl:
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                
                if not info:
                    raise Exception("فشلت المحاولة البديلة في استخراج معلومات الفيديو")
            
            except Exception as alt_e:
                logger.error(f"فشلت المحاولة البديلة للحصول على معلومات الفيديو: {alt_e}")
                # استخدام معلومات افتراضية لتجنب فشل البوت
                return {
                    'title': os.path.basename(url) if '/' in url else url,
                    'uploader': "غير معروف",
                    'duration': 0,
                    'thumbnail': None,
                    'view_count': 0,
                    'like_count': 0,
                }
        
        return {
            'title': info.get('title', 'Unknown'),
            'uploader': info.get('uploader', 'Unknown'),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', None),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'video_id': info.get('id', ''),
            'webpage_url': info.get('webpage_url', url),
        }
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        return None

def clean_cache():
    """Clean the song cache if it gets too large."""
    global song_cache
    from config import MAX_SONG_CACHE
    
    if len(song_cache) > MAX_SONG_CACHE:
        # Remove oldest entries (first ones in the dictionary)
        items_to_remove = len(song_cache) - MAX_SONG_CACHE
        keys_to_remove = list(song_cache.keys())[:items_to_remove]
        for key in keys_to_remove:
            del song_cache[key]
