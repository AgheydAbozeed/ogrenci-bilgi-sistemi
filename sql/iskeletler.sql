-- =====================================================================
-- sql/iskeletler.sql -- Kalan asamalar icin TEST EDILMIS baslangic iskeletleri
-- On kosul: 001..004 yuklu.  Tekrar calistirilabilir (idempotent).
-- Bu dosya TAMAMLANMIS asama degildir; docs/UYGULAMA_PLANI.md hangi kisimlarin yazilacagini soyler.
--   Asama A (risk)  : fn_risk_bayrak_hesapla  -> TODO: 4 kural daha + v_risk_ozet
--   Asama B (API)   : fn_sepete_ekle ornegi   -> TODO: docs/VERITABANI_API_VE_EKRANLAR.md'deki fonksiyonlar
--   Asama D (demo)  : kilitlenme, geri alma, explain -> TODO: akts hazirlama, indeks demosu
--   Asama E (AI)    : v_risk_ozellik          -> model bu gorunumden beslenir
-- =====================================================================

-- ---------------------------------------------------------------------
-- Giris ekrani icin demo kullanici listesi (sahibin yetkisiyle calisir: giris rolu yalnizca bu gorunumu gorur)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_demo_kullanicilar AS
SELECT k.kisi_id, k.ad || ' ' || k.soyad AS ad_soyad, array_agg(DISTINCT r.rol) AS roller
FROM kisi k
JOIN (SELECT kisi_id, rol FROM kisi_rol
      UNION
      SELECT danisman_id, 'danisman' FROM danismanlik) r ON r.kisi_id = k.kisi_id
GROUP BY k.kisi_id, k.ad, k.soyad;

-- ---------------------------------------------------------------------
-- Asama E: risk modelinin SIS tarafindaki ozellikleri (kayit duzeyinde)
-- OULAD karsiliklari docs/UYGULAMA_PLANI.md, Asama E3'te
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_risk_ozellik AS
SELECT k.kayit_id, k.ogrenci_id, k.donem_id,
  (SELECT count(*) FROM kayit e JOIN donem de ON de.donem_id = e.donem_id
    WHERE e.ogrenci_id = k.ogrenci_id AND e.ders_id = k.ders_id
      AND de.donem_sonu < dn.kayit_baslangic AND e.durum IN ('onayli','birakti'))       AS onceki_deneme,
  (SELECT coalesce(sum(d2.akts), 0) FROM kayit e JOIN ders d2 ON d2.ders_id = e.ders_id
    WHERE e.ogrenci_id = k.ogrenci_id AND e.donem_id = k.donem_id
      AND e.durum IN ('onay_bekliyor','onayli'))                                         AS alinan_kredi,
  floor(extract(epoch FROM (k.olusturma - dn.kayit_baslangic)) / 86400)::int             AS kayit_gunu,
  (SELECT avg(n.puan) FROM not_kaydi n WHERE n.kayit_id = k.kayit_id AND n.ilan_edildi)   AS ort_puan,
  (SELECT avg((n.puan = 0)::int) FROM not_kaydi n WHERE n.kayit_id = k.kayit_id AND n.ilan_edildi) AS eksik_oran,
  (SELECT avg(y.katildi::int) FROM yoklama y WHERE y.kayit_id = k.kayit_id)               AS katilim_orani
FROM kayit k JOIN donem dn ON dn.donem_id = k.donem_id
WHERE k.durum IN ('onay_bekliyor','onayli');

-- ---------------------------------------------------------------------
-- Asama A: risk bayraklari (ilk iki kural hazir; digerleri plan dosyasinda)
-- ---------------------------------------------------------------------
INSERT INTO parametre (anahtar, deger, aciklama) VALUES
  ('risk_gno_esigi', '2.00', 'GNO bu degerin altindaysa GNO_ESIK_ALTI bayragi')
ON CONFLICT DO NOTHING;

INSERT INTO risk_kural (kod, aciklama, siddet) VALUES
  ('GNO_ESIK_ALTI', 'GNO risk esiginin altinda', 2),
  ('ZORUNLU_FF',    'Zorunlu derste basarisiz ve bu donem tekrar kaydi yok', 2)
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION fn_risk_bayrak_hesapla(p_donem int) RETURNS int LANGUAGE plpgsql AS $$
BEGIN
  DELETE FROM risk_bayrak WHERE donem_id = p_donem;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT o.kisi_id, p_donem, 'GNO_ESIK_ALTI'
    FROM ogrenci o
   WHERE o.durum = 'aktif'
     AND fn_gno(o.kisi_id) < (SELECT deger::numeric FROM parametre WHERE anahtar = 'risk_gno_esigi')
  ON CONFLICT DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT DISTINCT s.ogrenci_id, p_donem, 'ZORUNLU_FF'
    FROM v_gecerli_sonuc s
    JOIN ogrenci o ON o.kisi_id = s.ogrenci_id AND o.durum = 'aktif'
    JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id AND md.ders_id = s.ders_id AND md.tur = 'zorunlu'
   WHERE s.durum = 'kaldi'
     AND NOT EXISTS (SELECT 1 FROM kayit k
                      WHERE k.ogrenci_id = s.ogrenci_id AND k.ders_id = s.ders_id
                        AND k.donem_id = p_donem AND k.durum IN ('sepet','onay_bekliyor','onayli'))
  ON CONFLICT DO NOTHING;

  -- TODO (Asama A): AKTS_GERIDE, DEVAMSIZLIK, ONKOSUL_BLOKAJI, DERS_BIRAKMA

  RETURN (SELECT count(*) FROM risk_bayrak WHERE donem_id = p_donem)::int;
END $$;

-- ---------------------------------------------------------------------
-- Asama D: demolar
-- ---------------------------------------------------------------------
-- Kilitlenme: iki ayri baglanti (A,B) ve (B,A) sirasiyla cagirir -> biri "deadlock detected" alir
CREATE OR REPLACE FUNCTION fn_demo_kilitlenme(p_a int, p_b int, p_bekle numeric DEFAULT 1) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM 1 FROM kayit WHERE kayit_id = p_a FOR UPDATE;
  PERFORM pg_sleep(p_bekle);
  PERFORM 1 FROM kayit WHERE kayit_id = p_b FOR UPDATE;
  RETURN 'tamam';
END $$;

-- Cozum: kilitleri hep ayni sirada al
CREATE OR REPLACE FUNCTION fn_demo_kilitlenme_duzeltilmis(p_a int, p_b int, p_bekle numeric DEFAULT 1) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM 1 FROM kayit WHERE kayit_id IN (p_a, p_b) ORDER BY kayit_id FOR UPDATE;
  PERFORM pg_sleep(p_bekle);
  RETURN 'tamam';
END $$;

-- Silinen notu denetim logundan geri getirir (log tabanli geri alma)
CREATE OR REPLACE FUNCTION fn_not_geri_al(p_log_id bigint) RETURNS void LANGUAGE plpgsql AS $$
DECLARE l denetim_log%ROWTYPE;
BEGIN
  SELECT * INTO l FROM denetim_log WHERE log_id = p_log_id AND tablo = 'not_kaydi' AND islem = 'D';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'LOG_BULUNAMADI: % numarali kayit bir not silme islemi degil', p_log_id;
  END IF;
  INSERT INTO not_kaydi SELECT * FROM jsonb_populate_record(NULL::not_kaydi, l.eski);
END $$;

-- EXPLAIN ANALYZE demosu: yalnizca beyaz listedeki sorgular (SQL enjeksiyonuna kapali)
CREATE OR REPLACE FUNCTION fn_demo_explain(p_kod text) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE v_sql text; v_plan json;
BEGIN
  v_sql := CASE p_kod
    WHEN 'transkript'   THEN 'SELECT * FROM v_transkript WHERE ogrenci_no = ''2025001'''
    WHEN 'sube_listesi' THEN 'SELECT * FROM kayit WHERE sube_id = (SELECT min(sube_id) FROM sube)'
    WHEN 'durum_filtre' THEN 'SELECT count(*) FROM kayit WHERE durum = ''onayli'''
    ELSE NULL END;
  IF v_sql IS NULL THEN
    RAISE EXCEPTION 'SORGU_BILINMIYOR: %', p_kod;
  END IF;
  EXECUTE 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' || v_sql INTO v_plan;
  RETURN v_plan::jsonb;
END $$;

-- ---------------------------------------------------------------------
-- Asama B: ogrenci eylemi ORNEGI. Kimlik oturum degiskeninden gelir; kurallar tetikleyicilerde.
-- Uygulama oturumu: SELECT set_config('app.kullanici_id', '<id>', true)  (islem basina)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_sepete_ekle(p_sube int) RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_uid int := nullif(current_setting('app.kullanici_id', true), '')::int; v_id int;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'YETKISIZ: oturum kimligi yok';
  END IF;
  INSERT INTO kayit (ogrenci_id, sube_id) VALUES (v_uid, p_sube) RETURNING kayit_id INTO v_id;
  RETURN v_id;
END $$;
