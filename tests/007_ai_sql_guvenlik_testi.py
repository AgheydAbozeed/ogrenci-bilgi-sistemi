"""
tests/007_ai_sql_guvenlik_testi.py — AI NL→SQL beyaz liste ve salt-okunur koruma testleri.
"""
import unittest

from app.ai.ders_oneri import ders_basari_tahmini_hesapla, uc_plan_karti_olustur
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

    def test_ne_degisirse_simulasyon_monotonlugu(self):
        taban = lojistik_risk_hesapla(
            gno=1.90,
            katilim_yuzde=62.0,
            odev_ort_puan=50.0,
            basarisiz_ders_sayisi=1,
            aktif_donem_akts=30,
        )
        iyilesmis = lojistik_risk_hesapla(
            gno=1.90,
            katilim_yuzde=92.0,
            odev_ort_puan=85.0,
            basarisiz_ders_sayisi=1,
            aktif_donem_akts=30,
        )
        kotulesmis = lojistik_risk_hesapla(
            gno=1.90,
            katilim_yuzde=40.0,
            odev_ort_puan=30.0,
            basarisiz_ders_sayisi=1,
            aktif_donem_akts=30,
        )
        self.assertLess(iyilesmis.skor, taban.skor)
        self.assertGreater(kotulesmis.skor, taban.skor)

    def test_ders_basari_tahmini_aralik_ve_siralama(self):
        secmeli_yuksek_gno = ders_basari_tahmini_hesapla(
            ders_kod="SEC105",
            ders_ad="Doğal Dil İşleme",
            akts=5,
            ogrenci_gno=3.40,
            ogrenci_sinif=2,
            daha_once_kaldi_mi=False,
        )
        zor_tekrar_dusuk_gno = ders_basari_tahmini_hesapla(
            ders_kod="MAT201",
            ders_ad="Diferansiyel Denklemler",
            akts=6,
            ogrenci_gno=1.65,
            ogrenci_sinif=1,
            daha_once_kaldi_mi=True,
        )
        self.assertTrue(35 <= secmeli_yuksek_gno.basari_yuzde <= 98)
        self.assertTrue(35 <= zor_tekrar_dusuk_gno.basari_yuzde <= 98)
        self.assertGreater(secmeli_yuksek_gno.basari_yuzde, zor_tekrar_dusuk_gno.basari_yuzde)

    def test_uc_plan_karti_kisit_ve_siralamasi(self):
        ornek_subeler = [
            {"sube_id": 1, "ders_kod": "BIL201", "ders_ad": "Veri Yapıları", "akts": 6, "saatler": "Pzt 1, Pzt 2", "durum": "alinabilir"},
            {"sube_id": 2, "ders_kod": "BIL202", "ders_ad": "Veritabanı", "akts": 6, "saatler": "Sal 1, Sal 2", "durum": "alinabilir"},
            {"sube_id": 3, "ders_kod": "MAT201", "ders_ad": "Dif. Denklemler", "akts": 6, "saatler": "Car 1, Car 2", "durum": "alinabilir"},
            {"sube_id": 4, "ders_kod": "SEC101", "ders_ad": "Seçmeli A", "akts": 6, "saatler": "Per 1, Per 2", "durum": "alinabilir"},
            {"sube_id": 5, "ders_kod": "SEC102", "ders_ad": "Seçmeli B", "akts": 6, "saatler": "Cum 1, Cum 2", "durum": "alinabilir"},
            {"sube_id": 6, "ders_kod": "BIL301", "ders_ad": "Yapay Zeka", "akts": 6, "saatler": "Pzt 1, Pzt 2", "durum": "onkosul_eksik"},
        ]
        planlar = uc_plan_karti_olustur(
            subeler_veri=ornek_subeler,
            akts_limiti=24,
            mevcut_secili_akts=0,
            ogrenci_gno=2.80,
            ogrenci_sinif=2,
        )
        self.assertEqual([p.kod for p in planlar], ["hizli", "dengeli", "guvenli"])
        for p in planlar:
            self.assertLessEqual(p.toplam_akts, 24)
            self.assertTrue(all(s["durum"] == "alinabilir" for s in p.subeler))
            self.assertTrue(len(p.gerekce) > 20)
        self.assertGreaterEqual(planlar[0].toplam_akts, planlar[2].toplam_akts)
        self.assertGreaterEqual(planlar[2].ortalama_basari_yuzde, planlar[0].ortalama_basari_yuzde)


if __name__ == "__main__":
    unittest.main()
