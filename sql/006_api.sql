-- =====================================================================
-- 006_api.sql -- Asama B (Parca 1): Kural guncellemesi, Okuma Gorunumleri ve Yazma API'si
-- On kosul: 001..005 yuklu.   Calistirma: psql -d obs -f sql/006_api.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) OTURUM KIMLIGI YARDIMCILARI VE DENETIM LOGU GUNCELLEMESI
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_oturum_kisi_id() RETURNS int
LANGUAGE plpgsql STABLE AS $$
DECLARE v_id int;
BEGIN
  v_id := nullif(current_setting('app.kullanici_id', true), '')::int;
  IF v_id IS NULL THEN
    RAISE EXCEPTION 'YETKISIZ: oturum kimligi (app.kullanici_id) tanimli degil';
  END IF;
  RETURN v_id;
END $$;

CREATE OR REPLACE FUNCTION fn_aktif_donem_id() RETURNS int
LANGUAGE sql STABLE AS $$
  SELECT donem_id FROM donem
  ORDER BY yil DESC, CASE tur WHEN 'yaz' THEN 3 WHEN 'bahar' THEN 2 ELSE 1 END DESC
  LIMIT 1;
$$;

-- Denetim logu: SECURITY DEFINER icinde current_user tablo sahibi olacagindan
-- once app.kullanici_id oturum degiskenini okur; app.gerekce varsa yeni JSON'a _gerekce ekler.
CREATE OR REPLACE FUNCTION fn_denetim() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_eski jsonb; v_yeni jsonb; v_pk text := ''; v_prev text; v_col text;
  v_zaman timestamptz := clock_timestamp();
  v_kul text; v_gerekce text;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('denetim_log'));
  IF TG_OP IN ('UPDATE','DELETE') THEN v_eski := to_jsonb(OLD); END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN v_yeni := to_jsonb(NEW); END IF;
  v_gerekce := nullif(current_setting('app.gerekce', true), '');
  IF v_gerekce IS NOT NULL AND v_yeni IS NOT NULL THEN
    v_yeni := v_yeni || jsonb_build_object('_gerekce', v_gerekce);
  END IF;
  FOREACH v_col IN ARRAY TG_ARGV LOOP
    v_pk := v_pk || coalesce(coalesce(v_yeni, v_eski) ->> v_col, '') || ',';
  END LOOP;
  v_kul := coalesce(nullif(current_setting('app.kullanici_id', true), ''), current_user);
  SELECT hash INTO v_prev FROM denetim_log ORDER BY log_id DESC LIMIT 1;
  INSERT INTO denetim_log (tablo, kayit_pk, islem, eski, yeni, kullanici, zaman, onceki_hash, hash)
  VALUES (TG_TABLE_NAME, v_pk, left(TG_OP, 1), v_eski, v_yeni, v_kul, v_zaman, v_prev,
          fn_log_hash(v_prev, TG_TABLE_NAME, v_pk, left(TG_OP, 1), v_eski, v_yeni, v_zaman));
  RETURN NULL;
END $$;

-- ---------------------------------------------------------------------
-- 2) KURAL EKSIKLIGI DUZELTMESI: MUFREDAT_DISI (Asama B Madde 7)
-- ---------------------------------------------------------------------
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
    IF NOT EXISTS (
      SELECT 1 FROM ogrenci o
      JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id
      WHERE o.kisi_id = NEW.ogrenci_id AND md.ders_id = NEW.ders_id
    ) THEN
      RAISE EXCEPTION 'MUFREDAT_DISI: ders ogrencinin mufredatinda degil';
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

    IF OLD.durum = 'sepet' AND NEW.durum = 'onay_bekliyor' THEN
      IF now() NOT BETWEEN v_donem.kayit_baslangic AND v_donem.ekle_birak_bitis THEN
        RAISE EXCEPTION 'DONEM_KAPALI: kayit penceresi disinda';
      END IF;
      IF coalesce((SELECT deger FROM parametre WHERE anahtar = 'akts_kilidi'), 'acik') = 'acik' THEN
        PERFORM 1 FROM ogrenci WHERE kisi_id = NEW.ogrenci_id FOR UPDATE;
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

    IF OLD.durum = 'onayli' AND NEW.durum = 'birakti' AND now() > v_donem.ekle_birak_bitis THEN
      RAISE EXCEPTION 'DONEM_KAPALI: ekle-birak penceresi bitti';
    END IF;
  END IF;
  RETURN NEW;
END $$;

-- ---------------------------------------------------------------------
-- 3) OKUMA GORUNUMLERI (§1.2)
-- ---------------------------------------------------------------------
-- Giris ekrani icin (sahip yetkisiyle calisir, obs_login rolu okur)
CREATE OR REPLACE VIEW v_demo_kullanicilar AS
SELECT k.kisi_id,
       k.ad || ' ' || k.soyad AS ad_soyad,
       array_remove(array_agg(DISTINCT r.rol ORDER BY r.rol), NULL) AS roller
  FROM kisi k
  LEFT JOIN (
    SELECT kisi_id, 'rol_' || rol AS rol FROM kisi_rol
    UNION
    SELECT danisman_id AS kisi_id, 'rol_danisman' AS rol
      FROM danismanlik WHERE gecerlilik @> current_date
  ) r ON r.kisi_id = k.kisi_id
 GROUP BY k.kisi_id, k.ad, k.soyad
 ORDER BY k.kisi_id;

-- Transkript gorunumunu security_invoker ile yeniden olustur
CREATE OR REPLACE VIEW v_transkript WITH (security_invoker = true) AS
SELECT o.ogrenci_no, kk.ad || ' ' || kk.soyad AS ad_soyad, d.yil, d.tur AS donem,
       ds.kod, ds.ad AS ders_adi, ds.akts, s.harf, h.katsayi, s.durum
FROM kayit k
JOIN ogrenci o     ON o.kisi_id = k.ogrenci_id
JOIN kisi kk       ON kk.kisi_id = o.kisi_id
JOIN donem d       ON d.donem_id = k.donem_id
JOIN ders ds       ON ds.ders_id = k.ders_id
JOIN kayit_sonuc s ON s.kayit_id = k.kayit_id
LEFT JOIN harf_notu_aralik h ON h.harf = s.harf;

-- Ana sayfa (ogrenci)
CREATE OR REPLACE VIEW v_ana_sayfa WITH (security_invoker = true) AS
SELECT o.kisi_id AS ogrenci_id,
       (dn.yil - o.giris_yili + 1)::int AS sinif,
       coalesce(g.gecilen_akts, 0)::int AS gecilen_akts,
       (SELECT round(sum(ds.akts * h.katsayi)::numeric / NULLIF(sum(ds.akts), 0), 2)
          FROM kayit k
          JOIN kayit_sonuc ks ON ks.kayit_id = k.kayit_id AND ks.durum IN ('gecti','kaldi')
          JOIN harf_notu_aralik h ON h.harf = ks.harf
          JOIN ders ds ON ds.ders_id = k.ders_id
         WHERE k.ogrenci_id = o.kisi_id
           AND k.donem_id = (
             SELECT k2.donem_id FROM kayit k2
             JOIN kayit_sonuc ks2 ON ks2.kayit_id = k2.kayit_id
             JOIN donem d2 ON d2.donem_id = k2.donem_id
             WHERE k2.ogrenci_id = o.kisi_id
             ORDER BY d2.yil DESC, CASE d2.tur WHEN 'yaz' THEN 3 WHEN 'bahar' THEN 2 ELSE 1 END DESC
             LIMIT 1
           )) AS dno,
       g.gno,
       dn.yil || ' ' || initcap(dn.tur) AS aktif_donem,
       (now() BETWEEN dn.kayit_baslangic AND dn.ekle_birak_bitis) AS kayit_acik,
       dn.kayit_bitis,
       dn.ekle_birak_bitis
  FROM ogrenci o
  LEFT JOIN v_gno g ON g.ogrenci_id = o.kisi_id
  LEFT JOIN donem dn ON dn.donem_id = fn_aktif_donem_id();

-- Kayitlarim (ogrenci)
DROP VIEW IF EXISTS v_kayitlarim;
CREATE VIEW v_kayitlarim WITH (security_invoker = true) AS
SELECT k.kayit_id, k.ogrenci_id, d.kod AS ders_kod, d.ad AS ders_ad,
       d.akts, s.sube_no, k.donem_id, k.durum,
       (SELECT ko.gerekce FROM kayit_onay ko
         WHERE ko.kayit_id = k.kayit_id ORDER BY ko.zaman DESC, ko.onay_id DESC LIMIT 1) AS onay_gerekce
  FROM kayit k
  JOIN sube s ON s.sube_id = k.sube_id
  JOIN ders d ON d.ders_id = k.ders_id;

-- Acik subeler (ogrenci icin durum ve neden hesaplar)
CREATE OR REPLACE VIEW v_acik_subeler WITH (security_invoker = true) AS
SELECT s.sube_id, s.donem_id, d.kod AS ders_kod, d.ad AS ders_ad,
       d.akts, s.sube_no,
       ou.unvan || ' ' || k.ad || ' ' || k.soyad AS hoca,
       coalesce((
         SELECT string_agg(
           (ARRAY['Pzt','Sal','Car','Per','Cum','Cmt','Paz'])[ss.gun] || ' ' || ss.ders_saati,
           ', ' ORDER BY ss.gun, ss.ders_saati
         ) FROM sube_saat ss WHERE ss.sube_id = s.sube_id
       ), '-') AS saatler,
       CASE
         WHEN EXISTS (
           SELECT 1 FROM v_gecerli_sonuc gs
            WHERE gs.ogrenci_id = o.kisi_id AND gs.ders_id = d.ders_id AND gs.durum = 'gecti'
         ) THEN 'gecildi'
         WHEN EXISTS (
           SELECT 1 FROM kayit ky
            WHERE ky.ogrenci_id = o.kisi_id AND ky.donem_id = s.donem_id
              AND ky.ders_id = d.ders_id AND ky.durum IN ('onay_bekliyor','onayli')
         ) THEN 'kayitli'
         WHEN EXISTS (
           SELECT 1 FROM kayit ky
            WHERE ky.ogrenci_id = o.kisi_id AND ky.donem_id = s.donem_id
              AND ky.ders_id = d.ders_id AND ky.durum = 'sepet'
         ) THEN 'sepette'
         WHEN EXISTS (SELECT 1 FROM fn_onkosul_eksikleri(o.kisi_id, d.ders_id)) THEN 'onkosul_eksik'
         WHEN EXISTS (
           SELECT 1 FROM sube_saat ss
           JOIN ogrenci_slot os ON os.donem_id = s.donem_id
                               AND os.gun = ss.gun AND os.ders_saati = ss.ders_saati
            WHERE ss.sube_id = s.sube_id AND os.ogrenci_id = o.kisi_id
         ) THEN 'cakisiyor'
         ELSE 'alinabilir'
       END AS durum,
       CASE
         WHEN EXISTS (SELECT 1 FROM fn_onkosul_eksikleri(o.kisi_id, d.ders_id))
         THEN (SELECT string_agg(kod, ', ') FROM fn_onkosul_eksikleri(o.kisi_id, d.ders_id))
         ELSE NULL
       END AS neden
  FROM sube s
  JOIN ders d ON d.ders_id = s.ders_id
  JOIN ogretim_uyesi ou ON ou.kisi_id = s.ogretim_uyesi_id
  JOIN kisi k ON k.kisi_id = ou.kisi_id
  JOIN ogrenci o ON o.kisi_id = nullif(current_setting('app.kullanici_id', true), '')::int
  JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id AND md.ders_id = d.ders_id;

-- Haftalik program (ogrenci)
CREATE OR REPLACE VIEW v_haftalik_program WITH (security_invoker = true) AS
SELECT k.donem_id, ss.gun, ss.ders_saati, d.kod AS ders_kod, s.sube_no, k.durum
  FROM kayit k
  JOIN sube s ON s.sube_id = k.sube_id
  JOIN ders d ON d.ders_id = k.ders_id
  JOIN sube_saat ss ON ss.sube_id = s.sube_id
 WHERE k.durum IN ('sepet','onay_bekliyor','onayli');

-- Not detay (ogrenci / ogretim uyesi)
CREATE OR REPLACE VIEW v_not_detay WITH (security_invoker = true) AS
SELECT k.kayit_id, d.kod AS ders_kod, db.ad AS bilesen, db.agirlik, nk.puan, nk.ilan_edildi
  FROM not_kaydi nk
  JOIN kayit k ON k.kayit_id = nk.kayit_id
  JOIN ders d  ON d.ders_id = k.ders_id
  JOIN degerlendirme_bileseni db ON db.bilesen_id = nk.bilesen_id;

-- Danisman gorunumleri
CREATE OR REPLACE VIEW v_onay_kuyrugu WITH (security_invoker = true) AS
SELECT k.kayit_id, k.ogrenci_id, o.ogrenci_no, kk.ad || ' ' || kk.soyad AS ad_soyad,
       d.kod AS ders_kod, d.ad AS ders_ad, d.akts, k.olusturma, fn_gno(k.ogrenci_id) AS gno
  FROM kayit k
  JOIN ogrenci o ON o.kisi_id = k.ogrenci_id
  JOIN kisi kk   ON kk.kisi_id = o.kisi_id
  JOIN ders d    ON d.ders_id = k.ders_id
 WHERE k.durum = 'onay_bekliyor';

CREATE OR REPLACE VIEW v_danisanlarim WITH (security_invoker = true) AS
SELECT o.kisi_id AS ogrenci_id, o.ogrenci_no, kk.ad || ' ' || kk.soyad AS ad_soyad,
       g.gno, coalesce(g.gecilen_akts, 0)::int AS gecilen_akts,
       coalesce(ro.bayrak_sayisi, 0)::int AS bayrak_sayisi,
       coalesce(ro.en_yuksek_siddet, 0)::int AS en_yuksek_siddet,
       rt.skor AS risk_skoru
  FROM ogrenci o
  JOIN kisi kk ON kk.kisi_id = o.kisi_id
  JOIN danismanlik dn ON dn.ogrenci_id = o.kisi_id AND dn.gecerlilik @> current_date
  LEFT JOIN v_gno g ON g.ogrenci_id = o.kisi_id
  LEFT JOIN v_risk_ozet ro ON ro.ogrenci_id = o.kisi_id AND ro.donem_id = fn_aktif_donem_id()
  LEFT JOIN LATERAL (
    SELECT skor FROM risk_tahmin r
     WHERE r.ogrenci_id = o.kisi_id AND r.donem_id = fn_aktif_donem_id()
     ORDER BY r.hesap_zamani DESC LIMIT 1
  ) rt ON true;

CREATE OR REPLACE VIEW v_danisan_bayraklari WITH (security_invoker = true) AS
SELECT rb.ogrenci_id, rb.kural_kod, rk.aciklama, rk.siddet
  FROM risk_bayrak rb
  JOIN risk_kural rk ON rk.kod = rb.kural_kod
 WHERE rb.donem_id = fn_aktif_donem_id();

CREATE OR REPLACE VIEW v_danisan_risk WITH (security_invoker = true) AS
SELECT rt.ogrenci_id, rt.skor, rt.ozellikler, ms.ad AS model, rt.hesap_zamani
  FROM risk_tahmin rt
  JOIN model_surum ms ON ms.model_id = rt.model_id
 WHERE rt.donem_id = fn_aktif_donem_id();

-- Ogretim uyesi gorunumleri
CREATE OR REPLACE VIEW v_sube_listem WITH (security_invoker = true) AS
SELECT s.sube_id, s.donem_id, d.kod AS ders_kod, d.ad AS ders_ad, s.sube_no,
       (SELECT count(*)::int FROM kayit k
         WHERE k.sube_id = s.sube_id AND k.durum IN ('onay_bekliyor','onayli')) AS ogrenci_sayisi
  FROM sube s
  JOIN ders d ON d.ders_id = s.ders_id
 WHERE s.ogretim_uyesi_id = nullif(current_setting('app.kullanici_id', true), '')::int;

CREATE OR REPLACE VIEW v_sube_ogrencileri WITH (security_invoker = true) AS
SELECT k.sube_id, k.kayit_id, o.ogrenci_no, kk.ad || ' ' || kk.soyad AS ad_soyad, k.durum
  FROM kayit k
  JOIN ogrenci o ON o.kisi_id = k.ogrenci_id
  JOIN kisi kk   ON kk.kisi_id = o.kisi_id
 WHERE k.durum IN ('onay_bekliyor','onayli');

CREATE OR REPLACE VIEW v_bilesenler WITH (security_invoker = true) AS
SELECT b.sube_id, b.bilesen_id, b.ad, b.agirlik
  FROM degerlendirme_bileseni b;

-- Diger okuma gorunumleri
CREATE OR REPLACE VIEW v_mufredat_listesi WITH (security_invoker = true) AS
SELECT m.mufredat_id, p.ad AS program, m.giris_yili
  FROM mufredat m
  JOIN program p ON p.program_id = m.program_id;

CREATE OR REPLACE VIEW v_parametreler WITH (security_invoker = true) AS
SELECT anahtar, deger, aciklama FROM parametre;

CREATE OR REPLACE VIEW v_denetim_log WITH (security_invoker = true) AS
SELECT log_id, zaman, kullanici, tablo, islem, kayit_pk, eski, yeni
  FROM denetim_log;

CREATE OR REPLACE VIEW v_silinen_notlar WITH (security_invoker = true) AS
SELECT log_id, zaman, kullanici, kayit_pk, eski
  FROM denetim_log
 WHERE tablo = 'not_kaydi' AND islem = 'D';

-- ---------------------------------------------------------------------
-- 4) MEZUNIYET _BEN VE _DANISAN SARMALAYICILARI (§1.2)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_mezuniyet_ozet_ben()
RETURNS TABLE (gecilen_akts int, gereken_akts int, gno numeric, min_gno numeric,
               gruplar_tamam boolean, mezuniyet_uygun boolean, eksikler text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
BEGIN
  RETURN QUERY SELECT * FROM fn_mezuniyet_ozet(fn_oturum_kisi_id());
END $$;

CREATE OR REPLACE FUNCTION fn_mezuniyet_denetim_ben(p_mufredat int DEFAULT NULL)
RETURNS TABLE (grup_id int, grup_ad text, tur text, min_ders int, min_akts int,
               sayilan_ders int, sayilan_akts int, durum text, eksik text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
BEGIN
  RETURN QUERY SELECT * FROM fn_mezuniyet_denetim(fn_oturum_kisi_id(), p_mufredat);
END $$;

CREATE OR REPLACE FUNCTION fn_ders_plani_ben(p_limit int DEFAULT NULL)
RETURNS TABLE (donem_sira int, ders_kod text, ders_ad text, akts int)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
BEGIN
  RETURN QUERY SELECT * FROM fn_ders_plani(fn_oturum_kisi_id(), p_limit);
END $$;

CREATE OR REPLACE FUNCTION fn_en_erken_mezuniyet_ben(p_limit int DEFAULT NULL)
RETURNS TABLE (kritik_yol_donem int, akts_limitli_donem int)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
BEGIN
  RETURN QUERY SELECT * FROM fn_en_erken_mezuniyet(fn_oturum_kisi_id(), p_limit);
END $$;

-- Danisman icin kendi danisanini sorgulama sarmalayicilari
CREATE OR REPLACE FUNCTION fn_mezuniyet_ozet_danisan(p_ogrenci int)
RETURNS TABLE (gecilen_akts int, gereken_akts int, gno numeric, min_gno numeric,
               gruplar_tamam boolean, mezuniyet_uygun boolean, eksikler text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE v_danisman int := fn_oturum_kisi_id();
BEGIN
  IF NOT EXISTS (SELECT 1 FROM danismanlik WHERE ogrenci_id = p_ogrenci AND danisman_id = v_danisman AND gecerlilik @> current_date) THEN
    RAISE EXCEPTION 'YETKISIZ: bu ogrencinin guncel danismani degilsiniz';
  END IF;
  RETURN QUERY SELECT * FROM fn_mezuniyet_ozet(p_ogrenci);
END $$;

CREATE OR REPLACE FUNCTION fn_mezuniyet_denetim_danisan(p_ogrenci int, p_mufredat int DEFAULT NULL)
RETURNS TABLE (grup_id int, grup_ad text, tur text, min_ders int, min_akts int,
               sayilan_ders int, sayilan_akts int, durum text, eksik text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE v_danisman int := fn_oturum_kisi_id();
BEGIN
  IF NOT EXISTS (SELECT 1 FROM danismanlik WHERE ogrenci_id = p_ogrenci AND danisman_id = v_danisman AND gecerlilik @> current_date) THEN
    RAISE EXCEPTION 'YETKISIZ: bu ogrencinin guncel danismani degilsiniz';
  END IF;
  RETURN QUERY SELECT * FROM fn_mezuniyet_denetim(p_ogrenci, p_mufredat);
END $$;

-- ---------------------------------------------------------------------
-- 5) YAZMA FONKSIYONLARI (§1.3 - SECURITY DEFINER)
-- ---------------------------------------------------------------------
-- Ogrenci: Sepete ekle
CREATE OR REPLACE FUNCTION fn_sepete_ekle(p_sube int) RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); v_id int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM ogrenci WHERE kisi_id = v_ogr) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca ogrenci sepete ders ekleyebilir';
  END IF;
  INSERT INTO kayit (ogrenci_id, sube_id) VALUES (v_ogr, p_sube) RETURNING kayit_id INTO v_id;
  RETURN v_id;
END $$;

-- Ogrenci: Sepetten cikar
CREATE OR REPLACE FUNCTION fn_sepetten_cikar(p_kayit int) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); v_sahip int; v_durum text;
BEGIN
  SELECT ogrenci_id, durum INTO v_sahip, v_durum FROM kayit WHERE kayit_id = p_kayit;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_ogr THEN RAISE EXCEPTION 'YETKISIZ: kayit size ait degil'; END IF;
  IF v_durum <> 'sepet' THEN RAISE EXCEPTION 'GECERSIZ_GECIS: yalnizca sepetteki kayit cikarilabilir'; END IF;
  UPDATE kayit SET durum = 'birakti' WHERE kayit_id = p_kayit;
END $$;

-- Ogrenci: Tek kaydi kesinlestir
CREATE OR REPLACE FUNCTION fn_kesinlestir(p_kayit int) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); v_sahip int;
BEGIN
  SELECT ogrenci_id INTO v_sahip FROM kayit WHERE kayit_id = p_kayit;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_ogr THEN RAISE EXCEPTION 'YETKISIZ: kayit size ait degil'; END IF;
  UPDATE kayit SET durum = 'onay_bekliyor' WHERE kayit_id = p_kayit;
END $$;

-- Ogrenci: Sepetteki tum kayitlari ayri alt islemlerde kesinlestir
CREATE OR REPLACE FUNCTION fn_kesinlestir_hepsi()
RETURNS TABLE (kayit_id int, sonuc text, mesaj text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); r record;
BEGIN
  FOR r IN
    SELECT k.kayit_id FROM kayit k
     WHERE k.ogrenci_id = v_ogr AND k.donem_id = fn_aktif_donem_id() AND k.durum = 'sepet'
     ORDER BY k.kayit_id
  LOOP
    BEGIN
      UPDATE kayit k SET durum = 'onay_bekliyor' WHERE k.kayit_id = r.kayit_id;
      RETURN QUERY SELECT r.kayit_id, 'tamam'::text, 'Kesinlestirildi'::text;
    EXCEPTION WHEN OTHERS THEN
      RETURN QUERY SELECT r.kayit_id, 'hata'::text, SQLERRM::text;
    END;
  END LOOP;
END $$;

-- Ogrenci: Kaydi birak (onay_bekliyor veya onayli -> birakti)
CREATE OR REPLACE FUNCTION fn_birak(p_kayit int) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); v_sahip int; v_durum text;
BEGIN
  SELECT ogrenci_id, durum INTO v_sahip, v_durum FROM kayit WHERE kayit_id = p_kayit;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_ogr THEN RAISE EXCEPTION 'YETKISIZ: kayit size ait degil'; END IF;
  IF v_durum NOT IN ('onay_bekliyor', 'onayli') THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: % -> birakti', v_durum;
  END IF;
  UPDATE kayit SET durum = 'birakti' WHERE kayit_id = p_kayit;
END $$;

-- Danisman: Karar ver
CREATE OR REPLACE FUNCTION fn_danisman_karar_ben(p_kayit int, p_karar text, p_gerekce text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  PERFORM fn_danisman_karar(p_kayit, fn_oturum_kisi_id(), p_karar, p_gerekce);
END $$;

-- Ogretim uyesi: Bilesenleri tek cagrida belirle
CREATE OR REPLACE FUNCTION fn_bilesenleri_belirle(p_sube int, p_adlar text[], p_agirliklar numeric[])
RETURNS int LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sahip int; v_len int; i int;
BEGIN
  SELECT ogretim_uyesi_id INTO v_sahip FROM sube WHERE sube_id = p_sube;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'SUBE_BULUNAMADI: %', p_sube; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  IF EXISTS (SELECT 1 FROM not_kaydi WHERE sube_id = p_sube) THEN
    RAISE EXCEPTION 'GECERSIZ_GECIS: not girilmis subede bilesenler degistirilemez';
  END IF;
  v_len := coalesce(array_length(p_adlar, 1), 0);
  IF v_len = 0 OR v_len IS DISTINCT FROM array_length(p_agirliklar, 1) THEN
    RAISE EXCEPTION 'AGIRLIK_TOPLAMI: bilesen dizileri bos veya esit uzunlukta degil';
  END IF;
  DELETE FROM degerlendirme_bileseni WHERE sube_id = p_sube;
  FOR i IN 1..v_len LOOP
    INSERT INTO degerlendirme_bileseni (sube_id, ad, agirlik)
    VALUES (p_sube, p_adlar[i], p_agirliklar[i]);
  END LOOP;
  SET CONSTRAINTS ctrg_bilesen_agirlik IMMEDIATE;
  RETURN v_len;
END $$;

-- Ogretim uyesi: Not gir (upsert; ilan edilmisse reddeder)
CREATE OR REPLACE FUNCTION fn_not_gir(p_kayit int, p_bilesen int, p_puan numeric)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sube int; v_sahip int; v_ilan boolean;
BEGIN
  SELECT k.sube_id, s.ogretim_uyesi_id INTO v_sube, v_sahip
    FROM kayit k JOIN sube s ON s.sube_id = k.sube_id WHERE k.kayit_id = p_kayit;
  IF v_sube IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  SELECT ilan_edildi INTO v_ilan FROM not_kaydi WHERE kayit_id = p_kayit AND bilesen_id = p_bilesen;
  IF coalesce(v_ilan, false) THEN
    RAISE EXCEPTION 'NOT_ILAN_EDILDI: ilan edilmis notu degistirmek icin fn_not_duzelt kullanin';
  END IF;
  INSERT INTO not_kaydi (kayit_id, bilesen_id, sube_id, puan, ilan_edildi)
  VALUES (p_kayit, p_bilesen, v_sube, p_puan, false)
  ON CONFLICT (kayit_id, bilesen_id) DO UPDATE SET puan = EXCLUDED.puan;
END $$;

-- Ogretim uyesi: Subenin notlarini ilan et
CREATE OR REPLACE FUNCTION fn_not_ilan_et(p_sube int) RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sahip int; v_adet int;
BEGIN
  SELECT ogretim_uyesi_id INTO v_sahip FROM sube WHERE sube_id = p_sube;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'SUBE_BULUNAMADI: %', p_sube; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  UPDATE not_kaydi SET ilan_edildi = true WHERE sube_id = p_sube AND NOT ilan_edildi;
  GET DIAGNOSTICS v_adet = ROW_COUNT;
  RETURN v_adet;
END $$;

-- Ogretim uyesi: Subedeki onayli kayitlarin sonuclarini hesapla
CREATE OR REPLACE FUNCTION fn_sonuclari_hesapla(p_sube int)
RETURNS TABLE (hesaplanan int, eksik int)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sahip int; r record;
        v_hesap int := 0; v_eksik int := 0;
BEGIN
  SELECT ogretim_uyesi_id INTO v_sahip FROM sube WHERE sube_id = p_sube;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'SUBE_BULUNAMADI: %', p_sube; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  FOR r IN SELECT kayit_id FROM kayit WHERE sube_id = p_sube AND durum = 'onayli' LOOP
    BEGIN
      PERFORM fn_sonuc_hesapla(r.kayit_id);
      v_hesap := v_hesap + 1;
    EXCEPTION WHEN OTHERS THEN
      v_eksik := v_eksik + 1;
    END;
  END LOOP;
  RETURN QUERY SELECT v_hesap, v_eksik;
END $$;

-- Ogretim uyesi: Ilan sonrasi gerekceli not duzeltme
CREATE OR REPLACE FUNCTION fn_not_duzelt(p_kayit int, p_bilesen int, p_puan numeric, p_gerekce text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sube int; v_sahip int;
BEGIN
  IF length(trim(coalesce(p_gerekce, ''))) = 0 THEN
    RAISE EXCEPTION 'GEREKCE_ZORUNLU: not duzeltmesi icin gerekce zorunludur';
  END IF;
  SELECT k.sube_id, s.ogretim_uyesi_id INTO v_sube, v_sahip
    FROM kayit k JOIN sube s ON s.sube_id = k.sube_id WHERE k.kayit_id = p_kayit;
  IF v_sube IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  PERFORM set_config('app.gerekce', p_gerekce, true);
  UPDATE not_kaydi SET puan = p_puan WHERE kayit_id = p_kayit AND bilesen_id = p_bilesen;
  IF NOT FOUND THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: not kaydi yok'; END IF;
  IF EXISTS (SELECT 1 FROM kayit_sonuc WHERE kayit_id = p_kayit) THEN
    PERFORM fn_sonuc_hesapla(p_kayit);
  END IF;
END $$;

-- Ogretim uyesi: Yoklama gir
CREATE OR REPLACE FUNCTION fn_yoklama_gir(p_kayit int, p_tarih date, p_katildi boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_hoca int := fn_oturum_kisi_id(); v_sahip int;
BEGIN
  SELECT s.ogretim_uyesi_id INTO v_sahip
    FROM kayit k JOIN sube s ON s.sube_id = k.sube_id WHERE k.kayit_id = p_kayit;
  IF v_sahip IS NULL THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_kayit; END IF;
  IF v_sahip <> v_hoca THEN RAISE EXCEPTION 'YETKISIZ: bu subenin ogretim uyesi degilsiniz'; END IF;
  INSERT INTO yoklama (kayit_id, tarih, katildi) VALUES (p_kayit, p_tarih, p_katildi)
  ON CONFLICT (kayit_id, tarih) DO UPDATE SET katildi = EXCLUDED.katildi;
END $$;

-- Sekreter: Donem ac, sube ac, sube saati ekle, danisman ata
CREATE OR REPLACE FUNCTION fn_donem_ac(p_yil smallint, p_tur text, p_kayit_bas timestamptz,
                                       p_kayit_bit timestamptz, p_eb_bit timestamptz, p_donem_sonu timestamptz)
RETURNS int LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_kul int := fn_oturum_kisi_id(); v_id int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('sekreter','yonetici')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sekreter veya yonetici donem acabilir';
  END IF;
  INSERT INTO donem (yil, tur, kayit_baslangic, kayit_bitis, ekle_birak_bitis, donem_sonu)
  VALUES (p_yil, p_tur, p_kayit_bas, p_kayit_bit, p_eb_bit, p_donem_sonu)
  RETURNING donem_id INTO v_id;
  RETURN v_id;
END $$;

CREATE OR REPLACE FUNCTION fn_sube_ac(p_ders int, p_donem int, p_sube_no smallint, p_hoca int)
RETURNS int LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_kul int := fn_oturum_kisi_id(); v_id int;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('sekreter','yonetici')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sekreter veya yonetici sube acabilir';
  END IF;
  INSERT INTO sube (ders_id, donem_id, sube_no, ogretim_uyesi_id)
  VALUES (p_ders, p_donem, p_sube_no, p_hoca)
  RETURNING sube_id INTO v_id;
  RETURN v_id;
END $$;

CREATE OR REPLACE FUNCTION fn_sube_saat_ekle(p_sube int, p_gun smallint, p_saat smallint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_kul int := fn_oturum_kisi_id();
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('sekreter','yonetici')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sekreter veya yonetici ders saati ekleyebilir';
  END IF;
  INSERT INTO sube_saat (sube_id, gun, ders_saati) VALUES (p_sube, p_gun, p_saat);
END $$;

CREATE OR REPLACE FUNCTION fn_danisman_ata(p_ogrenci int, p_danisman int, p_baslangic date DEFAULT current_date)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_kul int := fn_oturum_kisi_id(); v_eski_bas date;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol IN ('sekreter','yonetici')) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca sekreter veya yonetici danisman atayabilir';
  END IF;
  SELECT lower(gecerlilik) INTO v_eski_bas
    FROM danismanlik WHERE ogrenci_id = p_ogrenci AND upper_inf(gecerlilik);
  IF v_eski_bas IS NOT NULL THEN
    IF p_baslangic <= v_eski_bas THEN
      RAISE EXCEPTION 'GECERSIZ_GECIS: yeni danisman baslangic tarihi mevcut baslangictan sonra olmali';
    END IF;
    UPDATE danismanlik SET gecerlilik = daterange(v_eski_bas, p_baslangic, '[)')
     WHERE ogrenci_id = p_ogrenci AND upper_inf(gecerlilik);
  END IF;
  INSERT INTO danismanlik (ogrenci_id, danisman_id, gecerlilik)
  VALUES (p_ogrenci, p_danisman, daterange(p_baslangic, NULL, '[)'));
END $$;

-- Yonetici: Parametre guncelle
CREATE OR REPLACE FUNCTION fn_parametre_guncelle(p_anahtar text, p_deger text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_kul int := fn_oturum_kisi_id();
BEGIN
  IF NOT EXISTS (SELECT 1 FROM kisi_rol WHERE kisi_id = v_kul AND rol = 'yonetici') THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca yonetici parametre guncelleyebilir';
  END IF;
  UPDATE parametre SET deger = p_deger WHERE anahtar = p_anahtar;
  IF NOT FOUND THEN RAISE EXCEPTION 'KAYIT_BULUNAMADI: %', p_anahtar; END IF;
END $$;

-- Belge uret ve dogrula
CREATE OR REPLACE FUNCTION fn_belge_uret(p_tur text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_ogr int := fn_oturum_kisi_id(); v_kod text; v_hash text;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM ogrenci WHERE kisi_id = v_ogr) THEN
    RAISE EXCEPTION 'YETKISIZ: yalnizca ogrenci belge uretebilir';
  END IF;
  v_kod := substr(md5(random()::text || clock_timestamp()::text || v_ogr::text), 1, 12);
  SELECT encode(sha256(convert_to(coalesce(string_agg(kod || ':' || harf || ':' || durum, '|' ORDER BY yil, donem, kod), 'BOS'), 'UTF8')), 'hex')
    INTO v_hash
    FROM v_transkript WHERE ogrenci_no = (SELECT ogrenci_no FROM ogrenci WHERE kisi_id = v_ogr);
  INSERT INTO belge (ogrenci_id, tur, dogrulama_kodu, icerik_hash)
  VALUES (v_ogr, p_tur, v_kod, v_hash);
  RETURN v_kod;
END $$;

CREATE OR REPLACE FUNCTION fn_belge_dogrula(p_kod text)
RETURNS TABLE (gecerli boolean, ogrenci_no text, tur text, uretim_zamani timestamptz)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE b record; v_guncel_hash text; v_no text;
BEGIN
  SELECT * INTO b FROM belge WHERE dogrulama_kodu = p_kod;
  IF NOT FOUND THEN
    RETURN QUERY SELECT false, NULL::text, NULL::text, NULL::timestamptz;
    RETURN;
  END IF;
  SELECT o.ogrenci_no INTO v_no FROM ogrenci o WHERE o.kisi_id = b.ogrenci_id;
  SELECT encode(sha256(convert_to(coalesce(string_agg(kod || ':' || harf || ':' || durum, '|' ORDER BY yil, donem, kod), 'BOS'), 'UTF8')), 'hex')
    INTO v_guncel_hash
    FROM (
      SELECT ds.kod, s.harf, s.durum, d.yil, d.tur AS donem
        FROM kayit k
        JOIN donem d ON d.donem_id = k.donem_id
        JOIN ders ds ON ds.ders_id = k.ders_id
        JOIN kayit_sonuc s ON s.kayit_id = k.kayit_id
       WHERE k.ogrenci_id = b.ogrenci_id
    ) t;
  RETURN QUERY SELECT (b.icerik_hash = v_guncel_hash), v_no, b.tur::text, b.uretim_zamani;
END $$;
