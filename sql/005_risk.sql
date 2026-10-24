-- =====================================================================
-- 005_risk.sql -- Asama A: Kural tabanli akademik risk bayraklari ve ozetleri
-- =====================================================================

INSERT INTO parametre (anahtar, deger, aciklama) VALUES
  ('risk_gno_esik',         '2.00', 'GNO bu degerin altindaysa GNO_ESIK_ALTI bayragi uretilir'),
  ('risk_akts_oran',        '22',   'Sonuclanmis donem basina gecilen AKTS bu degerin altindaysa AKTS_GERIDE bayragi uretilir'),
  ('risk_devamsizlik_oran', '0.8',  'Devamsizlik sinirinin bu orani asilirsa DEVAMSIZLIK bayragi uretilir'),
  ('risk_birakma_adet',     '2',    'Son 2 donemde birakilan ders sayisi bu degere ulasirsa DERS_BIRAKMA bayragi uretilir')
ON CONFLICT (anahtar) DO NOTHING;

INSERT INTO risk_kural (kod, aciklama, siddet) VALUES
  ('GNO_ESIK_ALTI',   'Genel not ortalamasi kritik esigin altinda', 3),
  ('ZORUNLU_FF',      'Zorunlu dersten basarisiz (FF/FD) ve bu donem kaydi yok', 3),
  ('DEVAMSIZLIK',     'Bu donem onayli bir derste devamsizlik sinirina yaklasildi veya asildi', 2),
  ('AKTS_GERIDE',     'Donem basina gecilen ortalama AKTS beklenen hizin altinda', 1),
  ('ONKOSUL_BLOKAJI', 'Gecilmemis zorunlu bir dersin onkosulu basarisiz veya yetersiz notlu', 1),
  ('DERS_BIRAKMA',    'Son 2 donemde yuksek sayida ders birakma (W)', 1)
ON CONFLICT (kod) DO NOTHING;

CREATE OR REPLACE FUNCTION fn_risk_bayrak_hesapla(p_donem int DEFAULT NULL)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_donem       int;
  v_yil         int;
  v_sira        int;
  v_gno_esik    numeric;
  v_akts_oran   numeric;
  v_devam_sinir numeric;
  v_devam_oran  numeric;
  v_birak_adet  int;
  v_toplam      int;
BEGIN
  v_donem := coalesce(p_donem, (
    SELECT donem_id FROM donem
    ORDER BY yil DESC, CASE tur WHEN 'yaz' THEN 3 WHEN 'bahar' THEN 2 ELSE 1 END DESC
    LIMIT 1
  ));
  IF v_donem IS NULL THEN
    RAISE EXCEPTION 'DONEM_BULUNAMADI';
  END IF;

  SELECT yil, (yil * 10 + CASE tur WHEN 'guz' THEN 1 WHEN 'bahar' THEN 2 ELSE 3 END)
    INTO v_yil, v_sira
    FROM donem WHERE donem_id = v_donem;

  SELECT coalesce((SELECT deger::numeric FROM parametre WHERE anahtar = 'risk_gno_esik'), 2.00) INTO v_gno_esik;
  SELECT coalesce((SELECT deger::numeric FROM parametre WHERE anahtar = 'risk_akts_oran'), 22.0) INTO v_akts_oran;
  SELECT coalesce((SELECT deger::numeric FROM parametre WHERE anahtar = 'devamsizlik_siniri_yuzde'), 30.0) INTO v_devam_sinir;
  SELECT coalesce((SELECT deger::numeric FROM parametre WHERE anahtar = 'risk_devamsizlik_oran'), 0.8) INTO v_devam_oran;
  SELECT coalesce((SELECT deger::int     FROM parametre WHERE anahtar = 'risk_birakma_adet'), 2) INTO v_birak_adet;

  DELETE FROM risk_bayrak WHERE donem_id = v_donem;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT o.kisi_id, v_donem, 'GNO_ESIK_ALTI'
    FROM ogrenci o
    JOIN v_gno g ON g.ogrenci_id = o.kisi_id
   WHERE o.durum = 'aktif' AND g.gno IS NOT NULL AND g.gno < v_gno_esik
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT DISTINCT o.kisi_id, v_donem, 'ZORUNLU_FF'
    FROM ogrenci o
    JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id AND md.tur = 'zorunlu'
    JOIN v_gecerli_sonuc s ON s.ogrenci_id = o.kisi_id AND s.ders_id = md.ders_id
   WHERE o.durum = 'aktif' AND s.durum = 'kaldi'
     AND NOT EXISTS (
       SELECT 1 FROM kayit k
        WHERE k.ogrenci_id = o.kisi_id AND k.donem_id = v_donem
          AND k.ders_id = md.ders_id AND k.durum IN ('sepet', 'onay_bekliyor', 'onayli')
     )
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT o.kisi_id, v_donem, 'AKTS_GERIDE'
    FROM ogrenci o
    JOIN (
      SELECT k.ogrenci_id, count(DISTINCT k.donem_id) AS donem_sayisi,
             coalesce(v.gecilen_akts, 0) AS gecilen_akts
        FROM kayit k
        JOIN kayit_sonuc ks ON ks.kayit_id = k.kayit_id
        LEFT JOIN v_gno v   ON v.ogrenci_id = k.ogrenci_id
       GROUP BY k.ogrenci_id, v.gecilen_akts
    ) h ON h.ogrenci_id = o.kisi_id
   WHERE o.durum = 'aktif' AND h.donem_sayisi > 0
     AND (h.gecilen_akts::numeric / NULLIF(h.donem_sayisi, 0)) < v_akts_oran
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT DISTINCT k.ogrenci_id, v_donem, 'DEVAMSIZLIK'
    FROM kayit k
    JOIN ogrenci o ON o.kisi_id = k.ogrenci_id
    JOIN yoklama y ON y.kayit_id = k.kayit_id
   WHERE o.durum = 'aktif' AND k.donem_id = v_donem AND k.durum = 'onayli'
   GROUP BY k.ogrenci_id, k.kayit_id
  HAVING (avg((NOT y.katildi)::int) * 100.0) >= (v_devam_sinir * v_devam_oran)
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT DISTINCT o.kisi_id, v_donem, 'ONKOSUL_BLOKAJI'
    FROM ogrenci o
    JOIN mufredat_ders md   ON md.mufredat_id = o.mufredat_id AND md.tur = 'zorunlu'
    JOIN onkosul ok         ON ok.ders_id = md.ders_id
    JOIN harf_notu_aralik m ON m.harf = ok.min_harf
    JOIN v_gecerli_sonuc s  ON s.ogrenci_id = o.kisi_id AND s.ders_id = ok.onkosul_ders_id
   WHERE o.durum = 'aktif'
     AND NOT EXISTS (
       SELECT 1 FROM v_gecerli_sonuc gx
        WHERE gx.ogrenci_id = o.kisi_id AND gx.ders_id = md.ders_id AND gx.durum = 'gecti'
     )
     AND (s.durum <> 'gecti' OR s.katsayi < m.katsayi)
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  INSERT INTO risk_bayrak (ogrenci_id, donem_id, kural_kod)
  SELECT k.ogrenci_id, v_donem, 'DERS_BIRAKMA'
    FROM kayit k
    JOIN ogrenci o ON o.kisi_id = k.ogrenci_id
   WHERE o.durum = 'aktif' AND k.durum = 'birakti'
     AND k.donem_id IN (
       SELECT d.donem_id FROM donem d
        WHERE (d.yil * 10 + CASE d.tur WHEN 'guz' THEN 1 WHEN 'bahar' THEN 2 ELSE 3 END) <= v_sira
        ORDER BY d.yil DESC, CASE d.tur WHEN 'yaz' THEN 3 WHEN 'bahar' THEN 2 ELSE 1 END DESC
        LIMIT 2
     )
   GROUP BY k.ogrenci_id
  HAVING count(*) >= v_birak_adet
  ON CONFLICT (ogrenci_id, donem_id, kural_kod) DO NOTHING;

  SELECT count(*)::int INTO v_toplam FROM risk_bayrak WHERE donem_id = v_donem;
  RETURN v_toplam;
END $$;

CREATE OR REPLACE VIEW v_risk_ozet WITH (security_invoker = true) AS
SELECT rb.ogrenci_id, rb.donem_id,
       count(*)::int AS bayrak_sayisi,
       max(rk.siddet)::int AS en_yuksek_siddet,
       string_agg(rb.kural_kod, ', ' ORDER BY rk.siddet DESC, rb.kural_kod) AS bayrak_kodlari
  FROM risk_bayrak rb
  JOIN risk_kural rk ON rk.kod = rb.kural_kod
 GROUP BY rb.ogrenci_id, rb.donem_id;

CREATE OR REPLACE VIEW v_risk_ozellik WITH (security_invoker = true) AS
SELECT k.ogrenci_id, k.donem_id, k.ders_id,
       (SELECT count(*)::int FROM kayit k2
         WHERE k2.ogrenci_id = k.ogrenci_id AND k2.ders_id = k.ders_id
           AND k2.donem_id < k.donem_id AND k2.durum <> 'birakti') AS onceki_deneme,
       coalesce((SELECT sum(d2.akts)::int FROM kayit k3 JOIN ders d2 ON d2.ders_id = k3.ders_id
                  WHERE k3.ogrenci_id = k.ogrenci_id AND k3.donem_id = k.donem_id
                    AND k3.durum IN ('onay_bekliyor', 'onayli')), 0) AS alinan_kredi,
       EXTRACT(DAY FROM (k.olusturma - dn.kayit_baslangic))::int AS kayit_gunu,
       (SELECT round(avg(nk.puan), 2) FROM not_kaydi nk
         WHERE nk.kayit_id = k.kayit_id AND nk.ilan_edildi) AS ort_puan,
       (SELECT round(1.0 - (count(nk.bilesen_id)::numeric / NULLIF(count(db.bilesen_id), 0)), 2)
          FROM degerlendirme_bileseni db
          LEFT JOIN not_kaydi nk ON nk.bilesen_id = db.bilesen_id AND nk.kayit_id = k.kayit_id AND nk.ilan_edildi
         WHERE db.sube_id = k.sube_id) AS eksik_oran,
       (SELECT round(avg(y.katildi::int), 2) FROM yoklama y WHERE y.kayit_id = k.kayit_id) AS katilim_orani
  FROM kayit k
  JOIN donem dn ON dn.donem_id = k.donem_id
 WHERE k.durum = 'onayli';
