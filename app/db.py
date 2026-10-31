import os
import re
from collections import deque
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

_PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJE_KOK, ".env"))

HATA_SOZLUGU = {
    "ONKOSUL_EKSIK": "Önkoşul ders(ler)i tamamlanmamış",
    "ONKOSUL_DONGUSU": "Seçilen önkoşul ders grafında (DAG) döngü oluşturuyor",
    "MUFREDAT_DISI": "Bu ders müfredatınızda yer almıyor",
    "SAAT_CAKISMASI": "Seçilen şube mevcut ders programınızla çakışıyor",
    "CAKISMA": "Seçilen şube mevcut ders programınızla çakışıyor",
    "AKTS_ASIMI": "Dönemlik AKTS kredi sınırınızı aşıyorsunuz",
    "DONEM_KAPALI": "Kayıt / Ekle-Bırak takvimi dışındasınız",
    "TEKRAR_POLITIKASI": "Bu dersi tekrar alma koşulunu sağlamıyorsunuz",
    "GECERSIZ_GECIS": "İşlem kurala veya mevcut duruma uygun değil",
    "AGIRLIK_TOPLAMI": "Değerlendirme bileşenlerinin ağırlık toplamı 100 olmalıdır",
    "NOT_ILAN_EDILDI": "İlan edilmiş not doğrudan değiştirilemez; not düzeltme kullanın",
    "GEREKCE_ZORUNLU": "Bu işlem için zorunlu alan veya gerekçe eksiktir",
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

    if "AKTS_ASIMI" in msg:
        m = re.search(r"AKTS_ASIMI:\s*(\d+)\s*\+\s*(\d+)\s*>\s*limit\s*(\d+)", msg)
        if m:
            toplam = int(m.group(1)) + int(m.group(2))
            limit = int(m.group(3))
            return HATA_SABLONLARI["AKTS_ASIMI"].format(limit=limit, toplam=toplam)
        limit = baglam.get("limit", 30)
        toplam = baglam.get("toplam", 36)
        return HATA_SABLONLARI["AKTS_ASIMI"].format(limit=limit, toplam=toplam)

    if "ONKOSUL_EKSIK" in msg:
        detay = msg.split(":", 1)[1].strip() if ":" in msg else ""
        ders = baglam.get("ders") or "Seçilen ders"
        onkosul = baglam.get("onkosul") or detay or "ilgili önkoşul"
        harf = baglam.get("harf") or "CC"
        return HATA_SABLONLARI["ONKOSUL_EKSIK"].format(ders=ders, onkosul=onkosul, harf=harf)

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
    """
    PostgreSQL bağlantı ve oturum yöneticisi.
    Optimizasyon: Her sorguda yeni TCP bağlantısı açmak yerine kalıcı bağlantıyı
    (_conn) yeniden kullanır ve işlemleri atomik transaction bloklarında yürütür.
    """

    def __init__(self):
        self.dsn = os.getenv("DATABASE_URL", "postgresql://localhost/obs")
        self.conninfo = (
            f"host={os.getenv('DB_HOST', 'localhost')} "
            f"port={os.getenv('DB_PORT', '5431')} "
            f"dbname={os.getenv('DB_NAME', 'obs')} "
            f"user={os.getenv('DB_USER', 'obs_app')} "
            f"password={os.getenv('DB_PASSWORD', 'obs_pass')}"
        )
        self._conn: psycopg.Connection | None = None
        self.kisi_id: int | None = None
        self.ad_soyad: str = ""
        self.kullanici_no: str = ""
        self._sql_gecmisi: deque[tuple[str, tuple | None]] = deque(maxlen=50)
        self.aktif_rol: str = "obs_login"
        self.roller: list[str] = []

    @property
    def sql_gecmisi(self) -> list[tuple[str, tuple | None]]:
        return list(self._sql_gecmisi)

    def _baglanti_al(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed or self._conn.broken:
            self._conn = psycopg.connect(self.conninfo, row_factory=dict_row, autocommit=True)
        return self._conn

    def kapat(self):
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def oturum_ayarla(
        self,
        kisi_id: int,
        ad_soyad: str,
        roller: list[str],
        aktif_rol: str,
        kullanici_no: str = ""
    ):
        self.kisi_id = kisi_id
        self.ad_soyad = ad_soyad
        self.roller = roller
        self.aktif_rol = aktif_rol
        self.kullanici_no = kullanici_no

    def _baglam_uygula(self, cur):
        cur.execute(f"SET LOCAL ROLE {self.aktif_rol}")
        if self.kisi_id is not None:
            cur.execute("SELECT set_config('app.kullanici_id', %s, true)", (str(self.kisi_id),))

    def sorgula(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._baglanti_al()
        with conn.transaction():
            with conn.cursor() as cur:
                self._baglam_uygula(cur)
                self._sql_gecmisi.append((sql, params))
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    def tek_satir(self, sql: str, params: tuple = ()) -> dict | None:
        satirlar = self.sorgula(sql, params)
        return satirlar[0] if satirlar else None

    def calistir(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._baglanti_al()
        with conn.transaction():
            with conn.cursor() as cur:
                self._baglam_uygula(cur)
                self._sql_gecmisi.append((sql, params))
                cur.execute(sql, params)
                return cur.fetchall() if cur.description else []

    def demo_kullanicilar(self) -> list[dict]:
        conn = self._baglanti_al()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE obs_login")
                cur.execute("SELECT * FROM v_demo_kullanicilar")
                satirlar = cur.fetchall()

        sonuc = []
        ogr_sayac = 1
        aka_sayac = 1
        for k in satirlar:
            d = dict(k)
            roller = d.get("roller") or []
            if not d.get("giris_turu"):
                d["giris_turu"] = "ogrenci" if "rol_ogrenci" in roller else "akademisyen"
            if not d.get("kullanici_no"):
                if d["giris_turu"] == "ogrenci":
                    d["kullanici_no"] = f"2310{ogr_sayac}"
                    ogr_sayac += 1
                else:
                    d["kullanici_no"] = f"1010{aka_sayac}"
                    aka_sayac += 1
            if not d.get("sifre"):
                d["sifre"] = "123456"
            sonuc.append(d)
        return sonuc

    def kimlik_dogrula(self, giris_turu: str, kullanici_no: str, sifre: str) -> dict:
        """
        Öğrenci ('ogrenci') veya Akademisyen ('akademisyen') girişini
        5 haneli numara ve şifre ('123456') ile doğrular.
        """
        k_no = kullanici_no.strip()
        s_girilen = sifre.strip()
        if not k_no:
            raise ValueError("Lütfen 5 haneli numaranızı girin.")
        if not s_girilen:
            raise ValueError("Lütfen şifrenizi girin.")

        kullanicilar = self.demo_kullanicilar()
        eslesen = next(
            (
                u for u in kullanicilar
                if str(u.get("kullanici_no")) == k_no and u.get("giris_turu") == giris_turu
            ),
            None
        )
        if not eslesen:
            etiket = "Öğrenci numarası" if giris_turu == "ogrenci" else "Akademisyen / Personel numarası"
            raise ValueError(f"{etiket} ({k_no}) sistemde bulunamadı.")

        beklenen_sifre = str(eslesen.get("sifre") or "123456")
        if s_girilen != beklenen_sifre:
            raise ValueError("Girdiğiniz şifre hatalı. (Varsayılan şifre: 123456)")

        return eslesen
