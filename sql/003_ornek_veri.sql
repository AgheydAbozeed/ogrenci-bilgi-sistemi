-- =====================================================================
-- 003_ornek_veri.sql  --  ORNEK veri (gercek kisi/ders/yonetmelik degeri DEGILDIR)
-- On kosul: 001 ve 002.   Calistirma (superuser ile): psql -d obs -f sql/003_ornek_veri.sql
-- Harf notu katsayilari, AKTS limitleri vb. yalnizca ornektir; Firat Universitesi
-- yonetmeligindeki gercek degerlerle DEGISTIRIN.
-- Gecmis donem verisi toplu yukleme gibi tetikleyicisiz yuklenir (session_replication_role).
-- =====================================================================
BEGIN;
SET LOCAL session_replication_role = replica;

-- Parametreler ---------------------------------------------------------
INSERT INTO harf_notu_aralik (harf, min_puan, katsayi, gecer_mi) VALUES
  ('AA',90,4.00,true), ('BA',85,3.50,true), ('BB',80,3.00,true), ('CB',75,2.50,true),
  ('CC',70,2.00,true), ('DC',60,1.50,true), ('DD',50,1.00,true),
  ('FD',40,0.50,false), ('FF',0,0.00,false);

INSERT INTO akts_limit_kural (min_gno, max_gno, max_akts) VALUES
  (0.00, 2.50, 30), (2.50, 3.00, 45), (3.00, 4.01, 50);

INSERT INTO parametre (anahtar, deger, aciklama) VALUES
  ('akts_limit_varsayilan',    '30',   'GNO henuz yokken donemlik AKTS ust siniri'),
  ('tekrar_ders_kurali',       'son',  'Tekrar alinan derste sayilan not: son | en_yuksek'),
  ('devamsizlik_siniri_yuzde', '30',   'Devamsizlik siniri (ORNEK)'),
  ('akts_kilidi',              'acik', 'DEMO: acik = ogrenci satiri kilitlenir, kapali = yazma carpikligi gorulur');

-- Akademik yapi ---------------------------------------------------------
INSERT INTO bolum (ad) VALUES ('Yapay Zeka ve Veri Muhendisligi');
INSERT INTO program (bolum_id, ad, toplam_akts)
  SELECT bolum_id, 'Yapay Zeka ve Veri Muhendisligi (Lisans)', 240 FROM bolum;
INSERT INTO mufredat (program_id, giris_yili)
  SELECT p.program_id, v.y FROM program p, (VALUES (2025), (2026)) v(y);

INSERT INTO ders (kod, ad, akts, teorik_saat, uygulama_saat) VALUES
  ('BIL101','Programlamaya Giris',6,3,2), ('MAT101','Matematik I',6,4,0),
  ('BIL102','Programlama II',6,3,2),      ('MAT102','Matematik II',6,4,0),
  ('BIL201','Veri Yapilari',6,3,2),       ('BIL202','Veri Tabani Yonetim Sistemleri',6,3,2),
  ('BIL301','Yapay Zekaya Giris',6,3,0),
  ('SEC101','Secmeli A',6,3,0), ('SEC102','Secmeli B',6,3,0), ('SEC103','Secmeli C',6,3,0),
  ('SEC104','Secmeli D',6,3,0), ('SEC105','Secmeli E',6,3,0), ('SEC106','Secmeli F',6,3,0);

INSERT INTO mufredat_ders (mufredat_id, ders_id, donem_no, tur)
SELECT m.mufredat_id, d.ders_id, v.dn, v.tur
FROM mufredat m
CROSS JOIN (VALUES ('BIL101',1,'zorunlu'), ('MAT101',1,'zorunlu'), ('BIL102',2,'zorunlu'),
                   ('MAT102',2,'zorunlu'), ('BIL201',3,'zorunlu'), ('BIL202',4,'zorunlu'),
                   ('BIL301',5,'zorunlu'),
                   ('SEC101',3,'secmeli'), ('SEC102',3,'secmeli'), ('SEC103',3,'secmeli'),
                   ('SEC104',3,'secmeli'), ('SEC105',3,'secmeli'), ('SEC106',3,'secmeli')) v(kod, dn, tur)
JOIN ders d ON d.kod = v.kod;

INSERT INTO onkosul (ders_id, onkosul_ders_id, min_harf)
SELECT a.ders_id, b.ders_id, v.min_harf
FROM (VALUES ('BIL102','BIL101','DD'), ('MAT102','MAT101','DD'), ('BIL201','BIL102','CC'),
             ('BIL202','BIL201','DD'), ('BIL301','BIL201','DD')) v(ders, onk, min_harf)
JOIN ders a ON a.kod = v.ders
JOIN ders b ON b.kod = v.onk;

INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik)
SELECT mufredat_id, 'Zorunlu Cekirdek', 'zorunlu', 7, 42, 10 FROM mufredat
UNION ALL
SELECT mufredat_id, 'Secmeli Havuz', 'secmeli_havuz', 2, 12, 20 FROM mufredat;

INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
SELECT g.grup_id, md.ders_id
FROM gereksinim_grubu g
JOIN mufredat_ders md ON md.mufredat_id = g.mufredat_id
WHERE (g.tur = 'zorunlu' AND md.tur = 'zorunlu') OR (g.tur = 'secmeli_havuz' AND md.tur = 'secmeli');

-- Kisiler ----------------------------------------------------------------
INSERT INTO kisi (ad, soyad, eposta) VALUES
  ('Deniz','Hoca','hoca1@ornek.edu'), ('Ece','Hoca','hoca2@ornek.edu'),
  ('Ada','Ornek','ogr1@ornek.edu'),   ('Bora','Ornek','ogr2@ornek.edu'), ('Cem','Ornek','ogr3@ornek.edu'),
  ('Selin','Sekreter','sekreter@ornek.edu');

INSERT INTO ogretim_uyesi (kisi_id, bolum_id, unvan)
  SELECT k.kisi_id, (SELECT bolum_id FROM bolum LIMIT 1), 'Dr. Ogr. Uyesi'
  FROM kisi k WHERE k.eposta IN ('hoca1@ornek.edu','hoca2@ornek.edu');

INSERT INTO ogrenci (kisi_id, ogrenci_no, program_id, mufredat_id, giris_yili)
SELECT k.kisi_id, v.no, p.program_id, m.mufredat_id, v.yil
FROM (VALUES ('ogr1@ornek.edu','2026001',2026), ('ogr2@ornek.edu','2025001',2025),
             ('ogr3@ornek.edu','2025002',2025)) v(eposta, no, yil)
JOIN kisi k ON k.eposta = v.eposta
CROSS JOIN program p
JOIN mufredat m ON m.program_id = p.program_id AND m.giris_yili = v.yil;

INSERT INTO kisi_rol (kisi_id, rol) SELECT kisi_id, 'ogretim_uyesi' FROM ogretim_uyesi;
INSERT INTO kisi_rol (kisi_id, rol) SELECT kisi_id, 'ogrenci' FROM ogrenci;
INSERT INTO kisi_rol (kisi_id, rol) SELECT kisi_id, 'sekreter' FROM kisi WHERE eposta = 'sekreter@ornek.edu';

INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
  SELECT o.kisi_id, (SELECT kisi_id FROM kisi WHERE eposta = 'hoca1@ornek.edu'), daterange('2025-09-01', NULL)
  FROM ogrenci o;

-- Donemler: iki gecmis donem + su an kayit penceresi acik olan guncel donem ---------
INSERT INTO donem (yil, tur, kayit_baslangic, kayit_bitis, ekle_birak_bitis, donem_sonu) VALUES
  (2025, 'guz',   '2025-09-08', '2025-09-12', '2025-09-26', '2026-01-23'),
  (2025, 'bahar', '2026-02-09', '2026-02-13', '2026-02-27', '2026-06-12'),
  (2026, 'guz',   now() - interval '7 days', now() + interval '7 days',
                  now() + interval '14 days', now() + interval '90 days');

-- Subeler ------------------------------------------------------------------
INSERT INTO sube (ders_id, donem_id, sube_no, ogretim_uyesi_id)
SELECT d.ders_id, dn.donem_id, v.no, (SELECT kisi_id FROM kisi WHERE eposta = v.hoca)
FROM (VALUES
  ('BIL101',2025,'guz',  1,'hoca1@ornek.edu'), ('MAT101',2025,'guz',  1,'hoca2@ornek.edu'),
  ('BIL102',2025,'bahar',1,'hoca1@ornek.edu'), ('MAT102',2025,'bahar',1,'hoca2@ornek.edu'),
  ('BIL101',2026,'guz',  1,'hoca1@ornek.edu'), ('MAT101',2026,'guz',  1,'hoca2@ornek.edu'),
  ('BIL201',2026,'guz',  1,'hoca1@ornek.edu'), ('BIL201',2026,'guz',  2,'hoca2@ornek.edu'),
  ('BIL202',2026,'guz',  1,'hoca1@ornek.edu'), ('BIL301',2026,'guz',  1,'hoca2@ornek.edu'),
  ('MAT102',2026,'guz',  1,'hoca2@ornek.edu'),
  ('SEC101',2026,'guz',  1,'hoca1@ornek.edu'), ('SEC102',2026,'guz',  1,'hoca1@ornek.edu'),
  ('SEC103',2026,'guz',  1,'hoca2@ornek.edu'), ('SEC104',2026,'guz',  1,'hoca1@ornek.edu'),
  ('SEC105',2026,'guz',  1,'hoca2@ornek.edu'), ('SEC106',2026,'guz',  1,'hoca1@ornek.edu')
) v(kod, yil, tur, no, hoca)
JOIN ders d   ON d.kod = v.kod
JOIN donem dn ON dn.yil = v.yil AND dn.tur = v.tur;

-- Guncel donem ders saatleri (gun: 1=Pzt ... 5=Cuma). SEC101 ile BIL201-1 Pazartesi 2. saatte CAKISIR.
INSERT INTO sube_saat (sube_id, gun, ders_saati)
SELECT s.sube_id, v.gun, v.saat
FROM (VALUES
  ('BIL101',1,5,1), ('BIL101',1,5,2), ('BIL101',1,5,3),
  ('MAT101',1,5,4), ('MAT101',1,5,5), ('MAT101',1,5,6),
  ('BIL201',1,1,1), ('BIL201',1,1,2),
  ('BIL201',2,2,5), ('BIL201',2,2,6),
  ('BIL202',1,1,3), ('BIL202',1,1,4),
  ('BIL301',1,3,1), ('BIL301',1,3,2),
  ('MAT102',1,2,1), ('MAT102',1,2,2),
  ('SEC101',1,1,2),
  ('SEC102',1,2,3), ('SEC103',1,3,3), ('SEC104',1,4,1), ('SEC105',1,4,2), ('SEC106',1,4,3)
) v(kod, no, gun, saat)
JOIN ders d   ON d.kod = v.kod
JOIN donem dn ON dn.yil = 2026 AND dn.tur = 'guz'
JOIN sube s   ON s.ders_id = d.ders_id AND s.donem_id = dn.donem_id AND s.sube_no = v.no;

-- Gecmis donem kayitlari ve sonuclari --------------------------------------------
--   Bora (2025001): BIL101 AA, MAT101 FF, BIL102 BB      -> GNO 2.33
--   Cem  (2025002): BIL101 AA, MAT101 AA, BIL102 AA, MAT102 AA -> GNO 4.00
--   Ada  (2026001): henuz sonucu yok (ilk donem)
INSERT INTO kayit (ogrenci_id, sube_id, ders_id, donem_id, durum)
SELECT o.kisi_id, s.sube_id, s.ders_id, s.donem_id, 'onayli'
FROM (VALUES ('2025001','BIL101',2025,'guz'),  ('2025001','MAT101',2025,'guz'),  ('2025001','BIL102',2025,'bahar'),
             ('2025002','BIL101',2025,'guz'),  ('2025002','MAT101',2025,'guz'),
             ('2025002','BIL102',2025,'bahar'),('2025002','MAT102',2025,'bahar')) v(no, kod, yil, tur)
JOIN ogrenci o ON o.ogrenci_no = v.no
JOIN ders d    ON d.kod = v.kod
JOIN donem dn  ON dn.yil = v.yil AND dn.tur = v.tur
JOIN sube s    ON s.ders_id = d.ders_id AND s.donem_id = dn.donem_id AND s.sube_no = 1;

INSERT INTO kayit_sonuc (kayit_id, ortalama_puan, harf, durum)
SELECT k.kayit_id, v.puan, v.harf, CASE WHEN h.gecer_mi THEN 'gecti' ELSE 'kaldi' END
FROM (VALUES ('2025001','BIL101',92,'AA'), ('2025001','MAT101',25,'FF'), ('2025001','BIL102',82,'BB'),
             ('2025002','BIL101',95,'AA'), ('2025002','MAT101',91,'AA'),
             ('2025002','BIL102',93,'AA'), ('2025002','MAT102',90,'AA')) v(no, kod, puan, harf)
JOIN ogrenci o ON o.ogrenci_no = v.no
JOIN ders d    ON d.kod = v.kod
JOIN kayit k   ON k.ogrenci_id = o.kisi_id AND k.ders_id = d.ders_id
JOIN harf_notu_aralik h ON h.harf = v.harf;

SET LOCAL session_replication_role = origin;
COMMIT;
