-- =====================================================================
-- tests/005_yetki_testleri.sql -- Asama B: RLS (Satir Duzeyi Guvenlik) ve Rol Yetki Testleri
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

-- Kimlikleri yerel degiskenlere kaydet (rol degisince dogrudan kullanmak icin)
DO $$
BEGIN
  PERFORM set_config('test.ogr_bora', (SELECT kisi_id::text FROM ogrenci WHERE ogrenci_no = '2025001'), true);
  PERFORM set_config('test.ogr_cem',  (SELECT kisi_id::text FROM ogrenci WHERE ogrenci_no = '2025002'), true);
  PERFORM set_config('test.hoca1',    (SELECT kisi_id::text FROM kisi WHERE eposta = 'hoca1@ornek.edu'), true);
  PERFORM set_config('test.hoca2',    (SELECT kisi_id::text FROM kisi WHERE eposta = 'hoca2@ornek.edu'), true);
  PERFORM set_config('test.sekreter', (SELECT kisi_id::text FROM kisi WHERE eposta = 'sekreter@ornek.edu'), true);
  PERFORM set_config('test.yonetici', (SELECT kisi_id::text FROM kisi WHERE eposta = 'yonetici@ornek.edu'), true);
END $$;

-- Risk bayraklarini uretelim (Bora icin bayrak olussun)
SELECT fn_risk_bayrak_hesapla() INTO pg_temp.dummy_risk;

-- 1) obs_login rolu: yalnizca v_demo_kullanicilar okuyabilir, kayit tablosunu okuyamaz
SET LOCAL ROLE obs_login;
SELECT pg_temp.esit_bekle('obs_login: v_demo_kullanicilar okur',
  $q$SELECT (count(*) >= 6)::text FROM v_demo_kullanicilar$q$, 'true');
SELECT pg_temp.hata_bekle('obs_login: kayit tablosunu okuyamaz',
  $q$SELECT count(*) FROM kayit$q$, 'permission denied');

-- 2) rol_ogrenci (Bora - 3 kaydi var; Cem'in 4 kaydini goremez)
SET LOCAL ROLE rol_ogrenci;
SELECT set_config('app.kullanici_id', current_setting('test.ogr_bora'), true);

SELECT pg_temp.esit_bekle('Ogrenci (Bora): v_kayitlarim yalniz kendi 3 kaydini gosterir',
  $q$SELECT count(*)::text FROM v_kayitlarim$q$, '3');
SELECT pg_temp.esit_bekle('Ogrenci (Bora): Cem in kayitlarini goremez (0 satir)',
  $q$SELECT count(*)::text FROM kayit WHERE ogrenci_id = current_setting('test.ogr_cem')::int$q$, '0');
SELECT pg_temp.esit_bekle('Ogrenci (Bora): kendi risk bayraklarini bile goremez (0 satir)',
  $q$SELECT count(*)::text FROM risk_bayrak$q$, '0');
SELECT pg_temp.esit_bekle('Ogrenci (Bora): denetim_log goremez (0 satir)',
  $q$SELECT count(*)::text FROM v_denetim_log$q$, '0');
SELECT pg_temp.hata_bekle('Ogrenci: kayit tablosuna dogrudan INSERT yapamaz',
  $q$INSERT INTO kayit (ogrenci_id, sube_id) VALUES (current_setting('test.ogr_bora')::int, 1)$q$, 'permission denied');

-- 3) rol_danisman: hoca1 tum ogrencilerin danismani (7 kayit gorur), hoca2 hicbirinin danismani degil (0 gorur)
SET LOCAL ROLE rol_danisman;
SELECT set_config('app.kullanici_id', current_setting('test.hoca1'), true);
SELECT pg_temp.esit_bekle('Danisman (hoca1): danisanlarinin 7 kaydini gorur',
  $q$SELECT count(*)::text FROM v_kayitlarim$q$, '7');
SELECT pg_temp.esit_bekle('Danisman (hoca1): Bora nin risk bayraklarini gorur',
  $q$SELECT (count(*) > 0)::text FROM v_danisan_bayraklari WHERE ogrenci_id = current_setting('test.ogr_bora')::int$q$, 'true');

SELECT set_config('app.kullanici_id', current_setting('test.hoca2'), true);
SELECT pg_temp.esit_bekle('Danisman (hoca2 - danisani yok): 0 kayit gorur',
  $q$SELECT count(*)::text FROM v_kayitlarim$q$, '0');
SELECT pg_temp.esit_bekle('Danisman (hoca2 - danisani yok): 0 risk bayragi gorur',
  $q$SELECT count(*)::text FROM v_danisan_bayraklari$q$, '0');

-- 4) rol_ogretim_uyesi: hoca2 yalniz kendi subelerindeki (MAT101, MAT102) 3 kaydi gorur
SET LOCAL ROLE rol_ogretim_uyesi;
SELECT set_config('app.kullanici_id', current_setting('test.hoca2'), true);
SELECT pg_temp.esit_bekle('Ogretim uyesi (hoca2): yalniz kendi subelerindeki 3 kaydi gorur',
  $q$SELECT count(*)::text FROM kayit$q$, '3');

-- 5) rol_sekreter vs rol_yonetici: sekreter tum kayitlari gorur ama denetim_log goremez; yonetici denetim_log gorur
SET LOCAL ROLE rol_sekreter;
SELECT set_config('app.kullanici_id', current_setting('test.sekreter'), true);
SELECT pg_temp.esit_bekle('Sekreter: tum 7 kaydi gorur',
  $q$SELECT count(*)::text FROM kayit$q$, '7');
SELECT pg_temp.esit_bekle('Sekreter: denetim_log goremez (0 satir)',
  $q$SELECT count(*)::text FROM v_denetim_log$q$, '0');

SET LOCAL ROLE rol_yonetici;
SELECT set_config('app.kullanici_id', current_setting('test.yonetici'), true);
SELECT pg_temp.esit_bekle('Yonetici: parametre gunceller ve denetim_log okur',
  $q$SELECT (fn_parametre_guncelle('akts_limit_varsayilan', '30') IS NULL
             AND (SELECT count(*) FROM v_denetim_log) > 0)::text$q$, 'true');

RESET ROLE;
ROLLBACK;
