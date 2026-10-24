-- =====================================================================
-- tests/002_mezuniyet_testleri.sql -- Mezuniyet denetimi, What-If, ders plani, en erken mezuniyet
-- On kosul: 001..004 yuklu.   Calistirma (superuser): psql -d obs -f tests/002_mezuniyet_testleri.sql
-- Tek hareket icinde calisir, sonunda ROLLBACK (veri bozulmaz). Cikti: PASS | ad  /  FAIL | ad | ayrinti
-- =====================================================================
BEGIN;

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

-- Ogrenciler: Ada 2026001 (sonucu yok) | Bora 2025001 (BIL101 AA, MAT101 FF, BIL102 BB) | Cem 2025002 (BIL101, MAT101, BIL102, MAT102 AA)

-- 1) Mezuniyet denetimi: gruplara eslestirme ---------------------------------------------
SELECT pg_temp.esit_bekle('Cem zorunlu grup: 4 ders / 24 AKTS, eksik 3 ders',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || durum || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2025002')) WHERE grup_ad = 'Zorunlu Cekirdek'$q$,
  '4/24/eksik/BIL201, BIL202, BIL301');
SELECT pg_temp.esit_bekle('Cem secmeli havuz: hic ders yok',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || durum || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2025002')) WHERE grup_ad = 'Secmeli Havuz'$q$,
  '0/0/eksik/2 ders, 12 AKTS daha');
SELECT pg_temp.esit_bekle('Ada zorunlu grup: hicbiri gecilmemis',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || durum || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2026001')) WHERE grup_ad = 'Zorunlu Cekirdek'$q$,
  '0/0/eksik/BIL101, BIL102, BIL201, BIL202, BIL301, MAT101, MAT102');
SELECT pg_temp.esit_bekle('Bora zorunlu grup: MAT101 FF oldugu icin sayilmaz',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || durum || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2025001')) WHERE grup_ad = 'Zorunlu Cekirdek'$q$,
  '2/12/eksik/BIL201, BIL202, BIL301, MAT101, MAT102');
SELECT pg_temp.hata_bekle('Olmayan ogrenci', $q$SELECT * FROM fn_mezuniyet_denetim(-1)$q$, 'OGRENCI_BULUNAMADI');

-- 2) Cift sayim kurali: oncelikli grup dersi tuketir (cift_sayim = false) ya da paylasir (true) ---------
INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik, cift_sayim)
  SELECT mufredat_id, 'Ek Grup', 'zorunlu', 1, 0, 5, false FROM ogrenci WHERE ogrenci_no = '2025002';
INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
  SELECT g.grup_id, d.ders_id FROM gereksinim_grubu g, ders d WHERE g.ad = 'Ek Grup' AND d.kod = 'BIL101';
SELECT pg_temp.esit_bekle('Cift sayim YOK: BIL101 Ek Grup tarafindan tuketilir, zorunlu gruptan duser',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2025002')) WHERE grup_ad = 'Zorunlu Cekirdek'$q$,
  '3/18/BIL101, BIL201, BIL202, BIL301');
UPDATE gereksinim_grubu SET cift_sayim = true WHERE ad = 'Ek Grup';
SELECT pg_temp.esit_bekle('Cift sayim VAR: BIL101 iki grupta da sayilir',
  $q$SELECT sayilan_ders || '/' || sayilan_akts || '/' || coalesce(eksik, '-')
     FROM fn_mezuniyet_denetim(pg_temp.ogr('2025002')) WHERE grup_ad = 'Zorunlu Cekirdek'$q$,
  '4/24/BIL201, BIL202, BIL301');
DELETE FROM gereksinim_grubu WHERE ad = 'Ek Grup';

-- 3) What-If: ayni ogrenci baska mufredata karsi denetlenir ----------------------------------
INSERT INTO mufredat (program_id, giris_yili) SELECT program_id, 2030 FROM program;
INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik)
  SELECT mufredat_id, 'Zorunlu Cekirdek', 'zorunlu', 2, 12, 10 FROM mufredat WHERE giris_yili = 2030;
INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
  SELECT g.grup_id, d.ders_id
  FROM gereksinim_grubu g JOIN mufredat m ON m.mufredat_id = g.mufredat_id, ders d
  WHERE m.giris_yili = 2030 AND d.kod IN ('BIL101', 'MAT101');
SELECT pg_temp.esit_bekle('What-If: Cem 2030 mufredatini saglar',
  $q$SELECT durum FROM fn_mezuniyet_denetim(pg_temp.ogr('2025002'), (SELECT mufredat_id FROM mufredat WHERE giris_yili = 2030))$q$,
  'tamam');
SELECT pg_temp.esit_bekle('What-If: Ada 2030 mufredatini saglamaz',
  $q$SELECT durum FROM fn_mezuniyet_denetim(pg_temp.ogr('2026001'), (SELECT mufredat_id FROM mufredat WHERE giris_yili = 2030))$q$,
  'eksik');

-- 4) Ders plani ve en erken mezuniyet -----------------------------------------------------------
SELECT pg_temp.esit_bekle('Cem: kritik yol / AKTS limitli donem = 2/2',
  $q$SELECT kritik_yol_donem || '/' || akts_limitli_donem FROM fn_en_erken_mezuniyet(pg_temp.ogr('2025002'))$q$, '2/2');
SELECT pg_temp.esit_bekle('Bora: kritik yol / AKTS limitli donem = 2/2',
  $q$SELECT kritik_yol_donem || '/' || akts_limitli_donem FROM fn_en_erken_mezuniyet(pg_temp.ogr('2025001'))$q$, '2/2');
SELECT pg_temp.esit_bekle('Ada: BIL101 > BIL102 > BIL201 > BIL202 zinciri = 4 donem',
  $q$SELECT kritik_yol_donem || '/' || akts_limitli_donem FROM fn_en_erken_mezuniyet(pg_temp.ogr('2026001'))$q$, '4/4');
SELECT pg_temp.esit_bekle('Ada 1. donem: onkosulsuz dersler',
  $q$SELECT string_agg(ders_kod, ',' ORDER BY ders_kod) FROM fn_ders_plani(pg_temp.ogr('2026001')) WHERE donem_sira = 1$q$,
  'BIL101,MAT101');
SELECT pg_temp.esit_bekle('Ada AKTS limiti 6 iken: kritik yol 4 ama gercek 7 donem',
  $q$SELECT kritik_yol_donem || '/' || akts_limitli_donem FROM fn_en_erken_mezuniyet(pg_temp.ogr('2026001'), 6)$q$, '4/7');
SELECT pg_temp.hata_bekle('AKTS limiti 5 tek dersi bile almaya yetmez',
  $q$SELECT count(*) FROM fn_ders_plani(pg_temp.ogr('2026001'), 5)$q$, 'PLAN_KURULAMADI');

-- Yetersiz notlu onkosul: Bora BIL102'yi DD ile gecmis, BIL201 icin en az CC gerekir -> BIL102 tekrar planlanir
UPDATE kayit_sonuc SET harf = 'DD'
 WHERE kayit_id = (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
                    WHERE k.ogrenci_id = pg_temp.ogr('2025001') AND d.kod = 'BIL102');
SELECT pg_temp.esit_bekle('Bora (BIL102 DD): tekrar nedeniyle kritik yol 3 donem',
  $q$SELECT kritik_yol_donem || '/' || akts_limitli_donem FROM fn_en_erken_mezuniyet(pg_temp.ogr('2025001'))$q$, '3/3');
SELECT pg_temp.esit_bekle('Bora 1. donem: BIL102 tekrari + MAT101',
  $q$SELECT string_agg(ders_kod, ',' ORDER BY ders_kod) FROM fn_ders_plani(pg_temp.ogr('2025001')) WHERE donem_sira = 1$q$,
  'BIL102,MAT101');

-- 5) Ozet: toplam AKTS + GNO esigi + gruplar ----------------------------------------------------
-- Cem'e kalan dersleri gecmis say (toplu yukleme gibi tetikleyicisiz)
SET LOCAL session_replication_role = replica;
INSERT INTO kayit (ogrenci_id, sube_id, ders_id, donem_id, durum)
SELECT pg_temp.ogr('2025002'), s.sube_id, s.ders_id, s.donem_id, 'onayli'
FROM sube s JOIN ders d ON d.ders_id = s.ders_id JOIN donem dn ON dn.donem_id = s.donem_id
WHERE dn.yil = 2026 AND dn.tur = 'guz' AND s.sube_no = 1 AND d.kod IN ('BIL201','BIL202','BIL301','SEC101','SEC102');
INSERT INTO kayit_sonuc (kayit_id, ortalama_puan, harf, durum)
SELECT k.kayit_id, 95, 'AA', 'gecti'
FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
WHERE k.ogrenci_id = pg_temp.ogr('2025002') AND d.kod IN ('BIL201','BIL202','BIL301','SEC101','SEC102');
SET LOCAL session_replication_role = origin;

UPDATE program SET toplam_akts = 54;
SELECT pg_temp.esit_bekle('Cem: gruplar tamam, 54 AKTS, GNO 4.00 -> mezuniyete uygun',
  $q$SELECT mezuniyet_uygun || '/' || gruplar_tamam || '/' || gecilen_akts || '/' || gno FROM fn_mezuniyet_ozet(pg_temp.ogr('2025002'))$q$,
  'true/true/54/4.00');
UPDATE program SET toplam_akts = 240;
SELECT pg_temp.esit_bekle('Cem: toplam AKTS yetmeyince uygun degil',
  $q$SELECT mezuniyet_uygun || '/' || gruplar_tamam FROM fn_mezuniyet_ozet(pg_temp.ogr('2025002'))$q$,
  'false/true');
SELECT pg_temp.esit_bekle('Ada: ozet eksikleri listeler',
  $q$SELECT mezuniyet_uygun || '/' || (eksikler LIKE 'Zorunlu Cekirdek: BIL101%') FROM fn_mezuniyet_ozet(pg_temp.ogr('2026001'))$q$,
  'false/true');

ROLLBACK;
