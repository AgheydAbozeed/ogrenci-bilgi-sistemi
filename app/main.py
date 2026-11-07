import os
import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QWidget, QStackedWidget, QFrame,
    QMessageBox, QDockWidget, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from app.db import Veritabani
from app.stil import (
    OLCULER, stil_uret, aktif_tema_adi, tema_kaydet
)
from app.ekranlar.ogrenci_ana import OgrenciAnaSayfa, OgrenciDersSecimi
from app.ekranlar.ogrenci_diger import (
    OgrenciKisiselVeTakvim, OgrenciNotlarTranskript, OgrenciMezuniyetSimulasyon
)
from app.ekranlar.danisman_ekran import DanismanOnayKuyrugu, DanisanPaneli
from app.ekranlar.hoca_ve_yonetim import (
    OgretimUyesiPaneli, SekreterPaneli, YoneticiPaneli, YoneticiKayitEklemePaneli
)
from app.ai.sohbet import AIAsistanKatmani
from app.ai.merkez_ekran import AIMerkeziEkrani

ROL_ADLARI = {
    "rol_ogrenci": "Öğrenci",
    "rol_danisman": "Akademik Danışman",
    "rol_ogretim_uyesi": "Öğretim Üyesi",
    "rol_sekreter": "Bölüm Sekreteri",
    "rol_yonetici": "Sistem Yöneticisi",
}


class GirisPenceresi(QDialog):
    """
    Öğrenci / Akademisyen seçmeli, 5 haneli numara + şifre ('123456') doğrulamalı
    kurumsal giriş ekranı.
    """

    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.giris_turu = "ogrenci"  # 'ogrenci' veya 'akademisyen'
        self.kullanicilar = self.db.demo_kullanicilar()

        self.setWindowTitle("OBS — Kurumsal Kimlik Doğrulama")
        self.setFixedSize(500, 485)

        ana = QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        ust_bant = QFrame()
        ust_bant.setObjectName("GirisUstBant")
        ust_bant.setStyleSheet(
            "QFrame#GirisUstBant { background-color: #0F172A; border: none; }"
        )
        ub_lay = QHBoxLayout(ust_bant)
        ub_lay.setContentsMargins(24, 18, 24, 18)
        ub_lay.setSpacing(14)

        lbl_arma = QLabel("OBS")
        lbl_arma.setFixedSize(44, 44)
        lbl_arma.setAlignment(Qt.AlignCenter)
        lbl_arma.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-size: 11pt; "
            "font-weight: 800; border-radius: 10px; border: none;"
        )
        ub_lay.addWidget(lbl_arma)

        ub_metin = QVBoxLayout()
        ub_metin.setSpacing(3)
        lbl_b = QLabel("ÖĞRENCİ BİLGİ SİSTEMİ PORTALI")
        lbl_b.setStyleSheet(
            "color: #FFFFFF; font-size: 13pt; font-weight: 800; "
            "letter-spacing: 0.4px; border: none; background: transparent;"
        )
        lbl_a = QLabel("Öğrenci ve Akademisyen Merkezi Kimlik Doğrulama Sistemi")
        lbl_a.setStyleSheet(
            "color: #94A3B8; font-size: 9pt; font-weight: 500; "
            "border: none; background: transparent;"
        )
        ub_metin.addWidget(lbl_b)
        ub_metin.addWidget(lbl_a)
        ub_lay.addLayout(ub_metin, 1)
        ana.addWidget(ust_bant)

        govde_kap = QWidget()
        govde_lay = QVBoxLayout(govde_kap)
        govde_lay.setContentsMargins(20, 18, 20, 20)
        govde_lay.setSpacing(0)

        kart = QFrame()
        kart.setObjectName("PortalKart")
        lay = QVBoxLayout(kart)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        # 1) Öğrenci / Akademisyen Giriş Türü Seçim Sekmesi (Segmented Control)
        tur_cerceve = QFrame()
        tur_cerceve.setObjectName("GirisTurSecici")
        tur_cerceve.setStyleSheet(
            "QFrame#GirisTurSecici { background-color: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        tur_lay = QHBoxLayout(tur_cerceve)
        tur_lay.setContentsMargins(4, 4, 4, 4)
        tur_lay.setSpacing(6)
        self.btn_tur_ogr = QPushButton("Öğrenci Girişi")
        self.btn_tur_ogr.setMinimumHeight(34)
        self.btn_tur_ogr.setCursor(Qt.PointingHandCursor)
        self.btn_tur_ogr.clicked.connect(lambda: self._tur_sec("ogrenci"))

        self.btn_tur_aka = QPushButton("Akademisyen / Personel Girişi")
        self.btn_tur_aka.setMinimumHeight(34)
        self.btn_tur_aka.setCursor(Qt.PointingHandCursor)
        self.btn_tur_aka.clicked.connect(lambda: self._tur_sec("akademisyen"))

        tur_lay.addWidget(self.btn_tur_ogr, 1)
        tur_lay.addWidget(self.btn_tur_aka, 1)
        lay.addWidget(tur_cerceve)

        # 2) Numara Giriş Alanı
        self.lbl_no_baslik = QLabel("Öğrenci Numarası (5 Haneli — [Yıl][Bölüm][Sıra])")
        self.lbl_no_baslik.setStyleSheet("color: #334155; font-size: 9.5pt; font-weight: 700; border: none;")
        lay.addWidget(self.lbl_no_baslik)

        self.txt_no = QLineEdit()
        self.txt_no.setMinimumHeight(36)
        self.txt_no.setMaxLength(12)
        self.txt_no.textChanged.connect(self._numara_degisti)
        lay.addWidget(self.txt_no)

        # 3) Şifre Giriş Alanı
        lbl_sifre_baslik = QLabel("Şifre")
        lbl_sifre_baslik.setStyleSheet("color: #334155; font-size: 9.5pt; font-weight: 700; border: none;")
        lay.addWidget(lbl_sifre_baslik)
        sifre_lay = QHBoxLayout()
        sifre_lay.setSpacing(8)
        self.txt_sifre = QLineEdit()
        self.txt_sifre.setMinimumHeight(36)
        self.txt_sifre.setEchoMode(QLineEdit.Password)
        self.txt_sifre.setPlaceholderText("Şifrenizi girin (Varsayılan: 123456)")
        self.txt_sifre.returnPressed.connect(self.kabul)
        sifre_lay.addWidget(self.txt_sifre, 1)

        self.btn_goz = QPushButton("Göster")
        self.btn_goz.setObjectName("IkincilBtn")
        self.btn_goz.setFixedSize(64, 36)
        self.btn_goz.setCursor(Qt.PointingHandCursor)
        self.btn_goz.setToolTip("Şifreyi Göster / Gizle")
        self.btn_goz.clicked.connect(self._sifre_gorunurluk_degistir)
        sifre_lay.addWidget(self.btn_goz)
        lay.addLayout(sifre_lay)

        # 4) Akademisyenler için Oturum Rolü Seçimi (Çok rollü akademisyenlerde görünür)
        self.rol_kap = QWidget()
        rol_v = QVBoxLayout(self.rol_kap)
        rol_v.setContentsMargins(0, 0, 0, 0)
        rol_v.setSpacing(4)
        lbl_rol_b = QLabel("Oturum Rolü")
        lbl_rol_b.setStyleSheet("color: #334155; font-size: 9.5pt; font-weight: 700; border: none;")
        rol_v.addWidget(lbl_rol_b)
        self.cmb_rol = QComboBox()
        self.cmb_rol.setMinimumHeight(34)
        rol_v.addWidget(self.cmb_rol)
        lay.addWidget(self.rol_kap)

        # 5) Sunum kolaylığı için hızlı hesap rehberi (Seçilince numarayı ve 123456'yı doldurur)
        rehber_kutu = QFrame()
        rehber_kutu.setObjectName("GirisDemoKutu")
        rehber_kutu.setStyleSheet(
            "QFrame#GirisDemoKutu { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        rehber_lay = QHBoxLayout(rehber_kutu)
        rehber_lay.setContentsMargins(10, 8, 10, 8)
        rehber_lay.setSpacing(8)
        lbl_rehber = QLabel("Hızlı Hesap:")
        lbl_rehber.setStyleSheet("color: #475569; font-size: 9pt; font-weight: 700; border: none; background: transparent;")
        rehber_lay.addWidget(lbl_rehber)
        self.cmb_hizli = QComboBox()
        self.cmb_hizli.setMinimumHeight(32)
        self.cmb_hizli.currentIndexChanged.connect(self._hizli_hesap_secildi)
        rehber_lay.addWidget(self.cmb_hizli, 1)
        lay.addWidget(rehber_kutu)

        self.lbl_hata = QLabel("")
        self.lbl_hata.setStyleSheet(
            "background-color: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; "
            "border-radius: 6px; padding: 6px 10px; font-weight: 600; font-size: 9pt;"
        )
        self.lbl_hata.setVisible(False)
        lay.addWidget(self.lbl_hata)

        lay.addStretch()
        btn_giris = QPushButton("Sisteme Giriş Yap  ➔")
        btn_giris.setObjectName("BirincilBtn")
        btn_giris.setMinimumHeight(40)
        btn_giris.setCursor(Qt.PointingHandCursor)
        btn_giris.clicked.connect(self.kabul)
        lay.addWidget(btn_giris)

        govde_lay.addWidget(kart, 1)
        ana.addWidget(govde_kap, 1)
        self._tur_sec("ogrenci")

    def _sifre_gorunurluk_degistir(self):
        if self.txt_sifre.echoMode() == QLineEdit.Password:
            self.txt_sifre.setEchoMode(QLineEdit.Normal)
            self.btn_goz.setText("Gizle")
        else:
            self.txt_sifre.setEchoMode(QLineEdit.Password)
            self.btn_goz.setText("Göster")

    def _tur_sec(self, tur: str):
        self.giris_turu = tur
        self.lbl_hata.setVisible(False)
        secili_stil = (
            "background-color: #2563EB; color: #FFFFFF; font-weight: 700; "
            "border: none; border-radius: 6px; font-size: 9.5pt;"
        )
        pasif_stil = (
            "background-color: transparent; color: #475569; font-weight: 600; "
            "border: none; border-radius: 6px; font-size: 9.5pt;"
        )
        if tur == "ogrenci":
            self.btn_tur_ogr.setStyleSheet(secili_stil)
            self.btn_tur_aka.setStyleSheet(pasif_stil)
            self.lbl_no_baslik.setText("Öğrenci Numarası (5 Haneli — [Yıl][Bölüm][Sıra])")
            self.txt_no.setPlaceholderText("Örn: 23101, 24101, 25102")
            self.rol_kap.setVisible(False)
        else:
            self.btn_tur_aka.setStyleSheet(secili_stil)
            self.btn_tur_ogr.setStyleSheet(pasif_stil)
            self.lbl_no_baslik.setText("Akademisyen / Personel Numarası (5 Haneli)")
            self.txt_no.setPlaceholderText("Örn: 10101 (Danışman/Hoca), 10001 (Sekreter), 10000 (Yönetici)")
            self.rol_kap.setVisible(True)

        # Hızlı seçim listesini ilgili türe göre doldur
        self.cmb_hizli.blockSignals(True)
        self.cmb_hizli.clear()
        self.cmb_hizli.addItem("— Numarayı kendiniz yazın veya listeden seçin —", None)
        uygunlar = [u for u in self.kullanicilar if u.get("giris_turu") == tur]
        for u in uygunlar:
            no = u.get("kullanici_no", "")
            ad = u.get("ad_soyad", "")
            if tur == "ogrenci":
                prog = (u.get("program_ad") or "").replace(" (Lisans)", "")
                etiket = f"{no} — {ad}" + (f" ({prog})" if prog else "")
            else:
                roller_str = ", ".join(ROL_ADLARI.get(r, r) for r in (u.get("roller") or []))
                etiket = f"{no} — {ad} [{roller_str}]"
            self.cmb_hizli.addItem(etiket, u)
        self.cmb_hizli.blockSignals(False)

        # İlk uygun hesabı varsayılan olarak doldur
        if uygunlar:
            self.cmb_hizli.setCurrentIndex(1)
            self._hizli_hesap_secildi()
        else:
            self.txt_no.clear()
            self.txt_sifre.setText("123456")

    def _hizli_hesap_secildi(self):
        u = self.cmb_hizli.currentData()
        if not u:
            return
        self.txt_no.setText(str(u.get("kullanici_no") or ""))
        self.txt_sifre.setText("123456")
        self._numara_degisti(self.txt_no.text())

    def _numara_degisti(self, metin: str):
        self.lbl_hata.setVisible(False)
        k_no = metin.strip()
        self.cmb_rol.clear()
        eslesen = next(
            (
                u for u in self.kullanicilar
                if str(u.get("kullanici_no")) == k_no and u.get("giris_turu") == self.giris_turu
            ),
            None
        )
        if eslesen:
            for r in (eslesen.get("roller") or []):
                self.cmb_rol.addItem(ROL_ADLARI.get(r, r), r)
        elif self.giris_turu == "akademisyen":
            for r_kod in ("rol_danisman", "rol_ogretim_uyesi", "rol_sekreter", "rol_yonetici"):
                self.cmb_rol.addItem(ROL_ADLARI[r_kod], r_kod)

    def kabul(self):
        try:
            kullanici = self.db.kimlik_dogrula(
                self.giris_turu,
                self.txt_no.text(),
                self.txt_sifre.text()
            )
        except ValueError as e:
            self.lbl_hata.setText(f"✖  {e}")
            self.lbl_hata.setVisible(True)
            return

        roller = kullanici.get("roller") or []
        if self.giris_turu == "ogrenci":
            secili_rol = "rol_ogrenci"
        else:
            secili_rol = self.cmb_rol.currentData()
            if not secili_rol or secili_rol not in roller:
                secili_rol = roller[0] if roller else "rol_ogretim_uyesi"

        self.db.oturum_ayarla(
            kullanici["kisi_id"],
            kullanici["ad_soyad"],
            roller,
            secili_rol,
            str(kullanici.get("kullanici_no") or "")
        )
        self.accept()


class DemoRehberiDock(QDockWidget):
    """
    Tasarım Sistemi — Sunum Modu:
    Sağda QDockWidget: 'Demo rehberi', 10 adım; her adımın 'Git' düğmesi
    doğru kullanıcıya ve ekrana geçirir. Adımlar JSON dosyasında tutulur.
    """

    def __init__(self, ana_pencere: "AnaPencere"):
        super().__init__("🎯 Demo Rehberi (10 Adım)", ana_pencere)
        self.ana_pencere = ana_pencere
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setMinimumWidth(295)
        self.setMaximumWidth(350)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        kap = QWidget()
        lay = QVBoxLayout(kap)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        aciklama = QLabel(
            "Sunum sırasında aşağıdaki <b>10 adımı</b> sırayla takip edebilirsiniz. "
            "<b>Git ➔</b> düğmesi ilgili kullanıcıya, role ve ekrana otomatik geçirir."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet(
            "background-color: #DBEAFE; color: #1E3A8A; border-radius: 6px; padding: 8px 10px; font-size: 9pt;"
        )
        lay.addWidget(aciklama)

        adimlar = self._adimlari_yukle()
        for adim_veri in adimlar:
            kart = QFrame()
            kart.setObjectName("PortalKart")
            k_lay = QVBoxLayout(kart)
            k_lay.setContentsMargins(10, 8, 10, 8)
            k_lay.setSpacing(4)

            ust = QHBoxLayout()
            no = adim_veri.get("adim", "")
            baslik = adim_veri.get("baslik", "")
            lbl_b = QLabel(f"<b>{no}. {baslik}</b>")
            lbl_b.setWordWrap(True)
            ust.addWidget(lbl_b, 1)

            btn_git = QPushButton("Git ➔")
            btn_git.setObjectName("BirincilBtn")
            btn_git.setFixedWidth(68)
            rol = adim_veri.get("rol", "rol_ogrenci")
            ekran = int(adim_veri.get("ekran", 0))
            btn_git.clicked.connect(lambda _, r=rol, e=ekran: self.ana_pencere.demo_adimina_git(r, e))
            ust.addWidget(btn_git)
            k_lay.addLayout(ust)

            rol_etiket = ROL_ADLARI.get(rol, rol)
            lbl_rol = QLabel(f"Rol: <b>{rol_etiket}</b>  •  Sekme #{ekran + 1}")
            lbl_rol.setStyleSheet("color: #2563EB; font-size: 8.5pt;")
            k_lay.addWidget(lbl_rol)

            lbl_ipucu = QLabel(adim_veri.get("ipucu", ""))
            lbl_ipucu.setWordWrap(True)
            lbl_ipucu.setStyleSheet("color: #475569; font-size: 8.5pt;")
            k_lay.addWidget(lbl_ipucu)

            lay.addWidget(kart)

        lay.addStretch()
        scroll.setWidget(kap)
        self.setWidget(scroll)

    def _adimlari_yukle(self) -> list[dict]:
        json_yol = os.path.join(os.path.dirname(__file__), "demo_rehberi.json")
        try:
            with open(json_yol, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


class AnaPencere(QMainWindow):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.setWindowTitle("Öğrenci Bilgi Sistemi (OBS)")

        self.setMinimumSize(
            OLCULER["asgari_pencere_genislik"],
            OLCULER["asgari_pencere_yukseklik"]
        )
        ekran = QApplication.primaryScreen().availableGeometry()
        gen = max(OLCULER["asgari_pencere_genislik"], min(1280, int(ekran.width() * 0.94)))
        yuk = max(OLCULER["asgari_pencere_yukseklik"], min(780, int(ekran.height() * 0.90)))
        self.resize(gen, yuk)
        self.move(
            ekran.x() + (ekran.width() - gen) // 2,
            ekran.y() + (ekran.height() - yuk) // 2
        )

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana_lay = QHBoxLayout(merkez)
        ana_lay.setContentsMargins(0, 0, 0, 0)
        ana_lay.setSpacing(0)

        self.sol_menu = QFrame()
        self.sol_menu.setObjectName("SolMenu")
        self.sol_menu.setFixedWidth(OLCULER["menu_genislik"])
        sol_ana_lay = QVBoxLayout(self.sol_menu)
        sol_ana_lay.setContentsMargins(0, 0, 0, 12)
        sol_ana_lay.setSpacing(0)

        profil_kutu = QFrame()
        profil_kutu.setObjectName("SolMenuProfil")
        p_lay = QHBoxLayout(profil_kutu)
        p_lay.setContentsMargins(14, 14, 14, 14)
        p_lay.setSpacing(10)

        self.lbl_sol_avatar = QLabel("ÖB")
        self.lbl_sol_avatar.setFixedSize(36, 36)
        self.lbl_sol_avatar.setAlignment(Qt.AlignCenter)
        self.lbl_sol_avatar.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: 800; "
            "font-size: 11pt; border-radius: 18px;"
        )
        p_lay.addWidget(self.lbl_sol_avatar)

        v_isim = QVBoxLayout()
        v_isim.setSpacing(2)
        self.lbl_sol_isim = QLabel()
        self.lbl_sol_isim.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 10pt;")
        self.lbl_sol_rol = QLabel()
        self.lbl_sol_rol.setStyleSheet("color: #93C5FD; font-size: 8.5pt;")
        v_isim.addWidget(self.lbl_sol_isim)
        v_isim.addWidget(self.lbl_sol_rol)
        p_lay.addLayout(v_isim, 1)
        sol_ana_lay.addWidget(profil_kutu)

        self.menu_lay = QVBoxLayout()
        self.menu_lay.setContentsMargins(0, 8, 0, 8)
        self.menu_lay.setSpacing(4)
        sol_ana_lay.addLayout(self.menu_lay, 1)

        kisayol_lbl = QLabel(
            "⌨️ <b>Kısayollar:</b><br>"
            "• Ctrl+1…6 : Ekranlara geç<br>"
            "• F5 : Yenile<br>"
            "• Ctrl+Enter : Kesinleştir<br>"
            "• Esc : Kapat / Sıfırla"
        )
        kisayol_lbl.setStyleSheet(
            "color: #CBD5E1; font-size: 8.5pt; padding: 10px 14px; "
            "background-color: rgba(255,255,255,0.05); margin: 8px; border-radius: 6px;"
        )
        sol_ana_lay.addWidget(kisayol_lbl)

        ana_lay.addWidget(self.sol_menu)

        sag_govde = QVBoxLayout()
        sag_govde.setContentsMargins(0, 0, 0, 0)
        sag_govde.setSpacing(0)

        ust = QFrame()
        ust.setObjectName("UstCubuk")
        ust.setFixedHeight(52)
        u_lay = QHBoxLayout(ust)
        u_lay.setContentsMargins(20, 0, 20, 0)
        u_lay.setSpacing(10)

        self.lbl_kurum = QLabel("ÖĞRENCİ BİLGİ SİSTEMİ PORTALI")
        self.lbl_kurum.setStyleSheet("font-weight: 800; font-size: 11.5pt; letter-spacing: 0.4px;")
        u_lay.addWidget(self.lbl_kurum)
        u_lay.addStretch()

        self.cmb_rol_degis = QComboBox()
        self.cmb_rol_degis.currentIndexChanged.connect(self.rol_degistir)
        u_lay.addWidget(self.cmb_rol_degis)

        self.btn_tema = QPushButton()
        self.btn_tema.setObjectName("UstBarBtn")
        self.btn_tema.clicked.connect(self.tema_degistir)
        u_lay.addWidget(self.btn_tema)
        self._tema_buton_metni_guncelle()

        btn_demo = QPushButton("🎯  Demo Rehberi")
        btn_demo.setObjectName("UstBarBtn")
        btn_demo.clicked.connect(self.demo_rehberi_ac_kapat)
        u_lay.addWidget(btn_demo)

        self.btn_ust_ai = QPushButton("✦  AI Asistan")
        self.btn_ust_ai.setObjectName("AIDugme")
        self.btn_ust_ai.clicked.connect(lambda: self.ai_katmani.ac_kapat())
        u_lay.addWidget(self.btn_ust_ai)

        btn_cikis = QPushButton("⇥  Kullanıcı Değiştir")
        btn_cikis.setObjectName("IkincilBtn")
        btn_cikis.clicked.connect(self.kullanici_degistir)
        u_lay.addWidget(btn_cikis)

        sag_govde.addWidget(ust)

        self.icerik = QStackedWidget()
        sag_govde.addWidget(self.icerik, 1)
        ana_lay.addLayout(sag_govde, 1)

        self.demo_dock = DemoRehberiDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.demo_dock)

        self.menu_butonlari: list[QPushButton] = []
        self.ai_katmani = AIAsistanKatmani(self.icerik, self.db)
        self._kisayollari_kur()
        self.ekranlari_kur()

    def _kisayollari_kur(self):
        self._kisayollar = []
        for i in range(1, 7):
            sc = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            sc.activated.connect(lambda idx=i - 1: self.sekme_sec(idx))
            self._kisayollar.append(sc)

        sc_f5 = QShortcut(QKeySequence("F5"), self)
        sc_f5.activated.connect(self.aktif_ekrani_yenile)
        self._kisayollar.append(sc_f5)

        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            sc_kesin = QShortcut(QKeySequence(seq), self)
            sc_kesin.activated.connect(self.aktif_ekrani_kesinlestir)
            self._kisayollar.append(sc_kesin)

        sc_esc = QShortcut(QKeySequence("Esc"), self)
        sc_esc.activated.connect(self.esc_basildi)
        self._kisayollar.append(sc_esc)

    def aktif_ekrani_yenile(self):
        w = self.icerik.currentWidget()
        if w and hasattr(w, "yenile"):
            w.yenile()

    def aktif_ekrani_kesinlestir(self):
        w = self.icerik.currentWidget()
        if w and hasattr(w, "hepsini_kesinlestir"):
            w.hepsini_kesinlestir()

    def esc_basildi(self):
        aktif_modal = QApplication.activeModalWidget()
        if isinstance(aktif_modal, QDialog):
            aktif_modal.reject()
            return
        if hasattr(self, "ai_katmani") and self.ai_katmani.acik_mi():
            self.ai_katmani.ac_kapat()
            return
        w = self.icerik.currentWidget()
        if w and hasattr(w, "txt_ara"):
            w.txt_ara.clear()

    def _tema_buton_metni_guncelle(self):
        if aktif_tema_adi() == "koyu":
            self.btn_tema.setText("☀️  Açık Tema")
        else:
            self.btn_tema.setText("🌙  Koyu Tema")

    def tema_degistir(self):
        yeni_tema = "koyu" if aktif_tema_adi() == "acik" else "acik"
        tema_kaydet(yeni_tema)
        QApplication.instance().setStyleSheet(stil_uret(yeni_tema))
        self._tema_buton_metni_guncelle()
        if hasattr(self, "ai_katmani"):
            self.ai_katmani.tema_yenile()
        self.aktif_ekrani_yenile()

    def demo_rehberi_ac_kapat(self):
        self.demo_dock.setVisible(not self.demo_dock.isVisible())

    def demo_adimina_git(self, hedef_rol: str, hedef_ekran: int):
        if self.db.aktif_rol != hedef_rol:
            if hedef_rol in (self.db.roller or []):
                self.db.aktif_rol = hedef_rol
            else:
                kullanicilar = self.db.demo_kullanicilar()
                hedef_kul = next(
                    (k for k in kullanicilar if hedef_rol in (k["roller"] or [])),
                    None
                )
                if hedef_kul:
                    self.db.oturum_ayarla(
                        hedef_kul["kisi_id"],
                        hedef_kul["ad_soyad"],
                        hedef_kul["roller"],
                        hedef_rol,
                        str(hedef_kul.get("kullanici_no") or "")
                    )
            self.ekranlari_kur()
        self.sekme_sec(hedef_ekran)

    def ekranlari_kur(self):
        rol_ad = ROL_ADLARI.get(self.db.aktif_rol, self.db.aktif_rol)
        bas_harf = "".join([x[0] for x in self.db.ad_soyad.split()[:2]]).upper()
        self.lbl_sol_avatar.setText(bas_harf or "OB")
        self.lbl_sol_isim.setText(self.db.ad_soyad)
        no_bilgi = f" ({self.db.kullanici_no})" if getattr(self.db, "kullanici_no", "") else ""
        self.lbl_sol_rol.setText(f"{rol_ad}{no_bilgi}")

        self.cmb_rol_degis.blockSignals(True)
        self.cmb_rol_degis.clear()
        for r in (self.db.roller or []):
            self.cmb_rol_degis.addItem(ROL_ADLARI.get(r, r), r)
        if self.db.aktif_rol in (self.db.roller or []):
            self.cmb_rol_degis.setCurrentIndex(self.db.roller.index(self.db.aktif_rol))
        self.cmb_rol_degis.setVisible(len(self.db.roller or []) > 1)
        self.cmb_rol_degis.blockSignals(False)

        while self.menu_lay.count():
            item = self.menu_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.icerik.count():
            w = self.icerik.widget(0)
            self.icerik.removeWidget(w)
            w.deleteLater()
        self.menu_butonlari.clear()

        if self.db.aktif_rol == "rol_ogrenci":
            sekme_listesi = [
                ("⚙️   Ana Görünüm (Ctrl+1)", lambda: OgrenciAnaSayfa(self.db, self.sekme_sec)),
                ("📝   Ders Kayıt İşlemleri (Ctrl+2)", lambda: OgrenciDersSecimi(self.db)),
                ("A+   Not Bilgileri (Ctrl+3)", lambda: OgrenciNotlarTranskript(self.db)),
                ("🎓   Mezuniyet & DAG (Ctrl+4)", lambda: OgrenciMezuniyetSimulasyon(self.db)),
                ("👤   Kişisel & Takvim (Ctrl+5)", lambda: OgrenciKisiselVeTakvim(self.db)),
            ]
        elif self.db.aktif_rol == "rol_danisman":
            sekme_listesi = [
                ("☑️   Onay Kuyruğu (Ctrl+1)", lambda: DanismanOnayKuyrugu(self.db)),
                ("📊   Danışanlarım (Ctrl+2)", lambda: DanisanPaneli(self.db)),
                ("✦   AI Merkezi (Ctrl+3)", lambda: AIMerkeziEkrani(self.db)),
            ]
        elif self.db.aktif_rol == "rol_ogretim_uyesi":
            sekme_listesi = [
                ("👨‍🏫   Şubelerim, Not & Yoklama", lambda: OgretimUyesiPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_sekreter":
            sekme_listesi = [
                ("🗂️   Sekreterlik İşlemleri", lambda: SekreterPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_yonetici":
            sekme_listesi = [
                ("🛡️   Parametre & Denetim Logu (Ctrl+1)", lambda: YoneticiPaneli(self.db, self.sekme_sec)),
                ("🏛️   Öğrenci / Hoca / Ders Ekle (Ctrl+2)", lambda: YoneticiKayitEklemePaneli(self.db)),
                ("✦   AI Merkezi (Ctrl+3)", lambda: AIMerkeziEkrani(self.db)),
            ]
        else:
            sekme_listesi = []

        self._sekme_fabrikalari = []
        for idx, (etiket, fabrika) in enumerate(sekme_listesi):
            btn = QPushButton(etiket)
            btn.clicked.connect(lambda _, i=idx: self.sekme_sec(i))
            self.menu_lay.addWidget(btn)
            self.menu_butonlari.append(btn)
            self._sekme_fabrikalari.append(fabrika)
            yer_tutucu = QWidget()
            yer_tutucu.setProperty("_yer_tutucu", True)
            self.icerik.addWidget(yer_tutucu)

        self.menu_lay.addStretch()
        if self.menu_butonlari:
            self.sekme_sec(0)
        if hasattr(self, "ai_katmani"):
            self.ai_katmani.rol_degisti()

    def sekme_sec(self, idx: int):
        if idx < 0 or idx >= len(self.menu_butonlari):
            return
        for i, b in enumerate(self.menu_butonlari):
            b.setProperty("secili", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        w = self.icerik.widget(idx)
        if w.property("_yer_tutucu"):
            gercek_w = self._sekme_fabrikalari[idx]()
            self.icerik.insertWidget(idx, gercek_w)
            self.icerik.removeWidget(w)
            w.deleteLater()
        elif hasattr(w, "yenile"):
            w.yenile()
        self.icerik.setCurrentIndex(idx)
        if hasattr(self, "ai_katmani"):
            self.ai_katmani.konumla()
            self.ai_katmani.balon.raise_()
            if self.ai_katmani.acik_mi():
                self.ai_katmani.panel.raise_()
                self.ai_katmani.balon.raise_()

    def rol_degistir(self):
        yeni_rol = self.cmb_rol_degis.currentData()
        if yeni_rol and yeni_rol != self.db.aktif_rol:
            self.db.aktif_rol = yeni_rol
            self.ekranlari_kur()

    def kullanici_degistir(self):
        dlg = GirisPenceresi(self.db)
        if dlg.exec() == QDialog.Accepted:
            self.ekranlari_kur()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(stil_uret())
    db = Veritabani()
    try:
        dlg = GirisPenceresi(db)
    except Exception as e:
        QMessageBox.critical(None, "Veritabanı Bağlantı Hatası", str(e))
        sys.exit(1)

    if dlg.exec() == QDialog.Accepted:
        pencere = AnaPencere(db)
        pencere.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
