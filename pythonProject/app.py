from flask import Flask, request, jsonify, render_template, session, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, PageBreak
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import openai

# OpenAI API anahtarı tanımla
API_KEY = "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"  # Buraya kendi OpenAI API anahtarınızı yazın
client = openai.OpenAI(api_key=API_KEY)  # API anahtarıyla OpenAI istemcisini başlat

app = Flask(__name__, template_folder="templates")


# Static dosya (CSS, JS) sunumu için
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


app.secret_key = "supersecretkey"

# Güvenlik ayarları
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['WTF_CSRF_ENABLED'] = False

# SQLite veritabanı bağlantısı
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Türkçe karakter desteği için Arial fontunu kaydet
pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))


# Veritabanı modeli
class UserResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(500), nullable=False)


# Veritabanını oluştur
with app.app_context():
    db.create_all()

# Sorular ve koşullu sorular
questions = [
    {"question": "Adınız ve Soyadınız:", "type": "text"},
    {"question": "Öğrenim Durumunuz:", "type": "text"},
    {"question": "Geçmişteki başarı durumunuz:", "type": "radio", "options": ["İyi", "Orta", "Kötü"]},
    {"question": "İş Tecrübeniz (Pozisyon):", "type": "text"},
    {"question": "Doğum Yeriniz ve Yılınız:", "type": "text"},
    {"question": "Medeni Haliniz:", "type": "radio", "options": ["Evli", "Bekar", "Boşanmış"]},
    {"question": "Çocuğunuz var mı? Kaç tane?", "type": "text", "condition": {"Medeni Haliniz:": ["Evli", "Boşanmış"]}},
    {"question": "Kendinizi ne kadar sağlıklı görüyorsunuz?", "type": "text"},  # Bu satır sadece bir kez olmalı
    {"question": "Tipik bir gününüz veya haftanız nasıl geçer?", "type": "text"},
    {"question": "Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?", "type": "radio",
     "options": ["Evet", "Hayır"]},
    {"question": "Seanslarınız ne kadar sürdü? (Ay ve yıl olarak belirtiniz)", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Profesyonel yardım almaya ilişkin probleminizi tanımlayabilir misiniz?", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Problem Durumu:", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Ne kadar zamandır sürmektedir?", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Ne kadar sıklıkla meydana gelmektedir?", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Bu problem durumuyla ilgili olarak özellikle şu anda danışmaya başvurmanıza yol açan neden nedir?",
     "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Bu problem durumu günlük yaşamınızı nasıl etkiliyor?", "type": "text",
     "condition": {"Daha önce psikiyatrist, psikolog veya psikolojik danışmana başvurdunuz mu?": ["Evet"]}},
    {"question": "Fiziksel/Somatik Şikayetleriniz:", "type": "checkbox",
     "options": ["Uykuya dalmada güçlük", "Kabus görme", "Baş ağrısı", "Karın ağrısı", "Kalp çarpıntısı",
                 "Kilo alma/aşırı zayıflama", "Tansiyon", "Nefes darlığı", "Yeme düzeninde değişim"]},
    {"question": "DSM Soruları (Evet/Hayır):", "type": "dsm-yesno", "options": [
        "Uykuya dalmada güçlük",
        "Uykuda huzursuzluk, rahat uyuyamama",
        "Sabahın erken saatlerinde uyanma",
        "Yerinizde duramayacak ölçüde rahatsızlık hissetme",
        "Sinirlilik ya da içinin titremesi",
        "Gerginlik veya coşku hissi",
        "İştah azalması",
        "Cinsel arzu ve ilginin kaybı",
        "Bedeninizde ciddi bir rahatsızlık olduğu düşüncesi",
        "Karamsarlık hissi",
        "Olanlar için kendisini suçlama",
        "Her şeye karşı ilgisizlik hali",
        "Titreme",
        "Her şey için çok fazla endişe duyma",
        "Enerjinizde azalma veya yavaşlama hali",
        "Ölüm ya da ölme düşünceleri",
        "Her şey için çok fazla endişe duyma",
        "Sinirlilik ya da içinin titremesi",
        "Sizi korkutan belirli uğraş, yer veya nesnelerden kaçınma durumu",
        "Uykuda huzursuzluk, rahat uyuyamama",
        "Düşüncelerinizi bir konuya yoğunlaştırmada güçlük",
        "Gelecek konusunda ümitsizlik",
        "Adele (kas) ağrıları",
        "Soğuk veya sıcak basması",
        "Kalbin çok hızlı çarpması",
        "Nefes almada güçlük",
        "Bulantı ve midede rahatsızlık hissi",
        "Cinsel arzu ve ilginin kaybı",
        "Baygınlık ya da baş dönmesi",
        "Enerjinizde azalma veya yavaşlama hali"
    ]}
]

# Duplicate soru kontrolü ve temizleme işlemi
question_texts = [q["question"] for q in questions]
unique_questions = []
seen_questions = set()

for q in questions:
    if q["question"] not in seen_questions:
        seen_questions.add(q["question"])
        unique_questions.append(q)

questions = unique_questions  # Tekrarları kaldırılmış yeni liste

print(f"Güncellenmiş soru listesi: {len(questions)} soru var.")

@app.route("/")
def home():
    if "session_id" not in session:
        session["session_id"] = os.urandom(16).hex()
    return render_template("entry.html")


@app.route("/chat")
def chat():
    return render_template("index.html")


@app.route("/get_conversation", methods=["GET"])
def get_conversation():
    session_id = session.get("session_id")
    responses = UserResponse.query.filter_by(session_id=session_id).all()
    conversation = [{"question": resp.question, "answer": resp.answer} for resp in responses]
    return jsonify(conversation)


@app.route("/get_question", methods=["GET"])
def get_question():
    session_id = session.get("session_id")
    responses = UserResponse.query.filter_by(session_id=session_id).all()

    # 🔹 Kullanıcının zaten yanıtladığı soruları bir sete ekleyelim
    answered_questions = {resp.question for resp in responses}

    # 🔹 Aynı sorunun iki kez gönderilmemesi için bu seti kullanacağız
    considered_questions = set()

    for question_data in questions:
        question_text = question_data["question"]

        # Eğer soru zaten sorulmuş veya işlendi ise atla
        if question_text in answered_questions or question_text in considered_questions:
            continue

        considered_questions.add(question_text)  # Eklenenleri takip et

        # 🔹 Koşullu sorular varsa ve kullanıcı uygun değilse atla
        if "condition" in question_data:
            condition_met = True
            for cond_question, cond_values in question_data["condition"].items():
                user_answer = next((resp.answer for resp in responses if resp.question == cond_question), None)
                if user_answer not in cond_values:
                    condition_met = False
                    break
            if not condition_met:
                continue

        return jsonify({
            "question": question_text,
            "type": question_data["type"],
            "options": question_data.get("options"),
            "min": question_data.get("min"),
            "max": question_data.get("max")
        })

    return jsonify({"question": None})  # Eğer sorular bittiyse None döndür

@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.json
    answer = data.get("answer", "").strip()
    session_id = session.get("session_id")

    if session_id:
        current_question = next((q["question"] for q in questions if q["question"] not in
                                 {resp.question for resp in UserResponse.query.filter_by(session_id=session_id).all()}),
                                None)
        if current_question:
            new_response = UserResponse(session_id=session_id, question=current_question, answer=answer)
            db.session.add(new_response)
            db.session.commit()
            return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Tüm sorular yanıtlandı!"})


@app.route("/reset_chat", methods=["POST"])
def reset_chat():
    session_id = session.get("session_id")
    if session_id:
        UserResponse.query.filter_by(session_id=session_id).delete()
        db.session.commit()

    # Oturumu temizlemek yerine yeni bir oturum ID'si atama
    session["session_id"] = os.urandom(16).hex()

    return jsonify({"status": "success", "redirect": "/"})


@app.route("/download_pdf", methods=["GET"])
def download_pdf():
    session_id = session.get("session_id")
    responses = UserResponse.query.filter_by(session_id=session_id).all()

    if not responses:
        return jsonify({"status": "error", "message": "Sohbet boş!"})

    pdf_filename = os.path.join(basedir, "sohbet.pdf")
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()

    # Türkçe karakter desteği için Arial fontunu kullan
    styles["BodyText"].fontName = "Arial"
    styles["Title"].fontName = "Arial"

    story = []

    # Kapak sayfası ekle
    story.append(Paragraph("<b>Anamnez Sohbet Raporu</b>", styles["Title"]))
    story.append(PageBreak())

    # Soru ve cevapları ekle
    for response in responses:
        story.append(Paragraph(f"<b>{response.question}</b>", styles["BodyText"]))

        # DSM sorularını özel olarak formatla
        if response.question == "DSM Soruları (Evet/Hayır):":
            dsm_answers = response.answer.split(", ")
            for answer in dsm_answers:
                story.append(Paragraph(f"- {answer}", styles["BodyText"]))
        else:
            story.append(Paragraph(response.answer, styles["BodyText"]))

        story.append(Paragraph("<br/><br/>", styles["BodyText"]))

    # PDF oluştur
    doc.build(story)

    return send_file(pdf_filename, as_attachment=True)


# ANALYSIS.HTML İÇİN EKLENEN KISIMLAR
@app.route("/analysis", methods=["GET"])
def analysis():
    try:
        return render_template("analysis.html")
    except Exception as e:
        return f"Hata: {str(e)}"


# PDF'den metin çıkarma fonksiyonu - PyMuPDF (fitz) kullanarak
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        # PyMuPDF ile PDF'i aç
        with fitz.open(pdf_path) as doc:
            # PDF boş mu kontrol et
            if doc.page_count == 0:
                return "PDF dosyası boş veya sayfa içermiyor."

            # Her sayfadan metin çıkar
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    text += page_text + "\n"
                except Exception as e:
                    text += f"[Sayfa {page_num + 1} okunamadı: {str(e)}]\n"

            # Çıkarılan metin boş mu kontrol et
            if not text.strip():
                return "PDF'den metin çıkarılamadı. Dosya taranmış görüntü içeriyor olabilir veya boş olabilir."

            return text
    except Exception as e:
        return f"PDF okuma hatası: {str(e)}"


# Dosya yükleme ve OpenAI analizi - geliştirilmiş hata yakalama ve işleme
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "Dosya bulunamadı"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "Dosya seçilmedi"}), 400

    # Dosya uzantısı kontrolü
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"message": "Lütfen PDF dosyası yükleyin"}), 400

    # Geçici dosya yolu
    temp_path = os.path.join(basedir, "temp.pdf")

    try:
        # Dosyayı geçici bir konuma kaydet
        file.save(temp_path)

        # PDF dosyasının boyutunu kontrol et
        if os.path.getsize(temp_path) < 100:  # Çok küçük dosyalar muhtemelen geçerli değil
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"message": "Geçersiz PDF dosyası. Dosya çok küçük veya eksik."}), 400

        # PDF'in metnini çıkar
        extracted_text = extract_text_from_pdf(temp_path)

        # Metin hata mesajı içeriyor mu kontrol et
        if extracted_text.startswith("PDF okuma hatası:"):
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"message": extracted_text}), 400

        # Metin boş veya çok kısa ise
        if len(extracted_text) < 20:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "message": "PDF'den yeterli metin çıkarılamadı. Dosya korumalı olabilir veya metin içermiyor olabilir."}), 400

        # OpenAI API ile analiz et
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Sen bir psikologsun ve anamnez raporlarını analiz ediyorsun."},
                    {"role": "user",
                     "content": f"Bu anamnez raporunu analiz et ve hassas noktaları çıkar:\n\n{extracted_text}"}
                ]
            )
            analyzed_text = response.choices[0].message.content
        except Exception as api_error:
            return jsonify({"message": f"OpenAI API hatası: {str(api_error)}"}), 500

        # İşlem sonrası geçici dosyayı sil
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({"message": analyzed_text})

    except Exception as e:
        # Herhangi bir hata olursa geçici dosyayı temizle
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"message": f"Beklenmeyen hata: {str(e)}"}), 500


if __name__ == "__main__":
    try:
        # Gerekli bağımlılıkları kontrol et ve yükle
        print("Uygulama başlatılıyor...")
        print("API Anahtarı durumu:", "Ayarlanmamış" if not API_KEY else "Ayarlanmış")

        # Başlatma mesajı
        print("Uygulama http://localhost:5001 adresinde çalışıyor")
        app.run(debug=True, host="0.0.0.0", port=5001)
    except OSError as e:
        print(f"⚠️  Port 5001 kullanımda veya başka bir hata oluştu: {str(e)}")
        print("Alternatif bir port deneyin.")