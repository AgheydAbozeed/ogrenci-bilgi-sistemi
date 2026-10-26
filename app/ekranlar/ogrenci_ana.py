
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QCursor
from app.db import Veritabani, hata_coz


def ort_harf_rozeti(deger) -> str:
    try:
        v = float(deger)
    except (TypeError, ValueError):
        return "-"
    if v >= 3.50: return "A+"
    if v >= 3.00: return "A"
    if v >= 2.50: return "B"
    if v >= 2.00: return "C"
    if v >= 1.00: return "D"
    return "F"


from PySide6.QtGui import QPainter, QPen

def ort_harf_rozeti(deger) -> str:
    try:
        v = float(deger)
    except (TypeError, ValueError):
        return "-"
    if v >= 3.50: return "A+"
    if v >= 3.00: return "A"
    if v >= 2.50: return "B"
    if v >= 2.00: return "C"
    if v >= 1.00: return "D"
    return "F"

class DonemTimelineWidget(QWidget):
    def __init__(self, donemler):
        super().__init__()
        self.donemler = donemler[:6]
        self.setFixedHeight(78)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, n = self.width(), 6
        adim = w / n
        xs = [int(adim * i + adim / 2) for i in range(n)]
        y_cizgi = 20
        aktif_sayisi = len(self.donemler)

        # Arka plan kesintisiz gri cizgi (bastan sona)
        p.setPen(QPen(QColor("#e2e8f0"), 2))
        p.drawLine(24, y_cizgi, w - 24, y_cizgi)

        # Aktif donemler arasi kesintisiz yesil cizgi
        if aktif_sayisi > 0:
            son_x = xs[min(aktif_sayisi - 1, n - 1)]
            p.setPen(QPen(QColor("#4ade80"), 2))
            p.drawLine(24, y_cizgi, son_x, y_cizgi)

        tur_ad = {"guz": "Güz Dönemi", "bahar": "Bahar Dönemi", "yaz": "Yaz Dönemi"}
        font = self.font()

        for i, x in enumerate(xs):
            p.setPen(Qt.NoPen)
            if i < aktif_sayisi:
                # Ilk nokta biraz daha buyuk ve koyu yesil, diger aktifler canli yesil
                if i == 0:
                    p.setBrush(QColor("#22c55e"))
                    p.drawEllipse(x - 7, y_cizgi - 7, 14, 14)
                else:
                    p.setBrush(QColor("#4ade80"))
                    p.drawEllipse(x - 5, y_cizgi - 5, 10, 10)

                d = self.donemler[i]
                yil_str = f"{d['yil']}-{int(d['yil'])+1}"
                tur_str = tur_ad.get(d["tur"], str(d["tur"]))

                p.setPen(QColor("#475569"))
                font.setPointSize(10)
                font.setBold(False)
                p.setFont(font)
                p.drawText(int(x - adim/2), y_cizgi + 14, int(adim), 18, Qt.AlignCenter, yil_str)

                p.setPen(QColor("#334155"))
                font.setPointSize(10)
                p.setFont(font)
                p.drawText(int(x - adim/2), y_cizgi + 30, int(adim), 18, Qt.AlignCenter, tur_str)
            else:
                # Gelecek donemler icin sade gri noktalar (altinda yazi yok)
                p.setBrush(QColor("#e2e8f0"))
                p.drawEllipse(x - 5, y_cizgi - 5, 10, 10)


def bilgi_karti(baslik: str, deger: str, ikon: str = "A+", renk: str = "#1d70db") -> QFrame:
    kart = QFrame()
    kart.setObjectName("MetrikKutu")
    lay = QHBoxLayout(kart)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(14)

    lbl_ikon = QLabel(ikon)
    lbl_ikon.setFixedSize(44, 44)
    lbl_ikon.setAlignment(Qt.AlignCenter)
    lbl_ikon.setStyleSheet(
        f"color: {renk}; background-color: #f0f7ff; border: 1px solid #bfdbfe; "
        f"border-radius: 6px; font-size: 16px; font-weight: 800;"
    )
    lay.addWidget(lbl_ikon)

    v = QVBoxLayout()
    v.setSpacing(2)
    lbl_b = QLabel(baslik)
    lbl_b.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
    lbl_d = QLabel(deger)
    lbl_d.setStyleSheet("color: #0f172a; font-size: 18px; font-weight: 700;")
    v.addWidget(lbl_b)
    v.addWidget(lbl_d)
    lay.addLayout(v, 1)
    return kart


class TiklanabilirHizmetKarti(QFrame):
    def __init__(self, ikon: str, renk: str, baslik: str, aciklama: str, callback):
        super().__init__()
        self.setObjectName("HizmetKart")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.callback = callback

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)

        lbl_i = QLabel(ikon)
        lbl_i.setFixedSize(46, 46)
        lbl_i.setAlignment(Qt.AlignCenter)
        lbl_i.setStyleSheet(
            f"color: {renk}; font-size: 22px; font-weight: 800; "
            f"border: 2px solid {renk}; border-radius: 8px; background-color: #ffffff;"
        )
        lay.addWidget(lbl_i, 0, Qt.AlignTop)

        v = QVBoxLayout()
        v.setSpacing(4)
        lbl_b = QLabel(baslik)
        lbl_b.setStyleSheet(f"color: {renk}; font-size: 13px; font-weight: 700;")
        lbl_a = QLabel(aciklama)
        lbl_a.setWordWrap(True)
        lbl_a.setStyleSheet("color: #475569; font-size: 11px; line-height: 1.3;")
        v.addWidget(lbl_b)
        v.addWidget(lbl_a)
        lay.addLayout(v, 1)

    def mousePressEvent(self, event):
        if self.callback:
            self.callback()
        super().mousePressEvent(event)


class OgrenciAnaSayfa(QWidget):
    def __init__(self, db: Veritabani, sekme_gecis_cb=None):
        super().__init__()
        self.db = db
        self.sekme_gecis_cb = sekme_gecis_cb

        ana_lay = QVBoxLayout(self)
        ana_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.icerik_w = QWidget()
        self.lay = QVBoxLayout(self.icerik_w)
        self.lay.setContentsMargins(20, 18, 20, 22)
        self.lay.setSpacing(16)

        scroll.setWidget(self.icerik_w)
        ana_lay.addWidget(scroll)
        self.yenile()

    def _sekme_ac(self, idx: int):
        if self.sekme_gecis_cb:
            self.sekme_gecis_cb(idx)

    def yenile(self):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ozet = self.db.tek_satir("SELECT * FROM v_ana_sayfa") or {}
        mez = self.db.tek_satir("SELECT * FROM fn_mezuniyet_ozet_ben()") or {}

        profil = self.db.tek_satir(
            """SELECT o.ogrenci_no, o.giris_yili, k.ad || ' ' || k.soyad AS ad_soyad,
                      k.eposta, p.ad AS program_ad
                 FROM ogrenci o
                 JOIN kisi k ON k.kisi_id = o.kisi_id
                 LEFT JOIN mufredat m ON m.mufredat_id = o.mufredat_id
                 LEFT JOIN program p ON p.program_id = m.program_id
                WHERE o.kisi_id = fn_oturum_kisi_id()"""
        ) or {}

        danisman = self.db.tek_satir(
            """SELECT k.ad || ' ' || k.soyad AS ad_soyad, k.eposta
                 FROM danismanlik d
                 JOIN kisi k ON k.kisi_id = d.danisman_id
                WHERE d.ogrenci_id = fn_oturum_kisi_id()
                  AND d.gecerlilik @> current_date
                LIMIT 1"""
        ) or {}
        danisman_ad = danisman.get("ad_soyad") or "Atanmamış"

        ust_w = QWidget()
        ust_lay = QHBoxLayout(ust_w)
        ust_lay.setContentsMargins(0, 0, 0, 0)
        ust_lay.setSpacing(16)

        sol_kart = QFrame()
        sol_kart.setObjectName("PortalKart")
        s_lay = QVBoxLayout(sol_kart)
        s_lay.setContentsMargins(18, 16, 18, 16)
        s_lay.setSpacing(12)

        bas_harfler = "".join([p[0] for p in (profil.get("ad_soyad") or "Ö B").split()[:2]]).upper()
        lbl_avatar = QLabel(bas_harfler)
        lbl_avatar.setFixedSize(76, 76)
        lbl_avatar.setAlignment(Qt.AlignCenter)
        lbl_avatar.setStyleSheet(
            "background-color: #093567; color: #ffffff; font-size: 24px; "
            "font-weight: 800; border-radius: 38px; border: 3px solid #dbeafe;"
        )
        s_lay.addWidget(lbl_avatar, 0, Qt.AlignHCenter)

        bilgi_satirlari = [
            ("Ad Soyad", profil.get("ad_soyad") or self.db.ad_soyad),
            ("Öğrenci Numarası", str(profil.get("ogrenci_no") or "-")),
            ("Bölüm / Program", str(profil.get("program_ad") or "Bilgisayar Mühendisliği")),
            ("E-Posta", str(profil.get("eposta") or "-")),
            ("Akademik Danışman", danisman_ad),
        ]
        grid_p = QGridLayout()
        grid_p.setSpacing(0)
        for idx, (etiket, deger) in enumerate(bilgi_satirlari):
            bg = "#f4f7fb" if idx % 2 == 0 else "#ffffff"
            l_k = QLabel(etiket)
            l_k.setStyleSheet(
                f"background-color: {bg}; color: #3b6998; font-weight: 600; "
                "padding: 7px 10px; border: 1px solid #e5e9f0; border-right: none;"
            )
            l_v = QLabel(deger)
            l_v.setStyleSheet(
                f"background-color: {bg}; color: #1e293b; font-weight: 600; "
                "padding: 7px 10px; border: 1px solid #e5e9f0;"
            )
            grid_p.addWidget(l_k, idx, 0)
            grid_p.addWidget(l_v, idx, 1)
        s_lay.addLayout(grid_p)
        ust_lay.addWidget(sol_kart, 5)

        sag_kart = QFrame()
        sag_kart.setObjectName("PortalKart")
        r_lay = QVBoxLayout(sag_kart)
        r_lay.setContentsMargins(18, 16, 18, 16)
        r_lay.setSpacing(14)

        m_grid = QGridLayout()
        m_grid.setSpacing(12)
        m_grid.addWidget(
            bilgi_karti("Sınıf Bilgisi", f"{ozet.get('sinif', 1)}. Sınıf", "👨‍🏫", "#1d70db"), 0, 0
        )
        m_grid.addWidget(
            bilgi_karti("Verilen Kredi (AKTS)", f"{ozet.get('gecilen_akts', 0)} / {mez.get('gereken_akts', 30)}", "±÷", "#1d70db"), 0, 1
        )
        m_grid.addWidget(
            bilgi_karti("Dönem Not Ortalaması", str(ozet.get("dno") or "-"), ort_harf_rozeti(ozet.get("dno")), "#1d70db"), 1, 0
        )
        m_grid.addWidget(
            bilgi_karti("Genel Not Ortalaması", str(ozet.get("gno") or "-"), ort_harf_rozeti(ozet.get("gno")), "#1d70db"), 1, 1
        )
        r_lay.addLayout(m_grid)

        donemler = self.db.sorgula(
            "SELECT yil, tur FROM donem WHERE yil >= (SELECT giris_yili FROM ogrenci WHERE kisi_id = fn_oturum_kisi_id()) ORDER BY yil, CASE tur WHEN 'guz' THEN 1 WHEN 'bahar' THEN 2 ELSE 3 END"
        )
        r_lay.addWidget(DonemTimelineWidget(donemler))
        ust_lay.addWidget(sag_kart, 7)
        self.lay.addWidget(ust_w)

        hizmet_panel = QFrame()
        hizmet_panel.setObjectName("PortalKart")
        hp_lay = QVBoxLayout(hizmet_panel)
        hp_lay.setContentsMargins(20, 16, 20, 18)
        hp_lay.setSpacing(14)

        lbl_h_baslik = QLabel("Öğrenci Bilgi Sistemi Hizmetleri")
        lbl_h_baslik.setObjectName("BolumBaslik")
        lbl_h_baslik.setAlignment(Qt.AlignCenter)
        hp_lay.addWidget(lbl_h_baslik)

        h_grid = QGridLayout()
        h_grid.setSpacing(12)

        hizmetler = [
            ("👤", "#093567", "Kişisel Bilgiler",
             "Kişisel kimlik, bölüm, e-posta ve danışman iletişim bilgilerinizi görüntüleyebilirsiniz.",
             lambda: self._sekme_ac(4)),
            ("📝", "#22c55e", "Ders Kayıt İşlemleri",
             "Akademik durum, derse kaydolma, sepete ekleme/çıkarma ve kesinleştirme işlemlerini yapabilirsiniz.",
             lambda: self._sekme_ac(1)),
            ("📅", "#f59e0b", "Takvim & Haftalık Program",
             "Haftalık 5×8 ders programı ızgarası, ders saatleri ve kayıt penceresi takvimine ulaşabilirsiniz.",
             lambda: self._sekme_ac(4)),
            ("A+", "#1d70db", "Not Bilgileri & Transkript",
             "Döneme göre sınav bileşeni notlarınıza, resmi transkripte ve SHA-256 belge doğrulamaya ulaşabilirsiniz.",
             lambda: self._sekme_ac(2)),
            ("🎓", "#ef4444", "Mezuniyetime Ne Kaldı?",
             "Zorunlu/seçmeli grup denetimi, What-If müfredat simülasyonu ve DAG kritik yol ders planını inceleyin.",
             lambda: self._sekme_ac(3)),
            ("💬", "#a855f7", "Danışman Bilgileri",
             f"Aktif Danışmanınız: {danisman_ad}. Danışman onay durumlarınıza ve iletişim bilgilerine ulaşabilirsiniz.",
             lambda: self._sekme_ac(4)),
        ]

        for idx, (ikon, renk, baslik, aciklama, cb) in enumerate(hizmetler):
            kart = TiklanabilirHizmetKarti(ikon, renk, baslik, aciklama, cb)
            h_grid.addWidget(kart, idx // 3, idx % 3)

        hp_lay.addLayout(h_grid)
        self.lay.addWidget(hizmet_panel)

        hizli_panel = QFrame()
        hizli_panel.setObjectName("PortalKart")
        hz_lay = QVBoxLayout(hizli_panel)
        hz_lay.setContentsMargins(20, 16, 20, 18)
        hz_lay.setSpacing(10)

        lbl_hz = QLabel("Hızlı İşlemler")
        lbl_hz.setObjectName("BolumBaslik")
        lbl_hz.setAlignment(Qt.AlignCenter)
        hz_lay.addWidget(lbl_hz)

        kayit_durum_acik = "Açık ✓" if ozet.get("kayit_acik") else "Kapalı"
        lbl_hz_alt = QLabel(f"Hızlı işlem butonları aktif dönem ({ozet.get('aktif_donem') or '-'}) takvimine göre çalışmaktadır. Kayıt Penceresi: {kayit_durum_acik}")
        lbl_hz_alt.setAlignment(Qt.AlignCenter)
        lbl_hz_alt.setStyleSheet("color: #64748b; font-size: 11px;")
        hz_lay.addWidget(lbl_hz_alt)

        hz_grid = QGridLayout()
        hz_grid.setSpacing(12)

        hizli_butonlar = [
            ("⇅   Ders Ekle / Çıkar", lambda: self._sekme_ac(1)),
            ("📚   Akademik Durum & Transkript", lambda: self._sekme_ac(2)),
            ("🕒   Kayıtlı Dersler & Program", lambda: self._sekme_ac(1)),
            ("A+   Dönem Sonu Notları", lambda: self._sekme_ac(2)),
            ("🎓   Mezuniyetime Ne Kaldı?", lambda: self._sekme_ac(3)),
            ("👤   Kişisel & Danışman Bilgileri", lambda: self._sekme_ac(4)),
        ]
        for idx, (metin, cb) in enumerate(hizli_butonlar):
            btn = QPushButton(metin)
            btn.setObjectName("HizliIslemBtn")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(cb)
            hz_grid.addWidget(btn, idx // 3, idx % 3)

        hz_lay.addLayout(hz_grid)
        self.lay.addWidget(hizli_panel)


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
        baslik = QLabel("Ders Kayıt İşlemleri, Sepet ve Haftalık Program")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        self.lbl_akts = QLabel()
        self.lbl_akts.setStyleSheet("font-weight: 700; color: #093567; font-size: 12px;")
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
