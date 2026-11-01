-- =====================================================================
-- 009_yonetici_ekleme_ve_optimizasyon.sql
-- 1) Sistem Yoneticisi icin Ogrenci, Akademisyen/Ogretmen, Ders ve Sube
--    ekleme fonksiyonlari (SECURITY DEFINER + SHA-256 denetim_log izi)
-- 2) Otomatik 5 haneli numara ureticileri (fn_sonraki_ogrenci_no, fn_sonraki_akademisyen_no)
-- 3) Yonetim paneli okuma gorunumleri ve sorgu optimizasyon indeksleri
-- =====================================================================
BEGIN;

-- ---------------------------------------------------------------------
-- 1) PERFORMANS INDEKSLERI VE DENETIM TETIKLEYICILERI
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_kisi_kullanici_no ON kisi (kullanici_no);
CREATE INDEX IF NOT EXISTS ix_kayit_onay_kayit_zaman ON kayit_onay (kayit_id, zaman DESC, onay_id DESC);
CREATE INDEX IF NOT EXISTS ix_mufredat_ders_ders ON mufredat_ders (ders_id);

DROP TRIGGER IF EXISTS trg_denetim ON ogrenci;
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON ogrenci
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kisi_id');

DROP TRIGGER IF EXISTS trg_denetim ON ogretim_uyesi;
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON ogretim_uyesi
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kisi_id');

DROP TRIGGER IF EXISTS trg_denetim ON ders;
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON ders
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('ders_id');

DROP TRIGGER IF EXISTS trg_denetim ON sube;
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON sube
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('sube_id');

-- ---------------------------------------------------------------------
-- 2) OTOMATIK 5 HANELI NUMARA URETICILERI
-- ---------------------------------------------------------------------
-- Ogrenci numarasi kurali: [YY][B][SS] -> orn: 25106, 26101
CREATE OR REPLACE FUNCTION fn_sonraki_ogrenci_no(p_giris_yili smallint, p_program_id int)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_yy text := lpad((p_giris_yili % 100)::text, 2, '0');
  v_bolum_ad text;
  v_b_kod text := '1';
  v_max_sira int := 0;
  v_aday text;
BEGIN
  SELECT b.ad INTO v_bolum_ad
    FROM program p JOIN bolum b ON b.bolum_id = p.bolum_id
   WHERE p.program_id = p_program_id;

  IF v_bolum_ad ILIKE '%Yazılım%' THEN
    v_b_kod := '2';
  ELSIF v_bolum_ad ILIKE '%Yapay Zeka%' THEN
    v_b_kod := '3';
  ELSE
    v_b_kod := '1';
  END IF;

  SELECT COALESCE(MAX(right(ogrenci_no, 2)::int), 0)
    INTO v_max_sira
    FROM ogrenci
   WHERE left(ogrenci_no, 2) = v_yy
     AND ogrenci_no ~ '^[0-9]{5}$';

  LOOP
    v_max_sira := v_max_sira + 1;
    v_aday := v_yy || v_b_kod || lpad(v_max_sira::text, 2, '0');
    EXIT WHEN NOT EXISTS (
      SELECT 1 FROM ogrenci WHERE ogrenci_no = v_aday
      UNION ALL
      SELECT 1 FROM kisi WHERE kullanici_no = v_aday
    );
  END LOOP;

  RETURN v_aday;
END $$;

-- Akademisyen numarasi kurali: 10[B][SS] -> orn: 10104, 10202
CREATE OR REPLACE FUNCTION fn_sonraki_akademisyen_no(p_bolum_id int)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_bolum_ad text;
  v_b_kod text := '1';
  v_max_sira int := 0;
  v_aday text;
BEGIN
  SELECT ad INTO v_bolum_ad FROM bolum WHERE bolum_id = p_bolum_id;
  IF v_bolum_ad ILIKE '%Yazılım%' THEN
    v_b_kod := '2';
  ELSIF v_bolum_ad ILIKE '%Yapay Zeka%' THEN
    v_b_kod := '3';
  ELSE
    v_b_kod := '1';
  END IF;

  SELECT COALESCE(MAX(right(kullanici_no, 2)::int), 0)
    INTO v_max_sira
    FROM kisi
   WHERE left(kullanici_no, 3) = ('10' || v_b_kod)
     AND kullanici_no ~ '^[0-9]{5}$';

  LOOP
    v_max_sira := v_max_sira + 1;
    v_aday := '10' || v_b_kod || lpad(v_max_sira::text, 2, '0');
    EXIT WHEN NOT EXISTS (SELECT 1 FROM kisi WHERE kullanici_no = v_aday);
  END LOOP;

  RETURN v_aday;
END $$;

-- ---------------------------------------------------------------------
-- 3) YONETICI KAYIT EKLEME FONKSIYONLARI (SECURITY DEFINER)
-- ---------------------------------------------------------------------

-- A) Yeni Ogrenci Ekle
CREATE OR REPLACE FUNCTION fn_yonetici_ogrenci_ekle(
  p_ad text,
  p_soyad text,
  p_eposta text,
  p_ogrenci_no varchar(12),
  p_program_id int,
  p_giris_yili smallint,
  p_danisman_id int DEFAULT NULL,
  p_sifre text DEFAULT '123456'
)
RETURNS TABLE (kisi_id int, ogrenci_no text, ad_soyad text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_kul int := fn_oturum_kisi_id();
  v_ogr_no text;
  v_eposta text;
  v_mufredat_id int;
  v_kaynak_mufredat int;
  v_kisi_id int;
  v_danisman int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('yonetici', 'sekreter')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sistem yoneticisi veya sekreter yeni ogrenci ekleyebilir';
  END IF;

  IF length(trim(coalesce(p_ad, ''))) = 0 OR length(trim(coalesce(p_soyad, ''))) = 0 THEN
    RAISE EXCEPTION 'GEREKCE_ZORUNLU: ogrenci ad ve soyad alanlari bos birakilamaz';
  END IF;

  v_ogr_no := nullif(trim(coalesce(p_ogrenci_no, '')), '');
  IF v_ogr_no IS NULL THEN
    v_ogr_no := fn_sonraki_ogrenci_no(p_giris_yili, p_program_id);
  END IF;

  IF EXISTS (SELECT 1 FROM ogrenci o WHERE o.ogrenci_no = v_ogr_no)
     OR EXISTS (SELECT 1 FROM kisi k WHERE k.kullanici_no = v_ogr_no) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % numarali kullanici/ogrenci zaten kayitli', v_ogr_no;
  END IF;

  v_eposta := nullif(trim(coalesce(p_eposta, '')), '');
  IF v_eposta IS NULL THEN
    v_eposta := v_ogr_no || '@ogrenci.edu.tr';
  END IF;

  IF EXISTS (SELECT 1 FROM kisi k WHERE lower(k.eposta) = lower(v_eposta)) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % e-posta adresi baska bir kayitta kullaniliyor', v_eposta;
  END IF;

  -- Ilgili program ve giris yili icin mufredat yoksa olustur ve derslerini kopyala
  SELECT m.mufredat_id INTO v_mufredat_id
    FROM mufredat m
   WHERE m.program_id = p_program_id AND m.giris_yili = p_giris_yili;

  IF v_mufredat_id IS NULL THEN
    SELECT m.mufredat_id INTO v_kaynak_mufredat
      FROM mufredat m
     WHERE m.program_id = p_program_id
     ORDER BY m.giris_yili DESC LIMIT 1;

    INSERT INTO mufredat (program_id, giris_yili)
    VALUES (p_program_id, p_giris_yili)
    RETURNING mufredat_id INTO v_mufredat_id;

    IF v_kaynak_mufredat IS NOT NULL THEN
      INSERT INTO mufredat_ders (mufredat_id, ders_id, donem_no, tur)
      SELECT v_mufredat_id, md.ders_id, md.donem_no, md.tur
        FROM mufredat_ders md
       WHERE md.mufredat_id = v_kaynak_mufredat
      ON CONFLICT DO NOTHING;

      INSERT INTO gereksinim_grubu (mufredat_id, ad, tur, min_ders, min_akts, oncelik, cift_sayim)
      SELECT v_mufredat_id, gg.ad, gg.tur, gg.min_ders, gg.min_akts, gg.oncelik, gg.cift_sayim
        FROM gereksinim_grubu gg
       WHERE gg.mufredat_id = v_kaynak_mufredat
      ON CONFLICT DO NOTHING;

      INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
      SELECT g_yeni.grup_id, md.ders_id
        FROM gereksinim_grubu g_yeni
        JOIN mufredat_ders md ON md.mufredat_id = g_yeni.mufredat_id
       WHERE g_yeni.mufredat_id = v_mufredat_id
         AND ((g_yeni.tur = 'zorunlu' AND md.tur = 'zorunlu')
              OR (g_yeni.tur = 'secmeli_havuz' AND md.tur = 'secmeli'))
      ON CONFLICT DO NOTHING;
    END IF;
  END IF;

  INSERT INTO kisi (ad, soyad, eposta, kullanici_no, sifre)
  VALUES (trim(p_ad), trim(p_soyad), v_eposta, v_ogr_no, coalesce(nullif(trim(p_sifre), ''), '123456'))
  RETURNING kisi.kisi_id INTO v_kisi_id;

  INSERT INTO ogrenci (kisi_id, ogrenci_no, program_id, mufredat_id, giris_yili, durum)
  VALUES (v_kisi_id, v_ogr_no, p_program_id, v_mufredat_id, p_giris_yili, 'aktif');

  INSERT INTO kisi_rol (kisi_id, rol)
  VALUES (v_kisi_id, 'ogrenci')
  ON CONFLICT DO NOTHING;

  v_danisman := p_danisman_id;
  IF v_danisman IS NULL THEN
    SELECT ou.kisi_id INTO v_danisman FROM ogretim_uyesi ou ORDER BY ou.kisi_id LIMIT 1;
  END IF;

  IF v_danisman IS NOT NULL THEN
    INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
    VALUES (v_kisi_id, v_danisman, daterange(current_date, NULL, '[)'));
  END IF;

  RETURN QUERY SELECT v_kisi_id, v_ogr_no, (trim(p_ad) || ' ' || trim(p_soyad))::text;
END $$;

-- B) Yeni Akademisyen / Ogretmen Ekle
CREATE OR REPLACE FUNCTION fn_yonetici_ogretmen_ekle(
  p_ad text,
  p_soyad text,
  p_eposta text,
  p_kullanici_no varchar(12),
  p_bolum_id int,
  p_unvan text DEFAULT 'Dr. Öğr. Üyesi',
  p_ek_rol text DEFAULT NULL,
  p_sifre text DEFAULT '123456'
)
RETURNS TABLE (kisi_id int, kullanici_no text, ad_soyad text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_kul int := fn_oturum_kisi_id();
  v_k_no text;
  v_eposta text;
  v_kisi_id int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol = 'yonetici') THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sistem yoneticisi yeni akademisyen/ogretmen ekleyebilir';
  END IF;

  IF length(trim(coalesce(p_ad, ''))) = 0 OR length(trim(coalesce(p_soyad, ''))) = 0 THEN
    RAISE EXCEPTION 'GEREKCE_ZORUNLU: akademisyen ad ve soyad alanlari bos birakilamaz';
  END IF;

  v_k_no := nullif(trim(coalesce(p_kullanici_no, '')), '');
  IF v_k_no IS NULL THEN
    v_k_no := fn_sonraki_akademisyen_no(p_bolum_id);
  END IF;

  IF EXISTS (SELECT 1 FROM kisi k WHERE k.kullanici_no = v_k_no)
     OR EXISTS (SELECT 1 FROM ogrenci o WHERE o.ogrenci_no = v_k_no) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % kullanici numarasi zaten kayitli', v_k_no;
  END IF;

  v_eposta := nullif(trim(coalesce(p_eposta, '')), '');
  IF v_eposta IS NULL THEN
    v_eposta := v_k_no || '@ornek.edu.tr';
  END IF;

  IF EXISTS (SELECT 1 FROM kisi k WHERE lower(k.eposta) = lower(v_eposta)) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % e-posta adresi zaten kayitli', v_eposta;
  END IF;

  INSERT INTO kisi (ad, soyad, eposta, kullanici_no, sifre)
  VALUES (trim(p_ad), trim(p_soyad), v_eposta, v_k_no, coalesce(nullif(trim(p_sifre), ''), '123456'))
  RETURNING kisi.kisi_id INTO v_kisi_id;

  INSERT INTO ogretim_uyesi (kisi_id, bolum_id, unvan)
  VALUES (v_kisi_id, p_bolum_id, coalesce(nullif(trim(p_unvan), ''), 'Dr. Öğr. Üyesi'));

  INSERT INTO kisi_rol (kisi_id, rol)
  VALUES (v_kisi_id, 'ogretim_uyesi')
  ON CONFLICT DO NOTHING;

  IF p_ek_rol IN ('sekreter', 'yonetici') THEN
    INSERT INTO kisi_rol (kisi_id, rol)
    VALUES (v_kisi_id, p_ek_rol)
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN QUERY SELECT v_kisi_id, v_k_no, (coalesce(nullif(trim(p_unvan), ''), 'Dr. Öğr. Üyesi') || ' ' || trim(p_ad) || ' ' || trim(p_soyad))::text;
END $$;

-- C) Yeni Ders (ve Mufredat + Onkosul + Aktif Sube) Ekle
CREATE OR REPLACE FUNCTION fn_yonetici_ders_ekle(
  p_kod varchar(12),
  p_ad text,
  p_akts smallint,
  p_teorik smallint DEFAULT 3,
  p_uygulama smallint DEFAULT 0,
  p_donem_no smallint DEFAULT 1,
  p_tur varchar(8) DEFAULT 'zorunlu',
  p_onkosul_ders_id int DEFAULT NULL,
  p_onkosul_min_harf varchar(2) DEFAULT 'DD',
  p_aktif_sube_hoca_id int DEFAULT NULL,
  p_sube_gun smallint DEFAULT NULL,
  p_sube_saat smallint DEFAULT NULL
)
RETURNS TABLE (ders_id int, kod text, acilan_sube_id int)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_kul int := fn_oturum_kisi_id();
  v_kod text := upper(trim(coalesce(p_kod, '')));
  v_ad text := trim(coalesce(p_ad, ''));
  v_ders_id int;
  v_sube_id int := NULL;
  v_aktif_donem int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('yonetici', 'sekreter')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sistem yoneticisi veya sekreter yeni ders ekleyebilir';
  END IF;

  IF length(v_kod) < 3 OR length(v_ad) < 2 THEN
    RAISE EXCEPTION 'GEREKCE_ZORUNLU: ders kodu ve ders adi gecerli olmalidir';
  END IF;

  IF EXISTS (SELECT 1 FROM ders d WHERE upper(d.kod) = v_kod) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % kodlu ders sistemde zaten mevcut', v_kod;
  END IF;

  INSERT INTO ders (kod, ad, akts, teorik_saat, uygulama_saat)
  VALUES (v_kod, v_ad, p_akts, p_teorik, p_uygulama)
  RETURNING ders.ders_id INTO v_ders_id;

  -- Tum mevcut mufredatlara ve uygun gereksinim gruplarina bagla
  INSERT INTO mufredat_ders (mufredat_id, ders_id, donem_no, tur)
  SELECT m.mufredat_id, v_ders_id, p_donem_no, p_tur
    FROM mufredat m
  ON CONFLICT (mufredat_id, ders_id) DO NOTHING;

  INSERT INTO gereksinim_grubu_ders (grup_id, ders_id)
  SELECT g.grup_id, v_ders_id
    FROM gereksinim_grubu g
   WHERE (g.tur = 'zorunlu' AND p_tur = 'zorunlu')
      OR (g.tur = 'secmeli_havuz' AND p_tur = 'secmeli')
  ON CONFLICT (grup_id, ders_id) DO NOTHING;

  -- Onkosul secildiyse ekle (trg_onkosul_dongu DAG kontrolu yapar)
  IF p_onkosul_ders_id IS NOT NULL THEN
    INSERT INTO onkosul (ders_id, onkosul_ders_id, min_harf)
    VALUES (v_ders_id, p_onkosul_ders_id, coalesce(p_onkosul_min_harf, 'DD'))
    ON CONFLICT (ders_id, onkosul_ders_id) DO NOTHING;
  END IF;

  -- Aktif donemde sube acilmasi istendiyse
  IF p_aktif_sube_hoca_id IS NOT NULL THEN
    v_aktif_donem := fn_aktif_donem_id();
    INSERT INTO sube (ders_id, donem_id, sube_no, ogretim_uyesi_id)
    VALUES (v_ders_id, v_aktif_donem, 1, p_aktif_sube_hoca_id)
    RETURNING sube.sube_id INTO v_sube_id;

    INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik) VALUES
      (v_sube_id, 'Vize', 40.00),
      (v_sube_id, 'Final', 60.00)
    ON CONFLICT DO NOTHING;

    IF p_sube_gun IS NOT NULL AND p_sube_saat IS NOT NULL THEN
      INSERT INTO sube_saat (sube_id, gun, ders_saati)
      VALUES (v_sube_id, p_sube_gun, p_sube_saat)
      ON CONFLICT DO NOTHING;
      IF p_sube_saat < 8 THEN
        INSERT INTO sube_saat (sube_id, gun, ders_saati)
        VALUES (v_sube_id, p_sube_gun, p_sube_saat + 1)
        ON CONFLICT DO NOTHING;
      END IF;
    END IF;
  END IF;

  RETURN QUERY SELECT v_ders_id, v_kod, v_sube_id;
END $$;

-- ---------------------------------------------------------------------
-- 4) YONETIM GORUNUMLERI
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_yonetici_ogrenciler WITH (security_invoker = true) AS
SELECT o.kisi_id,
       o.ogrenci_no,
       k.ad || ' ' || k.soyad AS ad_soyad,
       k.eposta,
       p.ad AS program_ad,
       o.giris_yili,
       o.durum,
       coalesce(g.gno::text, '-') AS gno,
       coalesce(g.gecilen_akts, 0)::int AS gecilen_akts,
       coalesce((
         SELECT ou.unvan || ' ' || kd.ad || ' ' || kd.soyad
           FROM danismanlik d
           JOIN ogretim_uyesi ou ON ou.kisi_id = d.danisman_id
           JOIN kisi kd ON kd.kisi_id = ou.kisi_id
          WHERE d.ogrenci_id = o.kisi_id AND d.gecerlilik @> current_date
          LIMIT 1
       ), 'Atanmamış') AS danisman_ad
  FROM ogrenci o
  JOIN kisi k ON k.kisi_id = o.kisi_id
  JOIN program p ON p.program_id = o.program_id
  LEFT JOIN v_gno g ON g.ogrenci_id = o.kisi_id
 ORDER BY o.ogrenci_no DESC;

CREATE OR REPLACE VIEW v_yonetici_akademisyenler WITH (security_invoker = true) AS
SELECT ou.kisi_id,
       coalesce(k.kullanici_no, '-') AS kullanici_no,
       ou.unvan,
       k.ad || ' ' || k.soyad AS ad_soyad,
       k.eposta,
       b.ad AS bolum_ad,
       (SELECT count(*)::int FROM sube s WHERE s.ogretim_uyesi_id = ou.kisi_id AND s.donem_id = fn_aktif_donem_id()) AS aktif_sube_sayisi,
       (SELECT count(*)::int FROM danismanlik dn WHERE dn.danisman_id = ou.kisi_id AND dn.gecerlilik @> current_date) AS danisan_sayisi
  FROM ogretim_uyesi ou
  JOIN kisi k ON k.kisi_id = ou.kisi_id
  JOIN bolum b ON b.bolum_id = ou.bolum_id
 ORDER BY k.kullanici_no, ou.kisi_id;

CREATE OR REPLACE VIEW v_yonetici_dersler WITH (security_invoker = true) AS
SELECT d.ders_id,
       d.kod,
       d.ad,
       d.akts,
       d.teorik_saat || '+' || d.uygulama_saat AS saat_bilgi,
       coalesce((SELECT md.donem_no FROM mufredat_ders md WHERE md.ders_id = d.ders_id LIMIT 1), 1) AS donem_no,
       coalesce((SELECT md.tur FROM mufredat_ders md WHERE md.ders_id = d.ders_id LIMIT 1), 'zorunlu') AS tur,
       coalesce((
         SELECT string_agg(d_onk.kod || ' (' || ok.min_harf || ')', ', ')
           FROM onkosul ok JOIN ders d_onk ON d_onk.ders_id = ok.onkosul_ders_id
          WHERE ok.ders_id = d.ders_id
       ), '—') AS onkosullar,
       (SELECT count(*)::int FROM sube s WHERE s.ders_id = d.ders_id AND s.donem_id = fn_aktif_donem_id()) AS aktif_sube_sayisi
  FROM ders d
 ORDER BY donem_no, d.kod;

-- ---------------------------------------------------------------------
-- 5) YETKILER (GRANT)
-- ---------------------------------------------------------------------
GRANT SELECT ON v_yonetici_ogrenciler, v_yonetici_akademisyenler, v_yonetici_dersler
  TO rol_yonetici, rol_sekreter;

GRANT EXECUTE ON FUNCTION
  fn_sonraki_ogrenci_no(smallint, int),
  fn_sonraki_akademisyen_no(int),
  fn_yonetici_ogrenci_ekle(text, text, text, varchar, int, smallint, int, text),
  fn_yonetici_ogretmen_ekle(text, text, text, varchar, int, text, text, text),
  fn_yonetici_ders_ekle(varchar, text, smallint, smallint, smallint, smallint, varchar, int, varchar, int, smallint, smallint)
TO rol_yonetici, rol_sekreter;

COMMIT;
