import os
import subprocess
from datetime import datetime
from collections import OrderedDict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QComboBox, QLineEdit, QMessageBox, QSplitter, QTabWidget,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QMarginsF, QSizeF, QPointF
from PySide6.QtGui import (
    QColor, QBrush, QPen, QFont, QPainter, QPolygonF,
    QTextDocument, QPdfWriter, QPageSize
)
from app.db import Veritabani, hata_coz, hata_goster, HATA_SABLONLARI
from app.stil import OLCULER, aktif_palet, rozet_formatla
from app.ekranlar.ogrenci_ana import bilgi_karti
from app.ekranlar.db_rontgen_ve_acid import AcidDeneGeriAlDialog


class DersDugumuItem(QGraphicsRectItem):
    """
    Önkoşul Haritası (QGraphicsScene) üzerindeki 120×44 px ders düğümü.
    Tıklanınca eksik önkoşul zincirini vurgular.
    """

    def __init__(self, ders_id: int, kod: str, ad: str, durum: str, x: float, y: float, tiklama_cb):
        super().__init__(0, 0, 120, 44)
        self.setPos(x, y)
        self.ders_id = ders_id
        self.kod = kod
        self.ad = ad
        self.durum = durum  # 'gecildi', 'alinabilir', 'kilitli'
        self.tiklama_cb = tiklama_cb
        self.vurgulu = False
        self.secili = False
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{kod} — {ad}\nDurum: {durum.upper()}\n(Eksik önkoşul zincirini görmek için tıklayın)")

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # Renk kuralı: Geçilen yeşil, alınabilir mavi çerçeve, kilitli gri; vurguluysa kırmızı çerçeve
        if self.vurgulu:
            bg = QColor("#FEE2E2")
            border = QColor("#B91C1C")
            fg = QColor("#B91C1C")
            kalinlik = 3.0
            ikon = "🔒"
        elif self.durum == "gecildi":
            bg = QColor("#DCFCE7")
            border = QColor("#15803D")
            fg = QColor("#15803D")
            kalinlik = 2.0
            ikon = "✔"
        elif self.durum == "alinabilir":
            bg = QColor("#FFFFFF")
            border = QColor("#2563EB")
            fg = QColor("#2563EB")
            kalinlik = 2.5
            ikon = "○"
        else:
            bg = QColor("#F1F5F9")
            border = QColor("#94A3B8")
            fg = QColor("#475569")
            kalinlik = 1.5
            ikon = "🔒"

        if self.secili:
            kalinlik = 3.5

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, kalinlik))
        painter.drawRoundedRect(r, 8, 8)

        # Üst satır: İkon + Ders Kodu
        f_kod = QFont()
        f_kod.setPointSize(9)
        f_kod.setBold(True)
        painter.setFont(f_kod)
        painter.setPen(fg)
        painter.drawText(r.adjusted(6, 4, -6, -20), Qt.AlignCenter, f"{ikon} {self.kod}")

        # Alt satır: Kısaltılmış Ders Adı
        f_ad = QFont()
        f_ad.setPointSize(7)
        painter.setFont(f_ad)
        painter.setPen(QColor("#334155") if self.durum != "kilitli" else QColor("#64748B"))
        kisa_ad = self.ad if len(self.ad) <= 18 else self.ad[:16] + "…"
        painter.drawText(r.adjusted(4, 22, -4, -4), Qt.AlignCenter, kisa_ad)

    def mousePressEvent(self, event):
        if self.tiklama_cb:
            self.tiklama_cb(self.ders_id)
        super().mousePressEvent(event)


class OnkosulHaritasiWidget(QWidget):
    """
    Tasarım Sistemi — Önkoşul Haritası:
    - Çizim: QGraphicsScene; sütun = önkoşul zincirindeki sıra.
    - Düğüm ölçüleri: 120×44 px, yatay boşluk 80 px, dikey boşluk 28 px.
    - Renkler: Geçilen yeşil, alınabilir mavi çerçeve, kilitli gri.
    - Etkileşim: Tıklayınca eksik önkoşul zinciri vurgulanır; kritik yol kalın çizgi.
    """

    DUGUM_GEN = 120
    DUGUM_YUK = 44
    YATAY_BOSLUK = 80
    DIKEY_BOSLUK = 28

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.dersler: dict[int, dict] = {}
        self.onkosullar: list[dict] = []
        self.dugum_itemler: dict[int, DersDugumuItem] = {}
        self.kritik_kenarlar: set[tuple[int, int]] = set()
        self.secili_ders_id: int | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Üst lejant ve açıklama
        ust = QHBoxLayout()
        for bg, border, fg, metin in [
            ("#DCFCE7", "#15803D", "#15803D", "✔ Geçilen (Yeşil)"),
            ("#FFFFFF", "#2563EB", "#2563EB", "○ Alınabilir (Mavi Çerçeve)"),
            ("#F1F5F9", "#94A3B8", "#475569", "🔒 Kilitli (Gri)"),
            ("#FEE2E2", "#B91C1C", "#B91C1C", "⚡ Eksik Önkoşul Zinciri (Tıklayınca)"),
        ]:
            lbl = QLabel(metin)
            lbl.setStyleSheet(
                f"background:{bg}; color:{fg}; border:2px solid {border}; "
                "border-radius:6px; padding:3px 10px; font-weight:700; font-size:9pt;"
            )
            ust.addWidget(lbl)

        lbl_kritik = QLabel("━━ Kritik Yol (Kalın Çizgi)")
        lbl_kritik.setStyleSheet("color:#12355B; font-weight:800; font-size:9pt; padding-left:8px;")
        ust.addWidget(lbl_kritik)
        ust.addStretch()

        btn_sifirla = QPushButton("Vurguyu Temizle")
        btn_sifirla.setObjectName("IkincilBtn")
        btn_sifirla.clicked.connect(lambda: self.dugum_tiklandi(None))
        ust.addWidget(btn_sifirla)
        lay.addLayout(ust)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.view.setMinimumHeight(290)
        lay.addWidget(self.view, 1)

        self.lbl_etkilesim = QLabel(
            "💡 Bir ders düğümüne tıkladığınızda eksik önkoşul zinciri grafikte vurgulanır ve kullanıcı dilinde açıklanır."
        )
        self.lbl_etkilesim.setStyleSheet(
            "background-color: #EFF6FF; color: #1E3A8A; border: 1px solid #BFDBFE; "
            "border-radius: 6px; padding: 8px 12px; font-weight: 600;"
        )
        lay.addWidget(self.lbl_etkilesim)

    def yukle(self):
        ders_satirlari = self.db.sorgula(
            """SELECT d.ders_id, d.kod, d.ad, d.akts, md.donem_no, md.tur
                 FROM ogrenci o
                 JOIN mufredat_ders md ON md.mufredat_id = o.mufredat_id
                 JOIN ders d ON d.ders_id = md.ders_id
                WHERE o.kisi_id = fn_oturum_kisi_id()
                ORDER BY md.donem_no, d.kod"""
        )
        onkosul_satirlari = self.db.sorgula(
            """SELECT ok.ders_id, ok.onkosul_ders_id, ok.min_harf,
                      d_onk.kod AS onkosul_kod, h.katsayi AS min_katsayi
                 FROM onkosul ok
                 JOIN ders d_onk ON d_onk.ders_id = ok.onkosul_ders_id
                 JOIN harf_notu_aralik h ON h.harf = ok.min_harf"""
        )
        transkript = self.db.sorgula("SELECT * FROM v_transkript")

        gecilen_katsayi: dict[str, float] = {}
        for t in transkript:
            if t.get("durum") == "gecti":
                kod = t.get("kod") or t.get("ders_kodu")
                kat = float(t.get("katsayi") or 2.0)
                gecilen_katsayi[kod] = max(gecilen_katsayi.get(kod, 0.0), kat)

        self.dersler = {d["ders_id"]: dict(d) for d in ders_satirlari}
        self.onkosullar = [
            o for o in onkosul_satirlari
            if o["ders_id"] in self.dersler and o["onkosul_ders_id"] in self.dersler
        ]

        # Önkoşul haritası: her dersin önkoşulları
        onk_map: dict[int, list[dict]] = {did: [] for did in self.dersler}
        ardil_map: dict[int, list[int]] = {did: [] for did in self.dersler}
        for o in self.onkosullar:
            onk_map[o["ders_id"]].append(o)
            ardil_map[o["onkosul_ders_id"]].append(o["ders_id"])

        # Her dersin durumunu ('gecildi', 'alinabilir', 'kilitli') belirle
        for did, d in self.dersler.items():
            kod = d["kod"]
            if kod in gecilen_katsayi:
                d["durum"] = "gecildi"
            else:
                eksik_var = False
                for o in onk_map[did]:
                    onk_kod = o["onkosul_kod"]
                    min_k = float(o["min_katsayi"] or 1.0)
                    if onk_kod not in gecilen_katsayi or gecilen_katsayi[onk_kod] < min_k:
                        eksik_var = True
                        break
                d["durum"] = "kilitli" if eksik_var else "alinabilir"

        # Sütun = önkoşul zincirindeki sıra (0, 1, 2, ...)
        zincir_sira: dict[int, int] = {}

        def sira_hesapla(did: int, ziyaret: set[int]) -> int:
            if did in zincir_sira:
                return zincir_sira[did]
            if did in ziyaret:
                return 0
            ziyaret.add(did)
            onler = onk_map.get(did, [])
            if not onler:
                zincir_sira[did] = 0
            else:
                zincir_sira[did] = 1 + max(sira_hesapla(o["onkosul_ders_id"], ziyaret) for o in onler)
            return zincir_sira[did]

        for did in self.dersler:
            sira_hesapla(did, set())

        # Kritik yol (en uzun önkoşul zinciri) hesaplama
        ileri_uzunluk: dict[int, int] = {}
        ileri_secim: dict[int, int | None] = {}

        def ileri_hesapla(did: int, ziyaret: set[int]) -> int:
            if did in ileri_uzunluk:
                return ileri_uzunluk[did]
            if did in ziyaret:
                return 1
            ziyaret.add(did)
            ardillar = ardil_map.get(did, [])
            if not ardillar:
                ileri_uzunluk[did] = 1
                ileri_secim[did] = None
            else:
                en_iyi_ardil = max(ardillar, key=lambda a: ileri_hesapla(a, set(ziyaret)))
                ileri_uzunluk[did] = 1 + ileri_hesapla(en_iyi_ardil, set(ziyaret))
                ileri_secim[did] = en_iyi_ardil
            return ileri_uzunluk[did]

        for did in self.dersler:
            ileri_hesapla(did, set())

        self.kritik_kenarlar.clear()
        if ileri_uzunluk:
            max_uz = max(ileri_uzunluk.values())
            if max_uz > 1:
                for bas_id, uz in ileri_uzunluk.items():
                    if uz == max_uz and zincir_sira.get(bas_id, 0) == 0:
                        cur = bas_id
                        while ileri_secim.get(cur) is not None:
                            nxt = ileri_secim[cur]
                            self.kritik_kenarlar.add((cur, nxt))
                            cur = nxt

        # Sütunlara göre düğüm konumlarını ata (120×44 px, yatay 80 px, dikey 28 px)
        sutun_gruplari: dict[int, list[int]] = {}
        for did, sira in zincir_sira.items():
            sutun_gruplari.setdefault(sira, []).append(did)

        self.konumlar: dict[int, tuple[float, float]] = {}
        adim_x = self.DUGUM_GEN + self.YATAY_BOSLUK  # 120 + 80 = 200 px
        adim_y = self.DUGUM_YUK + self.DIKEY_BOSLUK  # 44 + 28 = 72 px

        for sira in sorted(sutun_gruplari.keys()):
            d_list = sorted(sutun_gruplari[sira], key=lambda x: self.dersler[x]["kod"])
            for idx, did in enumerate(d_list):
                x = 30 + sira * adim_x
                y = 44 + idx * adim_y
                self.konumlar[did] = (x, y)

        self.onk_map = onk_map
        self.gecilen_katsayi = gecilen_katsayi
        self._sahneyi_ciz(vurgulu_dugumler=set(), vurgulu_kenarlar=set())

    def _eksik_zincir_bul(self, hedef_id: int) -> tuple[set[int], set[tuple[int, int]], list[str]]:
        dugumler: set[int] = set()
        kenarlar: set[tuple[int, int]] = set()
        mesajlar: list[str] = []

        def gez(did: int, ziyaret: set[int]):
            if did in ziyaret:
                return
            ziyaret.add(did)
            ders_kod = self.dersler[did]["kod"]
            for o in self.onk_map.get(did, []):
                onk_id = o["onkosul_ders_id"]
                onk_kod = o["onkosul_kod"]
                min_harf = o["min_harf"]
                min_k = float(o["min_katsayi"] or 1.0)
                if onk_kod not in self.gecilen_katsayi or self.gecilen_katsayi[onk_kod] < min_k:
                    dugumler.add(onk_id)
                    dugumler.add(did)
                    kenarlar.add((onk_id, did))
                    m_str = HATA_SABLONLARI["ONKOSUL_EKSIK"].format(
                        ders=ders_kod, onkosul=onk_kod, harf=min_harf
                    )
                    if m_str not in mesajlar:
                        mesajlar.append(m_str)
                    gez(onk_id, ziyaret)

        gez(hedef_id, set())
        return dugumler, kenarlar, mesajlar

    def dugum_tiklandi(self, ders_id: int | None):
        self.secili_ders_id = ders_id
        if ders_id is None or ders_id not in self.dersler:
            self.lbl_etkilesim.setText(
                "💡 Bir ders düğümüne tıkladığınızda eksik önkoşul zinciri grafikte vurgulanır ve kullanıcı dilinde açıklanır."
            )
            self.lbl_etkilesim.setStyleSheet(
                "background-color: #EFF6FF; color: #1E3A8A; border: 1px solid #BFDBFE; "
                "border-radius: 6px; padding: 8px 12px; font-weight: 600;"
            )
            self._sahneyi_ciz(set(), set())
            return

        d = self.dersler[ders_id]
        v_dugumler, v_kenarlar, mesajlar = self._eksik_zincir_bul(ders_id)
        if mesajlar:
            self.lbl_etkilesim.setText("🔒  " + "  |  ".join(mesajlar))
            self.lbl_etkilesim.setStyleSheet(
                "background-color: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; "
                "border-radius: 6px; padding: 8px 12px; font-weight: 700;"
            )
        elif d["durum"] == "gecildi":
            self.lbl_etkilesim.setText(f"✔  {d['kod']} ({d['ad']}) dersi başarıyla geçilmiş.")
            self.lbl_etkilesim.setStyleSheet(
                "background-color: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; "
                "border-radius: 6px; padding: 8px 12px; font-weight: 700;"
            )
        else:
            self.lbl_etkilesim.setText(
                f"○  {d['kod']} ({d['ad']}) dersinin tüm önkoşulları tamamlanmış; bu dönem alınabilir."
            )
            self.lbl_etkilesim.setStyleSheet(
                "background-color: #DBEAFE; color: #2563EB; border: 1px solid #93C5FD; "
                "border-radius: 6px; padding: 8px 12px; font-weight: 700;"
            )
        self._sahneyi_ciz(v_dugumler, v_kenarlar)

    def _sahneyi_ciz(self, vurgulu_dugumler: set[int], vurgulu_kenarlar: set[tuple[int, int]]):
        self.scene.clear()
        self.dugum_itemler.clear()

        # Sütun başlıklarını çiz
        max_sira = 0
        for did, (x, _) in self.konumlar.items():
            sira = int(round((x - 30) / (self.DUGUM_GEN + self.YATAY_BOSLUK)))
            max_sira = max(max_sira, sira)

        for sira in range(max_sira + 1):
            x = 30 + sira * (self.DUGUM_GEN + self.YATAY_BOSLUK)
            baslik_item = self.scene.addText(f"{sira + 1}. Kademe (Zincir Sırası)")
            f = QFont()
            f.setPointSize(8)
            f.setBold(True)
            baslik_item.setFont(f)
            baslik_item.setDefaultTextColor(QColor("#475569"))
            baslik_item.setPos(x + 4, 10)

        # Önce kenarları (okları) çiz
        for o in self.onkosullar:
            u = o["onkosul_ders_id"]
            v = o["ders_id"]
            if u not in self.konumlar or v not in self.konumlar:
                continue
            ux, uy = self.konumlar[u]
            vx, vy = self.konumlar[v]
            p1 = QPointF(ux + self.DUGUM_GEN, uy + self.DUGUM_YUK / 2)
            p2 = QPointF(vx, vy + self.DUGUM_YUK / 2)

            if (u, v) in vurgulu_kenarlar:
                kalem = QPen(QColor("#B91C1C"), 3.5)
                ok_renk = QColor("#B91C1C")
            elif (u, v) in self.kritik_kenarlar:
                # Kritik yol kalın çizgi
                kalem = QPen(QColor("#12355B"), 3.2)
                ok_renk = QColor("#12355B")
            else:
                kalem = QPen(QColor("#94A3B8"), 1.6)
                ok_renk = QColor("#94A3B8")

            self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), kalem)

            # Ok ucu
            ok = QPolygonF([
                p2,
                QPointF(p2.x() - 8, p2.y() - 4),
                QPointF(p2.x() - 8, p2.y() + 4),
            ])
            self.scene.addPolygon(ok, QPen(ok_renk), QBrush(ok_renk))

        # Düğümleri (120×44 px) çiz
        for did, d in self.dersler.items():
            x, y = self.konumlar[did]
            item = DersDugumuItem(
                ders_id=did,
                kod=d["kod"],
                ad=d["ad"],
                durum=d["durum"],
                x=x,
                y=y,
                tiklama_cb=self.dugum_tiklandi,
            )
            item.vurgulu = did in vurgulu_dugumler
            item.secili = did == self.secili_ders_id
            self.scene.addItem(item)
            self.dugum_itemler[did] = item

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20, -15, 20, 20))


class OgrenciKisiselVeTakvim(QWidget):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 20)
        self.lay.setSpacing(14)
        self.yenile()

    def yenile(self):
        pal = aktif_palet()
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
        lbl_kb.setStyleSheet(f"color: {pal['vurgu']}; font-size: 12pt; font-weight: 700;")
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
            bg = pal["zebra_zemin"] if i % 2 == 0 else pal["kart_zemin"]
            lk = QLabel(k)
            lk.setStyleSheet(f"background:{bg}; color:{pal['ikincil_metin']}; font-weight:600; padding:7px 10px; border:1px solid {pal['kenarlik']};")
            lv = QLabel(v)
            lv.setStyleSheet(f"background:{bg}; color:{pal['metin']}; font-weight:600; padding:7px 10px; border:1px solid {pal['kenarlik']};")
            g1.addWidget(lk, i, 0)
            g1.addWidget(lv, i, 1)
        k_lay.addLayout(g1)
        ust_lay.addWidget(k_kart, 1)

        d_kart = QFrame()
        d_kart.setObjectName("PortalKart")
        d_lay = QVBoxLayout(d_kart)
        d_lay.setContentsMargins(18, 16, 18, 16)
        lbl_db = QLabel("💬  Akademik Danışman Bilgileri")
        lbl_db.setStyleSheet(f"color: {pal['vurgu']}; font-size: 12pt; font-weight: 700;")
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
            bg = pal["zebra_zemin"] if i % 2 == 0 else pal["kart_zemin"]
            lk = QLabel(k)
            lk.setStyleSheet(f"background:{bg}; color:{pal['ikincil_metin']}; font-weight:600; padding:7px 10px; border:1px solid {pal['kenarlik']};")
            lv = QLabel(v)
            lv.setStyleSheet(f"background:{bg}; color:{pal['metin']}; font-weight:600; padding:7px 10px; border:1px solid {pal['kenarlik']};")
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
        lbl_tb.setStyleSheet(f"color: {pal['vurgu']}; font-size: 12pt; font-weight: 700;")
        t_lay.addWidget(lbl_tb)

        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Yıl", "Dönem", "Kayıt Başlangıç", "Kayıt Bitiş", "Ekle-Bırak Bitiş"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
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
        btn_yenile = QPushButton("↻  Yenile (F5)")
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
        self.tbl_notlar.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
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
        self.tbl_tr.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
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
        self.lbl_kod.setStyleSheet("font-weight: 700; color: #2563EB;")
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

        self.kart_lay.addWidget(bilgi_karti("Genel Not Ortalaması", str(ozet.get("gno") or "-"), "A+", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Dönem Not Ortalaması", str(ozet.get("dno") or "-"), "📊", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("Geçilen Toplam AKTS", f"{ozet.get('gecilen_akts', 0)} AKTS", "±÷", "#15803D"))
        self.kart_lay.addWidget(bilgi_karti("Transkript Ders Sayısı", f"{len(tr)} Ders", "📚", "#2563EB"))

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
            durum_str = "✔ Geçti" if r["durum"] == "gecti" else ("✖ Kaldı" if r["durum"] == "kaldi" else str(r["durum"]))
            durum_item = QTableWidgetItem(durum_str)
            if r["durum"] == "gecti":
                harf_item.setBackground(QBrush(QColor("#DCFCE7")))
                harf_item.setForeground(QBrush(QColor("#15803D")))
                durum_item.setBackground(QBrush(QColor("#DCFCE7")))
                durum_item.setForeground(QBrush(QColor("#15803D")))
            elif r["durum"] == "kaldi":
                harf_item.setBackground(QBrush(QColor("#FEE2E2")))
                harf_item.setForeground(QBrush(QColor("#B91C1C")))
                durum_item.setBackground(QBrush(QColor("#FEE2E2")))
                durum_item.setForeground(QBrush(QColor("#B91C1C")))
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
            hata_goster(self, "Hata", e)

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
                    self, "Belge Geçerli ✔",
                    f"Öğrenci No: {r['ogrenci_no']}\nBelge Türü: {r['tur']}\n"
                    f"Üretim Zamanı: {r['uretim_zamani']}\n\nSHA-256 İçerik Özeti güncel transkript ile EŞLEŞİYOR."
                )
            else:
                QMessageBox.critical(
                    self, "Bütünlük Bozulmuş ✖",
                    f"Öğrenci No: {r['ogrenci_no']}\nBelge üretildikten sonra transkript notları değişmiş!"
                )
        except Exception as e:
            hata_goster(self, "Hata", e)

    def transkript_indir(self):
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
        <table width="680" cellspacing="0" cellpadding="0" style="border-bottom: 2px solid #12355B; padding-bottom: 8px; margin-bottom: 10px;">
            <tr>
                <td width="460" valign="middle">
                    <div style="font-size: 12pt; font-weight: bold; color: #12355B;">T.C. YÜKSEKÖĞRETİM KURULU — ÖĞRENCİ BİLGİ SİSTEMİ</div>
                    <div style="font-size: 9.5pt; font-weight: bold; color: #334155; margin-top: 2px;">RESMİ NOT DÖKÜM BELGESİ (TRANSKRİPT)</div>
                </td>
                <td width="220" align="right" valign="middle" style="font-size: 8pt; color: #1e293b;">
                    <b>Belge Tarihi:</b> {tarih_str}<br>
                    <b>SHA-256 Doğrulama Kodu:</b> <span style="color:#12355B; font-weight:bold;">{kod}</span>
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
        baslik = QLabel("Mezuniyetime Ne Kaldı? — Önkoşul DAG Haritası, Müfredat Denetimi & ACID Simülasyonu")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        btn_acid = QPushButton("🧪  ACID 'Dene ve Geri Al' (ROLLBACK) Simülatörü")
        btn_acid.setObjectName("BirincilBtn")
        btn_acid.clicked.connect(lambda: AcidDeneGeriAlDialog(self.db, self).exec())
        ust.addWidget(btn_acid)

        btn_yenile = QPushButton("↻  Yenile (F5)")
        btn_yenile.setObjectName("IkincilBtn")
        btn_yenile.clicked.connect(self.yenile)
        ust.addWidget(btn_yenile)
        self.lay.addLayout(ust)

        self.kart_lay = QHBoxLayout()
        self.kart_lay.setSpacing(12)
        self.lay.addLayout(self.kart_lay)

        self.sekmeler = QTabWidget()

        # Sekme 1: İnteraktif Önkoşul DAG Haritası (QGraphicsScene)
        self.dag_harita = OnkosulHaritasiWidget(self.db)
        self.sekmeler.addTab(self.dag_harita, "🕸️  İnteraktif Önkoşul Haritası (QGraphicsScene)")

        # Sekme 2: Müfredat Grup Denetimi & Topolojik Plan Tabloları
        w_tablolar = QWidget()
        l_tab = QVBoxLayout(w_tablolar)
        l_tab.setContentsMargins(10, 10, 10, 10)
        l_tab.setSpacing(12)

        k1 = QFrame()
        k1.setObjectName("PortalKart")
        l1 = QVBoxLayout(k1)
        l1.setContentsMargins(14, 12, 14, 12)
        l1.addWidget(QLabel("<b>🎓 Müfredat ve Seçmeli Grup Denetimi (fn_mezuniyet_denetim_ben)</b>"))
        self.tbl_denetim = QTableWidget(0, 7)
        self.tbl_denetim.setHorizontalHeaderLabels(["Grup Adı", "Tür", "Min Ders", "Min AKTS", "Sayılan Ders", "Sayılan AKTS", "Durum / Eksik"])
        self.tbl_denetim.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_denetim.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_denetim.setEditTriggers(QTableWidget.NoEditTriggers)
        l1.addWidget(self.tbl_denetim)
        l_tab.addWidget(k1, 1)

        k2 = QFrame()
        k2.setObjectName("PortalKart")
        l2 = QVBoxLayout(k2)
        l2.setContentsMargins(14, 12, 14, 12)
        l2.addWidget(QLabel("<b>🗓️ Önkoşul DAG Topolojik Ders Planı (fn_ders_plani_ben)</b>"))
        self.tbl_plan = QTableWidget(0, 4)
        self.tbl_plan.setHorizontalHeaderLabels(["Önerilen Dönem Sırası", "Ders Kodu", "Ders Adı", "AKTS"])
        self.tbl_plan.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_plan.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_plan.setEditTriggers(QTableWidget.NoEditTriggers)
        l2.addWidget(self.tbl_plan)
        l_tab.addWidget(k2, 1)

        self.sekmeler.addTab(w_tablolar, "📋  Müfredat Grup Denetimi & Dönemlik Plan Tablosu")
        self.lay.addWidget(self.sekmeler, 1)

        self.yenile()

    def yenile(self):
        while self.kart_lay.count():
            it = self.kart_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        denetim = self.db.sorgula("SELECT * FROM fn_mezuniyet_denetim_ben()")
        plan = self.db.sorgula("SELECT * FROM fn_ders_plani_ben(30)")
        trans = self.db.sorgula("SELECT * FROM v_transkript")

        katsayi = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0}
        tp, ta, ga = 0.0, 0, 0
        for r in trans:
            ak = int(r.get("akts") or 0)
            h = r.get("harf")
            if h in katsayi:
                tp += ak * katsayi[h]
                ta += ak
            if r.get("durum") == "gecti":
                ga += ak
        gno = (tp / ta) if ta > 0 else 0.0
        eksik_var = any(d.get("durum") != "tamam" for d in denetim)
        max_donem = max([int(p.get("donem_sira") or p.get("onerilen_donem") or p.get("donem_no") or 1) for p in plan], default=0)

        self.kart_lay.addWidget(
            bilgi_karti("Mezuniyet Durumu", "Eksikler Var" if eksik_var else "Mezun Olabilir ✔", "🎓", "#B91C1C" if eksik_var else "#15803D")
        )
        self.kart_lay.addWidget(bilgi_karti("AKTS (Geçilen / Hedef)", f"{ga} / 240", "⚖️", "#2563EB"))
        self.kart_lay.addWidget(bilgi_karti("GNO (Mevcut / Min)", f"{gno:.2f} / 2.00", "🅰️", "#15803D"))
        self.kart_lay.addWidget(bilgi_karti("DAG Kritik Yol", f"{max_donem} Dönem", "🕸️", "#2563EB"))

        self.dag_harita.yukle()

        self.tbl_denetim.setRowCount(0)
        for d in denetim:
            r = self.tbl_denetim.rowCount()
            self.tbl_denetim.insertRow(r)
            self.tbl_denetim.setItem(r, 0, QTableWidgetItem(str(d.get("grup_ad") or "")))
            self.tbl_denetim.setItem(r, 1, QTableWidgetItem(str(d.get("tur") or "")))
            self.tbl_denetim.setItem(r, 2, QTableWidgetItem(str(d.get("min_ders") or 0)))
            self.tbl_denetim.setItem(r, 3, QTableWidgetItem(str(d.get("min_akts") or 0)))
            self.tbl_denetim.setItem(r, 4, QTableWidgetItem(str(d.get("sayilan_ders") or 0)))
            self.tbl_denetim.setItem(r, 5, QTableWidgetItem(str(d.get("sayilan_akts") or 0)))
            tamam_mi = d.get("durum") == "tamam" or d.get("tamam") is True
            eksik_metin = "✔ Tamam" if tamam_mi else f"✖ Eksik: {d.get('eksik') or d.get('eksik_aciklama') or ''}"
            it = QTableWidgetItem(eksik_metin)
            it.setBackground(QBrush(QColor("#DCFCE7" if tamam_mi else "#FEE2E2")))
            it.setForeground(QBrush(QColor("#15803D" if tamam_mi else "#B91C1C")))
            self.tbl_denetim.setItem(r, 6, it)

        self.tbl_plan.setRowCount(0)
        for p in plan:
            r = self.tbl_plan.rowCount()
            self.tbl_plan.insertRow(r)
            d_no = p.get("donem_sira") or p.get("onerilen_donem") or p.get("donem_no") or 1
            self.tbl_plan.setItem(r, 0, QTableWidgetItem(f"{d_no}. Dönem"))
            self.tbl_plan.setItem(r, 1, QTableWidgetItem(str(p.get("ders_kod") or p.get("kod") or "")))
            self.tbl_plan.setItem(r, 2, QTableWidgetItem(str(p.get("ders_ad") or p.get("ad") or "")))
            self.tbl_plan.setItem(r, 3, QTableWidgetItem(str(p.get("akts") or 0)))
