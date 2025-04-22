from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>بوت تيليجرام</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            body {
                direction: rtl;
                text-align: right;
                font-family: Arial, sans-serif;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .features {
                margin-top: 20px;
            }
            .feature-item {
                margin-bottom: 10px;
                padding: 10px;
                border-radius: 5px;
            }
            .btn-primary {
                margin-top: 20px;
            }
            h1, h2, h3 {
                color: var(--bs-info);
            }
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">
            <div class="row">
                <div class="col-12 text-center mb-4">
                    <h1>بوت تيليجرام للموسيقى وحماية المجموعات</h1>
                    <p class="lead">بوت مُحسَّن باللغة العربية للموسيقى وحماية المجموعات مع أزرار تفاعلية ومميزات متعددة</p>
                </div>
            </div>
            
            <div class="row features">
                <div class="col-md-6">
                    <div class="feature-item">
                        <h3>🎵 ميزات الموسيقى</h3>
                        <ul>
                            <li>بحث وتشغيل الأغاني من خلال يوتيوب</li>
                            <li>قائمة بالفنانين المشهورين</li>
                            <li>البحث عن وتحميل مقاطع الفيديو</li>
                            <li>تشغيل عشوائي للأغاني</li>
                        </ul>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="feature-item">
                        <h3>🛡️ حماية المجموعات</h3>
                        <ul>
                            <li>التعرف على الكلمات المسيئة وحذفها تلقائياً</li>
                            <li>حذف الروابط غير المرغوب فيها</li>
                            <li>حذف الرسائل المحولة</li>
                            <li>نظام للتحذيرات قبل الطرد أو الحظر</li>
                        </ul>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="feature-item">
                        <h3>📚 ميزات دينية</h3>
                        <ul>
                            <li>قائمة بسور القرآن الكريم</li>
                            <li>تفعيل إشعارات الأذان</li>
                        </ul>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="feature-item">
                        <h3>💬 ميزات أخرى</h3>
                        <ul>
                            <li>واجهة عربية بالكامل</li>
                            <li>أزرار تفاعلية</li>
                            <li>ميزات إدارية للمشرفين</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-12 text-center">
                    <p>يعمل البوت حالياً على منصة Replit</p>
                    <a href="https://t.me/DARKCODE_Channel" target="_blank" class="btn btn-primary">زيارة قناة البوت</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)