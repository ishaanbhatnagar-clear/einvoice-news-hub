"""
Source crawlers for the eInvoice News Crawler
"""

from sources.base import BaseCrawler
from sources.zatca import ZATCACrawler
from sources.ey import EYCrawler
from sources.avalara import AvalaraCrawler
from sources.pagero import PageroCrawler
from sources.edicom import EDICOMCrawler
from sources.vertex import VertexCrawler
from sources.sovos import SovosCrawler
from sources.linkedin import LinkedInCrawler
from sources.vatupdate import VATUpdateCrawler
from sources.uae_fta import UAEFTACrawler
from sources.pagero_atlas import PageroAtlasCrawler
from sources.comarch import ComarchCrawler
from sources.egypt_eta import EgyptETACrawler
from sources.oman_ota import OmanOTACrawler
from sources.jordan_istd import JordanISTDCrawler
from sources.bahrain_nbr import BahrainNBRCrawler
from sources.qatar_gta import QatarGTACrawler
from sources.gulf_news import GulfNewsCrawler
from sources.arabian_business import ArabianBusinessCrawler
from sources.zawya import ZawyaCrawler
from sources.khaleej_times import KhaleejTimesCrawler

__all__ = [
    'BaseCrawler',
    'ZATCACrawler',
    'EYCrawler',
    'AvalaraCrawler',
    'PageroCrawler',
    'EDICOMCrawler',
    'VertexCrawler',
    'SovosCrawler',
    'LinkedInCrawler',
    'VATUpdateCrawler',
    'UAEFTACrawler',
    'PageroAtlasCrawler',
    'ComarchCrawler',
    'EgyptETACrawler',
    'OmanOTACrawler',
    'JordanISTDCrawler',
    'BahrainNBRCrawler',
    'QatarGTACrawler',
    'GulfNewsCrawler',
    'ArabianBusinessCrawler',
    'ZawyaCrawler',
    'KhaleejTimesCrawler',
]
