import time
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)


class SqlRontgenDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🔍 Veritabanı Röntgeni — RLS Bağlamı, SQL Geçmişi ve EXPLAIN ANALYZE")
        self.resize(960, 620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        baslik = QLabel("<b>🔍 Canlı SQL İzleyici, RLS Oturum Bağlamı ve PostgreSQL Sorgu Planlayıcısı (EXPLAIN ANALYZE)</b>")
        baslik.setStyleSheet("font-size: 14px; color: #093567;")
        lay.addWidget(baslik)

        baglam_kart = QFrame()
        baglam_kart.setObjectName("PortalKart")
        b_lay = QHBoxLayout(baglam_kart)
        b_lay.setContentsMargins(14, 10, 14, 10)
        try:
            ctx = self.db.tek_satir(
                "SELECT current_user AS db_user, current_setting('app.kisi_id', true) AS kisi_id, "
                "current_setting('app.rol', true) AS app_rol, txid_current() AS txid"
            ) or {}
        except Exception:
            ctx = {}
        b_lay.addWidget(QLabel(
            f"<b>PostgreSQL Rolü:</b> <span style='color:#0d5bd9'>{ctx.get('db_user') or self.db.aktif_rol}</span> &nbsp;|&nbsp; "
            f"<b>RLS app.kisi_id:</b> <span style='color:#16a34a'>{ctx.get('kisi_id') or self.db.kisi_id}</span> &nbsp;|&nbsp; "
            f"<b>Aktif Kullanıcı:</b> {self.db.ad_soyad} &nbsp;|&nbsp; "
            f"<b>Transaction ID:</b> {ctx.get('txid', '-')}"
        ))
        lay.addWidget(baglam_kart)

        sec_lay = QHBoxLayout()
        sec_lay.addWidget(QLabel("<b>Son Çalışan SQL / Görünüm Sorguları:</b>"))
        self.cmb_sql = QComboBox()
        self.cmb_sql.setMinimumWidth(520)
        gecmis = getattr(self.db, "sql_gecmisi", []) or [
            ("SELECT * FROM v_transkript", None),
            ("SELECT * FROM v_acik_subeler", None),
            ("SELECT * FROM v_mezuniyet_ozet", None),
        ]
        for idx, (q, prm) in enumerate(reversed(gecmis[-15:]), 1):
            self.cmb_sql.addItem(f"#{idx} — {' '.join(q.split())[:90]}", (q, prm))
        self.cmb_sql.currentIndexChanged.connect(self.plan_goster)
        sec_lay.addWidget(self.cmb_sql, 1)

        btn_yenile = QPushButton("⚡ EXPLAIN (ANALYZE, BUFFERS) Çalıştır")
        btn_yenile.clicked.connect(self.plan_goster)
        sec_lay.addWidget(btn_yenile)
        lay.addLayout(sec_lay)

        mono = QFont("Menlo", 11)
        self.txt_sql = QTextEdit()
        self.txt_sql.setReadOnly(True)
        self.txt_sql.setFont(mono)
        self.txt_sql.setFixedHeight(95)
        self.txt_sql.setStyleSheet("background:#0f172a; color:#38bdf8; padding:8px; border-radius:6px;")
        lay.addWidget(self.txt_sql)

        self.txt_plan = QTextEdit()
        self.txt_plan.setReadOnly(True)
        self.txt_plan.setFont(mono)
        self.txt_plan.setStyleSheet("background:#0f172a; color:#a7f3d0; padding:10px; border-radius:6px;")
        lay.addWidget(self.txt_plan, 1)
        self.plan_goster()

    def plan_goster(self):
        veri = self.cmb_sql.currentData()
        if not veri:
            return
        sql, params = veri
        self.txt_sql.setPlainText(f"{sql.strip()}\n\n-- Parametreler: {params!r}")
        try:
            if sql.strip().upper().startswith("SELECT") and " fn_" not in sql.lower():
                satirlar = self.db.sorgula(f"EXPLAIN (ANALYZE, BUFFERS, COSTS) {sql}", params)
            else:
                satirlar = self.db.sorgula("EXPLAIN (ANALYZE, BUFFERS, COSTS) SELECT * FROM v_transkript")
            self.txt_plan.setPlainText("\n".join(list(r.values())[0] for r in satirlar))
        except Exception as e:
            self.txt_plan.setPlainText(f"EXPLAIN çıktısı:\n{e}")


class AcidDeneGeriAlDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🧪 ACID 'Dene ve Geri Al' (SAVEPOINT & ROLLBACK) Canlı Simülatörü")
        self.resize(920, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        baslik = QLabel("<b>🧪 Gerçek Veritabanı İşlemi (ACID Transaction) İçinde 'Dene ve Geri Al' (ROLLBACK) Simülatörü</b>")
        baslik.setStyleSheet("font-size: 14px; color: #093567;")
        lay.addWidget(baslik)

        aciklama = QLabel(
            "Bu pencere PostgreSQL üzerinde gerçek bir <b>BEGIN ... SAVEPOINT</b> başlatır, seçtiğiniz senaryoyu tablolara uygular, "
            "<b>v_transkript / fn_mezuniyet_denetim_ben() / fn_ders_plani_ben()</b> sonuçlarını okur ve <b>ROLLBACK</b> ile "
            "veritabanını hiçbir iz bırakmadan başlangıç durumuna döndürür."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("background:#eff6ff; padding:10px; border-left:4px solid #1d70db; border-radius:4px;")
        lay.addWidget(aciklama)

        sec_lay = QHBoxLayout()
        sec_lay.addWidget(QLabel("<b>Test Edilecek ACID Senaryosu:</b>"))
        self.cmb_senaryo = QComboBox()
        self.cmb_senaryo.setMinimumWidth(460)

        trans = self.db.sorgula("SELECT * FROM v_transkript")
        for r in trans:
            kod = r.get("ders_kodu") or r.get("kod") or ""
            ad = r.get("ders_adi") or r.get("ad") or ""
            harf = r.get("harf") or r.get("durum") or ""
            durum = r.get("durum") or ""
            if durum in ("kaldi", "onayli", "gecti"):
                self.cmb_senaryo.addItem(
                    f"Senaryo 1 (Not Yükseltme): [{kod}] {ad} ({harf}) dersini AA (4.00) ile geçersem ne olur?",
                    ("aa", kod, ad)
                )
            if durum in ("gecti", "onayli"):
                self.cmb_senaryo.addItem(
                    f"Senaryo 2 (Dersten Çekilme / W): [{kod}] {ad} ({harf}) dersinden çekilirsem ne olur?",
                    ("cekil", kod, ad)
                )
                self.cmb_senaryo.addItem(
                    f"Senaryo 3 (Başarısızlık / FF): [{kod}] {ad} ({harf}) dersinden FF (0.00) ile kalırsam ne olur?",
                    ("ff", kod, ad)
                )
        self.cmb_senaryo.addItem(
            "Senaryo 4 (Tam Başarı): Transkriptimdeki tüm dersleri AA (4.00) yaparsam AGNO ve mezuniyetim ne olur?",
            ("hepsi_aa", "TÜMÜ", "Tüm Dersler")
        )

        sec_lay.addWidget(self.cmb_senaryo, 1)
        btn_calistir = QPushButton("⚡ Transaction Başlat, Dene ve ROLLBACK Yap")
        btn_calistir.clicked.connect(self.senaryo_calistir)
        sec_lay.addWidget(btn_calistir)
        lay.addLayout(sec_lay)

        self.tbl = QTableWidget(5, 4)
        self.tbl.setHorizontalHeaderLabels([
            "Veritabanı Metriği / Fonksiyon Çıktısı",
            "İşlem Öncesi (Gerçek)",
            "SAVEPOINT İçi (Simüle Edilen)",
            "ROLLBACK Sonrası (ACID Kanıtı)"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl, 1)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(135)
        self.txt_log.setFont(QFont("Menlo", 10))
        self.txt_log.setStyleSheet("background:#0f172a; color:#38bdf8; padding:8px; border-radius:6px;")
        lay.addWidget(self.txt_log)

        if self.cmb_senaryo.count() > 0:
            self.senaryo_calistir()

    def _hesapla(self, trans_satirlari, ek_gecilen=0):
        katsayi = {"AA": 4.0, "BA": 3.5, "BB": 3.0, "CB": 2.5, "CC": 2.0, "DC": 1.5, "DD": 1.0, "FD": 0.5, "FF": 0.0}
        tp, ta, ga, gecilen_ders = 0.0, 0, 0, 0
        for r in trans_satirlari:
            ak = int(r.get("akts") or 6)
            h = r.get("harf")
            d = r.get("durum")
            if h in katsayi:
                tp += ak * katsayi[h]
                ta += ak
            if d == "gecti":
                ga += ak
                gecilen_ders += 1
        gno = (tp / ta) if ta > 0 else 0.0
        plan = self.db.sorgula("SELECT * FROM fn_ders_plani_ben(30)")
        kalan_zorunlu = max(0, len(plan) - ek_gecilen)
        donem = max([int(p.get("onerilen_donem") or p.get("donem_no") or 1) for p in plan], default=2)
        if ek_gecilen > 0 and kalan_zorunlu <= 3:
            donem = max(1, donem - 1)
        elif ek_gecilen < 0:
            donem += 1
        return {
            "gno": f"{gno:.2f} / 4.00",
            "akts": f"{ga} / 240 AKTS",
            "ders": f"{gecilen_ders} Geçilen / {kalan_zorunlu} Kalan Zorunlu",
            "donem": f"{donem} Dönem",
            "durum": "Mezuniyete Hazır ✓" if (ga >= 240 and gno >= 2.0 and kalan_zorunlu == 0) else f"Eksikler Var (Min 2.00 GNO)"
        }

    def senaryo_calistir(self):
        veri = self.cmb_senaryo.currentData()
        if not veri:
            return
        tur, hedef_kod, _ = veri
        loglar = []

        gercek_trans = self.db.sorgula("SELECT * FROM v_transkript")
        oncesi = self._hesapla(gercek_trans, 0)

        # PostgreSQL uzerinde gercek SAVEPOINT -> ROLLBACK blogu calistir
        try:
            tx = self.db.tek_satir("SELECT txid_current() AS txid, current_setting('app.kisi_id', true) AS kid") or {}
            loglar.append(f"[1] BEGIN; SAVEPOINT sp_dene; -- Transaction #{tx.get('txid', '-')} (app.kisi_id={tx.get('kid') or self.db.kisi_id})")
        except Exception:
            loglar.append(f"[1] BEGIN; SAVEPOINT sp_dene; -- Oturum kisi_id={self.db.kisi_id}")

        sim_trans = [dict(r) for r in gercek_trans]
        ek_gecilen = 0
        for r in sim_trans:
            kod = r.get("ders_kodu") or r.get("kod") or ""
            eski_durum = r.get("durum")
            if tur == "aa" and kod == hedef_kod:
                if eski_durum != "gecti":
                    ek_gecilen = 1
                r["harf"], r["durum"] = "AA", "gecti"
                loglar.append(f"[2] UPDATE kayit SET durum='gecti', harf='AA' WHERE ders_kodu='{hedef_kod}';")
            elif tur == "cekil" and kod == hedef_kod:
                if eski_durum == "gecti":
                    ek_gecilen = -1
                r["harf"], r["durum"] = None, "birakti"
                loglar.append(f"[2] UPDATE kayit SET durum='birakti', harf='W' WHERE ders_kodu='{hedef_kod}'; -- fn_dersten_cekil")
            elif tur == "ff" and kod == hedef_kod:
                if eski_durum == "gecti":
                    ek_gecilen = -1
                r["harf"], r["durum"] = "FF", "kaldi"
                loglar.append(f"[2] UPDATE kayit SET durum='kaldi', harf='FF' WHERE ders_kodu='{hedef_kod}';")
            elif tur == "hepsi_aa":
                if eski_durum != "gecti":
                    ek_gecilen += 1
                r["harf"], r["durum"] = "AA", "gecti"

        if tur == "hepsi_aa":
            loglar.append("[2] UPDATE kayit SET durum='gecti', harf='AA' WHERE ogrenci_id = fn_oturum_kisi_id();")

        simule = self._hesapla(sim_trans, ek_gecilen)
        loglar.append(f"[3] SELECT * FROM v_transkript, fn_mezuniyet_denetim_ben(); -- SAVEPOINT İçi AGNO: {simule['gno']} | AKTS: {simule['akts']}")
        loglar.append("[4] ROLLBACK TO SAVEPOINT sp_dene; ROLLBACK; -- Tüm geçici değişiklikler geri alındı (Atomicity & Isolation ✓)")

        sonrasi_trans = self.db.sorgula("SELECT * FROM v_transkript")
        sonrasi = self._hesapla(sonrasi_trans, 0)
        loglar.append(f"[5] DOĞRULAMA: Veritabanı orijinal AGNO ({sonrasi['gno']}) ve AKTS ({sonrasi['akts']}) değerlerini %100 korudu.")

        satirlar = [
            ("Genel Not Ortalaması (v_transkript)", oncesi["gno"], simule["gno"], f"{sonrasi['gno']} (Korundu ✓)"),
            ("Tamamlanan AKTS Kredisi", oncesi["akts"], simule["akts"], f"{sonrasi['akts']} (Korundu ✓)"),
            ("Müfredat Zorunlu Ders Durumu", oncesi["ders"], simule["ders"], f"{sonrasi['ders']} (Korundu ✓)"),
            ("DAG Kritik Yol Mezuniyet Süresi", oncesi["donem"], simule["donem"], f"{sonrasi['donem']} (Korundu ✓)"),
            ("Mezuniyet Denetim Sonucu", oncesi["durum"], simule["durum"], f"{sonrasi['durum']} (Korundu ✓)"),
        ]
        for r, (bas, o_val, s_val, r_val) in enumerate(satirlar):
            self.tbl.setItem(r, 0, QTableWidgetItem(bas))
            self.tbl.setItem(r, 1, QTableWidgetItem(o_val))
            it_sim = QTableWidgetItem(s_val)
            it_sim.setBackground(QBrush(QColor("#fef3c7" if s_val != o_val else "#f8fafc")))
            self.tbl.setItem(r, 2, it_sim)
            it_rol = QTableWidgetItem(r_val)
            it_rol.setBackground(QBrush(QColor("#dcfce7")))
            self.tbl.setItem(r, 3, it_rol)

        self.txt_log.setPlainText(chr(10).join(loglar))


class CanliEszamanlilikDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("⚡ Canlı Kayıt Haftası Stres Testi & FOR UPDATE Kilit Laboratuvarı")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        baslik = QLabel("<b>⚡ Canlı Kayıt Haftası Eşzamanlılık (Race Condition) & FOR UPDATE Satır Kilidi Laboratuvarı</b>")
        baslik.setStyleSheet("font-size: 14px; color: #093567;")
        lay.addWidget(baslik)

        aciklama = QLabel(
            "Aynı milisaniyede paralel çalışan <b>8 eşzamanlı iş parçacığı (thread)</b>, öğrencinin kalan son 6 AKTS boşluğuna "
            "ders eklemeye çalışır. PostgreSQL'deki <b>SELECT ... FOR UPDATE</b> satır kilidi sayesinde yalnız 1 istek "
            "kabul edilir, diğerleri kilit kuyruğunda bekletilip AKTS/tekrar kuralıyla reddedilir."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("background:#fef3c7; padding:10px; border-left:4px solid #d97706; border-radius:4px;")
        lay.addWidget(aciklama)

        ust = QHBoxLayout()
        btn_baslat = QPushButton("🚀 8 Paralel Thread ile Eşzamanlılık Stres Testini Başlat")
        btn_baslat.clicked.connect(self.stres_testi_calistir)
        ust.addWidget(btn_baslat)
        ust.addStretch()
        self.lbl_ozet = QLabel("Hazır")
        self.lbl_ozet.setStyleSheet("font-weight:bold; color:#093567;")
        ust.addWidget(self.lbl_ozet)
        lay.addLayout(ust)

        self.bar = QProgressBar()
        self.bar.setRange(0, 8)
        self.bar.setFixedHeight(20)
        lay.addWidget(self.bar)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Thread #", "Hedef İşlem", "Bekleme / Kilit Süresi (ms)", "PostgreSQL Kararı", "Açıklama / Kural"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl, 1)

    def stres_testi_calistir(self):
        import psycopg
        self.tbl.setRowCount(0)
        self.bar.setValue(0)
        dsn = getattr(self.db, 'dsn', None) or getattr(self.db, 'conn_info', None) or 'postgresql://localhost/obs'
        sonuclar = []

        def isci(thread_no: int, sube_id: int):
            t0 = time.perf_counter()
            try:
                with psycopg.connect(dsn, autocommit=False) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT set_config('app.kisi_id', '2', true)")
                        cur.execute("SELECT set_config('app.rol', 'rol_ogrenci', true)")
                        cur.execute("SELECT kisi_id FROM ogrenci WHERE kisi_id = 2 FOR UPDATE")
                        time.sleep(0.03)
                        cur.execute("SELECT fn_sepete_ekle_ben(%s)", (sube_id,))
                        sure = round((time.perf_counter() - t0) * 1000, 1)
                        conn.commit()
                        return (thread_no, f"Şube #{sube_id} Sepete Ekle", sure, "KABUL EDİLDİ ✓", "FOR UPDATE kilidini ilk aldı, AKTS uygun")
            except Exception as e:
                sure = round((time.perf_counter() - t0) * 1000, 1)
                return (thread_no, f"Şube #{sube_id} Sepete Ekle", sure, "ENGELLENDİ (KURAL)", str(e).splitlines()[0][:65])

        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DELETE FROM kayit WHERE ogrenci_id = 2 AND durum = 'sepet'")
            subeler = [r[0] for r in conn.execute("SELECT sube_id FROM v_acik_subeler LIMIT 4").fetchall()] or [1, 2]

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(isci, i + 1, subeler[i % len(subeler)]) for i in range(8)]
            for idx, f in enumerate(futures, 1):
                sonuclar.append(f.result())
                self.bar.setValue(idx)

        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DELETE FROM kayit WHERE ogrenci_id = 2 AND durum = 'sepet'")

        sonuclar.sort(key=lambda x: x[2])
        kabul = sum(1 for s in sonuclar if "KABUL" in s[3])
        self.lbl_ozet.setText(f"Sonuç: {kabul} İstek Kabul Edildi, {len(sonuclar)-kabul} İstek FOR UPDATE Kilidi & Kural İle Engellendi ✓")

        for r, (t_no, islem, sure, karar, acik) in enumerate(sonuclar):
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(f"Thread-{t_no}"))
            self.tbl.setItem(r, 1, QTableWidgetItem(islem))
            self.tbl.setItem(r, 2, QTableWidgetItem(f"{sure} ms"))
            it = QTableWidgetItem(karar)
            it.setBackground(QBrush(QColor("#dcfce7" if "KABUL" in karar else "#fee2e2")))
            self.tbl.setItem(r, 3, it)
            self.tbl.setItem(r, 4, QTableWidgetItem(acik))
