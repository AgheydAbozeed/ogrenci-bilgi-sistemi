"""
✦ AI Asistan Sohbet Balonu ve Yanıt Kartları (DBMS Odaklı Salt-Okunur Sorgu Asistanı).

Özellikler:
  * Sağ altta kurumsal arayüzle uyumlu, kompakt "✦ AI Asistan" düğmesi.
  * Tıklanınca açılan, OBS PortalKart tasarım diliyle tam uyumlu sorgu paneli.
  * Rol bazında 2x2 grid halinde hazır soru düğmeleri:
      - "GNO'su 2'nin altındaki danışanlarım kimler?"
      - "Bu dönem hangi dersleri alabilirim?"
      - "Ne zaman mezun olurum?"
  * Her yanıtta:
      - "✦ AI · model v1 · güven %NN" rozeti + "demo verisi" etiketi
      - İki cümlelik özet açıklama
      - Sonuç tablosu (QTableWidget)
      - "Kullanılan SQL'i göster" açılır/kapanır düğmesi ve salt-okunur SQL kutusu
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ai.kimlik import AIDemoEtiket, AIDugme, AIRozet
from app.ai.sablon_motor import AsistanYaniti, SablonSorguMotoru
from app.stil import OLCULER, aktif_palet

SUTUN_ETIKETLERI = {
    "ogrenci_no": "Öğrenci No",
    "ad_soyad": "Ad Soyad",
    "gno": "GNO",
    "dno": "DNO",
    "gecilen_akts": "Geçilen AKTS",
    "ders_kod": "Ders Kodu",
    "kod": "Ders Kodu",
    "ders_ad": "Ders Adı",
    "ders_adi": "Ders Adı",
    "ad": "Ders Adı",
    "akts": "AKTS",
    "sube_no": "Şube",
    "hoca": "Öğretim Üyesi",
    "saatler": "Ders Saatleri",
    "donem_sira": "Dönem Sırası",
    "sinif": "Sınıf",
    "aktif_donem": "Aktif Dönem",
    "kayit_acik": "Kayıt Açık",
    "gun": "Gün",
    "ders_saati": "Saat",
    "durum": "Durum",
    "neden": "Engel Nedeni",
    "yil": "Yıl",
    "donem": "Dönem",
    "harf": "Harf",
    "katsayi": "Katsayı",
    "ogrenci_sayisi": "Öğrenci Sayısı",
    "bilesen": "Bileşen",
    "agirlik": "Ağırlık (%)",
    "puan": "Puan",
    "ilan_edildi": "İlan",
    "mufredat_id": "Müfredat #",
    "program": "Program",
    "giris_yili": "Giriş Yılı",
    "anahtar": "Parametre",
    "deger": "Değer",
    "aciklama": "Açıklama",
    "log_id": "Log #",
    "zaman": "Zaman",
    "kullanici": "Kullanıcı",
    "tablo": "Tablo",
    "islem": "İşlem",
    "kayit_pk": "Kayıt PK",
}


def _sohbet_qss(p: dict | None = None) -> str:
    p = p or aktif_palet()
    koyu = p["tema"] == "koyu"
    sql_zemin = "#0B1220" if koyu else "#0F172A"
    return f"""
QPushButton#AISohbetBalonu {{
    background-color: {p['ai_dugme']};
    color: {p['ai_dugme_metin']};
    border: 1px solid {p['ai_dugme_hover']};
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 9.5pt;
    font-weight: 700;
}}
QPushButton#AISohbetBalonu:hover {{
    background-color: {p['ai_dugme_hover']};
}}
QFrame#AIAsistanCekmece {{
    background-color: {p['zemin']};
    border: 1px solid {p['kenarlik']};
    border-top: 3px solid {p['ai_dugme']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#AIAsistanUstBar {{
    background-color: {p['kart_zemin']};
    border-bottom: 1px solid {p['kenarlik']};
    border-top-left-radius: {OLCULER['kart_yaricap']}px;
    border-top-right-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#AIAsistanAltBar {{
    background-color: {p['kart_zemin']};
    border-top: 1px solid {p['kenarlik']};
    border-bottom-left-radius: {OLCULER['kart_yaricap']}px;
    border-bottom-right-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#AIYanitKart {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['kenarlik']};
    border-left: 3px solid {p['ai_dugme']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#AISoruBalon {{
    background-color: {p['zebra_zemin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
}}
QPushButton#AIOneriCip {{
    background-color: {p['kart_zemin']};
    color: {p['metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 7px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    text-align: left;
}}
QPushButton#AIOneriCip:hover {{
    background-color: {p['ai_rozet_zemin']};
    color: {p['ai_rozet_metin']};
    border: 1px solid {p['ai_dugme']};
}}
QPushButton#AISqlGosterBtn {{
    background-color: {p['kart_zemin']};
    color: {p['ai_rozet_metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 4px 10px;
    font-size: 8.5pt;
    font-weight: 700;
}}
QPushButton#AISqlGosterBtn:hover, QPushButton#AISqlGosterBtn:checked {{
    background-color: {p['ai_rozet_zemin']};
    border: 1px solid {p['ai_dugme']};
}}
QPlainTextEdit#AISqlKutu {{
    background-color: {sql_zemin};
    color: #F8FAFC;
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 8px;
    font-family: Menlo, Consolas, monospace;
    font-size: 8.5pt;
}}
"""


class AsistanYanitKarti(QFrame):
    """
    Tek bir soru-yanıt çiftini gösteren kurumsal kart:
      - Soru başlığı
      - ✦ AI rozeti + demo verisi etiketi
      - İki cümlelik özet
      - Sonuç tablosu
      - 'Kullanılan SQL'i göster' düğmesi
    """

    def __init__(self, soru: str, yanit: AsistanYaniti, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("AIYanitKart")
        p = aktif_palet()
        yerlesim = QVBoxLayout(self)
        yerlesim.setContentsMargins(14, 12, 14, 12)
        yerlesim.setSpacing(8)

        # 1. Kullanıcı sorusu şeridi
        soru_cerceve = QFrame()
        soru_cerceve.setObjectName("AISoruBalon")
        s_lay = QHBoxLayout(soru_cerceve)
        s_lay.setContentsMargins(10, 6, 10, 6)
        lbl_soru = QLabel(f"<span style='color:{p['ai_rozet_metin']}; font-weight:700;'>Soru:</span> {soru}")
        lbl_soru.setWordWrap(True)
        s_lay.addWidget(lbl_soru)
        yerlesim.addWidget(soru_cerceve)

        # 2. Üst kimlik satırı: Başlık + ✦ AI rozeti + demo verisi
        ust = QHBoxLayout()
        ust.setSpacing(6)
        lbl_baslik = QLabel(f"<b>{yanit.baslik}</b>")
        lbl_baslik.setWordWrap(True)
        ust.addWidget(lbl_baslik, 1)
        ust.addWidget(AIRozet(model=yanit.model_surum, guven=yanit.guven))
        ust.addWidget(AIDemoEtiket())
        yerlesim.addLayout(ust)

        # 3. İki cümlelik açıklama
        lbl_ozet = QLabel(f"{yanit.cumle_1} {yanit.cumle_2}")
        lbl_ozet.setWordWrap(True)
        lbl_ozet.setStyleSheet(f"color: {p['metin']}; line-height: 1.35;")
        yerlesim.addWidget(lbl_ozet)

        # 4. Sonuç tablosu
        if yanit.sutunlar:
            tablo = QTableWidget(len(yanit.satirlar), len(yanit.sutunlar))
            etiketler = [SUTUN_ETIKETLERI.get(s, s) for s in yanit.sutunlar]
            tablo.setHorizontalHeaderLabels(etiketler)
            tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tablo.verticalHeader().setDefaultSectionSize(30)
            tablo.verticalHeader().setVisible(False)
            tablo.setEditTriggers(QTableWidget.NoEditTriggers)
            tablo.setSelectionBehavior(QTableWidget.SelectRows)
            for r_idx, satir in enumerate(yanit.satirlar):
                for c_idx, sutun in enumerate(yanit.sutunlar):
                    deger = satir.get(sutun)
                    if isinstance(deger, bool):
                        metin = "Evet" if deger else "Hayır"
                    else:
                        metin = "-" if deger is None else str(deger)
                    tablo.setItem(r_idx, c_idx, QTableWidgetItem(metin))
            gorunur_satir = min(max(len(yanit.satirlar), 1), 6)
            tablo.setFixedHeight(34 + gorunur_satir * 30)
            yerlesim.addWidget(tablo)

        # 5. Alt araç çubuğu: satır sayısı + "Kullanılan SQL'i göster"
        alt = QHBoxLayout()
        lbl_meta = QLabel(
            f"{len(yanit.satirlar)} kayıt · {yanit.sure_ms:.1f} ms · salt-okunur görünüm"
        )
        lbl_meta.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt;")
        alt.addWidget(lbl_meta)
        alt.addStretch()

        self.btn_sql = QPushButton("Kullanılan SQL'i göster")
        self.btn_sql.setObjectName("AISqlGosterBtn")
        self.btn_sql.setCursor(Qt.PointingHandCursor)
        self.btn_sql.setCheckable(True)
        self.btn_sql.toggled.connect(self._sql_ac_kapat)
        alt.addWidget(self.btn_sql)
        yerlesim.addLayout(alt)

        self.txt_sql = QPlainTextEdit(yanit.sql)
        self.txt_sql.setObjectName("AISqlKutu")
        self.txt_sql.setReadOnly(True)
        self.txt_sql.setFixedHeight(68)
        self.txt_sql.setVisible(False)
        yerlesim.addWidget(self.txt_sql)

    def _sql_ac_kapat(self, acik: bool):
        self.txt_sql.setVisible(acik)
        self.btn_sql.setText("Kullanılan SQL'i gizle" if acik else "Kullanılan SQL'i göster")


class AIAsistanPaneli(QFrame):
    """Sağ altta açılan, OBS tasarım sistemiyle uyumlu AI Asistan penceresi."""

    def __init__(self, db, kapat_cb=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.db = db
        self.motor = SablonSorguMotoru(db)
        self._kapat_cb = kapat_cb
        self.setObjectName("AIAsistanCekmece")

        golge = QGraphicsDropShadowEffect(self)
        golge.setBlurRadius(28)
        golge.setOffset(0, 6)
        golge.setColor(QColor(15, 23, 42, 75))
        self.setGraphicsEffect(golge)

        ana = QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        # Üst başlık çubuğu (iki satırlı ferah düzen — metin ve rozetler asla sıkışmaz)
        ust = QFrame()
        ust.setObjectName("AIAsistanUstBar")
        u_lay = QVBoxLayout(ust)
        u_lay.setContentsMargins(14, 10, 14, 10)
        u_lay.setSpacing(6)

        ust_satir_1 = QHBoxLayout()
        ust_satir_1.setSpacing(8)
        lbl_baslik = QLabel("<b>✦  AI Veritabanı Asistanı</b>")
        lbl_baslik.setStyleSheet("font-size: 11pt;")
        ust_satir_1.addWidget(lbl_baslik)
        ust_satir_1.addStretch()

        btn_temizle = QPushButton("Temizle")
        btn_temizle.setObjectName("AISqlGosterBtn")
        btn_temizle.setCursor(Qt.PointingHandCursor)
        btn_temizle.clicked.connect(self.gecmisi_temizle)
        ust_satir_1.addWidget(btn_temizle)

        btn_kapat = QPushButton("✕ Kapat")
        btn_kapat.setObjectName("AISqlGosterBtn")
        btn_kapat.setCursor(Qt.PointingHandCursor)
        btn_kapat.clicked.connect(lambda: self._kapat_cb() if self._kapat_cb else self.hide())
        ust_satir_1.addWidget(btn_kapat)
        u_lay.addLayout(ust_satir_1)

        ust_satir_2 = QHBoxLayout()
        ust_satir_2.setSpacing(6)
        self.ust_rozet = AIRozet(guven=89)
        ust_satir_2.addWidget(self.ust_rozet)
        ust_satir_2.addWidget(AIDemoEtiket())
        lbl_kisit = QLabel("Salt-okunur görünüm sorgusu · Karar vermez")
        lbl_kisit.setStyleSheet(f"color: {aktif_palet()['ikincil_metin']}; font-size: 8pt;")
        ust_satir_2.addWidget(lbl_kisit)
        ust_satir_2.addStretch()
        u_lay.addLayout(ust_satir_2)

        ana.addWidget(ust)

        # Hızlı soru ızgarası (2x2 düzenli kartlar)
        cip_kutu = QFrame()
        cip_kutu.setStyleSheet("border-bottom: 1px solid rgba(148,163,184,0.25);")
        self.cip_lay = QVBoxLayout(cip_kutu)
        self.cip_lay.setContentsMargins(14, 8, 14, 10)
        self.cip_lay.setSpacing(6)
        ana.addWidget(cip_kutu)

        # Kaydırılabilir yanıt listesi
        self.kaydirma = QScrollArea()
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setFrameShape(QFrame.NoFrame)
        self.icerik_w = QWidget()
        self.icerik_lay = QVBoxLayout(self.icerik_w)
        self.icerik_lay.setContentsMargins(14, 10, 14, 12)
        self.icerik_lay.setSpacing(10)

        self.lbl_bos = QLabel(
            "Yukarıdaki hazır sorulardan birine tıklayın veya aşağıya kendi sorunuzu yazın.\n"
            "Sorgular yalnızca rolünüzün izinli görünümlerinde (READ ONLY) çalıştırılır."
        )
        self.lbl_bos.setAlignment(Qt.AlignCenter)
        self.lbl_bos.setWordWrap(True)
        self.lbl_bos.setStyleSheet(
            f"color: {aktif_palet()['ikincil_metin']}; padding: 24px 12px; font-size: 9pt;"
        )
        self.icerik_lay.addWidget(self.lbl_bos)
        self.icerik_lay.addStretch()
        self.kaydirma.setWidget(self.icerik_w)
        ana.addWidget(self.kaydirma, 1)

        # Alt soru giriş satırı
        alt = QFrame()
        alt.setObjectName("AIAsistanAltBar")
        a_lay = QHBoxLayout(alt)
        a_lay.setContentsMargins(12, 10, 12, 10)
        a_lay.setSpacing(8)

        self.txt_soru = QLineEdit()
        self.txt_soru.setPlaceholderText(
            "Örn: Bu dönem hangi dersleri alabilirim? / Ne zaman mezun olurum?"
        )
        self.txt_soru.returnPressed.connect(self._gonder_tiklandi)
        a_lay.addWidget(self.txt_soru, 1)

        self.btn_sor = AIDugme("Sorgula")
        self.btn_sor.clicked.connect(self._gonder_tiklandi)
        a_lay.addWidget(self.btn_sor)
        ana.addWidget(alt)

        self.tema_yenile()
        self.cipleri_yenile()

    def tema_yenile(self):
        self.setStyleSheet(_sohbet_qss())

    def cipleri_yenile(self):
        while self.cip_lay.count():
            item = self.cip_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                alt_lay = item.layout()
                while alt_lay.count():
                    alt_it = alt_lay.takeAt(0)
                    if alt_it.widget():
                        alt_it.widget().deleteLater()

        lbl_ipucu = QLabel("<b>Hazır Sorular</b> (tıklayarak doğrudan çalıştırın):")
        lbl_ipucu.setStyleSheet(f"color: {aktif_palet()['ikincil_metin']}; font-size: 8.5pt;")
        self.cip_lay.addWidget(lbl_ipucu)

        izgara = QGridLayout()
        izgara.setSpacing(6)
        for idx, ornek in enumerate(self.motor.ornek_sorular()):
            btn = QPushButton(f"✦  {ornek}")
            btn.setObjectName("AIOneriCip")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, metin=ornek: self.soru_sor(metin))
            izgara.addWidget(btn, idx // 2, idx % 2)
        self.cip_lay.addLayout(izgara)

    def gecmisi_temizle(self):
        while self.icerik_lay.count() > 1:
            item = self.icerik_lay.takeAt(0)
            w = item.widget()
            if w and w is not self.lbl_bos:
                w.deleteLater()
            elif w is self.lbl_bos:
                self.icerik_lay.insertWidget(0, self.lbl_bos)
                break
        self.lbl_bos.setVisible(True)

    def _gonder_tiklandi(self):
        metin = self.txt_soru.text().strip()
        if not metin:
            return
        self.txt_soru.clear()
        self.soru_sor(metin)

    def soru_sor(self, soru: str):
        self.lbl_bos.setVisible(False)
        try:
            yanit = self.motor.yanitla(soru)
            self.ust_rozet.guncelle(model=yanit.model_surum, guven=yanit.guven)
            kart = AsistanYanitKarti(soru, yanit, self.icerik_w)
            self.icerik_lay.insertWidget(self.icerik_lay.count() - 1, kart)
            self.kaydirma.verticalScrollBar().setValue(
                self.kaydirma.verticalScrollBar().maximum()
            )
        except Exception as exc:
            hata_lbl = QLabel(f"⚠️ Sorgu çalıştırılamadı: {exc}")
            hata_lbl.setWordWrap(True)
            hata_lbl.setStyleSheet(
                f"background-color: {aktif_palet()['hata_zemin']}; "
                f"color: {aktif_palet()['hata_metin']}; padding: 10px; border-radius: 6px;"
            )
            self.icerik_lay.insertWidget(self.icerik_lay.count() - 1, hata_lbl)


class AIAsistanKatmani(QObject):
    """
    Ana pencerenin sağ altına yerleşen kurumsal '✦ AI Asistan' düğmesi ve
    açılır panel yöneticisi.
    """

    def __init__(self, ust_pencere: QWidget, db):
        super().__init__(ust_pencere)
        self.ust = ust_pencere
        self.db = db

        self.panel = AIAsistanPaneli(db, kapat_cb=self.ac_kapat, parent=ust_pencere)
        self.panel.hide()

        self.balon = QPushButton("✦  AI Asistan", ust_pencere)
        self.balon.setObjectName("AISohbetBalonu")
        self.balon.setCursor(Qt.PointingHandCursor)
        self.balon.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.balon.setToolTip(
            "Doğal dilde soru sorun; izinli görünümlerden salt-okunur SQL ile yanıtlansın."
        )
        golge = QGraphicsDropShadowEffect(self.balon)
        golge.setBlurRadius(14)
        golge.setOffset(0, 3)
        golge.setColor(QColor(91, 33, 182, 70))
        self.balon.setGraphicsEffect(golge)
        self.balon.clicked.connect(self.ac_kapat)

        self.tema_yenile()
        self.ust.installEventFilter(self)
        self.konumla()

    def eventFilter(self, obj, event):
        if obj is self.ust and event.type() in (QEvent.Resize, QEvent.Show):
            self.konumla()
        return super().eventFilter(obj, event)

    def tema_yenile(self):
        self.balon.setStyleSheet(_sohbet_qss())
        self.panel.tema_yenile()
        self.konumla()

    def rol_degisti(self):
        self.panel.gecmisi_temizle()
        self.panel.cipleri_yenile()
        self.konumla()

    def acik_mi(self) -> bool:
        return self.panel.isVisible()

    def ac_kapat(self):
        if self.panel.isVisible():
            self.panel.hide()
            self.balon.setText("✦  AI Asistan")
        else:
            self.panel.cipleri_yenile()
            self.konumla()
            self.panel.show()
            self.panel.raise_()
            self.balon.raise_()
            self.balon.setText("✕  Asistanı Kapat")
            self.panel.txt_soru.setFocus()

    def konumla(self):
        gen = self.ust.width()
        yuk = self.ust.height()
        margin_sag = 18
        margin_alt = 14

        self.balon.adjustSize()
        b_gen = max(132, self.balon.sizeHint().width() + 8)
        b_yuk = 36
        b_x = max(16, gen - b_gen - margin_sag)
        b_y = max(16, yuk - b_yuk - margin_alt)
        self.balon.setGeometry(QRect(b_x, b_y, b_gen, b_yuk))

        p_gen = min(600, max(480, int(gen * 0.52)))
        p_yuk = min(560, max(420, int(yuk * 0.72)))
        p_x = max(16, gen - p_gen - margin_sag)
        p_y = max(12, b_y - p_yuk - 8)
        self.panel.setGeometry(QRect(p_x, p_y, p_gen, p_yuk))
