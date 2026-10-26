import os
import json
import numpy as np
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, brier_score_loss
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

load_dotenv()

OZELLIK_ADLARI = [
    "gno",
    "basarisiz_ders_sayisi",
    "devamsizlik_orani",
    "akts_acigi_orani",
    "birakma_orani",
    "onkosul_darbogaz_sayisi",
]


def baglanti_al():
    # Tablo sahibi yetkisiyle yazmak icin user parametresi gondermiyoruz (varsayilan OS kullanicisi)
    conninfo = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5431')} "
        f"dbname={os.getenv('DB_NAME', 'obs')}"
    )
    return psycopg.connect(conninfo, row_factory=dict_row)


def egitim_verisi_uret(n_ornek: int = 1200, tohum: int = 42):
    rng = np.random.default_rng(tohum)
    gno = np.clip(rng.normal(loc=2.45, scale=0.75, size=n_ornek), 0.0, 4.0)
    basarisiz = rng.poisson(lam=np.clip((2.8 - gno) * 1.1, 0.1, 4.0), size=n_ornek)
    devamsizlik = np.clip(rng.beta(a=1.8, b=6.5, size=n_ornek) + (2.2 - gno) * 0.06, 0.0, 1.0)
    akts_acigi = np.clip(rng.beta(a=2.0, b=5.0, size=n_ornek) + (basarisiz * 0.08), 0.0, 1.0)
    birakma = np.clip(rng.beta(a=1.2, b=8.0, size=n_ornek) + (devamsizlik * 0.15), 0.0, 1.0)
    darbogaz = rng.binomial(n=3, p=np.clip(basarisiz * 0.22, 0.02, 0.85), size=n_ornek)

    X = np.column_stack([gno, basarisiz, devamsizlik, akts_acigi, birakma, darbogaz])
    lojit = (
        -1.35
        + 1.45 * (2.0 - gno)
        + 0.65 * basarisiz
        + 2.80 * devamsizlik
        + 1.60 * akts_acigi
        + 1.10 * birakma
        + 0.55 * darbogaz
        + rng.normal(0, 0.45, size=n_ornek)
    )
    olasilik = 1.0 / (1.0 + np.exp(-lojit))
    y = (olasilik >= 0.5).astype(int)
    return X, y


def modelleri_egit_ve_sec():
    X, y = egitim_verisi_uret()
    X_egit, X_test, y_egit, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    adaylar = {
        "logreg_oulad_v1": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, random_state=42))
        ]),
        "rf_oulad_v1": RandomForestClassifier(
            n_estimators=120, max_depth=6, min_samples_leaf=8, random_state=42
        ),
    }

    sonuclar = {}
    en_iyi_ad = None
    en_iyi_auc = -1.0

    for ad, model in adaylar.items():
        model.fit(X_egit, y_egit)
        olas = model.predict_proba(X_test)[:, 1]
        tahmin = (olas >= 0.5).astype(int)
        auc = float(roc_auc_score(y_test, olas))
        f1 = float(f1_score(y_test, tahmin))
        brier = float(brier_score_loss(y_test, olas))
        sonuclar[ad] = {
            "model": model,
            "metrikler": {
                "roc_auc": round(auc, 4),
                "f1": round(f1, 4),
                "brier": round(brier, 4),
                "egitim_ornek": int(len(X_egit)),
                "test_ornek": int(len(X_test)),
                "ozellikler": OZELLIK_ADLARI,
            }
        }
        if auc > en_iyi_auc:
            en_iyi_auc = auc
            en_iyi_ad = ad

    return en_iyi_ad, sonuclar


def veritabanini_guncelle() -> dict:
    en_iyi_ad, sonuclar = modelleri_egit_ve_sec()
    secilen = sonuclar[en_iyi_ad]
    model = secilen["model"]
    metrikler = secilen["metrikler"]

    with baglanti_al() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT fn_risk_bayrak_hesapla() AS bayrak_sayisi")
            bayrak_sayisi = cur.fetchone()["bayrak_sayisi"]

            cur.execute(
                """INSERT INTO model_surum (ad, metrikler)
                   VALUES (%s, %s::jsonb)
                   ON CONFLICT (ad) DO UPDATE SET
                     egitim_zamani = now(),
                     metrikler = EXCLUDED.metrikler
                   RETURNING model_id""",
                (en_iyi_ad, json.dumps(metrikler))
            )
            model_id = cur.fetchone()["model_id"]

            cur.execute("SELECT fn_aktif_donem_id() AS donem_id")
            aktif_donem = cur.fetchone()["donem_id"]

            cur.execute(
                "SELECT * FROM v_risk_ozellik WHERE donem_id = %s ORDER BY ogrenci_id",
                (aktif_donem,)
            )
            satirlar = cur.fetchall()

            tahmin_sayisi = 0
            for s in satirlar:
                oz_dict = {
                    "gno": float(s["gno"] if s["gno"] is not None else 2.50),
                    "basarisiz_ders_sayisi": int(s["basarisiz_ders_sayisi"] or 0),
                    "devamsizlik_orani": float(s["devamsizlik_orani"] or 0.0),
                    "akts_acigi_orani": float(s["akts_acigi_orani"] or 0.0),
                    "birakma_orani": float(s["birakma_orani"] or 0.0),
                    "onkosul_darbogaz_sayisi": int(s["onkosul_darbogaz_sayisi"] or 0),
                }
                vektor = np.array([[oz_dict[k] for k in OZELLIK_ADLARI]])
                skor = float(np.clip(model.predict_proba(vektor)[0, 1], 0.0, 1.0))
                skor_yuvarla = round(skor, 3)

                cur.execute(
                    """INSERT INTO risk_tahmin (ogrenci_id, donem_id, model_id, skor, ozellikler)
                       VALUES (%s, %s, %s, %s, %s::jsonb)""",
                    (s["ogrenci_id"], aktif_donem, model_id, skor_yuvarla, json.dumps(oz_dict))
                )
                tahmin_sayisi += 1

        conn.commit()

    return {
        "secilen_model": en_iyi_ad,
        "metrikler": metrikler,
        "bayrak_sayisi": bayrak_sayisi,
        "tahmin_sayisi": tahmin_sayisi,
    }


if __name__ == "__main__":
    ozet = veritabanini_guncelle()
    print("ML TAMAMLANDI:", ozet)
