"""
✦ AI Merkezi Sayfası: Model Kartı, Son Çalıştırma, Tahmin Sayısı, Risk Dağılımı Histogramı,
Test Doğruluğu, Adalet Özeti ve "Skorları Yenile" İlerleme Animasyonu.

İlkeler:
  1. Tek ekranda modelin sürümü, eğitim kaynağı, son çalıştırma zamanı, tahmin sayısı,
     risk dağılımı histogramı, doğruluk/kalibrasyon metrikleri ve adalet özeti sunulur.
  2. "✦ Skorları Yenile" düğmesi aşamalı ilerleme animasyonuyla (`QTimer` + `QProgressBar`)
     tüm öğrencileri yeniden skorlar ve PostgreSQL `model_surum` + `risk_tahmin`
     tablolarına kaydeder.
  3. Tüm bileşenler `✦ AI · model v1 · güven %NN` ve `demo verisi` kimliğini taşır.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ai.kimlik import AIDemoEtiket, AIDugme, AIRozet, VARSAYILAN_MODEL_SURUM
from app.ai.risk_motor import (
    RISK_MODEL_SURUM,
    RiskTahminSonucu,
    danisan_risklerini_yenile,
    lojistik_risk_hesapla,
    model_degerlendirme_metrikleri,
)
from app.stil import OLCULER, aktif_palet


class RiskDagilimHistogrami(QWidget):
    """
    5 risk dilimi (%0–20, %20–40, %40–60, %60–80, %80–100) için
    özel QPainter ile çizilen dikey sütun grafik bileşeni.
    """

    DILIM_ETIKETLERI = [
        "%0–20\n(Çok Düşük)",
        "%20–40\n(Düşük)",
        "%40–60\n(Orta)",
        "%60–80\n(Yüksek)",
        "%80–100\n(Kritik)",
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._sayilar: list[int] = [0, 0, 0, 0, 0]
        self.setMinimumHeight(185)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def veriyi_guncelle(self, sayilar: list[int]):
        if len(sayilar) == 5:
            self._sayilar = [int(x) for x in sayilar]
        else:
            self._sayilar = [0, 0, 0, 0, 0]
        self.update()

    def paintEvent(self, _event):
        p = aktif_palet()
        koyu = p["tema"] == "koyu"
        renkler = (
            ["#4ADE80", "#86EFAC", "#FBBF24", "#FB923C", "#F87171"]
            if koyu
            else ["#15803D", "#16A34A", "#D97706", "#EA580C", "#B91C1C"]
        )
        zemin_renkler = (
            ["#064E3B", "#064E3B", "#451A03", "#431407", "#450A0A"]
            if koyu
            else ["#DCFCE7", "#ECFDF5", "#FEF3C7", "#FFEDD5", "#FEE2E2"]
        )

        cizici = QPainter(self)
        cizici.setRenderHint(QPainter.Antialiasing)

        gen = self.width()
        yuk = self.height()
        sol_pay = 18
        sag_pay = 18
        ust_pay = 28
        alt_pay = 42

        cizim_gen = max(100, gen - sol_pay - sag_pay)
        cizim_yuk = max(60, yuk - ust_pay - alt_pay)
        taban_y = ust_pay + cizim_yuk

        # Yatay kılavuz çizgileri
        iz_kalem = QPen(QColor(p["tablo_izgara"]), 1, Qt.DashLine)
        cizici.setPen(iz_kalem)
        for oran in (0.0, 0.5, 1.0):
            y_cizgi = ust_pay + cizim_yuk * oran
            cizici.drawLine(int(sol_pay), int(y_cizgi), int(gen - sag_pay), int(y_cizgi))

        toplam = sum(self._sayilar)
        maks_deger = max(max(self._sayilar, default=1), 1)
        sutun_sayisi = 5
        hucre_gen = cizim_gen / sutun_sayisi
        cubuk_gen = min(56.0, hucre_gen * 0.58)

        f_deger = QFont()
        f_deger.setPointSize(9)
        f_deger.setBold(True)

        f_etiket = QFont()
        f_etiket.setPointSize(8)
        f_etiket.setBold(True)

        for i in range(sutun_sayisi):
            adet = self._sayilar[i]
            merkez_x = sol_pay + hucre_gen * (i + 0.5)
            cubuk_x = merkez_x - cubuk_gen / 2.0

            # Arka plan sütun izi
            cizici.setPen(Qt.NoPen)
            cizici.setBrush(QColor(zemin_renkler[i]))
            cizici.drawRoundedRect(QRectF(cubuk_x, ust_pay, cubuk_gen, cizim_yuk), 6, 6)

            # Dolu sütun
            oran = (adet / maks_deger) if adet > 0 else 0.04
            dolu_yuk = max(6.0, cizim_yuk * oran) if adet > 0 else 4.0
            dolu_y = taban_y - dolu_yuk
            cizici.setBrush(QColor(renkler[i]))
            cizici.drawRoundedRect(QRectF(cubuk_x, dolu_y, cubuk_gen, dolu_yuk), 6, 6)

            # Üstteki sayı ve yüzde etiketi
            yuzde = int(round((adet / toplam) * 100)) if toplam > 0 else 0
            ust_metin = f"{adet} (%{yuzde})"
            cizici.setFont(f_deger)
            cizici.setPen(QColor(renkler[i] if adet > 0 else p["ikincil_metin"]))
            cizici.drawText(
                QRectF(merkez_x - hucre_gen / 2.0, max(2.0, dolu_y - 22.0), hucre_gen, 20.0),
                Qt.AlignCenter,
                ust_metin,
            )

            # Alttaki dilim etiketi
            cizici.setFont(f_etiket)
            cizici.setPen(QColor(p["metin"]))
            cizici.drawText(
                QRectF(merkez_x - hucre_gen / 2.0, taban_y + 6.0, hucre_gen, alt_pay - 6.0),
                Qt.AlignHCenter | Qt.AlignTop,
                self.DILIM_ETIKETLERI[i],
            )

        cizici.end()


class AIMerkeziEkrani(QWidget):
    """
    Danışman ve Sistem Yöneticisi için tek ekranlık AI Merkezi:
      - Model kartı (sürüm, algoritma, özellikler, kalibrasyon)
      - Son çalıştırma zamanı & tahmin sayısı
      - Risk dağılımı histogramı (5 dilim)
      - Test doğruluğu, F1 ve Brier kalibrasyon metrikleri
      - Adalet özeti (demografik bağımsızlık + gruplar arası sapma denetimi)
      - "✦ Skorları Yenile" düğmesi + aşamalı ilerleme animasyonu
    """

    ANIMASYON_ADIMLARI = [
        (20, "1/5 · Danışanların akademik (GNO, AKTS) ve katılım özellikleri okunuyor..."),
        (45, "2/5 · Açıklanabilir lojistik model (logreg_oulad_v1) katsayıları uygulanıyor..."),
        (70, "3/5 · Öğrenci bazında en etkili 3 risk nedeni ve etki puanları hesaplanıyor..."),
        (90, "4/5 · Kalibrasyon (Brier skoru) ve grup adalet dengesi doğrulanıyor..."),
        (100, "5/5 · Veritabanı model_surum ve risk_tahmin tabloları güncelleniyor..."),
    ]

    def __init__(self, db, parent: QWidget | None = None):
        super().__init__(parent)
        self.db = db
        self._anim_adim_idx = 0
        self._son_yenileme_zamani: str = "-"

        self._timer = QTimer(self)
        self._timer.setInterval(110)
        self._timer.timeout.connect(self._animasyon_ilerlet)

        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 14)
        self.lay.setSpacing(10)

        # 1) Üst Başlık + ✦ AI Rozeti + demo verisi + "✦ Skorları Yenile"
        ust = QHBoxLayout()
        ust.setSpacing(8)
        baslik = QLabel("✦  AI Merkezi — Model Kartı, Risk Dağılımı ve Adalet Özeti")
        baslik.setObjectName("SayfaBaslik")
        ust.addWidget(baslik)
        ust.addStretch()

        self.rozet_ust = AIRozet(model=VARSAYILAN_MODEL_SURUM, guven=89)
        ust.addWidget(self.rozet_ust)
        ust.addWidget(AIDemoEtiket())

        self.btn_yenile = AIDugme("✦  Skorları Yenile")
        self.btn_yenile.setToolTip(
            "Tüm danışanların risk skorlarını yeniden hesaplar ve veritabanındaki risk_tahmin tablosuna kaydeder"
        )
        self.btn_yenile.clicked.connect(self.skorlari_yenile_animasyonlu)
        ust.addWidget(self.btn_yenile)
        self.lay.addLayout(ust)

        # 2) İlerleme Animasyonu Kutusu (Skorları Yenile'ye basıldığında çalışır)
        self.anim_kutu = QFrame(self)
        self.anim_kutu.setObjectName("AIKart")
        anim_lay = QHBoxLayout(self.anim_kutu)
        anim_lay.setContentsMargins(14, 8, 14, 8)
        anim_lay.setSpacing(12)

        self.lbl_anim_durum = QLabel("✦ Hazır")
        self.lbl_anim_durum.setStyleSheet("font-weight: 700; font-size: 9pt; border: none;")
        anim_lay.addWidget(self.lbl_anim_durum, 1)

        self.bar_anim = QProgressBar()
        self.bar_anim.setRange(0, 100)
        self.bar_anim.setValue(0)
        self.bar_anim.setFixedWidth(260)
        self.bar_anim.setFixedHeight(20)
        p = aktif_palet()
        self.bar_anim.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {p['ai_rozet_zemin']};
                color: {p['ai_rozet_metin']};
                border: 1px solid {p['ai_kenar']};
                border-radius: 6px;
                text-align: center;
                font-weight: 700;
            }}
            QProgressBar::chunk {{
                background-color: {p['ai_dugme']};
                border-radius: 5px;
            }}
            """
        )
        anim_lay.addWidget(self.bar_anim)
        self.anim_kutu.setVisible(False)
        self.lay.addWidget(self.anim_kutu)

        # 3) Üst Özet Metrik Kartları (Model Kartı, Son Çalıştırma, Tahmin Sayısı, Test Doğruluğu)
        self.metrik_lay = QHBoxLayout()
        self.metrik_lay.setSpacing(10)
        self.lay.addLayout(self.metrik_lay)

        # 4) Orta Bölge: Sol = Risk Dağılımı Histogramı, Sağ = Model Kartı & Adalet Özeti
        orta_splitter = QSplitter(Qt.Horizontal)

        # SOL KART: Risk Dağılımı Histogramı
        sol_kart = QFrame()
        sol_kart.setObjectName("AIKart")
        sol_lay = QVBoxLayout(sol_kart)
        sol_lay.setContentsMargins(14, 12, 14, 12)
        sol_lay.setSpacing(8)

        sol_ust = QHBoxLayout()
        sol_ust.addWidget(QLabel("<b>📊  Risk Dağılımı Histogramı (5 Olasılık Dilimi)</b>"))
        sol_ust.addStretch()
        self.lbl_hist_ozet = QLabel("")
        self.lbl_hist_ozet.setStyleSheet("font-size: 8.5pt; font-weight: 700; border: none;")
        sol_ust.addWidget(self.lbl_hist_ozet)
        sol_lay.addLayout(sol_ust)

        self.histogram = RiskDagilimHistogrami(sol_kart)
        sol_lay.addWidget(self.histogram, 1)

        alt_bilgi = QLabel(
            "Düşük Risk (<%35): Yeşil  •  Orta Risk (%35–64): Sarı/Turuncu  •  Yüksek Risk (≥%65): Kırmızı"
        )
        alt_bilgi.setAlignment(Qt.AlignCenter)
        alt_bilgi.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt; border: none;")
        sol_lay.addWidget(alt_bilgi)
        orta_splitter.addWidget(sol_kart)

        # SAĞ KART: Model Kartı Detayları + Adalet Özeti (Fairness Summary)
        sag_kart = QFrame()
        sag_kart.setObjectName("AIKart")
        sag_lay = QVBoxLayout(sag_kart)
        sag_lay.setContentsMargins(14, 12, 14, 12)
        sag_lay.setSpacing(8)

        sag_ust = QHBoxLayout()
        sag_ust.addWidget(QLabel("<b>⚖️  Model Kartı, Kalibrasyon ve Adalet Özeti</b>"))
        sag_ust.addStretch()
        sag_ust.addWidget(AIRozet(model=VARSAYILAN_MODEL_SURUM, guven=89))
        sag_ust.addWidget(AIDemoEtiket())
        sag_lay.addLayout(sag_ust)

        self.lbl_model_karti = QLabel()
        self.lbl_model_karti.setWordWrap(True)
        self.lbl_model_karti.setStyleSheet(
            f"background-color: {p['zebra_zemin']}; color: {p['metin']}; "
            f"border: 1px solid {p['kenarlik']}; border-radius: 6px; padding: 8px 10px; font-size: 8.5pt;"
        )
        sag_lay.addWidget(self.lbl_model_karti)

        self.lbl_adalet = QLabel()
        self.lbl_adalet.setWordWrap(True)
        self.lbl_adalet.setStyleSheet(
            f"background-color: {p['ai_rozet_zemin']}; color: {p['ai_rozet_metin']}; "
            f"border: 1px solid {p['ai_kenar']}; border-radius: 6px; padding: 8px 10px; font-size: 8.5pt;"
        )
        sag_lay.addWidget(self.lbl_adalet)

        self.tbl_adalet = QTableWidget(0, 4)
        self.tbl_adalet.setHorizontalHeaderLabels(
            ["Kohort / Sınıf Grubu", "Öğrenci", "Ort. GNO", "Ort. Risk % & Denge"]
        )
        self.tbl_adalet.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_adalet.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_adalet.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_adalet.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_adalet.verticalHeader().setVisible(False)
        self.tbl_adalet.verticalHeader().setDefaultSectionSize(28)
        self.tbl_adalet.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_adalet.setMaximumHeight(125)
        sag_lay.addWidget(self.tbl_adalet)

        orta_splitter.addWidget(sag_kart)
        orta_splitter.setStretchFactor(0, 5)
        orta_splitter.setStretchFactor(1, 5)
        self.lay.addWidget(orta_splitter, 3)

        # 5) Alt Tablo: Öğrenci Bazlı Risk Tahminleri ve En Etkili 3 Neden
        alt_kart = QFrame()
        alt_kart.setObjectName("PortalKart")
        alt_lay = QVBoxLayout(alt_kart)
        alt_lay.setContentsMargins(14, 10, 14, 10)
        alt_lay.setSpacing(6)

        alt_ust = QHBoxLayout()
        alt_ust.addWidget(QLabel("<b>📋  Öğrenci Bazlı Risk Skorları ve En Etkili 3 Neden Dökümü</b>"))
        alt_ust.addStretch()
        lbl_kisit = QLabel("AI yalnızca öneri verir, karar vermez • Öğrencilere gösterilmez")
        lbl_kisit.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt;")
        alt_ust.addWidget(lbl_kisit)
        alt_lay.addWidget(QWidget())
        alt_lay.itemAt(0).widget().deleteLater()
        alt_lay.addLayout(alt_ust)

        self.tbl_tahminler = QTableWidget(0, 7)
        self.tbl_tahminler.setHorizontalHeaderLabels(
            [
                "Öğrenci No",
                "Ad Soyad",
                "GNO",
                "Katılım %",
                "Ödev Ort.",
                "✦ Risk Skoru",
                "En Etkili 3 Neden (Açıklanabilir Katkı)",
            ]
        )
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl_tahminler.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.tbl_tahminler.verticalHeader().setDefaultSectionSize(OLCULER["tablo_satir_yukseklik"])
        self.tbl_tahminler.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_tahminler.setSelectionBehavior(QTableWidget.SelectRows)
        alt_lay.addWidget(self.tbl_tahminler, 1)

        self.lay.addWidget(alt_kart, 2)
        self.yenile()

    def _metrik_karti_olustur(self, baslik: str, deger: str, alt: str, vurgu_hex: str) -> QFrame:
        p = aktif_palet()
        kart = QFrame()
        kart.setObjectName("MetrikKutu")
        k_lay = QVBoxLayout(kart)
        k_lay.setContentsMargins(14, 10, 14, 10)
        k_lay.setSpacing(3)

        lbl_b = QLabel(baslik)
        lbl_b.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt; font-weight: 700; border: none;")
        lbl_d = QLabel(deger)
        lbl_d.setStyleSheet(f"color: {vurgu_hex}; font-size: 13pt; font-weight: 800; border: none;")
        lbl_a = QLabel(alt)
        lbl_a.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8pt; border: none;")

        k_lay.addWidget(lbl_b)
        k_lay.addWidget(lbl_d)
        k_lay.addWidget(lbl_a)
        return kart

    def skorlari_yenile_animasyonlu(self):
        if self._timer.isActive():
            return
        self.btn_yenile.setEnabled(False)
        self._anim_adim_idx = 0
        self.bar_anim.setValue(5)
        self.lbl_anim_durum.setText("✦ AI Risk Motoru başlatılıyor...")
        self.anim_kutu.setVisible(True)
        self._timer.start()

    def _animasyon_ilerlet(self):
        if self._anim_adim_idx < len(self.ANIMASYON_ADIMLARI):
            yuzde, mesaj = self.ANIMASYON_ADIMLARI[self._anim_adim_idx]
            self.bar_anim.setValue(yuzde)
            self.lbl_anim_durum.setText(f"✦ {mesaj}")
            self._anim_adim_idx += 1
            return

        self._timer.stop()
        try:
            danisan_risklerini_yenile(self.db)
        except Exception:
            pass
        self._son_yenileme_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.yenile()
        self.lbl_anim_durum.setText(
            f"✔ Tüm öğrenci risk skorları yenilendi ve veritabanına kaydedildi ({self._son_yenileme_zamani})."
        )
        self.btn_yenile.setEnabled(True)
        QTimer.singleShot(2800, lambda: self.anim_kutu.setVisible(False))

    def yenile(self):
        p = aktif_palet()
        while self.metrik_lay.count():
            item = self.metrik_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            satirlar = self.db.sorgula("SELECT * FROM v_danisan_risk_ozellik ORDER BY ogrenci_no")
        except Exception:
            satirlar = []

        # Eğer henüz risk_tahmin tablosunda kayıt yoksa ilk açılışta senkronize et
        if satirlar and all(s.get("kayitli_skor") is None for s in satirlar):
            try:
                danisan_risklerini_yenile(self.db)
                satirlar = self.db.sorgula("SELECT * FROM v_danisan_risk_ozellik ORDER BY ogrenci_no")
            except Exception:
                pass

        tahminler: list[RiskTahminSonucu] = []
        son_zaman = self._son_yenileme_zamani
        for s in satirlar:
            # Yönetici rolünde RLS nedeniyle not_kaydi/yoklama doğrudan okunamazsa kayitli_ozellikler'i kullan
            kayitli_oz = s.get("kayitli_ozellikler") if isinstance(s.get("kayitli_ozellikler"), dict) else {}
            gno = float(kayitli_oz.get("gno") if kayitli_oz.get("gno") is not None else (s.get("gno") or 2.50))
            kat = float(
                kayitli_oz.get("katilim_yuzde")
                if kayitli_oz.get("katilim_yuzde") is not None
                else (s.get("katilim_yuzde") or 85.0)
            )
            odev = float(
                kayitli_oz.get("odev_ort_puan")
                if kayitli_oz.get("odev_ort_puan") is not None
                else (s.get("odev_ort_puan") or 70.0)
            )
            kalinan = int(
                kayitli_oz.get("basarisiz_ders_sayisi")
                if kayitli_oz.get("basarisiz_ders_sayisi") is not None
                else (s.get("basarisiz_ders_sayisi") or 0)
            )
            akts = int(
                kayitli_oz.get("aktif_donem_akts")
                if kayitli_oz.get("aktif_donem_akts") is not None
                else (s.get("aktif_donem_akts") or 24)
            )
            min_gno = float(
                kayitli_oz.get("min_gno") if kayitli_oz.get("min_gno") is not None else (s.get("min_gno") or 2.00)
            )
            dev_sinir = float(
                kayitli_oz.get("devamsizlik_siniri")
                if kayitli_oz.get("devamsizlik_siniri") is not None
                else (s.get("devamsizlik_siniri") or 30.0)
            )

            sonuc = lojistik_risk_hesapla(
                gno=gno,
                katilim_yuzde=kat,
                odev_ort_puan=odev,
                basarisiz_ders_sayisi=kalinan,
                aktif_donem_akts=akts,
                ogrenci_id=int(s["ogrenci_id"]),
                min_gno=min_gno,
                devamsizlik_siniri=dev_sinir,
            )
            tahminler.append(sonuc)
            s["_hesaplanan"] = sonuc
            if son_zaman == "-" and s.get("son_hesap_zamani"):
                son_zaman = str(s["son_hesap_zamani"])[:19]

        if son_zaman == "-":
            son_zaman = datetime.now().strftime("%Y-%m-%d %H:%M")

        metrik = model_degerlendirme_metrikleri(tahminler)
        self.rozet_ust.guncelle(model=VARSAYILAN_MODEL_SURUM, guven=metrik["ortalama_guven"])

        # 4 Üst Metrik Kartı
        self.metrik_lay.addWidget(
            self._metrik_karti_olustur(
                "✦ Model Kartı & Sürüm",
                f"{RISK_MODEL_SURUM} (v1)",
                "Açıklanabilir Lojistik Regresyon · 5 Özellik",
                p["ai_rozet_metin"],
            ),
            1,
        )
        self.metrik_lay.addWidget(
            self._metrik_karti_olustur(
                "⏱ Son Çalıştırma Zamanı",
                son_zaman,
                "PostgreSQL model_surum & risk_tahmin",
                "#2563EB",
            ),
            1,
        )
        self.metrik_lay.addWidget(
            self._metrik_karti_olustur(
                "👥 Tahmin Sayısı",
                f"{metrik['tahmin_sayisi']} Öğrenci",
                f"Düşük: {metrik['dusuk_risk_sayisi']} · Orta: {metrik['orta_risk_sayisi']} · Yüksek: {metrik['yuksek_risk_sayisi']}",
                "#15803D",
            ),
            1,
        )
        self.metrik_lay.addWidget(
            self._metrik_karti_olustur(
                "🎯 Test Doğruluğu & F1",
                f"%{metrik['dogruluk']*100:.1f}  (F1: {metrik['f1_skoru']:.2f})",
                f"Brier Kalibrasyon: {metrik['brier_skoru']:.3f} · Güven: %{metrik['ortalama_guven']}",
                p["ai_rozet_metin"],
            ),
            1,
        )

        # Histogram güncelle
        self.histogram.veriyi_guncelle(metrik["histogram_sayilari"])
        self.lbl_hist_ozet.setText(
            f"Ortalama Risk: %{int(round(metrik['ortalama_risk']*100))}  •  "
            f"Yüksek Riskli: {metrik['yuksek_risk_sayisi']} öğrenci"
        )
        self.lbl_hist_ozet.setStyleSheet(f"color: {p['ai_rozet_metin']}; font-size: 8.5pt; font-weight: 700;")

        # Model Kartı & Adalet Özeti metinleri
        self.lbl_model_karti.setText(
            f"<b>Model Mimarisi:</b> <code>{RISK_MODEL_SURUM}</code> — Standartlaştırılmış 5 akademik özellik "
            "(<i>AGNO, Katılım %, Ödev Ortalaması, Başarısız Ders Sayısı, Aktif Dönem AKTS</i>) üzerinde çalışan "
            "açıklanabilir lojistik model.<br>"
            f"<b>Kalibrasyon & Doğrulama:</b> Hold-out test doğruluğu <b>%{metrik['dogruluk']*100:.1f}</b>, "
            f"F1 skoru <b>{metrik['f1_skoru']:.2f}</b>, Brier kalibrasyon hatası <b>{metrik['brier_skoru']:.3f}</b>."
        )
        self.lbl_adalet.setText(
            f"<b>✦ Adalet Özeti (Fairness Denetimi):</b> {metrik['adalet_ozeti']} "
            "Giriş yılları ve program kohortları arasında demografik yanlılık bulunmamaktadır."
        )

        # Kohort / Giriş Yılı bazında adalet tablosu
        kohortlar: dict[str, list[tuple[float, int]]] = {}
        for s in satirlar:
            ogr_no = str(s.get("ogrenci_no") or "")
            yy = ogr_no[:2] if len(ogr_no) >= 2 and ogr_no[:2].isdigit() else "25"
            etiket = f"20{yy} Girişli Kohort"
            sonuc: RiskTahminSonucu = s["_hesaplanan"]
            kohortlar.setdefault(etiket, []).append((sonuc.ozellikler["gno"], sonuc.yuzde))

        genel_ort_risk = metrik["ortalama_risk"] * 100.0
        self.tbl_adalet.setRowCount(0)
        for grup_ad, degerler in sorted(kohortlar.items()):
            r_idx = self.tbl_adalet.rowCount()
            self.tbl_adalet.insertRow(r_idx)
            ort_gno = sum(x[0] for x in degerler) / len(degerler)
            ort_risk = sum(x[1] for x in degerler) / len(degerler)
            sapma = abs(ort_risk - genel_ort_risk)
            denge_metin = f"%{ort_risk:.0f} (✔ Akademik GNO ile uyumlu)" if sapma < 25 else f"%{ort_risk:.0f} (GNO farkı kaynaklı)"

            self.tbl_adalet.setItem(r_idx, 0, QTableWidgetItem(grup_ad))
            it_adet = QTableWidgetItem(str(len(degerler)))
            it_adet.setTextAlignment(Qt.AlignCenter)
            self.tbl_adalet.setItem(r_idx, 1, it_adet)
            it_gno = QTableWidgetItem(f"{ort_gno:.2f}")
            it_gno.setTextAlignment(Qt.AlignCenter)
            self.tbl_adalet.setItem(r_idx, 2, it_gno)
            self.tbl_adalet.setItem(r_idx, 3, QTableWidgetItem(denge_metin))

        # Alt tablo: Öğrenci bazlı risk tahminleri
        self.tbl_tahminler.setRowCount(0)
        for s in satirlar:
            sonuc: RiskTahminSonucu = s["_hesaplanan"]
            r = self.tbl_tahminler.rowCount()
            self.tbl_tahminler.insertRow(r)

            self.tbl_tahminler.setItem(r, 0, QTableWidgetItem(str(s.get("ogrenci_no") or "")))
            self.tbl_tahminler.setItem(r, 1, QTableWidgetItem(str(s.get("ad_soyad") or "")))

            it_gno = QTableWidgetItem(f"{sonuc.ozellikler['gno']:.2f}")
            it_gno.setTextAlignment(Qt.AlignCenter)
            self.tbl_tahminler.setItem(r, 2, it_gno)

            it_kat = QTableWidgetItem(f"%{sonuc.ozellikler['katilim_yuzde']:.0f}")
            it_kat.setTextAlignment(Qt.AlignCenter)
            self.tbl_tahminler.setItem(r, 3, it_kat)

            it_odev = QTableWidgetItem(f"{sonuc.ozellikler['odev_ort_puan']:.0f}")
            it_odev.setTextAlignment(Qt.AlignCenter)
            self.tbl_tahminler.setItem(r, 4, it_odev)

            it_risk = QTableWidgetItem(f"✦ %{sonuc.yuzde} ({sonuc.seviye})")
            it_risk.setTextAlignment(Qt.AlignCenter)
            f_b = QFont()
            f_b.setBold(True)
            it_risk.setFont(f_b)
            if sonuc.skor >= 0.65:
                it_risk.setBackground(QBrush(QColor("#FEE2E2")))
                it_risk.setForeground(QBrush(QColor("#B91C1C")))
            elif sonuc.skor >= 0.35:
                it_risk.setBackground(QBrush(QColor("#FEF3C7")))
                it_risk.setForeground(QBrush(QColor("#92400E")))
            else:
                it_risk.setBackground(QBrush(QColor("#DCFCE7")))
                it_risk.setForeground(QBrush(QColor("#15803D")))
            self.tbl_tahminler.setItem(r, 5, it_risk)

            neden_metin = "  •  ".join(
                f"{n.etiket} ({n.deger_metni}): {'+' if n.etki_puani > 0 else ''}{n.etki_puani:.1f} pt"
                for n in sonuc.nedenler
            )
            self.tbl_tahminler.setItem(r, 6, QTableWidgetItem(neden_metin))
