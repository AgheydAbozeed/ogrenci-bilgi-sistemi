import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QWidget, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from app.db import Veritabani
from app.stil import OBS_STIL
from app.ekranlar.ogrenci_ana import OgrenciAnaSayfa, OgrenciDersSecimi
from app.ekranlar.ogrenci_diger import (
    OgrenciKisiselVeTakvim, OgrenciNotlarTranskript, OgrenciMezuniyetSimulasyon
)
from app.ekranlar.danisman_ekran import DanismanOnayKuyrugu, DanismanRiskPaneli
from app.ekranlar.hoca_ve_yonetim import OgretimUyesiPaneli, SekreterPaneli, YoneticiPaneli

ROL_ADLARI = {
    "rol_ogrenci": "Öğrenci",
    "rol_danisman": "Akademik Danışman",
    "rol_ogretim_uyesi": "Öğretim Üyesi",
    "rol_sekreter": "Bölüm Sekreteri",
    "rol_yonetici": "Sistem Yöneticisi",
}


class GirisPenceresi(QDialog):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.setWindowTitle("OBS — Kullanıcı Girişi")
        self.setFixedSize(440, 300)

        ana = QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        ust_bant = QFrame()
        ust_bant.setStyleSheet("background-color: #093567; border-bottom: 3px solid #1d70db;")
        ub_lay = QVBoxLayout(ust_bant)
        ub_lay.setContentsMargins(24, 18, 24, 16)
        lbl_b = QLabel("ÖĞRENCİ BİLGİ SİSTEMİ PORTALI")
        lbl_b.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800; letter-spacing: 0.5px;")
        lbl_a = QLabel("Satır Düzeyi Güvenlik (RLS) & Çok Rollü Akademik Yönetim")
        lbl_a.setStyleSheet("color: #93c5fd; font-size: 11px;")
        ub_lay.addWidget(lbl_b)
        ub_lay.addWidget(lbl_a)
        ana.addWidget(ust_bant)

        kart = QFrame()
        kart.setObjectName("PortalKart")
        lay = QVBoxLayout(kart)
        lay.setContentsMargins(26, 20, 26, 22)
        lay.setSpacing(10)

        self.kullanicilar = self.db.demo_kullanicilar()

        lay.addWidget(QLabel("<b>Kullanıcı Hesabı Seçin:</b>"))
        self.cmb_kul = QComboBox()
        self.cmb_kul.setMinimumHeight(32)
        for k in self.kullanicilar:
            roller_str = ", ".join(ROL_ADLARI.get(r, r) for r in (k["roller"] or []))
            self.cmb_kul.addItem(f"{k['ad_soyad']} ({roller_str})", k)
        self.cmb_kul.currentIndexChanged.connect(self._kullanici_degisti)
        lay.addWidget(self.cmb_kul)

        lay.addWidget(QLabel("<b>Oturum Rolü:</b>"))
        self.cmb_rol = QComboBox()
        self.cmb_rol.setMinimumHeight(32)
        lay.addWidget(self.cmb_rol)
        self._kullanici_degisti()

        lay.addStretch()
        btn = QPushButton("Sisteme Giriş Yap  ➔")
        btn.setObjectName("BirincilBtn")
        btn.setMinimumHeight(38)
        btn.clicked.connect(self.kabul)
        lay.addWidget(btn)
        ana.addWidget(kart, 1)

    def _kullanici_degisti(self):
        self.cmb_rol.clear()
        k = self.cmb_kul.currentData()
        if not k:
            return
        for r in (k["roller"] or []):
            self.cmb_rol.addItem(ROL_ADLARI.get(r, r), r)

    def kabul(self):
        k = self.cmb_kul.currentData()
        rol = self.cmb_rol.currentData()
        if not k or not rol:
            return
        self.db.oturum_ayarla(k["kisi_id"], k["ad_soyad"], k["roller"], rol)
        self.accept()


class AnaPencere(QMainWindow):
    def __init__(self, db: Veritabani):
        super().__init__()
        self.db = db
        self.setWindowTitle("Öğrenci Bilgi Sistemi (OBS)")
        self.setMinimumSize(940, 600)
        ekran = QApplication.primaryScreen().availableGeometry()
        gen = min(1150, int(ekran.width() * 0.93))
        yuk = min(720, int(ekran.height() * 0.89))
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
        self.sol_menu.setFixedWidth(215)
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
            "background-color: #1d70db; color: #ffffff; font-weight: 800; "
            "font-size: 13px; border-radius: 18px;"
        )
        p_lay.addWidget(self.lbl_sol_avatar)

        v_isim = QVBoxLayout()
        v_isim.setSpacing(2)
        self.lbl_sol_isim = QLabel()
        self.lbl_sol_isim.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 12px;")
        self.lbl_sol_rol = QLabel()
        self.lbl_sol_rol.setStyleSheet("color: #93c5fd; font-size: 10px;")
        v_isim.addWidget(self.lbl_sol_isim)
        v_isim.addWidget(self.lbl_sol_rol)
        p_lay.addLayout(v_isim, 1)
        sol_ana_lay.addWidget(profil_kutu)

        self.menu_lay = QVBoxLayout()
        self.menu_lay.setContentsMargins(0, 8, 0, 8)
        self.menu_lay.setSpacing(2)
        sol_ana_lay.addLayout(self.menu_lay, 1)
        ana_lay.addWidget(self.sol_menu)

        sag_govde = QVBoxLayout()
        sag_govde.setContentsMargins(0, 0, 0, 0)
        sag_govde.setSpacing(0)

        ust = QFrame()
        ust.setObjectName("UstCubuk")
        ust.setFixedHeight(48)
        u_lay = QHBoxLayout(ust)
        u_lay.setContentsMargins(20, 0, 20, 0)
        u_lay.setSpacing(12)

        lbl_kurum = QLabel("ÖĞRENCİ BİLGİ SİSTEMİ PORTALI")
        lbl_kurum.setStyleSheet("color: #093567; font-weight: 800; font-size: 13px; letter-spacing: 0.4px;")
        u_lay.addWidget(lbl_kurum)
        u_lay.addStretch()

        lbl_yardim = QLabel("🛟 OBS YARDIM")
        lbl_yardim.setStyleSheet("color: #dc2626; font-weight: 700; font-size: 11px;")

        lbl_dil = QLabel("Türkçe ▾")
        lbl_dil.setStyleSheet(
            "color: #334155; background-color: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )

        if len(self.db.roller) > 1:
            self.cmb_rol_degis = QComboBox()
            for r in self.db.roller:
                self.cmb_rol_degis.addItem(ROL_ADLARI.get(r, r), r)
            self.cmb_rol_degis.setCurrentIndex(self.db.roller.index(self.db.aktif_rol))
            self.cmb_rol_degis.currentIndexChanged.connect(self.rol_degistir)
            u_lay.addWidget(self.cmb_rol_degis)

        btn_cikis = QPushButton("⇥ Kullanıcı Değiştir")
        btn_cikis.setObjectName("IkincilBtn")
        btn_cikis.clicked.connect(self.kullanici_degistir)
        u_lay.addWidget(btn_cikis)

        sag_govde.addWidget(ust)

        self.icerik = QStackedWidget()
        sag_govde.addWidget(self.icerik, 1)
        ana_lay.addLayout(sag_govde, 1)

        self.menu_butonlari: list[QPushButton] = []
        self.ekranlari_kur()

    def ekranlari_kur(self):
        rol_ad = ROL_ADLARI.get(self.db.aktif_rol, self.db.aktif_rol)
        bas_harf = "".join([x[0] for x in self.db.ad_soyad.split()[:2]]).upper()
        self.lbl_sol_avatar.setText(bas_harf or "OB")
        self.lbl_sol_isim.setText(self.db.ad_soyad)
        self.lbl_sol_rol.setText(rol_ad)

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
                ("⚙️   Ana Görünüm", OgrenciAnaSayfa(self.db, self.sekme_sec)),
                ("📝   Ders Kayıt İşlemleri", OgrenciDersSecimi(self.db)),
                ("A+   Not Bilgileri", OgrenciNotlarTranskript(self.db)),
                ("🎓   Mezuniyetime Ne Kaldı?", OgrenciMezuniyetSimulasyon(self.db)),
                ("👤   Kişisel & Danışman / Takvim", OgrenciKisiselVeTakvim(self.db)),
            ]
        elif self.db.aktif_rol == "rol_danisman":
            sekme_listesi = [
                ("☑️   Onay Kuyruğu", DanismanOnayKuyrugu(self.db)),
                ("📊   Danışanlar & YZ Risk Paneli", DanismanRiskPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_ogretim_uyesi":
            sekme_listesi = [
                ("👨‍🏫   Şubelerim, Not & Yoklama", OgretimUyesiPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_sekreter":
            sekme_listesi = [
                ("🗂️   Sekreterlik İşlemleri", SekreterPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_yonetici":
            sekme_listesi = [
                ("🛡️   Parametre & Denetim Logu", YoneticiPaneli(self.db)),
            ]
        else:
            sekme_listesi = []

        for idx, (etiket, widget) in enumerate(sekme_listesi):
            btn = QPushButton(etiket)
            btn.clicked.connect(lambda _, i=idx: self.sekme_sec(i))
            self.menu_lay.addWidget(btn)
            self.menu_butonlari.append(btn)
            self.icerik.addWidget(widget)

        self.menu_lay.addStretch()
        if self.menu_butonlari:
            self.sekme_sec(0)

    def sekme_sec(self, idx: int):
        if idx < 0 or idx >= len(self.menu_butonlari):
            return
        for i, b in enumerate(self.menu_butonlari):
            b.setProperty("secili", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        w = self.icerik.widget(idx)
        if hasattr(w, "yenile"):
            w.yenile()
        self.icerik.setCurrentIndex(idx)

    def rol_degistir(self):
        yeni_rol = self.cmb_rol_degis.currentData()
        if yeni_rol and yeni_rol != self.db.aktif_rol:
            self.db.aktif_rol = yeni_rol
            self.ekranlari_kur()

    def kullanici_degistir(self):
        dlg = GirisPenceresi(self.db)
        if dlg.exec() == QDialog.Accepted:
            self.close()
            self.yeni_pencere = AnaPencere(self.db)
            self.yeni_pencere.show()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(OBS_STIL)
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
