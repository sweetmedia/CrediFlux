# -*- coding: utf-8 -*-
"""
RNC Lookup Service
Provides fast RNC/Cedula validation and information lookup using cached DGII data

3-Layer Validation Architecture:
- Layer 1: Format validation (before touching the cache)
- Layer 2: Local DGII database lookup (one cache key per RNC: O(1))
- Layer 3: Live DGII website scraping (only for authenticated callers)

Cache layout:
- ``dgii_rnc:{rnc}`` -> dict with the record (razon_social, estado, ...)
- ``dgii_rnc_database_meta`` -> {'count': N, 'loaded_at': iso, 'source': ...},
  written last by the loaders; its presence means the registry is loaded.
"""
import re
import logging
from typing import Optional, Dict
from django.core.cache import cache
from django.utils import timezone
from .dgii_scraper import scrape_dgii_rnc

logger = logging.getLogger(__name__)

RECORD_KEY_PREFIX = 'dgii_rnc:'
META_KEY = 'dgii_rnc_database_meta'
# Formato anterior: todo el padrón en una sola clave JSON. Nunca se lee.
LEGACY_CACHE_KEY = 'dgii_rnc_database'
BATCH_SIZE = 5000


def record_key(rnc: str) -> str:
    """Cache key for an RNC; normalized like lookups (11 digits, zero-padded)."""
    return f'{RECORD_KEY_PREFIX}{RNCLookupService._normalize_rnc(rnc)}'


def store_rnc_records(rnc_data: Dict[str, Dict], *, source: str, timeout=None) -> int:
    """
    Write the registry to the cache, one key per RNC, in batches of BATCH_SIZE.
    The meta key is written last, so the registry only counts as loaded once
    every record is in place. Shared by the management command and the Celery task.
    """
    count = 0
    batch = {}
    for rnc, record in rnc_data.items():
        batch[record_key(rnc)] = record
        if len(batch) >= BATCH_SIZE:
            cache.set_many(batch, timeout=timeout)
            count += len(batch)
            batch = {}
    if batch:
        cache.set_many(batch, timeout=timeout)
        count += len(batch)

    cache.set(
        META_KEY,
        {'count': count, 'loaded_at': timezone.now().isoformat(), 'source': source},
        timeout=timeout,
    )
    # Libera el blob del formato anterior si seguía en caché.
    cache.delete(LEGACY_CACHE_KEY)
    return count


class RNCLookupService:
    """Service for looking up RNC/Cedula information from DGII cached database"""

    @classmethod
    def lookup(cls, rnc_or_cedula: str) -> Optional[Dict]:
        """
        Look up an RNC or Cedula in the cached DGII database (one cache.get).

        Returns:
            Dictionary with RNC information if found, None otherwise
            {
                'rnc': str,
                'razon_social': str,
                'actividad_economica': str,
                'fecha_inicio': str,
                'estado': str,  # 'ACTIVO' or 'SUSPENDIDO'
                'regimen_pago': str,
                'is_active': bool,
            }
        """
        if not rnc_or_cedula or not cls._is_valid_format(rnc_or_cedula):
            return None

        rnc_clean = cls._normalize_rnc(rnc_or_cedula)
        record = cache.get(record_key(rnc_clean))
        if not isinstance(record, dict):
            return None

        estado = record.get('estado', '')
        return {
            'rnc': rnc_clean,
            'razon_social': record.get('razon_social', ''),
            'actividad_economica': record.get('actividad_economica', ''),
            'fecha_inicio': record.get('fecha_inicio', ''),
            'estado': estado,
            'regimen_pago': record.get('regimen_pago', ''),
            'is_active': estado.upper() == 'ACTIVO',
        }

    @classmethod
    def validate(cls, rnc_or_cedula: str, allow_scrape: bool) -> Dict:
        """
        Validate an RNC or Cedula and return validation result
        - Layer 1: Format validation (no cache access when invalid)
        - Layer 2: Local database lookup (one cache key)
        - Layer 3: Live DGII scraping if not found, only when ``allow_scrape``

        Returns:
            {
                'is_valid': bool,
                'exists': bool,
                'is_active': bool,
                'data': dict or None,
                'message': str,
                'source': str,  # 'local_db' or 'dgii_scraper'
            }
        """
        if not rnc_or_cedula:
            return {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula es requerido',
                'source': None,
            }

        # Layer 1: format
        if not cls._is_valid_format(rnc_or_cedula):
            return {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'Formato de RNC/Cédula inválido. Debe tener 11 dígitos.',
                'source': None,
            }

        # Layer 2: Lookup in local database
        data = cls.lookup(rnc_or_cedula)

        if data:
            is_active = data['is_active']
            logger.info(f'RNC Validation Layer 2: Found {rnc_or_cedula} in local database')

            return {
                'is_valid': True,
                'exists': True,
                'is_active': is_active,
                'data': {**data, 'source': 'local_db'},
                'message': 'RNC/Cédula encontrado' if is_active else 'RNC/Cédula encontrado pero está SUSPENDIDO',
                'source': 'local_db',
            }

        if not allow_scrape:
            # Las peticiones anónimas nunca disparan una consulta en línea a la DGII.
            return {
                'is_valid': True,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula no encontrado en la base de datos de la DGII',
                'source': None,
            }

        # Layer 3: Not found in local database, try scraping DGII
        logger.info(f'RNC Validation Layer 3: Attempting DGII scraping for {rnc_or_cedula}')

        try:
            scraped_data = scrape_dgii_rnc(cls._normalize_rnc(rnc_or_cedula))

            if scraped_data:
                is_active = scraped_data.get('is_active', False)
                logger.info(f'RNC Validation Layer 3: Successfully scraped {rnc_or_cedula} from DGII')

                # Cache the scraped result for future lookups
                cls._cache_scraped_result(scraped_data)

                return {
                    'is_valid': True,
                    'exists': True,
                    'is_active': is_active,
                    'data': scraped_data,
                    'message': 'RNC/Cédula encontrado en DGII (consulta en línea)' if is_active else 'RNC/Cédula encontrado en DGII pero está SUSPENDIDO',
                    'source': 'dgii_scraper',
                }
            else:
                logger.info(f'RNC Validation Layer 3: {rnc_or_cedula} not found via scraping')

                return {
                    'is_valid': True,  # Format is valid
                    'exists': False,   # But doesn't exist in DGII
                    'is_active': False,
                    'data': None,
                    'message': 'RNC/Cédula no encontrado en DGII',
                    'source': None,
                }

        except Exception as e:
            logger.error(f'RNC Validation Layer 3: Scraping error for {rnc_or_cedula}: {str(e)}')

            return {
                'is_valid': True,  # Format is valid
                'exists': False,   # But couldn't verify with DGII
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula no encontrado en base de datos local. Error al consultar DGII en línea.',
                'source': None,
            }

    @classmethod
    def is_database_loaded(cls) -> bool:
        """True when the per-key registry is loaded (reads only the meta key)."""
        meta = cache.get(META_KEY)
        if isinstance(meta, dict) and 'count' in meta:
            return True
        if meta is not None or cache.has_key(LEGACY_CACHE_KEY):
            logger.warning(
                'RNC database is in the legacy single-key format and is ignored. '
                'Re-run: python manage.py update_rnc_database --force'
            )
        return False

    @classmethod
    def get_database_stats(cls) -> Optional[Dict]:
        """Get statistics about the cached database"""
        meta = cache.get(META_KEY)
        if isinstance(meta, dict) and 'count' in meta:
            return meta
        return None

    @classmethod
    def _cache_scraped_result(cls, scraped_data: Dict) -> None:
        """
        Cache a scraped result under its own key so future lookups hit Layer 2.
        """
        try:
            rnc = scraped_data.get('rnc')
            if not rnc:
                logger.warning('Cannot cache scraped result: no RNC in data')
                return

            # Same shape as the loaders (without the 'source' field)
            cache.set(
                record_key(rnc),
                {
                    'razon_social': scraped_data.get('razon_social', ''),
                    'actividad_economica': scraped_data.get('actividad_economica', ''),
                    'fecha_inicio': scraped_data.get('fecha_inicio', ''),
                    'estado': scraped_data.get('estado', 'DESCONOCIDO'),
                    'regimen_pago': scraped_data.get('regimen_pago', 'DESCONOCIDO'),
                },
                timeout=None,
            )
            logger.info(f'Cached scraped result for RNC {rnc} in local database')

        except Exception as e:
            logger.error(f'Error caching scraped result: {str(e)}', exc_info=True)

    @staticmethod
    def _normalize_rnc(rnc: str) -> str:
        """
        Normalize RNC/Cedula by removing spaces, dashes, and padding with zeros

        Examples:
            '1-23-45678-9' -> '00102345678'
            '123456789' -> '00123456789'
            '12345678901' -> '12345678901'
        """
        clean = re.sub(r'[\s\-]', '', rnc)
        return clean.zfill(11)

    @staticmethod
    def _is_valid_format(rnc: str) -> bool:
        """
        Validate RNC/Cedula format
        Must be 9-11 digits (will be padded to 11)
        """
        clean = re.sub(r'[\s\-]', '', rnc)
        return clean.isdigit() and 9 <= len(clean) <= 11


# Convenience functions for direct use
def lookup_rnc(rnc_or_cedula: str) -> Optional[Dict]:
    """Convenience function to lookup an RNC"""
    return RNCLookupService.lookup(rnc_or_cedula)


def validate_rnc(rnc_or_cedula: str, allow_scrape: bool) -> Dict:
    """Convenience function to validate an RNC"""
    return RNCLookupService.validate(rnc_or_cedula, allow_scrape=allow_scrape)


def is_rnc_database_loaded() -> bool:
    """Convenience function to check if database is loaded"""
    return RNCLookupService.is_database_loaded()
