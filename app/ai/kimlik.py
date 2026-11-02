"""
✦ AI Görsel Kimlik Modülü.

AI tarafından üretilen tüm bileşenler tek bir mor tasarım diliyle işaretlenir:
  * İkon + rozet : "✦ AI · model v1 · güven %72"
  * Açık tema    : Düğme #7C3AED (beyaz metin 5,7:1), rozet #5B21B6 / #F5F3FF (8,2:1)
  * Koyu tema    : Vurgu/rozet #A78BFA / #0B1220 (6,9:1)
  * Demo etiketi : Her AI çıktısında sentetik veri uyarısı için "demo verisi" rozeti
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from app.stil import ACIK_PALET, KOYU_PALET, kontrast_orani

VARSAYILAN_MODEL_SURUM = "model v1"


def ai_rozet_metni(
    model: str = VARSAYILAN_MODEL_SURUM,
    guven: int | float | None = None,
) -> str:
    """'✦ AI · model v1 · güven %72' biçiminde standart rozet metni üretir."""
    temiz_model = (model or VARSAYILAN_MODEL_SURUM).strip()
    metin = f"✦ AI · {temiz_model}"
    if guven is not None:
        yuzde = max(0, min(100, int(round(float(guven)))))
        metin += f" · güven %{yuzde}"
    return metin


def ai_kontrast_raporu() -> dict[str, dict[str, float | bool]]:
    """
    AI görsel kimlik renk çiftlerinin WCAG 2.x AA (4.5:1) kontrast denetimini döndürür.
    """
    ciftler = {
        "acik_dugme": (ACIK_PALET["ai_dugme_metin"], ACIK_PALET["ai_dugme"]),
        "acik_rozet": (ACIK_PALET["ai_rozet_metin"], ACIK_PALET["ai_rozet_zemin"]),
        "koyu_rozet": (KOYU_PALET["ai_rozet_metin"], KOYU_PALET["ai_rozet_zemin"]),
    }
    rapor: dict[str, dict[str, float | bool]] = {}
    for ad, (fg, bg) in ciftler.items():
        oran = round(kontrast_orani(fg, bg), 1)
        rapor[ad] = {
            "oran": oran,
            "wcag_aa": oran >= 4.5,
        }
    return rapor


class AIRozet(QLabel):
    """Her AI çıktısının yanında gösterilen '✦ AI · model v1 · güven %72' rozeti."""

    def __init__(
        self,
        model: str = VARSAYILAN_MODEL_SURUM,
        guven: int | float | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(ai_rozet_metni(model, guven), parent)
        self.setObjectName("AIRozet")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignCenter)
        self.setToolTip(
            "Bu çıktı yapay zekâ tarafından öneri amacıyla üretilmiştir; "
            "nihai karar veritabanı kurallarına ve danışmana aittir."
        )

    def guncelle(
        self,
        model: str = VARSAYILAN_MODEL_SURUM,
        guven: int | float | None = None,
    ):
        self.setText(ai_rozet_metni(model, guven))


class AIDemoEtiket(QLabel):
    """Sentetik veri uyarısı için her AI çıktısına eklenen 'demo verisi' etiketi."""

    def __init__(self, metin: str = "demo verisi", parent: QWidget | None = None):
        super().__init__(metin, parent)
        self.setObjectName("AIDemoEtiket")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignCenter)
        self.setToolTip(
            "Veriler sentetiktir (demo verisi). AI yalnızca öneri sunar, "
            "otomatik akademik karar vermez."
        )


class AIDugme(QPushButton):
    """Mor AI görsel kimliğine sahip standart '✦ ...' eylem düğmesi."""

    def __init__(self, metin: str, parent: QWidget | None = None):
        etiket = metin if metin.lstrip().startswith("✦") else f"✦  {metin}"
        super().__init__(etiket, parent)
        self.setObjectName("AIDugme")
        self.setCursor(Qt.PointingHandCursor)


def ai_baslik_satiri(
    baslik: str,
    model: str = VARSAYILAN_MODEL_SURUM,
    guven: int | float | None = None,
    demo_goster: bool = True,
    parent: QWidget | None = None,
) -> tuple[QWidget, AIRozet]:
    """
    Başlık + AIRozet + AIDemoEtiket içeren hazır üst şerit bileşeni döndürür.
    """
    kapsayici = QWidget(parent)
    yerlesim = QHBoxLayout(kapsayici)
    yerlesim.setContentsMargins(0, 0, 0, 0)
    yerlesim.setSpacing(8)

    lbl_baslik = QLabel(f"<b>{baslik}</b>")
    yerlesim.addWidget(lbl_baslik)

    rozet = AIRozet(model=model, guven=guven, parent=kapsayici)
    yerlesim.addWidget(rozet)

    if demo_goster:
        yerlesim.addWidget(AIDemoEtiket(parent=kapsayici))

    yerlesim.addStretch()
    return kapsayici, rozet
