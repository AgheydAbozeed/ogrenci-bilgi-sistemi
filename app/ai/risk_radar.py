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
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ai.kimlik import AIDemoEtiket, AIRozet
from app.ai.risk_motor import RiskNedenKatkisi, RiskTahminSonucu
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

        # Etkileşim (kaydırıcılar) için ayrılan alt konteyner
        self.alt_ek_lay = QVBoxLayout()
        self.alt_ek_lay.setContentsMargins(0, 0, 0, 0)
        ana.addLayout(self.alt_ek_lay)

    def sonuc_goster(self, ad_soyad: str, sonuc: RiskTahminSonucu):
        self.lbl_baslik.setText(f"<b>✦  {ad_soyad} — Akademik Risk Radarı</b>")
        self.rozet.guncelle(model=sonuc.model_surum, guven=sonuc.guven)
        self.gosterge.deger_ayarla(sonuc.skor, sonuc.seviye)
        for idx, cubuk in enumerate(self.cubuklar):
            if idx < len(sonuc.nedenler):
                cubuk.guncelle(sonuc.nedenler[idx])
                cubuk.setVisible(True)
            else:
                cubuk.setVisible(False)
