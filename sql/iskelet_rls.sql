-- =====================================================================
-- sql/iskelet_rls.sql -- Satir duzeyi guvenlik (RLS) ISKELETI: yalnizca `kayit` tablosu icin ornek
-- On kosul: 001..004.  Super kullanici ile calistirin.  Tekrar calistirilabilir.
-- UYARI: Tablo sahibi ve super kullanici RLS'yi ATLAR. Uygulama bu rollerle (obs_app) baglanmali.
-- Asama B'de ayni kalip diger tablolara uygulanir (docs/VERITABANI_API_VE_EKRANLAR.md, "RLS matrisi").
-- =====================================================================

-- Roller (grup rolleri oturum acamaz; uygulama islem basina SET LOCAL ROLE ile birini secer)
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['rol_ogrenci','rol_danisman','rol_ogretim_uyesi','rol_sekreter','rol_yonetici'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', r);
    END IF;
  END LOOP;
END $$;
-- Uygulama girisi (parolayi degistirin; .env'de tutun, GitHub'a yuklemeyin):
--   CREATE ROLE obs_app LOGIN PASSWORD '...' NOINHERIT;
--   GRANT rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici TO obs_app;

GRANT SELECT ON kayit, danismanlik, ogrenci, sube
  TO rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici;

ALTER TABLE kayit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kayit_ogrenci ON kayit;
CREATE POLICY kayit_ogrenci ON kayit FOR SELECT TO rol_ogrenci
  USING (ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int);

DROP POLICY IF EXISTS kayit_danisman ON kayit;
CREATE POLICY kayit_danisman ON kayit FOR SELECT TO rol_danisman
  USING (EXISTS (SELECT 1 FROM danismanlik d
                  WHERE d.ogrenci_id = kayit.ogrenci_id
                    AND d.danisman_id = nullif(current_setting('app.kullanici_id', true), '')::int
                    AND d.gecerlilik @> current_date));

DROP POLICY IF EXISTS kayit_ogretim_uyesi ON kayit;
CREATE POLICY kayit_ogretim_uyesi ON kayit FOR SELECT TO rol_ogretim_uyesi
  USING (EXISTS (SELECT 1 FROM sube s
                  WHERE s.sube_id = kayit.sube_id
                    AND s.ogretim_uyesi_id = nullif(current_setting('app.kullanici_id', true), '')::int));

DROP POLICY IF EXISTS kayit_yonetim ON kayit;
CREATE POLICY kayit_yonetim ON kayit FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- ONEMLI: gorunumler varsayilan olarak SAHIBIN yetkisiyle calisir ve RLS'yi atlar.
-- Kullaniciya gosterilecek her gorunum security_invoker ile olusturulmali (PostgreSQL 15+):
CREATE OR REPLACE VIEW v_kayitlarim WITH (security_invoker = true) AS
SELECT k.kayit_id, k.ogrenci_id, d.kod AS ders_kod, d.ad AS ders_ad, d.akts, s.sube_no, k.donem_id, k.durum
FROM kayit k
JOIN sube s ON s.sube_id = k.sube_id
JOIN ders d ON d.ders_id = k.ders_id;
GRANT SELECT ON v_kayitlarim, ders TO rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici;

-- Hizli dogrulama (super kullanici olarak):
--   BEGIN;
--   SELECT set_config('app.kullanici_id', (SELECT kisi_id::text FROM ogrenci WHERE ogrenci_no = '2025002'), true);
--   SET LOCAL ROLE rol_ogrenci;
--   SELECT count(*) FROM v_kayitlarim;      -- yalnizca kendi kayitlari (ornek veride 4)
--   ROLLBACK;
