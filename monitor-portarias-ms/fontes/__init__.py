from fontes.bvs import BVS
from fontes.anvisa import Anvisa
from fontes.dou import DOU
from fontes.govbr import GovBR
from fontes.iofmg import IOFMG
from fontes.sesmg import SESMG

SOURCES = {
    "dou": DOU,
    "bvs": BVS,
    "govbr": GovBR,
    "sesmg": SESMG,
    "iofmg": IOFMG,
    "anvisa": Anvisa,
}

__all__ = ["SOURCES", "BVS", "DOU", "GovBR", "SESMG", "IOFMG", "Anvisa"]
