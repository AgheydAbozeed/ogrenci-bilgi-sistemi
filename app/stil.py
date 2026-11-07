try:
    from PySide6.QtCore import QSettings
except ImportError:  # pragma: no cover
    QSettings = None

# =====================================================================
# TASARIM SİSTEMİ — RENK PALETİ, WCAG 2.x KONTRAST VE ÖLÇÜLER
# =====================================================================

ACIK_PALET = {
    "tema": "acik",
    "zemin": "#F8FAFC",
    "metin": "#0F172A",
    "kart_zemin": "#FFFFFF",
    "ikincil_metin": "#475569",
    "kenarlik": "#E2E8F0",
    "tablo_izgara": "#EEF2F6",
    "tablo_baslik_zemin": "#F8FAFC",
    "secim_zemin": "#DBEAFE",
    "secim_metin": "#12355B",
    "menu_zemin": "#12355B",
    "menu_profil_zemin": "#0D2744",
    "menu_metin": "#FFFFFF",
    "menu_hover": "#1B4979",
    "vurgu": "#2563EB",
    "vurgu_hover": "#1D4ED8",
    "vurgu_metin": "#FFFFFF",
    "basari_metin": "#15803D",
    "basari_zemin": "#DCFCE7",
    "uyari_metin": "#92400E",
    "uyari_zemin": "#FEF3C7",
    "hata_metin": "#B91C1C",
    "hata_zemin": "#FEE2E2",
    "zebra_zemin": "#F4F7FB",
    "ai_dugme": "#7C3AED",
    "ai_dugme_hover": "#6D28D9",
    "ai_dugme_metin": "#FFFFFF",
    "ai_rozet_metin": "#5B21B6",
    "ai_rozet_zemin": "#F5F3FF",
    "ai_kenar": "#C4B5FD",
}

KOYU_PALET = {
    "tema": "koyu",
    "zemin": "#0B1220",
    "metin": "#E5E7EB",
    "kart_zemin": "#111A2E",
    "ikincil_metin": "#94A3B8",
    "kenarlik": "#1E293B",
    "tablo_izgara": "#1E293B",
    "tablo_baslik_zemin": "#0F172A",
    "secim_zemin": "#1E3A8A",
    "secim_metin": "#E5E7EB",
    "menu_zemin": "#080E1A",
    "menu_profil_zemin": "#050911",
    "menu_metin": "#E5E7EB",
    "menu_hover": "#1E293B",
    "vurgu": "#60A5FA",
    "vurgu_hover": "#3B82F6",
    "vurgu_metin": "#0B1220",
    "basari_metin": "#4ADE80",
    "basari_zemin": "#0B1220",
    "uyari_metin": "#FBBF24",
    "uyari_zemin": "#0B1220",
    "hata_metin": "#F87171",
    "hata_zemin": "#0B1220",
    "zebra_zemin": "#162038",
    "ai_dugme": "#A78BFA",
    "ai_dugme_hover": "#8B5CF6",
    "ai_dugme_metin": "#0B1220",
    "ai_rozet_metin": "#A78BFA",
    "ai_rozet_zemin": "#0B1220",
    "ai_kenar": "#6D28D9",
}

# Boşluk, Köşe Yarıçapı ve Tipografi Ölçekleri
BOSLUK_OLCEGI = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
}

KOSE_OLCEGI = {
    "rozet": 4,
    "dugme": 6,
    "kart": 8,
    "modal": 12,
}

YAZI_OLCEGI = {
    "baslik_1": {"boyut_px": 24, "boyut_pt": 18, "agirlik": 600, "satir_yuksekligi": 1.3},
    "baslik_2": {"boyut_px": 18, "boyut_pt": 14, "agirlik": 600, "satir_yuksekligi": 1.35},
    "baslik_3": {"boyut_px": 15, "boyut_pt": 12, "agirlik": 600, "satir_yuksekligi": 1.4},
    "govde": {"boyut_px": 13, "boyut_pt": 10, "agirlik": 400, "satir_yuksekligi": 1.5},
    "yardimci": {"boyut_px": 12, "boyut_pt": 9, "agirlik": 400, "satir_yuksekligi": 1.4},
    "kod": {
        "boyut_px": 12,
        "boyut_pt": 9,
        "agirlik": 500,
        "ailesi": '"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace',
    },
}

# Ölçü ve Yerleşim Sabitleri
OLCULER = {
    "yazi_yardimci_pt": 9,
    "yazi_govde_pt": 10,
    "yazi_baslik3_pt": 12,
    "yazi_baslik2_pt": 14,
    "yazi_baslik1_pt": 18,
    "yazi_tipi": '-apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif',
    "kod_yazi_tipi": '"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace',
    "bosluk_1": 4,
    "bosluk_2": 8,
    "bosluk_3": 12,
    "bosluk_4": 16,
    "bosluk_5": 24,
    "bosluk_6": 32,
    "rozet_yaricap": 4,
    "kart_yaricap": 8,
    "dugme_yaricap": 6,
    "modal_yaricap": 12,
    "menu_genislik": 220,
    "tablo_satir_yukseklik": 36,
    "asgari_pencere_genislik": 1100,
    "asgari_pencere_yukseklik": 700,
    "gecis_kisa_ms": 150,
    "gecis_uzun_ms": 200,
}

# Ders Kaydı Durum Rozetleri (Renk + İkon + Metin)
DURUM_ROZETLERI = {
    "alinabilir": {
        "metin": "Alınabilir",
        "ikon": "✔",
        "fg": "#15803D",
        "bg": "#DCFCE7",
        "koyu_fg": "#4ADE80",
        "koyu_bg": "#064E3B",
    },
    "sepette": {
        "metin": "Sepette",
        "ikon": "🛒",
        "fg": "#2563EB",
        "bg": "#DBEAFE",
        "koyu_fg": "#60A5FA",
        "koyu_bg": "#1E3A8A",
    },
    "sepet": {
        "metin": "Sepette",
        "ikon": "🛒",
        "fg": "#2563EB",
        "bg": "#DBEAFE",
        "koyu_fg": "#60A5FA",
        "koyu_bg": "#1E3A8A",
    },
    "kayitli": {
        "metin": "Kayıtlı",
        "ikon": "✔",
        "fg": "#FFFFFF",
        "bg": "#15803D",
        "koyu_fg": "#0B1220",
        "koyu_bg": "#4ADE80",
    },
    "onayli": {
        "metin": "Kayıtlı (Onaylı)",
        "ikon": "✔",
        "fg": "#FFFFFF",
        "bg": "#15803D",
        "koyu_fg": "#0B1220",
        "koyu_bg": "#4ADE80",
    },
    "onay_bekliyor": {
        "metin": "Onay Bekliyor",
        "ikon": "⏳",
        "fg": "#92400E",
        "bg": "#FEF3C7",
        "koyu_fg": "#FBBF24",
        "koyu_bg": "#451A03",
    },
    "reddedildi": {
        "metin": "Reddedildi",
        "ikon": "✖",
        "fg": "#B91C1C",
        "bg": "#FEE2E2",
        "koyu_fg": "#F87171",
        "koyu_bg": "#450A0A",
    },
    "onkosul_eksik": {
        "metin": "Önkoşul Eksik",
        "ikon": "🔒",
        "fg": "#B91C1C",
        "bg": "#FEE2E2",
        "koyu_fg": "#F87171",
        "koyu_bg": "#450A0A",
    },
    "cakisiyor": {
        "metin": "Saat Çakışıyor",
        "ikon": "✖",
        "fg": "#B91C1C",
        "bg": "#FEE2E2",
        "koyu_fg": "#F87171",
        "koyu_bg": "#450A0A",
    },
    "gecildi": {
        "metin": "Geçildi",
        "ikon": "—",
        "fg": "#475569",
        "bg": "#F1F5F9",
        "koyu_fg": "#94A3B8",
        "koyu_bg": "#1E293B",
    },
    "birakti": {
        "metin": "Bırakıldı",
        "ikon": "—",
        "fg": "#475569",
        "bg": "#F1F5F9",
        "koyu_fg": "#94A3B8",
        "koyu_bg": "#1E293B",
    },
}


def bagil_parlaklik(hex_kod: str) -> float:
    """WCAG 2.x bağıl parlaklık (relative luminance) formülü."""
    h = hex_kod.lstrip("#")
    if len(h) != 6:
        return 0.0
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    kanallar = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * kanallar[0] + 0.7152 * kanallar[1] + 0.0722 * kanallar[2]


def kontrast_orani(on_plan_hex: str, zemin_hex: str) -> float:
    """WCAG 2.x kontrast oranı hesaplayıcısı (AA eşiği normal metin için 4.5:1)."""
    l1 = bagil_parlaklik(on_plan_hex)
    l2 = bagil_parlaklik(zemin_hex)
    parlak, koyu = max(l1, l2), min(l1, l2)
    return (parlak + 0.05) / (koyu + 0.05)


def tum_palet_kontrast_raporu() -> list[dict]:
    """Açık ve koyu temadaki tüm ana metin/zemin çiftlerinin WCAG AA (4.5:1) uyumunu denetler."""
    ciftler = [
        ("Açık: Ana Metin / Zemin", ACIK_PALET["metin"], ACIK_PALET["zemin"]),
        ("Açık: Ana Metin / Kart", ACIK_PALET["metin"], ACIK_PALET["kart_zemin"]),
        ("Açık: İkincil Metin / Kart", ACIK_PALET["ikincil_metin"], ACIK_PALET["kart_zemin"]),
        ("Açık: Vurgu Düğme", ACIK_PALET["vurgu_metin"], ACIK_PALET["vurgu"]),
        ("Açık: Başarı Rozet", ACIK_PALET["basari_metin"], ACIK_PALET["basari_zemin"]),
        ("Açık: Uyarı Rozet", ACIK_PALET["uyari_metin"], ACIK_PALET["uyari_zemin"]),
        ("Açık: Hata Rozet", ACIK_PALET["hata_metin"], ACIK_PALET["hata_zemin"]),
        ("Açık: AI Düğme", ACIK_PALET["ai_dugme_metin"], ACIK_PALET["ai_dugme"]),
        ("Açık: AI Rozet", ACIK_PALET["ai_rozet_metin"], ACIK_PALET["ai_rozet_zemin"]),
        ("Koyu: Ana Metin / Zemin", KOYU_PALET["metin"], KOYU_PALET["zemin"]),
        ("Koyu: Ana Metin / Kart", KOYU_PALET["metin"], KOYU_PALET["kart_zemin"]),
        ("Koyu: İkincil Metin / Kart", KOYU_PALET["ikincil_metin"], KOYU_PALET["kart_zemin"]),
        ("Koyu: Vurgu Düğme", KOYU_PALET["vurgu_metin"], KOYU_PALET["vurgu"]),
        ("Koyu: Başarı Metin", KOYU_PALET["basari_metin"], KOYU_PALET["basari_zemin"]),
        ("Koyu: Uyarı Metin", KOYU_PALET["uyari_metin"], KOYU_PALET["uyari_zemin"]),
        ("Koyu: Hata Metin", KOYU_PALET["hata_metin"], KOYU_PALET["hata_zemin"]),
        ("Koyu: AI Düğme", KOYU_PALET["ai_dugme_metin"], KOYU_PALET["ai_dugme"]),
        ("Koyu: AI Rozet", KOYU_PALET["ai_rozet_metin"], KOYU_PALET["ai_rozet_zemin"]),
    ]
    sonuclar = []
    for ad, fg, bg in ciftler:
        oran = round(kontrast_orani(fg, bg), 2)
        sonuclar.append({"ad": ad, "fg": fg, "bg": bg, "oran": oran, "gecer_mi": oran >= 4.5})
    return sonuclar


def akts_cubuk_kurali(toplam_akts: int, sinir_akts: int) -> tuple[str, str, str]:
    """
    AKTS çubuğu renk kuralı hesaplayıcısı:
    - Oran < 0.80 (%80 altı): Mavi
    - 0.80 <= Oran <= 1.00 (%80-100): Sarı
    - Oran > 1.00 (%100 üstü): Kırmızı (örn. '36 / 30, sınırı aşıyor')
    Döndürür: (metin_rengi_hex, zemin_rengi_hex, durum_etiketi)
    """
    sinir = max(1, sinir_akts)
    oran = toplam_akts / sinir
    if oran > 1.0:
        return ("#B91C1C", "#FEE2E2", f"{toplam_akts} / {sinir_akts} AKTS — Sınırı aşıyor!")
    elif oran >= 0.8:
        return ("#92400E", "#FEF3C7", f"{toplam_akts} / {sinir_akts} AKTS — Sınıra yakın")
    else:
        return ("#2563EB", "#DBEAFE", f"{toplam_akts} / {sinir_akts} AKTS — Uygun")


def rozet_formatla(durum_kodu: str, neden: str | None = None) -> tuple[str, str, str]:
    """
    Durum koduna göre (bg_hex, fg_hex, 'İkon Metin (Neden)') döndürür.
    """
    koyu = aktif_tema_adi() == "koyu"
    bilgi = DURUM_ROZETLERI.get(
        durum_kodu,
        {
            "metin": durum_kodu,
            "ikon": "•",
            "fg": "#0F172A",
            "bg": "#F8FAFC",
            "koyu_fg": "#E5E7EB",
            "koyu_bg": "#111A2E",
        },
    )
    fg = bilgi["koyu_fg"] if koyu else bilgi["fg"]
    bg = bilgi["koyu_bg"] if koyu else bilgi["bg"]
    etiket = f"{bilgi['ikon']}  {bilgi['metin']}"
    if neden:
        etiket += f" ({neden})"
    return bg, fg, etiket


_BELLEK_TEMA = "acik"


def tema_ayarlari():
    if QSettings is None:
        return None
    return QSettings("OBS", "OgrenciBilgiSistemi")


def aktif_tema_adi() -> str:
    ayar = tema_ayarlari()
    if ayar is None:
        return _BELLEK_TEMA
    return str(ayar.value("tema", "acik"))


def tema_kaydet(tema: str):
    global _BELLEK_TEMA
    secim = tema if tema in ("acik", "koyu") else "acik"
    _BELLEK_TEMA = secim
    ayar = tema_ayarlari()
    if ayar is not None:
        ayar.setValue("tema", secim)


def aktif_palet() -> dict:
    return KOYU_PALET if aktif_tema_adi() == "koyu" else ACIK_PALET


def stil_uret(tema: str | None = None) -> str:
    p = KOYU_PALET if (tema or aktif_tema_adi()) == "koyu" else ACIK_PALET
    return f"""
QMainWindow, QDialog {{
    background-color: {p['zemin']};
    font-family: {OLCULER['yazi_tipi']};
    font-size: {OLCULER['yazi_govde_pt']}pt;
    color: {p['metin']};
}}
QWidget {{
    font-family: {OLCULER['yazi_tipi']};
    font-size: {OLCULER['yazi_govde_pt']}pt;
    color: {p['metin']};
}}
#UstCubuk {{
    background-color: {p['kart_zemin']};
    border-bottom: 1px solid {p['kenarlik']};
}}
#SolMenu {{
    background-color: {p['menu_zemin']};
    border: none;
}}
#SolMenuProfil {{
    background-color: {p['menu_profil_zemin']};
    border-bottom: 1px solid #1E3A5F;
}}
#SolMenu QPushButton {{
    text-align: left;
    padding: 12px 16px;
    border: none;
    color: {p['menu_metin']};
    font-size: {OLCULER['yazi_govde_pt']}pt;
    font-weight: 500;
    background-color: transparent;
    border-radius: 0px;
}}
#SolMenu QPushButton:hover {{
    background-color: {p['menu_hover']};
    color: #FFFFFF;
}}
#SolMenu QPushButton[secili="true"] {{
    background-color: {p['zemin']};
    color: {p['vurgu']};
    font-weight: 700;
    border-left: 4px solid {p['vurgu']};
}}
QFrame#PortalKart, QFrame#Kart {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#MetrikKutu {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#HizmetKart {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QFrame#HizmetKart:hover {{
    border: 1px solid {p['vurgu']};
    background-color: {p['zebra_zemin']};
}}
QPushButton#HizliIslemBtn {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 12px 16px;
    text-align: left;
    font-weight: 700;
    color: {p['metin']};
    font-size: {OLCULER['yazi_govde_pt']}pt;
}}
QPushButton#HizliIslemBtn:hover {{
    border: 1px solid {p['vurgu']};
    background-color: {p['zebra_zemin']};
}}
QLabel#BolumBaslik {{
    color: {p['vurgu']};
    font-size: {OLCULER['yazi_baslik2_pt']}pt;
    font-weight: 700;
}}
QLabel#SayfaBaslik {{
    color: {p['metin']};
    font-size: {OLCULER['yazi_baslik2_pt']}pt;
    font-weight: 700;
}}
QLabel#AnaBaslik {{
    color: {p['metin']};
    font-size: {OLCULER['yazi_baslik1_pt']}pt;
    font-weight: 800;
}}
QLabel#AltBaslik {{
    color: {p['ikincil_metin']};
    font-size: {OLCULER['yazi_baslik3_pt']}pt;
    font-weight: 600;
}}
QPushButton#BirincilBtn {{
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#BirincilBtn:hover {{
    background-color: #1D4ED8;
}}
QPushButton#BirincilBtn:disabled {{
    background-color: {p['kenarlik']};
    color: {p['ikincil_metin']};
}}
QPushButton#TehlikeBtn {{
    background-color: #B91C1C;
    color: #FFFFFF;
    border: none;
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 6px 12px;
    font-weight: 600;
}}
QPushButton#TehlikeBtn:hover {{
    background-color: #991B1B;
}}
QPushButton#IkincilBtn, QPushButton#UstBarBtn {{
    background-color: {p['kart_zemin']};
    color: {p['metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 6px 12px;
    font-weight: 600;
}}
QPushButton#IkincilBtn:hover, QPushButton#UstBarBtn:hover {{
    border: 1px solid {p['vurgu']};
    background-color: {p['zebra_zemin']};
}}
QPushButton#AIDugme {{
    background-color: {p['ai_dugme']};
    color: {p['ai_dugme_metin']};
    border: none;
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 6px 14px;
    font-weight: 700;
}}
QPushButton#AIDugme:hover {{
    background-color: {p['ai_dugme_hover']};
}}
QPushButton#AIDugme:disabled {{
    background-color: {p['kenarlik']};
    color: {p['ikincil_metin']};
}}
QLabel#AIRozet {{
    background-color: {p['ai_rozet_zemin']};
    color: {p['ai_rozet_metin']};
    border: 1px solid {p['ai_kenar']};
    border-radius: 9px;
    padding: 2px 9px;
    font-weight: 700;
    font-size: 8.5pt;
}}
QLabel#AIDemoEtiket {{
    background-color: {p['uyari_zemin']};
    color: {p['uyari_metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: 9px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 8pt;
}}
QFrame#AIKart {{
    background-color: {p['kart_zemin']};
    border: 1px solid {p['ai_kenar']};
    border-radius: {OLCULER['kart_yaricap']}px;
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {p['kart_zemin']};
    color: {p['metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    padding: 5px 10px;
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1.5px solid {p['vurgu']};
}}
QTableWidget {{
    background-color: {p['kart_zemin']};
    color: {p['metin']};
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['dugme_yaricap']}px;
    gridline-color: {p['tablo_izgara']};
    selection-background-color: {p['secim_zemin']};
    selection-color: {p['secim_metin']};
}}
QHeaderView::section {{
    background-color: {p['tablo_baslik_zemin']};
    color: {p['ikincil_metin']};
    font-weight: 700;
    padding: 8px;
    border: none;
    border-bottom: 1px solid {p['kenarlik']};
    border-right: 1px solid {p['tablo_izgara']};
}}
QTabWidget::pane {{
    border: 1px solid {p['kenarlik']};
    border-radius: {OLCULER['kart_yaricap']}px;
    background-color: {p['kart_zemin']};
}}
QTabBar::tab {{
    background-color: {p['tablo_baslik_zemin']};
    color: {p['ikincil_metin']};
    padding: 8px 16px;
    border: 1px solid {p['kenarlik']};
    border-bottom: none;
    border-top-left-radius: {OLCULER['dugme_yaricap']}px;
    border-top-right-radius: {OLCULER['dugme_yaricap']}px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: {p['kart_zemin']};
    color: {p['vurgu']};
    font-weight: 700;
}}
QDockWidget {{
    font-weight: 700;
    color: {p['metin']};
}}
QDockWidget::title {{
    background-color: {p['kart_zemin']};
    padding: 8px 12px;
    border-bottom: 1px solid {p['kenarlik']};
}}
"""


OBS_STIL = stil_uret()
