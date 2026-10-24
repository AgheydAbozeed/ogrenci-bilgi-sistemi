# AI Destekli Öğrenci Bilgi Sistemi (SIS)

PostgreSQL + Python (PySide6 masaüstü uygulaması). **İş kuralları veritabanındadır** (kısıt, tetikleyici, fonksiyon); uygulama yalnızca görünümleri okur ve fonksiyonları çağırır.

## Okuma sırası

1. `docs/TASARIM.md` — genel bakış, ER diyagramı, kurallar, algoritmalar
2. `docs/UYGULAMA_PLANI.md` — kalan aşamalar (A–H): ne yapılacak, nasıl test edilecek
3. `docs/VERITABANI_API_VE_EKRANLAR.md` — uygulamanın çağıracağı görünüm/fonksiyonlar ve ekran tasarımları
4. `docs/RAPOR_ISKELETI.md` — rapor iskeleti (normalizasyon, ilişkisel cebir, hareket demoları, savunma soruları ön dolu)

## Klasörler

| Klasör | İçerik |
|---|---|
| `sql/` | `001_sema` → `004_mezuniyet` (hazır, testli); `iskeletler.sql`, `iskelet_rls.sql` (doğrulanmış başlangıç kodu) |
| `tests/` | 62 test (`001_testler.sql`, `002_mezuniyet_testleri.sql`) |
| `docs/` | tasarım ve plan belgeleri |

## Kurulum (çekirdek)

```
createdb obs
psql -d obs -f sql/001_sema.sql
psql -d obs -f sql/002_kurallar.sql
psql -d obs -f sql/003_ornek_veri.sql      # süper kullanıcı ile
psql -d obs -f sql/004_mezuniyet.sql
psql -d obs -f tests/001_testler.sql       # 42 test (PASS / FAIL)
psql -d obs -f tests/002_mezuniyet_testleri.sql   # 20 test
```

`003` içindeki katsayılar, limitler ve tüm kişi/ders verileri **örnektir**; gerçek değerleri üniversite yönetmeliğinden parametre tablolarına gir.

## Durum

- [x] Çekirdek: 33 tablo, kurallar, mezuniyet algoritmaları, 62 test
- [ ] A risk bayrakları · B API + yetki · C büyük veri · D demolar · E AI · F uygulama · G paketleme · H kabul

## Güvenlik

Parolalar ve `.env` dosyası repoya yüklenmez. `.gitignore`: `.env`, `data/`, `*.dump`, `*.joblib`.
