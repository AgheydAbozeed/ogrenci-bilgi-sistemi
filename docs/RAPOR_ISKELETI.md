# Rapor İskeleti (ders haftalarıyla)

Her bölüm: hafta konusu → içerik → kaynak dosya → toplanacak çıktı. Normalizasyon, ilişkisel cebir/hesap, hareket ve savunma soruları **ön doldurulmuştur**: kendi cümlelerinle yeniden yaz ve anlayarak savun. Hocanın yapay zekâ yardımı politikasına uy.

**Raporu aşama aşama yaz:** bir aşamayı bitirince o bölümü yaz ve çıktıyı (ekran görüntüsü, test çıktısı) hemen kaydet.

## Bölüm planı

| # | Bölüm | Hafta | Kaynak dosya | Toplanacak çıktı |
|---|---|---|---|---|
| 1 | Amaç, kapsam, benzer sistemler | 1 | `TASARIM.md` §1–2 | benzer sistemler tablosu, kaynakça |
| 2 | Gereksinimler ve iş kuralları | — | `TASARIM.md` §5, `002_kurallar.sql` | kural → mekanizma tablosu |
| 3 | Dosya organizasyonu, fiziksel depolama | 2 | Aşama D (indeks) | boyut ve plan tabloları |
| 4 | ER/EER modeli | 3 | `TASARIM.md` §4.1 | ER diyagramı (PNG) |
| 5 | İlişkisel model, şema, kısıtlar | 4, 8 | `001_sema.sql` | kısıt kataloğu (`TASARIM.md` §4.3) |
| 6 | İlişkisel cebir ve hesap | 5–6 | bu belge §6 | 6 sorgu, üç dilde |
| 7 | SQL: view, fonksiyon, tetikleyici | 7 | `002`, `004` | nesne listesi, test çıktıları |
| 8 | Normal formlar | 10 | bu belge §8 | FD tablosu |
| 9 | Nesne-ilişkisel özellikler | 11 | bu belge §9 | örnek sorgular |
| 10 | Sorgu eniyileme | 12 | Aşama D | önce/sonra planları |
| 11 | Hareket, eşzamanlılık, kilitlenme | 12–14 | bu belge §11 | demo çıktıları, zaman çizelgeleri |
| 12 | Kurtarma | 15 | bu belge §12 | geri alma çıktıları |
| 13 | Güvenlik ve KVKK | — | `007_yetki.sql` | RLS sınama çıktıları |
| 14 | AI katmanı | — | `UYGULAMA_PLANI.md` Aşama E | metrik tablosu |
| 15 | Sonuç, sınırlılıklar, genişleme | — | `VERITABANI_API_VE_EKRANLAR.md` §1.6 | — |

---

## §3 Dosya organizasyonu (2. hafta)

**Ölç ve yaz:**
- `SELECT pg_size_pretty(pg_relation_size('kayit')), pg_size_pretty(pg_indexes_size('kayit')), pg_size_pretty(pg_total_relation_size('kayit'));` (ve `not_kaydi`) → büyük veride tablo ve indeks boyutları. PostgreSQL tabloyu 8 kB'lık sayfalarda (heap) tutar; indeksler B-tree'dir.
- `ix_kayit_sube`'yi bırakıp/oluşturarak indeks boyutunun maliyetini göster.
- İsteğe bağlı: `CLUSTER kayit USING ix_kayit_ogrenci;` sonrası aynı öğrencinin kayıtlarının yan yana düşmesinin plan/süre etkisi; `ALTER TABLE kayit SET (fillfactor = 70)` ile güncelleme davranışı.
- Teorik bağlantı: yığın (heap) dosyası, sıralı dosya, karma (hash), B+ ağacı; hangisi nerede kullanıldı.

## §6 İlişkisel cebir ve hesap (5–6. hafta)

Gösterim: σ seçme, π izdüşüm, ⋈ birleştirme, ρ yeniden adlandırma, ∪ birleşim, − fark, ÷ bölme, γ toplulaştırma.

| # | Soru | İlişkisel cebir | Tuple ilişkisel hesabı | SQL |
|---|---|---|---|---|
| Q1 | 2025001 numaralı öğrencinin geçtiği derslerin kodu ve harf notu | π_{kod, harf}( σ_{ogrenci_no='2025001' ∧ durum='gecti'}( OGRENCI ⋈ KAYIT ⋈ KAYIT_SONUC ⋈ DERS ) ) | { t \| ∃o∈OGRENCI ∃k∈KAYIT ∃s∈KAYIT_SONUC ∃d∈DERS ( o.ogrenci_no='2025001' ∧ k.ogrenci_id=o.kisi_id ∧ s.kayit_id=k.kayit_id ∧ s.durum='gecti' ∧ d.ders_id=k.ders_id ∧ t.kod=d.kod ∧ t.harf=s.harf ) } | `v_transkript` filtresi |
| Q2 | Hiç FF almamış öğrenciler | π_{kisi_id}(OGRENCI) − π_{ogrenci_id}( σ_{harf='FF'}( KAYIT ⋈ KAYIT_SONUC ) ) | { o.kisi_id \| o∈OGRENCI ∧ ¬∃k∈KAYIT ∃s∈KAYIT_SONUC ( k.ogrenci_id=o.kisi_id ∧ s.kayit_id=k.kayit_id ∧ s.harf='FF' ) } | `NOT EXISTS` |
| Q3 | Tüm zorunlu derslerini geçmiş öğrenciler | Gecilen(ogrenci_id, ders_id) ÷ Zorunlu(ders_id) (tek müfredat için) | { o.kisi_id \| o∈OGRENCI ∧ ∀z∈MUFREDAT_DERS ( z.mufredat_id=o.mufredat_id ∧ z.tur='zorunlu' → ∃g∈GECILEN ( g.ogrenci_id=o.kisi_id ∧ g.ders_id=z.ders_id ) ) } | çift `NOT EXISTS` (mezuniyet denetiminin çekirdeği) |
| Q4 | BIL201 ya da BIL202 alan öğrenciler | π_{ogrenci_id}(σ_{kod='BIL201'}(KAYIT ⋈ DERS)) ∪ π_{ogrenci_id}(σ_{kod='BIL202'}(KAYIT ⋈ DERS)) | { t \| ∃k∈KAYIT ∃d∈DERS ( d.ders_id=k.ders_id ∧ d.kod∈{'BIL201','BIL202'} ∧ t.ogrenci_id=k.ogrenci_id ) } | `UNION` ya da `IN` |
| Q5 | BIL102'nin doğrudan önkoşulları (kendine birleştirme) | π_{d2.kod}( σ_{d1.kod='BIL102'}( ρ_{d1}(DERS) ⋈ ONKOSUL ⋈ ρ_{d2}(DERS) ) ) | { t \| ∃d1,d2∈DERS ∃o∈ONKOSUL ( d1.kod='BIL102' ∧ o.ders_id=d1.ders_id ∧ o.onkosul_ders_id=d2.ders_id ∧ t.kod=d2.kod ) } | iki `JOIN` |
| Q6 | Öğrencinin GNO'su (genişletilmiş cebir) | γ_{ogrenci_id; SUM(akts·katsayi)/SUM(akts)}( GECERLI_SONUC ) | — (toplulaştırma temel hesapta yok) | `fn_gno` |

**Kuramsal not (Q5'in devamı):** *dolaylı* önkoşullar (geçişli kapanış) temel ilişkisel cebirle ifade edilemez. SQL:1999 `WITH RECURSIVE` bunu mümkün kılar (`fn_onkosul_dongu`, `fn_ders_plani`).

## §8 Normal formlar (10. hafta)

**FD ve normal form tablosu (ön dolu):**

| Tablo | Anahtar(lar) | Önemli bağımlılıklar | Sonuç |
|---|---|---|---|
| `harf_notu_aralik` | harf | harf → min_puan, katsayi, gecer_mi | BCNF |
| `akts_limit_kural` | kural_id | kural_id → min_gno, max_gno, max_akts (aralıklar çakışmaz) | BCNF |
| `parametre` | anahtar | anahtar → deger, aciklama | BCNF |
| `bolum`, `program`, `mufredat`, `ders` | vekil anahtar + doğal anahtarlar (`ad`, `kod`, `(program_id, giris_yili)`) | anahtarlardan her şey | BCNF |
| `mufredat_ders` | (mufredat_id, ders_id) | → donem_no, tur | BCNF |
| `onkosul` | (ders_id, onkosul_ders_id) | → min_harf | BCNF |
| `gereksinim_grubu`, `gereksinim_grubu_ders` | grup_id; (grup_id, ders_id) | anahtarlardan her şey | BCNF |
| `kisi`, `ogretim_uyesi`, `ogrenci` | kisi_id (+ eposta, ogrenci_no) | anahtarlardan her şey | BCNF |
| `danismanlik` | danismanlik_id | → ogrenci_id, danisman_id, gecerlilik (+ EXCLUDE: aralık çakışmaz) | BCNF |
| `donem`, `sube`, `sube_saat` | donem_id; sube_id ve (ders_id, donem_id, sube_no) | anahtarlardan her şey | BCNF |
| `kayit_onay`, `degerlendirme_bileseni`, `yoklama`, `belge`, `risk_*`, `denetim_log` | vekil/bileşik anahtarlar | anahtarlardan her şey | BCNF |
| **`kayit`** | kayit_id | kayit_id → sube_id → (ders_id, donem_id) | 2NF; **3NF ihlali (bilinçli)** |
| **`not_kaydi`** | (kayit_id, bilesen_id) | kayit_id → sube_id (anahtarın parçası) | 1NF; **2NF ihlali (bilinçli)** |
| **`kayit_sonuc`** | kayit_id | ortalama_puan → harf (parametre tablosu üzerinden) | **hesaplanmış nitelik (bilinçli)** |
| **`ogrenci_slot`** | (ogrenci_id, donem_id, gun, ders_saati) | kayit_id → ogrenci_id, donem_id | **türetilmiş yardımcı tablo (bilinçli)** |

**Bilinçli denormalizasyonlar ve gerekçesi (savunmada sorulur):**
- **`kayit.ders_id/donem_id`:** `ux_kayit_aktif` kısmi UNIQUE indeksi "aynı dönem aynı dersin iki aktif şubesi olamaz" kuralını bildirimsel yapabilsin diye. Tutarlılığı bileşik yabancı anahtar `(sube_id, ders_id, donem_id) → sube` garanti eder; değerleri BEFORE INSERT tetikleyici doldurur, uygulama giremez.
- **`not_kaydi.sube_id`:** iki bileşik FK ("kaydın şubesi = bileşenin şubesi") için. Yanlış şubenin bileşenine puan girilmesi veritabanı seviyesinde imkânsız (test edildi).
- **`kayit_sonuc.harf`:** yönetmelik katsayıları değişse bile geçmiş sonuç donmuş kalsın.
- **`ogrenci_slot`:** saat çakışmasını birincil anahtarın yakalaması için türetilir; `kayit` durumuna bağlı tetikleyiciyle senkron tutulur.

**Kötü tablo örneği (rapora koy):** `kayit_genis(ogrenci_no, ogrenci_ad, ders_kodu, ders_adi, akts, hoca_adi, puan)`
- Anahtar: (ogrenci_no, ders_kodu). FD'ler: ogrenci_no → ogrenci_ad; ders_kodu → ders_adi, akts; (ogrenci_no, ders_kodu) → hoca_adi, puan.
- 1NF ✔; **2NF ✗** (ogrenci_ad anahtarın parçasına, ders_adi/akts diğer parçasına bağlı).
- Anomaliler: *ekleme* (öğrenci kaydı olmadan ders eklenemez), *güncelleme* (ders adı değişince çok satır), *silme* (öğrencinin son dersi silinince öğrenci bilgisi kaybolur).
- Ayrıştırma: `ogrenci(ogrenci_no PK, ogrenci_ad)`, `ders(ders_kodu PK, ders_adi, akts)`, `kayit(ogrenci_no, ders_kodu, hoca_adi, puan)` — anahtar tabanlı olduğu için kayıpsız birleşim, FD'ler korunur. Sonraki adım: hoca şubeye bağlıdır → `sube` tablosu.

## §9 Nesne-ilişkisel özellikler (11. hafta)

Kullanılanlar ve nerede:
- **Genelleme:** `kisi` → `ogrenci`, `ogretim_uyesi` (sınıf-tablo yaklaşımı: alt tablonun PK'si üst tabloya FK). PostgreSQL tablo kalıtımı (`INHERITS`) ile karşılaştır: kalıtımda benzersizlik ve yabancı anahtar kısıtları alt tablolara yayılmadığı için seçilmedi.
- **Aralık tipleri:** `daterange` (`danismanlik.gecerlilik`), `numrange` (`akts_limit_kural`) + `EXCLUDE`.
- **`jsonb`:** `denetim_log.eski/yeni`, `risk_tahmin.ozellikler`, `model_surum.metrikler`; `jsonb_populate_record` ile JSON → satır (log tabanlı geri alma).
- **Dizi tipi:** `int[]` (denetim ve plan algoritmalarında).
- **Satır tipi ve tablo döndüren fonksiyonlar:** `denetim_log%ROWTYPE`, `RETURNS TABLE`.

Karşılaştırma tablosu (rapora): OODBMS (nesne kimliği, kalıtım, yöntemler yerleşik) · ORDBMS (ilişkisel + kullanıcı tanımlı tip, kalıtım, fonksiyon; PostgreSQL) · saf ilişkisel. **Python tarafı:** nesne–ilişkisel uyumsuzluğu bilinçli olarak ORM'siz çözüldü: satırlar `TabloModeli` ile gösterilir, iş kuralı veritabanında kaldığı için nesne eşlemesine gerek yok.

## §10 Sorgu eniyileme (12. hafta)

Büyük veride (Aşama C) 5 sorgu: transkript (`ogrenci_no`), şube listesi (`sube_id`), `durum='onayli'` sayımı (düşük seçicilik), önkoşul eksikleri, mezuniyet denetimi.

Ölçüm tablosu şablonu:

| Sorgu | İndeks durumu | Plan düğümü | Süre (ms) | Okunan blok | Yorum |
|---|---|---|---|---|---|
| sube_listesi | `ix_kayit_sube` yok | Seq Scan | | | |
| sube_listesi | `ix_kayit_sube` var | Index/Bitmap Scan | | | |

Adımlar: `ANALYZE` → `EXPLAIN (ANALYZE, BUFFERS)` → indeks ekle/bırak → tekrar ölç. **Mutlaka bir negatif örnek:** `durum='onayli'` satırların büyük kısmını seçer, planlayıcı indeksi kullanmaz. Planlardaki **Nested Loop / Hash Join / Merge Join**'ı hangi sorguda gördüğünü ve nedenini (seçicilik, satır sayısı) yaz.

## §11 Hareket, eşzamanlılık, kilitlenme (12–14. hafta)

**ACID örnekleri:** atomiklik (kayıt + log aynı işlemde), tutarlılık (kısıtlar/tetikleyiciler), yalıtım (aşağıdaki demolar), dayanıklılık (WAL, §12).

**Yalıtım düzeyleri (PostgreSQL):** READ COMMITTED (varsayılan; her ifade yeni anlık görüntü görür), REPEATABLE READ (işlem boyunca tek anlık görüntü), SERIALIZABLE; READ UNCOMMITTED, READ COMMITTED gibi davranır (kirli okuma yok).

**Demo 1 — AKTS yarışı (yazma çarpıklığı):**

| Adım | T1 (bağlantı A) | T2 (bağlantı B) |
|---|---|---|
| 1 | BEGIN | BEGIN |
| 2 | dönemlik AKTS toplamını oku → 24 | |
| 3 | | dönemlik AKTS toplamını oku → 24 |
| 4 | +6 AKTS'lik ders kesinleştir (24 + 6 ≤ 30 ✔) | |
| 5 | | +6 AKTS'lik ders kesinleştir (24 + 6 ≤ 30 ✔) |
| 6 | COMMIT | COMMIT |

Sonuç: dönemlik AKTS **36 > 30** (her işlem tek başına doğru, birlikte yanlış). **Çözüm:** `ogrenci` satırını `FOR UPDATE` ile kilitle: T2, T1 commit edene kadar bekler, sonra toplamı 30 görür ve `AKTS_ASIMI` alır. (SERIALIZABLE bu çarpıklığı serileştirme hatasıyla yakalar; bu projede denenmedi, "alternatif" olarak an.)

**Demo 2 — Kilitlenme:**

| Adım | T1 | T2 |
|---|---|---|
| 1 | kayıt A'yı kilitle | |
| 2 | | kayıt B'yi kilitle |
| 3 | kayıt B'yi ister → bekler | |
| 4 | | kayıt A'yı ister → bekleme çevrimi |
| 5 | PostgreSQL çevrimi (bekleme grafiğinde T1 → T2 → T1) yaklaşık `deadlock_timeout` (1 sn) sonra tespit eder, birini `deadlock detected` (40P01) ile iptal eder | |

**Çözüm:** kilitleri hep aynı sırada al (`ORDER BY kayit_id`): çevrim oluşamaz (`fn_demo_kilitlenme_duzeltilmis`). Bekleme grafiğini çiz.

**Demo 3 — Eşzamanlı çakışma (slot):** iki bağlantı aynı öğrenciye çakışan dersleri eklemeye çalışır: birincil anahtar yalnız birine izin verir (uygulama kontrolü olmadan).

## §12 Kurtarma (15. hafta)

Üç düzey:
1. **Mantıksal geri alma (uygulama düzeyi UNDO):** `denetim_log.eski` → `fn_not_geri_al`. Silinen notun geri gelmesi + hash zincirinin sağlam kalması.
2. **Yedekten geri dönüş:** `pg_dump -Fc` / `pg_restore`; son yedekten sonraki değişiklikler kaybolur (kayıp penceresi).
3. **Çökme kurtarma (WAL):** değişiklikler önce WAL'a yazılır (write-ahead logging). `pg_ctl stop -m immediate` sunucuyu temiz kapatmadan keser, bir sonraki açılışta WAL'dan **redo** yapılır: commit'li veri yerinde, commit'siz işlem geri alınmış olur. Teorideki redo/undo, kontrol noktası (checkpoint) ve WAL kuralıyla eşleştir.

**Not:** (3) uygulamadan gösterilemez (sunucuyu durdurmak gerekir). Hoca canlı demoda terminali yasakladıysa bunu ekran görüntüleri ve adım adım anlatımla raporda göster.
İsteğe bağlı: WAL arşivleme ile belirli bir ana dönüş (PITR).

## §13 Güvenlik ve KVKK

- Roller ve RLS: kimin neyi gördüğü matrisi (`VERITABANI_API_VE_EKRANLAR.md` §1.4).
- **Tuzak (rapora değer):** varsayılan görünümler sahibin yetkisiyle çalışıp RLS'yi atlar; `security_invoker` görünüm satırı süzer (aynı kullanıcıyla denendi: 7 satıra karşı 4 satır).
- Tablo sahibi ve süper kullanıcı RLS'yi atlar → uygulama bu hesaplarla bağlanmaz.
- `SECURITY DEFINER` fonksiyonlar: `search_path` sabit; kimlik oturum değişkeninden; yazma yalnızca fonksiyonlarla.
- Denetim logu: yalnız eklenir, hash zinciriyle bütünlüğü doğrulanır, oynama yakalanır (testli).
- KVKK: gerçek kişisel veri ve TC kimlik numarası yok; tüm veri sentetik; OULAD anonimleştirilmiş açık veri (CC BY 4.0).

## §14 AI katmanı

Yöntem, özellik eşlemesi (OULAD ↔ SIS), etiket, bölme ve adalet notları: `UYGULAMA_PLANI.md` Aşama E. Rapora koy: metrik tablosu (ROC-AUC, PR-AUC, ilk %10 isabeti, temel çizgi karşılaştırması), en etkili özellikler, **sınırlılıklar** (vekil özellikler, tek kurum verisi, sentetik SIS verisi, skor karar vermez, yalnız danışmana gösterilir).

## §15 Sonuç, sınırlılıklar, genişleme

- **Sınırlılıklar:** final taban puanı ve devamsızlık nedeniyle kalma yok; What-If'te ders denkliği yok; en erken mezuniyette seçmeli açığı yok; kontenjan/bekleme listesi kapsam dışı.
- **Genişleme (ERP modülü olarak):** harç/burs defteri, staj, ders denklik, kontenjan ve bekleme listesi, devamsızlık kuralı.

## Ekler

- [ ] ER diyagramı (PNG)
- [ ] Test çıktıları (62+ PASS) · [ ] SQL dosyalarının listesi
- [ ] Ekran görüntüleri: giriş, ders seçimi (hata + başarı), danışman onayı, notlar, mezuniyet + What-If, risk paneli, yönetim, demo (yarış, kilitlenme, geri alma, indeks)
- [ ] EXPLAIN önce/sonra tabloları
- [ ] Kaynakça (aşağıdaki adaylar; bağlantıyı aç, erişim tarihini yaz)

**Kaynakça adayları:** ODTÜ Kayıt Ofisi etkileşimli kayıt sayfası (`oidb.metu.edu.tr`) · İTÜ Ders Seçim Rehberi (`sis.itu.edu.tr`) · Fırat İnşaat Müh. ders kayıt kılavuzu · Ed-Fi Veri Standardı · Cornell CoursePlan (`github.com/cornell-dti/course-plan`) · OULAD: Kuzilek, Hlosta ve Zdrahal (2017), *Scientific Data* (`research.stem.open.ac.uk/ouanalyse/dataset/`) · PostgreSQL belgeleri (RLS, kilitler, EXPLAIN, WAL) · College-ERP (`github.com/samarth-p/College-ERP`), `msmrexe/postgres-course-registration-system` (karşılaştırma için).

---

## Savunma soruları (kısa cevaplarla)

1. **Neden `kayit`'te `ders_id/donem_id` tekrar ediliyor?** Kısmi UNIQUE indeks kuralı bildirimsel olsun; bileşik FK tutarlılığı garanti eder (bilinçli 3NF ihlali).
2. **Neden kurallar uygulamada değil veritabanında?** Her istemci (uygulama, betik, demo) aynı kurallara tabi; atlatılamaz; eşzamanlılıkta da geçerli.
3. **Saat çakışmasını neden birincil anahtarla yakaladınız?** Kontrol-sonra-yaz yarışı olmaz; eşzamanlı istekte bile tek biri geçer.
4. **AKTS yarışında neden satır kilidi?** Yazma çarpıklığı: iki işlem aynı eski toplamı okuyup ayrı satırlara yazıyor; öğrenci satırı kilidi okuma-yazmayı sıraya dizer.
5. **Hash zinciri ne sağlıyor, bedeli ne?** Log oynaması ele verilir; bedel: loga yazan işlemler sıralanır (advisory lock).
6. **ORM neden yok?** İş kuralı veritabanında, ORM'nin sağlayacağı ek değer az; ham SQL ders hedefiyle uyumlu.
7. **PostgreSQL neden?** RLS, EXCLUDE/aralık tipleri, `SKIP LOCKED`, WAL ve zengin yalıtım düzeyleri; hoca serbest bıraktı.
8. **Risk skoru neden karar vermiyor?** Sentetik ve tek kurum verisiyle eğitildi; yanlış alarm öğrenciyi yıkabilir; yalnız danışmana ve nedenleriyle gösterilir.
9. **`security_invoker` neden şart?** Görünümler varsayılan olarak sahibin yetkisiyle çalışır ve RLS'yi atlar; denedik.
10. **Mezuniyet denetimi neden açgözlü?** Dersleri gruplara eşlemenin en iyi çözümü zor bir problem; öncelik sıralı eşleştirme gerçek sistemlerin de kullandığı sezgisel yöntem; çift sayım kuralı grup başına ayarlanır.
