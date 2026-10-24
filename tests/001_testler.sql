-- =====================================================================
-- tests/001_testler.sql -- Kural testleri. Tek hareket icinde calisir, sonunda ROLLBACK (veri bozulmaz).
-- On kosul: 001, 002, 003 yuklu.   Calistirma (superuser): psql -d obs -f tests/001_testler.sql
-- Cikti: her test icin NOTICE satiri  "PASS | ad"  veya  "FAIL | ad | ayrinti"
-- =====================================================================
BEGIN;

-- Yardimci fonksiyonlar (yalnizca bu oturumda var) ---------------------------------
CREATE FUNCTION pg_temp.hata_bekle(p_ad text, p_sql text, p_beklenen text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  BEGIN
    EXECUTE p_sql;
    RAISE NOTICE 'FAIL | % | hata bekleniyordu: %', p_ad, p_beklenen;
  EXCEPTION WHEN OTHERS THEN
    IF position(p_beklenen IN SQLERRM) > 0 THEN
      RAISE NOTICE 'PASS | % | %', p_ad, p_beklenen;
    ELSE
      RAISE NOTICE 'FAIL | % | beklenen: % | gelen: %', p_ad, p_beklenen, SQLERRM;
    END IF;
  END;
END $$;

CREATE FUNCTION pg_temp.basari_bekle(p_ad text, p_sql text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE p_sql;
  RAISE NOTICE 'PASS | %', p_ad;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'FAIL | % | beklenmeyen hata: %', p_ad, SQLERRM;
END $$;

CREATE FUNCTION pg_temp.esit_bekle(p_ad text, p_sorgu text, p_beklenen text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v text;
BEGIN
  EXECUTE p_sorgu INTO v;
  IF v IS NOT DISTINCT FROM p_beklenen THEN
    RAISE NOTICE 'PASS | % | %', p_ad, coalesce(v, 'NULL');
  ELSE
    RAISE NOTICE 'FAIL | % | beklenen: % | gelen: %', p_ad, coalesce(p_beklenen, 'NULL'), coalesce(v, 'NULL');
  END IF;
END $$;

CREATE FUNCTION pg_temp.ogr(p_no text) RETURNS int LANGUAGE sql AS
$$ SELECT kisi_id FROM ogrenci WHERE ogrenci_no = p_no $$;

CREATE FUNCTION pg_temp.hoca(p_eposta text) RETURNS int LANGUAGE sql AS
$$ SELECT kisi_id FROM kisi WHERE eposta = p_eposta $$;

CREATE FUNCTION pg_temp.sube_id(p_kod text, p_no int DEFAULT 1, p_yil int DEFAULT 2026, p_tur text DEFAULT 'guz')
RETURNS int LANGUAGE sql AS $$
  SELECT s.sube_id FROM sube s
  JOIN ders d ON d.ders_id = s.ders_id JOIN donem dn ON dn.donem_id = s.donem_id
  WHERE d.kod = p_kod AND s.sube_no = p_no AND dn.yil = p_yil AND dn.tur = p_tur $$;

CREATE FUNCTION pg_temp.kayit_id(p_no text, p_kod text, p_yil int DEFAULT 2026, p_tur text DEFAULT 'guz')
RETURNS int LANGUAGE sql AS $$
  SELECT k.kayit_id FROM kayit k
  JOIN ders d ON d.ders_id = k.ders_id JOIN donem dn ON dn.donem_id = k.donem_id
  WHERE k.ogrenci_id = pg_temp.ogr(p_no) AND d.kod = p_kod AND dn.yil = p_yil AND dn.tur = p_tur
    AND k.durum <> 'birakti' $$;

-- 1) Hesaplamalar: GNO ve AKTS limiti ---------------------------------------------
SELECT pg_temp.esit_bekle('GNO Bora (AA,FF,BB)', $q$SELECT fn_gno(pg_temp.ogr('2025001'))::text$q$, '2.33');
SELECT pg_temp.esit_bekle('GNO Cem (hepsi AA)',  $q$SELECT fn_gno(pg_temp.ogr('2025002'))::text$q$, '4.00');
SELECT pg_temp.esit_bekle('GNO Ada (sonuc yok)', $q$SELECT fn_gno(pg_temp.ogr('2026001'))::text$q$, NULL);
SELECT pg_temp.esit_bekle('AKTS limit Bora (GNO 2.33)', $q$SELECT fn_akts_limit(pg_temp.ogr('2025001'))::text$q$, '30');
SELECT pg_temp.esit_bekle('AKTS limit Cem (GNO 4.00)',  $q$SELECT fn_akts_limit(pg_temp.ogr('2025002'))::text$q$, '50');
SELECT pg_temp.esit_bekle('AKTS limit Ada (varsayilan)', $q$SELECT fn_akts_limit(pg_temp.ogr('2026001'))::text$q$, '30');

-- 2) Onkosul (R-05) ----------------------------------------------------------------
SELECT pg_temp.hata_bekle('Ada: BIL201 onkosulsuz alinamaz',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2026001'), pg_temp.sube_id('BIL201'))$q$, 'ONKOSUL_EKSIK');
SELECT pg_temp.basari_bekle('Ada: BIL101 (onkosulsuz) sepete eklenir',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2026001'), pg_temp.sube_id('BIL101'))$q$);
SELECT pg_temp.hata_bekle('Bora: MAT102 alinamaz (MAT101 FF)',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id('MAT102'))$q$, 'ONKOSUL_EKSIK');
SELECT pg_temp.basari_bekle('Bora: BIL201 sepete eklenir (BIL102 BB >= CC)',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id('BIL201'))$q$);

-- 3) Saat cakismasi (R-06) ve ayni dersin iki subesi (R-04) --------------------------
SELECT pg_temp.hata_bekle('Bora: SEC101, BIL201 ile cakisir',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id('SEC101'))$q$, 'CAKISMA');
SELECT pg_temp.hata_bekle('Bora: BIL201 ikinci subesi alinamaz',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id('BIL201', 2))$q$, 'ux_kayit_aktif');

-- 4) Durum makinesi (R-12) ve donem penceresi (R-01) ---------------------------------
SELECT pg_temp.hata_bekle('sepet -> onayli dogrudan gecis yasak',
  $q$UPDATE kayit SET durum = 'onayli' WHERE kayit_id = pg_temp.kayit_id('2025001','BIL201')$q$, 'GECERSIZ_GECIS');
SELECT pg_temp.basari_bekle('Ada: gecmis donem BIL101 sepete eklenir',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2026001'), pg_temp.sube_id('BIL101', 1, 2025, 'guz'))$q$);
SELECT pg_temp.hata_bekle('Ada: gecmis donemde kesinlestirme reddedilir',
  $q$UPDATE kayit SET durum = 'onay_bekliyor' WHERE kayit_id = pg_temp.kayit_id('2026001','BIL101',2025,'guz')$q$, 'DONEM_KAPALI');

-- 5) AKTS limiti (R-07): Bora limiti 30; 5 ders x 6 = 30 gecer, 6. ders 36 olur -> reddedilir
DO $$
DECLARE k text;
BEGIN
  FOREACH k IN ARRAY ARRAY['SEC102','SEC103','SEC104','SEC105','SEC106'] LOOP
    INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id(k));
  END LOOP;
  FOREACH k IN ARRAY ARRAY['BIL201','SEC102','SEC103','SEC104','SEC105'] LOOP
    UPDATE kayit SET durum = 'onay_bekliyor' WHERE kayit_id = pg_temp.kayit_id('2025001', k);
  END LOOP;
  RAISE NOTICE 'PASS | Bora: 5 ders (30 AKTS) kesinlestirildi';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'FAIL | Bora: 5 ders kesinlestirme | %', SQLERRM;
END $$;
SELECT pg_temp.hata_bekle('Bora: 6. ders AKTS limitini asar (36 > 30)',
  $q$UPDATE kayit SET durum = 'onay_bekliyor' WHERE kayit_id = pg_temp.kayit_id('2025001','SEC106')$q$, 'AKTS_ASIMI');

-- 6) Danisman karari (R-13, R-14) --------------------------------------------------
SELECT pg_temp.hata_bekle('Danisman olmayan hoca onaylayamaz',
  $q$SELECT fn_danisman_karar(pg_temp.kayit_id('2025001','BIL201'), pg_temp.hoca('hoca2@ornek.edu'), 'onay')$q$, 'YETKISIZ');
SELECT pg_temp.basari_bekle('Guncel danisman onaylar',
  $q$SELECT fn_danisman_karar(pg_temp.kayit_id('2025001','BIL201'), pg_temp.hoca('hoca1@ornek.edu'), 'onay')$q$);
SELECT pg_temp.esit_bekle('Onay sonrasi durum onayli',
  $q$SELECT durum FROM kayit WHERE kayit_id = pg_temp.kayit_id('2025001','BIL201')$q$, 'onayli');
SELECT pg_temp.hata_bekle('Gerekcesiz red olmaz',
  $q$SELECT fn_danisman_karar(pg_temp.kayit_id('2025001','SEC102'), pg_temp.hoca('hoca1@ornek.edu'), 'red')$q$, 'check constraint');
SELECT pg_temp.basari_bekle('Gerekceli red',
  $q$SELECT fn_danisman_karar(pg_temp.kayit_id('2025001','SEC102'), pg_temp.hoca('hoca1@ornek.edu'), 'red', 'Program yogun')$q$);
SELECT pg_temp.esit_bekle('Red sonrasi durum reddedildi',
  $q$SELECT durum FROM kayit WHERE kayit_id = (SELECT max(kayit_id) FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
                                                WHERE d.kod = 'SEC102' AND k.ogrenci_id = pg_temp.ogr('2025001'))$q$, 'reddedildi');

-- 7) Bildirimsel kisitlar: danismanlik EXCLUDE ve onkosul dongusu --------------------------
SELECT pg_temp.hata_bekle('Ayni anda iki danisman olamaz',
  $q$INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
     VALUES (pg_temp.ogr('2025001'), pg_temp.hoca('hoca2@ornek.edu'), daterange(current_date, NULL))$q$, 'exclusion constraint');
SELECT pg_temp.hata_bekle('Onkosul dongusu reddedilir (BIL101 <- BIL301)',
  $q$INSERT INTO onkosul (ders_id, onkosul_ders_id)
     SELECT a.ders_id, b.ders_id FROM ders a, ders b WHERE a.kod = 'BIL101' AND b.kod = 'BIL301'$q$, 'ONKOSUL_DONGUSU');

-- 8) Degerlendirme: agirlik toplami (ertelenebilir kisit), bilesik FK, sonuc hesabi ----------
SELECT pg_temp.basari_bekle('BIL201-1 bilesenleri: Vize 40 + Final 50',
  $q$INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik)
     SELECT pg_temp.sube_id('BIL201'), v.ad, v.a FROM (VALUES ('Vize', 40), ('Final', 50)) v(ad, a)$q$);
SELECT pg_temp.hata_bekle('Agirlik toplami 90 islem sonunda reddedilir',
  'SET CONSTRAINTS ctrg_bilesen_agirlik IMMEDIATE', 'AGIRLIK_TOPLAMI');
DO $$
BEGIN
  INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik) VALUES (pg_temp.sube_id('BIL201'), 'Odev', 10);
  SET CONSTRAINTS ctrg_bilesen_agirlik IMMEDIATE;
  RAISE NOTICE 'PASS | Agirlik toplami 100 kabul edilir';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'FAIL | Agirlik toplami 100 | %', SQLERRM;
END $$;
SELECT pg_temp.basari_bekle('SEC102-1 bileseni: Final 100',
  $q$INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik) VALUES (pg_temp.sube_id('SEC102'), 'Final', 100)$q$);
SELECT pg_temp.hata_bekle('Baska subenin bileseniyle not girilemez (bilesik FK)',
  $q$INSERT INTO not_kaydi (kayit_id, bilesen_id, sube_id, puan, ilan_edildi)
     SELECT pg_temp.kayit_id('2025001','BIL201'), b.bilesen_id, pg_temp.sube_id('BIL201'), 70, true
     FROM degerlendirme_bileseni b WHERE b.sube_id = pg_temp.sube_id('SEC102')$q$, 'foreign key constraint');
SELECT pg_temp.basari_bekle('Bora BIL201: Vize 70 ilan edilir',
  $q$INSERT INTO not_kaydi (kayit_id, bilesen_id, sube_id, puan, ilan_edildi)
     SELECT pg_temp.kayit_id('2025001','BIL201'), b.bilesen_id, b.sube_id, 70, true
     FROM degerlendirme_bileseni b WHERE b.sube_id = pg_temp.sube_id('BIL201') AND b.ad = 'Vize'$q$);
SELECT pg_temp.hata_bekle('Tum bilesenler ilan edilmeden sonuc hesaplanamaz',
  $q$SELECT fn_sonuc_hesapla(pg_temp.kayit_id('2025001','BIL201'))$q$, 'NOT_EKSIK');
SELECT pg_temp.basari_bekle('Bora BIL201: Final 80 ve Odev 100 ilan edilir',
  $q$INSERT INTO not_kaydi (kayit_id, bilesen_id, sube_id, puan, ilan_edildi)
     SELECT pg_temp.kayit_id('2025001','BIL201'), b.bilesen_id, b.sube_id, CASE b.ad WHEN 'Final' THEN 80 ELSE 100 END, true
     FROM degerlendirme_bileseni b WHERE b.sube_id = pg_temp.sube_id('BIL201') AND b.ad IN ('Final','Odev')$q$);
SELECT pg_temp.basari_bekle('Sonuc hesaplanir',
  $q$SELECT fn_sonuc_hesapla(pg_temp.kayit_id('2025001','BIL201'))$q$);
SELECT pg_temp.esit_bekle('Ortalama 0.4*70 + 0.5*80 + 0.1*100 = 78 -> harf CB',
  $q$SELECT harf FROM kayit_sonuc WHERE kayit_id = pg_temp.kayit_id('2025001','BIL201')$q$, 'CB');
SELECT pg_temp.esit_bekle('GNO guncellenir: (24 + 0 + 18 + 15) / 24 = 2.38',
  $q$SELECT fn_gno(pg_temp.ogr('2025001'))::text$q$, '2.38');

-- 9) Denetim logu: kayit, hash zinciri, degistirilemezlik ---------------------------------
SELECT pg_temp.esit_bekle('Denetim kaydi olustu', $q$SELECT (count(*) > 0)::text FROM denetim_log WHERE tablo = 'kayit'$q$, 'true');
SELECT pg_temp.esit_bekle('Hash zinciri saglam', $q$SELECT fn_denetim_dogrula()::text$q$, NULL);
SELECT pg_temp.hata_bekle('Log UPDATE yasak',   $q$UPDATE denetim_log SET kullanici = 'x'$q$, 'DENETIM_LOGU_DEGISTIRILEMEZ');
SELECT pg_temp.hata_bekle('Log DELETE yasak',   $q$DELETE FROM denetim_log$q$, 'DENETIM_LOGU_DEGISTIRILEMEZ');
SELECT pg_temp.hata_bekle('Log TRUNCATE yasak', $q$TRUNCATE denetim_log$q$, 'DENETIM_LOGU_DEGISTIRILEMEZ');

-- Super kullanici tetikleyiciyi kapatip log satirini degistirirse zincir bozulur ve yakalanir
ALTER TABLE denetim_log DISABLE TRIGGER trg_denetim_koru;
UPDATE denetim_log SET yeni = jsonb_set(yeni, '{durum}', '"hile"')
 WHERE log_id = (SELECT min(log_id) FROM denetim_log WHERE yeni IS NOT NULL);
ALTER TABLE denetim_log ENABLE TRIGGER trg_denetim_koru;
SELECT pg_temp.esit_bekle('Log oynamasi hash zincirinde yakalanir',
  $q$SELECT (fn_denetim_dogrula() IS NOT NULL)::text$q$, 'true');

ROLLBACK;
