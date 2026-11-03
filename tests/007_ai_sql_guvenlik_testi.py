"""
tests/007_ai_sql_guvenlik_testi.py — AI NL→SQL beyaz liste ve salt-okunur koruma testleri.
"""
import unittest

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


if __name__ == "__main__":
    unittest.main()
