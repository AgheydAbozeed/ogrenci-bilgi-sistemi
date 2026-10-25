from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QInputDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_coz


class DanismanOnayKuyrugu(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Danışman Ders Kayıt Onay Kuyruğu")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()
        btn_yenile = QPushButton("Listeyi Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["Kayıt #", "Öğrenci No", "Ad Soyad", "Ders", "AKTS", "GNO", "Karar İşlemi"]
        )
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lay.addWidget(self.tbl, 1)
        self.yenile()

    def yenile(self):
        self.tbl.setRowCount(0)
        for r in self.db.sorgula("SELECT * FROM v_onay_kuyrugu ORDER BY olusturma"):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(r["kayit_id"])))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(r["ogrenci_no"])))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(r["ad_soyad"])))
            self.tbl.setItem(row, 3, QTableWidgetItem(f"{r['ders_kod']} - {r['ders_ad']}"))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(r["akts"])))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(r.get("gno") or "-")))

            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(4, 2, 4, 2)
            h.setSpacing(6)
            kid = r["kayit_id"]
            btn_onay = QPushButton("Onayla")
            btn_onay.setObjectName("BirincilBtn")
            btn_onay.clicked.connect(lambda _, x=kid: self.karar_ver(x, "onay"))
            btn_ret = QPushButton("Reddet")
            btn_ret.setObjectName("TehlikeBtn")
            btn_ret.clicked.connect(lambda _, x=kid: self.karar_ver(x, "ret"))
            h.addWidget(btn_onay)
            h.addWidget(btn_ret)
            self.tbl.setCellWidget(row, 6, w)

    def karar_ver(self, kayit_id: int, karar: str):
        gerekce = None
        if karar == "ret":
            metin, ok = QInputDialog.getText(self, "Ret Gerekçesi", "Lütfen ret gerekçesini girin (zorunlu):")
            if not ok:
                return
            gerekce = metin
        try:
            self.db.calistir("SELECT fn_danisman_karar_ben(%s, %s, %s)", (kayit_id, karar, gerekce))
            self.yenile()
        except Exception as e:
            QMessageBox.warning(self, "İşlem Engeli", hata_coz(e))


class DanismanRiskPaneli(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Danışanlarım ve Akademik Risk Erken Uyarı Paneli")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()
        btn_yenile = QPushButton("Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        splitter = QSplitter(Qt.Vertical)

        w_ust = QWidget()
        l_ust = QVBoxLayout(w_ust)
        l_ust.setContentsMargins(0, 0, 0, 0)
        l_ust.addWidget(QLabel("<b>Aktif Danışan Listesi (Detay görmek için satıra tıklayın)</b>"))
        self.tbl_danisan = QTableWidget(0, 6)
        self.tbl_danisan.setHorizontalHeaderLabels(
            ["Öğrenci No", "Ad Soyad", "GNO", "Geçilen AKTS", "Risk Bayrağı Sayısı", "ML Risk Skoru"]
        )
        self.tbl_danisan.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_danisan.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_danisan.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_danisan.itemSelectionChanged.connect(self.ogrenci_secildi)
        l_ust.addWidget(self.tbl_danisan)
        splitter.addWidget(w_ust)

        w_alt = QWidget()
        l_alt = QHBoxLayout(w_alt)
        l_alt.setContentsMargins(0, 0, 0, 0)

        v_bayrak = QVBoxLayout()
        v_bayrak.addWidget(QLabel("<b>Seçili Öğrencinin Akademik Risk Bayrakları (v_danisan_bayraklari)</b>"))
        self.tbl_bayrak = QTableWidget(0, 3)
        self.tbl_bayrak.setHorizontalHeaderLabels(["Kural Kodu", "Açıklama", "Şiddet (1-3)"])
        self.tbl_bayrak.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_bayrak.setEditTriggers(QTableWidget.NoEditTriggers)
        v_bayrak.addWidget(self.tbl_bayrak)
        l_alt.addLayout(v_bayrak, 1)

        v_mez = QVBoxLayout()
        v_mez.addWidget(QLabel("<b>Seçili Öğrencinin Mezuniyet Grup Denetimi</b>"))
        self.tbl_mez = QTableWidget(0, 4)
        self.tbl_mez.setHorizontalHeaderLabels(["Grup", "Tür", "AKTS (Sayılan/Min)", "Durum / Eksik"])
        self.tbl_mez.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_mez.setEditTriggers(QTableWidget.NoEditTriggers)
        v_mez.addWidget(self.tbl_mez)
        l_alt.addLayout(v_mez, 1)

        splitter.addWidget(w_alt)
        self.lay.addWidget(splitter, 1)
        self.danisanlar = []
        self.yenile()

    def yenile(self):
        self.danisanlar = self.db.sorgula("SELECT * FROM v_danisanlarim ORDER BY en_yuksek_siddet DESC, ogrenci_no")
        self.tbl_danisan.setRowCount(0)
        for d in self.danisanlar:
            r = self.tbl_danisan.rowCount()
            self.tbl_danisan.insertRow(r)
            self.tbl_danisan.setItem(r, 0, QTableWidgetItem(str(d["ogrenci_no"])))
            self.tbl_danisan.setItem(r, 1, QTableWidgetItem(str(d["ad_soyad"])))
            self.tbl_danisan.setItem(r, 2, QTableWidgetItem(str(d.get("gno") or "-")))
            self.tbl_danisan.setItem(r, 3, QTableWidgetItem(str(d["gecilen_akts"])))

            b_item = QTableWidgetItem(f"{d['bayrak_sayisi']} Bayrak (Max Şiddet: {d['en_yuksek_siddet']})")
            if d["en_yuksek_siddet"] >= 3:
                b_item.setBackground(QBrush(QColor("#fee2e2")))
            elif d["en_yuksek_siddet"] >= 1:
                b_item.setBackground(QBrush(QColor("#fef3c7")))
            else:
                b_item.setBackground(QBrush(QColor("#dcfce7")))
            self.tbl_danisan.setItem(r, 4, b_item)
            self.tbl_danisan.setItem(r, 5, QTableWidgetItem(str(d.get("risk_skoru") or "Hesaplanmadı")))

        if self.danisanlar:
            self.tbl_danisan.selectRow(0)

    def ogrenci_secildi(self):
        secili = self.tbl_danisan.currentRow()
        if secili < 0 or secili >= len(self.danisanlar):
            return
        ogr_id = self.danisanlar[secili]["ogrenci_id"]

        bayraklar = self.db.sorgula(
            "SELECT * FROM v_danisan_bayraklari WHERE ogrenci_id = %s ORDER BY siddet DESC", (ogr_id,)
        )
        self.tbl_bayrak.setRowCount(0)
        for b in bayraklar:
            r = self.tbl_bayrak.rowCount()
            self.tbl_bayrak.insertRow(r)
            self.tbl_bayrak.setItem(r, 0, QTableWidgetItem(str(b["kural_kod"])))
            self.tbl_bayrak.setItem(r, 1, QTableWidgetItem(str(b["aciklama"])))
            self.tbl_bayrak.setItem(r, 2, QTableWidgetItem(str(b["siddet"])))

        denetim = self.db.sorgula("SELECT * FROM fn_mezuniyet_denetim_danisan(%s)", (ogr_id,))
        self.tbl_mez.setRowCount(0)
        for m in denetim:
            r = self.tbl_mez.rowCount()
            self.tbl_mez.insertRow(r)
            self.tbl_mez.setItem(r, 0, QTableWidgetItem(str(m["grup_ad"])))
            self.tbl_mez.setItem(r, 1, QTableWidgetItem(str(m["tur"])))
            self.tbl_mez.setItem(r, 2, QTableWidgetItem(f"{m['sayilan_akts']} / {m['min_akts']}"))
            durum_str = "Tamam ✓" if m["durum"] == "tamam" else f"Eksik: {m.get('eksik') or ''}"
            self.tbl_mez.setItem(r, 3, QTableWidgetItem(durum_str))
