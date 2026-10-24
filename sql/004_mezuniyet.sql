-- =====================================================================
-- 004_mezuniyet.sql -- "Mezuniyetime Ne Kaldi?" algoritmalari (veritabaninda)
-- On kosul: 001, 002, 003.      Calistirma: psql -d obs -f sql/004_mezuniyet.sql
--
-- fn_mezuniyet_denetim : gecilen dersleri gereksinim gruplarina ONCELIK SIRALI ACGOZLU
--                        (best-fit) eslestirir. Kesin cozum zor bir problem oldugundan gercek
--                        denetim sistemleri de sezgisel eslestirme kullanir.
--                        Bir grup cift_sayim=false ise sectigi dersler sonraki gruplarda SAYILMAZ.
--                        p_mufredat verilirse WHAT-IF: ogrencinin dersleri baska mufredata karsi denetlenir
--                        (derslerin ders_id ile eslestigi varsayilir; ders_denklik tablosu sonraki surum).
-- fn_mezuniyet_ozet    : toplam AKTS, GNO esigi ve gruplari tek satirda ozetler.
-- fn_ders_plani        : kalan zorunlu dersleri onkosul ve AKTS limitine gore donemlere dagitir
--                        (kritik yol onceligiyle acgozlu planlama).
-- fn_en_erken_mezuniyet: en az donem sayisi = onkosul grafinda en uzun yol; AKTS limitiyle gercek sayi.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) MEZUNIYET DENETIMI (gereksinim gruplari)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_mezuniyet_denetim(p_ogrenci int, p_mufredat int DEFAULT NULL)
RETURNS TABLE (grup_id int, grup_ad text, tur text, min_ders int, min_akts int,
               sayilan_ders int, sayilan_akts int, durum text, eksik text)
LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE
  v_muf int;
  g record; c record;
  v_ders int; v_akts int;
  v_secilen int[]; v_kullanilan int[] := '{}';
  v_eksik text; v_tamam boolean;
BEGIN
  v_muf := coalesce(p_mufredat, (SELECT o.mufredat_id FROM ogrenci o WHERE o.kisi_id = p_ogrenci));
  IF v_muf IS NULL THEN
    RAISE EXCEPTION 'OGRENCI_BULUNAMADI: %', p_ogrenci;
  END IF;

  FOR g IN SELECT gg.* FROM gereksinim_grubu gg WHERE gg.mufredat_id = v_muf ORDER BY gg.oncelik, gg.grup_id LOOP
    v_ders := 0; v_akts := 0; v_secilen := '{}';
    FOR c IN
      SELECT s.ders_id, s.akts
        FROM v_gecerli_sonuc s
        JOIN gereksinim_grubu_ders gd ON gd.ders_id = s.ders_id AND gd.grup_id = g.grup_id
       WHERE s.ogrenci_id = p_ogrenci AND s.durum = 'gecti'
         AND NOT (s.ders_id = ANY (v_kullanilan))
       ORDER BY s.akts DESC, s.ders_id
    LOOP
      EXIT WHEN v_ders >= g.min_ders AND v_akts >= g.min_akts;   -- esikler dolunca fazlasi baska gruba kalir
      v_secilen := v_secilen || c.ders_id;
      v_ders := v_ders + 1;
      v_akts := v_akts + c.akts;
    END LOOP;
    IF NOT g.cift_sayim THEN
      v_kullanilan := v_kullanilan || v_secilen;                  -- cift sayim yok: ders tuketildi
    END IF;

    v_tamam := v_ders >= g.min_ders AND v_akts >= g.min_akts;
    v_eksik := NULL;
    IF NOT v_tamam THEN
      IF g.tur = 'zorunlu' THEN
        SELECT string_agg(d.kod, ', ' ORDER BY d.kod) INTO v_eksik
          FROM gereksinim_grubu_ders gd JOIN ders d ON d.ders_id = gd.ders_id
         WHERE gd.grup_id = g.grup_id AND NOT (gd.ders_id = ANY (v_secilen));
      ELSE
        v_eksik := greatest(g.min_ders - v_ders, 0) || ' ders, ' || greatest(g.min_akts - v_akts, 0) || ' AKTS daha';
      END IF;
    END IF;

    RETURN QUERY SELECT g.grup_id, g.ad::text, g.tur::text, g.min_ders::int, g.min_akts::int,
                        v_ders, v_akts, CASE WHEN v_tamam THEN 'tamam' ELSE 'eksik' END, v_eksik;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- 2) OZET: toplam AKTS + GNO esigi + gruplar
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_mezuniyet_ozet(p_ogrenci int)
RETURNS TABLE (gecilen_akts int, gereken_akts int, gno numeric, min_gno numeric,
               gruplar_tamam boolean, mezuniyet_uygun boolean, eksikler text)
LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE
  v_gecilen int; v_gereken int; v_gno numeric; v_min numeric; v_tamam boolean; v_eksik text;
BEGIN
  SELECT coalesce(sum(s.akts), 0)::int INTO v_gecilen
    FROM v_gecerli_sonuc s WHERE s.ogrenci_id = p_ogrenci AND s.durum = 'gecti';
  SELECT p.toplam_akts, p.min_gno INTO v_gereken, v_min
    FROM ogrenci o JOIN program p ON p.program_id = o.program_id WHERE o.kisi_id = p_ogrenci;
  IF v_gereken IS NULL THEN
    RAISE EXCEPTION 'OGRENCI_BULUNAMADI: %', p_ogrenci;
  END IF;
  v_gno := fn_gno(p_ogrenci);
  SELECT bool_and(d.durum = 'tamam'),
         string_agg(d.grup_ad || ': ' || d.eksik, '; ' ORDER BY d.grup_id) FILTER (WHERE d.durum <> 'tamam')
    INTO v_tamam, v_eksik
    FROM fn_mezuniyet_denetim(p_ogrenci) d;
  v_tamam := coalesce(v_tamam, false);
  RETURN QUERY SELECT v_gecilen, v_gereken, v_gno, v_min, v_tamam,
                      (v_tamam AND v_gecilen >= v_gereken AND coalesce(v_gno, 0) >= v_min), v_eksik;
END $$;

-- ---------------------------------------------------------------------
-- 3) DERS PLANI: kalan zorunlu dersler, onkosul + AKTS limiti, kritik yol onceligi
--    Kalan dersler = gecilmemis zorunlular + onkosul zincirinde eksik ya da YETERSIZ NOTLU olanlar
--    (yetersiz notlu onkosul, dersin tekrar alinmasi anlamina gelir).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_ders_plani(p_ogrenci int, p_limit int DEFAULT NULL)
RETURNS TABLE (donem_sira int, ders_kod text, ders_ad text, akts int)
LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
DECLARE
  v_muf int; v_limit int; v_sira int := 0; v_toplam int;
  v_kalan int[]; v_bitmis int[]; v_sec int[]; r record;
BEGIN
  SELECT o.mufredat_id INTO v_muf FROM ogrenci o WHERE o.kisi_id = p_ogrenci;
  IF v_muf IS NULL THEN
    RAISE EXCEPTION 'OGRENCI_BULUNAMADI: %', p_ogrenci;
  END IF;
  v_limit := coalesce(p_limit, fn_akts_limit(p_ogrenci));

  WITH RECURSIVE gerekli(ders_id) AS (
    SELECT md.ders_id FROM mufredat_ders md
     WHERE md.mufredat_id = v_muf AND md.tur = 'zorunlu'
       AND NOT EXISTS (SELECT 1 FROM v_gecerli_sonuc s
                        WHERE s.ogrenci_id = p_ogrenci AND s.ders_id = md.ders_id AND s.durum = 'gecti')
    UNION
    SELECT o.onkosul_ders_id
      FROM gerekli g
      JOIN onkosul o ON o.ders_id = g.ders_id
      JOIN harf_notu_aralik m ON m.harf = o.min_harf
     WHERE NOT EXISTS (SELECT 1 FROM v_gecerli_sonuc s
                        WHERE s.ogrenci_id = p_ogrenci AND s.ders_id = o.onkosul_ders_id
                          AND s.durum = 'gecti' AND s.katsayi >= m.katsayi)
  )
  SELECT coalesce(array_agg(DISTINCT ders_id), '{}') INTO v_kalan FROM gerekli;

  SELECT coalesce(array_agg(s.ders_id), '{}') INTO v_bitmis
    FROM v_gecerli_sonuc s
   WHERE s.ogrenci_id = p_ogrenci AND s.durum = 'gecti' AND NOT (s.ders_id = ANY (v_kalan));

  WHILE coalesce(array_length(v_kalan, 1), 0) > 0 LOOP
    v_sira := v_sira + 1; v_toplam := 0; v_sec := '{}';
    FOR r IN
      WITH RECURSIVE yol(baslangic, ders_id, uzunluk) AS (          -- her dersten sonra gelen en uzun zincir
        SELECT x, x, 1 FROM unnest(v_kalan) x
        UNION ALL
        SELECT y.baslangic, o.ders_id, y.uzunluk + 1
          FROM yol y JOIN onkosul o ON o.onkosul_ders_id = y.ders_id
         WHERE o.ders_id = ANY (v_kalan)
      ), yukseklik AS (
        SELECT baslangic AS ders_id, max(uzunluk) AS yuk FROM yol GROUP BY baslangic
      )
      SELECT d.ders_id, d.kod, d.ad, d.akts, h.yuk
        FROM ders d JOIN yukseklik h ON h.ders_id = d.ders_id
       WHERE d.ders_id = ANY (v_kalan)
         AND NOT EXISTS (SELECT 1 FROM onkosul o
                          WHERE o.ders_id = d.ders_id AND NOT (o.onkosul_ders_id = ANY (v_bitmis)))
       ORDER BY h.yuk DESC, d.akts DESC, d.kod                       -- kritik yoldaki ders once
    LOOP
      IF v_toplam + r.akts <= v_limit THEN
        v_sec := v_sec || r.ders_id;
        v_toplam := v_toplam + r.akts;
        RETURN QUERY SELECT v_sira, r.kod::text, r.ad::text, r.akts::int;
      END IF;
    END LOOP;

    IF coalesce(array_length(v_sec, 1), 0) = 0 THEN
      RAISE EXCEPTION 'PLAN_KURULAMADI: AKTS limiti (%) hicbir dersi almaya yetmiyor ya da onkosul dongusu var', v_limit;
    END IF;
    v_kalan := ARRAY(SELECT x FROM unnest(v_kalan) x WHERE NOT (x = ANY (v_sec)));
    v_bitmis := v_bitmis || v_sec;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- 4) EN ERKEN MEZUNIYET: kritik yol (AKTS siniri yokmus gibi) ve AKTS limitli gercek donem sayisi
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_en_erken_mezuniyet(p_ogrenci int, p_limit int DEFAULT NULL)
RETURNS TABLE (kritik_yol_donem int, akts_limitli_donem int)
LANGUAGE plpgsql STABLE AS $$
DECLARE v_plan int; v_kritik int;
BEGIN
  SELECT coalesce(max(p.donem_sira), 0) INTO v_plan   FROM fn_ders_plani(p_ogrenci, p_limit) p;
  SELECT coalesce(max(p.donem_sira), 0) INTO v_kritik FROM fn_ders_plani(p_ogrenci, 100000) p;
  RETURN QUERY SELECT v_kritik, v_plan;
END $$;
