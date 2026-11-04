"""
✦ Güvenli NL→SQL Çekirdeği: Şema Kataloğu, SQL Beyaz Liste Doğrulayıcısı ve Salt-Okunur Çalıştırıcı.

İlkeler:
  1. Yalnızca tek bir SELECT veya WITH ... SELECT ifadesine izin verilir.
  2. DML/DDL/oturum komutları (INSERT, UPDATE, DELETE, DROP, SET, COPY, pg_sleep vb.) engellenir.
  3. Sorgu yalnızca aktif rolün beyaz listesindeki görünüm (view) ve salt-okunur
     değerlendirme fonksiyonlarına erişebilir; ham tablolara doğrudan erişim reddedilir.
  4. Sorgu PostgreSQL'de READ ONLY işlem bloğunda, aktif rol + RLS bağlamıyla,
     statement_timeout ve satır sınırıyla çalıştırılır.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

# Rol bazında izin verilen salt-okunur görünümler (ve tablo-döndüren okuma fonksiyonları)
ROL_IZINLI_GORUNUMLER: dict[str, dict[str, str]] = {
    "rol_ogrenci": {
        "v_ana_sayfa": "Öğrencinin sınıf, geçilen AKTS, DNO, GNO ve aktif dönem özeti",
        "v_kayitlarim": "Öğrencinin dönemlik ders kayıtları ve onay durumları",
        "v_acik_subeler": "Bu dönem açılan şubeler, saatler ve alınabilirlik durumu (alinabilir, gecildi, kayitli, sepette, onkosul_eksik, cakisiyor)",
        "v_haftalik_program": "Öğrencinin haftalık ders programı (gün, ders saati, ders kodu)",
        "v_transkript": "Tüm dönemlerin harf notu ve AKTS transkript dökümü",
        "v_not_detay": "Derslerin vize/final/ödev bileşen puanları",
    },
    "rol_danisman": {
        "v_danisanlarim": "Danışmanın aktif danışan öğrencileri (ogrenci_id, ogrenci_no, ad_soyad, gno, gecilen_akts)",
        "v_danisan_risk_ozellik": "Danışanların GNO, başarısız ders, katılım %, ödev ortalaması ve AI risk tahmin skoru",
        "v_onay_kuyrugu": "Danışman onayı bekleyen ders kayıt talepleri",
        "v_kayitlarim": "Danışanların ders kayıtları",
        "v_transkript": "Danışanların transkript kayıtları",
    },
    "rol_ogretim_uyesi": {
        "v_sube_listem": "Öğretim üyesinin yürüttüğü şubeler ve öğrenci sayıları",
        "v_sube_ogrencileri": "Şubelerdeki kayıtlı öğrenciler",
        "v_bilesenler": "Şubelerin değerlendirme bileşenleri ve ağırlıkları",
        "v_not_detay": "Şubelerdeki bileşen notları",
    },
    "rol_sekreter": {
        "v_mufredat_listesi": "Program müfredatları ve giriş yılları",
        "v_kayitlarim": "Tüm ders kayıtları",
        "v_transkript": "Tüm transkript satırları",
    },
    "rol_yonetici": {
        "v_parametreler": "Sistem yönetmelik parametreleri (anahtar, deger, aciklama)",
        "v_denetim_log": "SHA-256 zincirli denetim izi kayıtları",
        "v_silinen_notlar": "Silinen not kayıtları",
        "v_mufredat_listesi": "Program müfredatları",
        "v_kayitlarim": "Tüm ders kayıtları",
        "v_transkript": "Tüm transkript satırları",
    },
}

# Rol bazında FROM/SELECT içinde çağrılmasına izin verilen salt-okunur fonksiyonlar
ROL_IZINLI_FONKSIYONLAR: dict[str, set[str]] = {
    "rol_ogrenci": {
        "fn_mezuniyet_ozet_ben",
        "fn_mezuniyet_denetim_ben",
        "fn_ders_plani_ben",
        "fn_en_erken_mezuniyet_ben",
        "fn_aktif_donem_id",
        "fn_akts_limit",
    },
    "rol_danisman": {
        "fn_mezuniyet_ozet_danisan",
        "fn_mezuniyet_denetim_danisan",
        "fn_aktif_donem_id",
    },
    "rol_ogretim_uyesi": {
        "fn_aktif_donem_id",
    },
    "rol_sekreter": {
        "fn_aktif_donem_id",
    },
    "rol_yonetici": {
        "fn_aktif_donem_id",
        "fn_denetim_dogrula",
    },
}

# Doğrudan erişimi her zaman engellenen ham tablolar ve sistem şemaları
YASAKLI_ILISKILER: set[str] = {
    "kisi",
    "kisi_rol",
    "ogrenci",
    "ogretim_uyesi",
    "bolum",
    "program",
    "mufredat",
    "mufredat_grup",
    "mufredat_ders",
    "ders",
    "onkosul",
    "donem",
    "sube",
    "sube_saat",
    "ogrenci_slot",
    "kayit",
    "kayit_onay",
    "degerlendirme_bileseni",
    "not_kaydi",
    "kayit_sonuc",
    "yoklama",
    "danismanlik",
    "parametre",
    "harf_notu_aralik",
    "denetim_log",
    "belge",
    "model_surum",
    "risk_tahmin",
    "pg_catalog",
    "information_schema",
}

YASAKLI_ANAHTAR_KELIMELER = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"COPY|CALL|DO|EXECUTE|PREPARE|DEALLOCATE|VACUUM|ANALYZE|"
    r"SET|RESET|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|LOCK|LISTEN|NOTIFY|"
    r"PG_SLEEP|PG_READ_FILE|PG_LS_DIR|LO_IMPORT|LO_EXPORT| SET_CONFIG"
    r")\b",
    re.IGNORECASE,
)

ILISKI_YAKALAYICI = re.compile(
    r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*(\()?",
    re.IGNORECASE,
)

CTE_AD_YAKALAYICI = re.compile(
    r"(?:WITH|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s*\(",
    re.IGNORECASE,
)


class SqlGuvenlikHatasi(ValueError):
    """İzinli görünümler dışına çıkan veya salt-okunur kuralını ihlal eden SQL hatası."""


@dataclass
class SorguSonucu:
    """Güvenli SQL çalıştırıcısının döndürdüğü standart sonuç nesnesi."""

    sql: str
    sutunlar: list[str] = field(default_factory=list)
    satirlar: list[dict] = field(default_factory=list)
    sure_ms: float = 0.0
    kesildi: bool = False


class SemaKatalogu:
    """Rol bazında izinli görünüm ve fonksiyonların kataloğunu sunar."""

    @staticmethod
    def izinli_gorunumler(rol: str) -> dict[str, str]:
        return dict(ROL_IZINLI_GORUNUMLER.get(rol, {}))

    @staticmethod
    def izinli_fonksiyonlar(rol: str) -> set[str]:
        return set(ROL_IZINLI_FONKSIYONLAR.get(rol, set()))

    @classmethod
    def izinli_kaynaklar(cls, rol: str) -> set[str]:
        return set(cls.izinli_gorunumler(rol).keys()) | cls.izinli_fonksiyonlar(rol)


def _metin_sabitlerini_temizle(sql: str) -> str:
    """Tırnak içi sabit metinleri ve yorumları silerek güvenli anahtar kelime taraması sağlar."""
    s = re.sub(r"--[^\n]*", " ", sql)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.DOTALL)
    s = re.sub(r"'(?:''|[^'])*'", "''", s)
    return s


def sql_dogrula(sql: str, rol: str) -> str:
    """
    SQL sorgusunun salt-okunur olduğunu ve yalnızca `rol` için izin verilen
    görünüm/fonksiyonları kullandığını doğrular. Geçerli ise temizlenmiş SQL'i döndürür.
    """
    if not sql or not sql.strip():
        raise SqlGuvenlikHatasi("Boş sorgu çalıştırılamaz.")

    temiz = sql.strip().rstrip(";").strip()
    if not temiz:
        raise SqlGuvenlikHatasi("Boş sorgu çalıştırılamaz.")

    maskeli = _metin_sabitlerini_temizle(temiz)

    if ";" in maskeli:
        raise SqlGuvenlikHatasi("Çoklu SQL ifadelerine izin verilmez.")

    if not re.match(r"^\s*(SELECT|WITH)\b", maskeli, re.IGNORECASE):
        raise SqlGuvenlikHatasi("Yalnızca SELECT sorgularına izin verilir.")

    yasak_eslesme = YASAKLI_ANAHTAR_KELIMELER.search(maskeli)
    if yasak_eslesme:
        kelime = yasak_eslesme.group(1).upper()
        raise SqlGuvenlikHatasi(f"Salt-okunur modda '{kelime}' ifadesine izin verilmez.")

    if re.search(r"\bFOR\s+(UPDATE|SHARE|NO\s+KEY\s+UPDATE|KEY\s+SHARE)\b", maskeli, re.IGNORECASE):
        raise SqlGuvenlikHatasi("Satır kilitleme (FOR UPDATE/SHARE) ifadelerine izin verilmez.")

    cte_adlari = {m.group(1).lower() for m in CTE_AD_YAKALAYICI.finditer(maskeli)}
    izinli_gorunumler = {k.lower() for k in SemaKatalogu.izinli_gorunumler(rol)}
    izinli_fonksiyonlar = {f.lower() for f in SemaKatalogu.izinli_fonksiyonlar(rol)}

    if not izinli_gorunumler and not izinli_fonksiyonlar:
        raise SqlGuvenlikHatasi(f"'{rol}' rolü için tanımlı izinli görünüm bulunmuyor.")

    bulunan_kaynaklar: list[str] = []
    for eslesme in ILISKI_YAKALAYICI.finditer(maskeli):
        ham_ad = eslesme.group(1).lower()
        fonksiyon_mu = bool(eslesme.group(2))
        if "." in ham_ad:
            sema, ad = ham_ad.split(".", 1)
            if sema != "public":
                raise SqlGuvenlikHatasi(f"'{sema}' şemasına erişim izni yoktur.")
        else:
            ad = ham_ad

        if ad in cte_adlari:
            continue

        bulunan_kaynaklar.append(ad)
        if ad in YASAKLI_ILISKILER:
            raise SqlGuvenlikHatasi(
                f"'{ad}' tablosuna doğrudan erişim yasaktır; yalnızca izinli görünümler kullanılabilir."
            )

        if fonksiyon_mu:
            if ad not in izinli_fonksiyonlar:
                raise SqlGuvenlikHatasi(f"'{ad}()' fonksiyonu '{rol}' rolünün izin listesinde değil.")
        else:
            if ad not in izinli_gorunumler and ad not in izinli_fonksiyonlar:
                raise SqlGuvenlikHatasi(f"'{ad}' görünümü '{rol}' rolünün izin listesinde değil.")

    if not bulunan_kaynaklar:
        raise SqlGuvenlikHatasi("Sorgu en az bir izinli görünümden veri okumalıdır.")

    return temiz


def guvenli_sorgu_calistir(
    db,
    sql: str,
    params: tuple = (),
    maks_satir: int = 50,
    zaman_asimi_ms: int = 3000,
) -> SorguSonucu:
    """
    Doğrulanmış SQL sorgusunu READ ONLY işlemde, rol + RLS altında ve satır/süre
    sınırıyla çalıştırır.
    """
    rol = getattr(db, "aktif_rol", "obs_login")
    dogrulanmis_sql = sql_dogrula(sql, rol)

    baslangic = time.perf_counter()
    conn = db._baglanti_al()
    with conn.transaction():
        with conn.cursor() as cur:
            db._baglam_uygula(cur)
            cur.execute("SET LOCAL transaction_read_only = on")
            cur.execute(f"SET LOCAL statement_timeout = {int(zaman_asimi_ms)}")
            cur.execute(dogrulanmis_sql, params)
            sutunlar = [col.name for col in cur.description] if cur.description else []
            ham_satirlar = cur.fetchmany(maks_satir + 1) if cur.description else []

    sure_ms = round((time.perf_counter() - baslangic) * 1000.0, 1)
    kesildi = len(ham_satirlar) > maks_satir
    satirlar = [dict(r) for r in ham_satirlar[:maks_satir]]
    return SorguSonucu(
        sql=dogrulanmis_sql,
        sutunlar=sutunlar,
        satirlar=satirlar,
        sure_ms=sure_ms,
        kesildi=kesildi,
    )
