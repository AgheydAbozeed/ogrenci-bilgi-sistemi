"""
✦ Ders Seçiminde AI Önerisi: Şube Başarı Olasılığı Tahmincisi.

İlkeler:
  1. AI yalnızca öneri ve tahmini başarı yüzdesi (%35–%98) üretir; kısıt kontrolü
     (AKTS sınırı, önkoşul, saat çakışması, kontenjan) tamamen PostgreSQL
     fonksiyonlarında (`fn_sepete_ekle`, `fn_kesinlestir_hepsi`) kalır.
  2. Her tahmin açıklanabilir lojistik kalibrasyonla hesaplanır:
       - Öğrencinin mevcut GNO'su (ve yönetmelikteki asgari mezuniyet GNO eşiği)
       - Dersin sınıf düzeyi (1xx/2xx/3xx/4xx), türü (zorunlu çekirdek vs seçmeli) ve AKTS yükü
       - Öğrencinin dersi daha önce alıp başarısız olup olmadığı (tekrar dersi etkisi)
  3. Tüm çıktılar `✦ AI · model v1 · güven %NN` ve `demo verisi` kimliğini taşır.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.ai.risk_motor import RISK_MODEL_SURUM


@dataclass(frozen=True)
class DersBasariTahmini:
    ders_kod: str
    ders_ad: str
    akts: int
    basari_olasiligi: float  # 0.0 - 1.0
    basari_yuzde: int        # 0 - 100
    seviye: str              # 'Yüksek Başarı', 'Dengeli', 'Yoğun Çalışma Gerekir'
    gerekce: str
    guven: int = 89
    model_surum: str = RISK_MODEL_SURUM


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def ders_seviye_ve_zorluk(ders_kod: str, akts: int = 6) -> tuple[int, float]:
    """
    Ders kodundan (örn. BIL101, MAT201, YZV302, SEC105) sınıf düzeyini (1..4)
    ve baz zorluk katsayısını (-0.45 .. +0.55) çıkarır.
    """
    kod = (ders_kod or "").strip().upper()
    eslesme = re.search(r"(\d)", kod)
    ders_sinifi = int(eslesme.group(1)) if eslesme else 1
    ders_sinifi = max(1, min(4, ders_sinifi))

    # Seçmeli dersler (SEC*) genelde ilgi alanına göre seçildiği için baz zorluğu daha düşüktür
    if kod.startswith("SEC"):
        baz_zorluk = -0.25 + max(0, akts - 5) * 0.05
    elif kod.startswith("MAT"):
        baz_zorluk = 0.25 + (ders_sinifi - 1) * 0.12 + max(0, akts - 5) * 0.06
    elif kod.startswith(("YZV", "BIL", "YAZ")):
        baz_zorluk = 0.10 + (ders_sinifi - 1) * 0.14 + max(0, akts - 5) * 0.05
    else:
        baz_zorluk = 0.05 + (ders_sinifi - 1) * 0.10

    return ders_sinifi, baz_zorluk


def ders_basari_tahmini_hesapla(
    ders_kod: str,
    ders_ad: str = "",
    akts: int = 6,
    ogrenci_gno: float | None = 2.50,
    ogrenci_sinif: int = 1,
    daha_once_kaldi_mi: bool = False,
    min_gno: float = 2.00,
) -> DersBasariTahmini:
    """
    Öğrencinin ilgili şubeyi ilk/yeni denemesinde başarıyla (en az DD/CC) geçme
    olasılığını (%35–%98 aralığında) ve tek cümlelik açıklanabilir gerekçesini hesaplar.
    """
    gno = float(ogrenci_gno) if ogrenci_gno is not None else 2.40
    gno = max(0.0, min(4.0, gno))
    sinif = max(1, min(4, int(ogrenci_sinif or 1)))
    akts_int = max(1, int(akts or 6))

    ders_sinifi, zorluk = ders_seviye_ve_zorluk(ders_kod, akts_int)
    ust_sinif_farki = max(0, ders_sinifi - sinif)

    # Lojit: pozitif değerler başarı olasılığını artırır
    lojit = (
        1.15
        + 1.10 * (gno - min_gno)
        - 0.90 * zorluk
        - 0.28 * ust_sinif_farki
        - (0.35 if daha_once_kaldi_mi else 0.0)
    )
    ham_olasilik = _sigmoid(lojit)
    # Aşırı uçları (%35 - %98) aralığına kalibre et
    olasilik = max(0.35, min(0.98, ham_olasilik))
    yuzde = int(round(olasilik * 100))

    if yuzde >= 80:
        seviye = "Yüksek Başarı"
    elif yuzde >= 62:
        seviye = "Dengeli"
    else:
        seviye = "Yoğun Çalışma Gerekir"

    kod_ust = (ders_kod or "").strip().upper()
    if daha_once_kaldi_mi:
        neden_ek = "daha önce tekrar gerektirdiği için düzenli takip önerilir"
    elif kod_ust.startswith("SEC"):
        neden_ek = "seçmeli havuz dersi olması nedeniyle dönem yükünü dengeler"
    elif ust_sinif_farki > 0:
        neden_ek = f"üst dönem ({ders_sinifi}. sınıf) dersi olduğundan ek çalışma gerektirir"
    else:
        neden_ek = f"{ders_sinifi}. sınıf düzeyi ve {akts_int} AKTS yükü mevcut GNO ({gno:.2f}) ile uyumludur"

    gerekce = (
        f"✦ AI Tahmini (%{yuzde} · {seviye}): {ders_kod} için {neden_ek}."
    )

    guven = max(82, min(95, 86 + (3 if ogrenci_gno is not None else 0)))
    return DersBasariTahmini(
        ders_kod=ders_kod,
        ders_ad=ders_ad,
        akts=akts_int,
        basari_olasiligi=round(olasilik, 4),
        basari_yuzde=yuzde,
        seviye=seviye,
        gerekce=gerekce,
        guven=guven,
        model_surum=RISK_MODEL_SURUM,
    )
