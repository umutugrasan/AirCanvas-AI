# AirCanvas AI — Gesture-Controlled Note & Web App

Web kamerası önündeki el hareketlerini gerçek zamanlı analiz eden, OpenCV + MediaPipe + Streamlit tabanlı bir jest kontrollü çizim ve not alma platformu.

## Özellikler

| Jest | Mantık (MediaPipe) | Tetiklenen İşlev |
|------|--------------------|------------------|
| **Hassas Çizim** | Sadece işaret parmağı açık (başparmak yumruğa kıvrık) | 8. nokta (işaret ucu) takibiyle tuvale çizim |
| **Kalem Havada** | İşaret + başparmak birlikte açık | Çizmez, sadece imleci taşır — harfler arası boşluk için |
| **Tutma / Taşıma** | Başparmak ucu + işaret ucu birbirine değer (pinch) | Parmağın altında not varsa onu, yoksa tüm tuvali blok halinde taşır |
| **Akıllı Silgi** | İşaret + orta parmak açık (makas/barış işareti) | İki parmağın orta noktası bölgesel silgi olur |
| **Ekran Görüntüsü** | Yumruk → ani 5 parmak açılışı | Mevcut kareyi dondurup "kağıt altlık" haline getirir |
| **Tüm Ekranı Temizle** | 5 parmak açık avuç | Tüm çizimleri ve notları sıfırlar |

## Teknolojik Altyapı

- **OpenCV** — kamera akışı, görüntü dönüşümleri, katman birleştirme
- **MediaPipe Hands** — 21 eklem noktasıyla gerçek zamanlı el iskeleti takibi
- **NumPy** — sanal tuval matrisi (640×480×3) yönetimi ve `warpAffine` ile blok taşıma
- **Streamlit + streamlit-webrtc** — tarayıcıda canlı webcam akışı

## Proje Yapısı

```
.
├── app.py                 # Streamlit web sürümü (streamlit run app.py)
├── aircanvas.py           # Bağımsız OpenCV penceresi sürümü
├── hand_tracker.py        # MediaPipe Hands sarmalayıcısı
├── gesture_detector.py    # Parmak durumu → jest etiketi
├── canvas_manager.py      # Tuval, notlar, screenshot ve blok taşıma katmanı
├── requirements.txt
└── screenshots/           # SCREENSHOT jesti kayıtları (otomatik oluşur)
```

## Kurulum

> **Önemli:** Python 3.11 önerilir. MediaPipe 3.13+ için kararlı wheel henüz yok. Ayrıca proje klasörü yolunda **Türkçe karakter olmamalıdır** (MediaPipe'ın C++ dosya yükleyicisi Windows'ta Türkçe karakterli yollarda kaynak dosyalarını açamıyor).

```powershell
# 1) Python 3.11 ile sanal ortam
py -3.11 -m venv venv
venv\Scripts\activate

# 2) Bağımlılıklar (sürümler birbirine sabitlenmiştir)
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Çalıştırma

### Web sürümü (Streamlit)

```powershell
streamlit run app.py
```

Tarayıcı sekmesinde **START** düğmesine basıp kamera izni verin. Yan panelden fırça rengini, kalınlığını ayarlayabilir; not metnini yazıp **Not ekle** ile parmak ucuna bir etiket bırakabilirsiniz. **Tuvali temizle** düğmesi tüm çizimleri sıfırlar.

### Bağımsız OpenCV sürümü

```powershell
python aircanvas.py
```

Klavye kısayolları:

| Tuş | İşlev |
|-----|-------|
| `q` | Çık |
| `c` | Tuvali temizle |
| `n` | Mevcut işaret parmağı ucuna örnek not bırak |
| `1` / `2` / `3` / `4` | Fırça rengi: mavi / yeşil / kırmızı / sarı |
| `+` / `-` | Fırça kalınlığını arttır / azalt |

## Görsel İmleç Geri Bildirimi

Karenin üst şeridinde gerçek zamanlı jest etiketi görünür; ayrıca:

- 🟡 Boş sarı halka → kalem havada (PEN_UP)
- 🔵 Dolu daire (fırça renginde) → kalem yerde (DRAW)
- 🟢 Yeşil çizgi + halka → pinch ile tutma (PINCH)
- ⚪ İnce gri daire → silgi sınırı (ERASE)

## Mimari Notlar

- `HandTracker.fingers_up()` her parmağın açık/kapalı durumunu, parmak ucu landmark'ının PIP eklemine göre konumuna bakarak çıkarır. Başparmak için yatay (X) karşılaştırma, diğerleri için dikey (Y) karşılaştırma kullanılır.
- `GestureDetector.detect()` durum makinesi yapısında çalışır: **yumruk → açık el** geçişini zaman penceresiyle (0.6 s) yakalar, ardışık screenshot için cooldown (1.2 s) uygular.
- `CanvasManager.drag()` parmak ucunda not varsa onu, yoksa tuvali baştan snapshot alıp `cv2.warpAffine` ile öteleyerek tüm çizimleri tek bir blok gibi taşır.
- `CanvasManager.compose()` siyah pikselleri şeffaf kabul ederek tuvali ham kameraya maskeleyerek bindirir; böylece çizgiler kayboldukları yerlerde kamera akışını gizlemez.

## CV Değerlendirme Notu

Proje, sadece hazır derin öğrenme modellerini çalıştırmakla kalmaz; gerçek zamanlı video akışı, durum makineli jest analizi, durum yönetimi (sürüklenen nesneler, blok taşıma, screenshot tetikleyicisi), kullanıcı arayüzü etkileşimi ve modüler Python mimarisi gibi kıdemli mühendislik pratiklerini sergiler.
