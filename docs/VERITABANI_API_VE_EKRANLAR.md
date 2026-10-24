# Veritabanı API'si ve Ekran Tasarımları

Uygulama (PySide6) tablolara dokunmaz; yalnızca bu belgedeki **görünümleri okur** ve **fonksiyonları çağırır**. Aşama B (API + yetki) ve Aşama F (uygulama) bu belgeye göre yazılır.

Durum: ✔ var ve testli · ◐ iskelet var (`sql/iskeletler.sql`, `sql/iskelet_rls.sql`) · ✎ yazılacak. Öncelik: **Z** zorunlu · **F** fark yaratan · **O** opsiyonel.

---

## 1. Veritabanı API'si

### 1.1 Kurallar

- Her uygulama işlemi **tek veritabanı işleminde** yapılır: `SET LOCAL ROLE <rol>` → `set_config('app.kullanici_id', '<id>', true)` → çağrı (`db.py`'deki `Is` sınıfı bunu yapar).
- **Okuma:** `WITH (security_invoker = true)` görünüm; RLS satırları kullanıcıya göre süzer. Varsayılan görünümler RLS'yi atlar (denendi).
- **Yazma:** `SECURITY DEFINER` fonksiyon + `SET search_path = public`; kimlik `nullif(current_setting('app.kullanici_id', true), '')::int`; yoksa `YETKISIZ`.
- **Hata:** `RAISE EXCEPTION 'KOD: açıklama'`; uygulama `:` öncesini koda çevirir (§1.5).
- `donem.yil` **akademik yıl başlangıcıdır** (2025 güz ve 2025 bahar aynı akademik yıl). Sınıf = `donem.yil − ogrenci.giris_yili + 1`.
- Mevcut fonksiyonlar kimliği parametre alır (`fn_gno(p_ogrenci)` …). Uygulamaya açılan **`_ben` sarmalayıcıları** oturum kimliğini kullanır, böylece öğrenci başkasının kimliğini veremez.

### 1.2 Okuma görünümleri (hepsi `security_invoker`)

| Görünüm | Sütunlar | Rol | Ekran | Durum | Ö |
|---|---|---|---|---|---|
| `v_demo_kullanicilar` | kisi_id, ad_soyad, roller | giriş rolü (`obs_login`) | Giriş | ◐ (sahip yetkisiyle: bilerek) | Z |
| `v_ana_sayfa` | sinif, gecilen_akts, dno, gno, aktif_donem, kayit_acik, kayit_bitis, ekle_birak_bitis | öğrenci | Ana sayfa | ✎ | Z |
| `v_acik_subeler` | sube_id, donem_id, ders_kod, ders_ad, akts, sube_no, hoca, saatler (`Pzt 1-2`), durum, neden | öğrenci | Ders seçimi | ✎ | Z |
| `v_kayitlarim` | kayit_id, ders_kod, ders_ad, akts, sube_no, donem_id, durum, onay_gerekce | öğrenci | Ders seçimi | ◐ | Z |
| `v_haftalik_program` | donem_id, gun, ders_saati, ders_kod, sube_no, durum | öğrenci | Ders seçimi | ✎ | Z |
| `v_transkript` | ogrenci_no, ad_soyad, yil, donem, kod, ders_adi, akts, harf, katsayi, durum | öğrenci, danışman | Notlar | ✔ (`security_invoker` ile yeniden oluştur) | Z |
| `v_not_detay` | kayit_id, ders_kod, bilesen, agirlik, puan, ilan_edildi | öğrenci, öğr. üyesi | Notlar | ✎ | Z |
| `v_onay_kuyrugu` | kayit_id, ogrenci_id, ogrenci_no, ad_soyad, ders_kod, ders_ad, akts, olusturma, gno | danışman | Danışman | ✎ | Z |
| `v_danisanlarim` | ogrenci_id, ogrenci_no, ad_soyad, gno, gecilen_akts, bayrak_sayisi, en_yuksek_siddet, risk_skoru | danışman | Danışman | ✎ | Z |
| `v_danisan_bayraklari` | ogrenci_id, kural_kod, aciklama, siddet | danışman | Danışman | ✎ | Z |
| `v_danisan_risk` | ogrenci_id, skor, ozellikler, model, hesap_zamani | danışman | Danışman | ✎ | F |
| `v_sube_listem` | sube_id, donem_id, ders_kod, ders_ad, sube_no, ogrenci_sayisi | öğr. üyesi | Notlar | ✎ | Z |
| `v_sube_ogrencileri` | sube_id, kayit_id, ogrenci_no, ad_soyad, durum | öğr. üyesi | Notlar | ✎ | Z |
| `v_bilesenler` | sube_id, bilesen_id, ad, agirlik | öğr. üyesi, öğrenci | Notlar | ✎ | Z |
| `v_mufredat_listesi` | mufredat_id, program, giris_yili | öğrenci | Mezuniyet (What-If) | ✎ | F |
| `v_parametreler` | anahtar, deger, aciklama | tümü okur | Yönetim | ✎ | Z |
| `v_denetim_log` | log_id, zaman, kullanici, tablo, islem, kayit_pk, eski, yeni | yönetici | Yönetim | ✎ | Z |
| `v_silinen_notlar` | log_id, zaman, kullanici, kayit_pk, eski | yönetici | Demo | ✎ | Z |

**Mezuniyet fonksiyonları (✔ var, kimlik parametreli):** `fn_mezuniyet_ozet`, `fn_mezuniyet_denetim`, `fn_ders_plani`, `fn_en_erken_mezuniyet`. Uygulamaya şu **`_ben` sarmalayıcıları** açılır (✎ Z): `fn_mezuniyet_ozet_ben()`, `fn_mezuniyet_denetim_ben(p_mufredat int DEFAULT NULL)`, `fn_ders_plani_ben(p_limit int DEFAULT NULL)`, `fn_en_erken_mezuniyet_ben(p_limit int DEFAULT NULL)`. Danışman kendi danışanı için aynı fonksiyonları kimlikle çağırabilir (`fn_..._danisan(p_ogrenci)`, danışmanlık kontrolüyle) — F.

**`v_acik_subeler.durum` değerleri** (öğrenci için hesaplanır, sırayla ilk uyan):
`gecildi` (ders daha önce geçildi) → `kayitli` (bu dönem `onay_bekliyor`/`onayli`) → `sepette` → `onkosul_eksik` (`neden` = eksik ders kodları, `fn_onkosul_eksikleri`) → `cakisiyor` (`sube_saat`, `ogrenci_slot` ile kesişiyor) → `alinabilir`. Yalnızca öğrencinin müfredatındaki dersler listelenir (bkz. §1.6, `MUFREDAT_DISI`).

### 1.3 Yazma fonksiyonları (`SECURITY DEFINER`)

| Fonksiyon | Parametreler | Dönüş | Rol | Durum | Ö |
|---|---|---|---|---|---|
| `fn_sepete_ekle` | p_sube int | kayit_id | öğrenci | ◐ | Z |
| `fn_sepetten_cikar` | p_kayit int | void | öğrenci | ✎ | Z |
| `fn_kesinlestir` | p_kayit int | void | öğrenci | ✎ | Z |
| `fn_kesinlestir_hepsi` | — | (kayit_id, sonuc, mesaj) | öğrenci | ✎ | Z |
| `fn_birak` | p_kayit int | void | öğrenci | ✎ | Z |
| `fn_danisman_karar_ben` | p_kayit, p_karar, p_gerekce | void | danışman | ✎ (✔ `fn_danisman_karar`'ı sarar) | Z |
| `fn_bilesenleri_belirle` | p_sube, p_adlar text[], p_agirliklar numeric[] | adet | öğr. üyesi | ✎ | Z |
| `fn_not_gir` | p_kayit, p_bilesen, p_puan | void (upsert) | öğr. üyesi | ✎ | Z |
| `fn_not_ilan_et` | p_sube | adet | öğr. üyesi | ✎ | Z |
| `fn_sonuclari_hesapla` | p_sube | (hesaplanan, eksik) | öğr. üyesi | ✎ (✔ `fn_sonuc_hesapla`'yı sarar) | Z |
| `fn_not_duzelt` | p_kayit, p_bilesen, p_puan, p_gerekce | void | öğr. üyesi | ✎ | F |
| `fn_yoklama_gir` | p_kayit, p_tarih, p_katildi | void (upsert) | öğr. üyesi | ✎ | F |
| `fn_donem_ac` | p_yil, p_tur, p_kayit_bas, p_kayit_bit, p_eb_bit, p_donem_sonu | donem_id | sekreter | ✎ | Z |
| `fn_sube_ac` | p_ders, p_donem, p_sube_no, p_hoca | sube_id | sekreter | ✎ | Z |
| `fn_sube_saat_ekle` | p_sube, p_gun, p_saat | void | sekreter | ✎ | Z |
| `fn_danisman_ata` | p_ogrenci, p_danisman, p_baslangic date | void | sekreter | ✎ | Z |
| `fn_parametre_guncelle` | p_anahtar, p_deger | void | yönetici | ✎ | Z |
| `fn_risk_bayrak_hesapla` | p_donem | adet | sekreter, yönetici | ◐ (Aşama A) | Z |
| `fn_belge_uret` | p_tur | doğrulama kodu | öğrenci | ✎ | F |
| `fn_belge_dogrula` | p_kod | (gecerli, ogrenci_no, tur, uretim_zamani) | tüm roller | ✎ | F |
| Demo: `fn_demo_akts_hazirla`, `fn_demo_akts_kilidi`, `fn_demo_kilitlenme`, `fn_demo_kilitlenme_duzeltilmis`, `fn_demo_not_sil`, `fn_not_geri_al`, `fn_demo_explain`, `fn_demo_indeks` | bkz. `UYGULAMA_PLANI.md` Aşama D | — | yönetici, sekreter | ◐ / ✎ | Z |

**Kritik kurallar (fonksiyon gövdesinde):**
- **Sahiplik:** öğrenci fonksiyonları kaydın `ogrenci_id`'sinin oturum kimliği olduğunu doğrular; öğretim üyesi fonksiyonları şubenin `ogretim_uyesi_id`'sini doğrular; aksi halde `YETKISIZ`.
- **`fn_sepetten_cikar`:** yalnız `sepet` durumundaki kaydı `birakti` yapar (geçiş tetikleyicide denetlenir).
- **`fn_kesinlestir`:** `sepet → onay_bekliyor` günceller; pencere, AKTS ve slot kuralları tetikleyicilerdedir. **`fn_kesinlestir_hepsi`:** öğrencinin aktif dönemdeki her `sepet` kaydını ayrı alt işlemde dener (`BEGIN … EXCEPTION WHEN OTHERS`), kayıt başına `tamam` / `hata` + mesaj döndürür ("Kontrol Et + Kesinleştir" düğmesi).
- **`fn_birak`:** `onay_bekliyor`/`onayli` → `birakti`; onaylı kaydı bırakma ekle-bırak penceresiyle sınırlıdır (tetikleyicide).
- **`fn_bilesenleri_belirle`:** bileşenleri **tek çağrıda** (dizilerle) yazar; ağırlık toplamı kuralı ertelenebilir kısıt olduğu için işlem sonunda denetlenir. Tek tek ekleme her çağrıda ayrı işlem olacağından ilk bileşende toplam ≠ 100 hatası verirdi. Notu girilmiş şubede bileşenleri değiştirmeyi reddet.
- **`fn_not_gir`:** şube ve bileşen eşleşmesini bileşik FK zaten garanti eder; satır `ilan_edildi = true` ise `NOT_ILAN_EDILDI` verir (düzeltme için `fn_not_duzelt`).
- **`fn_not_ilan_et`:** şubenin girilmiş notlarını `ilan_edildi = true` yapar. **`fn_sonuclari_hesapla`:** tüm bileşenleri ilan edilmiş `onayli` kayıtlar için `fn_sonuc_hesapla` çağırır, eksik kalanların sayısını döndürür.
- **`fn_not_duzelt`:** gerekçe boş olamaz (`GEREKCE_ZORUNLU`); `set_config('app.gerekce', p_gerekce, true)` ile gerekçeyi denetim logunun JSON'una taşır; sonuç varsa yeniden hesaplar.
- **`fn_danisman_ata`:** önceki açık aralığı kapatır (`UPDATE danismanlik SET gecerlilik = daterange(lower(gecerlilik), p_baslangic) WHERE ogrenci_id = … AND upper_inf(gecerlilik)`), sonra `daterange(p_baslangic, NULL)` ekler; `EXCLUDE` kısıtı çakışmayı yine de reddeder. `p_baslangic`, önceki aralığın başlangıcından küçük ya da eşitse hata ver.
- **`fn_belge_uret`:** `dogrulama_kodu = substr(md5(random()::text || clock_timestamp()::text), 1, 12)`; `icerik_hash` = transkript satırlarının `sha256` özeti. `fn_belge_dogrula` kodu ve özeti karşılaştırır.
- **`fn_parametre_guncelle`:** yalnız yönetici; değişiklik `denetim_log`'a otomatik düşer (tetikleyici var).

### 1.4 RLS matrisi (SELECT politikaları; yazma yalnız fonksiyonlarla)

| Tablo | öğrenci | danışman | öğr. üyesi | sekreter | yönetici |
|---|---|---|---|---|---|
| `kayit`, `kayit_onay`, `ogrenci_slot` | kendi | danışanları | kendi şubeleri (`kayit`) | tümü | tümü |
| `not_kaydi` | kendi (yalnız `ilan_edildi`) | danışanları (yalnız `ilan_edildi`) | kendi şubeleri | tümü | — |
| `kayit_sonuc`, `yoklama` | kendi | danışanları | kendi şubeleri | tümü | — |
| `degerlendirme_bileseni` | aldığı şubeler | danışanlarının şubeleri | kendi şubeleri | tümü | tümü |
| `ogrenci`, `kisi` | kendi | danışanları | kendi şubelerindeki öğrenciler | tümü | tümü |
| `danismanlik` | kendi | kendi satırları | — | tümü | tümü |
| `risk_bayrak`, `risk_tahmin` | **—** | danışanları | — | — | — |
| `belge` | kendi | — | — | tümü | tümü |
| `denetim_log` | — | — | — | — | tümü |
| `ders`, `mufredat`, `mufredat_ders`, `onkosul`, `gereksinim_*`, `program`, `bolum`, `donem`, `sube`, `sube_saat`, `ogretim_uyesi` | okuma | okuma | okuma | okuma | okuma |
| `harf_notu_aralik`, `akts_limit_kural`, `parametre` | okuma | okuma | okuma | okuma | okuma |

Risk verisi öğrenciye gösterilmez (tasarım ilkesi: skor yalnız danışmana). Kalıp: `iskelet_rls.sql`.

### 1.5 Hata kodu → Türkçe mesaj (`hatalar.py`)

| Kod / ipucu | Mesaj |
|---|---|
| `DONEM_KAPALI` | Kayıt veya ekle-bırak dönemi kapalı. |
| `ONKOSUL_EKSIK` | Bu dersin önkoşulu sağlanmıyor: {ayrıntı}. |
| `CAKISMA` | Seçtiğiniz dersin saati başka bir dersinizle çakışıyor. |
| `AKTS_ASIMI` | Dönemlik AKTS sınırınızı aşıyorsunuz. |
| mesajda `ux_kayit_aktif` | Bu dersi bu dönem zaten aldınız (başka bir şube). |
| `MUFREDAT_DISI` | Bu ders sizin müfredatınızda değil. |
| `YETKISIZ` | Bu işlem için yetkiniz yok. |
| `GECERSIZ_GECIS` | Bu kayıt durumundan bu işleme geçilemez. |
| mesajda `check constraint` (`kayit_onay`) | Red ve düzeltme isteği için gerekçe yazmalısınız. |
| `GEREKCE_ZORUNLU` | Bu değişiklik için gerekçe zorunlu. |
| `AGIRLIK_TOPLAMI` | Değerlendirme ağırlıkları toplamı 100 olmalı. |
| `NOT_EKSIK` | Tüm bileşenler ilan edilmeden sonuç hesaplanamaz. |
| `NOT_ILAN_EDILDI` | Not ilan edildi; değiştirmek için gerekçeli düzeltme kullanın. |
| `KAYIT_BULUNAMADI`, `SUBE_BULUNAMADI`, `OGRENCI_BULUNAMADI`, `LOG_BULUNAMADI` | Kayıt bulunamadı. |
| `PLAN_KURULAMADI` | Ders planı kurulamadı: AKTS limiti ya da önkoşul döngüsü. |
| `ONKOSUL_DONGUSU` | Bu önkoşul bir döngü oluşturur. |
| `DENETIM_LOGU_DEGISTIRILEMEZ` | Denetim kaydı değiştirilemez. |
| `SORGU_BILINMIYOR` | Bilinmeyen demo sorgusu. |
| `psycopg.errors.DeadlockDetected` (40P01) | Kilitlenme tespit edildi; işlemlerden biri geri alındı. |
| `psycopg.errors.SerializationFailure` (40001) | Eşzamanlı değişiklik çakıştı, tekrar deneyin. |
| bilinmeyen | Beklenmeyen hata (ayrıntı için tıklayın). |

### 1.6 Bilinen eksikler ve kapsam kararları

| Konu | Karar |
|---|---|
| **Müfredat dışı ders (`MUFREDAT_DISI`)** | **Yapılacak (Aşama B):** `fn_kayit_kurallar` INSERT dalına, dersin öğrencinin müfredatında (`mufredat_ders`) olduğunu denetleyen kontrol ekle. Şu an yalnız `v_acik_subeler` listesi bunu uygular. |
| Danışman süre aşımı (kayıt ne olur) | Kapsam dışı; karar: danışman karar verene kadar `onay_bekliyor` kalır. |
| Final taban puanı, devamsızlık nedeniyle kalma | Kapsam dışı (basitleştirme); devamsızlık yalnızca risk bayrağında kullanılır. |
| What-If'te farklı ders kataloğu (denklik) | Kapsam dışı; ortak `ders_id` varsayılır. |
| En erken mezuniyette seçmeli açığı | Kapsam dışı; yalnız zorunlu dersler planlanır. |
| Kontenjan / bekleme listesi | Kullanıcı kararıyla kapsam dışı. |

---

## 2. Ekran tasarımları

### 2.0 Genel kurallar

- Dil Türkçe; tarih `gg.aa.yyyy`; ondalık virgül; tablolar sütundan sıralanır; çift tıklama ayrıntı açar.
- **Her veritabanı çağrısı** `Is` işçisiyle yapılır; sürerken bekleme imleci ve ilgili düğme pasif.
- Her yazma işleminden sonra ilgili görünümler yeniden yüklenir.
- Hata: Türkçe mesaj kutusu (§1.5) + "Ayrıntı" düğmesi (ham mesaj). Boş durum: tabloda soluk metin ("Gösterilecek kayıt yok").
- Geri alınamaz işlemlerde (bırak, sil, red) onay penceresi.
- Menü rolün yetkisine göre görünür: öğrenci → Ana Sayfa, Ders Seçimi, Notlar, Mezuniyet; danışman → Danışman, Notlar (danışanların transkripti); öğretim üyesi → Notlar (not girişi); sekreter/yönetici → Yönetim.

### 2.1 Giriş

```
┌──────────────────────────────────┐
│   Öğrenci Bilgi Sistemi          │
│   Kullanıcı  [ Ada Örnek     ▼ ] │
│   Rol        [ Öğrenci       ▼ ] │
│              [   Giriş   ]       │
│   ● Veritabanı bağlı             │
└──────────────────────────────────┘
```
Veri: `v_demo_kullanicilar` (rol listesi = kişinin rolleri; danışmanlık `danisman` rolünü verir). **Giriş** → oturum kimliği ve rol belirlenir → ana pencere. Hata: bağlantı kurulamadı → "Veritabanına bağlanılamadı (.env dosyasını kontrol edin)".

### 2.2 Ana pencere (kabuk)

```
┌─────────────┬────────────────────────────────────────────┐
│ Ana Sayfa   │  Ada Örnek · Öğrenci                [Çıkış]│
│ Ders Seçimi ├────────────────────────────────────────────┤
│ Notlar      │                                            │
│ Mezuniyet   │   <seçili sayfa>                           │
│ (menü role  │                                            │
│  göre)      ├────────────────────────────────────────────┤
│             │  durum çubuğu: kayıt dönemi açık           │
└─────────────┴────────────────────────────────────────────┘
```
Sol menü `QListWidget`, sayfalar `QStackedWidget`; üstte kullanıcı ve rol.

### 2.3 Ana sayfa (öğrenci)

```
 ┌ Sınıf ───┐ ┌ Verilen kredi ┐ ┌ Dönem DNO ┐ ┌ GNO ──┐
 │ 2. Sınıf │ │ 54            │ │ 3,10      │ │ 2,80  │
 └──────────┘ └───────────────┘ └───────────┘ └───────┘
 Kayıt dönemi: AÇIK — ekle-bırak 14.11.2026'ya kadar
 2025 Güz ●─────● 2025 Bahar ●─────● 2026 Güz ○───── …
```
Veri: `v_ana_sayfa` (+ `v_transkript` dönem özeti). Boş: sonuç yoksa "Henüz sonuçlanmış ders yok". Kartlar `ilerleme_karti.py`.

### 2.4 Ders seçimi (öğrenci) — en kritik ekran

```
 Ara [__________]  Dönem [2026 Güz ▼]
 ┌ Açık şubeler ─────────────────────────────┐ ┌ Haftalık program ──────┐
 │ BIL201-1 Veri Yapıları  6  Pzt 1-2  ✔     │ │     Pzt Sal Çar Per Cum│
 │ BIL202-1 Veri Tabanı…   6  Pzt 3-4  ✖ Önkoşul eksik │ │ 1  [201]               │
 │ SEC101-1 Seçmeli A      6  Pzt 2    ✖ Çakışıyor     │ │ 2  [201]               │
 └──[ Sepete ekle ]──────────────────────────┘ └────────────────────────┘
 ┌ Kayıtlarım:  [Sepet] [Onay bekleyen] [Onaylı] [Reddedilen] ───────────────┐
 │ Ders        Şube  AKTS  Durum          Gerekçe                            │
 └──[ Sepetten çıkar ] [ Kontrol Et + Kesinleştir ] [ Bırak ]────────────────┘
 Toplam AKTS (kesinleşen + bekleyen): 24 / 30
```
- **Veri:** `v_acik_subeler`, `v_kayitlarim`, `v_haftalik_program`; sınır için `v_ana_sayfa`/`fn_akts_limit`.
- **Eylemler:** `fn_sepete_ekle`, `fn_sepetten_cikar`, `fn_kesinlestir_hepsi` (sonuç satır satır bir iletişim kutusunda), `fn_birak`.
- **Davranış:** `durum` rozetleri (`alinabilir` yeşil, `onkosul_eksik`/`cakisiyor` kırmızı + neden, `sepette`/`kayitli` gri); "Sepete ekle" yalnız `alinabilir` satırda aktif; sepetteki seçimler haftalık programda soluk görünür, kesinleşenler dolu.
- **Hatalar:** §1.5 mesajları; boş: "Açık şube yok".

### 2.5 Notlar

**Öğrenci modu**
```
 Dönem [Tümü ▼]
 ┌ Transkript ─────────────────────────────────────────────┐
 │ 2025 Güz  BIL101 Programlamaya Giriş  6  AA 4,00 geçti  │
 └─────────────────────────────────────────────────────────┘
 GNO 2,33   Geçilen AKTS 12
 ┌ Seçili dersin bileşenleri ──┐
 │ Vize 40 → 70   Final 50 → 80│
 └─────────────────────────────┘
```
Veri: `v_transkript`, `v_not_detay` (yalnız ilan edilmiş notlar); GNO: `v_ana_sayfa`.

**Öğretim üyesi modu**
```
 Şube [BIL201-1 ▼]   Bileşenler: Vize 40 | Final 50 | Ödev 10   [Bileşenleri belirle]
 ┌ Öğrenciler ───────────────────────────────────────────────┐
 │ No       Ad Soyad     Vize  Final  Ödev  Durum              │  ← hücreler düzenlenebilir
 └──[ Kaydet ] [ İlan et ] [ Sonuçları hesapla ]───────────────┘
```
Veri: `v_sube_listem`, `v_sube_ogrencileri`, `v_bilesenler`, `v_not_detay`. Eylemler: `fn_bilesenleri_belirle` (tek çağrı; toplam ≠ 100 → `AGIRLIK_TOPLAMI`), `fn_not_gir`, `fn_not_ilan_et`, `fn_sonuclari_hesapla`; ilan sonrası hücre değişince gerekçe soran pencere → `fn_not_duzelt`.

### 2.6 Mezuniyetime Ne Kaldı?

```
 AKTS ████████░░░░ 54/240     GNO 2,80 (en az 2,00)     Mezuniyete uygun: HAYIR
 ┌ Gereksinim grupları ───────────────────────────────────────────────┐
 │ Grup              Tür      Gereken  Sayılan  Durum   Eksik          │
 │ Zorunlu Çekirdek  zorunlu  7 / 42   4 / 24   eksik   BIL201, …      │
 └─────────────────────────────────────────────────────────────────────┘
 En erken mezuniyet: kritik yol 2 dönem · AKTS limitli 2 dönem
 ┌ Ders planı ───────────┐    What-If müfredat [ 2030 ▼ ] [Hesapla]
 │ 1. dönem  BIL201 …    │
 └───────────────────────┘
```
Veri/eylem: `fn_mezuniyet_ozet_ben`, `fn_mezuniyet_denetim_ben(p_mufredat)`, `fn_en_erken_mezuniyet_ben`, `fn_ders_plani_ben`, `v_mufredat_listesi`. What-If seçilince denetim tablosu o müfredata göre yenilenir ve başlıkta "What-If: 2030 müfredatı" görünür.

### 2.7 Danışman paneli

```
 [ Onay kuyruğu ] [ Danışanlarım ]
 ┌ Onay kuyruğu ──────────────────────────────────────────────────────────┐
 │ Öğrenci   Ders     AKTS  Tarih   GNO   [Onayla] [Reddet…] [Düzeltme iste]│
 └──────────────────────────────────────────────────────────────────────────┘
 ┌ Danışanlarım ─────────────────────────────┐ ┌ Seçili danışan ─────────────┐
 │ Öğrenci  GNO  AKTS  Bayrak  Risk          │ │ Bayraklar: GNO_ESIK_ALTI …  │
 └───────────────────────────────────────────┘ │ Skor 0,72 · en etkili 3 neden│
                                               └──────────────────────────────┘
```
Veri: `v_onay_kuyrugu`, `v_danisanlarim`, `v_danisan_bayraklari`, `v_danisan_risk`. Eylem: `fn_danisman_karar_ben`; **Reddet** ve **Düzeltme iste** gerekçe penceresi açar (boşsa gönderme).

### 2.8 Yönetim / Demo (sekreter, yönetici)

Sekmeler: **Dönem & Şube** · **Danışman Atama** · **Parametreler** · **Denetim Logu** · **Risk** · **Demo**

- **Dönem & Şube (sekreter):** dönem aç, şube aç, ders saati ekle (formlar → `fn_donem_ac`, `fn_sube_ac`, `fn_sube_saat_ekle`).
- **Danışman Atama:** öğrenci + danışman + başlangıç tarihi → `fn_danisman_ata`.
- **Parametreler (yönetici):** tablo + düzenle → `fn_parametre_guncelle`.
- **Denetim Logu (yönetici):** `v_denetim_log` + tablo filtresi + **Zinciri doğrula** (`fn_denetim_dogrula` → "Sağlam" / "Bozuk: log_id").
- **Risk:** **Bayrakları yenile** (`fn_risk_bayrak_hesapla`), **Skorları yenile** (Python modülü, `UYGULAMA_PLANI.md` E9) ve sonuç sayısı.
- **Demo:** dört kart.

```
 ┌ AKTS yarışı ──────────────────────────────────────────┐   ┌ Kilitlenme ────────────────┐
 │ Kilit: (•) kapalı ( ) açık  [Hazırla] [Çalıştır]      │   │ [Çalıştır] [Düzeltilmiş]   │
 │ Bağlantı   Sonuç                  Süre                │   │ A  deadlock detected       │
 │ A          KESİNLEŞTİ             0,02 s              │   │ B  tamam                   │
 │ B          KESİNLEŞTİ             0,02 s              │   └────────────────────────────┘
 │ Dönemlik AKTS: 36 / sınır 30  → İHLAL                 │   ┌ Geri alma ─────────────────┐
 └───────────────────────────────────────────────────────┘   │ [Notu sil] → silinenler    │
 ┌ İndeks öncesi/sonrası ────────────────────────────────┐   │ liste → [Geri al] → zincir │
 │ Sorgu [sube_listesi ▼] [Planı göster]                 │   └────────────────────────────┘
 │ Düğüm tipi    Süre (ms)   Okunan blok                 │
 │ [İndeksi bırak] [İndeksi oluştur]  [Yedek al…]        │
 └───────────────────────────────────────────────────────┘
```
Yarış ve kilitlenme kartları iki **ayrı bağlantı** açar (iki `Is`). İndeks kartı yalnızca beyaz listedeki `ix_kayit_sube` üzerinde çalışır. Yedek: `pg_dump` alt süreci, çıktı metin kutusuna akar (terminal penceresi açılmaz).
