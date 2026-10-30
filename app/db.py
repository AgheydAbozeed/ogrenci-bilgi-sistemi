import os
import re
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

HATA_SOZLUGU = {
    "ONKOSUL_EKSIK": "Önkoşul ders(ler)i tamamlanmamış",
    "MUFREDAT_DISI": "Bu ders müfredatınızda yer almıyor",
    "SAAT_CAKISMASI": "Seçilen şube mevcut ders programınızla çakışıyor",
    "CAKISMA": "Seçilen şube mevcut ders programınızla çakışıyor",
    "AKTS_ASIMI": "Dönemlik AKTS kredi sınırınızı aşıyorsunuz",
    "DONEM_KAPALI": "Kayıt / Ekle-Bırak takvimi dışındasınız",
    "TEKRAR_POLITIKASI": "Bu dersi tekrar alma koşulunu sağlamıyorsunuz",
    "GECERSIZ_GECIS": "Kayıt durumu bu işleme uygun değil",
    "AGIRLIK_TOPLAMI": "Değerlendirme bileşenlerinin ağırlık toplamı 100 olmalıdır",
    "NOT_ILAN_EDILDI": "İlan edilmiş not doğrudan değiştirilemez; not düzeltme kullanın",
    "GEREKCE_ZORUNLU": "Bu işlem için gerekçe girilmesi zorunludur",
    "YETKISIZ": "Bu işlem için yetkiniz bulunmuyor",
    "KAYIT_BULUNAMADI": "İlgili kayıt bulunamadı",
    "SUBE_BULUNAMADI": "İlgili şube bulunamadı",
}

HATA_SABLONLARI = {
    "AKTS_ASIMI": "Bu dönem en fazla {limit} AKTS alabilirsiniz; şu an {toplam}. Bir ders çıkarın.",
    "ONKOSUL_EKSIK": "{ders} için önce {onkosul} dersini en az {harf} ile geçmelisiniz.",
    "CAKISMA": "{ders}, {gun} {saat}. saatte {diger} ile çakışıyor.",
    "BOS_SEPET": "Sepetiniz boş. Soldaki listeden bir şube seçin.",
}


def hata_coz(exc: Exception, baglam: dict | None = None) -> str:
    """
    Teknik veritabanı hatalarını kullanıcı dilindeki mesaj şablonlarına dönüştürür.
    """
    msg = str(exc).splitlines()[0]
    baglam = baglam or {}

    # 1) AKTS_ASIMI: v_toplam + v_akts > limit v_limit
    if "AKTS_ASIMI" in msg:
        m = re.search(r"AKTS_ASIMI:\s*(\d+)\s*\+\s*(\d+)\s*>\s*limit\s*(\d+)", msg)
        if m:
            toplam = int(m.group(1)) + int(m.group(2))
            limit = int(m.group(3))
            return HATA_SABLONLARI["AKTS_ASIMI"].format(limit=limit, toplam=toplam)
        limit = baglam.get("limit", 30)
        toplam = baglam.get("toplam", 36)
        return HATA_SABLONLARI["AKTS_ASIMI"].format(limit=limit, toplam=toplam)

    # 2) ONKOSUL_EKSIK
    if "ONKOSUL_EKSIK" in msg:
        detay = msg.split(":", 1)[1].strip() if ":" in msg else ""
        ders = baglam.get("ders") or "Seçilen ders"
        onkosul = baglam.get("onkosul") or detay or "ilgili önkoşul"
        harf = baglam.get("harf") or "CC"
        return HATA_SABLONLARI["ONKOSUL_EKSIK"].format(ders=ders, onkosul=onkosul, harf=harf)

    # 3) CAKISMA / SAAT_CAKISMASI / ogrenci_slot tekillik kısıtı
    if "CAKISMA" in msg or "SAAT_CAKISMASI" in msg or "ogrenci_slot" in msg:
        ders = baglam.get("ders") or "Seçilen şube"
        gun = baglam.get("gun") or "ilgili gün"
        saat = baglam.get("saat") or "ilgili"
        diger = baglam.get("diger") or "mevcut dersiniz"
        return HATA_SABLONLARI["CAKISMA"].format(ders=ders, gun=gun, saat=saat, diger=diger)

    for kod, aciklama in HATA_SOZLUGU.items():
        if kod in msg:
            detay = msg.split(":", 1)[1].strip() if ":" in msg else ""
            return f"{aciklama}" + (f" ({detay})" if detay else "")
    return msg


def hata_goster(parent, baslik: str, exc: Exception, baglam: dict | None = None):
    """
    Kullanıcı dilindeki mesajı ana metinde gösterir; teknik hata kodunu ve
    PostgreSQL ayrıntısını katlanır 'Ayrıntıları Göster' (setDetailedText) bölümünde tutar.
    """
    from PySide6.QtWidgets import QMessageBox

    kullanici_mesaji = hata_coz(exc, baglam)
    teknik_metin = str(exc).strip()

    kutu = QMessageBox(parent)
    kutu.setIcon(QMessageBox.Warning)
    kutu.setWindowTitle(baslik)
    kutu.setText(kullanici_mesaji)
    if teknik_metin:
        kutu.setInformativeText("Teknik hata kodu katlanır ayrıntıda tutulmaktadır.")
        kutu.setDetailedText(f"Teknik Hata Ayrıntısı:\n{teknik_metin}")
    kutu.exec()


class Veritabani:
    def __init__(self):
        self.dsn = os.getenv("DATABASE_URL", "postgresql://localhost/obs")
        self.conninfo = (
            f"host={os.getenv('DB_HOST', 'localhost')} "
            f"port={os.getenv('DB_PORT', '5431')} "
            f"dbname={os.getenv('DB_NAME', 'obs')} "
            f"user={os.getenv('DB_USER', 'obs_app')} "
            f"password={os.getenv('DB_PASSWORD', 'obs_pass')}"
        )
        self.kisi_id: int | None = None
        self.ad_soyad: str = ""
        self.sql_gecmisi: list[tuple[str, tuple | None]] = []
        self.aktif_rol: str = "obs_login"
        self.roller: list[str] = []

    def oturum_ayarla(self, kisi_id: int, ad_soyad: str, roller: list[str], aktif_rol: str):
        self.kisi_id = kisi_id
        self.ad_soyad = ad_soyad
        self.roller = roller
        self.aktif_rol = aktif_rol

    def _baglam_uygula(self, cur):
        cur.execute(f"SET LOCAL ROLE {self.aktif_rol}")
        if self.kisi_id is not None:
            cur.execute("SELECT set_config('app.kullanici_id', %s, true)", (str(self.kisi_id),))

    def sorgula(self, sql: str, params: tuple = ()) -> list[dict]:
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                self._baglam_uygula(cur)
                self.sql_gecmisi.append((sql, params))
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    def tek_satir(self, sql: str, params: tuple = ()) -> dict | None:
        satirlar = self.sorgula(sql, params)
        return satirlar[0] if satirlar else None

    def calistir(self, sql: str, params: tuple = ()) -> list[dict]:
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                self._baglam_uygula(cur)
                self.sql_gecmisi.append((sql, params))
                cur.execute(sql, params)
                sonuc = cur.fetchall() if cur.description else []
            conn.commit()
            return sonuc

    def demo_kullanicilar(self) -> list[dict]:
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE obs_login")
                cur.execute("SELECT kisi_id, ad_soyad, roller FROM v_demo_kullanicilar")
                return cur.fetchall()
