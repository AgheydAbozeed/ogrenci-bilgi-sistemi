-- =====================================================================
-- tests/004_api_testleri.sql -- Asama B: DB API, MUFREDAT_DISI ve denetim logu testleri
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

CREATE FUNCTION pg_temp.kisi_eposta(p_eposta text) RETURNS int LANGUAGE sql AS
$$ SELECT kisi_id FROM kisi WHERE eposta = p_eposta $$;

CREATE FUNCTION pg_temp.sube_id(p_kod text, p_no int DEFAULT 1, p_yil int DEFAULT 2026, p_tur text DEFAULT 'guz')
RETURNS int LANGUAGE sql AS $$
  SELECT s.sube_id FROM sube s
  JOIN ders d ON d.ders_id = s.ders_id JOIN donem dn ON dn.donem_id = s.donem_id
  WHERE d.kod = p_kod AND s.sube_no = p_no AND dn.yil = p_yil AND dn.tur = p_tur $$;

-- 1) Kimlik yokken API cagrisi YETKISIZ verir
SELECT set_config('app.kullanici_id', '', true);
SELECT pg_temp.hata_bekle('Kimlik yokken fn_sepete_ekle YETKISIZ',
  $q$SELECT fn_sepete_ekle(pg_temp.sube_id('BIL101'))$q$, 'YETKISIZ');

-- 2) MUFREDAT_DISI kurali: mufredatta olmayan bir ders acilirsa ogrenci sepete ekleyemez
INSERT INTO ders (kod, ad, akts, teorik_saat, uygulama_saat) VALUES ('TIP101', 'Anatomi', 6, 4, 0);
INSERT INTO sube (ders_id, donem_id, sube_no, ogretim_uyesi_id)
SELECT d.ders_id, fn_aktif_donem_id(), 1, pg_temp.kisi_eposta('hoca1@ornek.edu')
  FROM ders d WHERE d.kod = 'TIP101';

SELECT set_config('app.kullanici_id', pg_temp.ogr('2026001')::text, true);
SELECT pg_temp.hata_bekle('Ada: Mufredatinda olmayan TIP101 dersini sepete ekleyemez',
  $q$SELECT fn_sepete_ekle(pg_temp.sube_id('TIP101'))$q$, 'MUFREDAT_DISI');

-- 3) Ogrenci sepet, kesinlestir_hepsi ve baskasinin kaydina mudahale engeli
SELECT pg_temp.esit_bekle('Ada: BIL101 sepete eklenir',
  $q$SELECT (fn_sepete_ekle(pg_temp.sube_id('BIL101')) > 0)::text$q$, 'true');
SELECT pg_temp.esit_bekle('Ada: MAT101 sepete eklenir',
  $q$SELECT (fn_sepete_ekle(pg_temp.sube_id('MAT101')) > 0)::text$q$, 'true');

-- Bora, Ada'nin sepetteki dersini cikaramaz
SELECT set_config('app.kullanici_id', pg_temp.ogr('2025001')::text, true);
SELECT pg_temp.hata_bekle('Bora: Ada nin kaydini sepetten cikaramaz',
  $q$SELECT fn_sepetten_cikar((SELECT max(kayit_id) FROM kayit WHERE ogrenci_id = pg_temp.ogr('2026001')))$q$, 'YETKISIZ');

-- Ada: fn_kesinlestir_hepsi ile ikisini de kesinlestirir
SELECT set_config('app.kullanici_id', pg_temp.ogr('2026001')::text, true);
SELECT pg_temp.esit_bekle('Ada: fn_kesinlestir_hepsi 2 kaydi tamamlar',
  $q$SELECT count(*)::text FROM fn_kesinlestir_hepsi() WHERE sonuc = 'tamam'$q$, '2');

-- Denetim logunda kullanici kimligi Ada'nin kisi_id'si olmali
SELECT pg_temp.esit_bekle('Denetim logu app.kullanici_id degerini yazar',
  $q$SELECT (kullanici = pg_temp.ogr('2026001')::text)::text FROM denetim_log ORDER BY log_id DESC LIMIT 1$q$, 'true');

-- 4) Danisman onayi (_ben sarmalayicisi)
SELECT set_config('app.kullanici_id', pg_temp.kisi_eposta('hoca1@ornek.edu')::text, true);
SELECT pg_temp.esit_bekle('Danisman: Ada nin BIL101 kaydini onaylar',
  $q$SELECT (fn_danisman_karar_ben(
       (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
         WHERE k.ogrenci_id = pg_temp.ogr('2026001') AND d.kod = 'BIL101' AND k.donem_id = fn_aktif_donem_id()),
       'onay') IS NULL)::text$q$, 'true');

-- 5) Ogretim uyesi: tek cagrida bilesen belirleme, not giris, ilan, sonuc hesabi ve gerekceli duzeltme
SELECT pg_temp.hata_bekle('Hoca1: Toplami 90 olan bilesen dizisi reddedilir',
  $q$SELECT fn_bilesenleri_belirle(pg_temp.sube_id('BIL101'), ARRAY['Vize','Final'], ARRAY[40, 50])$q$, 'AGIRLIK_TOPLAMI');

SELECT pg_temp.esit_bekle('Hoca1: Toplami 100 olan bilesen dizisi kabul edilir',
  $q$SELECT fn_bilesenleri_belirle(pg_temp.sube_id('BIL101'), ARRAY['Vize','Final'], ARRAY[40, 60])::text$q$, '2');

DO $$
DECLARE v_kayit int; v_vize int; v_final int;
BEGIN
  SELECT k.kayit_id INTO v_kayit FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
   WHERE k.ogrenci_id = pg_temp.ogr('2026001') AND d.kod = 'BIL101' AND k.donem_id = fn_aktif_donem_id();
  SELECT bilesen_id INTO v_vize  FROM degerlendirme_bileseni WHERE sube_id = pg_temp.sube_id('BIL101') AND ad = 'Vize';
  SELECT bilesen_id INTO v_final FROM degerlendirme_bileseni WHERE sube_id = pg_temp.sube_id('BIL101') AND ad = 'Final';
  PERFORM fn_not_gir(v_kayit, v_vize, 80);
  PERFORM fn_not_gir(v_kayit, v_final, 90);
END $$;

SELECT pg_temp.esit_bekle('Hoca1: Notlari ilan eder (2 not)',
  $q$SELECT fn_not_ilan_et(pg_temp.sube_id('BIL101'))::text$q$, '2');

SELECT pg_temp.hata_bekle('Hoca1: Ilan edilmis not fn_not_gir ile degistirilemez',
  $q$SELECT fn_not_gir(
       (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
         WHERE k.ogrenci_id = pg_temp.ogr('2026001') AND d.kod = 'BIL101' AND k.donem_id = fn_aktif_donem_id()),
       (SELECT bilesen_id FROM degerlendirme_bileseni WHERE sube_id = pg_temp.sube_id('BIL101') AND ad = 'Vize'),
       100)$q$, 'NOT_ILAN_EDILDI');

SELECT pg_temp.esit_bekle('Hoca1: Sonuclari hesaplar (1 hesaplanan, 0 eksik)',
  $q$SELECT hesaplanan || '/' || eksik FROM fn_sonuclari_hesapla(pg_temp.sube_id('BIL101'))$q$, '1/0');

SELECT pg_temp.hata_bekle('Hoca1: Gerekcesiz not duzeltme reddedilir',
  $q$SELECT fn_not_duzelt(
       (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
         WHERE k.ogrenci_id = pg_temp.ogr('2026001') AND d.kod = 'BIL101' AND k.donem_id = fn_aktif_donem_id()),
       (SELECT bilesen_id FROM degerlendirme_bileseni WHERE sube_id = pg_temp.sube_id('BIL101') AND ad = 'Vize'),
       95, '   ')$q$, 'GEREKCE_ZORUNLU');

SELECT pg_temp.esit_bekle('Hoca1: Gerekceli not duzeltme calisir ve loga _gerekce yazar',
  $q$SELECT (fn_not_duzelt(
       (SELECT k.kayit_id FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
         WHERE k.ogrenci_id = pg_temp.ogr('2026001') AND d.kod = 'BIL101' AND k.donem_id = fn_aktif_donem_id()),
       (SELECT bilesen_id FROM degerlendirme_bileseni WHERE sube_id = pg_temp.sube_id('BIL101') AND ad = 'Vize'),
       95, 'Maddi hata duzeltmesi') IS NULL
     AND (SELECT yeni ->> '_gerekce' FROM denetim_log WHERE tablo = 'not_kaydi' ORDER BY log_id DESC LIMIT 1) = 'Maddi hata duzeltmesi')::text$q$, 'true');

-- 6) Belge uretimi ve dogrulamasi
SELECT set_config('app.kullanici_id', pg_temp.ogr('2025002')::text, true);
SELECT pg_temp.esit_bekle('Cem: Belge uretir ve dogrulanir',
  $q$SELECT gecerli || '/' || ogrenci_no FROM fn_belge_dogrula(fn_belge_uret('transkript'))$q$, 'true/2025002');

ROLLBACK;
