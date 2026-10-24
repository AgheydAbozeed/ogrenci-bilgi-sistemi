-- =====================================================================
-- 001_sema.sql  --  AI Destekli Ogrenci Bilgi Sistemi (SIS)
-- Tablolar, anahtarlar ve bildirimsel (declarative) butunluk kisitlari
-- PostgreSQL 16+   |   Calistirma:  psql -d obs -f sql/001_sema.sql
-- Not: Tablo/sutun adlari Turkce karaktersizdir. Yonetmelik degerleri
--      kodda degil parametre tablolarindadir (003 dosyasindaki degerler ORNEKTIR).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;  -- EXCLUDE kisitinda "=" ile aralik (&&) birlesimi icin

-- ---------------------------------------------------------------------
-- 1) PARAMETRE TABLOLARI
-- ---------------------------------------------------------------------
CREATE TABLE harf_notu_aralik (
  harf      varchar(2)   PRIMARY KEY,
  min_puan  numeric(5,2) NOT NULL CHECK (min_puan BETWEEN 0 AND 100),
  katsayi   numeric(3,2) NOT NULL CHECK (katsayi BETWEEN 0 AND 4),
  gecer_mi  boolean      NOT NULL
);

CREATE TABLE akts_limit_kural (             -- GNO araligina gore donemlik AKTS ust siniri
  kural_id  serial       PRIMARY KEY,
  min_gno   numeric(4,2) NOT NULL,          -- dahil
  max_gno   numeric(4,2) NOT NULL,          -- haric
  max_akts  smallint     NOT NULL CHECK (max_akts > 0),
  CHECK (min_gno < max_gno),
  EXCLUDE USING gist (numrange(min_gno, max_gno, '[)') WITH &&)   -- araliklar cakisamaz
);

CREATE TABLE parametre (
  anahtar   text PRIMARY KEY,
  deger     text NOT NULL,
  aciklama  text
);

-- ---------------------------------------------------------------------
-- 2) AKADEMIK YAPI
-- ---------------------------------------------------------------------
CREATE TABLE bolum (
  bolum_id serial PRIMARY KEY,
  ad       text NOT NULL UNIQUE
);

CREATE TABLE program (
  program_id  serial PRIMARY KEY,
  bolum_id    int      NOT NULL REFERENCES bolum(bolum_id) ON DELETE RESTRICT,
  ad          text     NOT NULL,
  toplam_akts smallint NOT NULL CHECK (toplam_akts > 0),
  min_gno     numeric(3,2) NOT NULL DEFAULT 2.00 CHECK (min_gno BETWEEN 0 AND 4),
  UNIQUE (bolum_id, ad)
);

CREATE TABLE mufredat (
  mufredat_id serial PRIMARY KEY,
  program_id  int      NOT NULL REFERENCES program(program_id) ON DELETE RESTRICT,
  giris_yili  smallint NOT NULL CHECK (giris_yili BETWEEN 1990 AND 2100),
  UNIQUE (program_id, giris_yili)
);

CREATE TABLE ders (
  ders_id       serial PRIMARY KEY,
  kod           varchar(12) NOT NULL UNIQUE,
  ad            text        NOT NULL,
  akts          smallint    NOT NULL CHECK (akts > 0),
  teorik_saat   smallint    NOT NULL DEFAULT 0 CHECK (teorik_saat >= 0),
  uygulama_saat smallint    NOT NULL DEFAULT 0 CHECK (uygulama_saat >= 0)
);

CREATE TABLE mufredat_ders (                -- mufredat N-M ders
  mufredat_id int      NOT NULL REFERENCES mufredat(mufredat_id) ON DELETE CASCADE,
  ders_id     int      NOT NULL REFERENCES ders(ders_id) ON DELETE RESTRICT,
  donem_no    smallint NOT NULL CHECK (donem_no BETWEEN 1 AND 12),
  tur         varchar(8) NOT NULL CHECK (tur IN ('zorunlu','secmeli')),
  PRIMARY KEY (mufredat_id, ders_id)
);

CREATE TABLE onkosul (                      -- ders N-M ders (kendine baglanan iliski)
  ders_id          int NOT NULL REFERENCES ders(ders_id) ON DELETE CASCADE,
  onkosul_ders_id  int NOT NULL REFERENCES ders(ders_id) ON DELETE CASCADE,
  min_harf         varchar(2) NOT NULL DEFAULT 'DD' REFERENCES harf_notu_aralik(harf),
  PRIMARY KEY (ders_id, onkosul_ders_id),
  CHECK (ders_id <> onkosul_ders_id)
);

CREATE TABLE gereksinim_grubu (             -- mezuniyet denetimi icin gereksinim gruplari
  grup_id     serial PRIMARY KEY,
  mufredat_id int      NOT NULL REFERENCES mufredat(mufredat_id) ON DELETE CASCADE,
  ad          text     NOT NULL,
  tur         varchar(13) NOT NULL CHECK (tur IN ('zorunlu','secmeli_havuz')),
  min_ders    smallint NOT NULL DEFAULT 0 CHECK (min_ders >= 0),
  min_akts    smallint NOT NULL DEFAULT 0 CHECK (min_akts >= 0),
  oncelik     smallint NOT NULL DEFAULT 100,        -- eslestirmede kucuk = once
  cift_sayim  boolean  NOT NULL DEFAULT false,      -- ders baska gruplarda da sayilabilir mi
  UNIQUE (mufredat_id, ad)
);

CREATE TABLE gereksinim_grubu_ders (
  grup_id int NOT NULL REFERENCES gereksinim_grubu(grup_id) ON DELETE CASCADE,
  ders_id int NOT NULL REFERENCES ders(ders_id) ON DELETE RESTRICT,
  PRIMARY KEY (grup_id, ders_id)
);

-- ---------------------------------------------------------------------
-- 3) KISILER (genelleme: kisi -> ogrenci / ogretim_uyesi)
-- ---------------------------------------------------------------------
CREATE TABLE kisi (
  kisi_id serial PRIMARY KEY,
  ad      text NOT NULL,
  soyad   text NOT NULL,
  eposta  text NOT NULL UNIQUE CHECK (eposta LIKE '_%@_%')
);

CREATE TABLE ogretim_uyesi (
  kisi_id  int  PRIMARY KEY REFERENCES kisi(kisi_id) ON DELETE CASCADE,
  bolum_id int  NOT NULL REFERENCES bolum(bolum_id),
  unvan    text NOT NULL
);

CREATE TABLE ogrenci (
  kisi_id     int PRIMARY KEY REFERENCES kisi(kisi_id) ON DELETE CASCADE,
  ogrenci_no  varchar(12) NOT NULL UNIQUE,
  program_id  int NOT NULL REFERENCES program(program_id),
  mufredat_id int NOT NULL REFERENCES mufredat(mufredat_id),
  giris_yili  smallint NOT NULL CHECK (giris_yili BETWEEN 1990 AND 2100),
  durum       varchar(8) NOT NULL DEFAULT 'aktif' CHECK (durum IN ('aktif','mezun','dondurdu','ayrildi'))
);

CREATE TABLE kisi_rol (                     -- danisman rolu iliskiden turer (danismanlik), burada yok
  kisi_id int NOT NULL REFERENCES kisi(kisi_id) ON DELETE CASCADE,
  rol     varchar(13) NOT NULL CHECK (rol IN ('ogrenci','ogretim_uyesi','sekreter','yonetici')),
  PRIMARY KEY (kisi_id, rol)
);

CREATE TABLE danismanlik (                  -- ogrenci N-M ogretim uyesi, tarih araliklı
  danismanlik_id serial PRIMARY KEY,
  ogrenci_id     int NOT NULL REFERENCES ogrenci(kisi_id),
  danisman_id    int NOT NULL REFERENCES ogretim_uyesi(kisi_id),
  gecerlilik     daterange NOT NULL,
  EXCLUDE USING gist (ogrenci_id WITH =, gecerlilik WITH &&)    -- ayni anda tek aktif danisman
);

-- ---------------------------------------------------------------------
-- 4) DONEM VE SUBE
-- ---------------------------------------------------------------------
CREATE TABLE donem (
  donem_id         serial PRIMARY KEY,
  yil              smallint NOT NULL CHECK (yil BETWEEN 1990 AND 2100),
  tur              varchar(5) NOT NULL CHECK (tur IN ('guz','bahar','yaz')),
  kayit_baslangic  timestamptz NOT NULL,
  kayit_bitis      timestamptz NOT NULL,
  ekle_birak_bitis timestamptz NOT NULL,
  donem_sonu       timestamptz NOT NULL,
  UNIQUE (yil, tur),
  CHECK (kayit_baslangic < kayit_bitis AND kayit_bitis < ekle_birak_bitis AND ekle_birak_bitis < donem_sonu)
);

CREATE TABLE sube (                         -- dersin bir donemde acilan ornegi (ITU'de CRN)
  sube_id          serial PRIMARY KEY,
  ders_id          int      NOT NULL REFERENCES ders(ders_id),
  donem_id         int      NOT NULL REFERENCES donem(donem_id),
  sube_no          smallint NOT NULL CHECK (sube_no > 0),
  ogretim_uyesi_id int      NOT NULL REFERENCES ogretim_uyesi(kisi_id),
  UNIQUE (ders_id, donem_id, sube_no),
  UNIQUE (sube_id, ders_id, donem_id)       -- kayit tablosundaki bilesik yabanci anahtar icin
);

CREATE TABLE sube_saat (                    -- ayrik ders saati dilimleri (1..12)
  sube_id    int      NOT NULL REFERENCES sube(sube_id) ON DELETE CASCADE,
  gun        smallint NOT NULL CHECK (gun BETWEEN 1 AND 7),
  ders_saati smallint NOT NULL CHECK (ders_saati BETWEEN 1 AND 12),
  PRIMARY KEY (sube_id, gun, ders_saati)
);

-- ---------------------------------------------------------------------
-- 5) KAYIT, ONAY, NOT
-- ---------------------------------------------------------------------
CREATE TABLE kayit_gecis (                  -- izinli durum gecisleri (durum makinesi)
  onceki  varchar(13) NOT NULL,
  sonraki varchar(13) NOT NULL,
  PRIMARY KEY (onceki, sonraki)
);

CREATE TABLE kayit (
  kayit_id   serial PRIMARY KEY,
  ogrenci_id int NOT NULL REFERENCES ogrenci(kisi_id),
  sube_id    int NOT NULL,
  ders_id    int NOT NULL,                  -- sube'den turer (tetikleyici doldurur); tutarliligi bilesik FK saglar
  donem_id   int NOT NULL,
  durum      varchar(13) NOT NULL DEFAULT 'sepet'
             CHECK (durum IN ('sepet','onay_bekliyor','onayli','reddedildi','birakti')),
  olusturma  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (sube_id, ders_id, donem_id) REFERENCES sube(sube_id, ders_id, donem_id),
  UNIQUE (kayit_id, sube_id)                -- not_kaydi bilesik FK icin
);
CREATE UNIQUE INDEX ux_kayit_aktif ON kayit (ogrenci_id, ders_id, donem_id)
  WHERE durum NOT IN ('reddedildi','birakti');   -- ayni donem ayni dersin iki subesi olamaz

CREATE TABLE kayit_onay (
  onay_id     serial PRIMARY KEY,
  kayit_id    int NOT NULL REFERENCES kayit(kayit_id) ON DELETE CASCADE,
  danisman_id int NOT NULL REFERENCES ogretim_uyesi(kisi_id),
  karar       varchar(13) NOT NULL CHECK (karar IN ('onay','red','duzeltme_iste')),
  gerekce     text,
  zaman       timestamptz NOT NULL DEFAULT now(),
  CHECK (karar = 'onay' OR length(trim(coalesce(gerekce, ''))) > 0)   -- red/duzeltme gerekcesiz olmaz
);

CREATE TABLE ogrenci_slot (                 -- ogrencinin dolu saat dilimleri: cakismayi BIRINCIL ANAHTAR yakalar
  ogrenci_id int      NOT NULL REFERENCES ogrenci(kisi_id),
  donem_id   int      NOT NULL REFERENCES donem(donem_id),
  gun        smallint NOT NULL,
  ders_saati smallint NOT NULL,
  kayit_id   int      NOT NULL REFERENCES kayit(kayit_id) ON DELETE CASCADE,
  PRIMARY KEY (ogrenci_id, donem_id, gun, ders_saati)
);

CREATE TABLE degerlendirme_bileseni (
  bilesen_id serial PRIMARY KEY,
  sube_id    int          NOT NULL REFERENCES sube(sube_id) ON DELETE CASCADE,
  ad         text         NOT NULL,
  agirlik    numeric(5,2) NOT NULL CHECK (agirlik > 0 AND agirlik <= 100),
  UNIQUE (sube_id, ad),
  UNIQUE (bilesen_id, sube_id)              -- not_kaydi bilesik FK icin
);

CREATE TABLE not_kaydi (
  kayit_id    int          NOT NULL,
  bilesen_id  int          NOT NULL,
  sube_id     int          NOT NULL,
  puan        numeric(5,2) NOT NULL CHECK (puan BETWEEN 0 AND 100),
  ilan_edildi boolean      NOT NULL DEFAULT false,
  PRIMARY KEY (kayit_id, bilesen_id),
  FOREIGN KEY (kayit_id, sube_id)   REFERENCES kayit(kayit_id, sube_id) ON DELETE CASCADE,
  FOREIGN KEY (bilesen_id, sube_id) REFERENCES degerlendirme_bileseni(bilesen_id, sube_id) ON DELETE CASCADE
);  -- puanin bileseni ile kaydin subesi ayni olmak zorunda (iki bilesik FK)

CREATE TABLE kayit_sonuc (
  kayit_id      int PRIMARY KEY REFERENCES kayit(kayit_id) ON DELETE CASCADE,
  ortalama_puan numeric(5,2),
  harf          varchar(2) REFERENCES harf_notu_aralik(harf),
  durum         varchar(8) NOT NULL CHECK (durum IN ('gecti','kaldi','devamsiz','muaf')),
  hesap_zamani  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE yoklama (
  kayit_id int     NOT NULL REFERENCES kayit(kayit_id) ON DELETE CASCADE,
  tarih    date    NOT NULL,
  katildi  boolean NOT NULL,
  PRIMARY KEY (kayit_id, tarih)
);

-- ---------------------------------------------------------------------
-- 6) DENETIM, BELGE, RISK
-- ---------------------------------------------------------------------
CREATE TABLE denetim_log (
  log_id      bigserial PRIMARY KEY,
  tablo       text    NOT NULL,
  kayit_pk    text    NOT NULL,
  islem       char(1) NOT NULL CHECK (islem IN ('I','U','D')),
  eski        jsonb,
  yeni        jsonb,
  kullanici   text        NOT NULL DEFAULT current_user,
  zaman       timestamptz NOT NULL DEFAULT clock_timestamp(),
  onceki_hash text,
  hash        text NOT NULL
);

CREATE TABLE belge (
  belge_id       serial PRIMARY KEY,
  ogrenci_id     int         NOT NULL REFERENCES ogrenci(kisi_id),
  tur            varchar(20) NOT NULL CHECK (tur IN ('ogrenci_belgesi','transkript')),
  uretim_zamani  timestamptz NOT NULL DEFAULT now(),
  dogrulama_kodu varchar(16) NOT NULL UNIQUE,
  icerik_hash    text        NOT NULL
);

CREATE TABLE risk_kural (
  kod      varchar(30) PRIMARY KEY,
  aciklama text     NOT NULL,
  siddet   smallint NOT NULL CHECK (siddet BETWEEN 1 AND 3)
);

CREATE TABLE risk_bayrak (
  bayrak_id  serial PRIMARY KEY,
  ogrenci_id int         NOT NULL REFERENCES ogrenci(kisi_id),
  donem_id   int         NOT NULL REFERENCES donem(donem_id),
  kural_kod  varchar(30) NOT NULL REFERENCES risk_kural(kod),
  zaman      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ogrenci_id, donem_id, kural_kod)
);

CREATE TABLE model_surum (
  model_id      serial PRIMARY KEY,
  ad            text        NOT NULL UNIQUE,
  egitim_zamani timestamptz NOT NULL DEFAULT now(),
  metrikler     jsonb       NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE risk_tahmin (
  tahmin_id    serial PRIMARY KEY,
  ogrenci_id   int          NOT NULL REFERENCES ogrenci(kisi_id),
  donem_id     int          NOT NULL REFERENCES donem(donem_id),
  model_id     int          NOT NULL REFERENCES model_surum(model_id),
  skor         numeric(4,3) NOT NULL CHECK (skor BETWEEN 0 AND 1),
  ozellikler   jsonb        NOT NULL,        -- tahminin hangi ozelliklerle yapildigi (aciklanabilirlik)
  hesap_zamani timestamptz  NOT NULL DEFAULT now(),
  UNIQUE (ogrenci_id, donem_id, model_id)
);

-- ---------------------------------------------------------------------
-- 7) INDEKSLER (yabanci anahtar sutunlari ve sik sorgular)
-- ---------------------------------------------------------------------
CREATE INDEX ix_kayit_ogrenci     ON kayit (ogrenci_id, donem_id);
CREATE INDEX ix_kayit_sube        ON kayit (sube_id);
CREATE INDEX ix_sube_donem        ON sube (donem_id, ders_id);
CREATE INDEX ix_not_bilesen       ON not_kaydi (bilesen_id);
CREATE INDEX ix_risk_bayrak_ogr   ON risk_bayrak (ogrenci_id, donem_id);
CREATE INDEX ix_risk_tahmin_ogr   ON risk_tahmin (ogrenci_id, donem_id);
CREATE INDEX ix_denetim_tablo_pk  ON denetim_log (tablo, kayit_pk);
CREATE INDEX ix_danismanlik_danis ON danismanlik (danisman_id);
