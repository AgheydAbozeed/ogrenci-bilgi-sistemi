-- =====================================================================
-- tests/003_risk_testleri.sql -- Asama A: Risk bayraklari ve v_risk_ozet testleri
-- =====================================================================
BEGIN;

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

CREATE FUNCTION pg_temp.guncel_donem() RETURNS int LANGUAGE sql AS
$$ SELECT donem_id FROM donem WHERE yil = 2026 AND tur = 'guz' $$;

CREATE FUNCTION pg_temp.sube_id(p_kod text, p_no int DEFAULT 1, p_yil int DEFAULT 2026, p_tur text DEFAULT 'guz')
RETURNS int LANGUAGE sql AS $$
  SELECT s.sube_id FROM sube s
  JOIN ders d ON d.ders_id = s.ders_id JOIN donem dn ON dn.donem_id = s.donem_id
  WHERE d.kod = p_kod AND s.sube_no = p_no AND dn.yil = p_yil AND dn.tur = p_tur $$;

UPDATE parametre SET deger = '8' WHERE anahtar = 'risk_akts_oran';

-- 1) Ilk calistirma ve Idempotency
SELECT pg_temp.esit_bekle('Risk hesaplama 1. calistirma',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) > 0)::text$q$, 'true');

SELECT pg_temp.esit_bekle('Idempotent: 2. calistirmada bayrak sayisi degismez',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) = (SELECT count(*) FROM risk_bayrak WHERE donem_id = pg_temp.guncel_donem()))::text$q$, 'true');

-- 2) Sonucsuz ogrenci (Ada - GNO NULL)
SELECT pg_temp.esit_bekle('Ada (sonuc yok / GNO NULL): bayrak yok',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2026001')$q$, '0');

-- 3) Cem (GNO 4.00, 12 AKTS/donem)
SELECT pg_temp.esit_bekle('Cem (basarili ogrenci): bayrak yok',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025002')$q$, '0');

-- 4) Kural: ZORUNLU_FF
SELECT pg_temp.esit_bekle('Bora: MAT101 FF oldugu icin ZORUNLU_FF cikar',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'ZORUNLU_FF'$q$, '1');

INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025001'), pg_temp.sube_id('MAT101'));
SELECT pg_temp.esit_bekle('Bora: MAT101 sepete eklenince ZORUNLU_FF kalkar',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'ZORUNLU_FF') = 0)::text$q$, 'true');

-- 5) Kural: GNO_ESIK_ALTI
UPDATE parametre SET deger = '2.33' WHERE anahtar = 'risk_gno_esik';
SELECT pg_temp.esit_bekle('Bora (GNO 2.33, esik 2.33): tam esikte GNO_ESIK_ALTI cikmaz',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'GNO_ESIK_ALTI') = 0)::text$q$, 'true');

UPDATE parametre SET deger = '2.50' WHERE anahtar = 'risk_gno_esik';
SELECT pg_temp.esit_bekle('Bora (GNO 2.33, esik 2.50): esik altinda GNO_ESIK_ALTI cikar',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'GNO_ESIK_ALTI') = 1)::text$q$, 'true');
UPDATE parametre SET deger = '2.00' WHERE anahtar = 'risk_gno_esik';
SELECT fn_risk_bayrak_hesapla(pg_temp.guncel_donem());

-- 6) Kural: AKTS_GERIDE
SELECT pg_temp.esit_bekle('Bora (6 AKTS/donem < 8): AKTS_GERIDE cikar',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'AKTS_GERIDE'$q$, '1');
SELECT pg_temp.esit_bekle('Cem (12 AKTS/donem >= 8): AKTS_GERIDE cikmaz',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025002') AND kural_kod = 'AKTS_GERIDE'$q$, '0');

-- 7) Kural: ONKOSUL_BLOKAJI
SELECT pg_temp.esit_bekle('Bora (MAT101 FF -> MAT102 blokajli): ONKOSUL_BLOKAJI cikar',
  $q$SELECT count(*)::text FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025001') AND kural_kod = 'ONKOSUL_BLOKAJI'$q$, '1');

UPDATE kayit_sonuc SET harf = 'DD'
 WHERE kayit_id = (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
                    WHERE k.ogrenci_id = pg_temp.ogr('2025002') AND d.kod = 'BIL102');
SELECT pg_temp.esit_bekle('Cem (BIL102 DD < CC -> BIL201 blokajli): ONKOSUL_BLOKAJI cikar',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025002') AND kural_kod = 'ONKOSUL_BLOKAJI') = 1)::text$q$, 'true');

UPDATE kayit_sonuc SET harf = 'AA'
 WHERE kayit_id = (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
                    WHERE k.ogrenci_id = pg_temp.ogr('2025002') AND d.kod = 'BIL102');

-- 8) Kural: DEVAMSIZLIK
INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2025002'), pg_temp.sube_id('BIL201'));
UPDATE kayit SET durum = 'onay_bekliyor' WHERE ogrenci_id = pg_temp.ogr('2025002') AND donem_id = pg_temp.guncel_donem();
UPDATE kayit SET durum = 'onayli'        WHERE ogrenci_id = pg_temp.ogr('2025002') AND donem_id = pg_temp.guncel_donem();

INSERT INTO yoklama (kayit_id, tarih, katildi)
SELECT k.kayit_id, d.t, d.kat
  FROM kayit k,
       (VALUES (current_date - 3, true), (current_date - 2, true), (current_date - 1, true), (current_date, false)) d(t, kat)
 WHERE k.ogrenci_id = pg_temp.ogr('2025002') AND k.donem_id = pg_temp.guncel_donem();

SELECT pg_temp.esit_bekle('Cem (%25 devamsizlik >= %24 esik): DEVAMSIZLIK cikar',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025002') AND kural_kod = 'DEVAMSIZLIK') = 1)::text$q$, 'true');

UPDATE yoklama SET katildi = true WHERE tarih = current_date;
SELECT pg_temp.esit_bekle('Cem (%0 devamsizlik < %24 esik): DEVAMSIZLIK cikmaz',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2025002') AND kural_kod = 'DEVAMSIZLIK') = 0)::text$q$, 'true');

-- 9) Kural: DERS_BIRAKMA
INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2026001'), pg_temp.sube_id('BIL101'));
UPDATE kayit SET durum = 'birakti' WHERE ogrenci_id = pg_temp.ogr('2026001') AND durum = 'sepet';
SELECT pg_temp.esit_bekle('Ada (1 ders birakti < 2): DERS_BIRAKMA cikmaz',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2026001') AND kural_kod = 'DERS_BIRAKMA') = 0)::text$q$, 'true');

INSERT INTO kayit (ogrenci_id, sube_id) VALUES (pg_temp.ogr('2026001'), pg_temp.sube_id('MAT101'));
UPDATE kayit SET durum = 'birakti' WHERE ogrenci_id = pg_temp.ogr('2026001') AND durum = 'sepet';
SELECT pg_temp.esit_bekle('Ada (2 ders birakti >= 2): DERS_BIRAKMA cikar',
  $q$SELECT (fn_risk_bayrak_hesapla(pg_temp.guncel_donem()) >= 0 AND (SELECT count(*) FROM risk_bayrak WHERE ogrenci_id = pg_temp.ogr('2026001') AND kural_kod = 'DERS_BIRAKMA') = 1)::text$q$, 'true');

-- 10) v_risk_ozet gorunumu kontrolu
SELECT pg_temp.esit_bekle('v_risk_ozet Bora: 2 bayrak (AKTS_GERIDE, ONKOSUL_BLOKAJI), max siddet 1',
  $q$SELECT bayrak_sayisi || '/' || en_yuksek_siddet || '/' || bayrak_kodlari
       FROM v_risk_ozet WHERE ogrenci_id = pg_temp.ogr('2025001') AND donem_id = pg_temp.guncel_donem()$q$,
  '2/1/AKTS_GERIDE, ONKOSUL_BLOKAJI');

ROLLBACK;
