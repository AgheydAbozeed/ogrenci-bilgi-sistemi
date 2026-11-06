from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QInputDialog, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from app.db import Veritabani, hata_goster
from app.stil import OLCULER
from app.ekranlar.ogrenci_ana import bilgi_karti
from app.ai.risk_motor import RiskTahminSonucu, lojistik_risk_hesapla
from app.ai.risk_radar import RiskRadariKarti


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
        btn_yenile = QPushButton("↻  Listeyi Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        kutu = QFrame()
        kutu.setObjectName("PortalKart")
        k_lay = QVBoxLayout(kutu)
        k_lay.setContentsMargins(14, 12, 14, 12)
        k_lay.addWidget(QLabel("<b>☑️  Onay Bekleyen Ders Seçimleri (Ret durumunda gerekçe girilmesi zorunludur)</b>"))

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["Kayıt #", "Öğrenci No", "Ad Soyad", "Ders", "AKTS", "GNO", "Karar İşlemi"]
        )
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        k_lay.addWidget(self.tbl, 1)
        self.lay.addWidget(kutu, 1)
        self.yenile()

    def yenile(self):
        while self.kart_lay.count():
            item = self.kart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        kuyruk = self.db.sorgula("SELECT * FROM v_onay_kuyrugu ORDER BY olusturma")
        danisan_sayisi = int((self.db.tek_satir("SELECT count(*)::int AS c FROM v_danisanlarim") or {}).get("c", 0))
        toplam_akts = sum(int(r["akts"] or 0) for r in kuyruk)

        self.kart_lay.addWidget(bilgi_karti("Bekleyen Onay Talebi", f"{len(kuyruk)} Kayıt", "⏳", "#92400E"))
        self.kart_lay.addWidget(bilgi_karti("Onay Bekleyen AKTS", f"{toplam_akts} AKTS", "±÷", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Aktif Danışan Öğrenci", f"{danisan_sayisi} Öğrenci", "👥", "#15803D"))

        self.tbl.setUpdatesEnabled(False)
        self.tbl.setRowCount(0)
        for r in kuyruk:
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
            btn_onay = QPushButton("✔ Onayla")
            btn_onay.setObjectName("BirincilBtn")
            btn_onay.clicked.connect(lambda _, x=kid: self.karar_ver(x, "onay"))
            btn_ret = QPushButton("✖ Reddet")
            btn_ret.setObjectName("TehlikeBtn")
            btn_ret.clicked.connect(lambda _, x=kid: self.karar_ver(x, "ret"))
            h.addWidget(btn_onay)
            h.addWidget(btn_ret)
            self.tbl.setCellWidget(row, 6, w)
        self.tbl.setUpdatesEnabled(True)

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
            hata_goster(self, "İşlem Engeli", e)


class DanisanPaneli(QWidget):
    """Danışmanın aktif danışanları, AI dairesel risk radarı ve mezuniyet grup denetimi."""

    GNO_ESIK = 2.0

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.danisanlar: list[dict] = []
        self._risk_sonuclari: dict[int, RiskTahminSonucu] = {}
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(10)

        ust = QHBoxLayout()
        baslik = QLabel("Danışanlarım ve ✦ AI Akademik Risk Radarı")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()
        btn_yenile = QPushButton("↻  Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w_ust = QFrame()
        w_ust.setObjectName("PortalKart")
        l_ust = QVBoxLayout(w_ust)
        l_ust.setContentsMargins(14, 10, 14, 10)
        l_ust.addWidget(QLabel("<b>👥  Aktif Danışan Listesi (Risk radarı ve denetim için satıra tıklayın)</b>"))
        self.tbl_danisan = QTableWidget(0, 6)
        self.tbl_danisan.setHorizontalHeaderLabels(
            ["Öğrenci No", "Ad Soyad", "GNO", "Geçilen AKTS", "Katılım %", "✦ AI Risk Tahmini"]
        )
        self.tbl_danisan.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_danisan.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_danisan.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_danisan.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_danisan.itemSelectionChanged.connect(self.ogrenci_secildi)
        l_ust.addWidget(self.tbl_danisan)
        splitter.addWidget(w_ust)

        w_alt = QWidget()
        l_alt = QHBoxLayout(w_alt)
        l_alt.setContentsMargins(0, 0, 0, 0)
        l_alt.setSpacing(12)

        self.radar_karti = RiskRadariKarti(w_alt)
        l_alt.addWidget(self.radar_karti, 1)

        k_mez = QFrame()
        k_mez.setObjectName("PortalKart")
        v_mez = QVBoxLayout(k_mez)
        v_mez.setContentsMargins(12, 10, 12, 10)
        self.lbl_mez = QLabel("<b>🎓  Seçili Öğrencinin Mezuniyet Grup Denetimi</b>")
        v_mez.addWidget(self.lbl_mez)
        self.tbl_mez = QTableWidget(0, 4)
        self.tbl_mez.setHorizontalHeaderLabels(["Grup", "Tür", "AKTS (Sayılan/Min)", "Durum / Eksik"])
        self.tbl_mez.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_mez.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_mez.setEditTriggers(QTableWidget.NoEditTriggers)
        v_mez.addWidget(self.tbl_mez)
        l_alt.addWidget(k_mez, 1)

        splitter.addWidget(w_alt)
        self.lay.addWidget(splitter, 1)
        self.yenile()

    def _danisan_verisi_yukle(self) -> list[dict]:
        try:
            return self.db.sorgula("SELECT * FROM v_danisan_risk_ozellik ORDER BY ogrenci_no")
        except Exception:
            return self.db.sorgula("SELECT * FROM v_danisanlarim ORDER BY ogrenci_no")

    def yenile(self):
        while self.kart_lay.count():
            item = self.kart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.danisanlar = self._danisan_verisi_yukle()
        self._risk_sonuclari.clear()
        min_gno_esik = 2.00
        for d in self.danisanlar:
            oid = int(d["ogrenci_id"])
            min_gno_esik = float(d.get("min_gno") or 2.00)
            self._risk_sonuclari[oid] = lojistik_risk_hesapla(
                gno=float(d.get("gno") or 2.50),
                katilim_yuzde=float(d.get("katilim_yuzde") or 85.0),
                odev_ort_puan=float(d.get("odev_ort_puan") or 70.0),
                basarisiz_ders_sayisi=int(d.get("basarisiz_ders_sayisi") or 0),
                aktif_donem_akts=int(d.get("aktif_donem_akts") or 24),
                ogrenci_id=oid,
                min_gno=min_gno_esik,
                devamsizlik_siniri=float(d.get("devamsizlik_siniri") or 30.0),
            )

        gnolar = [float(d["gno"]) for d in self.danisanlar if d.get("gno") is not None]
        yuksek_risk = sum(1 for r in self._risk_sonuclari.values() if r.skor >= 0.65)
        ortalama = f"{sum(gnolar) / len(gnolar):.2f}" if gnolar else "-"

        self.kart_lay.addWidget(bilgi_karti("Toplam Danışan", f"{len(self.danisanlar)} Öğrenci", "👥", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("✦ Yüksek Riskli", f"{yuksek_risk} Öğrenci", "⚠️", "#B91C1C"))
        self.kart_lay.addWidget(bilgi_karti(f"Ort. GNO (Min {min_gno_esik:.2f})", ortalama, "±÷", "#15803D"))

        self.tbl_danisan.setRowCount(0)
        for d in self.danisanlar:
            r = self.tbl_danisan.rowCount()
            self.tbl_danisan.insertRow(r)
            oid = int(d["ogrenci_id"])
            sonuc = self._risk_sonuclari[oid]

            self.tbl_danisan.setItem(r, 0, QTableWidgetItem(str(d["ogrenci_no"])))
            self.tbl_danisan.setItem(r, 1, QTableWidgetItem(str(d["ad_soyad"])))
            self.tbl_danisan.setItem(r, 2, QTableWidgetItem(str(d.get("gno") or "-")))
            self.tbl_danisan.setItem(r, 3, QTableWidgetItem(str(d["gecilen_akts"])))
            katilim_str = f"%{float(d.get('katilim_yuzde') or 85.0):.0f}"
            self.tbl_danisan.setItem(r, 4, QTableWidgetItem(katilim_str))

            risk_item = QTableWidgetItem(f"✦ %{sonuc.yuzde} ({sonuc.seviye})")
            if sonuc.skor >= 0.65:
                risk_item.setBackground(QBrush(QColor("#FEE2E2")))
                risk_item.setForeground(QBrush(QColor("#B91C1C")))
            elif sonuc.skor >= 0.35:
                risk_item.setBackground(QBrush(QColor("#FEF3C7")))
                risk_item.setForeground(QBrush(QColor("#92400E")))
            else:
                risk_item.setBackground(QBrush(QColor("#DCFCE7")))
                risk_item.setForeground(QBrush(QColor("#15803D")))
            self.tbl_danisan.setItem(r, 5, risk_item)

        if self.danisanlar:
            self.tbl_danisan.selectRow(0)

    def ogrenci_secildi(self):
        secili = self.tbl_danisan.currentRow()
        if secili < 0 or secili >= len(self.danisanlar):
            return
        ogrenci = self.danisanlar[secili]
        oid = int(ogrenci["ogrenci_id"])
        sonuc = self._risk_sonuclari.get(oid)
        if sonuc:
            self.radar_karti.sonuc_goster(ogrenci["ad_soyad"], sonuc, ogrenci)

        self.lbl_mez.setText(f"<b>🎓  {ogrenci['ad_soyad']} — Mezuniyet Grup Denetimi</b>")
        denetim = self.db.sorgula("SELECT * FROM fn_mezuniyet_denetim_danisan(%s)", (oid,))
        self.tbl_mez.setRowCount(0)
        for m in denetim:
            r = self.tbl_mez.rowCount()
            self.tbl_mez.insertRow(r)
            self.tbl_mez.setItem(r, 0, QTableWidgetItem(str(m["grup_ad"])))
            self.tbl_mez.setItem(r, 1, QTableWidgetItem(str(m["tur"])))
            self.tbl_mez.setItem(r, 2, QTableWidgetItem(f"{m['sayilan_akts']} / {m['min_akts']}"))
            durum_str = "✔ Tamam" if m["durum"] == "tamam" else f"✖ Eksik: {m.get('eksik') or ''}"
            self.tbl_mez.setItem(r, 3, QTableWidgetItem(durum_str))
