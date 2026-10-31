-- =====================================================================
-- 008_kurumsal_veri_ve_giris.sql
-- 1) Kisi tablosuna kullanici_no (5 haneli) ve sifre ('123456') ekler
-- 2) 3 Bolum (1: Bilgisayar, 2: Yazilim, 3: Yapay Zeka), zengin dersler,
--    akademisyenler (10101..10201, 10001, 10000) ve her yil icin 5'er
--    ogrenci (23101..23305, 24101..24305, 25101..25305) tanimlar.
-- 3) Her ogrencinin giris yilindan itibaren okudugu TUM donemlerin
--    sube, kayit, bilesen (Vize/Final) ve transkript sonuclarini doldurur.
-- =====================================================================
BEGIN;
SET LOCAL session_replication_role = replica;

ALTER TABLE kisi ADD COLUMN IF NOT EXISTS kullanici_no varchar(12) UNIQUE;
ALTER TABLE kisi ADD COLUMN IF NOT EXISTS sifre text NOT NULL DEFAULT '123456';

-- 1) BOLUMLER VE PROGRAMLAR (1: Bilgisayar, 2: Yazilim, 3: Yapay Zeka)
INSERT INTO bolum (ad) VALUES
  ('Bilgisayar Mühendisliği'),
  ('Yazılım Mühendisliği'),
  ('Yapay Zeka ve Veri Mühendisliği')
ON CONFLICT (ad) DO NOTHING;

INSERT INTO program (bolum_id, ad, toplam_akts, min_gno)
SELECT b.bolum_id, b.ad || ' (Lisans)', 240, 2.00
FROM bolum b
ON CONFLICT (bolum_id, ad) DO NOTHING;

INSERT INTO mufredat (program_id, giris_yili)
SELECT p.program_id, y.yil
FROM program p
CROSS JOIN (VALUES (2023), (2024), (2025), (2026)) AS y(yil)
ON CONFLICT (program_id, giris_yili) DO NOTHING;

-- 2) DERSLER (Kurumsal Ders Adlari ve AKTS)
INSERT INTO ders (kod, ad, akts, teorik_saat, uygulama_saat) VALUES
  ('BIL101', 'Algoritma ve Programlamaya Giriş I', 6, 3, 2),
  ('MAT101', 'Matematik I (Kalkülüs I)',           6, 4, 0),
  ('FIZ101', 'Genel Fizik I',                      6, 3, 2),
  ('BIL103', 'Bilgisayar Mühendisliğine Giriş',    4, 2, 0),
  ('BIL102', 'Nesne Yönelimli Programlama',        6, 3, 2),
  ('MAT102', 'Matematik II (Kalkülüs II)',         6, 4, 0),
  ('MAT104', 'Ayrık Matematik',                    5, 3, 0),
  ('BIL201', 'Veri Yapıları ve Algoritmalar',      6, 3, 2),
  ('BIL203', 'Sayısal Tasarım ve Mantık Devreleri',6, 3, 2),
  ('MAT201', 'Doğrusal Cebir',                     5, 3, 0),
  ('BIL202', 'Veritabanı Yönetim Sistemleri',      6, 3, 2),
  ('BIL204', 'İşletim Sistemleri',                 6, 3, 2),
  ('BIL206', 'Algoritma Analizi',                  5, 3, 0),
  ('BIL301', 'Yazılım Mühendisliği',               6, 3, 0),
  ('BIL302', 'Yapay Zeka ve Makine Öğrenmesi',     6, 3, 2),
  ('BIL304', 'Bilgisayar Ağları',                  5, 3, 0),
  ('SEC101', 'Bulut Bilişim ve Dağıtık Sistemler', 6, 3, 0),
  ('SEC102', 'Siber Güvenlik ve Kriptografi',      6, 3, 0),
  ('SEC103', 'Derin Öğrenme Uygulamaları',         6, 3, 0),
  ('SEC104', 'Mobil Uygulama Geliştirme',          6, 3, 0),
  ('SEC105', 'Doğal Dil İşleme',                   6, 3, 0),
  ('SEC106', 'Büyük Veri Analitiği',               6, 3, 0)
ON CONFLICT (kod) DO UPDATE
  SET ad = EXCLUDED.ad,
      akts = EXCLUDED.akts,
      teorik_saat = EXCLUDED.teorik_saat,
      uygulama_saat = EXCLUDED.uygulama_saat;

INSERT INTO mufredat_ders (mufredat_id, ders_id, donem_no, tur)
SELECT m.mufredat_id, d.ders_id, v.dn, v.tur
FROM mufredat m
CROSS JOIN (VALUES
  ('BIL101',1,'zorunlu'), ('MAT101',1,'zorunlu'), ('FIZ101',1,'zorunlu'), ('BIL103',1,'zorunlu'),
  ('BIL102',2,'zorunlu'), ('MAT102',2,'zorunlu'), ('MAT104',2,'zorunlu'),
  ('BIL201',3,'zorunlu'), ('BIL203',3,'zorunlu'), ('MAT201',3,'zorunlu'),
  ('BIL202',4,'zorunlu'), ('BIL204',4,'zorunlu'), ('BIL206',4,'zorunlu'),
  ('BIL301',5,'zorunlu'), ('BIL302',5,'zorunlu'), ('BIL304',6,'zorunlu'),
  ('SEC101',5,'secmeli'), ('SEC102',5,'secmeli'), ('SEC103',6,'secmeli'),
  ('SEC104',6,'secmeli'), ('SEC105',6,'secmeli'), ('SEC106',6,'secmeli')
) v(kod, dn, tur)
JOIN ders d ON d.kod = v.kod
ON CONFLICT (mufredat_id, ders_id) DO NOTHING;

INSERT INTO onkosul (ders_id, onkosul_ders_id, min_harf)
SELECT a.ders_id, b.ders_id, v.min_harf
FROM (VALUES
  ('BIL102','BIL101','DD'),
  ('MAT102','MAT101','DD'),
  ('BIL201','BIL102','CC'),
  ('BIL202','BIL201','DD'),
  ('BIL204','BIL201','DD'),
  ('BIL206','BIL201','CC'),
  ('BIL301','BIL202','DD'),
  ('BIL302','BIL201','DD'),
  ('BIL304','BIL204','DD'),
  ('SEC103','BIL302','DD')
) v(ders, onk, min_harf)
JOIN ders a ON a.kod = v.ders
JOIN ders b ON b.kod = v.onk
ON CONFLICT (ders_id, onkosul_ders_id) DO NOTHING;

INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik)
SELECT m.mufredat_id, 'Zorunlu Çekirdek', 'zorunlu', 7, 42, 10 FROM mufredat m
ON CONFLICT (mufredat_id, ad) DO NOTHING;

INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik)
SELECT m.mufredat_id, 'Seçmeli Havuz', 'secmeli_havuz', 2, 12, 20 FROM mufredat m
ON CONFLICT (mufredat_id, ad) DO NOTHING;

INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
SELECT g.grup_id, md.ders_id
FROM gereksinim_grubu g
JOIN mufredat_ders md ON md.mufredat_id = g.mufredat_id
WHERE (g.tur = 'zorunlu' AND md.tur = 'zorunlu')
   OR (g.tur = 'secmeli_havuz' AND md.tur = 'secmeli')
ON CONFLICT (grup_id, ders_id) DO NOTHING;

-- 3) AKADEMISYEN VE PERSONEL HESAPLARI (Sifre: 123456)
UPDATE kisi SET ad = 'Ahmet',  soyad = 'Yılmaz',   kullanici_no = '10101', sifre = '123456' WHERE eposta = 'hoca1@ornek.edu';
UPDATE kisi SET ad = 'Zeynep', soyad = 'Kaya',     kullanici_no = '10102', sifre = '123456' WHERE eposta = 'hoca2@ornek.edu';
UPDATE kisi SET ad = 'Selin',  soyad = 'Arslan',   kullanici_no = '10001', sifre = '123456' WHERE eposta = 'sekreter@ornek.edu';
UPDATE kisi SET ad = 'Yavuz',  soyad = 'Yönetici', kullanici_no = '10000', sifre = '123456' WHERE eposta = 'yonetici@ornek.edu';

INSERT INTO kisi (ad, soyad, eposta, kullanici_no, sifre) VALUES
  ('Ahmet',  'Yılmaz',   'hoca1@ornek.edu',    '10101', '123456'),
  ('Zeynep', 'Kaya',     'hoca2@ornek.edu',    '10102', '123456'),
  ('Murat',  'Demir',    'hoca3@ornek.edu',    '10103', '123456'),
  ('Elif',   'Çelik',    'hoca4@ornek.edu',    '10201', '123456'),
  ('Selin',  'Arslan',   'sekreter@ornek.edu', '10001', '123456'),
  ('Yavuz',  'Yönetici', 'yonetici@ornek.edu', '10000', '123456')
ON CONFLICT (eposta) DO UPDATE
  SET ad = EXCLUDED.ad,
      soyad = EXCLUDED.soyad,
      kullanici_no = EXCLUDED.kullanici_no,
      sifre = EXCLUDED.sifre;

INSERT INTO ogretim_uyesi (kisi_id, bolum_id, unvan)
SELECT k.kisi_id,
       COALESCE((SELECT bolum_id FROM bolum WHERE ad = v.bolum LIMIT 1), (SELECT bolum_id FROM bolum LIMIT 1)),
       v.unvan
FROM (VALUES
  ('hoca1@ornek.edu', 'Bilgisayar Mühendisliği', 'Prof. Dr.'),
  ('hoca2@ornek.edu', 'Bilgisayar Mühendisliği', 'Doç. Dr.'),
  ('hoca3@ornek.edu', 'Bilgisayar Mühendisliği', 'Dr. Öğr. Üyesi'),
  ('hoca4@ornek.edu', 'Yazılım Mühendisliği',    'Prof. Dr.')
) v(eposta, bolum, unvan)
JOIN kisi k ON k.eposta = v.eposta
ON CONFLICT (kisi_id) DO UPDATE SET unvan = EXCLUDED.unvan;

INSERT INTO kisi_rol (kisi_id, rol)
SELECT kisi_id, 'ogretim_uyesi' FROM ogretim_uyesi
ON CONFLICT DO NOTHING;

INSERT INTO kisi_rol (kisi_id, rol)
SELECT kisi_id, 'sekreter' FROM kisi WHERE eposta = 'sekreter@ornek.edu'
ON CONFLICT DO NOTHING;

INSERT INTO kisi_rol (kisi_id, rol)
SELECT kisi_id, 'yonetici' FROM kisi WHERE eposta = 'yonetici@ornek.edu'
ON CONFLICT DO NOTHING;

-- 4) OGRENCILER (Her yil icin 5'er ogrenci, 5 Haneli Numara: [YY][B][SS], Sifre: 123456)
UPDATE kisi SET ad = 'Ada',  soyad = 'Korkmaz', kullanici_no = '25204', sifre = '123456' WHERE eposta = 'ogr1@ornek.edu';
UPDATE kisi SET ad = 'Bora', soyad = 'Aksoy',   kullanici_no = '25102', sifre = '123456' WHERE eposta = 'ogr2@ornek.edu';
UPDATE kisi SET ad = 'Cem',  soyad = 'Güneş',   kullanici_no = '25103', sifre = '123456' WHERE eposta = 'ogr3@ornek.edu';

UPDATE ogrenci SET ogrenci_no = '25204', giris_yili = 2025 WHERE kisi_id = (SELECT kisi_id FROM kisi WHERE eposta = 'ogr1@ornek.edu');
UPDATE ogrenci SET ogrenci_no = '25102', giris_yili = 2025 WHERE kisi_id = (SELECT kisi_id FROM kisi WHERE eposta = 'ogr2@ornek.edu');
UPDATE ogrenci SET ogrenci_no = '25103', giris_yili = 2025 WHERE kisi_id = (SELECT kisi_id FROM kisi WHERE eposta = 'ogr3@ornek.edu');

INSERT INTO kisi (ad, soyad, eposta, kullanici_no, sifre) VALUES
  -- 2023 Girişliler (5 öğrenci)
  ('Ali',    'Veli',    '23101@ogrenci.edu.tr', '23101', '123456'),
  ('Ayşe',   'Demir',   '23102@ogrenci.edu.tr', '23102', '123456'),
  ('Mehmet', 'Kaya',    '23103@ogrenci.edu.tr', '23103', '123456'),
  ('Zeynep', 'Şahin',   '23204@ogrenci.edu.tr', '23204', '123456'),
  ('Burak',  'Çelik',   '23305@ogrenci.edu.tr', '23305', '123456'),
  -- 2024 Girişliler (5 öğrenci)
  ('Elif',   'Yıldız',  '24101@ogrenci.edu.tr', '24101', '123456'),
  ('Caner',  'Aydın',   '24102@ogrenci.edu.tr', '24102', '123456'),
  ('Selin',  'Koç',     '24103@ogrenci.edu.tr', '24103', '123456'),
  ('Emre',   'Özkan',   '24204@ogrenci.edu.tr', '24204', '123456'),
  ('Derya',  'Arslan',  '24305@ogrenci.edu.tr', '24305', '123456'),
  -- 2025 Girişliler (ek 2 öğrenci -> toplam 5 öğrenci)
  ('Deniz',  'Polat',   '25101@ogrenci.edu.tr', '25101', '123456'),
  ('Mert',   'Yavuz',   '25305@ogrenci.edu.tr', '25305', '123456')
ON CONFLICT (eposta) DO UPDATE
  SET ad = EXCLUDED.ad,
      soyad = EXCLUDED.soyad,
      kullanici_no = EXCLUDED.kullanici_no,
      sifre = EXCLUDED.sifre;

INSERT INTO ogrenci (kisi_id, ogrenci_no, program_id, mufredat_id, giris_yili)
SELECT k.kisi_id,
       v.ogr_no,
       p.program_id,
       m.mufredat_id,
       v.yil
FROM (VALUES
  ('23101@ogrenci.edu.tr', '23101', 2023, 'Bilgisayar Mühendisliği (Lisans)'),
  ('23102@ogrenci.edu.tr', '23102', 2023, 'Bilgisayar Mühendisliği (Lisans)'),
  ('23103@ogrenci.edu.tr', '23103', 2023, 'Bilgisayar Mühendisliği (Lisans)'),
  ('23204@ogrenci.edu.tr', '23204', 2023, 'Yazılım Mühendisliği (Lisans)'),
  ('23305@ogrenci.edu.tr', '23305', 2023, 'Yapay Zeka ve Veri Mühendisliği (Lisans)'),
  ('24101@ogrenci.edu.tr', '24101', 2024, 'Bilgisayar Mühendisliği (Lisans)'),
  ('24102@ogrenci.edu.tr', '24102', 2024, 'Bilgisayar Mühendisliği (Lisans)'),
  ('24103@ogrenci.edu.tr', '24103', 2024, 'Bilgisayar Mühendisliği (Lisans)'),
  ('24204@ogrenci.edu.tr', '24204', 2024, 'Yazılım Mühendisliği (Lisans)'),
  ('24305@ogrenci.edu.tr', '24305', 2024, 'Yapay Zeka ve Veri Mühendisliği (Lisans)'),
  ('25101@ogrenci.edu.tr', '25101', 2025, 'Bilgisayar Mühendisliği (Lisans)'),
  ('25305@ogrenci.edu.tr', '25305', 2025, 'Yapay Zeka ve Veri Mühendisliği (Lisans)')
) v(eposta, ogr_no, yil, prog_ad)
JOIN kisi k ON k.eposta = v.eposta
JOIN program p ON p.ad = v.prog_ad
JOIN mufredat m ON m.program_id = p.program_id AND m.giris_yili = v.yil
ON CONFLICT (kisi_id) DO UPDATE
  SET ogrenci_no = EXCLUDED.ogrenci_no,
      program_id = EXCLUDED.program_id,
      mufredat_id = EXCLUDED.mufredat_id,
      giris_yili = EXCLUDED.giris_yili;

INSERT INTO kisi_rol (kisi_id, rol)
SELECT kisi_id, 'ogrenci' FROM ogrenci
ON CONFLICT DO NOTHING;

-- Danismanlik baslangic tarihlerini yalnizca tek kaydi olanlar icin 2023-09-01 yap
UPDATE danismanlik d1
   SET gecerlilik = daterange('2023-09-01', NULL, '[)')
 WHERE upper_inf(d1.gecerlilik)
   AND NOT EXISTS (
     SELECT 1 FROM danismanlik d2
      WHERE d2.ogrenci_id = d1.ogrenci_id
        AND d2.danismanlik_id <> d1.danismanlik_id
   );

INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
SELECT o.kisi_id,
       CASE WHEN (o.kisi_id % 2) = 0
            THEN (SELECT kisi_id FROM kisi WHERE kullanici_no = '10102')
            ELSE (SELECT kisi_id FROM kisi WHERE kullanici_no = '10101')
       END,
       daterange('2023-09-01', NULL, '[)')
FROM ogrenci o
WHERE NOT EXISTS (
  SELECT 1 FROM danismanlik d WHERE d.ogrenci_id = o.kisi_id AND upper_inf(d.gecerlilik)
);

-- 5) DONEMLER (2023 Guz -> 2026 Guz arasi tum donemler)
INSERT INTO donem (yil, tur, kayit_baslangic, kayit_bitis, ekle_birak_bitis, donem_sonu) VALUES
  (2023, 'guz',   '2023-09-11', '2023-09-15', '2023-09-29', '2024-01-19'),
  (2023, 'bahar', '2024-02-12', '2024-02-16', '2024-03-01', '2024-06-14'),
  (2024, 'guz',   '2024-09-09', '2024-09-13', '2024-09-27', '2025-01-17'),
  (2024, 'bahar', '2025-02-10', '2025-02-14', '2025-02-28', '2025-06-13'),
  (2025, 'guz',   '2025-09-08', '2025-09-12', '2025-09-26', '2026-01-23'),
  (2025, 'bahar', '2026-02-09', '2026-02-13', '2026-02-27', '2026-06-12')
ON CONFLICT (yil, tur) DO NOTHING;

-- Her gecmis ve aktif donemde tum dersler icin 1. subeyi ac (boylece her donem ders kaydi yapilabilir)
INSERT INTO sube (ders_id, donem_id, sube_no, ogretim_uyesi_id)
SELECT d.ders_id,
       dn.donem_id,
       1,
       CASE (d.ders_id % 3)
         WHEN 0 THEN (SELECT kisi_id FROM kisi WHERE kullanici_no = '10101')
         WHEN 1 THEN (SELECT kisi_id FROM kisi WHERE kullanici_no = '10102')
         ELSE        (SELECT kisi_id FROM kisi WHERE kullanici_no = '10103')
       END
FROM ders d
CROSS JOIN donem dn
ON CONFLICT (ders_id, donem_id, sube_no) DO NOTHING;

-- Aktif donem (2026 Guz) ders saatleri
INSERT INTO sube_saat (sube_id, gun, ders_saati)
SELECT s.sube_id, v.gun, v.saat
FROM (VALUES
  ('FIZ101', 1, 3, 5), ('FIZ101', 1, 3, 6),
  ('BIL103', 1, 4, 5), ('BIL103', 1, 4, 6),
  ('BIL203', 1, 2, 7), ('BIL203', 1, 2, 8),
  ('MAT201', 1, 4, 7), ('MAT201', 1, 4, 8),
  ('BIL204', 1, 5, 7), ('BIL204', 1, 5, 8),
  ('BIL206', 1, 1, 5), ('BIL206', 1, 1, 6),
  ('BIL302', 1, 3, 7), ('BIL302', 1, 3, 8),
  ('BIL304', 1, 2, 4)
) v(kod, no, gun, saat)
JOIN ders d   ON d.kod = v.kod
JOIN donem dn ON dn.yil = 2026 AND dn.tur = 'guz'
JOIN sube s   ON s.ders_id = d.ders_id AND s.donem_id = dn.donem_id AND s.sube_no = v.no
ON CONFLICT DO NOTHING;

-- Tum subeler icin Vize (%40) ve Final (%60) degerlendirme bilesenlerini olustur
INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik)
SELECT s.sube_id, v.ad, v.agirlik
FROM sube s
CROSS JOIN (VALUES ('Vize', 40.00), ('Final', 60.00)) AS v(ad, agirlik)
ON CONFLICT (sube_id, ad) DO NOTHING;

-- 6) OGRENCILERIN OKUDUGU TUM DONEMLERIN TRANSKRIPT KAYITLARI
-- Her ogrenci giris_yili'ndan 2025 Bahar'a kadar olan her donemde o yariyilin derslerini almis olur:
--   yariyil_no = (dn.yil - o.giris_yili) * 2 + (CASE dn.tur WHEN 'guz' THEN 1 ELSE 2 END)
-- Boylece:
--   2023 girisliler -> 2023 Guz (1), 2023 Bahar (2), 2024 Guz (3), 2024 Bahar (4), 2025 Guz (5), 2025 Bahar (6) [6 donem!]
--   2024 girisliler -> 2024 Guz (1), 2024 Bahar (2), 2025 Guz (3), 2025 Bahar (4) [4 donem!]
--   2025 girisliler -> 2025 Guz (1), 2025 Bahar (2) [2 donem!]

-- Gecmis donem kayitlarini temiz bir sekilde tamamla (25102 ve 25103'un ozel test notlarini koruyarak)
INSERT INTO kayit (ogrenci_id, sube_id, ders_id, donem_id, durum)
SELECT o.kisi_id, s.sube_id, d.ders_id, dn.donem_id, 'onayli'
FROM ogrenci o
JOIN donem dn ON dn.yil >= o.giris_yili AND dn.yil <= 2025 AND dn.tur IN ('guz', 'bahar')
JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id
                     AND md.donem_no = ((dn.yil - o.giris_yili) * 2 + CASE dn.tur WHEN 'guz' THEN 1 ELSE 2 END)
JOIN ders d ON d.ders_id = md.ders_id
JOIN sube s ON s.ders_id = d.ders_id AND s.donem_id = dn.donem_id AND s.sube_no = 1
WHERE o.ogrenci_no NOT IN ('25102', '25103', '25204')
  AND (md.tur = 'zorunlu' OR d.kod IN ('SEC101', 'SEC102', 'SEC103'))
  AND NOT EXISTS (
    SELECT 1 FROM kayit k
     WHERE k.ogrenci_id = o.kisi_id AND k.donem_id = dn.donem_id AND k.ders_id = d.ders_id
  );

-- Gecmis donem sonuclarini ogrenci profiline gore uret
-- Riskli profiller: 23103 (Mehmet Kaya) ve 24103 (Selin Koc) -> dusuk notlar (DD, DC, FD, FF)
-- Basarili profiller: 23101 (Ali Veli), 24101 (Elif Yildiz), 24305 (Derya Arslan) -> yuksek notlar (AA, BA, BB)
-- Diger ogrenciler -> dengeli notlar (BB, CB, CC, BA)
INSERT INTO kayit_sonuc (kayit_id, ortalama_puan, harf, durum)
SELECT k.kayit_id,
       hesap.puan,
       hesap.harf,
       CASE WHEN hesap.harf IN ('FD', 'FF') THEN 'kaldi' ELSE 'gecti' END
FROM kayit k
JOIN ogrenci o ON o.kisi_id = k.ogrenci_id
JOIN donem dn  ON dn.donem_id = k.donem_id
JOIN ders d    ON d.ders_id = k.ders_id
CROSS JOIN LATERAL (
  SELECT
    CASE
      WHEN o.ogrenci_no IN ('23103', '24103') THEN
        CASE ((k.kayit_id + d.ders_id) % 5)
          WHEN 0 THEN 35.0
          WHEN 1 THEN 54.0
          WHEN 2 THEN 62.0
          WHEN 3 THEN 42.0
          ELSE        71.0
        END
      WHEN o.ogrenci_no IN ('23101', '24101', '24305') THEN
        CASE ((k.kayit_id + d.ders_id) % 4)
          WHEN 0 THEN 93.0
          WHEN 1 THEN 87.0
          WHEN 2 THEN 82.0
          ELSE        91.0
        END
      ELSE
        CASE ((k.kayit_id + d.ders_id) % 5)
          WHEN 0 THEN 86.0
          WHEN 1 THEN 77.0
          WHEN 2 THEN 72.0
          WHEN 3 THEN 81.0
          ELSE        66.0
        END
    END AS puan,
    CASE
      WHEN o.ogrenci_no IN ('23103', '24103') THEN
        CASE ((k.kayit_id + d.ders_id) % 5)
          WHEN 0 THEN 'FF'
          WHEN 1 THEN 'DD'
          WHEN 2 THEN 'DC'
          WHEN 3 THEN 'FD'
          ELSE        'CC'
        END
      WHEN o.ogrenci_no IN ('23101', '24101', '24305') THEN
        CASE ((k.kayit_id + d.ders_id) % 4)
          WHEN 0 THEN 'AA'
          WHEN 1 THEN 'BA'
          WHEN 2 THEN 'BB'
          ELSE        'AA'
        END
      ELSE
        CASE ((k.kayit_id + d.ders_id) % 5)
          WHEN 0 THEN 'BA'
          WHEN 1 THEN 'CB'
          WHEN 2 THEN 'CC'
          WHEN 3 THEN 'BB'
          ELSE        'DC'
        END
    END AS harf
) hesap
WHERE dn.yil <= 2025
  AND NOT EXISTS (SELECT 1 FROM kayit_sonuc ks WHERE ks.kayit_id = k.kayit_id);

-- Gecmis donemlerdeki tum kayitlar icin Vize ve Final not_kaydi satirlarini da doldur (Not Bilgileri ekrani icin)
INSERT INTO not_kaydi (kayit_id, bilesen_id, sube_id, puan, ilan_edildi)
SELECT k.kayit_id,
       db.bilesen_id,
       k.sube_id,
       CASE WHEN db.ad = 'Vize'
            THEN GREATEST(10, LEAST(100, ks.ortalama_puan - 3))
            ELSE GREATEST(10, LEAST(100, ks.ortalama_puan + 2))
       END,
       true
FROM kayit k
JOIN kayit_sonuc ks ON ks.kayit_id = k.kayit_id
JOIN degerlendirme_bileseni db ON db.sube_id = k.sube_id
ON CONFLICT (kayit_id, bilesen_id) DO NOTHING;

-- 7) AKTIF DONEM (2026 GUZ) KAYITLARI (Danisman Onay Kuyrugu ve Ogretim Uyesi Not Girisi Icin)
-- Ogrencilere 2026 Guz doneminde 1 onayli ders ve 1 onay_bekliyor ders ekle (test etmesi kolay olsun)
INSERT INTO kayit (ogrenci_id, sube_id, ders_id, donem_id, durum)
SELECT o.kisi_id, s.sube_id, d.ders_id, dn.donem_id, v.durum
FROM (VALUES
  ('23101', 'SEC104', 'onayli'),
  ('23101', 'SEC105', 'onay_bekliyor'),
  ('23102', 'SEC104', 'onayli'),
  ('23102', 'SEC105', 'onay_bekliyor'),
  ('23103', 'MAT101', 'onay_bekliyor'),
  ('24101', 'BIL301', 'onayli'),
  ('24101', 'BIL302', 'onay_bekliyor'),
  ('24102', 'BIL301', 'onayli'),
  ('25101', 'BIL201', 'onayli'),
  ('25101', 'BIL203', 'onay_bekliyor')
) v(ogr_no, kod, durum)
JOIN ogrenci o ON o.ogrenci_no = v.ogr_no
JOIN ders d    ON d.kod = v.kod
JOIN donem dn  ON dn.yil = 2026 AND dn.tur = 'guz'
JOIN sube s    ON s.ders_id = d.ders_id AND s.donem_id = dn.donem_id AND s.sube_no = 1
WHERE NOT EXISTS (
  SELECT 1 FROM kayit k WHERE k.ogrenci_id = o.kisi_id AND k.donem_id = dn.donem_id AND k.ders_id = d.ders_id
);

-- Aktif donem onayli kayitlar icin ogrenci_slot satirlarini senkronize et
INSERT INTO ogrenci_slot (ogrenci_id, donem_id, gun, ders_saati, kayit_id)
SELECT k.ogrenci_id, k.donem_id, ss.gun, ss.ders_saati, k.kayit_id
FROM kayit k
JOIN donem dn ON dn.donem_id = k.donem_id AND dn.yil = 2026 AND dn.tur = 'guz'
JOIN sube_saat ss ON ss.sube_id = k.sube_id
WHERE k.durum IN ('sepet', 'onay_bekliyor', 'onayli')
ON CONFLICT DO NOTHING;

-- 8) DANISMAN ATAMA FONKSIYONU DUZELTMESI
-- Sekreter ekranindan ayni gun icinde tekrar tekrar danisman degistirildiginde
-- EXCLUDE kisitini koruyarak mevcut aktif danismanligi kapatir/gunceller ve yeni danismani bugun aktif yapar.
CREATE OR REPLACE FUNCTION fn_danisman_ata(p_ogrenci int, p_danisman int, p_baslangic date DEFAULT current_date)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_kul int := fn_oturum_kisi_id();
  v_etkin_bas date := LEAST(COALESCE(p_baslangic, current_date), current_date);
  r record;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('sekreter','yonetici')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sekreter veya yonetici danisman atayabilir';
  END IF;

  -- Bitis tarihi v_etkin_bas'tan sonra olan veya acik uclu olan mevcut kayitlari duzenle
  FOR r IN
    SELECT danismanlik_id, lower(gecerlilik) AS bas
      FROM danismanlik
     WHERE ogrenci_id = p_ogrenci
       AND (upper_inf(gecerlilik) OR upper(gecerlilik) > v_etkin_bas)
  LOOP
    IF r.bas >= v_etkin_bas THEN
      DELETE FROM danismanlik WHERE danismanlik_id = r.danismanlik_id;
    ELSE
      UPDATE danismanlik
         SET gecerlilik = daterange(r.bas, v_etkin_bas, '[)')
       WHERE danismanlik_id = r.danismanlik_id;
    END IF;
  END LOOP;

  INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
  VALUES (p_ogrenci, p_danisman, daterange(v_etkin_bas, NULL, '[)'));
END $$;

GRANT EXECUTE ON FUNCTION fn_danisman_ata(int, int, date) TO rol_sekreter, rol_yonetici;

-- 9) GIRIS GORUNUMU
CREATE OR REPLACE VIEW v_demo_kullanicilar AS
SELECT k.kisi_id,
       k.ad || ' ' || k.soyad AS ad_soyad,
       array_remove(array_agg(DISTINCT r.rol ORDER BY r.rol), NULL) AS roller,
       COALESCE(o.ogrenci_no, k.kullanici_no) AS kullanici_no,
       k.sifre,
       CASE WHEN o.kisi_id IS NOT NULL THEN 'ogrenci' ELSE 'akademisyen' END AS giris_turu,
       p.ad AS program_ad,
       o.giris_yili
  FROM kisi k
  LEFT JOIN ogrenci o ON o.kisi_id = k.kisi_id
  LEFT JOIN program p ON p.program_id = o.program_id
  LEFT JOIN (
    SELECT kisi_id, 'rol_' || rol AS rol FROM kisi_rol
    UNION
    SELECT danisman_id AS kisi_id, 'rol_danisman' AS rol
      FROM danismanlik WHERE gecerlilik @> current_date
  ) r ON r.kisi_id = k.kisi_id
 GROUP BY k.kisi_id, k.ad, k.soyad, o.ogrenci_no, k.kullanici_no, k.sifre, o.kisi_id, p.ad, o.giris_yili
 ORDER BY giris_turu DESC, COALESCE(o.ogrenci_no, k.kullanici_no);

GRANT SELECT ON v_demo_kullanicilar TO obs_login, rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici;

SET LOCAL session_replication_role = origin;
COMMIT;

-- Risk bayraklarini guncelle
SELECT fn_risk_bayrak_hesapla();
