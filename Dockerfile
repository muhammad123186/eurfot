# استخدام صورة بايثون الرسمية
FROM python:3.10-slim

# منع بايثون من تخزين الملفات المؤقتة وطباعة المخرجات مباشرة على الشاشة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت متطلبات النظام الأساسية إذا لزم الأمر
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات وتثبيت مكتبات بايثون
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع إلى داخل الحاوية
COPY . /app/

# جمع ملفات الـ Static (اختياري، يفضل وضعه هنا أو تنفيذه لاحقاً)
# RUN python manage.py collectstatic --noinput

# تحديد المنفذ (Port) الذي سيستمع عليه تطبيق Cloud Run
ENV PORT=8080

# أمر تشغيل سيرفر المشروع عبر Gunicorn (سيرفر جاهز للإنتاج)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 project.wsgi:application