from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_coz


def bilgi_karti(baslik: str, deger: str) -> QFrame:
    kart = QFrame()
    kart.setObjectName("Kart")
    lay = QVBoxLayout(kart)
    lay.setContentsMargins(14, 10, 14, 10)
    lbl_b = QLabel(baslik.upper())
    lbl_b.setObjectName("KartBaslik")
    lbl_d = QLabel(deger)
    lbl_d.setObjectName("KartDeger")
    lay.addWidget(lbl_b)
    lay.addWidget(lbl_d)
    return kart


class OgrenciAnaSayfa(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 20, 20, 20)
        self.lay.setSpacing(16)
        self.yenile()

    def yenile(self):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        baslik = QLabel("Öğrenci Akademik Özeti")
        baslik.setObjectName("SayfaBaslik")
        self.lay.addWidget(baslik)

        ozet = self.db.tek_satir("SELECT * FROM v_ana_sayfa") or {}
        mez = self.db.tek_satir("SELECT * FROM fn_mezuniyet_ozet_ben()") or {}
        limit_row = self.db.tek_satir("SELECT fn_akts_limit(fn_oturum_kisi_id()) AS lim") or {}

        kart_lay = QHBoxLayout()
        kart_lay.setSpacing(12)
        kart_lay.addWidget(bilgi_karti("Aktif Dönem", str(ozet.get("aktif_donem") or "-")))
        kart_lay.addWidget(bilgi_karti("Sınıf", f"{ozet.get('sinif', '-')}. Sınıf"))
        kart_lay.addWidget(bilgi_karti("GNO / DNO", f"{ozet.get('gno') or '-'} / {ozet.get('dno') or '-'}"))
        kart_lay.addWidget(bilgi_karti("Geçilen AKTS", f"{ozet.get('gecilen_akts', 0)} / {mez.get('gereken_akts', 30)}"))
        kart_lay.addWidget(bilgi_karti("Dönem AKTS Limiti", f"{limit_row.get('lim', 30)} AKTS"))
        self.lay.addLayout(kart_lay)

        durum_kart = QFrame()
        durum_kart.setObjectName("Kart")
        d_lay = QVBoxLayout(durum_kart)
        kayit_acik = "Açık" if ozet.get("kayit_acik") else "Kapalı"
        mez_uygun = "Uygun ✓" if mez.get("mezuniyet_uygun") else f"Eksik Var ({mez.get('eksikler') or '-'})"
        d_lay.addWidget(QLabel(f"<b>Kayıt Penceresi:</b> {kayit_acik} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Mezuniyet Durumu:</b> {mez_uygun}"))
        self.lay.addWidget(durum_kart)

        lbl_k = QLabel("Bu Dönemki Kayıtlarım ve Transkript Özeti")
        lbl_k.setObjectName("SayfaBaslik")
        self.lay.addWidget(lbl_k)

        tablo = QTableWidget(0, 6)
        tablo.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı", "AKTS", "Şube", "Durum", "Danışman Gerekçesi"])
        tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tablo.setEditTriggers(QTableWidget.NoEditTriggers)

        for r in self.db.sorgula("SELECT * FROM v_kayitlarim ORDER BY kayit_id DESC"):
            row = tablo.rowCount()
            tablo.insertRow(row)
            tablo.setItem(row, 0, QTableWidgetItem(str(r["ders_kod"])))
            tablo.setItem(row, 1, QTableWidgetItem(str(r["ders_ad"])))
            tablo.setItem(row, 2, QTableWidgetItem(str(r["akts"])))
            tablo.setItem(row, 3, QTableWidgetItem(str(r["sube_no"])))
            tablo.setItem(row, 4, QTableWidgetItem(str(r["durum"])))
            tablo.setItem(row, 5, QTableWidgetItem(str(r.get("onay_gerekce") or "-")))
        self.lay.addWidget(tablo)


class OgrenciDersSecimi(QWidget):
    DURUM_RENK = {
        "alinabilir": ("#dcfce7", "#166534", "Alınabilir"),
        "sepette": ("#dbeafe", "#1e40af", "Sepette"),
        "kayitli": ("#e0e7ff", "#3730a3", "Kayıtlı"),
        "onkosul_eksik": ("#fee2e2", "#991b1b", "Önkoşul Eksik"),
        "cakisiyor": ("#fef3c7", "#92400e", "Saat Çakışıyor"),
        "gecildi": ("#f1f5f9", "#475569", "Geçildi"),
    }

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(10)

        ust = QHBoxLayout()
        baslik = QLabel("Ders Seçimi, Sepet ve Haftalık Program")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        self.lbl_akts = QLabel()
        self.lbl_akts.setStyleSheet("font-weight: 700; color: #1e3a8a; font-size: 13px;")
        ust.addWidget(self.lbl_akts)

        btn_kesin = QPushButton("Sepeti Kesinleştir (Danışman Onayına Gönder)")
        btn_kesin.setObjectName("BirincilBtn")
        btn_kesin.clicked.connect(self.hepsini_kesinlestir)
        ust.addWidget(btn_kesin)

        btn_yenile = QPushButton("Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        splitter = QSplitter(Qt.Vertical)

        # 1. Açık Şubeler Tablosu
        ust_w = QWidget()
        u_lay = QVBoxLayout(ust_w)
        u_lay.setContentsMargins(0, 0, 0, 0)
        u_lay.addWidget(QLabel("<b>Açık Şubeler (Müfredatınızdaki Dersler)</b>"))
        self.tbl_subeler = QTableWidget(0, 8)
        self.tbl_subeler.setHorizontalHeaderLabels(
            ["Kod", "Ders Adı", "AKTS", "Şube", "Öğretim Üyesi", "Saatler", "Durum / Neden", "İşlem"]
        )
        self.tbl_subeler.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_subeler.setEditTriggers(QTableWidget.NoEditTriggers)
        u_lay.addWidget(self.tbl_subeler)
        splitter.addWidget(ust_w)

        # 2. Alt Bölüm: Sepetim/Kayıtlarım + Haftalık Program Izgarası
        alt_w = QWidget()
        a_lay = QHBoxLayout(alt_w)
        a_lay.setContentsMargins(0, 0, 0, 0)

        sol_v = QVBoxLayout()
        sol_v.addWidget(QLabel("<b>Aktif Dönem Sepetim ve Kayıtlarım</b>"))
        self.tbl_kayit = QTableWidget(0, 6)
        self.tbl_kayit.setHorizontalHeaderLabels(["Kod", "Ders Adı", "AKTS", "Durum", "Gerekçe", "İşlem"])
        self.tbl_kayit.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_kayit.setEditTriggers(QTableWidget.NoEditTriggers)
        sol_v.addWidget(self.tbl_kayit)
        a_lay.addLayout(sol_v, 3)

        sag_v = QVBoxLayout()
        sag_v.addWidget(QLabel("<b>Haftalık Ders Programı (5 Gün × 8 Saat)</b>"))
        self.tbl_prog = QTableWidget(8, 5)
        self.tbl_prog.setHorizontalHeaderLabels(["Pzt", "Sal", "Çar", "Per", "Cum"])
        self.tbl_prog.setVerticalHeaderLabels([f"{s}. Saat" for s in range(1, 9)])
        self.tbl_prog.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_prog.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_prog.setEditTriggers(QTableWidget.NoEditTriggers)
        sag_v.addWidget(self.tbl_prog)
        a_lay.addLayout(sag_v, 2)

        splitter.addWidget(alt_w)
        self.lay.addWidget(splitter)
        self.yenile()

    def yenile(self):
        aktif_donem = (self.db.tek_satir("SELECT fn_aktif_donem_id() AS id") or {}).get("id")
        lim = (self.db.tek_satir("SELECT fn_akts_limit(fn_oturum_kisi_id()) AS lim") or {}).get("lim", 30)

        # Açık şubeler
        subeler = self.db.sorgula(
            "SELECT * FROM v_acik_subeler WHERE donem_id = %s ORDER BY ders_kod, sube_no", (aktif_donem,)
        )
        self.tbl_subeler.setRowCount(0)
        for s in subeler:
            r = self.tbl_subeler.rowCount()
            self.tbl_subeler.insertRow(r)
            self.tbl_subeler.setItem(r, 0, QTableWidgetItem(s["ders_kod"]))
            self.tbl_subeler.setItem(r, 1, QTableWidgetItem(s["ders_ad"]))
            self.tbl_subeler.setItem(r, 2, QTableWidgetItem(str(s["akts"])))
            self.tbl_subeler.setItem(r, 3, QTableWidgetItem(str(s["sube_no"])))
            self.tbl_subeler.setItem(r, 4, QTableWidgetItem(s["hoca"]))
            self.tbl_subeler.setItem(r, 5, QTableWidgetItem(s["saatler"]))

            bg, fg, etiket = self.DURUM_RENK.get(s["durum"], ("#ffffff", "#000000", s["durum"]))
            if s.get("neden"):
                etiket += f" ({s['neden']})"
            item_d = QTableWidgetItem(etiket)
            item_d.setBackground(QBrush(QColor(bg)))
            item_d.setForeground(QBrush(QColor(fg)))
            self.tbl_subeler.setItem(r, 6, item_d)

            btn = QPushButton("Sepete Ekle")
            btn.setObjectName("BirincilBtn")
            btn.setEnabled(s["durum"] == "alinabilir")
            sube_id = s["sube_id"]
            btn.clicked.connect(lambda _, sid=sube_id: self.sepete_ekle(sid))
            self.tbl_subeler.setCellWidget(r, 7, btn)

        # Kayıtlarım (aktif dönem)
        kayitlar = self.db.sorgula(
            "SELECT * FROM v_kayitlarim WHERE donem_id = %s ORDER BY kayit_id", (aktif_donem,)
        )
        self.tbl_kayit.setRowCount(0)
        secili_akts = 0
        for k in kayitlar:
            if k["durum"] in ("sepet", "onay_bekliyor", "onayli"):
                secili_akts += int(k["akts"])
            r = self.tbl_kayit.rowCount()
            self.tbl_kayit.insertRow(r)
            self.tbl_kayit.setItem(r, 0, QTableWidgetItem(k["ders_kod"]))
            self.tbl_kayit.setItem(r, 1, QTableWidgetItem(k["ders_ad"]))
            self.tbl_kayit.setItem(r, 2, QTableWidgetItem(str(k["akts"])))
            self.tbl_kayit.setItem(r, 3, QTableWidgetItem(k["durum"]))
            self.tbl_kayit.setItem(r, 4, QTableWidgetItem(str(k.get("onay_gerekce") or "-")))

            kid = k["kayit_id"]
            if k["durum"] == "sepet":
                btn_k = QPushButton("Sepetten Çıkar")
                btn_k.setObjectName("TehlikeBtn")
                btn_k.clicked.connect(lambda _, x=kid: self.sepetten_cikar(x))
                self.tbl_kayit.setCellWidget(r, 5, btn_k)
            elif k["durum"] in ("onay_bekliyor", "onayli"):
                btn_k = QPushButton("Dersi Bırak")
                btn_k.setObjectName("IkincilBtn")
                btn_k.clicked.connect(lambda _, x=kid: self.dersi_birak(x))
                self.tbl_kayit.setCellWidget(r, 5, btn_k)
            else:
                self.tbl_kayit.setItem(r, 5, QTableWidgetItem("-"))

        self.lbl_akts.setText(f"Seçilen / Aktif AKTS: {secili_akts} / {lim}")

        # Haftalık program ızgarası
        self.tbl_prog.clearContents()
        prog = self.db.sorgula("SELECT * FROM v_haftalik_program WHERE donem_id = %s", (aktif_donem,))
        for p in prog:
            gun = int(p["gun"]) - 1
            saat = int(p["ders_saati"]) - 1
            if 0 <= gun < 5 and 0 <= saat < 8:
                hucre = QTableWidgetItem(f"{p['ders_kod']} ({p['durum']})")
                renk = "#dbeafe" if p["durum"] == "sepet" else "#dcfce7"
                hucre.setBackground(QBrush(QColor(renk)))
                self.tbl_prog.setItem(saat, gun, hucre)

    def sepete_ekle(self, sube_id: int):
        try:
            self.db.calistir("SELECT fn_sepete_ekle(%s)", (sube_id,))
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "Kural Engeli", hata_coz(e))

    def sepetten_cikar(self, kayit_id: int):
        try:
            self.db.calistir("SELECT fn_sepetten_cikar(%s)", (kayit_id,))
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "İşlem Hatası", hata_coz(e))

    def dersi_birak(self, kayit_id: int):
        try:
            self.db.calistir("SELECT fn_birak(%s)", (kayit_id,))
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "İşlem Hatası", hata_coz(e))

    def hepsini_kesinlestir(self):
        try:
            sonuclar = self.db.calistir("SELECT * FROM fn_kesinlestir_hepsi()")
            if not sonuclar:
                QMessageBox.information(self, "Bilgi", "Sepetinizde kesinleştirilecek ders bulunmuyor.")
                return
            hatalar = [f"Kayıt #{s['kayit_id']}: {hata_coz(Exception(s['mesaj']))}" for s in sonuclar if s["sonuc"] == "hata"]
            tamam = sum(1 for s in sonuclar if s["sonuc"] == "tamam")
            self.yenile()
            if hatalar:
                QMessageBox.warning(self, "Kısmi Kesinleştirme", f"{tamam} ders kesinleştirildi.\n\nHatalar:\n" + "\n".join(hatalar))
            else:
                QMessageBox.information(self, "Başarılı", f"{tamam} ders danışman onayına gönderildi.")
        except Exception as e:
            QMessageBox.warning(self, "İşlem Hatası", hata_coz(e))
