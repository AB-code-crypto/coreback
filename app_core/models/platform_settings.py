from django.core.exceptions import ValidationError
from django.db import models

from app_core.models import TimestampedModel

DEFAULT_STABLECOIN_CODES = """AEUR
AUDD
BOLD
BRZ
CADC
DAI
DECL
DJED
DOLA
EURA
EURC
EURI
EUROe
EURR
EURS
EURT
EURe
FDUSD
FRAX
GBPT
GBPe
GHO
GRAI
GUSD
GYEN
HAY
HCHF
JPYC
LUSD
MIM
MXNT
PAR
PYUSD
QCAD
RLUSD
TAUD
TRYB
TUSD
USD0
USD1
USDA
USDC
USDD
USDH
USDK
USDM
USDP
USDR
USDS
USDT
USDV
USDe
USK
USX
VAI
VCHF
XCHF
XIDR
XSGD
ZARP
agEUR
alUSD
cEUR
crvUSD
eUSD
frxUSD
jEUR
sUSD"""

DEFAULT_FIAT_CURRENCY_CODES = """AED
AFN
ALL
AMD
ANG
AOA
ARS
AUD
AWG
AZN
BAM
BBD
BDT
BGN
BHD
BIF
BMD
BND
BOB
BRL
BSD
BTN
BWP
BYN
BZD
CAD
CDF
CHF
CLP
CNY
COP
CRC
CUP
CVE
CZK
DJF
DKK
DOP
DZD
EGP
ERN
ETB
EUR
FJD
FKP
GBP
GEL
GHS
GIP
GMD
GNF
GTQ
GYD
HKD
HNL
HTG
HUF
IDR
ILS
INR
IQD
IRR
ISK
JMD
JOD
JPY
KES
KGS
KHR
KMF
KPW
KRW
KWD
KYD
KZT
LAK
LBP
LKR
LRD
LSL
LYD
MAD
MDL
MGA
MKD
MMK
MNT
MOP
MRU
MUR
MVR
MWK
MXN
MYR
MZN
NAD
NGN
NIO
NOK
NPR
NZD
OMR
PAB
PEN
PGK
PHP
PKR
PLN
PYG
QAR
RON
RSD
RUB
RWF
SAR
SBD
SCR
SDG
SEK
SGD
SHP
SLE
SOS
SRD
SSP
STN
SYP
SZL
THB
TJS
TMT
TND
TOP
TRY
TTD
TWD
TZS
UAH
UAHG
UGX
USD
UYU
UZS
VED
VES
VND
VUV
WST
XAF
XAUT
XCD
XOF
XPF
YER
ZAR
ZMW
ZWG"""

DEFAULT_MEMO_TAG_NETWORK_CODES = """ATOM
BNB
EOS
HBAR
KAVA
LUNA
LUNC
NOT
OSMO
TON
XEM
XLM
XRP"""


class PlatformSettings(TimestampedModel):
    stablecoin_codes = models.TextField(
        default=DEFAULT_STABLECOIN_CODES,
        blank=True,
        verbose_name="Коды стейблкоинов",
        help_text=(
            "Список кодов стейблкоинов. Можно вводить через запятую или с новой строки. "
            "При сохранении список будет очищен от дублей, отсортирован по алфавиту "
            "и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )
    fiat_currency_codes = models.TextField(
        default=DEFAULT_FIAT_CURRENCY_CODES,
        blank=True,
        verbose_name="Коды фиатных валют",
        help_text=(
            "Список кодов фиатных валют. Можно вводить через запятую или с новой строки. "
            "При сохранении список будет очищен от дублей, отсортирован по алфавиту "
            "и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )
    memo_tag_network_codes = models.TextField(
        default=DEFAULT_MEMO_TAG_NETWORK_CODES,
        blank=True,
        verbose_name="Коды сетей с MEMO/TAG",
        help_text=(
            "Список кодов сетей, где для перевода требуется MEMO, TAG, Destination Tag или аналогичное поле. "
            "Можно вводить через запятую или с новой строки. При сохранении список будет очищен от дублей, "
            "отсортирован по алфавиту и сохранён в одну строку через запятую и пробел. Регистр не изменяется."
        ),
    )

    class Meta:
        verbose_name = "Глобальные настройки платформы"
        verbose_name_plural = "Глобальные настройки платформы"

    def __str__(self) -> str:
        return "Platform settings"

    @staticmethod
    def _normalize_codes_text(value: str) -> str:
        if not value:
            return ""

        raw_items = value.replace("\n", ",").split(",")
        cleaned_items = []
        seen = set()

        for item in raw_items:
            item = item.strip()
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            cleaned_items.append(item)

        cleaned_items = sorted(cleaned_items, key=lambda x: x.casefold())
        return ", ".join(cleaned_items)

    @staticmethod
    def _split_codes_text(value: str) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def clean(self):
        super().clean()

        qs = self.__class__.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError("В системе может существовать только одна запись PlatformSettings.")

    def save(self, *args, **kwargs):
        self.stablecoin_codes = self._normalize_codes_text(self.stablecoin_codes)
        self.fiat_currency_codes = self._normalize_codes_text(self.fiat_currency_codes)
        self.memo_tag_network_codes = self._normalize_codes_text(self.memo_tag_network_codes)
        super().save(*args, **kwargs)

    def get_stablecoin_codes(self) -> list[str]:
        return self._split_codes_text(self.stablecoin_codes)

    def get_fiat_currency_codes(self) -> list[str]:
        return self._split_codes_text(self.fiat_currency_codes)

    def get_memo_tag_network_codes(self) -> list[str]:
        return self._split_codes_text(self.memo_tag_network_codes)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create()
        return obj
