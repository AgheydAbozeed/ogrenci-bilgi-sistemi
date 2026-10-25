from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QLineEdit, QInputDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from app.db import Veritabani, hata_coz


class OgretimUyesiPaneli(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(10)

        ust = QHBoxLayout()
        baslik = QLabel("Şube Yönetimi, Değerlendirme Bileşenleri, Not ve Yoklama")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        ust.addWidget(QLabel("<b>Şube Seçin:</b>"))
        self.cmb_sube = QComboBox()
        self.cmb_sube.setMinimumWidth(260)
        self.cmb_sube.currentIndexChanged.connect(self.sube_yukle)
        ust.addWidget(self.cmb_sube)

        btn_bilesen = QPushButton("Vize (%40) + Final (%60) Tanımla")
        btn_bilesen.setObjectName("IkincilBtn")
        btn_bilesen.clicked.connect(self.varsayilan_bilesen)
        ust.addWidget(btn_bilesen)

        btn_ilan = QPushButton("Notları İlan Et")
        btn_ilan.setObjectName("BirincilBtn")
        btn_ilan.clicked.connect(self.notlari_ilan_et)
        ust.addWidget(btn_ilan)

        btn_hesapla = QPushButton("Harf Notlarını Hesapla")
        btn_hesapla.setObjectName("BirincilBtn")
        btn_hesapla.clicked.connect(self.harf_hesapla)
        ust.addWidget(btn_hesapla)
        self.lay.addLayout(ust)

        splitter = QSplitter(Qt.Vertical)

        # Öğrenciler ve hızlı işlem
        w_ogr = QWidget()
        l_ogr = QVBoxLayout(w_ogr)
        l_ogr.setContentsMargins(0, 0, 0, 0)
        l_ogr.addWidget(QLabel("<b>Şubedeki Öğrenciler (v_sube_ogrencileri)</b>"))
        self.tbl_ogr = QTableWidget(0, 5)
        self.tbl_ogr.setHorizontalHeaderLabels(["Kayıt #", "Öğrenci No", "Ad Soyad", "Kayıt Durumu", "İşlemler"])
        self.tbl_ogr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_ogr.setEditTriggers(QTableWidget.NoEditTriggers)
        l_ogr.addWidget(self.tbl_ogr)
        splitter.addWidget(w_ogr)

        # Girilmiş Notlar
        w_not = QWidget()
        l_not = QVBoxLayout(w_not)
        l_not.setContentsMargins(0, 0, 0, 0)
        l_not.addWidget(QLabel("<b>Şubedeki Not Kayıtları (İlan sonrası düzeltme için satırdaki butonu kullanın)</b>"))
        self.tbl_not = QTableWidget(0, 6)
        self.tbl_not.setHorizontalHeaderLabels(["Kayıt #", "Ders", "Bileşen", "Ağırlık", "Puan", "İlan Durumu / Düzelt"])
        self.tbl_not.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_not.setEditTriggers(QTableWidget.NoEditTriggers)
        l_not.addWidget(self.tbl_not)
        splitter.addWidget(w_not)

        self.lay.addWidget(splitter, 1)
        self.yenile()

    def yenile(self):
        self.cmb_sube.blockSignals(True)
        self.cmb_sube.clear()
        for s in self.db.sorgula("SELECT * FROM v_sube_listem ORDER BY donem_id DESC, ders_kod"):
            self.cmb_sube.addItem(
                f"{s['ders_kod']} - {s['ders_ad']} (Şube {s['sube_no']}) [{s['ogrenci_sayisi']} Öğr.]",
                s["sube_id"]
            )
        self.cmb_sube.blockSignals(False)
        self.sube_yukle()

    def sube_yukle(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            self.tbl_ogr.setRowCount(0)
            self.tbl_not.setRowCount(0)
            return

        bilesenler = self.db.sorgula("SELECT * FROM v_bilesenler WHERE sube_id = %s ORDER BY bilesen_id", (sube_id,))
        ogrenciler = self.db.sorgula("SELECT * FROM v_sube_ogrencileri WHERE sube_id = %s ORDER BY ogrenci_no", (sube_id,))

        self.tbl_ogr.setRowCount(0)
        for o in ogrenciler:
            r = self.tbl_ogr.rowCount()
            self.tbl_ogr.insertRow(r)
            self.tbl_ogr.setItem(r, 0, QTableWidgetItem(str(o["kayit_id"])))
            self.tbl_ogr.setItem(r, 1, QTableWidgetItem(str(o["ogrenci_no"])))
            self.tbl_ogr.setItem(r, 2, QTableWidgetItem(str(o["ad_soyad"])))
            self.tbl_ogr.setItem(r, 3, QTableWidgetItem(str(o["durum"])))

            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(2, 2, 2, 2)
            kid = o["kayit_id"]
            btn_not = QPushButton("Not Gir")
            btn_not.setObjectName("BirincilBtn")
            btn_not.clicked.connect(lambda _, x=kid, b=bilesenler: self.not_gir_dlg(x, b))
            btn_yok = QPushButton("Yoklama (Katılmadı)")
            btn_yok.setObjectName("IkincilBtn")
            btn_yok.clicked.connect(lambda _, x=kid: self.yoklama_gir(x, False))
            h.addWidget(btn_not)
            h.addWidget(btn_yok)
            self.tbl_ogr.setCellWidget(r, 4, w)

        notlar = self.db.sorgula(
            """SELECT nk.kayit_id, nk.bilesen_id, d.kod AS ders_kod, db.ad AS bilesen,
                      db.agirlik, nk.puan, nk.ilan_edildi
                 FROM not_kaydi nk
                 JOIN kayit k ON k.kayit_id = nk.kayit_id
                 JOIN ders d ON d.ders_id = k.ders_id
                 JOIN degerlendirme_bileseni db ON db.bilesen_id = nk.bilesen_id
                WHERE nk.sube_id = %s ORDER BY nk.kayit_id, nk.bilesen_id""",
            (sube_id,)
        )
        self.tbl_not.setRowCount(0)
        for n in notlar:
            r = self.tbl_not.rowCount()
            self.tbl_not.insertRow(r)
            self.tbl_not.setItem(r, 0, QTableWidgetItem(str(n["kayit_id"])))
            self.tbl_not.setItem(r, 1, QTableWidgetItem(str(n["ders_kod"])))
            self.tbl_not.setItem(r, 2, QTableWidgetItem(str(n["bilesen"])))
            self.tbl_not.setItem(r, 3, QTableWidgetItem(str(n["agirlik"])))
            self.tbl_not.setItem(r, 4, QTableWidgetItem(str(n["puan"])))

            if n["ilan_edildi"]:
                btn_d = QPushButton("Gerekçeli Düzelt")
                btn_d.setObjectName("IkincilBtn")
                kid, bid = n["kayit_id"], n["bilesen_id"]
                btn_d.clicked.connect(lambda _, k=kid, b=bid: self.not_duzelt_dlg(k, b))
                self.tbl_not.setCellWidget(r, 5, btn_d)
            else:
                self.tbl_not.setItem(r, 5, QTableWidgetItem("Taslak (İlan Edilmedi)"))

    def varsayilan_bilesen(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            self.db.calistir(
                "SELECT fn_bilesenleri_belirle(%s, ARRAY['Vize','Final'], ARRAY[40, 60])", (sube_id,)
            )
            QMessageBox.information(self, "Başarılı", "Vize (%40) ve Final (%60) bileşenleri tanımlandı.")
            self.sube_yukle()
        except Exception as e:
            QMessageBox.warning(self, "Kural Engeli", hata_coz(e))

    def not_gir_dlg(self, kayit_id: int, bilesenler: list[dict]):
        if not bilesenler:
            QMessageBox.warning(self, "Bileşen Yok", "Önce üstteki 'Vize (%40) + Final (%60) Tanımla' butonuna basın.")
            return
        adlar = [f"{b['ad']} (%{b['agirlik']})" for b in bilesenler]
        secim, ok = QInputDialog.getItem(self, "Bileşen Seç", "Not girilecek bileşen:", adlar, 0, False)
        if not ok:
            return
        bilesen_id = bilesenler[adlar.index(secim)]["bilesen_id"]
        puan, ok2 = QInputDialog.getDouble(self, "Puan Gir", "Puan (0-100):", 80, 0, 100, 1)
        if not ok2:
            return
        try:
            self.db.calistir("SELECT fn_not_gir(%s, %s, %s)", (kayit_id, bilesen_id, puan))
            self.sube_yukle()
        except Exception as e:
            QMessageBox.warning(self, "Kural Engeli", hata_coz(e))

    def not_duzelt_dlg(self, kayit_id: int, bilesen_id: int):
        puan, ok = QInputDialog.getDouble(self, "Yeni Puan", "Düzeltilmiş Puan (0-100):", 85, 0, 100, 1)
        if not ok:
            return
        gerekce, ok2 = QInputDialog.getText(self, "Zorunlu Gerekçe", "Düzeltme gerekçesi (Denetim loguna yazılır):")
        if not ok2:
            return
        try:
            self.db.calistir("SELECT fn_not_duzelt(%s, %s, %s, %s)", (kayit_id, bilesen_id, puan, gerekce))
            QMessageBox.information(self, "Düzeltildi", "Not güncellendi ve denetim loguna gerekçe işlendi.")
            self.sube_yukle()
        except Exception as e:
            QMessageBox.warning(self, "Kural Engeli", hata_coz(e))

    def yoklama_gir(self, kayit_id: int, katildi: bool):
        try:
            self.db.calistir("SELECT fn_yoklama_gir(%s, %s, %s)", (kayit_id, date.today(), katildi))
            QMessageBox.information(self, "Yoklama İşlendi", f"Bugün ({date.today()}) için yoklama kaydedildi.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))

    def notlari_ilan_et(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            r = self.db.calistir("SELECT fn_not_ilan_et(%s) AS adet", (sube_id,))
            QMessageBox.information(self, "İlan Edildi", f"{r[0]['adet']} adet taslak not ilan edildi.")
            self.sube_yukle()
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))

    def harf_hesapla(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            r = self.db.calistir("SELECT * FROM fn_sonuclari_hesapla(%s)", (sube_id,))[0]
            QMessageBox.information(
                self, "Sonuçlar Hesaplandı",
                f"Hesaplanan Öğrenci: {r['hesaplanan']}\nEksik Bileşenli Öğrenci: {r['eksik']}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))


class SekreterPaneli(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Bölüm Sekreterliği — Danışman Atama ve Risk Hesaplama")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_risk = QPushButton("Aktif Dönem Risk Bayraklarını Yeniden Hesapla")
        btn_risk.setObjectName("BirincilBtn")
        btn_risk.clicked.connect(self.risk_hesapla)
        ust.addWidget(btn_risk)
        self.lay.addLayout(ust)

        atama_kart = QFrame()
        atama_kart.setObjectName("Kart")
        a_lay = QHBoxLayout(atama_kart)
        a_lay.addWidget(QLabel("<b>Öğrenci:</b>"))
        self.cmb_ogr = QComboBox()
        a_lay.addWidget(self.cmb_ogr, 1)
        a_lay.addWidget(QLabel("<b>Yeni Danışman:</b>"))
        self.cmb_hoca = QComboBox()
        a_lay.addWidget(self.cmb_hoca, 1)
        btn_ata = QPushButton("Danışman Ata (EXCLUDE Korumalı)")
        btn_ata.setObjectName("BirincilBtn")
        btn_ata.clicked.connect(self.danisman_ata)
        a_lay.addWidget(btn_ata)
        self.lay.addWidget(atama_kart)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Öğrenci ID", "Danışman ID", "Geçerlilik Aralığı (daterange)", "Aktif mi?"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lay.addWidget(self.tbl, 1)
        self.yenile()

    def yenile(self):
        self.cmb_ogr.clear()
        for o in self.db.sorgula("SELECT o.kisi_id, o.ogrenci_no, k.ad || ' ' || k.soyad AS ad FROM ogrenci o JOIN kisi k ON k.kisi_id = o.kisi_id ORDER BY o.ogrenci_no"):
            self.cmb_ogr.addItem(f"{o['ogrenci_no']} - {o['ad']}", o["kisi_id"])

        self.cmb_hoca.clear()
        for h in self.db.sorgula("SELECT ou.kisi_id, ou.unvan || ' ' || k.ad || ' ' || k.soyad AS ad FROM ogretim_uyesi ou JOIN kisi k ON k.kisi_id = ou.kisi_id ORDER BY ou.kisi_id"):
            self.cmb_hoca.addItem(h["ad"], h["kisi_id"])

        self.tbl.setRowCount(0)
        for d in self.db.sorgula("SELECT ogrenci_id, danisman_id, gecerlilik::text AS aralik, (gecerlilik @> current_date) AS aktif FROM danismanlik ORDER BY ogrenci_id, gecerlilik"):
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(d["ogrenci_id"])))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(d["danisman_id"])))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(d["aralik"])))
            self.tbl.setItem(r, 3, QTableWidgetItem("Evet ✓" if d["aktif"] else "Geçmiş Kayıt"))

    def danisman_ata(self):
        ogr_id = self.cmb_ogr.currentData()
        hoca_id = self.cmb_hoca.currentData()
        try:
            self.db.calistir("SELECT fn_danisman_ata(%s, %s, current_date + 1)", (ogr_id, hoca_id))
            QMessageBox.information(self, "Atandı", "Eski danışmanlık aralığı kapatıldı ve yeni danışman atandı.")
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "Kural Engeli", hata_coz(e))

    def risk_hesapla(self):
        try:
            r = self.db.calistir("SELECT fn_risk_bayrak_hesapla() AS toplam")[0]
            QMessageBox.information(self, "Tamamlandı", f"Aktif dönem için toplam {r['toplam']} risk bayrağı üretildi.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))


class YoneticiPaneli(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Sistem Yönetimi — Parametreler ve SHA-256 Denetim Logu Zinciri")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_zincir = QPushButton("SHA-256 Log Zincirini Doğrula (fn_denetim_dogrula)")
        btn_zincir.setObjectName("BirincilBtn")
        btn_zincir.clicked.connect(self.zincir_dogrula)
        ust.addWidget(btn_zincir)

        btn_yenile = QPushButton("Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        splitter = QSplitter(Qt.Vertical)

        # Parametreler
        w_p = QWidget()
        l_p = QVBoxLayout(w_p)
        l_p.setContentsMargins(0, 0, 0, 0)
        l_p.addWidget(QLabel("<b>Sistem Parametreleri (v_parametreler)</b>"))
        self.tbl_param = QTableWidget(0, 4)
        self.tbl_param.setHorizontalHeaderLabels(["Anahtar", "Değer", "Açıklama", "İşlem"])
        self.tbl_param.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_param.setEditTriggers(QTableWidget.NoEditTriggers)
        l_p.addWidget(self.tbl_param)
        splitter.addWidget(w_p)

        # Denetim Logu
        w_log = QWidget()
        l_log = QVBoxLayout(w_log)
        l_log.setContentsMargins(0, 0, 0, 0)
        l_log.addWidget(QLabel("<b>Değiştirilemez Denetim Logu (v_denetim_log — Yalnızca Yönetici Görebilir)</b>"))
        self.tbl_log = QTableWidget(0, 6)
        self.tbl_log.setHorizontalHeaderLabels(["Log #", "Zaman", "Kullanıcı", "Tablo / İşlem", "PK", "Yeni Değer / Gerekçe"])
        self.tbl_log.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_log.setEditTriggers(QTableWidget.NoEditTriggers)
        l_log.addWidget(self.tbl_log)
        splitter.addWidget(w_log)

        self.lay.addWidget(splitter, 1)
        self.yenile()

    def yenile(self):
        self.tbl_param.setRowCount(0)
        for p in self.db.sorgula("SELECT * FROM v_parametreler ORDER BY anahtar"):
            r = self.tbl_param.rowCount()
            self.tbl_param.insertRow(r)
            self.tbl_param.setItem(r, 0, QTableWidgetItem(str(p["anahtar"])))
            self.tbl_param.setItem(r, 1, QTableWidgetItem(str(p["deger"])))
            self.tbl_param.setItem(r, 2, QTableWidgetItem(str(p.get("aciklama") or "")))
            btn = QPushButton("Değiştir")
            btn.setObjectName("IkincilBtn")
            anahtar, mevcut = p["anahtar"], p["deger"]
            btn.clicked.connect(lambda _, a=anahtar, m=mevcut: self.param_degistir(a, m))
            self.tbl_param.setCellWidget(r, 3, btn)

        self.tbl_log.setRowCount(0)
        for lg in self.db.sorgula("SELECT * FROM v_denetim_log ORDER BY log_id DESC LIMIT 60"):
            r = self.tbl_log.rowCount()
            self.tbl_log.insertRow(r)
            self.tbl_log.setItem(r, 0, QTableWidgetItem(str(lg["log_id"])))
            self.tbl_log.setItem(r, 1, QTableWidgetItem(str(lg["zaman"])[:19]))
            self.tbl_log.setItem(r, 2, QTableWidgetItem(str(lg["kullanici"])))
            self.tbl_log.setItem(r, 3, QTableWidgetItem(f"{lg['tablo']} ({lg['islem']})"))
            self.tbl_log.setItem(r, 4, QTableWidgetItem(str(lg["kayit_pk"])))
            self.tbl_log.setItem(r, 5, QTableWidgetItem(str(lg.get("yeni") or lg.get("eski") or "")))

    def param_degistir(self, anahtar: str, mevcut: str):
        yeni, ok = QInputDialog.getText(self, "Parametre Güncelle", f"'{anahtar}' için yeni değer:", text=mevcut)
        if not ok:
            return
        try:
            self.db.calistir("SELECT fn_parametre_guncelle(%s, %s)", (anahtar, yeni))
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))

    def zincir_dogrula(self):
        try:
            bozuk = self.db.sorgula("SELECT * FROM fn_denetim_dogrula()")
            if not bozuk:
                QMessageBox.information(
                    self, "Zincir Sağlam ✓",
                    "Tüm denetim_log satırlarının SHA-256 özet zinciri doğrulandı.\nHiçbir kırılma veya müdahale tespit edilmedi."
                )
            else:
                QMessageBox.critical(self, "Zincir Kırık!", f"Bozulan log satırları: {bozuk}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))
