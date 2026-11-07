"""
Tasarım Sistemi — Vektörel SVG İkon Seti (Lucide tarzı temiz çizgisel ikonlar).

Emoji ikonların işletim sistemleri arasındaki tutarsız görünümü yerine,
renk paletiyle (açık/koyu tema) tam uyumlu, ölçeklenebilir QIcon / QPixmap
üretir.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

try:
    from PySide6.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover
    QSvgRenderer = None

# 24x24 viewBox üzerinde Lucide tarzı vektör yolları
SVG_YOLLARI: dict[str, str] = {
    "ana_sayfa": (
        '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
    ),
    "ders_secimi": (
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
        '<path d="M9 7h6"/><path d="M9 11h6"/>'
    ),
    "notlar": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="8" y1="13" x2="16" y2="13"/>'
        '<line x1="8" y1="17" x2="13" y2="17"/>'
    ),
    "mezuniyet": (
        '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/>'
        '<path d="M6 12v5c0 2 3 3 6 3s6-1 6-3v-5"/>'
    ),
    "takvim": (
        '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
    ),
    "onay": (
        '<path d="M9 11l3 3L22 4"/>'
        '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'
    ),
    "danisanlar": (
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "ai_merkezi": (
        '<path d="M12 2L14.8 8.5L21.5 11.2L14.8 14L12 20.5L9.2 14L2.5 11.2L9.2 8.5L12 2Z"/>'
    ),
    "ogretim_uyesi": (
        '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>'
        '<line x1="8" y1="21" x2="16" y2="21"/>'
        '<line x1="12" y1="17" x2="12" y2="21"/>'
    ),
    "sekreter": (
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
    ),
    "kalkan": (
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    ),
    "ekle": (
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="8" x2="12" y2="16"/>'
        '<line x1="8" y1="12" x2="16" y2="12"/>'
    ),
    "yenile": (
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
    ),
    "tema_acik": (
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>'
        '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/>'
        '<line x1="21" y1="12" x2="23" y2="12"/>'
    ),
    "tema_koyu": (
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
    ),
    "rehber": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'
    ),
    "cikis": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '<polyline points="16 17 21 12 16 7"/>'
        '<line x1="21" y1="12" x2="9" y2="12"/>'
    ),
    "ara": (
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    ),
}


def svg_metni_uret(ad: str, renk_hex: str = "#475569", kalinlik: float = 2.0) -> str:
    ic = SVG_YOLLARI.get(ad, SVG_YOLLARI["ana_sayfa"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{renk_hex}" stroke-width="{kalinlik}" '
        f'stroke-linecap="round" stroke-linejoin="round">{ic}</svg>'
    )


def svg_pixmap(ad: str, renk_hex: str = "#475569", boyut: int = 18) -> QPixmap:
    pm = QPixmap(boyut, boyut)
    pm.fill(Qt.transparent)
    cizici = QPainter(pm)
    cizici.setRenderHint(QPainter.Antialiasing)
    if QSvgRenderer is not None:
        svg_kod = svg_metni_uret(ad, renk_hex)
        renderer = QSvgRenderer(QByteArray(svg_kod.encode("utf-8")))
        renderer.render(cizici, QRectF(0, 0, boyut, boyut))
    else:
        kalem = QPen(QColor(renk_hex), 1.8)
        cizici.setPen(kalem)
        cizici.drawRoundedRect(QRectF(2, 2, boyut - 4, boyut - 4), 3, 3)
    cizici.end()
    return pm


def svg_ikon(ad: str, renk_hex: str = "#475569", boyut: int = 18) -> QIcon:
    return QIcon(svg_pixmap(ad, renk_hex, boyut))
