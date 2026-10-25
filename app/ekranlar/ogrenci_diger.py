from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QSpinBox, QLineEdit, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_coz
from app.ekranlar.ogrenci_ana import bilgi_karti


class OgrenciNotlarTranskript(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Not Detayları, Resmi Transkript ve Belge Doğrulama")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()
        btn_yenile = QPushButton("Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        splitter = QSplitter(Qt.Vertical)

        # 1. İlan Edilmiş Sınav Notları (v_not_detay)
        w_not = QWidget()
        l_not = QVBoxLayout(w_not)
        l_not.setContentsMargins(0, 0, 0, 0)
        l_not.addWidget(QLabel("<b>İlan Edilmiş Değerlendirme Bileşeni Notlarım (RLS Korumalı)</b>"))
        self.tbl_notlar = QTableWidget(0, 5)
        self.tbl_notlar.setHorizontalHeaderLabels(["Kayıt #", "Ders Kodu", "Bileşen", "Ağırlık (%)", "Puan"])
        self.tbl_notlar.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_notlar.setEditTriggers(QTableWidget.NoEditTriggers)
        l_not.addWidget(self.tbl_notlar)
        splitter.addWidget(w_not)

        # 2. Transkript (v_transkript)
        w_tr = QWidget()
        l_tr = QVBoxLayout(w_tr)
        l_tr.setContentsMargins(0, 0, 0, 0)
        l_tr.addWidget(QLabel("<b>Resmi Transkript Dökümü</b>"))
        self.tbl_tr = QTableWidget(0, 7)
        self.tbl_tr.setHorizontalHeaderLabels(["Yıl", "Dönem", "Ders Kodu", "Ders Adı", "AKTS", "Harf Notu", "Durum"])
        self.tbl_tr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_tr.setEditTriggers(QTableWidget.NoEditTriggers)
        l_tr.addWidget(self.tbl_tr)
        splitter.addWidget(w_tr)

        self.lay.addWidget(splitter, 1)

        # 3. SHA-256 Belge Üretimi ve Doğrulama Kartı
        belge_kart = QFrame()
        belge_kart.setObjectName("Kart")
        b_lay = QHBoxLayout(belge_kart)
        b_lay.setContentsMargins(14, 10, 14, 10)

        btn_uret = QPushButton("Transkript Belgesi Üret (SHA-256)")
        btn_uret.setObjectName("BirincilBtn")
        btn_uret.clicked.connect(self.belge_uret)
        b_lay.addWidget(btn_uret)

        self.lbl_kod = QLabel("Doğrulama Kodu: -")
        self.lbl_kod.setStyleSheet("font-weight: 700; color: #0f172a;")
        b_lay.addWidget(self.lbl_kod)
        b_lay.addStretch()

        b_lay.addWidget(QLabel("Kod Sorgula:"))
        self.txt_dogrula = QLineEdit()
        self.txt_dogrula.setPlaceholderText("12 haneli doğrulama kodu...")
        self.txt_dogrula.setFixedWidth(180)
        b_lay.addWidget(self.txt_dogrula)

        btn_dogrula = QPushButton("Belgeyi Doğrula")
        btn_dogrula.setObjectName("IkincilBtn")
        btn_dogrula.clicked.connect(self.belge_dogrula)
        b_lay.addWidget(btn_dogrula)

        self.lay.addWidget(belge_kart)
        self.yenile()

    def yenile(self):
        self.tbl_notlar.setRowCount(0)
        for r in self.db.sorgula("SELECT * FROM v_not_detay ORDER BY kayit_id DESC, bilesen"):
            row = self.tbl_notlar.rowCount()
            self.tbl_notlar.insertRow(row)
            self.tbl_notlar.setItem(row, 0, QTableWidgetItem(str(r["kayit_id"])))
            self.tbl_notlar.setItem(row, 1, QTableWidgetItem(str(r["ders_kod"])))
            self.tbl_notlar.setItem(row, 2, QTableWidgetItem(str(r["bilesen"])))
            self.tbl_notlar.setItem(row, 3, QTableWidgetItem(str(r["agirlik"])))
            self.tbl_notlar.setItem(row, 4, QTableWidgetItem(str(r["puan"])))

        self.tbl_tr.setRowCount(0)
        for r in self.db.sorgula("SELECT * FROM v_transkript ORDER BY yil, donem, kod"):
            row = self.tbl_tr.rowCount()
            self.tbl_tr.insertRow(row)
            self.tbl_tr.setItem(row, 0, QTableWidgetItem(str(r["yil"])))
            self.tbl_tr.setItem(row, 1, QTableWidgetItem(str(r["donem"])))
            self.tbl_tr.setItem(row, 2, QTableWidgetItem(str(r["kod"])))
            self.tbl_tr.setItem(row, 3, QTableWidgetItem(str(r["ders_adi"])))
            self.tbl_tr.setItem(row, 4, QTableWidgetItem(str(r["akts"])))
            self.tbl_tr.setItem(row, 5, QTableWidgetItem(str(r["harf"])))
            self.tbl_tr.setItem(row, 6, QTableWidgetItem(str(r["durum"])))

    def belge_uret(self):
        try:
            sonuc = self.db.calistir("SELECT fn_belge_uret('transkript') AS kod")
            kod = sonuc[0]["kod"]
            self.lbl_kod.setText(f"Doğrulama Kodu: {kod}")
            self.txt_dogrula.setText(kod)
            QMessageBox.information(self, "Belge Üretildi", f"SHA-256 imzalı belge üretildi.\nDoğrulama Kodu: {kod}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))

    def belge_dogrula(self):
        kod = self.txt_dogrula.text().strip()
        if not kod:
            return
        try:
            r = self.db.tek_satir("SELECT * FROM fn_belge_dogrula(%s)", (kod,))
            if not r or not r.get("ogrenci_no"):
                QMessageBox.warning(self, "Geçersiz Kod", "Bu doğrulama koduna ait belge bulunamadı.")
            elif r.get("gecerli"):
                QMessageBox.information(
                    self, "Belge Geçerli ✓",
                    f"Öğrenci No: {r['ogrenci_no']}\nBelge Türü: {r['tur']}\n"
                    f"Üretim Zamanı: {r['uretim_zamani']}\n\nSHA-256 İçerik Özeti güncel transkript ile EŞLEŞİYOR."
                )
            else:
                QMessageBox.critical(
                    self, "Bütünlük Bozulmuş ✗",
                    f"Öğrenci No: {r['ogrenci_no']}\nBelge üretildikten sonra transkript notları değişmiş!"
                )
        except Exception as e:
            QMessageBox.warning(self, "Hata", hata_coz(e))


class OgrenciMezuniyetSimulasyon(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Mezuniyet Denetimi ve DAG / Kritik Yol Simülasyonu")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        ust.addWidget(QLabel("<b>What-If Müfredat:</b>"))
        self.cmb_muf = QComboBox()
        self.cmb_muf.addItem("Kendi Müfredatım", None)
        for m in self.db.sorgula("SELECT * FROM v_mufredat_listesi ORDER BY giris_yili DESC"):
            self.cmb_muf.addItem(f"{m['program']} ({m['giris_yili']})", m["mufredat_id"])
        self.cmb_muf.currentIndexChanged.connect(self.yenile)
        ust.addWidget(self.cmb_muf)

        ust.addWidget(QLabel("<b>Dönem AKTS Limiti Simülasyonu:</b>"))
        self.spn_akts = QSpinBox()
        self.spn_akts.setRange(6, 45)
        self.spn_akts.setValue(30)
        self.spn_akts.setSuffix(" AKTS")
        self.spn_akts.valueChanged.connect(self.yenile)
        ust.addWidget(self.spn_akts)

        btn_yenile = QPushButton("Simülasyonu Çalıştır")
        btn_yenile.setObjectName("BirincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addWidget(QLabel("<b>Müfredat ve Seçmeli Grup Denetimi (fn_mezuniyet_denetim_ben)</b>"))
        self.tbl_denetim = QTableWidget(0, 7)
        self.tbl_denetim.setHorizontalHeaderLabels(
            ["Grup Adı", "Tür", "Min Ders", "Min AKTS", "Sayılan Ders", "Sayılan AKTS", "Durum / Eksik"]
        )
        self.tbl_denetim.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_denetim.setEditTriggers(QTableWidget.NoEditTriggers)
        l1.addWidget(self.tbl_denetim)
        splitter.addWidget(w1)

        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addWidget(QLabel("<b>Önkoşul DAG Topolojik Ders Planı (fn_ders_plani_ben)</b>"))
        self.tbl_plan = QTableWidget(0, 4)
        self.tbl_plan.setHorizontalHeaderLabels(["Önerilen Dönem Sırası", "Ders Kodu", "Ders Adı", "AKTS"])
        self.tbl_plan.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_plan.setEditTriggers(QTableWidget.NoEditTriggers)
        l2.addWidget(self.tbl_plan)
        splitter.addWidget(w2)

        self.lay.addWidget(splitter, 1)
        self.yenile()

    def yenile(self):
        while self.kart_lay.count():
            item = self.kart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        muf_id = self.cmb_muf.currentData()
        akts_lim = self.spn_akts.value()

        ozet = self.db.tek_satir("SELECT * FROM fn_mezuniyet_ozet_ben()") or {}
        erken = self.db.tek_satir("SELECT * FROM fn_en_erken_mezuniyet_ben(%s)", (akts_lim,)) or {}

        uygun_str = "Mezuniyete Uygun ✓" if ozet.get("mezuniyet_uygun") else "Eksikler Var"
        self.kart_lay.addWidget(bilgi_karti("Mezuniyet Durumu", uygun_str))
        self.kart_lay.addWidget(bilgi_karti("AKTS (Geçilen / Gereken)", f"{ozet.get('gecilen_akts', 0)} / {ozet.get('gereken_akts', 30)}"))
        self.kart_lay.addWidget(bilgi_karti("GNO (Mevcut / Min)", f"{ozet.get('gno') or '-'} / {ozet.get('min_gno', 2.00)}"))
        self.kart_lay.addWidget(bilgi_karti("DAG Kritik Yol", f"{erken.get('kritik_yol_donem', 0)} Dönem"))
        self.kart_lay.addWidget(bilgi_karti(f"{akts_lim} AKTS Limitli Süre", f"{erken.get('akts_limitli_donem', 0)} Dönem"))

        denetimler = self.db.sorgula("SELECT * FROM fn_mezuniyet_denetim_ben(%s)", (muf_id,))
        self.tbl_denetim.setRowCount(0)
        for d in denetimler:
            r = self.tbl_denetim.rowCount()
            self.tbl_denetim.insertRow(r)
            self.tbl_denetim.setItem(r, 0, QTableWidgetItem(str(d["grup_ad"])))
            self.tbl_denetim.setItem(r, 1, QTableWidgetItem(str(d["tur"])))
            self.tbl_denetim.setItem(r, 2, QTableWidgetItem(str(d["min_ders"])))
            self.tbl_denetim.setItem(r, 3, QTableWidgetItem(str(d["min_akts"])))
            self.tbl_denetim.setItem(r, 4, QTableWidgetItem(str(d["sayilan_ders"])))
            self.tbl_denetim.setItem(r, 5, QTableWidgetItem(str(d["sayilan_akts"])))
            durum_metin = "Tamam ✓" if d["durum"] == "tamam" else f"Eksik: {d.get('eksik') or ''}"
            item = QTableWidgetItem(durum_metin)
            item.setBackground(QBrush(QColor("#dcfce7" if d["durum"] == "tamam" else "#fee2e2")))
            self.tbl_denetim.setItem(r, 6, item)

        plan = self.db.sorgula("SELECT * FROM fn_ders_plani_ben(%s)", (akts_lim,))
        self.tbl_plan.setRowCount(0)
        for p in plan:
            r = self.tbl_plan.rowCount()
            self.tbl_plan.insertRow(r)
            self.tbl_plan.setItem(r, 0, QTableWidgetItem(f"{p['donem_sira']}. Dönem"))
            self.tbl_plan.setItem(r, 1, QTableWidgetItem(str(p["ders_kod"])))
            self.tbl_plan.setItem(r, 2, QTableWidgetItem(str(p["ders_ad"])))
            self.tbl_plan.setItem(r, 3, QTableWidgetItem(str(p["akts"])))
