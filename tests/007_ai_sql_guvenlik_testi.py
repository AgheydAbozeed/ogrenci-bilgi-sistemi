"""
tests/007_ai_sql_guvenlik_testi.py — AI NL→SQL beyaz liste ve salt-okunur koruma testleri.
"""
import unittest

from app.ai.risk_motor import lojistik_risk_hesapla, model_degerlendirme_metrikleri
from app.ai.sablon_motor import NIYET_SABLONLARI, niyet_siniflandir
from app.ai.sql_koruma import SemaKatalogu, SqlGuvenlikHatasi, sql_dogrula


class TestAiSqlGuvenlik(unittest.TestCase):
    def test_ogrenci_izinli_gorunumler_gecer(self):
        sql = "SELECT ders_kod, ders_ad, akts FROM v_acik_subeler WHERE durum = 'alinabilir'"
        temiz = sql_dogrula(sql, "rol_ogrenci")
        self.assertEqual(temiz, sql)

    def test_ogrenci_mezuniyet_fonksiyonu_gecer(self):
        sql = "SELECT * FROM fn_en_erken_mezuniyet_ben()"
        self.assertEqual(sql_dogrula(sql, "rol_ogrenci"), sql)

    def test_danisman_izinli_gorunum_gecer(self):
        sql = "SELECT ogrenci_no, ad_soyad, gno FROM v_danisanlarim WHERE gno < 2.00 ORDER BY gno ASC"
        self.assertEqual(sql_dogrula(sql, "rol_danisman"), sql)

    def test_ham_tabloya_erisim_engellenir(self):
        with self.assertRaises(SqlGuvenlikHatasi):
            sql_dogrula("SELECT * FROM ogrenci", "rol_ogrenci")

    def test_rol_disi_gorunum_engellenir(self):
        with self.assertRaises(SqlGuvenlikHatasi):
            sql_dogrula("SELECT * FROM v_danisanlarim", "rol_ogrenci")

    def test_dml_ve_coklu_ifade_engellenir(self):
        with self.assertRaises(SqlGuvenlikHatasi):
            sql_dogrula("DELETE FROM v_kayitlarim", "rol_ogrenci")
        with self.assertRaises(SqlGuvenlikHatasi):
            sql_dogrula("SELECT * FROM v_ana_sayfa; DROP TABLE kayit", "rol_ogrenci")

    def test_for_update_kilidi_engellenir(self):
        with self.assertRaises(SqlGuvenlikHatasi):
            sql_dogrula("SELECT * FROM v_ana_sayfa FOR UPDATE", "rol_ogrenci")

    def test_katalog_rolleri_tanimli(self):
        for rol in ("rol_ogrenci", "rol_danisman", "rol_ogretim_uyesi", "rol_sekreter", "rol_yonetici"):
            self.assertTrue(len(SemaKatalogu.izinli_kaynaklar(rol)) > 0)

    def test_tum_sablonlar_beyaz_listeden_gecer(self):
        for sablon in NIYET_SABLONLARI:
            sql, _ = sablon.sql_uret(sablon.ornek_soru)
            for rol in sablon.roller:
                self.assertEqual(sql_dogrula(sql, rol), sql)

    def test_temel_sorular_dogru_niyete_eslenir(self):
        s1, g1 = niyet_siniflandir("GNO'su 2'nin altındaki danışanlarım kimler?", "rol_danisman")
        self.assertEqual(s1.kod, "danisman_dusuk_gno")
        self.assertGreaterEqual(g1, 80)

        s2, _ = niyet_siniflandir("Bu dönem hangi dersleri alabilirim?", "rol_ogrenci")
        self.assertEqual(s2.kod, "ogrenci_alinabilir_dersler")

        s3, _ = niyet_siniflandir("Ne zaman mezun olurum?", "rol_ogrenci")
        self.assertEqual(s3.kod, "ogrenci_mezuniyet_zamani")

    def test_lojistik_risk_ve_uc_neden_hesabi(self):
        yuksek = lojistik_risk_hesapla(
            gno=1.55,
            katilim_yuzde=55.0,
            odev_ort_puan=42.0,
            basarisiz_ders_sayisi=2,
            aktif_donem_akts=30,
        )
        dusuk = lojistik_risk_hesapla(
            gno=3.45,
            katilim_yuzde=95.0,
            odev_ort_puan=88.0,
            basarisiz_ders_sayisi=0,
            aktif_donem_akts=24,
        )
        self.assertGreater(yuksek.skor, dusuk.skor)
        self.assertEqual(len(yuksek.nedenler), 3)
        self.assertTrue(yuksek.nedenler[0].risk_artirici_mi)
        self.assertFalse(dusuk.nedenler[0].risk_artirici_mi)

        metrik = model_degerlendirme_metrikleri([yuksek, dusuk])
        self.assertEqual(metrik["tahmin_sayisi"], 2)
        self.assertEqual(sum(metrik["histogram_sayilari"]), 2)


if __name__ == "__main__":
    unittest.main()
