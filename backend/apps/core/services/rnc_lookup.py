# -*- coding: utf-8 -*-
"""
RNC Lookup Service
Provides fast RNC/Cedula validation and information lookup using cached DGII data

3-Layer Validation Architecture:
- Layer 1: Format validation (Luhn algorithm via frontend)
- Layer 2: Local DGII database lookup (cached data)
- Layer 3: Live DGII website scraping (when not found in cache)
"""
import json
import re
import logging
from typing import Optional, Dict
from django.core.cache import cache
from .dgii_scraper import scrape_dgii_rnc

logger = logging.getLogger(__name__)


class RNCLookupService:
    """Service for looking up RNC/Cedula information from DGII cached database"""

    CACHE_KEY = 'dgii_rnc_database'

    @classmethod
    def lookup(cls, rnc_or_cedula: str) -> Optional[Dict]:
        """
        Look up an RNC or Cedula in the cached DGII database

        Args:
            rnc_or_cedula: RNC or Cedula number to look up

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
        if not rnc_or_cedula:
            return None

        # Clean and normalize the input
        rnc_clean = cls._normalize_rnc(rnc_or_cedula)

        # Get cached database
        rnc_database_json = cache.get(cls.CACHE_KEY)

        if not rnc_database_json:
            # Database not loaded yet
            return None

        # Parse JSON (cache stores as JSON string to save memory)
        try:
            rnc_database = json.loads(rnc_database_json)
        except (json.JSONDecodeError, TypeError):
            return None

        # Lookup the RNC
        if rnc_clean in rnc_database:
            record = rnc_database[rnc_clean]

            # Add the RNC number and active status to the result
            return {
                'rnc': rnc_clean,
                'razon_social': record['razon_social'],
                'actividad_economica': record['actividad_economica'],
                'fecha_inicio': record['fecha_inicio'],
                'estado': record['estado'],
                'regimen_pago': record['regimen_pago'],
                'is_active': record['estado'].upper() == 'ACTIVO',
            }

        return None

    @classmethod
    def validate(cls, rnc_or_cedula: str) -> Dict:
        """
        Validate an RNC or Cedula and return validation result
        Uses 3-layer architecture:
        - Layer 1: Format validation (frontend Luhn)
        - Layer 2: Local database lookup
        - Layer 3: Live DGII scraping if not found

        Args:
            rnc_or_cedula: RNC or Cedula number to validate

        Returns:
            Dictionary with validation results:
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

        # Check format
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
            # Found in local database
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

        # Layer 3: Not found in local database, try scraping DGII
        logger.info(f'RNC Validation Layer 3: Attempting DGII scraping for {rnc_or_cedula}')

        try:
            scraped_data = scrape_dgii_rnc(cls._normalize_rnc(rnc_or_cedula))

            if scraped_data:
                # Successfully scraped from DGII
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
                # Not found even via scraping
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
            # Scraping failed, return not found
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
        """Check if the RNC database is loaded in cache"""
        return cache.get(cls.CACHE_KEY) is not None

    @classmethod
    def get_database_stats(cls) -> Optional[Dict]:
        """Get statistics about the cached database"""
        meta = cache.get(f'{cls.CACHE_KEY}_meta')
        return meta

    @classmethod
    def _cache_scraped_result(cls, scraped_data: Dict) -> None:
        """
        Cache a scraped result in the local database
        This allows future lookups to use Layer 2 instead of Layer 3

        Args:
            scraped_data: Dictionary with scraped RNC data
        """
        try:
            # Get existing database
            rnc_database_json = cache.get(cls.CACHE_KEY)

            if not rnc_database_json:
                logger.warning('Cannot cache scraped result: database not loaded')
                return

            # Parse JSON
            rnc_database = json.loads(rnc_database_json)

            # Extract RNC and prepare cache entry
            rnc = scraped_data.get('rnc')
            if not rnc:
                logger.warning('Cannot cache scraped result: no RNC in data')
                return

            # Add to database (without the 'source' field to match local DB format)
            cache_entry = {
                'razon_social': scraped_data.get('razon_social', ''),
                'actividad_economica': scraped_data.get('actividad_economica', ''),
                'fecha_inicio': scraped_data.get('fecha_inicio', ''),
                'estado': scraped_data.get('estado', 'DESCONOCIDO'),
                'regimen_pago': scraped_data.get('regimen_pago', 'DESCONOCIDO'),
            }

            rnc_database[rnc] = cache_entry

            # Update cache with new entry
            cache.set(cls.CACHE_KEY, json.dumps(rnc_database), timeout=None)

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
        # Remove spaces and dashes
        clean = re.sub(r'[\s\-]', '', rnc)

        # Pad with zeros to 11 digits
        return clean.zfill(11)

    @staticmethod
    def _is_valid_format(rnc: str) -> bool:
        """
        Validate RNC/Cedula format
        Must be 9-11 digits (will be padded to 11)
        """
        # Remove spaces and dashes
        clean = re.sub(r'[\s\-]', '', rnc)

        # Check if it's numeric and has valid length
        return clean.isdigit() and 9 <= len(clean) <= 11


# Convenience functions for direct use
def lookup_rnc(rnc_or_cedula: str) -> Optional[Dict]:
    """Convenience function to lookup an RNC"""
    return RNCLookupService.lookup(rnc_or_cedula)


def validate_rnc(rnc_or_cedula: str) -> Dict:
    """Convenience function to validate an RNC"""
    return RNCLookupService.validate(rnc_or_cedula)


def is_rnc_database_loaded() -> bool:
    """Convenience function to check if database is loaded"""
    return RNCLookupService.is_database_loaded()
