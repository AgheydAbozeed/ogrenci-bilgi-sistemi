# Uygulama Planı — Kalan Aşamalar (A–H)

Bu belge, bitmiş çekirdeğin (`sql/001–004`, `tests/001–002`) üzerine kalan işleri **kendi başına uygulayabilmen** için her aşamayı tanımlar: Girdi → Yapılacaklar → Çıktı → Kabul → Tuzaklar. Zaman tahmini yok; boyut: **S** küçük, **M** orta, **L** büyük.

Doğrulanmış başlangıç kodu: `sql/iskeletler.sql` ve `sql/iskelet_rls.sql` (PostgreSQL 16'da çalıştırıldı, iki kez çalıştırılabilir, 62 testi bozmuyor). Ekran ve fonksiyon ayrıntıları: `VERITABANI_API_VE_EKRANLAR.md`. Rapor: `RAPOR_ISKELETI.md`.

## 0. Sıra ve bağımlılık

```
A Risk bayrakları ──┐
B DB API + yetki ───┼──► F PySide6 uygulaması ──► G Paketleme ──► H Kabul / sunum
C Büyük veri ──► D Demo fonksiyonları ─┤
C ──► E AI (OULAD) ────────────────────┘
```

**Önerilen sıra:** A → B (önce Z öncelikli fonksiyonlar) → F (giriş + ders seçimi ile ilk çalışan dilim) → C → D → E → F (kalan ekranlar) → G → H → rapor.

**Kurallar:**
- Her aşamadan sonra o aşamanın testini yaz ve eski 62 testi tekrar çalıştır.
- Testler küçük örnek veriye (`003`) dayanır: testleri ayrı bir `obs_test` veritabanında tut, büyük veriyi `obs`'ye yükle.
- Her aşamanın sonunda `main`'e yükle (GitHub'da dal/PR şart değil).

---

## Aşama A — Risk bayrakları (SQL) · S

**Girdi:** `iskeletler.sql` (`fn_risk_bayrak_hesapla` — 2 kural hazır).

**Yapılacaklar:**
1. Parametreleri ekle: `risk_akts_oran` (22), `risk_devamsizlik_oran` (0.8), `risk_birakma_adet` (2); `risk_kural`'a 4 kural ekle.
2. Dört kuralı `fn_risk_bayrak_hesapla`'ya ekle (her biri `ON CONFLICT DO NOTHING`):

| Kod | Şiddet | Mantık |
|---|---|---|
| `AKTS_GERIDE` | 1 | `v_gno.gecilen_akts` / sonuçlanmış dönem sayısı < `risk_akts_oran` (sonuçlanmış dönem: `kayit_sonuc`'u olan kayıtların farklı `donem_id` sayısı; `NULLIF` ile sıfıra bölmeyi engelle) |
| `DEVAMSIZLIK` | 2 | Bu dönem onaylı kayıtta devamsızlık yüzdesi ≥ `devamsizlik_siniri_yuzde` × `risk_devamsizlik_oran` (`yoklama`: `avg((NOT katildi)::int) * 100`) |
| `ONKOSUL_BLOKAJI` | 1 | Zorunlu ders X geçilmemiş ve X'in önkoşulu ya başarısız ya da `min_harf` katsayısının altında (`fn_ders_plani`'ndaki "gerekli" CTE'siyle aynı mantık) |
| `DERS_BIRAKMA` | 1 | Seçilen dönem dahil son 2 dönemde `durum = 'birakti'` sayısı ≥ `risk_birakma_adet` |

3. `v_risk_ozet` görünümü: öğrenci başına bayrak sayısı, en yüksek şiddet, bayrak kodları listesi (`string_agg`).

**Çıktı:** `sql/005_risk.sql`, `tests/003_risk_testleri.sql`.

**Test senaryoları (her kural için "çıkar" ve "çıkmaz"):**
- GNO tam eşikteyse bayrak yok (karşılaştırma `<`).
- Bora'nın MAT101 FF'si `ZORUNLU_FF` üretir; bu dönem MAT101'e `sepet` kaydı açılınca bayrak kalkar.
- Eşiği `parametre`'den değiştirince sonuç değişir.
- Fonksiyonu iki kez çalıştırınca aynı sayı (idempotent).

**Kabul:** 62 eski test + yeni testler geçer; sonuçsuz öğrenci (GNO NULL) için hata ve bayrak yok.

**Tuzak:** `AKTS_GERIDE` eşiği (22) gerçek müfredat içindir; örnek veride dönem başına 6–12 AKTS olduğundan herkes bayraklanır, testte eşiği düşür.

---

## Aşama B — DB API ve yetki (SQL) · L

**Girdi:** `VERITABANI_API_VE_EKRANLAR.md` §1 (görünüm/fonksiyon listesi, RLS matrisi), `iskelet_rls.sql`, `iskeletler.sql` (`fn_sepete_ekle`).

**İlke:** **Okuma = `security_invoker` görünüm (RLS otomatik süzer); yazma = `SECURITY DEFINER` fonksiyon (kimlik `app.kullanici_id` oturum değişkeninden).** Öğrencilere tablolarda doğrudan INSERT/UPDATE yetkisi verilmez.

**Yapılacaklar (sırayla):**
1. Roller: tablo sahibi (süper kullanıcı ya da `obs_admin`), uygulama girişi `obs_app` (süper kullanıcı ve tablo sahibi **olmayan**), grup rolleri `rol_*` (`iskelet_rls.sql` hazır). Giriş ekranı için ayrı kısıtlı rol `obs_login`: yalnızca `v_demo_kullanicilar` SELECT.
2. Her tabloda `ENABLE ROW LEVEL SECURITY` + SELECT politikaları (RLS matrisi; kalıp `iskelet_rls.sql`'de).
3. Kullanıcıya gösterilen her görünümü `WITH (security_invoker = true)` ile oluştur. Varsayılan görünümler sahibin yetkisiyle çalışır ve RLS'yi **atlar** (denendi: varsayılan görünüm 7 satır, `security_invoker` görünüm 4 satır gösterdi).
4. `fn_denetim`'i güncelle: log'a `coalesce(nullif(current_setting('app.kullanici_id', true), ''), current_user)` yaz (SECURITY DEFINER içinde `current_user` sahip olur, gerçek kullanıcı kaybolur). `app.gerekce` oturum değişkeni doluysa JSON'a `_gerekce` ekle (ilan sonrası not düzeltme gerekçesi için).
5. API fonksiyonlarını yaz: önce **Z**, sonra **F** (`VERITABANI_API_VE_EKRANLAR.md` §1.3).
6. `REVOKE ALL ON FUNCTION ... FROM PUBLIC`; `GRANT EXECUTE` yalnızca ilgili rollere.
7. **Kural eksiği:** `fn_kayit_kurallar`'ın INSERT dalına müfredat denetimi ekle (`MUFREDAT_DISI`): ders, öğrencinin `mufredat_id`'siyle `mufredat_ders`'te yoksa reddet. Test: Ada, müfredatında olmayan bir dersi sepete ekleyemez.

**Çıktı:** `sql/006_api.sql`, `sql/007_yetki.sql`, `tests/004_api_testleri.sql`, `tests/005_yetki_testleri.sql`.

**Kabul:**
- Öğrenci başkasının kaydını, notunu ve risk verisini göremez (0 satır).
- Danışman yalnız danışanlarını, öğretim üyesi yalnız kendi şubelerini görür; sekreter/yönetici tümünü; `denetim_log` yalnız yönetici.
- Kimlik yokken her API `YETKISIZ` verir.
- Her API işlemi denetim logunda kullanıcı kimliğiyle görünür.
- Tüm eski testler geçer.

**Tuzaklar:**
1. Süper kullanıcı ve tablo sahibi RLS'yi atlar — uygulama `obs_app` ile bağlanmalı.
2. Bir kişi hem danışman hem öğretim üyesi olabilir: uygulama işlem başına tek rol seçer (`SET LOCAL ROLE`, rol adı sabit listeden).
3. `SECURITY DEFINER` fonksiyonlarda `SET search_path = public` şart.
4. `current_setting(..., true)` + `nullif` kullan, yoksa kimlik boşken ham hata çıkar.
5. Politikalar alt sorguda başka tabloyu okur (`danismanlik`, `sube`): o role o tabloda SELECT yetkisi gerekir.

---

## Aşama C — Büyük sentetik veri (Python) · M

Amaç: indeks/optimizasyon demosu ve AI için hacim. Bu bir geliştirici betiğidir (uygulamanın parçası değil, terminal kullanabilirsin).

**Girdi:** 001–004 yüklü boş şema (parametreler ve `harf_notu_aralik` dolu).

**Yapılacaklar:** `veri/uretici.py`
- Parametreler: profil `kucuk` (≈2.000 öğrenci, 8 dönem) / `buyuk` (≈30.000 öğrenci → ≈1,4 M `kayit`, ≈4 M `not_kaydi`); `--tohum` (aynı tohum aynı veri).
- Yapı: 2 program × ~40 ders (önkoşullar DAG, 8 yarıyıl, 1 seçmeli havuzu), `sube_saat` 12 dilim, dönem başına ders başına 1–2 şube.
- Yükleme sırası: parametre → bolum/program/mufredat → ders/mufredat_ders/onkosul/gereksinim → donem (8) → kisi/ogretim_uyesi/ogrenci → danismanlik → sube/sube_saat → kayit → degerlendirme_bileseni → not_kaydi → kayit_sonuc → yoklama (yalnız son 2 dönem).
- Teknik: süper kullanıcı + `SET session_replication_role = replica` + psycopg `cursor.copy` (COPY). `kayit.ders_id/donem_id` elle doldurulur (BEFORE INSERT tetikleyici replica modunda çalışmaz). Yükleme sonunda `setval` ile `serial` dizilerini güncelle. `ux_kayit_aktif` ve `ix_*` indekslerini büyük yüklemeden sonra oluştur.
- Dağılımlar: GNO çan eğrisi (ort. 2,6; sd 0,6; [0,4]'e kırp), başarısızlık %12–18, ders bırakma %3, dönemde 5–7 ders, AKTS limitine uy, çakışmasız slotlar. AI hazırsa not/yoklama değerlerini OULAD özellik dağılımlarından örnekle (E10).

**Çıktı:** `veri/uretici.py`, `veri/README.md`, satır sayıları tablosu.

**Kabul:** aynı `--tohum` aynı satır sayılarını verir; `fn_gno` ve `fn_mezuniyet_denetim` rastgele 20 öğrencide hatasız çalışır; yetim satır yok (FK zaten korur, yine de say).

**Tuzaklar:** replica modunda tetikleyiciler (slot, denetim logu) çalışmaz: büyük veri "geçmiş" sayılır, `ogrenci_slot` ve `denetim_log` boş kalır (sorun değil). Güncel dönemin küçük bir alt kümesini normal (tetikleyicili) yükle ki uygulama canlı veriyle çalışsın.

---

## Aşama D — Demo fonksiyonları (SQL) · S

**Girdi:** `iskeletler.sql` (kilitlenme, geri alma, explain hazır).

**Yapılacaklar:**
1. **AKTS yarışı:** `fn_demo_akts_hazirla()` (Bora'nın 4 dersini kesinleştirir, 2 dersi `sepet`'te bırakır, iki `kayit_id` döndürür); `fn_demo_akts_kilidi(p_deger text)` ('acik' / 'kapali', yalnız yönetici; `parametre.akts_kilidi`'ni günceller).
2. **Kilitlenme:** `fn_demo_kilitlenme` ve `_duzeltilmis` (hazır). Uygulama iki **ayrı bağlantıdan** (A,B) ve (B,A) sırasıyla çağırır.
3. **Geri alma:** `fn_demo_not_sil(p_kayit int)` (kaza simülasyonu, yönetici); `v_silinen_notlar` (`denetim_log`'dan `islem = 'D'`, `tablo = 'not_kaydi'`); `fn_not_geri_al(log_id)` (hazır).
4. **İndeks:** `fn_demo_indeks(p_islem text)` — yalnızca `ix_kayit_sube` için 'birak' (`DROP INDEX`) / 'olustur' (`CREATE INDEX`); `SECURITY DEFINER`, beyaz liste. `fn_demo_explain(kod)` hazır; uygulama JSON plandan `Node Type`, `Actual Total Time`, `Shared Hit Blocks` / `Shared Read Blocks` çıkarır.

**Çıktı:** `sql/008_demo.sql`. Kilitlenme iki oturum gerektirir; Demo sayfasında doğrulanır. Yarış için `tests/001`'deki AKTS testi yeterli.

**Kabul (hepsi sandbox'ta denendi, büyük veri hariç):**
- Kilit kapalıyken iki eşzamanlı kesinleştirme dönemlik AKTS'yi aşar (36 > 30), açıkken biri `AKTS_ASIMI` alır (30).
- Kilitlenmede bir işlem `deadlock detected` alır; düzeltilmişte ikisi de `tamam`.
- Silinen not log'dan geri gelir ve hash zinciri sağlam kalır.
- Büyük veride indeksiz plan `Seq Scan`, indeksli plan `Index Scan`/`Bitmap` (düğüm tipi ve süre farkı tabloda).

**Tuzak:** Kilitlenme için iki işlem **farklı bağlantılarda** olmalı. PostgreSQL kilitlenmeyi `deadlock_timeout` (varsayılan 1 sn) sonra tespit eder; `p_bekle` ≥ 1 yap.

---

## Aşama E — AI risk skoru (Python) · L

**Girdi:** Aşama C verisi (opsiyonel ama önerilir), `v_risk_ozellik` (hazır), OULAD.

**E1 Veri:** OULAD'ı Open University'nin veri sayfasından indir (`https://research.stem.open.ac.uk/ouanalyse/dataset/`; indirme bağlantısı ve MD5 sayfada), `data/oulad/` altına aç (git'e girmez). Lisans CC BY 4.0: raporda atıf ver (Kuzilek, Hlosta ve Zdrahal, 2017, *Scientific Data*). Bu dosyayı ben indiremiyorum (ağ izinleri).

**E2 Tablolar:** `studentInfo`, `studentRegistration`, `assessments`, `studentAssessment`, `studentVle`, `courses`, `vle`. `studentVle` büyüktür: parça parça (chunk) oku, yalnız `date ≤ N` olanı gün bazında topla.

**E3 Özellikler** (kesme günü N = 60; OULAD günleri dönem başına göredir ve negatif olabilir):

| SIS özelliği (`v_risk_ozellik`) | OULAD karşılığı |
|---|---|
| `onceki_deneme` | `studentInfo.num_of_prev_attempts` |
| `alinan_kredi` | `studentInfo.studied_credits` |
| `kayit_gunu` | `studentRegistration.date_registration` |
| `ort_puan` | `avg(studentAssessment.score)` — `assessments.date ≤ N` olan değerlendirmeler |
| `eksik_oran` | 1 − (N gününe kadar teslim edilen / planlanan değerlendirme sayısı) |
| `katilim_orani` | (≤ N gününde en az 1 tıklaması olan gün sayısı) / (N + 1) — yoklama için **vekil** özellik |

Eksik değer: `ort_puan` yoksa modül ortalamasıyla doldur + `ilk_not_yok` bayrağı.

**E4 Etiket:** `final_result ∈ {Fail, Withdrawn}` → 1; `Pass`, `Distinction` → 0 (değerleri `value_counts()` ile kontrol et). `date_unregistration ≤ N` olan satırları eğitimden **çıkar** (sonuç kesme gününden önce belli, sızıntı olur).

**E5 Bölme:** eğitim `2013*`, test `2014*` sunumları (`code_presentation`); aynı öğrenci iki kümede yer almasın.

**E6 Model:** eksik değer + standartlaştırma → `LogisticRegression(class_weight='balanced', max_iter=1000)`; karşılaştırma için `HistGradientBoostingClassifier`. Metrikler: ROC-AUC, PR-AUC, ilk %10'daki isabet (danışman kapasitesi sınırlı), temel çizgi (yalnız `onceki_deneme`).

**E7 Açıklama:** lojistik katsayı × standartlaştırılmış değer → en etkili 3 katkı → `risk_tahmin.ozellikler = {"ozellikler": {...}, "katkilar": {...}}`.

**E8 Kaydet:** `modeller/risk_v1.joblib` (model, ölçekleyici, özellik listesi, metrikler; git'e girmez); metrikler `model_surum.metrikler` JSONB'a yazılır.

**E9 Puanlama:** `ai/puanla.py` `v_risk_ozellik`'i dönem filtresiyle okur → aynı ön işleme → skor (0–1) → öğrenci bazında `max(skor)` → `risk_tahmin` upsert (`model_id`, `ozellikler`). **Uygulamadaki "Skorları yenile" butonu bu modülü içe aktarıp iş parçacığında çalıştırır (terminal yok).**

**E10 Sentetik SIS tutarlılığı:** Aşama C'de notlar OULAD dağılımlarından örneklenirse skorlar anlamlı çıkar. Raporda şu ayrımı yap: **gerçek doğrulama OULAD test kümesinde; SIS'teki skorlar sentetik veriye uygulanmış bir gösterim.**

**E11 Adalet:** `gender`, `region`, `highest_education`, `imd_band`, `age_band`, `disability` özellik olarak **kullanılmaz**; (opsiyonel) test kümesinde grup bazlı hata oranlarını raporla.

**E12 Sınırlılıklar:** vekil özellikler (tıklama ≠ yoklama), tek kurum verisi, model başka kuruma taşınmayabilir (Marist'in OAAI çalışması bunu inceledi), skor karar vermez.

**Çıktı:** `ai/ozellik.py`, `ai/egit.py`, `ai/puanla.py`, `modeller/`, rapor bölümü.

**Kabul:** test AUC'si raporlanır (sonuç ne olursa dürüstçe); aynı girdiyle aynı skor (tohum sabit); `risk_tahmin` satırlarında `model_id` ve `ozellikler` dolu; skor ∈ [0, 1].

**Tuzaklar:** sızıntı (kesme gününden sonraki bilgi), öğrenci bazlı bölme, eşiği 0,5'e sabitleme (ilk %10 yaklaşımı daha anlamlı), OULAD tarihlerinin dönem başına göre olması.

---

## Aşama F — PySide6 uygulaması · L

**Girdi:** `VERITABANI_API_VE_EKRANLAR.md` §2 (ekranlar), Aşama B API'si.

**F1 Klasör yapısı**
```
app/  main.py  config.py  db.py  hatalar.py  modeller.py  stil.qss
      ekranlar/    giris.py  ana_sayfa.py  ders_secimi.py  notlar.py  mezuniyet.py  danisman.py  yonetim_demo.py
      bilesenler/  haftalik_program.py  ilerleme_karti.py
```

**F2 `config.py`:** `.env` okur (`python-dotenv`); paketlenmiş uygulamada yol `Path(sys.executable).parent / ".env"`. Ayarlar: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

**F3 `db.py` iskeleti** (sözdizimi denetlendi; PySide6 ile çalıştırılmadı):
```python
import os
import psycopg
from PySide6.QtCore import QObject, QRunnable, Signal

ROLLER = {"rol_ogrenci", "rol_danisman", "rol_ogretim_uyesi", "rol_sekreter", "rol_yonetici"}  # sabit liste

def baglan():
    return psycopg.connect(host=os.environ["DB_HOST"], port=os.environ.get("DB_PORT", "5432"),
                           dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
                           password=os.environ["DB_PASSWORD"])

class Sinyaller(QObject):
    bitti = Signal(object)      # satır listesi ya da None
    hata = Signal(str, str)     # (kod, mesaj)

class Is(QRunnable):
    """Her iş kendi bağlantısını açar; arayüze yalnızca sinyalle döner."""
    def __init__(self, sorgu, parametreler=(), kullanici_id=None, rol=None):
        super().__init__()
        self.sorgu, self.parametreler = sorgu, parametreler
        self.kullanici_id, self.rol = kullanici_id, rol
        self.sinyal = Sinyaller()

    def run(self):
        try:
            with baglan() as conn, conn.transaction():
                if self.rol:
                    assert self.rol in ROLLER
                    conn.execute(f"SET LOCAL ROLE {self.rol}")
                if self.kullanici_id is not None:
                    conn.execute("SELECT set_config('app.kullanici_id', %s, true)", (str(self.kullanici_id),))
                cur = conn.execute(self.sorgu, self.parametreler)
                sonuc = cur.fetchall() if cur.description else None
            self.sinyal.bitti.emit(sonuc)
        except psycopg.Error as e:
            mesaj = e.diag.message_primary or str(e)
            kod = mesaj.split(":")[0] if ":" in mesaj else (e.sqlstate or "HATA")
            self.sinyal.hata.emit(kod, mesaj)
```
Kullanım: `QThreadPool.globalInstance().start(is_)`; sonuç `is_.sinyal.bitti.connect(...)`. Yinelenen anahtar gibi `RAISE EXCEPTION` olmayan hatalarda (`ux_kayit_aktif`, CHECK) kod yerine `mesaj` içinde arama yap (`hatalar.py`).

**F4 `hatalar.py`:** hata kodu → Türkçe mesaj sözlüğü (`VERITABANI_API_VE_EKRANLAR.md` §1.5); bilinmeyen kod → "Beklenmeyen hata" + "Ayrıntı" düğmesi.

**F5 `modeller.py`:** genel `TabloModeli(QAbstractTableModel)` (sütun adları + satırlar); sıralama için `QSortFilterProxyModel`.

**F6 Sıra:** (1) config + db + hatalar → (2) main + giriş → (3) ders_secimi (en kritik) → (4) danisman → (5) notlar → (6) ana_sayfa → (7) mezuniyet → (8) yonetim_demo. Her ekrandan sonra elle test (Aşama H listesi).

**F7 Demo sayfası** (terminalsiz):
- **AKTS yarışı:** iki `Is` aynı anda `fn_kesinlestir`; sonuç tablosu (bağlantı, sonuç, süre); kilit anahtarı (açık/kapalı).
- **Kilitlenme:** (A,B) ve (B,A) iki bağlantı; hata `psycopg.errors.DeadlockDetected` → Türkçe mesaj; "düzeltilmiş" düğmesi.
- **Geri alma:** not sil → `v_silinen_notlar`'da görünür → "Geri al".
- **İndeks:** `fn_demo_explain` sonuçları tabloda (düğüm tipi, süre, buffers) + "İndeksi bırak / oluştur".
- **Yedek (opsiyonel):** `subprocess.run(["pg_dump", "-Fc", ...], creationflags=subprocess.CREATE_NO_WINDOW)` (Windows; diğer sistemlerde bayrak gerekmez), çıktı bir metin kutusuna akar, terminal penceresi açılmaz.

**F8 Stil:** tek `stil.qss`: kartlar, sol menü, tablo başlıkları.

**Kabul:** ekranlar yalnız DB API'sini çağırır (arayüzde iş kuralı yok); hata kodları Türkçe mesaja döner; uzun işler arayüzü dondurmaz; 6 ekranın hepsi Aşama H listesinden geçer.

**Tuzaklar:**
1. İş parçacığından arayüze doğrudan dokunma (sinyal kullan).
2. Bağlantıyı iş parçacıkları arasında paylaşma (her `Is` kendi bağlantısı).
3. `SET LOCAL ROLE` adını kullanıcı girdisinden alma (sabit liste).
4. Qt'nin QtSql PostgreSQL sürücüsünü kullanma (paketlemede "driver not loaded" sorunu); `psycopg[binary]` kullan.

---

## Aşama G — Paketleme · S

1. `pip install pyinstaller`; `pyinstaller --noconfirm --windowed --name OBS --add-data "app/stil.qss;." app/main.py` (macOS/Linux'ta `;` yerine `:`).
2. Çalışmazsa: `--collect-all psycopg --collect-all psycopg_binary` ekle.
3. `.env` exe'nin yanına konur; yoksa uygulama "Bağlantı ayarı bulunamadı" kutusu gösterir.
4. Temiz bir bilgisayarda ya da yeni kullanıcı hesabında dene: yalnızca PostgreSQL kurulu olmalı.
5. `KURULUM.md`: PostgreSQL kurulumu → `createdb` → 001–004 (+ 005–008) sırayla → örnek veri → `.env` → uygulama.
6. Yedek plan: Windows'ta `main.pyw` (konsolsuz) başlatıcı.

**Kabul:** çift tıkla açılır, terminal penceresi görünmez, veritabanı bağlantı hatasında anlaşılır mesaj verir.

**Not:** PyInstaller çıktısı işletim sistemine özgüdür: demo hangi bilgisayarda yapılacaksa orada derle.

---

## Aşama H — Kabul testi ve sunum akışı · S

**Demo senaryosu (sırayla):**
1. Giriş: Ada → ders seçimi: `BIL201` → "önkoşul eksik"; `BIL101` + `MAT101` sepete → Kontrol Et + Kesinleştir.
2. Giriş: Deniz Hoca (danışman) → onay kuyruğu → Ada'nın kaydını onayla; bir kaydı gerekçesiz reddetmeyi dene (hata), gerekçeyle reddet.
3. Giriş: öğretim üyesi → şube → bileşenleri belirle (tek çağrıda; 40 + 50 → `AGIRLIK_TOPLAMI` hatası, 40 + 50 + 10 kabul) → not gir → ilan et → sonuçları hesapla.
4. Öğrenci: notlar/transkript → GNO → Mezuniyetime Ne Kaldı? → What-If → en erken mezuniyet.
5. Danışman paneli: riskli danışanlar → bayraklar + skor + en etkili 3 neden.
6. Yönetim/Demo: AKTS yarışı (kilit kapalı → aşar; açık → engellenir), kilitlenme ve çözümü, silinen notu geri alma, indeks öncesi/sonrası.
7. Denetim logu: hash zincirini doğrula; log oynamayı dene (hata).

**Kontrol listesi:** her ekranda boş durum (veri yok) ve hata durumu görüldü; her hata kodu Türkçe mesaj veriyor; 62+ test geçiyor; `KURULUM.md`'deki adımlarla temiz kurulum çalışıyor; uygulama ilk açılışta terminal penceresi göstermiyor.

---

## Kesme sırası (zaman daralırsa)

1. LLM danışman, tahmini not, anomali tespiti — zaten opsiyonel.
2. AI skoru → yalnız SQL bayrakları kalsın (A); panelde "skor yok" yaz.
3. RLS politikaları → API fonksiyonlarındaki kimlik kontrolleri (`YETKISIZ`) kalsın.
4. Yedekten dönüş demosu → log tabanlı geri alma yeterli.
5. Paketleme → `main.pyw` başlatıcı.

**Asla kesme:** B'nin Z fonksiyonları; F'de ders seçimi + danışman onayı + notlar; D'de AKTS yarışı ve kilitlenme.

## Dosya durumu

| Dosya | Durum |
|---|---|
| `sql/001_sema.sql`, `002_kurallar.sql`, `003_ornek_veri.sql`, `004_mezuniyet.sql` | ✔ hazır, testli |
| `tests/001_testler.sql` (42), `tests/002_mezuniyet_testleri.sql` (20) | ✔ hazır |
| `sql/iskeletler.sql`, `sql/iskelet_rls.sql` | ◐ doğrulanmış iskelet |
| `sql/005_risk.sql` … `008_demo.sql`, `tests/003–005` | ✎ yapılacak (A, B, D) |
| `veri/uretici.py` | ✎ yapılacak (C) |
| `ai/*.py`, `modeller/` | ✎ yapılacak (E) |
| `app/` | ✎ yapılacak (F) |
| `KURULUM.md`, rapor | ✎ yapılacak (G, H) |
