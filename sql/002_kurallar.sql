-- =====================================================================
-- 002_kurallar.sql  --  Is kurallari VERITABANINDA: fonksiyon, gorunum, tetikleyici
-- On kosul: 001_sema.sql          Calistirma: psql -d obs -f sql/002_kurallar.sql
-- Hata kodlari mesajin basinda gelir: DONEM_KAPALI, ONKOSUL_EKSIK, CAKISMA, AKTS_ASIMI,
--   YETKISIZ, GECERSIZ_GECIS, GEREKCE_ZORUNLU, AGIRLIK_TOPLAMI, ONKOSUL_DONGUSU ...
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) DURUM MAKINESI (R-12): kayit durumlari yalnizca izinli gecislerle degisir
-- ---------------------------------------------------------------------
INSERT INTO kayit_gecis (onceki, sonraki) VALUES
  ('sepet','onay_bekliyor'), ('sepet','birakti'),
  ('onay_bekliyor','onayli'), ('onay_bekliyor','reddedildi'),
  ('onay_bekliyor','sepet'),  ('onay_bekliyor','birakti'),
  ('onayli','birakti')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- 2) NOT / ORTALAMA GORUNUMLERI VE FONKSIYONLARI (R-26)
-- ---------------------------------------------------------------------
-- Tekrar alinan derste hangi sonucun sayildigi parametre ile belirlenir (son | en_yuksek).
CREATE OR REPLACE VIEW v_gecerli_sonuc AS
SELECT DISTINCT ON (k.ogrenci_id, k.ders_id)
       k.ogrenci_id, k.ders_id, k.kayit_id, d.yil, d.tur AS donem_tur,
       s.harf, h.katsayi, s.durum, ds.akts
FROM kayit k
JOIN kayit_sonuc s      ON s.kayit_id = k.kayit_id AND s.durum IN ('gecti','kaldi')
JOIN harf_notu_aralik h ON h.harf = s.harf
JOIN donem d            ON d.donem_id = k.donem_id
JOIN ders ds            ON ds.ders_id = k.ders_id
ORDER BY k.ogrenci_id, k.ders_id,
         CASE WHEN (SELECT deger FROM parametre WHERE anahtar = 'tekrar_ders_kurali') = 'en_yuksek'
              THEN h.katsayi END DESC NULLS LAST,
         d.yil DESC,
         CASE d.tur WHEN 'yaz' THEN 3 WHEN 'bahar' THEN 2 ELSE 1 END DESC;

CREATE OR REPLACE FUNCTION fn_gno(p_ogrenci int) RETURNS numeric
LANGUAGE sql STABLE AS $$
  SELECT round(sum(akts * katsayi)::numeric / NULLIF(sum(akts), 0), 2)
  FROM v_gecerli_sonuc WHERE ogrenci_id = p_ogrenci;
$$;

CREATE OR REPLACE FUNCTION fn_akts_limit(p_ogrenci int) RETURNS int
LANGUAGE plpgsql STABLE AS $$
DECLARE v_gno numeric; v_limit int;
BEGIN
  v_gno := fn_gno(p_ogrenci);
  IF v_gno IS NOT NULL THEN
    SELECT max_akts INTO v_limit FROM akts_limit_kural WHERE v_gno >= min_gno AND v_gno < max_gno;
  END IF;
  IF v_limit IS NULL THEN
    SELECT deger::int INTO v_limit FROM parametre WHERE anahtar = 'akts_limit_varsayilan';
  END IF;
  RETURN v_limit;
END $$;

CREATE OR REPLACE VIEW v_gno AS
SELECT ogrenci_id, fn_gno(ogrenci_id) AS gno,
       sum(akts) FILTER (WHERE durum = 'gecti') AS gecilen_akts
FROM v_gecerli_sonuc GROUP BY ogrenci_id;

CREATE OR REPLACE VIEW v_transkript AS
SELECT o.ogrenci_no, kk.ad || ' ' || kk.soyad AS ad_soyad, d.yil, d.tur AS donem,
       ds.kod, ds.ad AS ders_adi, ds.akts, s.harf, h.katsayi, s.durum
FROM kayit k
JOIN ogrenci o   ON o.kisi_id = k.ogrenci_id
JOIN kisi kk     ON kk.kisi_id = o.kisi_id
JOIN donem d     ON d.donem_id = k.donem_id
JOIN ders ds     ON ds.ders_id = k.ders_id
JOIN kayit_sonuc s ON s.kayit_id = k.kayit_id
LEFT JOIN harf_notu_aralik h ON h.harf = s.harf;

-- ---------------------------------------------------------------------
-- 3) ONKOSUL (R-05) VE DONGU KORUMASI
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_onkosul_eksikleri(p_ogrenci int, p_ders int)
RETURNS TABLE (kod varchar) LANGUAGE sql STABLE AS $$
  SELECT d.kod
  FROM onkosul o
  JOIN ders d              ON d.ders_id = o.onkosul_ders_id
  JOIN harf_notu_aralik m  ON m.harf = o.min_harf
  WHERE o.ders_id = p_ders
    AND NOT EXISTS (
      SELECT 1 FROM v_gecerli_sonuc g
      WHERE g.ogrenci_id = p_ogrenci AND g.ders_id = o.onkosul_ders_id
        AND g.durum = 'gecti' AND g.katsayi >= m.katsayi);
$$;

-- Onkosul grafi DAG kalmali: yeni kenar bir dongu yaratiyorsa reddet (recursive CTE)
CREATE OR REPLACE FUNCTION fn_onkosul_dongu() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE zincir(ders_id) AS (
      SELECT NEW.onkosul_ders_id
      UNION
      SELECT o.onkosul_ders_id FROM onkosul o JOIN zincir z ON o.ders_id = z.ders_id
    )
    SELECT 1 FROM zincir WHERE ders_id = NEW.ders_id
  ) THEN
    RAISE EXCEPTION 'ONKOSUL_DONGUSU: % -> % bir dongu yaratir', NEW.ders_id, NEW.onkosul_ders_id;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_onkosul_dongu BEFORE INSERT OR UPDATE ON onkosul
  FOR EACH ROW EXECUTE FUNCTION fn_onkosul_dongu();

-- ---------------------------------------------------------------------
-- 4) KAYIT KURALLARI (R-01, R-02, R-05, R-07, R-12, R-15)
-- ---------------------------------------------------------------------
-- 'akts_kilidi' parametresi YALNIZCA demo icindir: 'kapali' iken eszamanli kesinlestirmeler
-- AKTS limitini asabilir (yazma carpikligi); 'acik' iken ogrenci satiri kilitlenir ve dogru calisir.
CREATE OR REPLACE FUNCTION fn_kayit_kurallar() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_donem donem%ROWTYPE;
  v_akts  int; v_toplam int; v_limit int; v_eksik text;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT s.ders_id, s.donem_id INTO NEW.ders_id, NEW.donem_id
      FROM sube s WHERE s.sube_id = NEW.sube_id;
    IF NEW.ders_id IS NULL THEN
      RAISE EXCEPTION 'SUBE_BULUNAMADI: %', NEW.sube_id;
    END IF;
    IF NEW.durum <> 'sepet' THEN
      RAISE EXCEPTION 'GECERSIZ_GECIS: kayit sepet durumunda baslar';
    END IF;
    SELECT string_agg(kod, ', ') INTO v_eksik FROM fn_onkosul_eksikleri(NEW.ogrenci_id, NEW.ders_id);
    IF v_eksik IS NOT NULL THEN
      RAISE EXCEPTION 'ONKOSUL_EKSIK: %', v_eksik;
    END IF;
    RETURN NEW;
  END IF;

  -- UPDATE
  IF NEW.ogrenci_id <> OLD.ogrenci_id OR NEW.sube_id <> OLD.sube_id THEN
    RAISE EXCEPTION 'KAYIT_DEGISTIRILEMEZ: ogrenci ve sube degistirilemez';
  END IF;

  IF NEW.durum <> OLD.durum THEN
    IF NOT EXISTS (SELECT 1 FROM kayit_gecis WHERE onceki = OLD.durum AND sonraki = NEW.durum) THEN
      RAISE EXCEPTION 'GECERSIZ_GECIS: % -> %', OLD.durum, NEW.durum;
    END IF;
    SELECT * INTO v_donem FROM donem WHERE donem_id = NEW.donem_id;

    -- sepet -> onay_bekliyor : kesinlestirme (Kontrol Et + Kesinlestir)
    IF OLD.durum = 'sepet' AND NEW.durum = 'onay_bekliyor' THEN
      IF now() NOT BETWEEN v_donem.kayit_baslangic AND v_donem.ekle_birak_bitis THEN
        RAISE EXCEPTION 'DONEM_KAPALI: kayit penceresi disinda';
      END IF;
      IF coalesce((SELECT deger FROM parametre WHERE anahtar = 'akts_kilidi'), 'acik') = 'acik' THEN
        PERFORM 1 FROM ogrenci WHERE kisi_id = NEW.ogrenci_id FOR UPDATE;  -- ayni ogrencinin esz. kesinlestirmelerini sirala
      END IF;
      SELECT akts INTO v_akts FROM ders WHERE ders_id = NEW.ders_id;
      SELECT coalesce(sum(d.akts), 0) INTO v_toplam
        FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
       WHERE k.ogrenci_id = NEW.ogrenci_id AND k.donem_id = NEW.donem_id
         AND k.durum IN ('onay_bekliyor','onayli') AND k.kayit_id <> NEW.kayit_id;
      v_limit := fn_akts_limit(NEW.ogrenci_id);
      IF v_toplam + v_akts > v_limit THEN
        RAISE EXCEPTION 'AKTS_ASIMI: % + % > limit %', v_toplam, v_akts, v_limit;
      END IF;
    END IF;

    -- onayli kaydi birakma yalnizca ekle-birak penceresi bitmeden
    IF OLD.durum = 'onayli' AND NEW.durum = 'birakti' AND now() > v_donem.ekle_birak_bitis THEN
      RAISE EXCEPTION 'DONEM_KAPALI: ekle-birak penceresi bitti';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_kayit_kurallar BEFORE INSERT OR UPDATE ON kayit
  FOR EACH ROW EXECUTE FUNCTION fn_kayit_kurallar();

-- ---------------------------------------------------------------------
-- 5) SAAT CAKISMASI (R-06): kayit durumuna gore ogrenci_slot satirlari tutulur;
--    ayni ogrenci/donem/gun/saat icin ikinci satiri BIRINCIL ANAHTAR reddeder
--    (eszamanli isteklerde de gecerli; uygulamada kontrol gerekmez)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_kayit_slot_senkron() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    DELETE FROM ogrenci_slot WHERE kayit_id = OLD.kayit_id;
  END IF;
  IF NEW.durum IN ('sepet','onay_bekliyor','onayli') THEN
    BEGIN
      INSERT INTO ogrenci_slot (ogrenci_id, donem_id, gun, ders_saati, kayit_id)
      SELECT NEW.ogrenci_id, NEW.donem_id, ss.gun, ss.ders_saati, NEW.kayit_id
      FROM sube_saat ss WHERE ss.sube_id = NEW.sube_id;
    EXCEPTION WHEN unique_violation THEN
      RAISE EXCEPTION 'CAKISMA: secilen subenin ders saati mevcut bir kayitla cakisiyor';
    END;
  END IF;
  RETURN NULL;
END $$;
CREATE TRIGGER trg_kayit_slot AFTER INSERT OR UPDATE OF durum ON kayit
  FOR EACH ROW EXECUTE FUNCTION fn_kayit_slot_senkron();

-- ---------------------------------------------------------------------
-- 6) DANISMAN KARARI (R-13, R-14): onay / red / duzeltme_iste
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_danisman_karar(p_kayit int, p_danisman int, p_karar text, p_gerekce text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_ogr int;
BEGIN
  SELECT ogrenci_id INTO v_ogr FROM kayit WHERE kayit_id = p_kayit FOR UPDATE;
  IF v_ogr IS NULL THEN
    RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM danismanlik
                  WHERE ogrenci_id = v_ogr AND danisman_id = p_danisman AND gecerlilik @> current_date) THEN
    RAISE EXCEPTION 'YETKISIZ: danisman bu ogrencinin guncel danismani degil';
  END IF;
  INSERT INTO kayit_onay (kayit_id, danisman_id, karar, gerekce)
  VALUES (p_kayit, p_danisman, p_karar, p_gerekce);
  UPDATE kayit SET durum = CASE p_karar WHEN 'onay' THEN 'onayli'
                                        WHEN 'red'  THEN 'reddedildi'
                                        ELSE 'sepet' END
   WHERE kayit_id = p_kayit;
END $$;

-- ---------------------------------------------------------------------
-- 7) DEGERLENDIRME AGIRLIKLARI (R-21): ertelenebilir kisit -- toplam islem sonunda 100 olmali
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_bilesen_agirlik_kontrol() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_sube int; v_toplam numeric;
BEGIN
  v_sube := coalesce(NEW.sube_id, OLD.sube_id);
  SELECT sum(agirlik) INTO v_toplam FROM degerlendirme_bileseni WHERE sube_id = v_sube;
  IF v_toplam IS NOT NULL AND v_toplam <> 100 THEN
    RAISE EXCEPTION 'AGIRLIK_TOPLAMI: sube % icin toplam % (100 olmali)', v_sube, v_toplam;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER ctrg_bilesen_agirlik
  AFTER INSERT OR UPDATE OR DELETE ON degerlendirme_bileseni
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_bilesen_agirlik_kontrol();

-- ---------------------------------------------------------------------
-- 8) SONUC HESABI (R-22): harf notu puandan hesaplanir, elle girilmez
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_sonuc_hesapla(p_kayit int) RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_ort numeric; v_harf varchar(2); v_gecer boolean; v_girilen int; v_toplam int;
BEGIN
  SELECT count(*) INTO v_girilen FROM not_kaydi n WHERE n.kayit_id = p_kayit AND n.ilan_edildi;
  SELECT count(*) INTO v_toplam
    FROM degerlendirme_bileseni b JOIN kayit k ON k.sube_id = b.sube_id WHERE k.kayit_id = p_kayit;
  IF v_toplam = 0 OR v_girilen <> v_toplam THEN
    RAISE EXCEPTION 'NOT_EKSIK: tum bilesenler ilan edilmeden sonuc hesaplanamaz (% / %)', v_girilen, v_toplam;
  END IF;
  SELECT round(sum(n.puan * b.agirlik) / 100.0, 2) INTO v_ort
    FROM not_kaydi n JOIN degerlendirme_bileseni b ON b.bilesen_id = n.bilesen_id
   WHERE n.kayit_id = p_kayit AND n.ilan_edildi;
  SELECT harf, gecer_mi INTO v_harf, v_gecer
    FROM harf_notu_aralik WHERE min_puan <= v_ort ORDER BY min_puan DESC LIMIT 1;
  INSERT INTO kayit_sonuc (kayit_id, ortalama_puan, harf, durum)
  VALUES (p_kayit, v_ort, v_harf, CASE WHEN v_gecer THEN 'gecti' ELSE 'kaldi' END)
  ON CONFLICT (kayit_id) DO UPDATE
    SET ortalama_puan = EXCLUDED.ortalama_puan, harf = EXCLUDED.harf,
        durum = EXCLUDED.durum, hesap_zamani = now();
END $$;

-- ---------------------------------------------------------------------
-- 9) DENETIM LOGU (R-30): tetikleyici ile yazilir, hash zinciri ile degisikligi ele verir,
--    UPDATE/DELETE/TRUNCATE yasaktir. Zincir sirali yazim ister (advisory lock) -- bilincli odunlesim.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_log_hash(p_onceki text, p_tablo text, p_pk text, p_islem text,
                                       p_eski jsonb, p_yeni jsonb, p_zaman timestamptz)
RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT encode(sha256(convert_to(
           coalesce(p_onceki, '') || '|' || p_tablo || '|' || p_pk || '|' || p_islem || '|' ||
           coalesce(p_eski::text, '') || '|' || coalesce(p_yeni::text, '') || '|' ||
           to_char(p_zaman AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'), 'UTF8')), 'hex');
$$;

CREATE OR REPLACE FUNCTION fn_denetim() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_eski jsonb; v_yeni jsonb; v_pk text := ''; v_prev text; v_col text;
  v_zaman timestamptz := clock_timestamp();
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('denetim_log'));          -- zincirin catallanmasini onler
  IF TG_OP IN ('UPDATE','DELETE') THEN v_eski := to_jsonb(OLD); END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN v_yeni := to_jsonb(NEW); END IF;
  FOREACH v_col IN ARRAY TG_ARGV LOOP
    v_pk := v_pk || coalesce(coalesce(v_yeni, v_eski) ->> v_col, '') || ',';
  END LOOP;
  SELECT hash INTO v_prev FROM denetim_log ORDER BY log_id DESC LIMIT 1;
  INSERT INTO denetim_log (tablo, kayit_pk, islem, eski, yeni, kullanici, zaman, onceki_hash, hash)
  VALUES (TG_TABLE_NAME, v_pk, left(TG_OP, 1), v_eski, v_yeni, current_user, v_zaman, v_prev,
          fn_log_hash(v_prev, TG_TABLE_NAME, v_pk, left(TG_OP, 1), v_eski, v_yeni, v_zaman));
  RETURN NULL;
END $$;

-- Zincir saglam ise NULL, bozuksa ilk bozuk log_id doner
CREATE OR REPLACE FUNCTION fn_denetim_dogrula() RETURNS bigint LANGUAGE plpgsql STABLE AS $$
DECLARE r record; v_prev text := NULL;
BEGIN
  FOR r IN SELECT * FROM denetim_log ORDER BY log_id LOOP
    IF r.onceki_hash IS DISTINCT FROM v_prev THEN RETURN r.log_id; END IF;
    IF r.hash <> fn_log_hash(r.onceki_hash, r.tablo, r.kayit_pk, r.islem, r.eski, r.yeni, r.zaman) THEN
      RETURN r.log_id;
    END IF;
    v_prev := r.hash;
  END LOOP;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION fn_denetim_degistirilemez() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'DENETIM_LOGU_DEGISTIRILEMEZ: denetim_log yalnizca eklenir';
END $$;
CREATE TRIGGER trg_denetim_koru BEFORE UPDATE OR DELETE ON denetim_log
  FOR EACH ROW EXECUTE FUNCTION fn_denetim_degistirilemez();
CREATE TRIGGER trg_denetim_koru_truncate BEFORE TRUNCATE ON denetim_log
  FOR EACH STATEMENT EXECUTE FUNCTION fn_denetim_degistirilemez();

CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON kayit
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kayit_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON kayit_onay
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('onay_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON not_kaydi
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kayit_id', 'bilesen_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON kayit_sonuc
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kayit_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON danismanlik
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('danismanlik_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON harf_notu_aralik
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('harf');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON akts_limit_kural
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('kural_id');
CREATE TRIGGER trg_denetim AFTER INSERT OR UPDATE OR DELETE ON parametre
  FOR EACH ROW EXECUTE FUNCTION fn_denetim('anahtar');
