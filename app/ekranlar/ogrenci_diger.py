from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QSpinBox, QLineEdit, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from app.db import Veritabani, hata_coz
from app.ekranlar.ogrenci_ana import bilgi_karti


class OgrenciKisiselVeTakvim(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 20)
        self.lay.setSpacing(14)
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

        baslik = QLabel("Kişisel Bilgiler, Akademik Danışman ve Dönem Takvimi")
        baslik.setObjectName("SayfaBaslik")
        self.lay.addWidget(baslik)

        profil = self.db.tek_satir(
            """SELECT o.ogrenci_no, o.giris_yili, k.ad || ' ' || k.soyad AS ad_soyad,
                      k.eposta, p.ad AS program_ad, b.ad AS bolum_ad
                 FROM ogrenci o
                 JOIN kisi k ON k.kisi_id = o.kisi_id
                 LEFT JOIN mufredat m ON m.mufredat_id = o.mufredat_id
                 LEFT JOIN program p ON p.program_id = m.program_id
                 LEFT JOIN bolum b ON b.bolum_id = p.bolum_id
                WHERE o.kisi_id = fn_oturum_kisi_id()"""
        ) or {}

        danisman = self.db.tek_satir(
            """SELECT ou.unvan || ' ' || k.ad || ' ' || k.soyad AS ad_soyad,
                      k.eposta, d.gecerlilik::text AS aralik
                 FROM danismanlik d
                 JOIN kisi k ON k.kisi_id = d.danisman_id
                 LEFT JOIN ogretim_uyesi ou ON ou.kisi_id = d.danisman_id
                WHERE d.ogrenci_id = fn_oturum_kisi_id()
                  AND d.gecerlilik @> current_date
                LIMIT 1"""
        ) or {}

        ust_lay = QHBoxLayout()
        ust_lay.setSpacing(16)

        k_kart = QFrame()
        k_kart.setObjectName("PortalKart")
        k_lay = QVBoxLayout(k_kart)
        k_lay.setContentsMargins(18, 16, 18, 16)
        lbl_kb = QLabel("👤  Öğrenci Kimlik ve Bölüm Bilgileri")
        lbl_kb.setStyleSheet("color: #093567; font-size: 14px; font-weight: 700;")
        k_lay.addWidget(lbl_kb)

        satirlar_k = [
            ("Ad Soyad", profil.get("ad_soyad") or self.db.ad_soyad),
            ("Öğrenci Numarası", str(profil.get("ogrenci_no") or "-")),
            ("Fakülte / Bölüm", str(profil.get("bolum_ad") or "Bilgisayar ve Bilişim Fakültesi")),
            ("Program", str(profil.get("program_ad") or "Bilgisayar Mühendisliği")),
            ("Giriş Yılı", str(profil.get("giris_yili") or "-")),
            ("Kurumsal E-Posta", str(profil.get("eposta") or "-")),
        ]
        g1 = QGridLayout()
        g1.setSpacing(0)
        for i, (k, v) in enumerate(satirlar_k):
            bg = "#f4f7fb" if i % 2 == 0 else "#ffffff"
            lk = QLabel(k)
            lk.setStyleSheet(f"background:{bg}; color:#3b6998; font-weight:600; padding:7px 10px; border:1px solid #e5e9f0;")
            lv = QLabel(v)
            lv.setStyleSheet(f"background:{bg}; color:#1e293b; font-weight:600; padding:7px 10px; border:1px solid #e5e9f0;")
            g1.addWidget(lk, i, 0)
            g1.addWidget(lv, i, 1)
        k_lay.addLayout(g1)
        ust_lay.addWidget(k_kart, 1)

        d_kart = QFrame()
        d_kart.setObjectName("PortalKart")
        d_lay = QVBoxLayout(d_kart)
        d_lay.setContentsMargins(18, 16, 18, 16)
        lbl_db = QLabel("💬  Akademik Danışman Bilgileri")
        lbl_db.setStyleSheet("color: #7e22ce; font-size: 14px; font-weight: 700;")
        d_lay.addWidget(lbl_db)

        satirlar_d = [
            ("Danışman Ad Soyad", danisman.get("ad_soyad") or "Atanmamış"),
            ("Danışman E-Posta", danisman.get("eposta") or "-"),
            ("Görev Geçerlilik Aralığı", danisman.get("aralik") or "-"),
            ("Onay Yetkisi", "Ders Seçimi Kesinleştirme & Ekle-Bırak Onayı"),
            ("Akademik Risk Takibi", "Kural Tabanlı Bayrak + YZ (OULAD) Risk İzleme"),
        ]
        g2 = QGridLayout()
        g2.setSpacing(0)
        for i, (k, v) in enumerate(satirlar_d):
            bg = "#faf5ff" if i % 2 == 0 else "#ffffff"
            lk = QLabel(k)
            lk.setStyleSheet(f"background:{bg}; color:#6b21a8; font-weight:600; padding:7px 10px; border:1px solid #e9d5ff;")
            lv = QLabel(v)
            lv.setStyleSheet(f"background:{bg}; color:#1e293b; font-weight:600; padding:7px 10px; border:1px solid #e9d5ff;")
            g2.addWidget(lk, i, 0)
            g2.addWidget(lv, i, 1)
        d_lay.addLayout(g2)
        ust_lay.addWidget(d_kart, 1)

        self.lay.addLayout(ust_lay)

        t_kart = QFrame()
        t_kart.setObjectName("PortalKart")
        t_lay = QVBoxLayout(t_kart)
        t_lay.setContentsMargins(18, 14, 18, 16)
        lbl_tb = QLabel("📅  Akademik Dönem ve Kayıt / Ekle-Bırak Takvimi")
        lbl_tb.setStyleSheet("color: #d97706; font-size: 14px; font-weight: 700;")
        t_lay.addWidget(lbl_tb)

        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Yıl", "Dönem", "Kayıt Başlangıç", "Kayıt Bitiş", "Ekle-Bırak Bitiş"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)

        for r in self.db.sorgula("SELECT yil, tur, kayit_baslangic, kayit_bitis, ekle_birak_bitis FROM donem ORDER BY yil DESC, donem_id DESC"):
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setItem(row, 0, QTableWidgetItem(str(r["yil"])))
            tbl.setItem(row, 1, QTableWidgetItem(str(r["tur"]).upper()))
            tbl.setItem(row, 2, QTableWidgetItem(str(r["kayit_baslangic"])[:16]))
            tbl.setItem(row, 3, QTableWidgetItem(str(r["kayit_bitis"])[:16]))
            tbl.setItem(row, 4, QTableWidgetItem(str(r["ekle_birak_bitis"])[:16]))
        t_lay.addWidget(tbl)
        self.lay.addWidget(t_kart, 1)


class OgrenciNotlarTranskript(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Not Bilgileri, Resmi Transkript ve SHA-256 Belge Doğrulama")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()
        btn_yenile = QPushButton("Yenile")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w_not = QFrame()
        w_not.setObjectName("PortalKart")
        l_not = QVBoxLayout(w_not)
        l_not.setContentsMargins(14, 12, 14, 12)
        l_not.addWidget(QLabel("<b>📝  İlan Edilmiş Değerlendirme Bileşeni Notlarım (RLS Korumalı)</b>"))
        self.tbl_notlar = QTableWidget(0, 5)
        self.tbl_notlar.setHorizontalHeaderLabels(["Kayıt #", "Ders Kodu", "Bileşen", "Ağırlık (%)", "Puan"])
        self.tbl_notlar.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_notlar.setEditTriggers(QTableWidget.NoEditTriggers)
        l_not.addWidget(self.tbl_notlar)
        splitter.addWidget(w_not)

        w_tr = QFrame()
        w_tr.setObjectName("PortalKart")
        l_tr = QVBoxLayout(w_tr)
        l_tr.setContentsMargins(14, 12, 14, 12)
        l_tr.addWidget(QLabel("<b>📜  Resmi Transkript Dökümü</b>"))
        self.tbl_tr = QTableWidget(0, 7)
        self.tbl_tr.setHorizontalHeaderLabels(["Yıl", "Dönem", "Ders Kodu", "Ders Adı", "AKTS", "Harf Notu", "Durum"])
        self.tbl_tr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_tr.setEditTriggers(QTableWidget.NoEditTriggers)
        l_tr.addWidget(self.tbl_tr)
        splitter.addWidget(w_tr)

        self.lay.addWidget(splitter, 1)

        belge_kart = QFrame()
        belge_kart.setObjectName("PortalKart")
        b_lay = QHBoxLayout(belge_kart)
        b_lay.setContentsMargins(14, 10, 14, 10)

        btn_uret = QPushButton("🔐  Transkript Belgesi Üret (SHA-256)")
        btn_uret.setObjectName("BirincilBtn")
        btn_uret.clicked.connect(self.belge_uret)
        b_lay.addWidget(btn_uret)

        self.lbl_kod = QLabel("Doğrulama Kodu: -")
        self.lbl_kod.setStyleSheet("font-weight: 700; color: #093567;")
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
        btn_html = QPushButton("📄  PDF Olarak İndir")
        btn_html.setObjectName("IkincilBtn")
        btn_html.clicked.connect(self.transkript_indir)
        b_lay.addWidget(btn_html)

        self.lay.addWidget(belge_kart)
        self.yenile()

    def yenile(self):
        while self.kart_lay.count():
            item = self.kart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ozet = self.db.tek_satir("SELECT * FROM v_ana_sayfa") or {}
        notlar = self.db.sorgula("SELECT * FROM v_not_detay ORDER BY kayit_id DESC, bilesen")
        tr = self.db.sorgula("SELECT * FROM v_transkript ORDER BY yil, donem, kod")

        self.kart_lay.addWidget(bilgi_karti("Genel Not Ortalaması", str(ozet.get("gno") or "-"), "A+", "#1d70db"))
        self.kart_lay.addWidget(bilgi_karti("Dönem Not Ortalaması", str(ozet.get("dno") or "-"), "📊", "#0d9488"))
        self.kart_lay.addWidget(bilgi_karti("Geçilen Toplam AKTS", f"{ozet.get('gecilen_akts', 0)} AKTS", "±÷", "#16a34a"))
        self.kart_lay.addWidget(bilgi_karti("Transkript Ders Sayısı", f"{len(tr)} Ders", "📚", "#7e22ce"))

        self.tbl_notlar.setRowCount(0)
        for r in notlar:
            row = self.tbl_notlar.rowCount()
            self.tbl_notlar.insertRow(row)
            self.tbl_notlar.setItem(row, 0, QTableWidgetItem(str(r["kayit_id"])))
            self.tbl_notlar.setItem(row, 1, QTableWidgetItem(str(r["ders_kod"])))
            self.tbl_notlar.setItem(row, 2, QTableWidgetItem(str(r["bilesen"])))
            self.tbl_notlar.setItem(row, 3, QTableWidgetItem(str(r["agirlik"])))
            self.tbl_notlar.setItem(row, 4, QTableWidgetItem(str(r["puan"])))

        self.tbl_tr.setRowCount(0)
        for r in tr:
            row = self.tbl_tr.rowCount()
            self.tbl_tr.insertRow(row)
            self.tbl_tr.setItem(row, 0, QTableWidgetItem(str(r["yil"])))
            self.tbl_tr.setItem(row, 1, QTableWidgetItem(str(r["donem"]).upper()))
            self.tbl_tr.setItem(row, 2, QTableWidgetItem(str(r["kod"])))
            self.tbl_tr.setItem(row, 3, QTableWidgetItem(str(r["ders_adi"])))
            self.tbl_tr.setItem(row, 4, QTableWidgetItem(str(r["akts"])))

            harf_item = QTableWidgetItem(str(r["harf"]))
            durum_item = QTableWidgetItem(str(r["durum"]))
            if r["durum"] == "gecti":
                harf_item.setBackground(QBrush(QColor("#dcfce7")))
                harf_item.setForeground(QBrush(QColor("#166534")))
                durum_item.setBackground(QBrush(QColor("#dcfce7")))
            elif r["durum"] == "kaldi":
                harf_item.setBackground(QBrush(QColor("#fee2e2")))
                harf_item.setForeground(QBrush(QColor("#991b1b")))
                durum_item.setBackground(QBrush(QColor("#fee2e2")))
            self.tbl_tr.setItem(row, 5, harf_item)
            self.tbl_tr.setItem(row, 6, durum_item)

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



    def transkript_indir(self):
        import os, subprocess
        from datetime import datetime
        from collections import OrderedDict
        from PySide6.QtGui import QTextDocument, QPdfWriter, QPageSize
        from PySide6.QtCore import QMarginsF, QSizeF

        kod = self.txt_dogrula.text().strip()
        if not kod:
            try:
                sonuc = self.db.calistir("SELECT fn_belge_uret('transkript') AS kod")
                kod = sonuc[0]["kod"]
                self.lbl_kod.setText(f"Doğrulama Kodu: {kod}")
                self.txt_dogrula.setText(kod)
            except Exception:
                kod = "Üretilmedi"

        profil = self.db.tek_satir(
            """SELECT o.ogrenci_no, o.giris_yili, k.ad || ' ' || k.soyad AS ad_soyad,
                      k.eposta, p.ad AS program_ad, b.ad AS bolum_ad
                 FROM ogrenci o
                 JOIN kisi k ON k.kisi_id = o.kisi_id
                 LEFT JOIN mufredat m ON m.mufredat_id = o.mufredat_id
                 LEFT JOIN program p ON p.program_id = m.program_id
                 LEFT JOIN bolum b ON b.bolum_id = p.bolum_id
                WHERE o.kisi_id = fn_oturum_kisi_id()"""
        ) or {}

        kayitlar = self.db.sorgula("SELECT * FROM v_transkript ORDER BY yil, CASE donem WHEN 'guz' THEN 1 WHEN 'bahar' THEN 2 ELSE 3 END, kod")

        katsayi_map = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0}
        donem_ad = {"guz": "Güz", "bahar": "Bahar", "yaz": "Yaz"}
        giris_yili = int(profil.get("giris_yili") or (kayitlar[0]["yil"] if kayitlar else 2025))

        donemler = OrderedDict()
        for r in kayitlar:
            k = (int(r["yil"]), str(r["donem"]).lower())
            donemler.setdefault(k, []).append(r)

        aktif_dersler = self.db.sorgula(
            """SELECT dm.yil, dm.tur AS donem, d.kod, d.ad AS ders_adi, d.akts
                 FROM kayit k
                 JOIN donem dm ON dm.donem_id = k.donem_id
                 JOIN ders d ON d.ders_id = k.ders_id
                WHERE k.ogrenci_id = fn_oturum_kisi_id()
                  AND k.durum IN ('onayli', 'onay_bekliyor')
                ORDER BY d.kod"""
        )
        for ad in aktif_dersler:
            k = (int(ad["yil"]), str(ad["donem"]).lower())
            mevcut_kodlar = {x["kod"] for x in donemler.get(k, [])}
            if ad["kod"] not in mevcut_kodlar:
                donemler.setdefault(k, []).append({
                    "yil": ad["yil"], "donem": ad["donem"], "kod": ad["kod"],
                    "ders_adi": ad["ders_adi"], "akts": ad["akts"], "harf": None
                })

        kutular_html = []
        g_kredi = 0
        g_akts = 0
        g_puan = 0.0

        for (yil, d_tur), ders_listesi in donemler.items():
            sinif_no = max(1, yil - giris_yili + 1)
            baslik = f"{sinif_no}. Yıl {donem_ad.get(d_tur, d_tur.title())}"

            d_kredi = 0
            d_akts = 0
            d_puan = 0.0
            satir_html = ""

            for d in ders_listesi:
                akts = int(d["akts"] or 0)
                kredi = max(1, round(akts * 0.65))
                harf = d.get("harf")
                if harf in katsayi_map:
                    kat = katsayi_map[harf]
                    puan = round(akts * kat, 1)
                    d_kredi += kredi
                    d_akts += akts
                    d_puan += puan
                    not_str = f"{kat:.2f}".replace(".", ",")
                    puan_str = f"{int(puan) if puan.is_integer() else puan}".replace(".", ",")
                    harf_str = harf
                else:
                    not_str = "--"
                    puan_str = "--"
                    harf_str = ""

                satir_html += f"""
                <tr>
                    <td width="50" style="padding: 3px 2px; font-size: 8pt;">{d['kod']}</td>
                    <td width="132" style="padding: 3px 2px; font-size: 8pt;">{str(d['ders_adi']).upper()}</td>
                    <td width="32" align="center" style="padding: 3px 2px; font-size: 8pt;">{kredi}</td>
                    <td width="32" align="center" style="padding: 3px 2px; font-size: 8pt;">{akts}</td>
                    <td width="34" align="right" style="padding: 3px 2px; font-size: 8pt;">{not_str}</td>
                    <td width="32" align="right" style="padding: 3px 2px; font-size: 8pt;">{puan_str}</td>
                    <td width="30" align="center" style="padding: 3px 2px; font-size: 8pt; font-weight: bold;">{harf_str}</td>
                </tr>"""

            ano = (d_puan / d_akts) if d_akts > 0 else 0.0
            g_kredi += d_kredi
            g_akts += d_akts
            g_puan += d_puan
            agno = (g_puan / g_akts) if g_akts > 0 else 0.0

            ano_s = f"{ano:.2f}".replace(".", ",")
            agno_s = f"{agno:.2f}".replace(".", ",")
            dp_s = f"{int(d_puan) if d_puan.is_integer() else round(d_puan,1)}"
            gp_s = f"{int(g_puan) if g_puan.is_integer() else round(g_puan,1)}"

            kutu = f"""
            <table width="332" cellspacing="0" cellpadding="0" style="margin-bottom: 14px;">
                <tr style="background-color: #f7e6c4;">
                    <td colspan="7" align="center" style="font-weight: bold; font-size: 9pt; border: 1px solid #222; border-bottom: none; padding: 3px;">{baslik}</td>
                </tr>
                <tr style="background-color: #f7e6c4; font-weight: bold; font-size: 7.5pt;">
                    <td width="50" style="border-left: 1px solid #222; border-bottom: 1px solid #222; padding: 2px 3px;">D.Kodu</td>
                    <td width="132" style="border-bottom: 1px solid #222; padding: 2px 2px;">Ders Adı</td>
                    <td width="28" align="center" style="border-bottom: 1px solid #222; padding: 2px 1px;">Kredi</td>
                    <td width="28" align="center" style="border-bottom: 1px solid #222; padding: 2px 1px;">AKTS</td>
                    <td width="30" align="right" style="border-bottom: 1px solid #222; padding: 2px 2px;">Not</td>
                    <td width="30" align="right" style="border-bottom: 1px solid #222; padding: 2px 2px;">Puan</td>
                    <td width="28" align="center" style="border-right: 1px solid #222; border-bottom: 1px solid #222; padding: 2px 2px;">Harf</td>
                </tr>
                {satir_html}
                <tr>
                    <td colspan="7" style="border: 1px solid #222; padding: 4px 5px; font-size: 6.8pt; background-color: #ffffff;">
                        ANO : {ano_s} &nbsp; D.Kredi : {d_kredi} &nbsp; D.AKTS : {d_akts} &nbsp; D.Puan : {dp_s} &nbsp;
                        <b>AGNO : {agno_s}</b> &nbsp; G.Kredi : {g_kredi} &nbsp; G.AKTS : {g_akts} &nbsp; G.Puan : {gp_s}
                    </td>
                </tr>
            </table>"""
            kutular_html.append(kutu)

        grid_satirlar = ""
        for i in range(0, len(kutular_html), 2):
            sol = kutular_html[i]
            sag = kutular_html[i + 1] if i + 1 < len(kutular_html) else ""
            grid_satirlar += f"""
            <tr>
                <td width="334" valign="top">{sol}</td>
                <td width="12"></td>
                <td width="334" valign="top">{sag}</td>
            </tr>"""

        tarih_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
            body {{ font-family: Arial, Helvetica, sans-serif; color: #111111; margin: 0; padding: 0; }}
        </style></head><body>
        <table width="680" cellspacing="0" cellpadding="0" style="border-bottom: 2px solid #093567; padding-bottom: 8px; margin-bottom: 10px;">
            <tr>
                <td width="460" valign="middle">
                    <div style="font-size: 12pt; font-weight: bold; color: #093567;">T.C. YÜKSEKÖĞRETİM KURULU — ÖĞRENCİ BİLGİ SİSTEMİ</div>
                    <div style="font-size: 9.5pt; font-weight: bold; color: #334155; margin-top: 2px;">RESMİ NOT DÖKÜM BELGESİ (TRANSKRİPT)</div>
                </td>
                <td width="220" align="right" valign="middle" style="font-size: 8pt; color: #1e293b;">
                    <b>Belge Tarihi:</b> {tarih_str}<br>
                    <b>SHA-256 Doğrulama Kodu:</b> <span style="color:#093567; font-weight:bold;">{kod}</span>
                </td>
            </tr>
        </table>

        <table width="680" cellspacing="0" cellpadding="4" style="border: 1px solid #cbd5e1; background-color: #f8fafc; margin-bottom: 14px; font-size: 8.5pt;">
            <tr>
                <td width="110" style="color:#475569;"><b>Öğrenci No:</b></td>
                <td width="270"><b>{profil.get('ogrenci_no') or '-'}</b></td>
                <td width="110" style="color:#475569;"><b>Fakülte / Bölüm:</b></td>
                <td width="306">{profil.get('bolum_ad') or 'Mühendislik Fakültesi'}</td>
            </tr>
            <tr>
                <td style="color:#475569;"><b>Adı Soyadı:</b></td>
                <td><b>{profil.get('ad_soyad') or self.db.ad_soyad}</b></td>
                <td style="color:#475569;"><b>Program / Seviye:</b></td>
                <td>{profil.get('program_ad') or 'Bilgisayar Mühendisliği'} </td>
            </tr>
            <tr>
                <td style="color:#475569;"><b>Kayıt Yılı:</b></td>
                <td>{giris_yili}</td>
                <td style="color:#475569;"><b>Genel AGNO / AKTS:</b></td>
                <td><b>{f"{(g_puan/g_akts if g_akts else 0):.2f}".replace(".", ",")}</b> / {g_akts} AKTS</td>
            </tr>
        </table>

        <table width="680" cellspacing="0" cellpadding="0">
            {grid_satirlar}
        </table>

        <table width="680" cellspacing="0" cellpadding="6" style="margin-top: 18px; border-top: 1px solid #cbd5e1; font-size: 7.5pt; color: #475569;">
            <tr>
                <td>
                    <b>Kriptografik Bütünlük Onayı:</b> Bu belge veritabanındaki <i>fn_belge_uret('transkript')</i> fonksiyonu ile SHA-256 özet zinciri kullanılarak üretilmiştir.
                    OBS Belge Doğrulama ekranından <b>{kod}</b> kodu ile doğrulanabilir.
                </td>
            </tr>
        </table>
        </body></html>"""

        dosya = os.path.abspath("transkript_belgesi.pdf")
        pdf = QPdfWriter(dosya)
        pdf.setPageSize(QPageSize(QPageSize.A4))
        pdf.setResolution(96)
        pdf.setPageMargins(QMarginsF(8, 8, 8, 8))
        doc = QTextDocument()
        doc.setPageSize(QSizeF(720, 1020))
        doc.setHtml(html)
        doc.print_(pdf)
        subprocess.run(["open", dosya])

class OgrenciMezuniyetSimulasyon(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 16)
        self.lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("Mezuniyetime Ne Kaldı? — Müfredat Denetimi & DAG Simülasyonu")
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

        ust.addWidget(QLabel("<b>Dönem AKTS Limiti:</b>"))
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
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        splitter = QSplitter(Qt.Vertical)

        w1 = QFrame()
        w1.setObjectName("PortalKart")
        l1 = QVBoxLayout(w1)
        l1.setContentsMargins(14, 12, 14, 12)
        l1.addWidget(QLabel("<b>🎓  Müfredat ve Seçmeli Grup Denetimi (fn_mezuniyet_denetim_ben)</b>"))
        self.tbl_denetim = QTableWidget(0, 7)
        self.tbl_denetim.setHorizontalHeaderLabels(
            ["Grup Adı", "Tür", "Min Ders", "Min AKTS", "Sayılan Ders", "Sayılan AKTS", "Durum / Eksik"]
        )
        self.tbl_denetim.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_denetim.setEditTriggers(QTableWidget.NoEditTriggers)
        l1.addWidget(self.tbl_denetim)
        splitter.addWidget(w1)

        w2 = QFrame()
        w2.setObjectName("PortalKart")
        l2 = QVBoxLayout(w2)
        l2.setContentsMargins(14, 12, 14, 12)
        l2.addWidget(QLabel("<b>🗓️  Önkoşul DAG Topolojik Ders Planı (fn_ders_plani_ben)</b>"))
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

        uygun_mu = bool(ozet.get("mezuniyet_uygun"))
        uygun_str = "Mezuniyete Uygun ✓" if uygun_mu else "Eksikler Var"
        self.kart_lay.addWidget(bilgi_karti("Mezuniyet Durumu", uygun_str, "🎓", "#16a34a" if uygun_mu else "#dc2626"))
        self.kart_lay.addWidget(bilgi_karti("AKTS (Geçilen / Hedef)", f"{ozet.get('gecilen_akts', 0)} / {ozet.get('gereken_akts', 30)}", "±÷", "#1d70db"))
        self.kart_lay.addWidget(bilgi_karti("GNO (Mevcut / Min)", f"{ozet.get('gno') or '-'} / {ozet.get('min_gno', 2.00)}", "A+", "#0d9488"))
        self.kart_lay.addWidget(bilgi_karti("DAG Kritik Yol", f"{erken.get('kritik_yol_donem', 0)} Dönem", "⛓️", "#d97706"))
        self.kart_lay.addWidget(bilgi_karti(f"{akts_lim} AKTS Limitli Süre", f"{erken.get('akts_limitli_donem', 0)} Dönem", "⏱️", "#7e22ce"))

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
