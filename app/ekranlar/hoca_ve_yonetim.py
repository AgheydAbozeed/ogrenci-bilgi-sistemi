from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QInputDialog, QMessageBox, QSplitter, QTabWidget,
    QLineEdit, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_goster
from app.stil import OLCULER
from app.ekranlar.ogrenci_ana import bilgi_karti


def _kartlari_temizle(lay: QHBoxLayout):
    while lay.count():
        it = lay.takeAt(0)
        if it.widget():
            it.widget().deleteLater()


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

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w_ogr = QFrame()
        w_ogr.setObjectName("PortalKart")
        l_ogr = QVBoxLayout(w_ogr)
        l_ogr.setContentsMargins(14, 10, 14, 10)
        l_ogr.addWidget(QLabel("<b>Şubedeki Öğrenciler (v_sube_ogrencileri)</b>"))
        self.tbl_ogr = QTableWidget(0, 5)
        self.tbl_ogr.setHorizontalHeaderLabels(["Kayıt #", "Öğrenci No", "Ad Soyad", "Kayıt Durumu", "İşlemler"])
        self.tbl_ogr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_ogr.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_ogr.setEditTriggers(QTableWidget.NoEditTriggers)
        l_ogr.addWidget(self.tbl_ogr)
        splitter.addWidget(w_ogr)

        w_not = QFrame()
        w_not.setObjectName("PortalKart")
        l_not = QVBoxLayout(w_not)
        l_not.setContentsMargins(14, 10, 14, 10)
        l_not.addWidget(QLabel("<b>Şubedeki Not Kayıtları (İlan sonrası düzeltme için satırdaki butonu kullanın)</b>"))
        self.tbl_not = QTableWidget(0, 6)
        self.tbl_not.setHorizontalHeaderLabels(["Kayıt #", "Ders", "Bileşen", "Ağırlık", "Puan", "İlan Durumu / Düzelt"])
        self.tbl_not.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_not.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
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

        self.tbl_ogr.setUpdatesEnabled(False)
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
        self.tbl_ogr.setUpdatesEnabled(True)

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
        self.tbl_not.setUpdatesEnabled(False)
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
                t_it = QTableWidgetItem("⏳ Taslak (İlan Edilmedi)")
                t_it.setBackground(QBrush(QColor("#FEF3C7")))
                t_it.setForeground(QBrush(QColor("#92400E")))
                self.tbl_not.setItem(r, 5, t_it)
        self.tbl_not.setUpdatesEnabled(True)

        _kartlari_temizle(self.kart_lay)
        self.kart_lay.addWidget(bilgi_karti("Aktif Şubelerim", f"{self.cmb_sube.count()} Şube", "👨‍🏫", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Şubedeki Öğrenci", f"{self.tbl_ogr.rowCount()} Öğrenci", "👥", "#15803D"))
        self.kart_lay.addWidget(bilgi_karti("Girilen Not Kaydı", f"{self.tbl_not.rowCount()} Not", "📝", "#2563EB"))

    def varsayilan_bilesen(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            self.db.calistir(
                "SELECT fn_bilesenleri_belirle(%s, ARRAY['Vize','Final'], ARRAY[40, 60])", (sube_id,)
            )
            QMessageBox.information(self, "Başarılı ✔", "Vize (%40) ve Final (%60) bileşenleri tanımlandı.")
            self.sube_yukle()
        except Exception as e:
            hata_goster(self, "Kural Engeli", e)

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
            self.db.calistir("SELECT fn_not_gir(%s::int, %s::int, %s::numeric)", (kayit_id, bilesen_id, puan))
            self.sube_yukle()
        except Exception as e:
            hata_goster(self, "Kural Engeli", e)

    def not_duzelt_dlg(self, kayit_id: int, bilesen_id: int):
        puan, ok = QInputDialog.getDouble(self, "Yeni Puan", "Düzeltilmiş Puan (0-100):", 85, 0, 100, 1)
        if not ok:
            return
        gerekce, ok2 = QInputDialog.getText(self, "Zorunlu Gerekçe", "Düzeltme gerekçesi (Denetim loguna yazılır):")
        if not ok2:
            return
        try:
            self.db.calistir("SELECT fn_not_duzelt(%s::int, %s::int, %s::numeric, %s)", (kayit_id, bilesen_id, puan, gerekce))
            QMessageBox.information(self, "Düzeltildi ✔", "Not güncellendi ve denetim loguna gerekçe işlendi.")
            self.sube_yukle()
        except Exception as e:
            hata_goster(self, "Kural Engeli", e)

    def yoklama_gir(self, kayit_id: int, katildi: bool):
        try:
            self.db.calistir("SELECT fn_yoklama_gir(%s, %s, %s)", (kayit_id, date.today(), katildi))
            QMessageBox.information(self, "Yoklama İşlendi", f"Bugün ({date.today()}) için yoklama kaydedildi.")
        except Exception as e:
            hata_goster(self, "Hata", e)

    def notlari_ilan_et(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            r = self.db.calistir("SELECT fn_not_ilan_et(%s) AS adet", (sube_id,))
            QMessageBox.information(self, "İlan Edildi ✔", f"{r[0]['adet']} adet taslak not ilan edildi.")
            self.sube_yukle()
        except Exception as e:
            hata_goster(self, "Hata", e)

    def harf_hesapla(self):
        sube_id = self.cmb_sube.currentData()
        if not sube_id:
            return
        try:
            r = self.db.calistir("SELECT * FROM fn_sonuclari_hesapla(%s)", (sube_id,))[0]
            QMessageBox.information(
                self, "Sonuçlar Hesaplandı ✔",
                f"Hesaplanan Öğrenci: {r['hesaplanan']}\nEksik Bileşenli Öğrenci: {r['eksik']}"
            )
        except Exception as e:
            hata_goster(self, "Hata", e)


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

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        atama_kart = QFrame()
        atama_kart.setObjectName("PortalKart")
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
        self.tbl.setHorizontalHeaderLabels(["Öğrenci (No - Ad Soyad)", "Danışman", "Geçerlilik Aralığı (daterange)", "Aktif mi?"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
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

        self.tbl.setUpdatesEnabled(False)
        self.tbl.setRowCount(0)
        sorgu_dan = """
            SELECT o.ogrenci_no || ' — ' || ko.ad || ' ' || ko.soyad AS ogrenci_bilgi,
                   ou.unvan || ' ' || kd.ad || ' ' || kd.soyad AS danisman_bilgi,
                   d.gecerlilik::text AS aralik,
                   (d.gecerlilik @> current_date) AS aktif
              FROM danismanlik d
              JOIN ogrenci o ON o.kisi_id = d.ogrenci_id
              JOIN kisi ko ON ko.kisi_id = o.kisi_id
              JOIN ogretim_uyesi ou ON ou.kisi_id = d.danisman_id
              JOIN kisi kd ON kd.kisi_id = ou.kisi_id
             ORDER BY o.ogrenci_no, d.gecerlilik DESC
        """
        for d in self.db.sorgula(sorgu_dan):
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(d["ogrenci_bilgi"])))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(d["danisman_bilgi"])))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(d["aralik"])))
            a_it = QTableWidgetItem("✔ Aktif Atama" if d["aktif"] else "— Geçmiş Kayıt")
            a_it.setBackground(QBrush(QColor("#DCFCE7" if d["aktif"] else "#F1F5F9")))
            a_it.setForeground(QBrush(QColor("#15803D" if d["aktif"] else "#475569")))
            self.tbl.setItem(r, 3, a_it)
        self.tbl.setUpdatesEnabled(True)

        _kartlari_temizle(self.kart_lay)
        self.kart_lay.addWidget(bilgi_karti("Bölüm Öğrencileri", f"{self.cmb_ogr.count()} Öğrenci", "🎓", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Bölüm Danışmanları", f"{self.cmb_hoca.count()} Hoca", "☑️", "#15803D"))
        self.kart_lay.addWidget(bilgi_karti("Atama Kayıtları", f"{self.tbl.rowCount()} Kayıt", "🗂️", "#2563EB"))

    def danisman_ata(self):
        ogr_id = self.cmb_ogr.currentData()
        hoca_id = self.cmb_hoca.currentData()
        try:
            self.db.calistir("SELECT fn_danisman_ata(%s, %s, current_date)", (ogr_id, hoca_id))
            QMessageBox.information(self, "Atandı ✔", "Eski danışmanlık aralığı kapatıldı ve yeni danışman atandı.")
            self.yenile()
        except Exception as e:
            hata_goster(self, "Kural Engeli", e)

    def risk_hesapla(self):
        try:
            r = self.db.calistir("SELECT fn_risk_bayrak_hesapla() AS toplam")[0]
            QMessageBox.information(self, "Tamamlandı ✔", f"Aktif dönem için toplam {r['toplam']} risk bayrağı üretildi.")
        except Exception as e:
            hata_goster(self, "Hata", e)


class YoneticiKayitEklemePaneli(QWidget):
    """
    Sistem Yöneticisi için Kurumsal Kayıt Yönetimi:
    - Yeni Öğrenci Ekle (5 haneli otomatik [YY][B][SS] öğrenci no, danışman ve müfredat atamalı)
    - Yeni Öğretmen / Akademisyen Ekle (5 haneli otomatik 10[B][SS] personel no, unvan, bölüm ve rol atamalı)
    - Yeni Ders & Müfredat Ekle (Önkoşul DAG kontrolü ve isteğe bağlı aktif dönem şube açılışı ile)
    - Mevcut Derse Yeni Şube & Ders Saati Aç
    """

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Kurumsal Kayıt Yönetimi — Öğrenci, Akademisyen, Ders ve Şube Ekle")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_yenile = QPushButton("↻  Tüm Listeleri Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        self.sekmeler = QTabWidget()
        self.sekmeler.addTab(self._ogrenci_sekmesi_olustur(), "🎓  Öğrenci Ekle & Listele")
        self.sekmeler.addTab(self._ogretmen_sekmesi_olustur(), "👨‍🏫  Akademisyen / Öğretmen Ekle")
        self.sekmeler.addTab(self._ders_sekmesi_olustur(), "📚  Ders & Müfredat Ekle")
        self.sekmeler.addTab(self._sube_sekmesi_olustur(), "🗓️  Şube & Ders Saati Aç")
        self.lay.addWidget(self.sekmeler, 1)

        self.yenile()

    # ------------------------------------------------------------------
    # SEKME 1: ÖĞRENCİ EKLEME VE LİSTELEME
    # ------------------------------------------------------------------
    def _ogrenci_sekmesi_olustur(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        form_kart = QFrame()
        form_kart.setObjectName("PortalKart")
        g = QGridLayout(form_kart)
        g.setContentsMargins(14, 12, 14, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)

        g.addWidget(QLabel("<b>Ad:</b>"), 0, 0)
        self.txt_ogr_ad = QLineEdit()
        self.txt_ogr_ad.setPlaceholderText("Örn: Kerem")
        g.addWidget(self.txt_ogr_ad, 0, 1)

        g.addWidget(QLabel("<b>Soyad:</b>"), 0, 2)
        self.txt_ogr_soyad = QLineEdit()
        self.txt_ogr_soyad.setPlaceholderText("Örn: Aydın")
        g.addWidget(self.txt_ogr_soyad, 0, 3)

        g.addWidget(QLabel("<b>Program / Bölüm:</b>"), 0, 4)
        self.cmb_ogr_prog = QComboBox()
        self.cmb_ogr_prog.currentIndexChanged.connect(self._otomatik_ogrenci_no_oner)
        g.addWidget(self.cmb_ogr_prog, 0, 5)

        g.addWidget(QLabel("<b>Giriş Yılı:</b>"), 1, 0)
        self.spn_ogr_yil = QSpinBox()
        self.spn_ogr_yil.setRange(2020, 2030)
        self.spn_ogr_yil.setValue(2025)
        self.spn_ogr_yil.valueChanged.connect(self._otomatik_ogrenci_no_oner)
        g.addWidget(self.spn_ogr_yil, 1, 1)

        g.addWidget(QLabel("<b>Öğrenci No (5 Hane):</b>"), 1, 2)
        no_lay = QHBoxLayout()
        no_lay.setSpacing(4)
        self.txt_ogr_no = QLineEdit()
        self.txt_ogr_no.setMaxLength(12)
        self.txt_ogr_no.textChanged.connect(self._ogr_no_degisti)
        no_lay.addWidget(self.txt_ogr_no, 1)
        btn_oto_no = QPushButton("🔄")
        btn_oto_no.setObjectName("IkincilBtn")
        btn_oto_no.setFixedWidth(34)
        btn_oto_no.setToolTip("Giriş yılı ve bölüme göre sıradaki 5 haneli numarayı öner")
        btn_oto_no.clicked.connect(self._otomatik_ogrenci_no_oner)
        no_lay.addWidget(btn_oto_no)
        g.addLayout(no_lay, 1, 3)

        g.addWidget(QLabel("<b>Kurumsal E-Posta:</b>"), 1, 4)
        self.txt_ogr_eposta = QLineEdit()
        self.txt_ogr_eposta.setPlaceholderText("Örn: 25106@ogrenci.edu.tr")
        g.addWidget(self.txt_ogr_eposta, 1, 5)

        g.addWidget(QLabel("<b>Akademik Danışman:</b>"), 2, 0)
        self.cmb_ogr_danisman = QComboBox()
        g.addWidget(self.cmb_ogr_danisman, 2, 1, 1, 2)

        g.addWidget(QLabel("<b>Başlangıç Şifresi:</b>"), 2, 3)
        self.txt_ogr_sifre = QLineEdit("123456")
        g.addWidget(self.txt_ogr_sifre, 2, 4)

        btn_ekle = QPushButton("➕  Yeni Öğrenciyi Sisteme Kaydet")
        btn_ekle.setObjectName("BirincilBtn")
        btn_ekle.setMinimumHeight(34)
        btn_ekle.clicked.connect(self.ogrenci_ekle)
        g.addWidget(btn_ekle, 2, 5)

        v.addWidget(form_kart)

        ara_lay = QHBoxLayout()
        ara_lay.addWidget(QLabel("<b>📋 Sistemdeki Kayıtlı Öğrenciler (v_yonetici_ogrenciler)</b>"))
        ara_lay.addStretch()
        self.txt_ogr_ara = QLineEdit()
        self.txt_ogr_ara.setPlaceholderText("🔍 Öğrenci no, ad soyad veya bölüm ara...")
        self.txt_ogr_ara.setMinimumWidth(260)
        self.txt_ogr_ara.textChanged.connect(lambda m: self._tablo_filtrele(self.tbl_ogrenciler, m))
        ara_lay.addWidget(self.txt_ogr_ara)
        v.addLayout(ara_lay)

        self.tbl_ogrenciler = QTableWidget(0, 8)
        self.tbl_ogrenciler.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "E-Posta", "Program / Bölüm",
            "Giriş Yılı", "Danışman", "GNO / AKTS", "Durum"
        ])
        self.tbl_ogrenciler.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_ogrenciler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_ogrenciler.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_ogrenciler.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.tbl_ogrenciler, 1)
        return w

    # ------------------------------------------------------------------
    # SEKME 2: ÖĞRETMEN / AKADEMİSYEN EKLEME VE LİSTELEME
    # ------------------------------------------------------------------
    def _ogretmen_sekmesi_olustur(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        form_kart = QFrame()
        form_kart.setObjectName("PortalKart")
        g = QGridLayout(form_kart)
        g.setContentsMargins(14, 12, 14, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)

        g.addWidget(QLabel("<b>Unvan:</b>"), 0, 0)
        self.cmb_hoca_unvan = QComboBox()
        for u in ["Dr. Öğr. Üyesi", "Doç. Dr.", "Prof. Dr.", "Öğr. Gör. Dr.", "Arş. Gör."]:
            self.cmb_hoca_unvan.addItem(u, u)
        g.addWidget(self.cmb_hoca_unvan, 0, 1)

        g.addWidget(QLabel("<b>Ad:</b>"), 0, 2)
        self.txt_hoca_ad = QLineEdit()
        self.txt_hoca_ad.setPlaceholderText("Örn: Hakan")
        g.addWidget(self.txt_hoca_ad, 0, 3)

        g.addWidget(QLabel("<b>Soyad:</b>"), 0, 4)
        self.txt_hoca_soyad = QLineEdit()
        self.txt_hoca_soyad.setPlaceholderText("Örn: Tekin")
        g.addWidget(self.txt_hoca_soyad, 0, 5)

        g.addWidget(QLabel("<b>Bölüm:</b>"), 1, 0)
        self.cmb_hoca_bolum = QComboBox()
        self.cmb_hoca_bolum.currentIndexChanged.connect(self._otomatik_akademisyen_no_oner)
        g.addWidget(self.cmb_hoca_bolum, 1, 1)

        g.addWidget(QLabel("<b>Personel No (5 Hane):</b>"), 1, 2)
        no_lay = QHBoxLayout()
        no_lay.setSpacing(4)
        self.txt_hoca_no = QLineEdit()
        self.txt_hoca_no.setMaxLength(12)
        self.txt_hoca_no.textChanged.connect(self._hoca_no_degisti)
        no_lay.addWidget(self.txt_hoca_no, 1)
        btn_oto_hno = QPushButton("🔄")
        btn_oto_hno.setObjectName("IkincilBtn")
        btn_oto_hno.setFixedWidth(34)
        btn_oto_hno.clicked.connect(self._otomatik_akademisyen_no_oner)
        no_lay.addWidget(btn_oto_hno)
        g.addLayout(no_lay, 1, 3)

        g.addWidget(QLabel("<b>Kurumsal E-Posta:</b>"), 1, 4)
        self.txt_hoca_eposta = QLineEdit()
        self.txt_hoca_eposta.setPlaceholderText("Örn: 10104@ornek.edu.tr")
        g.addWidget(self.txt_hoca_eposta, 1, 5)

        g.addWidget(QLabel("<b>Ek Yetki Rolü:</b>"), 2, 0)
        self.cmb_hoca_ekrol = QComboBox()
        self.cmb_hoca_ekrol.addItem("Yalnızca Öğretim Üyesi", None)
        self.cmb_hoca_ekrol.addItem("Öğretim Üyesi + Bölüm Sekreteri", "sekreter")
        self.cmb_hoca_ekrol.addItem("Öğretim Üyesi + Sistem Yöneticisi", "yonetici")
        g.addWidget(self.cmb_hoca_ekrol, 2, 1, 1, 2)

        g.addWidget(QLabel("<b>Başlangıç Şifresi:</b>"), 2, 3)
        self.txt_hoca_sifre = QLineEdit("123456")
        g.addWidget(self.txt_hoca_sifre, 2, 4)

        btn_ekle = QPushButton("➕  Yeni Akademisyeni Kaydet")
        btn_ekle.setObjectName("BirincilBtn")
        btn_ekle.setMinimumHeight(34)
        btn_ekle.clicked.connect(self.ogretmen_ekle)
        g.addWidget(btn_ekle, 2, 5)

        v.addWidget(form_kart)

        v.addWidget(QLabel("<b>📋 Sistemdeki Akademisyenler / Öğretim Üyeleri (v_yonetici_akademisyenler)</b>"))
        self.tbl_akademisyenler = QTableWidget(0, 7)
        self.tbl_akademisyenler.setHorizontalHeaderLabels([
            "Personel No", "Unvan", "Ad Soyad", "E-Posta", "Bölüm",
            "Aktif Dönem Şube Sayısı", "Danışan Öğrenci Sayısı"
        ])
        self.tbl_akademisyenler.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_akademisyenler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_akademisyenler.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_akademisyenler.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.tbl_akademisyenler, 1)
        return w

    # ------------------------------------------------------------------
    # SEKME 3: YENİ DERS & MÜFREDAT EKLEME
    # ------------------------------------------------------------------
    def _ders_sekmesi_olustur(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        form_kart = QFrame()
        form_kart.setObjectName("PortalKart")
        g = QGridLayout(form_kart)
        g.setContentsMargins(14, 12, 14, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)

        g.addWidget(QLabel("<b>Ders Kodu:</b>"), 0, 0)
        self.txt_ders_kod = QLineEdit()
        self.txt_ders_kod.setPlaceholderText("Örn: BIL305")
        self.txt_ders_kod.setMaxLength(12)
        g.addWidget(self.txt_ders_kod, 0, 1)

        g.addWidget(QLabel("<b>Ders Adı:</b>"), 0, 2)
        self.txt_ders_ad = QLineEdit()
        self.txt_ders_ad.setPlaceholderText("Örn: Blokzincir ve Dağıtık Sistemler")
        g.addWidget(self.txt_ders_ad, 0, 3, 1, 3)

        g.addWidget(QLabel("<b>AKTS Kredisi:</b>"), 1, 0)
        self.spn_ders_akts = QSpinBox()
        self.spn_ders_akts.setRange(1, 15)
        self.spn_ders_akts.setValue(6)
        g.addWidget(self.spn_ders_akts, 1, 1)

        g.addWidget(QLabel("<b>Teorik / Uyg. Saat:</b>"), 1, 2)
        saat_lay = QHBoxLayout()
        self.spn_ders_teo = QSpinBox()
        self.spn_ders_teo.setRange(0, 10)
        self.spn_ders_teo.setValue(3)
        self.spn_ders_uyg = QSpinBox()
        self.spn_ders_uyg.setRange(0, 10)
        self.spn_ders_uyg.setValue(2)
        saat_lay.addWidget(self.spn_ders_teo)
        saat_lay.addWidget(QLabel("+"))
        saat_lay.addWidget(self.spn_ders_uyg)
        g.addLayout(saat_lay, 1, 3)

        g.addWidget(QLabel("<b>Yarıyıl / Tür:</b>"), 1, 4)
        yt_lay = QHBoxLayout()
        self.spn_ders_donem = QSpinBox()
        self.spn_ders_donem.setRange(1, 8)
        self.spn_ders_donem.setValue(5)
        self.spn_ders_donem.setSuffix(". Yarıyıl")
        self.cmb_ders_tur = QComboBox()
        self.cmb_ders_tur.addItem("Zorunlu Ders", "zorunlu")
        self.cmb_ders_tur.addItem("Seçmeli Ders", "secmeli")
        yt_lay.addWidget(self.spn_ders_donem)
        yt_lay.addWidget(self.cmb_ders_tur)
        g.addLayout(yt_lay, 1, 5)

        g.addWidget(QLabel("<b>Önkoşul Dersi:</b>"), 2, 0)
        onk_lay = QHBoxLayout()
        self.cmb_ders_onkosul = QComboBox()
        self.cmb_ders_minharf = QComboBox()
        for h in ["DD", "DC", "CC", "CB", "BB"]:
            self.cmb_ders_minharf.addItem(f"Min {h}", h)
        onk_lay.addWidget(self.cmb_ders_onkosul, 1)
        onk_lay.addWidget(self.cmb_ders_minharf)
        g.addLayout(onk_lay, 2, 1, 1, 2)

        g.addWidget(QLabel("<b>Aktif Dönem Şubesi:</b>"), 2, 3)
        sb_lay = QHBoxLayout()
        self.cmb_ders_sube_hoca = QComboBox()
        self.cmb_ders_gun = QComboBox()
        for idx, g_ad in enumerate(["Pzt", "Sal", "Çar", "Per", "Cum"], 1):
            self.cmb_ders_gun.addItem(g_ad, idx)
        self.spn_ders_saat = QSpinBox()
        self.spn_ders_saat.setRange(1, 8)
        self.spn_ders_saat.setValue(3)
        self.spn_ders_saat.setSuffix(". Saat")
        sb_lay.addWidget(self.cmb_ders_sube_hoca, 1)
        sb_lay.addWidget(self.cmb_ders_gun)
        sb_lay.addWidget(self.spn_ders_saat)
        g.addLayout(sb_lay, 2, 4)

        btn_ekle = QPushButton("➕  Dersi Müfredata Kaydet")
        btn_ekle.setObjectName("BirincilBtn")
        btn_ekle.setMinimumHeight(34)
        btn_ekle.clicked.connect(self.ders_ekle)
        g.addWidget(btn_ekle, 2, 5)

        v.addWidget(form_kart)

        ara_lay = QHBoxLayout()
        ara_lay.addWidget(QLabel("<b>📋 Müfredattaki Tüm Dersler ve Önkoşul Bağlantıları (v_yonetici_dersler)</b>"))
        ara_lay.addStretch()
        self.txt_ders_ara = QLineEdit()
        self.txt_ders_ara.setPlaceholderText("🔍 Ders kodu veya adı ara...")
        self.txt_ders_ara.setMinimumWidth(240)
        self.txt_ders_ara.textChanged.connect(lambda m: self._tablo_filtrele(self.tbl_dersler, m))
        ara_lay.addWidget(self.txt_ders_ara)
        v.addLayout(ara_lay)

        self.tbl_dersler = QTableWidget(0, 8)
        self.tbl_dersler.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "AKTS", "Saat (T+U)",
            "Yarıyıl", "Tür", "Önkoşul(lar)", "Aktif Şube"
        ])
        self.tbl_dersler.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_dersler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_dersler.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_dersler.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.tbl_dersler, 1)
        return w

    # ------------------------------------------------------------------
    # SEKME 4: MEVCUT DERSE ŞUBE VE DERS SAATİ AÇMA
    # ------------------------------------------------------------------
    def _sube_sekmesi_olustur(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        form_kart = QFrame()
        form_kart.setObjectName("PortalKart")
        g = QGridLayout(form_kart)
        g.setContentsMargins(14, 12, 14, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)

        g.addWidget(QLabel("<b>Ders Seçin:</b>"), 0, 0)
        self.cmb_sb_ders = QComboBox()
        g.addWidget(self.cmb_sb_ders, 0, 1, 1, 2)

        g.addWidget(QLabel("<b>Öğretim Üyesi:</b>"), 0, 3)
        self.cmb_sb_hoca = QComboBox()
        g.addWidget(self.cmb_sb_hoca, 0, 4, 1, 2)

        g.addWidget(QLabel("<b>Şube No:</b>"), 1, 0)
        self.spn_sb_no = QSpinBox()
        self.spn_sb_no.setRange(1, 10)
        self.spn_sb_no.setValue(2)
        g.addWidget(self.spn_sb_no, 1, 1)

        g.addWidget(QLabel("<b>Ders Günü:</b>"), 1, 2)
        self.cmb_sb_gun = QComboBox()
        for idx, g_ad in enumerate(["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"], 1):
            self.cmb_sb_gun.addItem(g_ad, idx)
        g.addWidget(self.cmb_sb_gun, 1, 3)

        g.addWidget(QLabel("<b>Başlangıç Saati:</b>"), 1, 4)
        self.spn_sb_saat = QSpinBox()
        self.spn_sb_saat.setRange(1, 8)
        self.spn_sb_saat.setValue(3)
        self.spn_sb_saat.setSuffix(". Saat")
        g.addWidget(self.spn_sb_saat, 1, 5)

        btn_sb_ac = QPushButton("➕  Aktif Dönemde Yeni Şube Aç ve Saat Ekle (fn_sube_ac)")
        btn_sb_ac.setObjectName("BirincilBtn")
        btn_sb_ac.setMinimumHeight(34)
        btn_sb_ac.clicked.connect(self.sube_ac_islem)
        g.addWidget(btn_sb_ac, 2, 0, 1, 6)

        v.addWidget(form_kart)

        v.addWidget(QLabel("<b>📋 Aktif Dönem (2026 Güz) Açık Şubeler ve Öğretim Üyeleri</b>"))
        self.tbl_subeler = QTableWidget(0, 6)
        self.tbl_subeler.setHorizontalHeaderLabels([
            "Şube #", "Ders Kodu", "Ders Adı", "Şube No", "Öğretim Üyesi", "Ders Saatleri"
        ])
        self.tbl_subeler.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_subeler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_subeler.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(self.tbl_subeler, 1)
        return w

    def _tablo_filtrele(self, tbl: QTableWidget, metin: str):
        q = metin.strip().lower()
        for r in range(tbl.rowCount()):
            eslesti = any(
                q in (tbl.item(r, c).text().lower() if tbl.item(r, c) else "")
                for c in range(tbl.columnCount())
            )
            tbl.setRowHidden(r, not eslesti)

    def _otomatik_ogrenci_no_oner(self):
        prog_id = self.cmb_ogr_prog.currentData()
        yil = self.spn_ogr_yil.value()
        if not prog_id:
            return
        try:
            r = self.db.tek_satir("SELECT fn_sonraki_ogrenci_no(%s::smallint, %s::int) AS no", (yil, prog_id))
            if r and r.get("no"):
                self.txt_ogr_no.setText(str(r["no"]))
        except Exception:
            pass

    def _ogr_no_degisti(self, metin: str):
        no = metin.strip()
        if no:
            self.txt_ogr_eposta.setText(f"{no}@ogrenci.edu.tr")

    def _otomatik_akademisyen_no_oner(self):
        bolum_id = self.cmb_hoca_bolum.currentData()
        if not bolum_id:
            return
        try:
            r = self.db.tek_satir("SELECT fn_sonraki_akademisyen_no(%s::int) AS no", (bolum_id,))
            if r and r.get("no"):
                self.txt_hoca_no.setText(str(r["no"]))
        except Exception:
            pass

    def _hoca_no_degisti(self, metin: str):
        no = metin.strip()
        if no:
            self.txt_hoca_eposta.setText(f"{no}@ornek.edu.tr")

    def yenile(self):
        # Seçim kutularını doldur
        self.cmb_ogr_prog.blockSignals(True)
        self.cmb_ogr_prog.clear()
        for p in self.db.sorgula("SELECT program_id, ad FROM program ORDER BY program_id"):
            self.cmb_ogr_prog.addItem(p["ad"], p["program_id"])
        self.cmb_ogr_prog.blockSignals(False)

        self.cmb_hoca_bolum.blockSignals(True)
        self.cmb_hoca_bolum.clear()
        for b in self.db.sorgula("SELECT bolum_id, ad FROM bolum ORDER BY bolum_id"):
            self.cmb_hoca_bolum.addItem(b["ad"], b["bolum_id"])
        self.cmb_hoca_bolum.blockSignals(False)

        hocalar = self.db.sorgula(
            "SELECT ou.kisi_id, ou.unvan || ' ' || k.ad || ' ' || k.soyad AS ad_soyad "
            "FROM ogretim_uyesi ou JOIN kisi k ON k.kisi_id = ou.kisi_id ORDER BY ou.kisi_id"
        )
        self.cmb_ogr_danisman.clear()
        self.cmb_sb_hoca.clear()
        self.cmb_ders_sube_hoca.clear()
        self.cmb_ders_sube_hoca.addItem("— Şube Açma —", None)
        for h in hocalar:
            self.cmb_ogr_danisman.addItem(h["ad_soyad"], h["kisi_id"])
            self.cmb_sb_hoca.addItem(h["ad_soyad"], h["kisi_id"])
            self.cmb_ders_sube_hoca.addItem(f"1. Şubeyi Aç: {h['ad_soyad']}", h["kisi_id"])
        if self.cmb_ders_sube_hoca.count() > 1:
            self.cmb_ders_sube_hoca.setCurrentIndex(1)

        dersler_kisa = self.db.sorgula("SELECT ders_id, kod, ad FROM ders ORDER BY kod")
        self.cmb_ders_onkosul.clear()
        self.cmb_ders_onkosul.addItem("— Önkoşul Yok —", None)
        self.cmb_sb_ders.clear()
        for d in dersler_kisa:
            etiket = f"{d['kod']} — {d['ad']}"
            self.cmb_ders_onkosul.addItem(etiket, d["ders_id"])
            self.cmb_sb_ders.addItem(etiket, d["ders_id"])

        self._otomatik_ogrenci_no_oner()
        self._otomatik_akademisyen_no_oner()

        # Tablo 1: Öğrenciler
        ogrenciler = self.db.sorgula("SELECT * FROM v_yonetici_ogrenciler")
        self.tbl_ogrenciler.setUpdatesEnabled(False)
        self.tbl_ogrenciler.setRowCount(0)
        for o in ogrenciler:
            r = self.tbl_ogrenciler.rowCount()
            self.tbl_ogrenciler.insertRow(r)
            self.tbl_ogrenciler.setItem(r, 0, QTableWidgetItem(str(o["ogrenci_no"])))
            self.tbl_ogrenciler.setItem(r, 1, QTableWidgetItem(str(o["ad_soyad"])))
            self.tbl_ogrenciler.setItem(r, 2, QTableWidgetItem(str(o["eposta"])))
            self.tbl_ogrenciler.setItem(r, 3, QTableWidgetItem(str(o["program_ad"])))
            self.tbl_ogrenciler.setItem(r, 4, QTableWidgetItem(str(o["giris_yili"])))
            self.tbl_ogrenciler.setItem(r, 5, QTableWidgetItem(str(o["danisman_ad"])))
            self.tbl_ogrenciler.setItem(r, 6, QTableWidgetItem(f"{o['gno']} ({o['gecilen_akts']} AKTS)"))
            d_it = QTableWidgetItem(f"✔ {o['durum'].upper()}")
            d_it.setBackground(QBrush(QColor("#DCFCE7")))
            d_it.setForeground(QBrush(QColor("#15803D")))
            self.tbl_ogrenciler.setItem(r, 7, d_it)
        self.tbl_ogrenciler.setUpdatesEnabled(True)

        # Tablo 2: Akademisyenler
        akademisyenler = self.db.sorgula("SELECT * FROM v_yonetici_akademisyenler")
        self.tbl_akademisyenler.setUpdatesEnabled(False)
        self.tbl_akademisyenler.setRowCount(0)
        for a in akademisyenler:
            r = self.tbl_akademisyenler.rowCount()
            self.tbl_akademisyenler.insertRow(r)
            self.tbl_akademisyenler.setItem(r, 0, QTableWidgetItem(str(a["kullanici_no"])))
            self.tbl_akademisyenler.setItem(r, 1, QTableWidgetItem(str(a["unvan"])))
            self.tbl_akademisyenler.setItem(r, 2, QTableWidgetItem(str(a["ad_soyad"])))
            self.tbl_akademisyenler.setItem(r, 3, QTableWidgetItem(str(a["eposta"])))
            self.tbl_akademisyenler.setItem(r, 4, QTableWidgetItem(str(a["bolum_ad"])))
            self.tbl_akademisyenler.setItem(r, 5, QTableWidgetItem(f"{a['aktif_sube_sayisi']} Şube"))
            self.tbl_akademisyenler.setItem(r, 6, QTableWidgetItem(f"{a['danisan_sayisi']} Öğrenci"))
        self.tbl_akademisyenler.setUpdatesEnabled(True)

        # Tablo 3: Dersler
        dersler = self.db.sorgula("SELECT * FROM v_yonetici_dersler")
        self.tbl_dersler.setUpdatesEnabled(False)
        self.tbl_dersler.setRowCount(0)
        for d in dersler:
            r = self.tbl_dersler.rowCount()
            self.tbl_dersler.insertRow(r)
            self.tbl_dersler.setItem(r, 0, QTableWidgetItem(str(d["kod"])))
            self.tbl_dersler.setItem(r, 1, QTableWidgetItem(str(d["ad"])))
            self.tbl_dersler.setItem(r, 2, QTableWidgetItem(str(d["akts"])))
            self.tbl_dersler.setItem(r, 3, QTableWidgetItem(str(d["saat_bilgi"])))
            self.tbl_dersler.setItem(r, 4, QTableWidgetItem(f"{d['donem_no']}. Yarıyıl"))
            tur_it = QTableWidgetItem("Zorunlu" if d["tur"] == "zorunlu" else "Seçmeli")
            tur_it.setBackground(QBrush(QColor("#DBEAFE" if d["tur"] == "zorunlu" else "#FEF3C7")))
            tur_it.setForeground(QBrush(QColor("#1E3A8A" if d["tur"] == "zorunlu" else "#92400E")))
            self.tbl_dersler.setItem(r, 5, tur_it)
            self.tbl_dersler.setItem(r, 6, QTableWidgetItem(str(d["onkosullar"])))
            self.tbl_dersler.setItem(r, 7, QTableWidgetItem(f"{d['aktif_sube_sayisi']} Şube"))
        self.tbl_dersler.setUpdatesEnabled(True)

        # Tablo 4: Aktif Dönem Şubeleri
        subeler = self.db.sorgula(
            """SELECT s.sube_id, d.kod, d.ad, s.sube_no,
                      ou.unvan || ' ' || k.ad || ' ' || k.soyad AS hoca,
                      coalesce((
                        SELECT string_agg((ARRAY['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'])[ss.gun] || ' ' || ss.ders_saati || '.Saat', ', ' ORDER BY ss.gun, ss.ders_saati)
                          FROM sube_saat ss WHERE ss.sube_id = s.sube_id
                      ), '—') AS saatler
                 FROM sube s
                 JOIN ders d ON d.ders_id = s.ders_id
                 JOIN ogretim_uyesi ou ON ou.kisi_id = s.ogretim_uyesi_id
                 JOIN kisi k ON k.kisi_id = ou.kisi_id
                WHERE s.donem_id = fn_aktif_donem_id()
                ORDER BY d.kod, s.sube_no"""
        )
        self.tbl_subeler.setUpdatesEnabled(False)
        self.tbl_subeler.setRowCount(0)
        for s in subeler:
            r = self.tbl_subeler.rowCount()
            self.tbl_subeler.insertRow(r)
            self.tbl_subeler.setItem(r, 0, QTableWidgetItem(str(s["sube_id"])))
            self.tbl_subeler.setItem(r, 1, QTableWidgetItem(str(s["kod"])))
            self.tbl_subeler.setItem(r, 2, QTableWidgetItem(str(s["ad"])))
            self.tbl_subeler.setItem(r, 3, QTableWidgetItem(f"Şube {s['sube_no']}"))
            self.tbl_subeler.setItem(r, 4, QTableWidgetItem(str(s["hoca"])))
            self.tbl_subeler.setItem(r, 5, QTableWidgetItem(str(s["saatler"])))
        self.tbl_subeler.setUpdatesEnabled(True)

        _kartlari_temizle(self.kart_lay)
        self.kart_lay.addWidget(bilgi_karti("Kayıtlı Öğrenci", f"{len(ogrenciler)} Öğrenci", "🎓", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Akademisyen Kadrosu", f"{len(akademisyenler)} Hoca", "👨‍🏫", "#15803D"))
        self.kart_lay.addWidget(bilgi_karti("Müfredat Dersleri", f"{len(dersler)} Ders", "📚", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Aktif Dönem Şubesi", f"{len(subeler)} Şube", "🗓️", "#92400E"))

    def ogrenci_ekle(self):
        ad = self.txt_ogr_ad.text().strip()
        soyad = self.txt_ogr_soyad.text().strip()
        eposta = self.txt_ogr_eposta.text().strip()
        ogr_no = self.txt_ogr_no.text().strip()
        prog_id = self.cmb_ogr_prog.currentData()
        yil = self.spn_ogr_yil.value()
        danisman_id = self.cmb_ogr_danisman.currentData()
        sifre = self.txt_ogr_sifre.text().strip() or "123456"

        try:
            sonuc = self.db.calistir(
                "SELECT * FROM fn_yonetici_ogrenci_ekle(%s, %s, %s, %s, %s::int, %s::smallint, %s::int, %s)",
                (ad, soyad, eposta, ogr_no, prog_id, yil, danisman_id, sifre)
            )[0]
            self.txt_ogr_ad.clear()
            self.txt_ogr_soyad.clear()
            self.yenile()
            QMessageBox.information(
                self, "Öğrenci Eklendi ✔",
                f"Yeni öğrenci başarıyla kaydedildi ve SHA-256 denetim loguna işlendi!\n\n"
                f"• Ad Soyad: {sonuc['ad_soyad']}\n"
                f"• Öğrenci Numarası: {sonuc['ogrenci_no']}\n"
                f"• Giriş Şifresi: {sifre}\n\n"
                f"Bu numara ve şifre ile giriş ekranından hemen oturum açabilirsiniz."
            )
        except Exception as e:
            hata_goster(self, "Öğrenci Ekleme Hatası", e)

    def ogretmen_ekle(self):
        unvan = self.cmb_hoca_unvan.currentData()
        ad = self.txt_hoca_ad.text().strip()
        soyad = self.txt_hoca_soyad.text().strip()
        eposta = self.txt_hoca_eposta.text().strip()
        k_no = self.txt_hoca_no.text().strip()
        bolum_id = self.cmb_hoca_bolum.currentData()
        ek_rol = self.cmb_hoca_ekrol.currentData()
        sifre = self.txt_hoca_sifre.text().strip() or "123456"

        try:
            sonuc = self.db.calistir(
                "SELECT * FROM fn_yonetici_ogretmen_ekle(%s, %s, %s, %s, %s::int, %s, %s, %s)",
                (ad, soyad, eposta, k_no, bolum_id, unvan, ek_rol, sifre)
            )[0]
            self.txt_hoca_ad.clear()
            self.txt_hoca_soyad.clear()
            self.yenile()
            QMessageBox.information(
                self, "Akademisyen Eklendi ✔",
                f"Yeni akademisyen başarıyla kaydedildi ve SHA-256 denetim loguna işlendi!\n\n"
                f"• Akademisyen: {sonuc['ad_soyad']}\n"
                f"• Personel Numarası: {sonuc['kullanici_no']}\n"
                f"• Giriş Şifresi: {sifre}"
            )
        except Exception as e:
            hata_goster(self, "Akademisyen Ekleme Hatası", e)

    def ders_ekle(self):
        kod = self.txt_ders_kod.text().strip().upper()
        ad = self.txt_ders_ad.text().strip()
        akts = self.spn_ders_akts.value()
        teo = self.spn_ders_teo.value()
        uyg = self.spn_ders_uyg.value()
        donem_no = self.spn_ders_donem.value()
        tur = self.cmb_ders_tur.currentData()
        onk_id = self.cmb_ders_onkosul.currentData()
        min_harf = self.cmb_ders_minharf.currentData()
        sube_hoca = self.cmb_ders_sube_hoca.currentData()
        gun = self.cmb_ders_gun.currentData() if sube_hoca else None
        saat = self.spn_ders_saat.value() if sube_hoca else None

        try:
            sonuc = self.db.calistir(
                "SELECT * FROM fn_yonetici_ders_ekle(%s, %s, %s::smallint, %s::smallint, %s::smallint, "
                "%s::smallint, %s, %s::int, %s, %s::int, %s::smallint, %s::smallint)",
                (kod, ad, akts, teo, uyg, donem_no, tur, onk_id, min_harf, sube_hoca, gun, saat)
            )[0]
            self.txt_ders_kod.clear()
            self.txt_ders_ad.clear()
            self.yenile()
            sube_bilgi = f"Aktif Dönem Şube #{sonuc['acilan_sube_id']} açıldı." if sonuc.get("acilan_sube_id") else "Şube açılmadı."
            QMessageBox.information(
                self, "Ders Eklendi ✔",
                f"Yeni ders müfredata eklendi ve SHA-256 denetim loguna işlendi!\n\n"
                f"• Ders: {sonuc['kod']} — {ad} ({akts} AKTS)\n"
                f"• {sube_bilgi}"
            )
        except Exception as e:
            hata_goster(self, "Ders Ekleme Hatası", e)

    def sube_ac_islem(self):
        ders_id = self.cmb_sb_ders.currentData()
        hoca_id = self.cmb_sb_hoca.currentData()
        sube_no = self.spn_sb_no.value()
        gun = self.cmb_sb_gun.currentData()
        saat = self.spn_sb_saat.value()
        try:
            donem_id = (self.db.tek_satir("SELECT fn_aktif_donem_id() AS id") or {}).get("id")
            r = self.db.calistir(
                "SELECT fn_sube_ac(%s::int, %s::int, %s::smallint, %s::int) AS sube_id",
                (ders_id, donem_id, sube_no, hoca_id)
            )[0]
            sube_id = r["sube_id"]
            self.db.calistir("SELECT fn_sube_saat_ekle(%s::int, %s::smallint, %s::smallint)", (sube_id, gun, saat))
            if saat < 8:
                self.db.calistir("SELECT fn_sube_saat_ekle(%s::int, %s::smallint, %s::smallint)", (sube_id, gun, saat + 1))
            self.yenile()
            QMessageBox.information(self, "Şube Açıldı ✔", f"Şube #{sube_id} açıldı ve ders saatleri eklendi.")
        except Exception as e:
            hata_goster(self, "Şube Açma Hatası", e)


class YoneticiPaneli(QWidget):
    def __init__(self, db: Veritabani, sekme_gecis_cb=None):
        super().__init__()
        self.db = db
        self.sekme_gecis_cb = sekme_gecis_cb
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Sistem Yönetimi — Parametreler ve SHA-256 Denetim Logu Zinciri")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        if self.sekme_gecis_cb:
            btn_ekle_gec = QPushButton("➕  Öğrenci / Hoca / Ders Ekle (Ctrl+2)")
            btn_ekle_gec.setObjectName("BirincilBtn")
            btn_ekle_gec.clicked.connect(lambda: self.sekme_gecis_cb(1))
            ust.addWidget(btn_ekle_gec)

        btn_zincir = QPushButton("SHA-256 Log Zincirini Doğrula (fn_denetim_dogrula)")
        btn_zincir.setObjectName("BirincilBtn")
        btn_zincir.clicked.connect(self.zincir_dogrula)
        ust.addWidget(btn_zincir)

        btn_yenile = QPushButton("↻  Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w_p = QFrame()
        w_p.setObjectName("PortalKart")
        l_p = QVBoxLayout(w_p)
        l_p.setContentsMargins(14, 10, 14, 10)
        l_p.addWidget(QLabel("<b>Sistem Parametreleri (v_parametreler)</b>"))
        self.tbl_param = QTableWidget(0, 4)
        self.tbl_param.setHorizontalHeaderLabels(["Anahtar", "Değer", "Açıklama", "İşlem"])
        self.tbl_param.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_param.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_param.setEditTriggers(QTableWidget.NoEditTriggers)
        l_p.addWidget(self.tbl_param)
        splitter.addWidget(w_p)

        w_log = QFrame()
        w_log.setObjectName("PortalKart")
        l_log = QVBoxLayout(w_log)
        l_log.setContentsMargins(14, 10, 14, 10)
        l_log.addWidget(QLabel("<b>Değiştirilemez Denetim Logu (v_denetim_log — Yalnızca Yönetici Görebilir)</b>"))
        self.tbl_log = QTableWidget(0, 6)
        self.tbl_log.setHorizontalHeaderLabels(["Log #", "Zaman", "Kullanıcı", "Tablo / İşlem", "PK", "Yeni Değer / Gerekçe"])
        self.tbl_log.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_log.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_log.setEditTriggers(QTableWidget.NoEditTriggers)
        l_log.addWidget(self.tbl_log)
        splitter.addWidget(w_log)

        self.lay.addWidget(splitter, 1)
        self.yenile()

    def yenile(self):
        self.tbl_param.setUpdatesEnabled(False)
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
        self.tbl_param.setUpdatesEnabled(True)

        self.tbl_log.setUpdatesEnabled(False)
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
        self.tbl_log.setUpdatesEnabled(True)

        _kartlari_temizle(self.kart_lay)
        self.kart_lay.addWidget(bilgi_karti("Sistem Parametresi", f"{self.tbl_param.rowCount()} Anahtar", "⚙️", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Denetim Log Kaydı", f"{self.tbl_log.rowCount()} İşlem", "📜", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("SHA-256 Log Zinciri", "Aktif & Korumalı ✔", "🛡️", "#15803D"))

    def param_degistir(self, anahtar: str, mevcut: str):
        yeni, ok = QInputDialog.getText(self, "Parametre Güncelle", f"'{anahtar}' için yeni değer:", text=mevcut)
        if not ok:
            return
        try:
            self.db.calistir("SELECT fn_parametre_guncelle(%s, %s)", (anahtar, yeni))
            self.yenile()
        except Exception as e:
            hata_goster(self, "Hata", e)

    def zincir_dogrula(self):
        try:
            satirlar = self.db.sorgula("SELECT * FROM fn_denetim_dogrula()")
            bozuk = [r for r in satirlar if any(v is not None for v in r.values())]
            if not bozuk:
                QMessageBox.information(
                    self, "Zincir Sağlam ✔",
                    "Tüm denetim_log satırlarının SHA-256 özet zinciri doğrulandı.\nHiçbir kırılma veya müdahale tespit edilmedi."
                )
            else:
                QMessageBox.critical(self, "Zincir Kırık!", f"Bozulan log satırları: {bozuk}")
        except Exception as e:
            hata_goster(self, "Hata", e)
