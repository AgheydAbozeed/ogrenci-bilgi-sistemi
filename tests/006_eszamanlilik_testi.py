"""
tests/006_eszamanlilik_testi.py -- Asama D: AKTS Yaris Durumu (Race Condition) ve Satir Kilidi Kaniti
Iki paralel veritabani baglantisi (Thread) ayni milisaniyede (Barrier ile) ayni ogrencinin
sepetteki iki farkli 6 AKTS'lik dersini (BIL101 ve MAT101) kesinlestirmeye calisir.
Ogrencinin AKTS limiti 8'e dusurulmustur (6 + 6 = 12 > 8):
  1) akts_kilidi = 'acik' iken (FOR UPDATE aktif): Yalnizca 1 islem basarili olur, digeri AKTS_ASIMI alir.
  2) Test sonunda tum gecici degisiklikler temizlenir.
"""
import os
import threading
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

CONNINFO = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5431')} "
    f"dbname={os.getenv('DB_NAME', 'obs')}"
)


def hazirla(kilit_durumu: str) -> tuple[int, int, int, str]:
    with psycopg.connect(CONNINFO, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT deger FROM parametre WHERE anahtar = 'akts_limit_varsayilan'")
            eski_limit = cur.fetchone()["deger"]

            cur.execute("UPDATE parametre SET deger = '8' WHERE anahtar = 'akts_limit_varsayilan'")
            cur.execute("UPDATE parametre SET deger = %s WHERE anahtar = 'akts_kilidi'", (kilit_durumu,))

            cur.execute("SELECT kisi_id FROM ogrenci WHERE ogrenci_no = '2026001'")
            ogr_id = cur.fetchone()["kisi_id"]

            cur.execute("SELECT fn_aktif_donem_id() AS id")
            donem_id = cur.fetchone()["id"]

            # Ada'nin aktif donem kayitlarini temizle ve iki 6 AKTS'lik dersi sepete ekle
            cur.execute("DELETE FROM kayit WHERE ogrenci_id = %s AND donem_id = %s", (ogr_id, donem_id))

            cur.execute(
                """SELECT s.sube_id, d.kod FROM sube s
                   JOIN ders d ON d.ders_id = s.ders_id
                  WHERE s.donem_id = %s AND d.kod IN ('BIL101', 'MAT101')
                  ORDER BY d.kod""",
                (donem_id,)
            )
            subeler = cur.fetchall()

            cur.execute("SELECT set_config('app.kullanici_id', %s, true)", (str(ogr_id),))
            cur.execute("SELECT fn_sepete_ekle(%s) AS id", (subeler[0]["sube_id"],))
            k1 = cur.fetchone()["id"]
            cur.execute("SELECT fn_sepete_ekle(%s) AS id", (subeler[1]["sube_id"],))
            k2 = cur.fetchone()["id"]
        conn.commit()
    return ogr_id, k1, k2, eski_limit


def temizle(ogr_id: int, eski_limit: str):
    with psycopg.connect(CONNINFO) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM kayit WHERE ogrenci_id = %s AND donem_id = fn_aktif_donem_id()", (ogr_id,))
            cur.execute("UPDATE parametre SET deger = %s WHERE anahtar = 'akts_limit_varsayilan'", (eski_limit,))
            cur.execute("UPDATE parametre SET deger = 'acik' WHERE anahtar = 'akts_kilidi'")
        conn.commit()


def yaris_calistir(kilit_durumu: str) -> tuple[list[str], int]:
    ogr_id, k1, k2, eski_limit = hazirla(kilit_durumu)
    bariyer = threading.Barrier(2)
    sonuclar = []
    kilit = threading.Lock()

    def isci(kayit_id: int):
        with psycopg.connect(CONNINFO, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.kullanici_id', %s, true)", (str(ogr_id),))
                bariyer.wait()
                try:
                    cur.execute("SELECT fn_kesinlestir(%s)", (kayit_id,))
                    conn.commit()
                    with kilit:
                        sonuclar.append("BASARILI")
                except Exception as e:
                    conn.rollback()
                    with kilit:
                        sonuclar.append("AKTS_ASIMI" if "AKTS_ASIMI" in str(e) else f"HATA:{e}")

    try:
        t1 = threading.Thread(target=isci, args=(k1,))
        t2 = threading.Thread(target=isci, args=(k2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        with psycopg.connect(CONNINFO, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT coalesce(sum(d.akts), 0) AS toplam
                         FROM kayit k JOIN ders d ON d.ders_id = k.ders_id
                        WHERE k.ogrenci_id = %s AND k.donem_id = fn_aktif_donem_id()
                          AND k.durum = 'onay_bekliyor'""",
                    (ogr_id,)
                )
                toplam_akts = int(cur.fetchone()["toplam"])
        return sorted(sonuclar), toplam_akts
    finally:
        temizle(ogr_id, eski_limit)


if __name__ == "__main__":
    sonuclar, toplam_akts = yaris_calistir("acik")
    if sonuclar == ["AKTS_ASIMI", "BASARILI"] and toplam_akts == 6:
        print(f"PASS | Eszamanli AKTS kilidi (FOR UPDATE) yarisi engelledi | Sonuclar: {sonuclar} | Onay Bekleyen AKTS: {toplam_akts}/8")
    else:
        print(f"FAIL | Beklenen ['AKTS_ASIMI', 'BASARILI'] ve 6 AKTS | Gelen: {sonuclar}, {toplam_akts} AKTS")
        raise SystemExit(1)
