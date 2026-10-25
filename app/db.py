import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

HATA_SOZLUGU = {
    "ONKOSUL_EKSIK": "Önkoşul ders(ler)i tamamlanmamış",
    "MUFREDAT_DISI": "Bu ders müfredatınızda yer almıyor",
    "SAAT_CAKISMASI": "Seçilen şube mevcut ders programınızla çakışıyor",
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

def hata_coz(exc: Exception) -> str:
    msg = str(exc).splitlines()[0]
    for kod, aciklama in HATA_SOZLUGU.items():
        if kod in msg:
            detay = msg.split(":", 1)[1].strip() if ":" in msg else ""
            return f"{aciklama}" + (f" ({detay})" if detay else "")
    return msg

class Veritabani:
    def __init__(self):
        self.conninfo = (
            f"host={os.getenv('DB_HOST', 'localhost')} "
            f"port={os.getenv('DB_PORT', '5431')} "
            f"dbname={os.getenv('DB_NAME', 'obs')} "
            f"user={os.getenv('DB_USER', 'obs_app')} "
            f"password={os.getenv('DB_PASSWORD', 'obs_pass')}"
        )
        self.kisi_id: int | None = None
        self.ad_soyad: str = ""
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
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    def tek_satir(self, sql: str, params: tuple = ()) -> dict | None:
        satirlar = self.sorgula(sql, params)
        return satirlar[0] if satirlar else None

    def calistir(self, sql: str, params: tuple = ()) -> list[dict]:
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                self._baglam_uygula(cur)
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
