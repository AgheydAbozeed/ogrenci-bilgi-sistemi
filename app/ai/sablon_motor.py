"""
✦ Niyet Sınıflandırıcı ve Şablonlu SQL Sorgu Motoru (Çevrimdışı / LLM'siz).

Kullanıcının doğal dildeki sorusunu:
  1. Türkçe karakter ve noktalama normalize ederek anahtar kelime/kalıp puanlamasıyla sınıflandırır.
  2. Yalnızca kullanıcının aktif rolünün izinli görünümlerinden (`v_danisanlarim`,
     `v_acik_subeler`, `fn_en_erken_mezuniyet_ben()` vb.) salt-okunur bir SQL sorgusuna çevirir.
  3. Sorguyu `guvenli_sorgu_calistir` ile READ ONLY işlemde çalıştırır.
  4. Sonucu **tablo + tam iki cümlelik özet** + kullanılan SQL + güven yüzdesi olarak döndürür.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from app.ai.sql_koruma import SorguSonucu, SqlGuvenlikHatasi, guvenli_sorgu_calistir, sql_dogrula

VARSAYILAN_MODEL_SURUM = "model v1"

_TR_HARITA = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def metin_normallestir(metin: str) -> str:
    """Türkçe karakterleri ASCII karşılıklarına çevirir ve küçük harfe indirger."""
    kucuk = (metin or "").lower().translate(_TR_HARITA)
    return re.sub(r"\s+", " ", kucuk).strip()


def _ondalik_cikar(metin: str, varsayilan: float = 2.0) -> float:
    """Metin içindeki '2.0', '2,50', '2' gibi GNO eşik değerini yakalar."""
    norm = metin_normallestir(metin)
    eslesme = re.search(r"\b([0-4](?:[.,]\d{1,2})?)\b", norm)
    if not eslesme:
        return varsayilan
    deger = float(eslesme.group(1).replace(",", "."))
    return max(0.0, min(4.0, round(deger, 2)))


@dataclass
class AsistanYaniti:
    """AI Asistan'ın ürettiği yapılandırılmış yanıt."""

    niyet_kodu: str
    baslik: str
    cumle_1: str
    cumle_2: str
    sql: str
    sutunlar: list[str] = field(default_factory=list)
    satirlar: list[dict] = field(default_factory=list)
    guven: int = 85
    model_surum: str = VARSAYILAN_MODEL_SURUM
    sure_ms: float = 0.0
    oneriler: list[str] = field(default_factory=list)

    @property
    def iki_cumle_ozet(self) -> str:
        return f"{self.cumle_1} {self.cumle_2}".strip()


@dataclass
class NiyetSablonu:
    kod: str
    roller: set[str]
    baslik: str
    ornek_soru: str
    anahtar_kaliplar: list[tuple[str, int]]
    sql_uret: Callable[[str], tuple[str, dict]]
    ozet_uret: Callable[[list[dict], dict], tuple[str, str]]


# =====================================================================
# Özet (2 Cümle) Üreticileri
# =====================================================================
def _ozet_ogrenci_alinabilir(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    toplam_akts = sum(int(s.get("akts") or 0) for s in satirlar)
    if satirlar:
        c1 = f"Bu dönem önkoşul ve saat çakışması engeli olmadan alabileceğiniz {len(satirlar)} şube (toplam {toplam_akts} AKTS) bulundu."
        c2 = "Tablodaki şubelerden uygun olanları ders seçimi ekranından sepetinize ekleyip kesinleştirebilirsiniz."
    else:
        c1 = "Bu dönem doğrudan alınabilir durumda açık şube bulunmadı."
        c2 = "Ders seçimi ekranından önkoşul veya çakışma durumlarını kontrol edebilirsiniz."
    return c1, c2


def _ozet_ogrenci_mezuniyet(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    if not satirlar:
        return (
            "Kalan zorunlu dersiniz bulunmuyor; mezuniyet ders planınız tamamlanmış görünüyor.",
            "Müfredat grup denetimini ve GNO koşulunu mezuniyet ekranından kontrol edebilirsiniz.",
        )
    son_donem = max(int(s.get("donem_sira") or 1) for s in satirlar)
    toplam_akts = sum(int(s.get("akts") or 0) for s in satirlar)
    c1 = f"En erken mezuniyet simülasyonuna göre kalan zorunlu derslerinizi {son_donem} dönemde ({len(satirlar)} ders, toplam {toplam_akts} AKTS) tamamlayabilirsiniz."
    c2 = "Bu plan önkoşul zincirleri (DAG kritik yolu) ve dönemlik AKTS tavanı dikkate alınarak hesaplanmıştır."
    return c1, c2


def _ozet_ogrenci_durum(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    if not satirlar:
        return (
            "Akademik özet bilginiz şu anda okunamadı.",
            "Lütfen aktif öğrenci oturumunuzu kontrol edin.",
        )
    s = satirlar[0]
    gno = s.get("gno") if s.get("gno") is not None else "-"
    akts = s.get("gecilen_akts") or 0
    sinif = s.get("sinif") or "-"
    c1 = f"Mevcut akademik durumunuz: {sinif}. sınıf, genel not ortalamanız (GNO) {gno} ve tamamlanan krediniz {akts} AKTS'dir."
    c2 = f"Aktif dönem ({s.get('aktif_donem') or '-'}) kayıt durumu tabloda ayrıntılı olarak gösterilmiştir."
    return c1, c2


def _ozet_ogrenci_program(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    ders_sayisi = len({s.get("ders_kod") for s in satirlar if s.get("ders_kod")})
    c1 = f"Haftalık programınızda {ders_sayisi} farklı derse ait toplam {len(satirlar)} ders saati yer alıyor."
    c2 = "Tabloda gün, saat dilimi ve kayıt onay durumlarını birlikte inceleyebilirsiniz."
    return c1, c2


def _ozet_ogrenci_transkript(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    gecilen = sum(1 for s in satirlar if s.get("durum") == "gecti")
    kalinan = sum(1 for s in satirlar if s.get("durum") == "kaldi")
    c1 = f"Transkriptinizde sonuçlanmış toplam {len(satirlar)} ders kaydı ({gecilen} geçti, {kalinan} kaldı) bulunmaktadır."
    c2 = "Derslerin dönem, AKTS, harf notu ve katsayı dökümü aşağıdaki tabloda sıralanmıştır."
    return c1, c2


def _ozet_ogrenci_engelli_subeler(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    c1 = f"Bu dönem önkoşul eksikliği veya saat çakışması nedeniyle kilitli olan {len(satirlar)} şube tespit edildi."
    c2 = "Her şubenin engel nedeni tabloda belirtilmiştir; önkoşul haritasından kritik yolu inceleyebilirsiniz."
    return c1, c2


def _ozet_danisman_dusuk_gno(satirlar: list[dict], p: dict) -> tuple[str, str]:
    esik = p.get("esik", 2.0)
    c1 = f"GNO'su {esik:.2f} eşiğinin altında olan {len(satirlar)} danışan öğrenci tespit edildi."
    c2 = "Bu çıktı yalnızca danışman bilgilendirmesi içindir; öğrencilerin ders yükünü ve mezuniyet denetimini birlikte değerlendirebilirsiniz."
    return c1, c2


def _ozet_danisman_tum(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    gnolar = [float(s["gno"]) for s in satirlar if s.get("gno") is not None]
    ort = f"{sum(gnolar) / len(gnolar):.2f}" if gnolar else "-"
    c1 = f"Üzerinize tanımlı toplam {len(satirlar)} aktif danışan öğrenci bulunmaktadır (ortalama GNO: {ort})."
    c2 = "Danışanlarınızın GNO ve geçilen AKTS bilgileri aşağıda listelenmiştir."
    return c1, c2


def _ozet_danisman_onay(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    toplam_akts = sum(int(s.get("akts") or 0) for s in satirlar)
    c1 = f"Onay kuyruğunuzda karar bekleyen {len(satirlar)} ders seçimi (toplam {toplam_akts} AKTS) bulunuyor."
    c2 = "Onay Kuyruğu ekranından talepleri onaylayabilir veya gerekçe girerek reddedebilirsiniz."
    return c1, c2


def _ozet_hoca_subeler(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    toplam_ogr = sum(int(s.get("ogrenci_sayisi") or 0) for s in satirlar)
    c1 = f"Bu dönem yürüttüğünüz {len(satirlar)} şubede toplam {toplam_ogr} kayıtlı öğrenci bulunmaktadır."
    c2 = "Şubelerim ekranından değerlendirme bileşenlerini tanımlayabilir ve not/yoklama girişi yapabilirsiniz."
    return c1, c2


def _ozet_hoca_notlar(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    c1 = f"Şubelerinizde girilmiş toplam {len(satirlar)} değerlendirme bileşeni not kaydı listelendi."
    c2 = "İlan durumu ve bileşen ağırlıklarını tablodan kontrol edebilirsiniz."
    return c1, c2


def _ozet_sekreter_mufredat(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    c1 = f"Sistemde tanımlı {len(satirlar)} program müfredatı görüntülenmektedir."
    c2 = "Sekreterlik ekranından danışman atamalarını ve dönem işlemlerini yönetebilirsiniz."
    return c1, c2


def _ozet_yonetici_parametre(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    c1 = f"Veritabanında aktif olan {len(satirlar)} yönetmelik ve sistem parametresi listelendi."
    c2 = "Parametre değişiklikleri SHA-256 zincirli denetim loguna otomatik olarak kaydedilir."
    return c1, c2


def _ozet_yonetici_denetim(satirlar: list[dict], _p: dict) -> tuple[str, str]:
    c1 = f"Denetim izi tablosundaki en güncel {len(satirlar)} işlem kaydı getirildi."
    c2 = "Yönetici panelinden SHA-256 hash zincirinin bütünlüğünü doğrulayabilirsiniz."
    return c1, c2


# =====================================================================
# Şablon Kataloğu
# =====================================================================
NIYET_SABLONLARI: list[NiyetSablonu] = [
    # --- DANIŞMAN ---
    NiyetSablonu(
        kod="danisman_dusuk_gno",
        roller={"rol_danisman"},
        baslik="GNO Eşiği Altındaki Danışanlar",
        ornek_soru="GNO'su 2'nin altındaki danışanlarım kimler?",
        anahtar_kaliplar=[
            ("gno", 3),
            ("altinda", 4),
            ("altindaki", 4),
            ("dusuk", 3),
            ("2", 2),
            ("risk", 2),
            ("kritik", 2),
            ("danisan", 2),
        ],
        sql_uret=lambda soru: (
            f"SELECT ogrenci_no, ad_soyad, gno, gecilen_akts "
            f"FROM v_danisanlarim "
            f"WHERE gno < {_ondalik_cikar(soru, 2.0):.2f} "
            f"ORDER BY gno ASC, ogrenci_no ASC",
            {"esik": _ondalik_cikar(soru, 2.0)},
        ),
        ozet_uret=_ozet_danisman_dusuk_gno,
    ),
    NiyetSablonu(
        kod="danisman_onay_kuyrugu",
        roller={"rol_danisman"},
        baslik="Onay Bekleyen Ders Kayıtları",
        ornek_soru="Onay bekleyen ders kayıtları hangileri?",
        anahtar_kaliplar=[
            ("onay", 5),
            ("bekleyen", 4),
            ("kuyruk", 4),
            ("kuyrugu", 4),
            ("talep", 2),
        ],
        sql_uret=lambda _soru: (
            "SELECT ogrenci_no, ad_soyad, ders_kod, ders_ad, akts, gno "
            "FROM v_onay_kuyrugu ORDER BY olusturma ASC",
            {},
        ),
        ozet_uret=_ozet_danisman_onay,
    ),
    NiyetSablonu(
        kod="danisman_tum_danisanlar",
        roller={"rol_danisman"},
        baslik="Aktif Danışan Öğrenci Listesi",
        ornek_soru="Tüm danışanlarımın GNO ve AKTS durumu nedir?",
        anahtar_kaliplar=[
            ("danisanlarim", 4),
            ("danisan", 3),
            ("tum", 2),
            ("liste", 3),
            ("kimler", 2),
            ("akts", 2),
        ],
        sql_uret=lambda _soru: (
            "SELECT ogrenci_no, ad_soyad, gno, gecilen_akts "
            "FROM v_danisanlarim ORDER BY ogrenci_no ASC",
            {},
        ),
        ozet_uret=_ozet_danisman_tum,
    ),
    # --- ÖĞRENCİ ---
    NiyetSablonu(
        kod="ogrenci_alinabilir_dersler",
        roller={"rol_ogrenci"},
        baslik="Bu Dönem Alınabilir Şubeler",
        ornek_soru="Bu dönem hangi dersleri alabilirim?",
        anahtar_kaliplar=[
            ("hangi ders", 5),
            ("alabilirim", 5),
            ("alinabilir", 5),
            ("bu donem", 3),
            ("acik sube", 3),
            ("secilebilir", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT ders_kod, ders_ad, akts, sube_no, hoca, saatler "
            "FROM v_acik_subeler "
            "WHERE durum = 'alinabilir' "
            "ORDER BY ders_kod ASC, sube_no ASC",
            {},
        ),
        ozet_uret=_ozet_ogrenci_alinabilir,
    ),
    NiyetSablonu(
        kod="ogrenci_mezuniyet_zamani",
        roller={"rol_ogrenci"},
        baslik="En Erken Mezuniyet Planı",
        ornek_soru="Ne zaman mezun olurum?",
        anahtar_kaliplar=[
            ("ne zaman", 5),
            ("mezun", 5),
            ("mezuniyet", 5),
            ("kac donem", 4),
            ("biter", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT donem_sira, ders_kod, ders_ad, akts "
            "FROM fn_ders_plani_ben() "
            "ORDER BY donem_sira ASC, ders_kod ASC",
            {},
        ),
        ozet_uret=_ozet_ogrenci_mezuniyet,
    ),
    NiyetSablonu(
        kod="ogrenci_akademik_ozet",
        roller={"rol_ogrenci"},
        baslik="Akademik Durum ve GNO Özeti",
        ornek_soru="GNO ve tamamladığım AKTS durumum nedir?",
        anahtar_kaliplar=[
            ("gno", 4),
            ("dno", 4),
            ("ortalama", 4),
            ("kac akts", 3),
            ("durumum", 3),
            ("ozet", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT sinif, gno, dno, gecilen_akts, aktif_donem, kayit_acik "
            "FROM v_ana_sayfa",
            {},
        ),
        ozet_uret=_ozet_ogrenci_durum,
    ),
    NiyetSablonu(
        kod="ogrenci_haftalik_program",
        roller={"rol_ogrenci"},
        baslik="Haftalık Ders Programım",
        ornek_soru="Haftalık ders programım nasıl?",
        anahtar_kaliplar=[
            ("haftalik", 5),
            ("program", 4),
            ("saat", 3),
            ("takvim", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT gun, ders_saati, ders_kod, sube_no, durum "
            "FROM v_haftalik_program "
            "ORDER BY gun ASC, ders_saati ASC",
            {},
        ),
        ozet_uret=_ozet_ogrenci_program,
    ),
    NiyetSablonu(
        kod="ogrenci_transkript",
        roller={"rol_ogrenci"},
        baslik="Transkript ve Harf Notlarım",
        ornek_soru="Transkriptimde hangi dersler ve harf notları var?",
        anahtar_kaliplar=[
            ("transkript", 5),
            ("harf", 4),
            ("notlarim", 4),
            ("gecmis ders", 3),
            ("kaldigim", 3),
            ("gectigim", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT yil, donem, kod, ders_adi, akts, harf, katsayi, durum "
            "FROM v_transkript "
            "ORDER BY yil DESC, kod ASC",
            {},
        ),
        ozet_uret=_ozet_ogrenci_transkript,
    ),
    NiyetSablonu(
        kod="ogrenci_engelli_subeler",
        roller={"rol_ogrenci"},
        baslik="Önkoşul / Çakışma Engelli Şubeler",
        ornek_soru="Hangi derslerde önkoşul eksiğim veya çakışmam var?",
        anahtar_kaliplar=[
            ("onkosul", 5),
            ("cakisma", 5),
            ("cakisiyor", 4),
            ("eksik", 3),
            ("alamadigim", 4),
            ("kilitli", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT ders_kod, ders_ad, akts, durum, neden "
            "FROM v_acik_subeler "
            "WHERE durum IN ('onkosul_eksik', 'cakisiyor') "
            "ORDER BY ders_kod ASC",
            {},
        ),
        ozet_uret=_ozet_ogrenci_engelli_subeler,
    ),
    # --- ÖĞRETİM ÜYESİ ---
    NiyetSablonu(
        kod="hoca_subelerim",
        roller={"rol_ogretim_uyesi"},
        baslik="Yürüttüğüm Şubeler",
        ornek_soru="Bu dönem hangi şubeleri yürütüyorum?",
        anahtar_kaliplar=[
            ("sube", 4),
            ("ders", 3),
            ("ogrenci sayisi", 4),
            ("yuruttugum", 4),
        ],
        sql_uret=lambda _soru: (
            "SELECT ders_kod, ders_ad, sube_no, ogrenci_sayisi "
            "FROM v_sube_listem ORDER BY ders_kod ASC, sube_no ASC",
            {},
        ),
        ozet_uret=_ozet_hoca_subeler,
    ),
    NiyetSablonu(
        kod="hoca_not_detay",
        roller={"rol_ogretim_uyesi"},
        baslik="Şube Değerlendirme ve Not Kayıtları",
        ornek_soru="Şubelerimdeki not ve bileşen durumu nedir?",
        anahtar_kaliplar=[
            ("not", 4),
            ("bilesen", 4),
            ("vize", 3),
            ("final", 3),
            ("puan", 3),
        ],
        sql_uret=lambda _soru: (
            "SELECT ders_kod, bilesen, agirlik, puan, ilan_edildi "
            "FROM v_not_detay ORDER BY ders_kod ASC, bilesen ASC",
            {},
        ),
        ozet_uret=_ozet_hoca_notlar,
    ),
    # --- SEKRETER ---
    NiyetSablonu(
        kod="sekreter_mufredatlar",
        roller={"rol_sekreter"},
        baslik="Program Müfredat Listesi",
        ornek_soru="Sistemde hangi program müfredatları tanımlı?",
        anahtar_kaliplar=[
            ("mufredat", 5),
            ("program", 4),
            ("bolum", 3),
            ("liste", 2),
        ],
        sql_uret=lambda _soru: (
            "SELECT mufredat_id, program, giris_yili "
            "FROM v_mufredat_listesi ORDER BY giris_yili DESC",
            {},
        ),
        ozet_uret=_ozet_sekreter_mufredat,
    ),
    # --- YÖNETİCİ ---
    NiyetSablonu(
        kod="yonetici_parametreler",
        roller={"rol_yonetici"},
        baslik="Sistem Yönetmelik Parametreleri",
        ornek_soru="Sistem parametreleri ve AKTS limitleri nelerdir?",
        anahtar_kaliplar=[
            ("parametre", 5),
            ("ayar", 3),
            ("limit", 4),
            ("yonetmelik", 4),
        ],
        sql_uret=lambda _soru: (
            "SELECT anahtar, deger, aciklama "
            "FROM v_parametreler ORDER BY anahtar ASC",
            {},
        ),
        ozet_uret=_ozet_yonetici_parametre,
    ),
    NiyetSablonu(
        kod="yonetici_denetim_log",
        roller={"rol_yonetici"},
        baslik="Son Denetim Log Kayıtları",
        ornek_soru="Son denetim log kayıtlarında neler var?",
        anahtar_kaliplar=[
            ("denetim", 5),
            ("log", 5),
            ("hash", 3),
            ("iz", 2),
        ],
        sql_uret=lambda _soru: (
            "SELECT log_id, zaman, kullanici, tablo, islem, kayit_pk "
            "FROM v_denetim_log ORDER BY log_id DESC LIMIT 20",
            {},
        ),
        ozet_uret=_ozet_yonetici_denetim,
    ),
]


def rol_ornek_sorulari(rol: str) -> list[str]:
    """Aktif rol için hazır öneri sorularını döndürür."""
    sorular = [s.ornek_soru for s in NIYET_SABLONLARI if rol in s.roller]
    return sorular[:4]


def niyet_siniflandir(soru: str, rol: str) -> tuple[NiyetSablonu, int]:
    """
    Soruyu aktif rolün şablonları arasında puanlayarak en uygun `NiyetSablonu`
    ve güven yüzdesini (%65–%96) döndürür.
    """
    adaylar = [s for s in NIYET_SABLONLARI if rol in s.roller]
    if not adaylar:
        raise SqlGuvenlikHatasi(f"'{rol}' rolü için tanımlı soru şablonu bulunmuyor.")

    norm = metin_normallestir(soru)
    en_iyi_sablon = adaylar[0]
    en_iyi_puan = -1

    for sablon in adaylar:
        puan = 0
        for kalip, agirlik in sablon.anahtar_kaliplar:
            if kalip in norm:
                puan += agirlik
        if metin_normallestir(sablon.ornek_soru) == norm:
            puan += 12
        if puan > en_iyi_puan:
            en_iyi_puan = puan
            en_iyi_sablon = sablon

    if en_iyi_puan <= 0:
        guven = 68
    else:
        guven = min(96, 74 + en_iyi_puan * 3)
    return en_iyi_sablon, guven


class SablonSorguMotoru:
    """
    LLM gerektirmeyen, niyet sınıflandırıcı + izinli görünüm şablonlarıyla çalışan
    AI Asistan sorgu motoru.
    """

    def __init__(self, db, model_surum: str = VARSAYILAN_MODEL_SURUM):
        self.db = db
        self.model_surum = model_surum

    def ornek_sorular(self) -> list[str]:
        rol = getattr(self.db, "aktif_rol", "rol_ogrenci")
        return rol_ornek_sorulari(rol)

    def _aktif_model_adi(self) -> str:
        return self.model_surum

    def yanitla(self, soru: str) -> AsistanYaniti:
        rol = getattr(self.db, "aktif_rol", "rol_ogrenci")
        sablon, guven = niyet_siniflandir(soru, rol)
        ham_sql, parametreler = sablon.sql_uret(soru)
        dogrulanmis_sql = sql_dogrula(ham_sql, rol)

        sonuc: SorguSonucu = guvenli_sorgu_calistir(self.db, dogrulanmis_sql)
        cumle_1, cumle_2 = sablon.ozet_uret(sonuc.satirlar, parametreler)
        oneriler = [s for s in rol_ornek_sorulari(rol) if s != sablon.ornek_soru][:3]

        return AsistanYaniti(
            niyet_kodu=sablon.kod,
            baslik=sablon.baslik,
            cumle_1=cumle_1,
            cumle_2=cumle_2,
            sql=sonuc.sql,
            sutunlar=sonuc.sutunlar,
            satirlar=sonuc.satirlar,
            guven=guven,
            model_surum=self._aktif_model_adi(),
            sure_ms=sonuc.sure_ms,
            oneriler=oneriler,
        )
