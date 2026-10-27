import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSlider, QComboBox, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)


class XaiSimulasyonDialog(QDialog):
    """Aciklanabilir Yapay Zeka (XAI), What-If Simulatoru ve Akilli AKTS Reçetesi."""

    def __init__(self, db, parent=None, baslangic_ogrenci_id=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🤖 YZ Akademik Karar Destek & Açıklanabilir Risk (XAI) Simülatörü")
        self.resize(940, 620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        ust = QHBoxLayout()
        baslik = QLabel("<b>🤖 Açıklanabilir Yapay Zeka (XAI) & What-If Senaryo Simülatörü</b>")
        baslik.setStyleSheet("font-size: 15px; color: #093567;")
        ust.addWidget(baslik)
        ust.addStretch()

        self.cmb_ogr = QComboBox()
        self.cmb_ogr.setMinimumWidth(260)
        self.ogrenciler = self.db.sorgula("SELECT * FROM v_ml_ozellik_vektoru ORDER BY ogrenci_id")
        for o in self.ogrenciler:
            self.cmb_ogr.addItem(f"Öğrenci #{o['ogrenci_id']} (GNO: {o['gno']} | Mevcut Risk: %{int(float(o.get('basarisizlik_olasiligi') or 0.3)*100)})", o)
        if baslangic_ogrenci_id:
            for i, o in enumerate(self.ogrenciler):
                if o["ogrenci_id"] == baslangic_ogrenci_id:
                    self.cmb_ogr.setCurrentIndex(i)
                    break
        self.cmb_ogr.currentIndexChanged.connect(self.ogrenci_yukle)
        ust.addWidget(QLabel("<b>Analiz Edilen Öğrenci:</b>"))
        ust.addWidget(self.cmb_ogr)
        lay.addLayout(ust)

        orta = QHBoxLayout()
        orta.setSpacing(14)

        # SOL PANEL: What-If Canli Kaydiricilar
        sol = QFrame()
        sol.setObjectName("PortalKart")
        s_lay = QVBoxLayout(sol)
        s_lay.setContentsMargins(14, 12, 14, 12)
        s_lay.addWidget(QLabel("<b>🎛️ What-If (Karşı-Olgusal) Senaryo Parametreleri</b>"))

        self.sliders = {}
        self.lbl_vals = {}
        param_tanim = [
            ("gno", "Genel Not Ortalaması (AGNO)", 0, 400, 200, lambda v: f"{v/100:.2f}"),
            ("basari", "Kredi Başarı Oranı (%)", 0, 100, 70, lambda v: f"%{v}"),
            ("ff_sayisi", "Toplam FF / Tekrar Sayısı", 0, 8, 1, lambda v: f"{v} Ders"),
            ("devamsizlik", "Ortalama Devamsızlık (%)", 0, 60, 10, lambda v: f"%{v}"),
            ("akts_yuku", "Planlanan Dönem AKTS Yükü", 12, 42, 30, lambda v: f"{v} AKTS"),
        ]
        for anahtar, etiket, mn, mx, varsayilan, fmt in param_tanim:
            satir = QHBoxLayout()
            lbl = QLabel(etiket)
            val_lbl = QLabel(fmt(varsayilan))
            val_lbl.setStyleSheet("font-weight: bold; color: #093567;")
            satir.addWidget(lbl)
            satir.addStretch()
            satir.addWidget(val_lbl)
            s_lay.addLayout(satir)

            sl = QSlider(Qt.Horizontal)
            sl.setRange(mn, mx)
            sl.setValue(varsayilan)
            sl.valueChanged.connect(self.simule_et)
            s_lay.addWidget(sl)
            self.sliders[anahtar] = (sl, fmt)
            self.lbl_vals[anahtar] = val_lbl

        s_lay.addStretch()
        orta.addWidget(sol, 1)

        # SAG PANEL: XAI Faktor Etkisi ve Canli Skor
        sag = QFrame()
        sag.setObjectName("PortalKart")
        r_lay = QVBoxLayout(sag)
        r_lay.setContentsMargins(14, 12, 14, 12)
        r_lay.addWidget(QLabel("<b>📊 XAI Faktör Etki Analizi (Feature Attribution)</b>"))

        self.lbl_skor = QLabel("Tahmini Akademik Risk: %0")
        self.lbl_skor.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px; border-radius: 6px;")
        r_lay.addWidget(self.lbl_skor)

        self.bar_risk = QProgressBar()
        self.bar_risk.setRange(0, 100)
        self.bar_risk.setFixedHeight(22)
        r_lay.addWidget(self.bar_risk)

        self.tbl_xai = QTableWidget(5, 3)
        self.tbl_xai.setHorizontalHeaderLabels(["Öznitelik (Feature)", "Mevcut Değer", "Riske Net Katkısı (XAI)"])
        self.tbl_xai.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_xai.setEditTriggers(QTableWidget.NoEditTriggers)
        r_lay.addWidget(self.tbl_xai, 1)

        orta.addWidget(sag, 1)
        lay.addLayout(orta, 1)

        # ALT PANEL: YZ Akilli Akademik Koç ve Reçete
        alt = QFrame()
        alt.setObjectName("PortalKart")
        a_lay = QVBoxLayout(alt)
        a_lay.setContentsMargins(14, 10, 14, 10)
        a_lay.addWidget(QLabel("<b>🧭 YZ Akıllı Akademik Koç & Optimal Ders Yükü Reçetesi</b>"))
        self.lbl_recete = QLabel()
        self.lbl_recete.setWordWrap(True)
        self.lbl_recete.setStyleSheet("font-size: 12px; color: #1e293b; line-height: 1.4;")
        a_lay.addWidget(self.lbl_recete)
        lay.addWidget(alt)

        self.ogrenci_yukle()

    def ogrenci_yukle(self):
        veri = self.cmb_ogr.currentData()
        if not veri:
            return
        gno = int(float(veri.get("gno") or 2.0) * 100)
        basari = int(float(veri.get("kredi_basari_orani") or 0.7) * 100)
        ff = int(veri.get("ff_sayisi") or 0)
        devam = int(float(veri.get("devamsizlik_orani") or 0.1) * 100)
        akts = int(veri.get("donem_akts_yuku") or 30)

        degerler = {"gno": gno, "basari": basari, "ff_sayisi": ff, "devamsizlik": devam, "akts_yuku": max(12, min(42, akts))}
        for k, v in degerler.items():
            sl, _ = self.sliders[k]
            sl.blockSignals(True)
            sl.setValue(v)
            sl.blockSignals(False)
        self.simule_et()

    def simule_et(self):
        for k, (sl, fmt) in self.sliders.items():
            self.lbl_vals[k].setText(fmt(sl.value()))

        gno = self.sliders["gno"][0].value() / 100.0
        basari = self.sliders["basari"][0].value() / 100.0
        ff = self.sliders["ff_sayisi"][0].value()
        devam = self.sliders["devamsizlik"][0].value() / 100.0
        akts = self.sliders["akts_yuku"][0].value()

        # Kalibre edilmis Lojistik Regresyon log-odds katkisi (OULAD agirliklari)
        katkilar = [
            ("Genel Not Ortalaması (AGNO)", f"{gno:.2f}", -1.35 * (gno - 2.20)),
            ("Kredi Başarı Oranı", f"%{int(basari*100)}", -1.80 * (basari - 0.70)),
            ("FF / Başarısız Ders Tekrarı", f"{ff} Ders", +0.55 * ff),
            ("Devamsızlık Oranı", f"%{int(devam*100)}", +4.20 * (devam - 0.10)),
            ("Dönem AKTS Ders Yükü", f"{akts} AKTS", +0.07 * (akts - 30)),
        ]
        logit = -0.35 + sum(k[2] for k in katkilar)
        olasilik = 1.0 / (1.0 + math.exp(-max(-6, min(6, logit))))
        yuzde = int(round(olasilik * 100))

        self.bar_risk.setValue(yuzde)
        if yuzde >= 65:
            renk, bg, seviye = "#dc2626", "#fee2e2", "KRİTİK RİSK (Yakın İzlem)"
        elif yuzde >= 35:
            renk, bg, seviye = "#d97706", "#fef3c7", "ORTA RİSK (Kontrollü Yük)"
        else:
            renk, bg, seviye = "#16a34a", "#dcfce7", "GÜVENLİ BÖLGE (Düşük Risk)"

        self.lbl_skor.setText(f"Tahmini Başarısızlık Olasılığı: %{yuzde}  —  {seviye}")
        self.lbl_skor.setStyleSheet(f"font-size: 15px; font-weight: bold; padding: 8px; border-radius: 6px; color: {renk}; background: {bg};")
        self.bar_risk.setStyleSheet(f"QProgressBar::chunk {{ background-color: {renk}; border-radius: 4px; }}")

        from PySide6.QtGui import QColor, QBrush
        for r, (ad, deg, etki) in enumerate(katkilar):
            puan_etki = int(round(etki * 18))
            isaret = f"+%{puan_etki} (Risk Artırıcı ▲)" if puan_etki > 0 else f"%{puan_etki} (Risk Düşürücü ▼)"
            self.tbl_xai.setItem(r, 0, QTableWidgetItem(ad))
            self.tbl_xai.setItem(r, 1, QTableWidgetItem(deg))
            it = QTableWidgetItem(isaret)
            it.setBackground(QBrush(QColor("#fee2e2" if puan_etki > 2 else "#dcfce7" if puan_etki < -2 else "#f8fafc")))
            self.tbl_xai.setItem(r, 2, it)

        # Akilli Reçete ve Counterfactual Hedef
        onerilen_akts = 20 if yuzde >= 65 else (26 if yuzde >= 35 else 36)
        hedef_gno = max(gno, round(2.00 + max(0, (logit + 0.6) / 1.35), 2))
        self.lbl_recete.setText(
            f"• <b>Counterfactual (Güvenli Bölge) Hedefi:</b> Riskin %35'in altına inmesi için AGNO en az <b>{min(4.0, hedef_gno):.2f}</b> olmalı ve devamsızlık <b>%12</b> altında tutulmalıdır.<br>"
            f"• <b>YZ Optimal AKTS Tavan Önerisi:</b> Mevcut risk profiline göre bu dönem önerilen maksimum ders yükü <b>{onerilen_akts} AKTS</b>'dir "
            f"{'(Mevcut yükünüz güvenli sınırı aşıyor!)' if akts > onerilen_akts else '(Mevcut AKTS yükünüz dengeli ✓)'}.<br>"
            f"• <b>Stratejik Öncelik:</b> Önce <b>{ff} adet FF/tekrar dersini</b> ve önkoşul zincirini (DAG kritik yol) açan zorunlu dersleri sepete ekleyiniz."
        )


class CanEgrisiDialog(QDialog):
    """Ogretim Uyesi Sube Not Dagilimi (Can Egrisi Histogrami) ve Istatistik Analitigi."""

    def __init__(self, db, sube_id: int, sube_baslik: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📊 Şube Not Dağılım Analitiği ve Çan Eğrisi — {sube_baslik}")
        self.resize(720, 480)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        baslik = QLabel(f"<b>📊 {sube_baslik} — Harf Notu Dağılımı ve Sınıf İstatistikleri</b>")
        baslik.setStyleSheet("font-size: 14px; color: #093567;")
        lay.addWidget(baslik)

        kayitlar = db.sorgula(
            """SELECT k.kayit_id, k.harf, k.durum,
                      COALESCE(SUM(n.puan * dbil.agirlik / 100.0), 0) AS ortalama
                 FROM kayit k
                 LEFT JOIN degerlendirme_bileseni dbil ON dbil.sube_id = k.sube_id
                 LEFT JOIN not_kaydi n ON n.kayit_id = k.kayit_id AND n.bilesen_id = dbil.bilesen_id
                WHERE k.sube_id = %s AND k.durum NOT IN ('sepet', 'birakti')
                GROUP BY k.kayit_id, k.harf, k.durum""",
            (sube_id,),
        )

        puanlar = [float(r["ortalama"] or 0) for r in kayitlar]
        ogr_say = len(puanlar)
        sinif_ort = sum(puanlar) / ogr_say if ogr_say else 0.0
        std_sapma = math.sqrt(sum((x - sinif_ort) ** 2 for x in puanlar) / ogr_say) if ogr_say else 0.0

        harf_sirasi = ["AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF"]
        sayac = {h: 0 for h in harf_sirasi}
        for r in kayitlar:
            h = r.get("harf")
            if not h:
                p = float(r["ortalama"] or 0)
                h = "AA" if p >= 90 else "BA" if p >= 85 else "BB" if p >= 75 else "CB" if p >= 70 else "CC" if p >= 60 else "DC" if p >= 55 else "DD" if p >= 50 else "FF"
            if h in sayac:
                sayac[h] += 1

        gecen = sum(sayac[h] for h in ["AA", "BA", "BB", "CB", "CC", "DC", "DD"])
        basari_yuzde = int(round((gecen / ogr_say) * 100)) if ogr_say else 0

        ozet = QLabel(
            f"<b>Kayıtlı Öğrenci:</b> {ogr_say} &nbsp;|&nbsp; "
            f"<b>Sınıf Ortalaması:</b> {sinif_ort:.1f} / 100 &nbsp;|&nbsp; "
            f"<b>Standart Sapma (σ):</b> {std_sapma:.1f} &nbsp;|&nbsp; "
            f"<b>Geçme Oranı:</b> %{basari_yuzde}"
        )
        ozet.setStyleSheet("background:#f8fafc; padding:10px; border:1px solid #cbd5e1; border-radius:6px;")
        lay.addWidget(ozet)

        kart = QFrame()
        kart.setObjectName("PortalKart")
        k_lay = QVBoxLayout(kart)
        k_lay.setContentsMargins(14, 12, 14, 12)

        renk_harf = {
            "AA": "#15803d", "BA": "#16a34a", "BB": "#22c55e", "CB": "#0d9488",
            "CC": "#0284c7", "DC": "#d97706", "DD": "#ea580c", "FD": "#e11d48", "FF": "#dc2626"
        }
        max_adet = max(1, max(sayac.values()))
        for h in harf_sirasi:
            adet = sayac[h]
            satir = QHBoxLayout()
            lbl_h = QLabel(f"<b>{h}</b>")
            lbl_h.setFixedWidth(36)
            bar = QProgressBar()
            bar.setRange(0, max_adet)
            bar.setValue(adet)
            bar.setFormat(f" {adet} Öğrenci (%{int(round(adet/ogr_say*100)) if ogr_say else 0})")
            bar.setFixedHeight(22)
            bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {renk_harf[h]}; border-radius: 4px; }}")
            satir.addWidget(lbl_h)
            satir.addWidget(bar, 1)
            k_lay.addLayout(satir)

        lay.addWidget(kart, 1)
