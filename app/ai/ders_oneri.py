"""
✦ Ders Seçiminde AI Önerisi: Şube Başarı Olasılığı Tahmincisi ve 3 Plan Kartı (Hızlı / Dengeli / Güvenli).

İlkeler:
  1. AI yalnızca öneri, tahmini başarı yüzdesi (%35–%98) ve 3 alternatif ders planı
     (Hızlı / Dengeli / Güvenli) üretir; kısıt kontrolü (AKTS sınırı, önkoşul,
     saat çakışması, kontenjan) tamamen PostgreSQL fonksiyonlarında
     (`fn_sepete_ekle`, `fn_kesinlestir_hepsi`) kalır.
  2. Her tahmin açıklanabilir lojistik kalibrasyonla hesaplanır:
       - Öğrencinin mevcut GNO'su (ve yönetmelikteki asgari mezuniyet GNO eşiği)
       - Dersin sınıf düzeyi (1xx/2xx/3xx/4xx), türü (zorunlu çekirdek vs seçmeli) ve AKTS yükü
       - Öğrencinin dersi daha önce alıp başarısız olup olmadığı (tekrar dersi etkisi)
  3. Tüm çıktılar `✦ AI · model v1 · güven %NN` ve `demo verisi` kimliğini taşır.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.ai.risk_motor import RISK_MODEL_SURUM

_GUN_HARITA = {
    "pzt": 0,
    "sal": 1,
    "car": 2,
    "çar": 2,
    "per": 3,
    "cum": 4,
}


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


@dataclass(frozen=True)
class ProgramPlanKarti:
    kod: str                       # 'hizli' | 'dengeli' | 'guvenli'
    baslik: str                    # '⚡ Hızlı Plan' | '⚖️ Dengeli Plan' | '🛡️ Güvenli Plan'
    alt_baslik: str
    subeler: list[dict] = field(default_factory=list)
    eklenen_akts: int = 0
    toplam_akts: int = 0
    akts_limiti: int = 30
    ortalama_basari_yuzde: int = 80
    gerekce: str = ""
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

    lojit = (
        1.15
        + 1.10 * (gno - min_gno)
        - 0.90 * zorluk
        - 0.28 * ust_sinif_farki
        - (0.35 if daha_once_kaldi_mi else 0.0)
    )
    ham_olasilik = _sigmoid(lojit)
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

    gerekce = f"✦ AI Tahmini (%{yuzde} · {seviye}): {ders_kod} için {neden_ek}."
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


def _saat_slotlarini_coz(saatler_str: str) -> set[tuple[int, int]]:
    """Şube saat metnini {(gun_0_4, saat_0_7), ...} kümesine çevirir."""
    slotlar: set[tuple[int, int]] = set()
    if not saatler_str or saatler_str == "-":
        return slotlar
    for parca in str(saatler_str).split(","):
        p = parca.strip().lower()
        if not p:
            continue
        kelimeler = p.split()
        if len(kelimeler) < 2:
            continue
        gun_idx = _GUN_HARITA.get(kelimeler[0][:3])
        if gun_idx is None:
            continue
        kalan = kelimeler[1]
        if ":" in kalan and "-" in kalan:
            try:
                bas_str, bit_str = kalan.split("-", 1)
                bas_saat = int(bas_str.split(":")[0])
                bit_saat = int(bit_str.split(":")[0])
                for s in range(max(1, bas_saat - 8), min(9, bit_saat - 8 + 1)):
                    slotlar.add((gun_idx, s - 1))
            except ValueError:
                pass
        else:
            sayilar = re.findall(r"\d+", kalan)
            if sayilar:
                s_no = int(sayilar[0])
                if 1 <= s_no <= 8:
                    slotlar.add((gun_idx, s_no - 1))
    return slotlar


def _cakismasiz_secim_yap(
    adaylar: list[dict],
    hedef_ek_akts: int,
    baslangic_slotlar: set[tuple[int, int]],
    maks_ders_sayisi: int | None = None,
) -> list[dict]:
    """
    Sıralanmış aday şube listesinden:
      - Aynı ders_kod'dan en fazla 1 şube alan,
      - Mevcut ve seçilen saat slotlarıyla çakışmayan,
      - hedef_ek_akts bütçesini aşmayan
    alt kümeyi açgözlü (greedy) olarak seçer.
    """
    secilen: list[dict] = []
    secilen_kodlar: set[str] = set()
    aktif_slotlar = set(baslangic_slotlar)
    toplam_ek = 0

    for s in adaylar:
        if maks_ders_sayisi is not None and len(secilen) >= maks_ders_sayisi:
            break
        kod = str(s.get("ders_kod") or "")
        akts = int(s.get("akts") or 6)
        if not kod or kod in secilen_kodlar:
            continue
        if toplam_ek + akts > hedef_ek_akts:
            continue
        sube_slotlari = _saat_slotlarini_coz(str(s.get("saatler") or ""))
        if sube_slotlari and (sube_slotlari & aktif_slotlar):
            continue
        secilen.append(s)
        secilen_kodlar.add(kod)
        aktif_slotlar |= sube_slotlari
        toplam_ek += akts

    return secilen


def uc_plan_karti_olustur(
    subeler_veri: list[dict],
    akts_limiti: int = 30,
    mevcut_secili_akts: int = 0,
    dolu_slotlar: dict[tuple[int, int], tuple[str, str]] | set[tuple[int, int]] | None = None,
    kalinan_kodlar: set[str] | None = None,
    ogrenci_gno: float | None = 2.50,
    ogrenci_sinif: int = 1,
    min_gno: float = 2.00,
) -> list[ProgramPlanKarti]:
    """
    Öğrencinin bu dönem 'alinabilir' durumdaki şubelerini değerlendirerek
    3 farklı stratejide (Hızlı / Dengeli / Güvenli) program öneri kartı üretir.
    Kısıtlar veritabanı kurallarıyla uyumludur; AI yalnızca sıralar ve önerir.
    """
    limit = max(6, int(akts_limiti or 30))
    mevcut_akts = max(0, int(mevcut_secili_akts or 0))
    kalan_butce = max(0, limit - mevcut_akts)
    kalinan = set(kalinan_kodlar or set())

    if isinstance(dolu_slotlar, dict):
        baslangic_slotlar = set(dolu_slotlar.keys())
    elif isinstance(dolu_slotlar, set):
        baslangic_slotlar = set(dolu_slotlar)
    else:
        baslangic_slotlar = set()

    # Yalnızca DB görünümünün 'alinabilir' olarak işaretlediği şubeleri aday al
    uygun_subeler: list[dict] = []
    for s in subeler_veri:
        if s.get("durum") != "alinabilir":
            continue
        kopya = dict(s)
        if "tahmini_basari_yuzde" not in kopya:
            t = ders_basari_tahmini_hesapla(
                ders_kod=str(kopya.get("ders_kod") or ""),
                ders_ad=str(kopya.get("ders_ad") or ""),
                akts=int(kopya.get("akts") or 6),
                ogrenci_gno=ogrenci_gno,
                ogrenci_sinif=ogrenci_sinif,
                daha_once_kaldi_mi=(str(kopya.get("ders_kod") or "") in kalinan),
                min_gno=min_gno,
            )
            kopya["tahmini_basari_yuzde"] = t.basari_yuzde
            kopya["tahmini_basari_gerekce"] = t.gerekce
        uygun_subeler.append(kopya)

    # 1) HIZLI PLAN: Tekrar dersleri + zorunlu çekirdek dersler öncelikli, AKTS limitinin tamamını hedefler
    def _hizli_anahtar(s: dict) -> tuple:
        kod = str(s.get("ders_kod") or "").upper()
        tekrar_oncelik = 1 if kod in kalinan else 0
        zorunlu_oncelik = 0 if kod.startswith("SEC") else 1
        sinif_no, _ = ders_seviye_ve_zorluk(kod, int(s.get("akts") or 6))
        return (-tekrar_oncelik, -zorunlu_oncelik, sinif_no, -int(s.get("akts") or 6), -int(s.get("tahmini_basari_yuzde") or 75))

    hizli_adaylar = sorted(uygun_subeler, key=_hizli_anahtar)
    hizli_secim = _cakismasiz_secim_yap(hizli_adaylar, kalan_butce, baslangic_slotlar)

    # 2) DENGELİ PLAN: Zorunlu + yüksek başarılı seçmeli karışımı, kalan bütçenin ~%80'ini (veya en az 12-18 AKTS) hedefler
    dengeli_butce = max(min(kalan_butce, 12), int(round(kalan_butce * 0.82)))

    def _dengeli_anahtar(s: dict) -> tuple:
        kod = str(s.get("ders_kod") or "").upper()
        tekrar_oncelik = 1 if kod in kalinan else 0
        basari = int(s.get("tahmini_basari_yuzde") or 75)
        zorunlu_bonus = 6 if not kod.startswith("SEC") else 3
        return (-tekrar_oncelik, -(basari + zorunlu_bonus), int(s.get("akts") or 6))

    dengeli_adaylar = sorted(uygun_subeler, key=_dengeli_anahtar)
    dengeli_secim = _cakismasiz_secim_yap(
        dengeli_adaylar,
        dengeli_butce,
        baslangic_slotlar,
        maks_ders_sayisi=max(2, len(hizli_secim) - 1) if len(hizli_secim) > 2 else None,
    )

    # 3) GÜVENLİ PLAN: En yüksek tahmini başarı yüzdesine sahip şubeler, GNO yükseltme/koruma odaklı ılımlı yük
    guvenli_butce = max(min(kalan_butce, 12), int(round(kalan_butce * 0.65)))

    def _guvenli_anahtar(s: dict) -> tuple:
        basari = int(s.get("tahmini_basari_yuzde") or 75)
        akts = int(s.get("akts") or 6)
        return (-basari, akts, str(s.get("ders_kod") or ""))

    guvenli_adaylar = sorted(uygun_subeler, key=_guvenli_anahtar)
    maks_guvenli = max(1, len(dengeli_secim) - 1) if len(dengeli_secim) > 2 else 2
    guvenli_secim = _cakismasiz_secim_yap(
        guvenli_adaylar,
        guvenli_butce,
        baslangic_slotlar,
        maks_ders_sayisi=maks_guvenli,
    )

    def _kart_olustur(kod: str, baslik: str, alt_baslik: str, liste: list[dict], strateji_aciklama: str) -> ProgramPlanKarti:
        ek_akts = sum(int(x.get("akts") or 0) for x in liste)
        top_akts = mevcut_akts + ek_akts
        ort_basari = (
            int(round(sum(int(x.get("tahmini_basari_yuzde") or 75) for x in liste) / len(liste)))
            if liste
            else 0
        )
        if liste:
            kodlar_metin = ", ".join(str(x.get("ders_kod")) for x in liste)
            gerekce = (
                f"{strateji_aciklama} Önerilen {len(liste)} ders ({kodlar_metin}) saat çakışması içermez, "
                f"toplam yükü {top_akts}/{limit} AKTS'ye taşır ve ortalama tahmini başarı olasılığı %{ort_basari} düzeyindedir."
            )
        else:
            gerekce = (
                f"Mevcut sepet/kayıt yükünüz ({mevcut_akts}/{limit} AKTS) veya açık şube kısıtları nedeniyle "
                "eklenebilecek çakışmasız yeni şube bulunamadı."
            )
        return ProgramPlanKarti(
            kod=kod,
            baslik=baslik,
            alt_baslik=alt_baslik,
            subeler=liste,
            eklenen_akts=ek_akts,
            toplam_akts=top_akts,
            akts_limiti=limit,
            ortalama_basari_yuzde=ort_basari,
            gerekce=gerekce,
            guven=89,
            model_surum=RISK_MODEL_SURUM,
        )

    return [
        _kart_olustur(
            "hizli",
            "⚡ Hızlı Mezuniyet Planı",
            "Kredi sınırına yakın maksimum ilerleme ve zorunlu ders önceliği",
            hizli_secim,
            "Mezuniyet süresini kısaltmak için zorunlu çekirdek derslere ve AKTS üst sınırına öncelik verildi.",
        ),
        _kart_olustur(
            "dengeli",
            "⚖️ Dengeli İlerleme Planı",
            "Zorunlu çekirdek dersler ile yüksek başarılı seçmeli dengesi",
            dengeli_secim,
            "Dönem içi iş yükünü dengelemek üzere çekirdek dersler ile yüksek başarı olasılıklı seçmeliler harmanlandı.",
        ),
        _kart_olustur(
            "guvenli",
            "🛡️ Güvenli GNO Planı",
            "En yüksek tahmini başarı yüzdesi ve kontrollü AKTS yükü",
            guvenli_secim,
            "GNO'yu korumak ve yükseltmek amacıyla tahmini başarı yüzdesi en yüksek derslerle kontrollü bir yük oluşturuldu.",
        ),
    ]
