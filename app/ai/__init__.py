"""AI paketi: görsel kimlik, güvenli SQL motoru, şablonlu asistan, risk radarı ve ders öneri bileşenleri."""

from __future__ import annotations

from app.ai.risk_motor import (
    RISK_MODEL_SURUM,
    RiskNedenKatkisi,
    RiskTahminSonucu,
    danisan_risklerini_yenile,
    lojistik_risk_hesapla,
    model_degerlendirme_metrikleri,
    risk_seviyesi,
)
from app.ai.sablon_motor import (
    NIYET_SABLONLARI,
    AsistanYaniti,
    NiyetSablonu,
    SablonSorguMotoru,
    niyet_siniflandir,
    rol_ornek_sorulari,
)
from app.ai.sql_koruma import (
    ROL_IZINLI_FONKSIYONLAR,
    ROL_IZINLI_GORUNUMLER,
    SemaKatalogu,
    SorguSonucu,
    SqlGuvenlikHatasi,
    guvenli_sorgu_calistir,
    sql_dogrula,
)

__all__ = [
    "VARSAYILAN_MODEL_SURUM",
    "AIDemoEtiket",
    "AIDugme",
    "AIRozet",
    "ai_baslik_satiri",
    "ai_kontrast_raporu",
    "ai_rozet_metni",
    "ROL_IZINLI_FONKSIYONLAR",
    "ROL_IZINLI_GORUNUMLER",
    "SemaKatalogu",
    "SorguSonucu",
    "SqlGuvenlikHatasi",
    "guvenli_sorgu_calistir",
    "sql_dogrula",
    "NIYET_SABLONLARI",
    "AsistanYaniti",
    "NiyetSablonu",
    "SablonSorguMotoru",
    "niyet_siniflandir",
    "rol_ornek_sorulari",
    "AIAsistanKatmani",
    "AIAsistanPaneli",
    "AsistanYanitKarti",
    "RISK_MODEL_SURUM",
    "RiskNedenKatkisi",
    "RiskTahminSonucu",
    "danisan_risklerini_yenile",
    "lojistik_risk_hesapla",
    "model_degerlendirme_metrikleri",
    "risk_seviyesi",
    "DaireselRiskGostergesi",
    "NedenKatkiCubugu",
    "RiskRadariKarti",
]

_KIMLIK_SEMBOLLERI = {
    "VARSAYILAN_MODEL_SURUM",
    "AIDemoEtiket",
    "AIDugme",
    "AIRozet",
    "ai_baslik_satiri",
    "ai_kontrast_raporu",
    "ai_rozet_metni",
}

_SOHBET_SEMBOLLERI = {
    "AIAsistanKatmani",
    "AIAsistanPaneli",
    "AsistanYanitKarti",
}

_RADAR_SEMBOLLERI = {
    "DaireselRiskGostergesi",
    "NedenKatkiCubugu",
    "RiskRadariKarti",
}


def __getattr__(ad: str):
    if ad in _KIMLIK_SEMBOLLERI:
        from app.ai import kimlik

        return getattr(kimlik, ad)
    if ad in _SOHBET_SEMBOLLERI:
        from app.ai import sohbet

        return getattr(sohbet, ad)
    if ad in _RADAR_SEMBOLLERI:
        from app.ai import risk_radar

        return getattr(risk_radar, ad)
    raise AttributeError(f"module 'app.ai' has no attribute {ad!r}")
