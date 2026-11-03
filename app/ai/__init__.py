"""AI paketi: görsel kimlik, güvenli SQL motoru, şablonlu asistan, risk radarı ve ders öneri bileşenleri."""

from __future__ import annotations

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


def __getattr__(ad: str):
    if ad in _KIMLIK_SEMBOLLERI:
        from app.ai import kimlik

        return getattr(kimlik, ad)
    raise AttributeError(f"module 'app.ai' has no attribute {ad!r}")
