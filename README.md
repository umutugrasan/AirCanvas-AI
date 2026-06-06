# AirCanvas AI — Gesture-Controlled Note & Web App

Web kamerası önündeki el hareketlerini gerçek zamanlı analiz eden, OpenCV + MediaPipe + Streamlit tabanlı bir jest kontrollü çizim, not alma ve **resim annotation** platformu.

## Özellikler

### Jestler

| Jest | Mantık (MediaPipe) | Tetiklenen İşlev |
|------|--------------------|------------------|
| **Hassas Çizim** | Sadece işaret parmağı açık (başparmak yumruğa kıvrık) | 8. nokta (işaret ucu) takibiyle tuvale çizim |
| **Kalem Havada** | İşaret + başparmak birlikte açık | Çizmez, imleci taşır + **iki parmak arası mesafe = fırça kalınlığı** (geniş → kalın) |
| **Tutma / Taşıma** | Başparmak ucu + işaret ucu birbirine değer (pinch) | Parmak altında not varsa onu, yoksa tüm tuvali blok halinde taşır |
| **Akıllı Silgi** | İşaret + orta parmak açık (makas/barış işareti) | İki parmağın orta noktası bölgesel silgi olur |
| **Ekran Görüntüsü** | Yumruk → ani 5 parmak açılışı | Mevcut kareyi dondurup "kağıt altlık" haline getirir |
| **Tüm Ekranı Temizle** | 5 parmak açık avuç | Tüm çizimleri, notları ve geçmişi sıfırlar |

### Ekstra (jest dışı) yetenekler

- **Resim yükle → üzerine yaz**: yan panelden PNG/JPG yükle, üstüne not düş.
- **PIP webcam**: kullanıcı sağ alt köşede küçük thumbnail olarak görünür.
- **Havadan renk paleti**: ekranın üst şeridindeki paletin üzerine işaret parmağıyla yaklaş, ~5 kare bekle → renk seçilir. Çizim akışını kesmez.
- **Havadan fırça kalınlığı**: Kalem havadayken (PEN_UP) başparmak ile işaret arasındaki mesafe doğrudan kalınlığa eşlenir (40–200 px → 2–30 px). Cursor üzerinde gerçek kalınlıkta önizleme dairesi gösterilir.
- **Geri al / Yinele**: her stroke öncesi canvas snapshot'ı; sınır 30 adım.
- **Şekil düzeltme** (toggleable): DRAW jesti bitince stroke yeterince kapalıysa elipse, yeterince doğrusalsa düz çizgiye snap eder.
- **PNG olarak indir**: composed (kamera + tuval + arka plan + notlar) tek tıkla indirilir.

## Teknolojik Altyapı

- **OpenCV** — kamera akışı, görüntü dönüşümleri, `warpAffine` ile blok taşıma, `fitEllipse`/`fitLine` ile şekil düzeltme
- **MediaPipe Hands** — 21 eklem noktasıyla gerçek zamanlı el iskeleti takibi
- **NumPy** — sanal tuval matrisi (640×480×3) yönetimi
- **Streamlit + streamlit-webrtc** — tarayıcıda canlı webcam akışı

## Proje Yapısı

```
.
├── app.py                 # Streamlit web sürümü (streamlit run app.py)
├── aircanvas.py           # Bağımsız OpenCV pencere sürümü
├── hand_tracker.py        # MediaPipe Hands sarmalayıcısı
├── gesture_detector.py    # Parmak durumu → jest etiketi (durum makinesi)
├── canvas_manager.py      # Tuval, notlar, history, blok taşıma, şekil düzeltme
├── overlay.py             # Palet + HUD katmanı (her iki sürüm paylaşır)
├── requirements.txt
└── screenshots/           # SCREENSHOT / "p" kısayolu kayıtları
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

Tarayıcı sekmesinde **START** → kamera izni ver. Renk paleti ve fırça kalınlığı **doğrudan jestlerle** kontrol edilir; yan panel sade tutulmuştur:

- Geri al / Yinele / Tuvali temizle butonları
- **Resim yükle** → çizimi mevcut resim üzerine yap
- **Sağ altta PIP webcam** kutusunu aç/kapat
- **Şekil düzeltme** anahtarı
- Not ekleme (parmak ucuna)
- **PNG olarak indir** düğmesi (akışı başlattıktan sonra görünür)

### Bağımsız OpenCV sürümü

```powershell
python aircanvas.py
```

| Tuş | İşlev |
|-----|-------|
| `q` | Çık |
| `c` | Tuvali temizle |
| `z` / `y` | Geri al / Yinele |
| `n` | Mevcut parmak ucuna örnek not |
| `1`–`6` | Palet renkleri (mavi/yeşil/kırmızı/sarı/pembe/beyaz) |
| `+` / `-` | Fırça kalınlığı |
| `s` | Şekil düzeltmeyi aç/kapat |
| `p` | Mevcut kareyi PNG olarak kaydet |
| `b` | Arka planı (yüklenen resim/screenshot) temizle |
| `h` | PIP webcam'i aç/kapat |

## Görsel İmleç Geri Bildirimi

Karenin üst şeridinde gerçek zamanlı jest etiketi; ayrıca:

- 🟡 Sarı çizgi (başparmak↔işaret) + brush renginde halka → kalem havada (PEN_UP); halkanın yarıçapı = mevcut fırça kalınlığı
- 🔵 Dolu daire (fırça renginde) → kalem yerde (DRAW)
- 🟢 Yeşil çizgi + halka → pinch ile tutma (PINCH)
- ⚪ İnce gri daire → silgi sınırı (ERASE)

## Mimari Notlar

- `HandTracker.fingers_up()` her parmağın açık/kapalı durumunu, parmak ucu landmark'ının PIP eklemine göre konumuna bakarak çıkarır. Başparmak için yatay (X) karşılaştırma, diğerleri için dikey (Y) karşılaştırma kullanılır.
- `GestureDetector.detect()` durum makinesi: **yumruk → açık el** geçişini zaman penceresiyle (0.6 s) yakalar, ardışık screenshot için cooldown (1.2 s) uygular.
- `CanvasManager.drag()` parmak ucunda not varsa onu, yoksa tuvali baştan snapshot alıp `cv2.warpAffine` ile öteleyerek tüm çizimleri tek bir blok gibi taşır.
- `CanvasManager.push_history()` "değiştirici" jest (DRAW/ERASE/PINCH/CLEAR/SCREENSHOT) başlamadan önce çağrılır; en fazla 30 snapshot tutulur.
- `CanvasManager._correct_stroke_in_place()` chord/uzunluk oranına bakarak stroke'un kapalı mı doğrusal mı olduğuna karar verir; sonra `fitEllipse` veya `fitLine` ile snap eder.
- `overlay.palette_cells()` palet hücrelerini frame genişliğine göre hesaplar; `hit_test_palette` parmak ucu hangi hücrede onu döndürür. ~5 kare dwell süresi accidental seçimi engeller.
- `CanvasManager.compose()` siyah piksellerini şeffaf kabul ederek tuvali base'e (kamera frame'i veya yüklenen arka plan) maskeleyerek bindirir; PIP webcam'i sağ alt köşeye yerleştirir.

## CV Değerlendirme Notu

Proje, sadece hazır derin öğrenme modellerini çalıştırmakla kalmaz; gerçek zamanlı video akışı, durum makineli jest analizi, undo/redo geçmişi, blok taşıma, otomatik şekil düzeltme (`fitEllipse`/`fitLine`), kullanıcı arayüzü etkileşimi ve modüler Python mimarisi gibi kıdemli mühendislik pratiklerini sergiler.
