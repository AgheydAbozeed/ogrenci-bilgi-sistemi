import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QSplitter, QScrollArea, QTabWidget, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QBrush, QCursor, QPainter, QPen, QFont
from app.db import Veritabani, hata_coz, hata_goster, HATA_SABLONLARI
from app.stil import (
    OLCULER, DURUM_ROZETLERI, akts_cubuk_kurali, rozet_formatla, aktif_palet
)

GUN_KISA_HARITA = {
    "pzt": (0, "Pazartesi"),
    "sal": (1, "Salı"),
    "car": (2, "Çarşamba"),
    "çar": (2, "Çarşamba"),
    "per": (3, "Perşembe"),
    "cum": (4, "Cuma"),
}


def ort_harf_rozeti(deger) -> str:
    try:
        v = float(deger)
    except (TypeError, ValueError):
        return "-"
    if v >= 3.50:
        return "A+"
    if v >= 3.00:
        return "A"
    if v >= 2.50:
        return "B"
    if v >= 2.00:
        return "C"
    if v >= 1.00:
        return "D"
    return "F"


def saat_metni_coz(saatler_str: str) -> list[tuple[int, int, str]]:
    """
    'Pzt 1, Pzt 2, Car 3' veya 'Pzt 09:00-11:00' biçimindeki metni
    [(gun_idx_0_4, saat_idx_0_7, gun_tam_ad), ...] listesine çevirir.
    """
    sonuc = []
    if not saatler_str or saatler_str == "-":
        return sonuc
    for parca in saatler_str.split(","):
        p = parca.strip()
        # Biçim 1: 'Pzt 1' veya 'Car 3'
        m1 = re.match(r"^([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{1,2})$", p)
        if m1:
            g_kisa = m1.group(1).lower()[:3]
            saat_no = int(m1.group(2))
            if g_kisa in GUN_KISA_HARITA and 1 <= saat_no <= 8:
                g_idx, g_ad = GUN_KISA_HARITA[g_kisa]
                sonuc.append((g_idx, saat_no - 1, g_ad))
            continue
        # Biçim 2: 'Pzt 09:00-11:00'
        m2 = re.search(r"([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{1,2}):\d{2}\s*[-–]\s*(\d{1,2}):\d{2}", p)
        if m2:
            g_kisa = m2.group(1).lower()[:3]
            bas, bit = int(m2.group(2)), int(m2.group(3))
            if g_kisa in GUN_KISA_HARITA:
                g_idx, g_ad = GUN_KISA_HARITA[g_kisa]
                for h in range(max(9, bas), min(17, bit)):
                    sonuc.append((g_idx, h - 9, g_ad))
    return sonuc


class DonemTimelineWidget(QWidget):
    def __init__(self, donemler):
        super().__init__()
        self.donemler = donemler[:6]
        self.setFixedHeight(78)

    def paintEvent(self, event):
        pal = aktif_palet()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, n = self.width(), 6
        adim = w / n
        xs = [int(adim * i + adim / 2) for i in range(n)]
        y_cizgi = 20
        aktif_sayisi = len(self.donemler)

        p.setPen(QPen(QColor(pal["kenarlik"]), 2))
        p.drawLine(24, y_cizgi, w - 24, y_cizgi)

        if aktif_sayisi > 0:
            son_x = xs[min(aktif_sayisi - 1, n - 1)]
            p.setPen(QPen(QColor("#15803D"), 2))
            p.drawLine(24, y_cizgi, son_x, y_cizgi)

        tur_ad = {"guz": "Güz Dönemi", "bahar": "Bahar Dönemi", "yaz": "Yaz Dönemi"}
        font = self.font()

        for i, x in enumerate(xs):
            p.setPen(Qt.NoPen)
            if i < aktif_sayisi:
                if i == 0:
                    p.setBrush(QColor("#15803D"))
                    p.drawEllipse(x - 7, y_cizgi - 7, 14, 14)
                else:
                    p.setBrush(QColor("#22C55E"))
                    p.drawEllipse(x - 5, y_cizgi - 5, 10, 10)

                d = self.donemler[i]
                yil_str = f"{d['yil']}-{int(d['yil'])+1}"
                tur_str = tur_ad.get(d["tur"], str(d["tur"]))

                p.setPen(QColor(pal["ikincil_metin"]))
                font.setPointSize(9)
                font.setBold(False)
                p.setFont(font)
                p.drawText(int(x - adim / 2), y_cizgi + 14, int(adim), 18, Qt.AlignCenter, yil_str)

                p.setPen(QColor(pal["metin"]))
                font.setPointSize(9)
                p.setFont(font)
                p.drawText(int(x - adim / 2), y_cizgi + 30, int(adim), 18, Qt.AlignCenter, tur_str)
            else:
                p.setBrush(QColor(pal["kenarlik"]))
                p.drawEllipse(x - 5, y_cizgi - 5, 10, 10)


def bilgi_karti(baslik: str, deger: str, ikon: str = "A+", renk: str = "#2563EB") -> QFrame:
    pal = aktif_palet()
    kart = QFrame()
    kart.setObjectName("MetrikKutu")
    lay = QHBoxLayout(kart)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(12)

    lbl_ikon = QLabel(ikon)
    lbl_ikon.setFixedSize(44, 44)
    lbl_ikon.setAlignment(Qt.AlignCenter)
    lbl_ikon.setStyleSheet(
        f"color: {renk}; background-color: {pal['zebra_zemin']}; border: 1px solid {pal['kenarlik']}; "
        f"border-radius: 6px; font-size: 14pt; font-weight: 800;"
    )
    lay.addWidget(lbl_ikon)

    v = QVBoxLayout()
    v.setSpacing(2)
    lbl_b = QLabel(baslik)
    lbl_b.setStyleSheet(f"color: {pal['ikincil_metin']}; font-size: 9.5pt; font-weight: 500;")
    lbl_d = QLabel(deger)
    lbl_d.setStyleSheet(f"color: {pal['metin']}; font-size: 14pt; font-weight: 700;")
    v.addWidget(lbl_b)
    v.addWidget(lbl_d)
    lay.addLayout(v, 1)
    return kart


class TiklanabilirHizmetKarti(QFrame):
    def __init__(self, ikon: str, renk: str, baslik: str, aciklama: str, callback):
        super().__init__()
        pal = aktif_palet()
        self.setObjectName("HizmetKart")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.callback = callback

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        lbl_i = QLabel(ikon)
        lbl_i.setFixedSize(46, 46)
        lbl_i.setAlignment(Qt.AlignCenter)
        lbl_i.setStyleSheet(
            f"color: {renk}; font-size: 16pt; font-weight: 800; "
            f"border: 2px solid {renk}; border-radius: 8px; background-color: {pal['kart_zemin']};"
        )
        lay.addWidget(lbl_i, 0, Qt.AlignTop)

        v = QVBoxLayout()
        v.setSpacing(4)
        lbl_b = QLabel(baslik)
        lbl_b.setStyleSheet(f"color: {renk}; font-size: 11pt; font-weight: 700;")
        lbl_a = QLabel(aciklama)
        lbl_a.setWordWrap(True)
        lbl_a.setStyleSheet(f"color: {pal['ikincil_metin']}; font-size: 9.5pt;")
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
        self.lay.setContentsMargins(20, 16, 20, 20)
        self.lay.setSpacing(16)

        scroll.setWidget(self.icerik_w)
        ana_lay.addWidget(scroll)
        self.yenile()

    def _sekme_ac(self, idx: int):
        if self.sekme_gecis_cb:
            self.sekme_gecis_cb(idx)

    def yenile(self):
        pal = aktif_palet()
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ozet = self.db.tek_satir("SELECT * FROM v_ana_sayfa") or {}
        mez = self.db.tek_satir("SELECT * FROM fn_mezuniyet_ozet_ben()") or {}

        profil = self.db.tek_satir(
            """SELECT o.ogrenci_no, o.giris_yili, k.ad || ' ' || k.soyad AS ad_soyad,
                      k.eposta, p.ad AS program_ad,
                      (SELECT kd.ad || ' ' || kd.soyad
                         FROM danismanlik d
                         JOIN kisi kd ON kd.kisi_id = d.danisman_id
                        WHERE d.ogrenci_id = o.kisi_id
                          AND d.gecerlilik @> current_date
                        LIMIT 1) AS danisman_ad
                 FROM ogrenci o
                 JOIN kisi k ON k.kisi_id = o.kisi_id
                 LEFT JOIN mufredat m ON m.mufredat_id = o.mufredat_id
                 LEFT JOIN program p ON p.program_id = m.program_id
                WHERE o.kisi_id = fn_oturum_kisi_id()"""
        ) or {}
        danisman_ad = profil.get("danisman_ad") or "Atanmamış"

        ust_w = QWidget()
        ust_lay = QHBoxLayout(ust_w)
        ust_lay.setContentsMargins(0, 0, 0, 0)
        ust_lay.setSpacing(16)

        sol_kart = QFrame()
        sol_kart.setObjectName("PortalKart")
        s_lay = QVBoxLayout(sol_kart)
        s_lay.setContentsMargins(16, 16, 16, 16)
        s_lay.setSpacing(12)

        bas_harfler = "".join([p[0] for p in (profil.get("ad_soyad") or "Ö B").split()[:2]]).upper()
        lbl_avatar = QLabel(bas_harfler)
        lbl_avatar.setFixedSize(72, 72)
        lbl_avatar.setAlignment(Qt.AlignCenter)
        lbl_avatar.setStyleSheet(
            "background-color: #12355B; color: #FFFFFF; font-size: 18pt; "
            "font-weight: 800; border-radius: 36px; border: 3px solid #2563EB;"
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
            bg = pal["zebra_zemin"] if idx % 2 == 0 else pal["kart_zemin"]
            l_k = QLabel(etiket)
            l_k.setStyleSheet(
                f"background-color: {bg}; color: {pal['ikincil_metin']}; font-weight: 600; "
                f"padding: 7px 10px; border: 1px solid {pal['kenarlik']}; border-right: none;"
            )
            l_v = QLabel(deger)
            l_v.setStyleSheet(
                f"background-color: {bg}; color: {pal['metin']}; font-weight: 600; "
                f"padding: 7px 10px; border: 1px solid {pal['kenarlik']};"
            )
            grid_p.addWidget(l_k, idx, 0)
            grid_p.addWidget(l_v, idx, 1)
        s_lay.addLayout(grid_p)
        ust_lay.addWidget(sol_kart, 5)

        sag_kart = QFrame()
        sag_kart.setObjectName("PortalKart")
        r_lay = QVBoxLayout(sag_kart)
        r_lay.setContentsMargins(16, 16, 16, 16)
        r_lay.setSpacing(12)

        m_grid = QGridLayout()
        m_grid.setSpacing(12)
        m_grid.addWidget(
            bilgi_karti("Sınıf Bilgisi", f"{ozet.get('sinif', 1)}. Sınıf", "🎓", "#2563EB"), 0, 0
        )
        m_grid.addWidget(
            bilgi_karti("Geçilen Kredi (AKTS)", f"{ozet.get('gecilen_akts', 0)} / {mez.get('gereken_akts', 240)}", "±÷", "#15803D"), 0, 1
        )
        m_grid.addWidget(
            bilgi_karti("Dönem Not Ortalaması", str(ozet.get("dno") or "-"), ort_harf_rozeti(ozet.get("dno")), "#2563EB"), 1, 0
        )
        m_grid.addWidget(
            bilgi_karti("Genel Not Ortalaması", str(ozet.get("gno") or "-"), ort_harf_rozeti(ozet.get("gno")), "#2563EB"), 1, 1
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
        hp_lay.setSpacing(12)

        lbl_h_baslik = QLabel("Öğrenci Bilgi Sistemi Hizmetleri")
        lbl_h_baslik.setObjectName("BolumBaslik")
        lbl_h_baslik.setAlignment(Qt.AlignCenter)
        hp_lay.addWidget(lbl_h_baslik)

        h_grid = QGridLayout()
        h_grid.setSpacing(12)

        hizmetler = [
            ("👤", "#12355B", "Kişisel Bilgiler",
             "Kişisel kimlik, bölüm, e-posta ve danışman iletişim bilgilerinizi görüntüleyebilirsiniz.",
             lambda: self._sekme_ac(4)),
            ("📝", "#15803D", "Ders Kayıt İşlemleri",
             "Şube seçimi, üzerine gelince haftalık program önizlemesi ve AKTS çubuğu ile kayıt yapın.",
             lambda: self._sekme_ac(1)),
            ("📅", "#92400E", "Takvim & Haftalık Program",
             "Haftalık 5×8 ders programı ızgarası, ders saatleri ve kayıt penceresi takvimine ulaşabilirsiniz.",
             lambda: self._sekme_ac(4)),
            ("A+", "#2563EB", "Not Bilgileri & Transkript",
             "Döneme göre sınav bileşeni notlarınıza, resmi transkripte ve SHA-256 belge doğrulamaya ulaşabilirsiniz.",
             lambda: self._sekme_ac(2)),
            ("🎓", "#B91C1C", "Mezuniyetime Ne Kaldı? & Önkoşul Haritası",
             "Zorunlu/seçmeli grup denetimi, interaktif Önkoşul DAG haritası ve kritik yol ders planını inceleyin.",
             lambda: self._sekme_ac(3)),
            ("💬", "#2563EB", "Danışman Bilgileri",
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
        hz_lay.setSpacing(12)

        lbl_hz = QLabel("Hızlı İşlemler")
        lbl_hz.setObjectName("BolumBaslik")
        lbl_hz.setAlignment(Qt.AlignCenter)
        hz_lay.addWidget(lbl_hz)

        kayit_durum_acik = "Açık ✔" if ozet.get("kayit_acik") else "Kapalı"
        lbl_hz_alt = QLabel(
            f"Hızlı işlem butonları aktif dönem ({ozet.get('aktif_donem') or '-'}) takvimine göre çalışmaktadır. Kayıt Penceresi: {kayit_durum_acik}"
        )
        lbl_hz_alt.setAlignment(Qt.AlignCenter)
        lbl_hz_alt.setStyleSheet(f"color: {pal['ikincil_metin']}; font-size: 9.5pt;")
        hz_lay.addWidget(lbl_hz_alt)

        hz_grid = QGridLayout()
        hz_grid.setSpacing(12)

        hizli_butonlar = [
            ("⇅   Ders Ekle / Çıkar (Ctrl+2)", lambda: self._sekme_ac(1)),
            ("📚   Akademik Durum & Transkript (Ctrl+3)", lambda: self._sekme_ac(2)),
            ("🕒   Kayıtlı Dersler & Program", lambda: self._sekme_ac(1)),
            ("A+   Dönem Sonu Notları", lambda: self._sekme_ac(2)),
            ("🎓   Mezuniyet & Önkoşul DAG (Ctrl+4)", lambda: self._sekme_ac(3)),
            ("👤   Kişisel & Danışman Bilgileri (Ctrl+5)", lambda: self._sekme_ac(4)),
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
    """
    Tasarım Sistemi Kararları:
    - Sol %60 şube listesi, sağ %40 haftalık program, altta sekmeli 'Kayıtlarım'.
    - Sayfa altında sabit AKTS çubuğu (%80 altı mavi, %80-100 sarı, üstü kırmızı).
    - Üzerine gelince (hover) önizleme: Şubenin saatleri programda %40 saydam gölge olarak görünür.
    - Çakışma gösterimi: Çakışan hücre kırmızı çapraz taramalı (Qt.BDiagPattern).
    - Renge ek olarak ikon + metin rozetleri ve kullanıcı dilinde neden/boş durum mesajları.
    """

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.subeler_veri: list[dict] = []
        self.dolu_slotlar: dict[tuple[int, int], tuple[str, str]] = {}  # (gun_0_4, saat_0_7) -> (ders_kod, durum)
        self.aktif_limit = 30
        self.secili_akts = 0

        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 16, 16, 12)
        self.lay.setSpacing(12)

        # Üst Başlık ve Eylem Çubuğu
        ust = QHBoxLayout()
        baslik = QLabel("Ders Kayıt İşlemleri, Sepet ve Haftalık Program")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_takvim = QPushButton("📅  Tam Ekran Çakışma Matrisi")
        btn_takvim.setObjectName("IkincilBtn")
        btn_takvim.clicked.connect(self.haftalik_program_goster)
        ust.addWidget(btn_takvim)

        btn_kesin = QPushButton("✔  Sepeti Kesinleştir (Ctrl+Enter)")
        btn_kesin.setObjectName("BirincilBtn")
        btn_kesin.clicked.connect(self.hepsini_kesinlestir)
        ust.addWidget(btn_kesin)

        btn_yenile = QPushButton("↻  Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        # Ana Dikey Bölücü: Üstte (Sol %60 Şubeler + Sağ %40 Haftalık Program), Altta Sekmeli Kayıtlarım
        ana_splitter = QSplitter(Qt.Vertical)

        ust_bolge = QWidget()
        ust_h = QHBoxLayout(ust_bolge)
        ust_h.setContentsMargins(0, 0, 0, 0)
        ust_h.setSpacing(12)

        # SOL %60: Şube Listesi
        sol_kart = QFrame()
        sol_kart.setObjectName("PortalKart")
        sol_lay = QVBoxLayout(sol_kart)
        sol_lay.setContentsMargins(12, 12, 12, 12)
        sol_lay.setSpacing(8)

        arama_lay = QHBoxLayout()
        lbl_acik = QLabel("<b>Açık Şubeler (Üzerine gelerek programda önizleyin)</b>")
        arama_lay.addWidget(lbl_acik)
        arama_lay.addStretch()
        self.txt_ara = QLineEdit()
        self.txt_ara.setPlaceholderText("🔍 Ders kodu, adı veya öğretim üyesi ara...")
        self.txt_ara.setMinimumWidth(240)
        self.txt_ara.textChanged.connect(self.sube_filtrele)
        arama_lay.addWidget(self.txt_ara)
        sol_lay.addLayout(arama_lay)

        self.tbl_subeler = QTableWidget(0, 8)
        self.tbl_subeler.setHorizontalHeaderLabels(
            ["Kod", "Ders Adı", "AKTS", "Şb", "Öğretim Üyesi", "Saatler", "Durum Rozeti & Neden", "İşlem"]
        )
        self.tbl_subeler.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tbl_subeler.horizontalHeader().setStretchLastSection(True)
        self.tbl_subeler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_subeler.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_subeler.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_subeler.setMouseTracking(True)
        self.tbl_subeler.cellEntered.connect(self._sube_uzerine_gelindi)
        self.tbl_subeler.viewport().installEventFilter(self)
        sol_lay.addWidget(self.tbl_subeler, 1)
        ust_h.addWidget(sol_kart, 6)  # %60

        # SAĞ %40: Haftalık Ders Programı (Önizleme + Çapraz Tarama Destekli)
        sag_kart = QFrame()
        sag_kart.setObjectName("PortalKart")
        sag_lay = QVBoxLayout(sag_kart)
        sag_lay.setContentsMargins(12, 12, 12, 12)
        sag_lay.setSpacing(8)

        prog_ust = QHBoxLayout()
        prog_ust.addWidget(QLabel("<b>Haftalık Ders Programı (5×8)</b>"))
        prog_ust.addStretch()
        self.lbl_onizleme_ipucu = QLabel("Şube üzerine gelin: %40 gölge | Çakışma: ▨ taralı")
        self.lbl_onizleme_ipucu.setStyleSheet("color: #475569; font-size: 8.5pt;")
        prog_ust.addWidget(self.lbl_onizleme_ipucu)
        sag_lay.addLayout(prog_ust)

        self.tbl_prog = QTableWidget(8, 5)
        self.tbl_prog.setHorizontalHeaderLabels(["Pzt", "Sal", "Çar", "Per", "Cum"])
        self.tbl_prog.setVerticalHeaderLabels([f"{s}. Saat" for s in range(1, 9)])
        self.tbl_prog.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_prog.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_prog.setEditTriggers(QTableWidget.NoEditTriggers)
        sag_lay.addWidget(self.tbl_prog, 1)
        ust_h.addWidget(sag_kart, 4)  # %40

        ana_splitter.addWidget(ust_bolge)

        # ALT BÖLGE: Sekmeli 'Kayıtlarım' + Boş Durum Mesajı
        alt_sekme_kap = QWidget()
        alt_lay = QVBoxLayout(alt_sekme_kap)
        alt_lay.setContentsMargins(0, 0, 0, 0)
        alt_lay.setSpacing(6)

        self.lbl_bos_sepet = QLabel(f"ℹ️  {HATA_SABLONLARI['BOS_SEPET']}")
        self.lbl_bos_sepet.setAlignment(Qt.AlignCenter)
        self.lbl_bos_sepet.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; "
            "border-radius: 6px; padding: 8px 12px; font-weight: 600;"
        )
        alt_lay.addWidget(self.lbl_bos_sepet)

        self.sekme_kayitlar = QTabWidget()
        self.tbl_kayit = self._kayit_tablosu_olustur()
        self.tbl_sepet_filtre = self._kayit_tablosu_olustur()
        self.tbl_onayli_filtre = self._kayit_tablosu_olustur()

        self.sekme_kayitlar.addTab(self.tbl_kayit, "📋 Tüm Kayıtlarım (0)")
        self.sekme_kayitlar.addTab(self.tbl_sepet_filtre, "🛒 Sepetim (0)")
        self.sekme_kayitlar.addTab(self.tbl_onayli_filtre, "✔ Kesinleşen / Onaylı (0)")
        alt_lay.addWidget(self.sekme_kayitlar, 1)

        ana_splitter.addWidget(alt_sekme_kap)
        ana_splitter.setStretchFactor(0, 3)
        ana_splitter.setStretchFactor(1, 2)
        self.lay.addWidget(ana_splitter, 1)

        # SAYFA ALTINDA SABİT AKTS ÇUBUĞU
        self.akts_cerceve = QFrame()
        self.akts_cerceve.setObjectName("PortalKart")
        akts_lay = QHBoxLayout(self.akts_cerceve)
        akts_lay.setContentsMargins(16, 10, 16, 10)
        akts_lay.setSpacing(16)

        lbl_akts_baslik = QLabel("<b>Dönemlik AKTS Yükü:</b>")
        akts_lay.addWidget(lbl_akts_baslik)

        self.bar_akts = QProgressBar()
        self.bar_akts.setMinimumHeight(22)
        self.bar_akts.setTextVisible(True)
        akts_lay.addWidget(self.bar_akts, 1)

        self.lbl_akts = QLabel()
        self.lbl_akts.setStyleSheet("font-weight: 700; font-size: 10.5pt;")
        akts_lay.addWidget(self.lbl_akts)

        self.lay.addWidget(self.akts_cerceve)
        self.yenile()

    def _kayit_tablosu_olustur(self) -> QTableWidget:
        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(["Kod", "Ders Adı", "AKTS", "Durum Rozeti", "Danışman Gerekçesi", "İşlem"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        return tbl

    def eventFilter(self, obj, event):
        if obj is self.tbl_subeler.viewport() and event.type() == QEvent.Leave:
            self._programi_ciz(onizleme_sube=None)
        return super().eventFilter(obj, event)

    def _cakisma_detayi_bul(self, ders_kod: str, saatler_str: str) -> str:
        """
        Çakışan şube için kullanıcı dilinde mesaj üretir:
        '{ders}, {gun} {saat}. saatte {diger} ile çakışıyor.'
        """
        for g_idx, s_idx, g_ad in saat_metni_coz(saatler_str):
            mevcut = self.dolu_slotlar.get((g_idx, s_idx))
            if mevcut:
                diger_kod, _ = mevcut
                return HATA_SABLONLARI["CAKISMA"].format(
                    ders=ders_kod, gun=g_ad, saat=s_idx + 1, diger=diger_kod
                )
        return "Mevcut programla saat çakışması"

    def _onkosul_detayi_bul(self, ders_kod: str, neden_str: str) -> str:
        """
        Önkoşul eksiği için kullanıcı dilinde mesaj üretir:
        '{ders} için önce {onkosul} dersini en az {harf} ile geçmelisiniz.'
        """
        onkosul_kod = (neden_str or "").strip() or "önkoşul"
        return HATA_SABLONLARI["ONKOSUL_EKSIK"].format(
            ders=ders_kod, onkosul=onkosul_kod, harf="CC"
        )

    def yenile(self):
        baglam_meta = self.db.tek_satir(
            "SELECT fn_aktif_donem_id() AS id, fn_akts_limit(fn_oturum_kisi_id()) AS lim"
        ) or {}
        aktif_donem = baglam_meta.get("id")
        self.aktif_limit = int(baglam_meta.get("lim") or 30)

        # Önce haftalık programdaki dolu slotları oku
        prog = self.db.sorgula("SELECT * FROM v_haftalik_program WHERE donem_id = %s", (aktif_donem,))
        self.dolu_slotlar.clear()
        for p in prog:
            gun = int(p["gun"]) - 1
            saat = int(p["ders_saati"]) - 1
            if 0 <= gun < 5 and 0 <= saat < 8:
                self.dolu_slotlar[(gun, saat)] = (p["ders_kod"], p["durum"])

        # Açık şubeleri oku ve tabloya yerleştir
        self.subeler_veri = self.db.sorgula(
            "SELECT * FROM v_acik_subeler WHERE donem_id = %s ORDER BY ders_kod, sube_no", (aktif_donem,)
        )
        self.tbl_subeler.setRowCount(0)
        for s in self.subeler_veri:
            r = self.tbl_subeler.rowCount()
            self.tbl_subeler.insertRow(r)
            self.tbl_subeler.setItem(r, 0, QTableWidgetItem(s["ders_kod"]))
            self.tbl_subeler.setItem(r, 1, QTableWidgetItem(s["ders_ad"]))
            it_akts = QTableWidgetItem(str(s["akts"]))
            it_akts.setTextAlignment(Qt.AlignCenter)
            self.tbl_subeler.setItem(r, 2, it_akts)
            it_sb = QTableWidgetItem(str(s["sube_no"]))
            it_sb.setTextAlignment(Qt.AlignCenter)
            self.tbl_subeler.setItem(r, 3, it_sb)
            self.tbl_subeler.setItem(r, 4, QTableWidgetItem(s["hoca"]))
            self.tbl_subeler.setItem(r, 5, QTableWidgetItem(s["saatler"]))

            durum = s["durum"]
            neden_metin = s.get("neden")
            if durum == "onkosul_eksik" and neden_metin:
                neden_metin = self._onkosul_detayi_bul(s["ders_kod"], neden_metin)
            elif durum == "cakisiyor":
                neden_metin = self._cakisma_detayi_bul(s["ders_kod"], s["saatler"])

            bg, fg, etiket = rozet_formatla(durum, neden_metin)
            item_d = QTableWidgetItem(etiket)
            item_d.setBackground(QBrush(QColor(bg)))
            item_d.setForeground(QBrush(QColor(fg)))
            f_bold = QFont()
            f_bold.setBold(True)
            item_d.setFont(f_bold)
            self.tbl_subeler.setItem(r, 6, item_d)

            btn = QPushButton("➕ Sepete Ekle" if durum == "alinabilir" else "—")
            btn.setObjectName("BirincilBtn" if durum == "alinabilir" else "IkincilBtn")
            btn.setEnabled(durum == "alinabilir")
            sube_id = s["sube_id"]
            btn.clicked.connect(lambda _, sid=sube_id, sv=s: self.sepete_ekle(sid, sv))
            self.tbl_subeler.setCellWidget(r, 7, btn)

        self.tbl_subeler.resizeColumnsToContents()

        # Kayıtlarımı oku ve 3 sekmeli tabloya doldur
        kayitlar = self.db.sorgula(
            "SELECT * FROM v_kayitlarim WHERE donem_id = %s ORDER BY kayit_id", (aktif_donem,)
        )
        self._kayit_tablosu_doldur(self.tbl_kayit, kayitlar)
        sepet_list = [k for k in kayitlar if k["durum"] == "sepet"]
        onay_list = [k for k in kayitlar if k["durum"] in ("onay_bekliyor", "onayli")]
        self._kayit_tablosu_doldur(self.tbl_sepet_filtre, sepet_list)
        self._kayit_tablosu_doldur(self.tbl_onayli_filtre, onay_list)

        self.sekme_kayitlar.setTabText(0, f"📋 Tüm Kayıtlarım ({len(kayitlar)})")
        self.sekme_kayitlar.setTabText(1, f"🛒 Sepetim ({len(sepet_list)})")
        self.sekme_kayitlar.setTabText(2, f"✔ Kesinleşen / Onaylı ({len(onay_list)})")

        # Boş durum (sepet) görünürlüğü
        aktif_kayit_var = any(k["durum"] in ("sepet", "onay_bekliyor", "onayli") for k in kayitlar)
        self.lbl_bos_sepet.setVisible(not aktif_kayit_var)

        # Sabit AKTS çubuğunu güncelle
        self.secili_akts = sum(
            int(k["akts"]) for k in kayitlar if k["durum"] in ("sepet", "onay_bekliyor", "onayli")
        )
        self._akts_cubugu_guncelle(self.secili_akts, self.aktif_limit)

        # Haftalık programı çiz
        self._programi_ciz(onizleme_sube=None)

    def _kayit_tablosu_doldur(self, tbl: QTableWidget, satirlar: list[dict]):
        tbl.setRowCount(0)
        for k in satirlar:
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(k["ders_kod"]))
            tbl.setItem(r, 1, QTableWidgetItem(k["ders_ad"]))
            it_akts = QTableWidgetItem(str(k["akts"]))
            it_akts.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(r, 2, it_akts)

            bg, fg, rozet_metin = rozet_formatla(k["durum"])
            it_durum = QTableWidgetItem(rozet_metin)
            it_durum.setBackground(QBrush(QColor(bg)))
            it_durum.setForeground(QBrush(QColor(fg)))
            f_b = QFont()
            f_b.setBold(True)
            it_durum.setFont(f_b)
            tbl.setItem(r, 3, it_durum)

            tbl.setItem(r, 4, QTableWidgetItem(str(k.get("onay_gerekce") or "—")))

            kid = k["kayit_id"]
            if k["durum"] == "sepet":
                btn_k = QPushButton("✖ Sepetten Çıkar")
                btn_k.setObjectName("TehlikeBtn")
                btn_k.clicked.connect(lambda _, x=kid: self.sepetten_cikar(x))
                tbl.setCellWidget(r, 5, btn_k)
            elif k["durum"] in ("onay_bekliyor", "onayli"):
                btn_k = QPushButton("Dersi Bırak")
                btn_k.setObjectName("IkincilBtn")
                btn_k.clicked.connect(lambda _, x=kid: self.dersi_birak(x))
                tbl.setCellWidget(r, 5, btn_k)
            else:
                tbl.setItem(r, 5, QTableWidgetItem("—"))

    def _akts_cubugu_guncelle(self, toplam: int, sinir: int):
        fg_hex, bg_hex, etiket = akts_cubuk_kurali(toplam, sinir)
        self.bar_akts.setMaximum(max(sinir, toplam, 1))
        self.bar_akts.setValue(toplam)
        oran_yuzde = int(round((toplam / max(1, sinir)) * 100))
        self.bar_akts.setFormat(f"%{oran_yuzde} ({toplam} / {sinir} AKTS)")
        self.bar_akts.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {bg_hex};
                color: {fg_hex};
                border: 1px solid {fg_hex};
                border-radius: 6px;
                text-align: center;
                font-weight: 700;
            }}
            QProgressBar::chunk {{
                background-color: {fg_hex};
                border-radius: 5px;
            }}
            """
        )
        self.lbl_akts.setText(etiket)
        self.lbl_akts.setStyleSheet(f"color: {fg_hex}; font-weight: 700; font-size: 10.5pt;")

    def _sube_uzerine_gelindi(self, row: int, _col: int):
        if 0 <= row < len(self.subeler_veri):
            sube = self.subeler_veri[row]
            self._programi_ciz(onizleme_sube=sube)
            # AKTS çubuğunda şube eklendiğinde oluşacak toplamı da önizle
            if sube.get("durum") == "alinabilir":
                aday_toplam = self.secili_akts + int(sube.get("akts") or 0)
                self._akts_cubugu_guncelle(aday_toplam, self.aktif_limit)
            else:
                self._akts_cubugu_guncelle(self.secili_akts, self.aktif_limit)

    def _programi_ciz(self, onizleme_sube: dict | None = None):
        """
        Sağdaki 5x8 haftalık programı çizer.
        - Mevcut kayıtlı/sepetteki dersleri gösterir.
        - onizleme_sube verilirse:
          * Boş hücrelerde %40 saydam gölge (QColor(37, 99, 235, 102)) olarak önizler.
          * Dolu hücreyle çakışıyorsa kırmızı çapraz taramalı (Qt.BDiagPattern) olarak gösterir.
        """
        self.tbl_prog.clearContents()
        for (gun, saat), (kod, durum) in self.dolu_slotlar.items():
            bg, fg, _ = rozet_formatla(durum)
            ikon = DURUM_ROZETLERI.get(durum, {}).get("ikon", "✔")
            hucre = QTableWidgetItem(f"{ikon} {kod}\n({durum})")
            hucre.setBackground(QBrush(QColor(bg)))
            hucre.setForeground(QBrush(QColor(fg)))
            hucre.setTextAlignment(Qt.AlignCenter)
            f = QFont()
            f.setBold(True)
            hucre.setFont(f)
            self.tbl_prog.setItem(saat, gun, hucre)

        if not onizleme_sube:
            self._akts_cubugu_guncelle(self.secili_akts, self.aktif_limit)
            return

        onizleme_kod = onizleme_sube.get("ders_kod", "")
        saatler_str = onizleme_sube.get("saatler", "")
        for g_idx, s_idx, _ in saat_metni_coz(saatler_str):
            if not (0 <= g_idx < 5 and 0 <= s_idx < 8):
                continue
            mevcut = self.dolu_slotlar.get((g_idx, s_idx))
            if mevcut and mevcut[0] != onizleme_kod:
                # ÇAKIŞMA: Kırmızı çapraz taramalı (Qt.BDiagPattern)
                hucre = QTableWidgetItem(f"✖ ÇAKIŞMA\n{mevcut[0]} ⚡ {onizleme_kod}")
                tarama = QBrush(QColor("#B91C1C"), Qt.BDiagPattern)
                hucre.setBackground(tarama)
                hucre.setForeground(QBrush(QColor("#B91C1C")))
                hucre.setTextAlignment(Qt.AlignCenter)
                f = QFont()
                f.setBold(True)
                hucre.setFont(f)
                self.tbl_prog.setItem(s_idx, g_idx, hucre)
            elif not mevcut:
                # ÜZERİNE GELİNCE ÖNİZLEME: %40 saydam gölge
                hucre = QTableWidgetItem(f"👁️ {onizleme_kod}\n(Önizleme)")
                golge_renk = QColor(37, 99, 235, 102)  # %40 saydam vurgu mavisi
                hucre.setBackground(QBrush(golge_renk))
                hucre.setForeground(QBrush(QColor("#1E3A8A")))
                hucre.setTextAlignment(Qt.AlignCenter)
                self.tbl_prog.setItem(s_idx, g_idx, hucre)

    def sepete_ekle(self, sube_id: int, sube_veri: dict | None = None):
        baglam = {}
        if sube_veri:
            baglam["ders"] = sube_veri.get("ders_kod")
            baglam["onkosul"] = sube_veri.get("neden")
            baglam["limit"] = self.aktif_limit
            baglam["toplam"] = self.secili_akts + int(sube_veri.get("akts") or 0)
        try:
            self.db.calistir("SELECT fn_sepete_ekle(%s)", (sube_id,))
            self.yenile()
        except Exception as e:
            hata_goster(self, "Kural Engeli", e, baglam)

    def sepetten_cikar(self, kayit_id: int):
        try:
            self.db.calistir("SELECT fn_sepetten_cikar(%s)", (kayit_id,))
            self.yenile()
        except Exception as e:
            hata_goster(self, "İşlem Hatası", e)

    def dersi_birak(self, kayit_id: int):
        try:
            self.db.calistir("SELECT fn_birak(%s)", (kayit_id,))
            self.yenile()
        except Exception as e:
            hata_goster(self, "İşlem Hatası", e)

    def hepsini_kesinlestir(self):
        try:
            sonuclar = self.db.calistir("SELECT * FROM fn_kesinlestir_hepsi()")
            if not sonuclar:
                QMessageBox.information(self, "Bilgi", HATA_SABLONLARI["BOS_SEPET"])
                return
            hatalar = []
            teknik_detaylar = []
            for s in sonuclar:
                if s["sonuc"] == "hata":
                    hatalar.append(
                        f"• {hata_coz(Exception(s['mesaj']), {'limit': self.aktif_limit, 'toplam': self.secili_akts})}"
                    )
                    teknik_detaylar.append(f"Kayıt #{s['kayit_id']}: {s['mesaj']}")
            tamam = sum(1 for s in sonuclar if s["sonuc"] == "tamam")
            self.yenile()
            if hatalar:
                kutu = QMessageBox(self)
                kutu.setIcon(QMessageBox.Warning)
                kutu.setWindowTitle("Kısmi Kesinleştirme")
                kutu.setText(f"{tamam} ders kesinleştirildi.\n\n" + "\n".join(hatalar))
                kutu.setInformativeText("Teknik hata kodları katlanır ayrıntıda tutulmaktadır.")
                kutu.setDetailedText("\n".join(teknik_detaylar))
                kutu.exec()
            else:
                QMessageBox.information(self, "Başarılı ✔", f"{tamam} ders danışman onayına gönderildi.")
        except Exception as e:
            hata_goster(self, "İşlem Hatası", e, {"limit": self.aktif_limit, "toplam": self.secili_akts})

    def sube_filtrele(self, metin: str):
        q = metin.strip().lower()
        for r in range(self.tbl_subeler.rowCount()):
            eslesti = any(
                q in (self.tbl_subeler.item(r, c).text().lower() if self.tbl_subeler.item(r, c) else "")
                for c in (0, 1, 4, 6)
            )
            self.tbl_subeler.setRowHidden(r, not eslesti)

    def haftalik_program_goster(self):
        from PySide6.QtWidgets import QDialog

        dlg = QDialog(self)
        dlg.setWindowTitle("📅 Haftalık Ders Programı ve Saat Çakışma Matrisi")
        dlg.resize(940, 580)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        baslik = QLabel("<b>Haftalık Ders Programı Zaman Çizelgesi (Seçilen & Açık Şubeler)</b>")
        baslik.setObjectName("SayfaBaslik")
        lay.addWidget(baslik)

        lejant = QHBoxLayout()
        for bg, fg, metin in [
            ("#15803D", "#FFFFFF", "✔ Kayıtlı / Onaylı Dersim"),
            ("#DBEAFE", "#2563EB", "🛒 Sepetteki Dersim"),
            ("#FEF3C7", "#92400E", "⏳ Açık Şube (Seçilebilir)"),
            ("#FEE2E2", "#B91C1C", "✖ Saat Çakışması (Çapraz Taralı)"),
        ]:
            lbl = QLabel(metin)
            lbl.setStyleSheet(
                f"background:{bg}; color:{fg}; padding:4px 10px; border-radius:6px; font-weight:700; font-size:9.5pt;"
            )
            lejant.addWidget(lbl)
        lejant.addStretch()
        lay.addLayout(lejant)

        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
        saatler = [f"{s}. Saat ({s+8:02d}:00)" for s in range(1, 9)]

        grid = QTableWidget(len(saatler), len(gunler))
        grid.setHorizontalHeaderLabels(gunler)
        grid.setVerticalHeaderLabels(saatler)
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        grid.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        grid.setEditTriggers(QTableWidget.NoEditTriggers)

        dolu_hucreler = {}
        for (g_idx, s_idx), (kod, durum) in self.dolu_slotlar.items():
            dolu_hucreler[(s_idx, g_idx)] = kod
            bg, fg, _ = rozet_formatla(durum)
            it = QTableWidgetItem(f"✔ {kod}\n({durum})")
            it.setBackground(QBrush(QColor(bg)))
            it.setForeground(QBrush(QColor(fg)))
            f = QFont()
            f.setBold(True)
            it.setFont(f)
            it.setTextAlignment(Qt.AlignCenter)
            grid.setItem(s_idx, g_idx, it)

        for s in self.subeler_veri:
            kod = s["ders_kod"]
            ad = s["ders_ad"]
            saat_metin = s["saatler"]
            for g_idx, s_idx, _ in saat_metni_coz(saat_metin):
                mevcut = dolu_hucreler.get((s_idx, g_idx))
                if mevcut and mevcut != kod:
                    it = QTableWidgetItem(f"✖ {mevcut} ⚡ {kod}\n(Çakışıyor)")
                    it.setBackground(QBrush(QColor("#B91C1C"), Qt.BDiagPattern))
                    it.setForeground(QBrush(QColor("#B91C1C")))
                    f = QFont()
                    f.setBold(True)
                    it.setFont(f)
                    it.setTextAlignment(Qt.AlignCenter)
                    grid.setItem(s_idx, g_idx, it)
                elif not grid.item(s_idx, g_idx):
                    it = QTableWidgetItem(f"{kod}\n{ad[:18]}")
                    it.setBackground(QBrush(QColor("#FEF3C7")))
                    it.setForeground(QBrush(QColor("#92400E")))
                    it.setTextAlignment(Qt.AlignCenter)
                    grid.setItem(s_idx, g_idx, it)

        lay.addWidget(grid, 1)
        dlg.exec()
