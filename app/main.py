import os
import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QWidget, QStackedWidget, QFrame,
    QMessageBox, QDockWidget, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from app.db import Veritabani
from app.stil import (
    OLCULER, stil_uret, aktif_tema_adi, tema_kaydet, aktif_palet
)
from app.ekranlar.db_rontgen_ve_acid import SqlRontgenDialog
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
        self.setFixedSize(460, 320)

        ana = QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        ust_bant = QFrame()
        ust_bant.setStyleSheet("background-color: #12355B; border-bottom: 3px solid #2563EB;")
        ub_lay = QVBoxLayout(ust_bant)
        ub_lay.setContentsMargins(24, 18, 24, 16)
        lbl_b = QLabel("ÖĞRENCİ BİLGİ SİSTEMİ PORTALI")
        lbl_b.setStyleSheet("color: #FFFFFF; font-size: 14pt; font-weight: 800; letter-spacing: 0.4px;")
        lbl_a = QLabel("Satır Düzeyi Güvenlik (RLS) & Çok Rollü Akademik Yönetim")
        lbl_a.setStyleSheet("color: #93C5FD; font-size: 9.5pt;")
        ub_lay.addWidget(lbl_b)
        ub_lay.addWidget(lbl_a)
        ana.addWidget(ust_bant)

        kart = QFrame()
        kart.setObjectName("PortalKart")
        lay = QVBoxLayout(kart)
        lay.setContentsMargins(24, 20, 24, 22)
        lay.setSpacing(10)

        self.kullanicilar = self.db.demo_kullanicilar()

        lay.addWidget(QLabel("<b>Kullanıcı Hesabı Seçin:</b>"))
        self.cmb_kul = QComboBox()
        self.cmb_kul.setMinimumHeight(34)
        for k in self.kullanicilar:
            roller_str = ", ".join(ROL_ADLARI.get(r, r) for r in (k["roller"] or []))
            self.cmb_kul.addItem(f"{k['ad_soyad']} ({roller_str})", k)
        self.cmb_kul.currentIndexChanged.connect(self._kullanici_degisti)
        lay.addWidget(self.cmb_kul)

        lay.addWidget(QLabel("<b>Oturum Rolü:</b>"))
        self.cmb_rol = QComboBox()
        self.cmb_rol.setMinimumHeight(34)
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

        # Tasarım Sistemi: Asgari pencere genişliği 1100 px, yüksekliği 700 px
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

        # Sol Menü: Genişlik 220 px (#12355B lacivert)
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

        # Sol menü altında klavye kısayolları bilgi kartı
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

        btn_sql = QPushButton("🔍  SQL & EXPLAIN Röntgeni")
        btn_sql.setObjectName("UstBarBtn")
        btn_sql.clicked.connect(lambda: SqlRontgenDialog(self.db, self).exec())
        u_lay.addWidget(btn_sql)

        btn_cikis = QPushButton("⇥  Kullanıcı Değiştir")
        btn_cikis.setObjectName("IkincilBtn")
        btn_cikis.clicked.connect(self.kullanici_degistir)
        u_lay.addWidget(btn_cikis)

        sag_govde.addWidget(ust)

        self.icerik = QStackedWidget()
        sag_govde.addWidget(self.icerik, 1)
        ana_lay.addLayout(sag_govde, 1)

        # Sunum Modu: Sağda QDockWidget (Demo Rehberi)
        self.demo_dock = DemoRehberiDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.demo_dock)

        self.menu_butonlari: list[QPushButton] = []
        self._kisayollari_kur()
        self.ekranlari_kur()

    def _kisayollari_kur(self):
        """
        Tasarım Sistemi Klavye Kısayolları:
        - Ctrl+1 … Ctrl+6 : Ekranlara geç
        - F5 : Yenile
        - Ctrl+Enter : Kesinleştir
        - Esc : İletişim kutusunu kapat / filtreyi temizle
        """
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
        self.aktif_ekrani_yenile()

    def demo_rehberi_ac_kapat(self):
        self.demo_dock.setVisible(not self.demo_dock.isVisible())

    def demo_adimina_git(self, hedef_rol: str, hedef_ekran: int):
        """
        Demo rehberindeki 'Git ➔' düğmesine basıldığında doğru kullanıcıya,
        role ve ekrana otomatik geçirir.
        """
        if self.db.aktif_rol != hedef_rol:
            # Mevcut kullanıcının bu rolü varsa doğrudan rol değiştir
            if hedef_rol in (self.db.roller or []):
                self.db.aktif_rol = hedef_rol
            else:
                # Demo kullanıcıları arasından bu role sahip ilk kullanıcıya geç
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
                        hedef_rol
                    )
            self.ekranlari_kur()
        self.sekme_sec(hedef_ekran)

    def ekranlari_kur(self):
        rol_ad = ROL_ADLARI.get(self.db.aktif_rol, self.db.aktif_rol)
        bas_harf = "".join([x[0] for x in self.db.ad_soyad.split()[:2]]).upper()
        self.lbl_sol_avatar.setText(bas_harf or "OB")
        self.lbl_sol_isim.setText(self.db.ad_soyad)
        self.lbl_sol_rol.setText(rol_ad)

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
                ("⚙️   Ana Görünüm (Ctrl+1)", OgrenciAnaSayfa(self.db, self.sekme_sec)),
                ("📝   Ders Kayıt İşlemleri (Ctrl+2)", OgrenciDersSecimi(self.db)),
                ("A+   Not Bilgileri (Ctrl+3)", OgrenciNotlarTranskript(self.db)),
                ("🎓   Mezuniyet & DAG (Ctrl+4)", OgrenciMezuniyetSimulasyon(self.db)),
                ("👤   Kişisel & Takvim (Ctrl+5)", OgrenciKisiselVeTakvim(self.db)),
            ]
        elif self.db.aktif_rol == "rol_danisman":
            sekme_listesi = [
                ("☑️   Onay Kuyruğu (Ctrl+1)", DanismanOnayKuyrugu(self.db)),
                ("📊   Danışanlar & YZ Risk (Ctrl+2)", DanismanRiskPaneli(self.db)),
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
