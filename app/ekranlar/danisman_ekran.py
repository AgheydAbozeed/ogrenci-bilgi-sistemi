from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QInputDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_goster
from app.stil import OLCULER, aktif_palet
from app.ekranlar.ogrenci_ana import bilgi_karti


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


class DanismanRiskPaneli(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(10)

        ust = QHBoxLayout()
        baslik = QLabel("Danışanlarım ve YZ Destekli Akademik Risk Paneli")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_ml = QPushButton("🤖  YZ (ML) Risk Modelini & Bayrakları Güncelle")
        btn_ml.setObjectName("BirincilBtn")
        btn_ml.clicked.connect(self.ml_yeniden_hesapla)
        ust.addWidget(btn_ml)

        btn_yenile = QPushButton("↻  Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        self.lbl_ml_detay = QLabel("Öğrenci seçildiğinde ML özellik vektörü ve model bilgisi burada gösterilir.")
        self.lbl_ml_detay.setObjectName("PortalKart")
        self.lbl_ml_detay.setStyleSheet("padding: 8px 12px;")
        self.lay.addWidget(self.lbl_ml_detay)

        splitter = QSplitter(Qt.Vertical)

        w_ust = QFrame()
        w_ust.setObjectName("PortalKart")
        l_ust = QVBoxLayout(w_ust)
        l_ust.setContentsMargins(14, 10, 14, 10)
        l_ust.addWidget(QLabel("<b>👥  Aktif Danışan Listesi (Detay görmek için satıra tıklayın)</b>"))
        self.tbl_danisan = QTableWidget(0, 6)
        self.tbl_danisan.setHorizontalHeaderLabels(
            ["Öğrenci No", "Ad Soyad", "GNO", "Geçilen AKTS", "Kural Bayrakları", "YZ (ML) Risk Skoru"]
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

        k_bayrak = QFrame()
        k_bayrak.setObjectName("PortalKart")
        v_bayrak = QVBoxLayout(k_bayrak)
        v_bayrak.setContentsMargins(12, 10, 12, 10)
        v_bayrak.addWidget(QLabel("<b>🚩  Seçili Öğrencinin Akademik Risk Bayrakları</b>"))
        self.tbl_bayrak = QTableWidget(0, 3)
        self.tbl_bayrak.setHorizontalHeaderLabels(["Kural Kodu", "Açıklama", "Şiddet (1-3)"])
        self.tbl_bayrak.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_bayrak.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_bayrak.setEditTriggers(QTableWidget.NoEditTriggers)
        v_bayrak.addWidget(self.tbl_bayrak)
        l_alt.addWidget(k_bayrak, 1)

        k_mez = QFrame()
        k_mez.setObjectName("PortalKart")
        v_mez = QVBoxLayout(k_mez)
        v_mez.setContentsMargins(12, 10, 12, 10)
        v_mez.addWidget(QLabel("<b>🎓  Seçili Öğrencinin Mezuniyet Grup Denetimi</b>"))
        self.tbl_mez = QTableWidget(0, 4)
        self.tbl_mez.setHorizontalHeaderLabels(["Grup", "Tür", "AKTS (Sayılan/Min)", "Durum / Eksik"])
        self.tbl_mez.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_mez.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_mez.setEditTriggers(QTableWidget.NoEditTriggers)
        v_mez.addWidget(self.tbl_mez)
        l_alt.addWidget(k_mez, 1)

        splitter.addWidget(w_alt)
        self.lay.addWidget(splitter, 1)
        self.danisanlar = []
        self.yenile()

    def ml_yeniden_hesapla(self):
        try:
            from ml.risk_model import veritabanini_guncelle
            ozet = veritabanini_guncelle()
            self.yenile()
            m = ozet["metrikler"]
            QMessageBox.information(
                self, "YZ Risk Modeli Güncellendi ✔",
                f"Seçilen Model: {ozet['secilen_model']}\n"
                f"ROC-AUC: {m['roc_auc']}  |  F1: {m['f1']}  |  Brier: {m['brier']}\n\n"
                f"Üretilen Kural Bayrağı: {ozet['bayrak_sayisi']}\n"
                f"Skorlanan Öğrenci Sayısı: {ozet['tahmin_sayisi']}"
            )
        except Exception as e:
            hata_goster(self, "ML Hesaplama Hatası", e)

    def yenile(self):
        while self.kart_lay.count():
            item = self.kart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.danisanlar = self.db.sorgula("SELECT * FROM v_danisanlarim ORDER BY en_yuksek_siddet DESC, ogrenci_no")
        yuksek_risk = sum(1 for d in self.danisanlar if d["en_yuksek_siddet"] >= 3 or (d.get("risk_skoru") and float(d["risk_skoru"]) >= 0.65))
        toplam_bayrak = sum(int(d["bayrak_sayisi"] or 0) for d in self.danisanlar)

        self.kart_lay.addWidget(bilgi_karti("Toplam Danışan", f"{len(self.danisanlar)} Öğrenci", "👥", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Yüksek Riskli Öğrenci", f"{yuksek_risk} Öğrenci", "⚠️", "#B91C1C"))
        self.kart_lay.addWidget(bilgi_karti("Aktif Risk Bayrağı", f"{toplam_bayrak} Bayrak", "🚩", "#92400E"))

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
                b_item.setBackground(QBrush(QColor("#FEE2E2")))
                b_item.setForeground(QBrush(QColor("#B91C1C")))
            elif d["en_yuksek_siddet"] >= 1:
                b_item.setBackground(QBrush(QColor("#FEF3C7")))
                b_item.setForeground(QBrush(QColor("#92400E")))
            else:
                b_item.setBackground(QBrush(QColor("#DCFCE7")))
                b_item.setForeground(QBrush(QColor("#15803D")))
            self.tbl_danisan.setItem(r, 4, b_item)

            skor = d.get("risk_skoru")
            if skor is not None:
                s_val = float(skor)
                seviye = "✖ Yüksek Risk" if s_val >= 0.65 else ("⏳ Orta Risk" if s_val >= 0.35 else "✔ Düşük Risk")
                s_item = QTableWidgetItem(f"{s_val:.3f} ({seviye})")
                bg = "#FEE2E2" if s_val >= 0.65 else ("#FEF3C7" if s_val >= 0.35 else "#DCFCE7")
                fg = "#B91C1C" if s_val >= 0.65 else ("#92400E" if s_val >= 0.35 else "#15803D")
                s_item.setBackground(QBrush(QColor(bg)))
                s_item.setForeground(QBrush(QColor(fg)))
            else:
                s_item = QTableWidgetItem("Hesaplanmadı")
            self.tbl_danisan.setItem(r, 5, s_item)

        if self.danisanlar:
            self.tbl_danisan.selectRow(0)

    def ogrenci_secildi(self):
        secili = self.tbl_danisan.currentRow()
        if secili < 0 or secili >= len(self.danisanlar):
            return
        ogr_id = self.danisanlar[secili]["ogrenci_id"]
        ad_soyad = self.danisanlar[secili]["ad_soyad"]

        risk_detay = self.db.tek_satir(
            "SELECT * FROM v_danisan_risk WHERE ogrenci_id = %s ORDER BY hesap_zamani DESC LIMIT 1", (ogr_id,)
        )
        if risk_detay and risk_detay.get("ozellikler"):
            oz = risk_detay["ozellikler"]
            self.lbl_ml_detay.setText(
                f"<b>{ad_soyad} — YZ Model:</b> {risk_detay['model']} &nbsp;|&nbsp; "
                f"<b>Tahmin Skoru:</b> {risk_detay['skor']} &nbsp;|&nbsp; "
                f"<b>Özellik Vektörü:</b> GNO={oz.get('gno')}, Başarısız Ders={oz.get('basarisiz_ders_sayisi')}, "
                f"Devamsızlık={oz.get('devamsizlik_orani')}, AKTS Açığı={oz.get('akts_acigi_orani')}, "
                f"Darboğaz={oz.get('onkosul_darbogaz_sayisi')}"
            )
        else:
            self.lbl_ml_detay.setText(f"<b>{ad_soyad}:</b> Henüz YZ risk tahmini bulunmuyor.")

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
            durum_str = "✔ Tamam" if m["durum"] == "tamam" else f"✖ Eksik: {m.get('eksik') or ''}"
            self.tbl_mez.setItem(r, 3, QTableWidgetItem(durum_str))
