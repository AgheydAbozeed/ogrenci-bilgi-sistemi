-- =====================================================================
-- 007_yetki.sql -- Asama B (Parca 2): Roller, Satir Duzeyi Guvenlik (RLS) ve Yetkiler
-- On kosul: 001..006 yuklu.   Calistirma: psql -d obs -f sql/007_yetki.sql
-- =====================================================================

-- 1) ROLLER VE ORNEK YONETICI KULLANICISI -----------------------------
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['rol_ogrenci','rol_danisman','rol_ogretim_uyesi','rol_sekreter','rol_yonetici','obs_login'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', r);
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'obs_app') THEN
    CREATE ROLE obs_app LOGIN PASSWORD 'obs_pass' NOINHERIT;
  END IF;
END $$;

GRANT rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici, obs_login TO obs_app;
GRANT rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici, obs_login TO CURRENT_USER;

-- Ornek veride yonetici yoksa ekle (demo ve testler icin)
INSERT INTO kisi (ad, soyad, eposta) VALUES ('Yavuz', 'Yonetici', 'yonetici@ornek.edu')
ON CONFLICT (eposta) DO NOTHING;
INSERT INTO kisi_rol (kisi_id, rol)
SELECT kisi_id, 'yonetici' FROM kisi WHERE eposta = 'yonetici@ornek.edu'
ON CONFLICT DO NOTHING;

-- 2) RLS (ROW LEVEL SECURITY) POLITIKALARI (§1.4 RLS Matrisi) ---------
-- Yardimci: Sonsuz dongu (recursion) olmamasi icin tablo sahibinin yetkisiyle calisan kontrol fonksiyonlari
CREATE OR REPLACE FUNCTION fn_rls_danisani_mi(p_ogrenci int) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM danismanlik
     WHERE ogrenci_id = p_ogrenci
       AND danisman_id = nullif(current_setting('app.kullanici_id', true), '')::int
       AND gecerlilik @> current_date
  );
$$;

CREATE OR REPLACE FUNCTION fn_rls_hocanin_subesi_mi(p_sube int) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM sube
     WHERE sube_id = p_sube
       AND ogretim_uyesi_id = nullif(current_setting('app.kullanici_id', true), '')::int
  );
$$;

CREATE OR REPLACE FUNCTION fn_rls_hocanin_ogrencisi_mi(p_ogrenci int) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM kayit k JOIN sube s ON s.sube_id = k.sube_id
     WHERE k.ogrenci_id = p_ogrenci
       AND s.ogretim_uyesi_id = nullif(current_setting('app.kullanici_id', true), '')::int
  );
$$;

CREATE OR REPLACE FUNCTION fn_rls_kayit_erisim(p_kayit int, p_rol text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM kayit k
     WHERE k.kayit_id = p_kayit
       AND (
         (p_rol = 'ogrenci'       AND k.ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int) OR
         (p_rol = 'danisman'      AND fn_rls_danisani_mi(k.ogrenci_id)) OR
         (p_rol = 'ogretim_uyesi' AND fn_rls_hocanin_subesi_mi(k.sube_id))
       )
  );
$$;

-- A) kayit
ALTER TABLE kayit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS kayit_ogrenci ON kayit;
CREATE POLICY kayit_ogrenci ON kayit FOR SELECT TO rol_ogrenci
  USING (ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS kayit_danisman ON kayit;
CREATE POLICY kayit_danisman ON kayit FOR SELECT TO rol_danisman
  USING (fn_rls_danisani_mi(ogrenci_id));
DROP POLICY IF EXISTS kayit_ogretim_uyesi ON kayit;
CREATE POLICY kayit_ogretim_uyesi ON kayit FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_hocanin_subesi_mi(sube_id));
DROP POLICY IF EXISTS kayit_yonetim ON kayit;
CREATE POLICY kayit_yonetim ON kayit FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- B) kayit_onay
ALTER TABLE kayit_onay ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS kayit_onay_ogrenci ON kayit_onay;
CREATE POLICY kayit_onay_ogrenci ON kayit_onay FOR SELECT TO rol_ogrenci
  USING (fn_rls_kayit_erisim(kayit_id, 'ogrenci'));
DROP POLICY IF EXISTS kayit_onay_danisman ON kayit_onay;
CREATE POLICY kayit_onay_danisman ON kayit_onay FOR SELECT TO rol_danisman
  USING (fn_rls_kayit_erisim(kayit_id, 'danisman'));
DROP POLICY IF EXISTS kayit_onay_hoca ON kayit_onay;
CREATE POLICY kayit_onay_hoca ON kayit_onay FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_kayit_erisim(kayit_id, 'ogretim_uyesi'));
DROP POLICY IF EXISTS kayit_onay_yonetim ON kayit_onay;
CREATE POLICY kayit_onay_yonetim ON kayit_onay FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- C) ogrenci_slot
ALTER TABLE ogrenci_slot ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS slot_ogrenci ON ogrenci_slot;
CREATE POLICY slot_ogrenci ON ogrenci_slot FOR SELECT TO rol_ogrenci
  USING (ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS slot_danisman ON ogrenci_slot;
CREATE POLICY slot_danisman ON ogrenci_slot FOR SELECT TO rol_danisman
  USING (fn_rls_danisani_mi(ogrenci_id));
DROP POLICY IF EXISTS slot_hoca ON ogrenci_slot;
CREATE POLICY slot_hoca ON ogrenci_slot FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_kayit_erisim(kayit_id, 'ogretim_uyesi'));
DROP POLICY IF EXISTS slot_yonetim ON ogrenci_slot;
CREATE POLICY slot_yonetim ON ogrenci_slot FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- D) not_kaydi (ogrenci ve danisman yalniz ilan_edildi=true gorur; yonetici goremez)
ALTER TABLE not_kaydi ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS not_ogrenci ON not_kaydi;
CREATE POLICY not_ogrenci ON not_kaydi FOR SELECT TO rol_ogrenci
  USING (ilan_edildi AND fn_rls_kayit_erisim(kayit_id, 'ogrenci'));
DROP POLICY IF EXISTS not_danisman ON not_kaydi;
CREATE POLICY not_danisman ON not_kaydi FOR SELECT TO rol_danisman
  USING (ilan_edildi AND fn_rls_kayit_erisim(kayit_id, 'danisman'));
DROP POLICY IF EXISTS not_hoca ON not_kaydi;
CREATE POLICY not_hoca ON not_kaydi FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_hocanin_subesi_mi(sube_id));
DROP POLICY IF EXISTS not_sekreter ON not_kaydi;
CREATE POLICY not_sekreter ON not_kaydi FOR SELECT TO rol_sekreter USING (true);

-- E) kayit_sonuc ve yoklama (yonetici goremez)
ALTER TABLE kayit_sonuc ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sonuc_ogrenci ON kayit_sonuc;
CREATE POLICY sonuc_ogrenci ON kayit_sonuc FOR SELECT TO rol_ogrenci
  USING (fn_rls_kayit_erisim(kayit_id, 'ogrenci'));
DROP POLICY IF EXISTS sonuc_danisman ON kayit_sonuc;
CREATE POLICY sonuc_danisman ON kayit_sonuc FOR SELECT TO rol_danisman
  USING (fn_rls_kayit_erisim(kayit_id, 'danisman'));
DROP POLICY IF EXISTS sonuc_hoca ON kayit_sonuc;
CREATE POLICY sonuc_hoca ON kayit_sonuc FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_kayit_erisim(kayit_id, 'ogretim_uyesi'));
DROP POLICY IF EXISTS sonuc_sekreter ON kayit_sonuc;
CREATE POLICY sonuc_sekreter ON kayit_sonuc FOR SELECT TO rol_sekreter USING (true);

ALTER TABLE yoklama ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS yoklama_ogrenci ON yoklama;
CREATE POLICY yoklama_ogrenci ON yoklama FOR SELECT TO rol_ogrenci
  USING (fn_rls_kayit_erisim(kayit_id, 'ogrenci'));
DROP POLICY IF EXISTS yoklama_danisman ON yoklama;
CREATE POLICY yoklama_danisman ON yoklama FOR SELECT TO rol_danisman
  USING (fn_rls_kayit_erisim(kayit_id, 'danisman'));
DROP POLICY IF EXISTS yoklama_hoca ON yoklama;
CREATE POLICY yoklama_hoca ON yoklama FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_kayit_erisim(kayit_id, 'ogretim_uyesi'));
DROP POLICY IF EXISTS yoklama_sekreter ON yoklama;
CREATE POLICY yoklama_sekreter ON yoklama FOR SELECT TO rol_sekreter USING (true);

-- F) degerlendirme_bileseni
ALTER TABLE degerlendirme_bileseni ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS bilesen_okuma ON degerlendirme_bileseni;
CREATE POLICY bilesen_okuma ON degerlendirme_bileseni FOR SELECT
  TO rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici USING (true);

-- G) ogrenci ve kisi
ALTER TABLE ogrenci ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ogrenci_kendi ON ogrenci;
CREATE POLICY ogrenci_kendi ON ogrenci FOR SELECT TO rol_ogrenci
  USING (kisi_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS ogrenci_danisman ON ogrenci;
CREATE POLICY ogrenci_danisman ON ogrenci FOR SELECT TO rol_danisman
  USING (fn_rls_danisani_mi(kisi_id));
DROP POLICY IF EXISTS ogrenci_hoca ON ogrenci;
CREATE POLICY ogrenci_hoca ON ogrenci FOR SELECT TO rol_ogretim_uyesi
  USING (fn_rls_hocanin_ogrencisi_mi(kisi_id));
DROP POLICY IF EXISTS ogrenci_yonetim ON ogrenci;
CREATE POLICY ogrenci_yonetim ON ogrenci FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

ALTER TABLE kisi ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS kisi_ogrenci ON kisi;
CREATE POLICY kisi_ogrenci ON kisi FOR SELECT TO rol_ogrenci
  USING (kisi_id = nullif(current_setting('app.kullanici_id', true), '')::int
         OR EXISTS (SELECT 1 FROM ogretim_uyesi ou WHERE ou.kisi_id = kisi.kisi_id));
DROP POLICY IF EXISTS kisi_danisman ON kisi;
CREATE POLICY kisi_danisman ON kisi FOR SELECT TO rol_danisman
  USING (kisi_id = nullif(current_setting('app.kullanici_id', true), '')::int
         OR fn_rls_danisani_mi(kisi_id)
         OR EXISTS (SELECT 1 FROM ogretim_uyesi ou WHERE ou.kisi_id = kisi.kisi_id));
DROP POLICY IF EXISTS kisi_hoca ON kisi;
CREATE POLICY kisi_hoca ON kisi FOR SELECT TO rol_ogretim_uyesi
  USING (kisi_id = nullif(current_setting('app.kullanici_id', true), '')::int
         OR fn_rls_hocanin_ogrencisi_mi(kisi_id)
         OR EXISTS (SELECT 1 FROM ogretim_uyesi ou WHERE ou.kisi_id = kisi.kisi_id));
DROP POLICY IF EXISTS kisi_yonetim ON kisi;
CREATE POLICY kisi_yonetim ON kisi FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- H) danismanlik
ALTER TABLE danismanlik ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS danismanlik_ogrenci ON danismanlik;
CREATE POLICY danismanlik_ogrenci ON danismanlik FOR SELECT TO rol_ogrenci
  USING (ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS danismanlik_danisman ON danismanlik;
CREATE POLICY danismanlik_danisman ON danismanlik FOR SELECT TO rol_danisman
  USING (danisman_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS danismanlik_yonetim ON danismanlik;
CREATE POLICY danismanlik_yonetim ON danismanlik FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- I) risk_bayrak ve risk_tahmin (YALNIZ danisman kendi danisanlarini gorur; ogrenci asla goremez)
ALTER TABLE risk_bayrak ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS risk_bayrak_danisman ON risk_bayrak;
CREATE POLICY risk_bayrak_danisman ON risk_bayrak FOR SELECT TO rol_danisman
  USING (fn_rls_danisani_mi(ogrenci_id));

ALTER TABLE risk_tahmin ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS risk_tahmin_danisman ON risk_tahmin;
CREATE POLICY risk_tahmin_danisman ON risk_tahmin FOR SELECT TO rol_danisman
  USING (fn_rls_danisani_mi(ogrenci_id));

-- J) belge
ALTER TABLE belge ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS belge_ogrenci ON belge;
CREATE POLICY belge_ogrenci ON belge FOR SELECT TO rol_ogrenci
  USING (ogrenci_id = nullif(current_setting('app.kullanici_id', true), '')::int);
DROP POLICY IF EXISTS belge_yonetim ON belge;
CREATE POLICY belge_yonetim ON belge FOR SELECT TO rol_sekreter, rol_yonetici USING (true);

-- K) denetim_log (YALNIZ yonetici gorur)
ALTER TABLE denetim_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS denetim_log_yonetici ON denetim_log;
CREATE POLICY denetim_log_yonetici ON denetim_log FOR SELECT TO rol_yonetici USING (true);

-- 3) TABLO, GORUNUM VE FONKSIYON YETKILERI (GRANT / REVOKE) ------------
-- Tum tablolarda ve gorunumlerde SELECT yetkisi (RLS satirlari otomatik suzer)
GRANT SELECT ON ALL TABLES IN SCHEMA public
  TO rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici;

-- Giris rolu yalnizca v_demo_kullanicilar gorunumunu okuyabilir
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM obs_login;
GRANT SELECT ON v_demo_kullanicilar TO obs_login;

-- Fonksiyon yetkilerini PUBLIC'ten geri al, ilgili rollere dagit
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
  fn_oturum_kisi_id(), fn_aktif_donem_id(), fn_gno(int), fn_akts_limit(int),
  fn_onkosul_eksikleri(int, int), fn_log_hash(text, text, text, text, jsonb, jsonb, timestamptz),
  fn_rls_danisani_mi(int), fn_rls_hocanin_subesi_mi(int), fn_rls_hocanin_ogrencisi_mi(int),
  fn_rls_kayit_erisim(int, text), fn_belge_dogrula(text)
TO rol_ogrenci, rol_danisman, rol_ogretim_uyesi, rol_sekreter, rol_yonetici;

GRANT EXECUTE ON FUNCTION
  fn_sepete_ekle(int), fn_sepetten_cikar(int), fn_kesinlestir(int), fn_kesinlestir_hepsi(),
  fn_birak(int), fn_mezuniyet_ozet_ben(), fn_mezuniyet_denetim_ben(int),
  fn_ders_plani_ben(int), fn_en_erken_mezuniyet_ben(int), fn_belge_uret(text),
  fn_mezuniyet_ozet(int), fn_mezuniyet_denetim(int, int), fn_ders_plani(int, int), fn_en_erken_mezuniyet(int, int)
TO rol_ogrenci;

GRANT EXECUTE ON FUNCTION
  fn_danisman_karar_ben(int, text, text), fn_danisman_karar(int, int, text, text),
  fn_mezuniyet_ozet_danisan(int), fn_mezuniyet_denetim_danisan(int, int),
  fn_mezuniyet_ozet(int), fn_mezuniyet_denetim(int, int), fn_ders_plani(int, int), fn_en_erken_mezuniyet(int, int)
TO rol_danisman;

GRANT EXECUTE ON FUNCTION
  fn_bilesenleri_belirle(int, text[], numeric[]), fn_not_gir(int, int, numeric),
  fn_not_ilan_et(int), fn_sonuclari_hesapla(int), fn_sonuc_hesapla(int),
  fn_not_duzelt(int, int, numeric, text), fn_yoklama_gir(int, date, boolean)
TO rol_ogretim_uyesi;

GRANT EXECUTE ON FUNCTION
  fn_donem_ac(smallint, text, timestamptz, timestamptz, timestamptz, timestamptz),
  fn_sube_ac(int, int, smallint, int), fn_sube_saat_ekle(int, smallint, smallint),
  fn_danisman_ata(int, int, date), fn_risk_bayrak_hesapla(int)
TO rol_sekreter, rol_yonetici;

GRANT EXECUTE ON FUNCTION
  fn_parametre_guncelle(text, text), fn_denetim_dogrula()
TO rol_yonetici;
