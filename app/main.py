import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QWidget, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from app.db import Veritabani
from app.stil import OBS_STIL
from app.ekranlar.ogrenci_ana import OgrenciAnaSayfa, OgrenciDersSecimi
from app.ekranlar.ogrenci_diger import OgrenciNotlarTranskript, OgrenciMezuniyetSimulasyon
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
        self.setWindowTitle("OBS — Kullanıcı Girişi (Demo)")
        self.setFixedSize(420, 260)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        baslik = QLabel("Öğrenci Bilgi Sistemi")
        baslik.setObjectName("SayfaBaslik")
        alt = QLabel("Veritabanı RLS & Oturum Kimliği Demo Girişi")
        alt.setStyleSheet("color: #64748b; font-size: 12px;")
        lay.addWidget(baslik)
        lay.addWidget(alt)

        self.kullanicilar = self.db.demo_kullanicilar()

        lay.addWidget(QLabel("<b>Kullanıcı Seçin:</b>"))
        self.cmb_kul = QComboBox()
        for k in self.kullanicilar:
            roller_str = ", ".join(ROL_ADLARI.get(r, r) for r in (k["roller"] or []))
            self.cmb_kul.addItem(f"{k['ad_soyad']} ({roller_str})", k)
        self.cmb_kul.currentIndexChanged.connect(self._kullanici_degisti)
        lay.addWidget(self.cmb_kul)

        lay.addWidget(QLabel("<b>Giriş Rolü:</b>"))
        self.cmb_rol = QComboBox()
        lay.addWidget(self.cmb_rol)
        self._kullanici_degisti()

        lay.addStretch()
        btn = QPushButton("Sisteme Giriş Yap")
        btn.setObjectName("BirincilBtn")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self.kabul)
        lay.addWidget(btn)

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
        self.setMinimumSize(920, 580)
        ekran = QApplication.primaryScreen().availableGeometry()
        gen = min(1120, int(ekran.width() * 0.92))
        yuk = min(700, int(ekran.height() * 0.88))
        self.resize(gen, yuk)
        self.move(
            ekran.x() + (ekran.width() - gen) // 2,
            ekran.y() + (ekran.height() - yuk) // 2
        )

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana_lay = QVBoxLayout(merkez)
        ana_lay.setContentsMargins(0, 0, 0, 0)
        ana_lay.setSpacing(0)

        ust = QFrame()
        ust.setObjectName("UstCubuk")
        ust.setFixedHeight(46)
        u_lay = QHBoxLayout(ust)
        u_lay.setContentsMargins(18, 0, 18, 0)
        lbl_logo = QLabel("OBS  |  Öğrenci Bilgi Sistemi")
        lbl_logo.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        u_lay.addWidget(lbl_logo)
        u_lay.addStretch()

        self.lbl_oturum = QLabel()
        u_lay.addWidget(self.lbl_oturum)

        if len(self.db.roller) > 1:
            self.cmb_rol_degis = QComboBox()
            for r in self.db.roller:
                self.cmb_rol_degis.addItem(ROL_ADLARI.get(r, r), r)
            self.cmb_rol_degis.setCurrentIndex(self.db.roller.index(self.db.aktif_rol))
            self.cmb_rol_degis.currentIndexChanged.connect(self.rol_degistir)
            u_lay.addWidget(self.cmb_rol_degis)

        btn_cikis = QPushButton("Kullanıcı Değiştir")
        btn_cikis.setObjectName("IkincilBtn")
        btn_cikis.clicked.connect(self.kullanici_degistir)
        u_lay.addWidget(btn_cikis)
        ana_lay.addWidget(ust)

        govde = QHBoxLayout()
        govde.setContentsMargins(0, 0, 0, 0)
        govde.setSpacing(0)

        self.sol_menu = QFrame()
        self.sol_menu.setObjectName("SolMenu")
        self.sol_menu.setFixedWidth(195)
        self.menu_lay = QVBoxLayout(self.sol_menu)
        self.menu_lay.setContentsMargins(0, 12, 0, 12)
        self.menu_lay.setSpacing(2)
        govde.addWidget(self.sol_menu)

        self.icerik = QStackedWidget()
        govde.addWidget(self.icerik, 1)
        ana_lay.addLayout(govde, 1)

        self.menu_butonlari: list[QPushButton] = []
        self.ekranlari_kur()

    def ekranlari_kur(self):
        rol_ad = ROL_ADLARI.get(self.db.aktif_rol, self.db.aktif_rol)
        self.lbl_oturum.setText(f"{self.db.ad_soyad}  •  {rol_ad}  ")

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
                ("Ana Sayfa", OgrenciAnaSayfa(self.db)),
                ("Ders Seçimi & Sepet", OgrenciDersSecimi(self.db)),
                ("Notlar & Transkript", OgrenciNotlarTranskript(self.db)),
                ("Mezuniyet & Simülasyon", OgrenciMezuniyetSimulasyon(self.db)),
            ]
        elif self.db.aktif_rol == "rol_danisman":
            sekme_listesi = [
                ("Onay Kuyruğu", DanismanOnayKuyrugu(self.db)),
                ("Danışanlar & Risk Paneli", DanismanRiskPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_ogretim_uyesi":
            sekme_listesi = [
                ("Şubelerim, Not & Yoklama", OgretimUyesiPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_sekreter":
            sekme_listesi = [
                ("Sekreterlik İşlemleri", SekreterPaneli(self.db)),
            ]
        elif self.db.aktif_rol == "rol_yonetici":
            sekme_listesi = [
                ("Parametre & Denetim Logu", YoneticiPaneli(self.db)),
            ]
        else:
            sekme_listesi = []

        for idx, (ad, widget) in enumerate(sekme_listesi):
            btn = QPushButton(ad)
            btn.clicked.connect(lambda _, i=idx: self.sekme_sec(i))
            self.menu_lay.addWidget(btn)
            self.menu_butonlari.append(btn)
            self.icerik.addWidget(widget)

        self.menu_lay.addStretch()
        if self.menu_butonlari:
            self.sekme_sec(0)

    def sekme_sec(self, idx: int):
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
