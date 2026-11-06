"""
✦ Danışman Paneli Dairesel Risk Radarı ve En Etkili 3 Neden Çubukları.

Bileşenler:
  * DaireselRiskGostergesi : 0–100% arası risk olasılığını renk kodlu (yeşil/sarı/kırmızı)
                             dairesel yay (arc) olarak çizer.
  * NedenKatkiCubugu       : Tek bir özelliğin riske etkisini yatay çubuk olarak çizer
                             (riski artıran kırmızı +, azaltan yeşil -).
  * RiskRadariKarti        : ✦ AI rozeti + demo verisi etiketi + dairesel gösterge +
                             en etkili 3 nedenin yatay çubukları.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.ai.kimlik import AIDemoEtiket, AIRozet
from app.ai.risk_motor import RiskNedenKatkisi, RiskTahminSonucu, lojistik_risk_hesapla
from app.stil import aktif_palet


def _risk_renkleri(skor: float, koyu: bool = False) -> tuple[str, str]:
    """Skora göre (ana_renk_hex, yumusak_zemin_hex) döndürür."""
    if skor >= 0.65:
        return ("#F87171", "#450A0A") if koyu else ("#B91C1C", "#FEE2E2")
    if skor >= 0.35:
        return ("#FBBF24", "#451A03") if koyu else ("#92400E", "#FEF3C7")
    return ("#4ADE80", "#064E3B") if koyu else ("#15803D", "#DCFCE7")


class DaireselRiskGostergesi(QWidget):
    """270 derecelik kadran üzerinde dairesel risk yüzdesi ve seviye göstergesi."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._skor: float = 0.25
        self._seviye: str = "Düşük Risk"
        self.setFixedSize(136, 136)

    def deger_ayarla(self, skor: float, seviye: str):
        self._skor = max(0.0, min(1.0, float(skor)))
        self._seviye = seviye
        self.update()

    def paintEvent(self, _event):
        p = aktif_palet()
        koyu = p["tema"] == "koyu"
        ana_hex, _ = _risk_renkleri(self._skor, koyu)

        cizici = QPainter(self)
        cizici.setRenderHint(QPainter.Antialiasing)

        kalinlik = 11
        alan = QRectF(
            kalinlik,
            kalinlik,
            self.width() - 2 * kalinlik,
            self.height() - 2 * kalinlik,
        )

        # Arka plan izi (225° başlangıç, -270° yay)
        iz_kalem = QPen(QColor(p["kenarlik"]), kalinlik, Qt.SolidLine, Qt.RoundCap)
        cizici.setPen(iz_kalem)
        cizici.drawArc(alan, 225 * 16, -270 * 16)

        # Dolu risk yayı
        dolu_aci = int(-270 * 16 * self._skor)
        deger_kalem = QPen(QColor(ana_hex), kalinlik, Qt.SolidLine, Qt.RoundCap)
        cizici.setPen(deger_kalem)
        cizici.drawArc(alan, 225 * 16, dolu_aci)

        # Merkez yüzde metni
        yuzde = int(round(self._skor * 100))
        cizici.setPen(QColor(p["metin"]))
        f_buyuk = QFont()
        f_buyuk.setPointSize(17)
        f_buyuk.setBold(True)
        cizici.setFont(f_buyuk)
        cizici.drawText(
            QRectF(0, 32, self.width(), 38),
            Qt.AlignCenter,
            f"%{yuzde}",
        )

        # Alt seviye etiketi
        cizici.setPen(QColor(ana_hex))
        f_kucuk = QFont()
        f_kucuk.setPointSize(8)
        f_kucuk.setBold(True)
        cizici.setFont(f_kucuk)
        cizici.drawText(
            QRectF(8, 74, self.width() - 16, 26),
            Qt.AlignCenter,
            self._seviye,
        )
        cizici.end()


class NedenKatkiCubugu(QWidget):
    """
    Tek bir nedenin riske katkısını gösteren yatay çubuk:
      - Riski artıran nedenler: Kırmızı (#B91C1C / #F87171) sağa doğru
      - Riski azaltan nedenler: Yeşil (#15803D / #4ADE80) sola doğru
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._etiket = "-"
        self._deger = "-"
        self._etki = 0.0
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def guncelle(self, neden: RiskNedenKatkisi):
        self._etiket = neden.etiket
        self._deger = neden.deger_metni
        self._etki = neden.etki_puani
        self.update()

    def paintEvent(self, _event):
        p = aktif_palet()
        koyu = p["tema"] == "koyu"
        artirici = self._etki > 0.0
        renk_hex = (
            ("#F87171" if koyu else "#B91C1C")
            if artirici
            else ("#4ADE80" if koyu else "#15803D")
        )

        cizici = QPainter(self)
        cizici.setRenderHint(QPainter.Antialiasing)

        gen = self.width()
        # Üst satır: Özellik adı + mevcut değer + etki puanı
        f_ust = QFont()
        f_ust.setPointSize(8)
        f_ust.setBold(True)
        cizici.setFont(f_ust)
        cizici.setPen(QColor(p["metin"]))
        sol_metin = f"{self._etiket} ({self._deger})"
        cizici.drawText(QRectF(0, 0, gen * 0.72, 18), Qt.AlignLeft | Qt.AlignVCenter, sol_metin)

        isaret = "+" if self._etki > 0 else ""
        yon_etiket = "▲ Risk artırıcı" if artirici else "▼ Risk azaltıcı"
        sag_metin = f"{isaret}{self._etki:.1f} pt · {yon_etiket}"
        cizici.setPen(QColor(renk_hex))
        cizici.drawText(QRectF(gen * 0.55, 0, gen * 0.45, 18), Qt.AlignRight | Qt.AlignVCenter, sag_metin)

        # Alt satır: Yatay bar izi
        iz_y = 23
        iz_yuk = 9
        cizici.setPen(Qt.NoPen)
        cizici.setBrush(QColor(p["kenarlik"]))
        cizici.drawRoundedRect(QRectF(0, iz_y, gen, iz_yuk), 4, 4)

        # Dolu çubuk (maksimum 25 puan üzerinden ölçeklenir)
        oran = min(1.0, max(0.08, abs(self._etki) / 25.0))
        dolu_gen = gen * oran
        cizici.setBrush(QColor(renk_hex))
        cizici.drawRoundedRect(QRectF(0, iz_y, dolu_gen, iz_yuk), 4, 4)
        cizici.end()


class RiskRadariKarti(QFrame):
    """
    Danışman panelinde seçili öğrencinin dairesel risk radarını ve
    en etkili 3 nedenin kırmızı/yeşil yatay çubuklarını gösteren AI kartı.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("AIKart")
        ana = QVBoxLayout(self)
        ana.setContentsMargins(14, 12, 14, 12)
        ana.setSpacing(10)

        # Üst başlık + ✦ AI rozeti + demo verisi etiketi
        ust = QHBoxLayout()
        ust.setSpacing(6)
        self.lbl_baslik = QLabel("<b>✦  Akademik Risk Radarı ve En Etkili 3 Neden</b>")
        ust.addWidget(self.lbl_baslik)
        ust.addStretch()
        self.rozet = AIRozet()
        ust.addWidget(self.rozet)
        ust.addWidget(AIDemoEtiket())
        ana.addLayout(ust)

        # Orta gövde: Sol dairesel gösterge, Sağ 3 yatay neden çubuğu
        govde = QHBoxLayout()
        govde.setSpacing(16)

        self.gosterge = DaireselRiskGostergesi(self)
        govde.addWidget(self.gosterge, 0, Qt.AlignVCenter)

        sag_lay = QVBoxLayout()
        sag_lay.setSpacing(6)
        self.cubuklar = [NedenKatkiCubugu(self) for _ in range(3)]
        for c in self.cubuklar:
            sag_lay.addWidget(c)
        govde.addLayout(sag_lay, 1)
        ana.addLayout(govde)

        # Alt bilgilendirme satırı
        self.lbl_not = QLabel(
            "AI öneri verir, karar vermez; yalnızca danışmana ve nedenleriyle gösterilir."
        )
        self.lbl_not.setStyleSheet(f"color: {aktif_palet()['ikincil_metin']}; font-size: 8.5pt;")
        ana.addWidget(self.lbl_not)

        # Etkileşim ("Ne değişirse?" canlı kaydırıcıları) kutusu
        self._taban_veri: dict = {}
        self._taban_yuzde: int = 0
        self._kaydirici_kilit: bool = False

        whatif_kutu = QFrame(self)
        whatif_kutu.setObjectName("WhatIfKutu")
        p = aktif_palet()
        whatif_kutu.setStyleSheet(
            f"QFrame#WhatIfKutu {{ background-color: {p['zebra_zemin']}; "
            f"border: 1px solid {p['ai_kenar']}; border-radius: 8px; }}"
        )
        w_lay = QVBoxLayout(whatif_kutu)
        w_lay.setContentsMargins(12, 8, 12, 8)
        w_lay.setSpacing(6)

        w_ust = QHBoxLayout()
        lbl_w_baslik = QLabel("<b>✦  Ne Değişirse? (Canlı Risk Simülasyonu)</b>")
        lbl_w_baslik.setStyleSheet(f"color: {p['ai_rozet_metin']}; font-size: 9pt; border: none;")
        w_ust.addWidget(lbl_w_baslik)
        w_ust.addStretch()

        self.lbl_fark = QLabel("Mevcut gerçek değerler")
        self.lbl_fark.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt; font-weight: 600; border: none;")
        w_ust.addWidget(self.lbl_fark)

        self.btn_sifirla = QPushButton("↺ Gerçek Değerlere Dön")
        self.btn_sifirla.setObjectName("IkincilBtn")
        self.btn_sifirla.setCursor(Qt.PointingHandCursor)
        self.btn_sifirla.setFixedHeight(24)
        self.btn_sifirla.setStyleSheet(
            f"padding: 2px 8px; font-size: 8pt; font-weight: 700; color: {p['ai_rozet_metin']};"
        )
        self.btn_sifirla.clicked.connect(self.simulasyonu_sifirla)
        w_ust.addWidget(self.btn_sifirla)
        w_lay.addLayout(w_ust)

        izgara = QGridLayout()
        izgara.setContentsMargins(0, 0, 0, 0)
        izgara.setHorizontalSpacing(10)
        izgara.setVerticalSpacing(4)

        lbl_k = QLabel("Katılım Oranı (%):")
        lbl_k.setStyleSheet("font-size: 8.5pt; font-weight: 600; border: none;")
        self.sld_katilim = QSlider(Qt.Horizontal)
        self.sld_katilim.setRange(0, 100)
        self.sld_katilim.setValue(85)
        self.sld_katilim.valueChanged.connect(self._simulasyon_hesapla)
        self.lbl_katilim_deger = QLabel("%85")
        self.lbl_katilim_deger.setFixedWidth(56)
        self.lbl_katilim_deger.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_katilim_deger.setStyleSheet("font-size: 8.5pt; font-weight: 700; border: none;")

        lbl_o = QLabel("Ödev Puanı (0-100):")
        lbl_o.setStyleSheet("font-size: 8.5pt; font-weight: 600; border: none;")
        self.sld_odev = QSlider(Qt.Horizontal)
        self.sld_odev.setRange(0, 100)
        self.sld_odev.setValue(70)
        self.sld_odev.valueChanged.connect(self._simulasyon_hesapla)
        self.lbl_odev_deger = QLabel("70 / 100")
        self.lbl_odev_deger.setFixedWidth(56)
        self.lbl_odev_deger.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_odev_deger.setStyleSheet("font-size: 8.5pt; font-weight: 700; border: none;")

        izgara.addWidget(lbl_k, 0, 0)
        izgara.addWidget(self.sld_katilim, 0, 1)
        izgara.addWidget(self.lbl_katilim_deger, 0, 2)
        izgara.addWidget(lbl_o, 1, 0)
        izgara.addWidget(self.sld_odev, 1, 1)
        izgara.addWidget(self.lbl_odev_deger, 1, 2)
        w_lay.addLayout(izgara)
        ana.addWidget(whatif_kutu)

    def _cizimi_guncelle(self, sonuc: RiskTahminSonucu):
        self.rozet.guncelle(model=sonuc.model_surum, guven=sonuc.guven)
        self.gosterge.deger_ayarla(sonuc.skor, sonuc.seviye)
        for idx, cubuk in enumerate(self.cubuklar):
            if idx < len(sonuc.nedenler):
                cubuk.guncelle(sonuc.nedenler[idx])
                cubuk.setVisible(True)
            else:
                cubuk.setVisible(False)

    def sonuc_goster(self, ad_soyad: str, sonuc: RiskTahminSonucu, ogrenci_verisi: dict | None = None):
        self.lbl_baslik.setText(f"<b>✦  {ad_soyad} — Akademik Risk Radarı</b>")
        self._taban_yuzde = sonuc.yuzde
        veri = ogrenci_verisi or {}
        self._taban_veri = {
            "gno": float(veri.get("gno") if veri.get("gno") is not None else sonuc.ozellikler.get("gno", 2.50)),
            "katilim_yuzde": float(
                veri.get("katilim_yuzde")
                if veri.get("katilim_yuzde") is not None
                else sonuc.ozellikler.get("katilim_yuzde", 85.0)
            ),
            "odev_ort_puan": float(
                veri.get("odev_ort_puan")
                if veri.get("odev_ort_puan") is not None
                else sonuc.ozellikler.get("odev_ort_puan", 70.0)
            ),
            "basarisiz_ders_sayisi": int(
                veri.get("basarisiz_ders_sayisi")
                if veri.get("basarisiz_ders_sayisi") is not None
                else sonuc.ozellikler.get("basarisiz_ders_sayisi", 0)
            ),
            "aktif_donem_akts": int(
                veri.get("aktif_donem_akts")
                if veri.get("aktif_donem_akts") is not None
                else sonuc.ozellikler.get("aktif_donem_akts", 24)
            ),
            "ogrenci_id": veri.get("ogrenci_id"),
            "min_gno": float(veri.get("min_gno") or sonuc.ozellikler.get("min_gno", 2.00)),
            "devamsizlik_siniri": float(
                veri.get("devamsizlik_siniri") or sonuc.ozellikler.get("devamsizlik_siniri", 30.0)
            ),
        }
        self._kaydirici_kilit = True
        kat = int(round(self._taban_veri["katilim_yuzde"]))
        odev = int(round(self._taban_veri["odev_ort_puan"]))
        self.sld_katilim.setValue(kat)
        self.sld_odev.setValue(odev)
        self.lbl_katilim_deger.setText(f"%{kat}")
        self.lbl_odev_deger.setText(f"{odev} / 100")
        self._kaydirici_kilit = False

        p = aktif_palet()
        self.lbl_fark.setText(f"Başlangıç riski: %{self._taban_yuzde}")
        self.lbl_fark.setStyleSheet(f"color: {p['ikincil_metin']}; font-size: 8.5pt; font-weight: 600; border: none;")
        self._cizimi_guncelle(sonuc)

    def simulasyonu_sifirla(self):
        if not self._taban_veri:
            return
        self.sld_katilim.setValue(int(round(self._taban_veri["katilim_yuzde"])))
        self.sld_odev.setValue(int(round(self._taban_veri["odev_ort_puan"])))

    def _simulasyon_hesapla(self):
        if self._kaydirici_kilit or not self._taban_veri:
            return
        kat = float(self.sld_katilim.value())
        odev = float(self.sld_odev.value())
        self.lbl_katilim_deger.setText(f"%{int(kat)}")
        self.lbl_odev_deger.setText(f"{int(odev)} / 100")

        yeni_sonuc = lojistik_risk_hesapla(
            gno=self._taban_veri["gno"],
            katilim_yuzde=kat,
            odev_ort_puan=odev,
            basarisiz_ders_sayisi=self._taban_veri["basarisiz_ders_sayisi"],
            aktif_donem_akts=self._taban_veri["aktif_donem_akts"],
            ogrenci_id=self._taban_veri["ogrenci_id"],
            min_gno=self._taban_veri["min_gno"],
            devamsizlik_siniri=self._taban_veri["devamsizlik_siniri"],
        )
        self._cizimi_guncelle(yeni_sonuc)

        fark = yeni_sonuc.yuzde - self._taban_yuzde
        p = aktif_palet()
        if fark == 0:
            self.lbl_fark.setText(f"Başlangıç: %{self._taban_yuzde} (değişim yok)")
            self.lbl_fark.setStyleSheet(
                f"color: {p['ikincil_metin']}; font-size: 8.5pt; font-weight: 600; border: none;"
            )
        elif fark < 0:
            renk = "#4ADE80" if p["tema"] == "koyu" else "#15803D"
            self.lbl_fark.setText(f"Başlangıç: %{self._taban_yuzde} → %{yeni_sonuc.yuzde} ({fark} pt risk azalışı)")
            self.lbl_fark.setStyleSheet(f"color: {renk}; font-size: 8.5pt; font-weight: 700; border: none;")
        else:
            renk = "#F87171" if p["tema"] == "koyu" else "#B91C1C"
            self.lbl_fark.setText(f"Başlangıç: %{self._taban_yuzde} → %{yeni_sonuc.yuzde} (+{fark} pt risk artışı)")
            self.lbl_fark.setStyleSheet(f"color: {renk}; font-size: 8.5pt; font-weight: 700; border: none;")
