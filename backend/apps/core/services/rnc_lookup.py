# -*- coding: utf-8 -*-
"""
RNC Lookup Service
Provides fast RNC/Cedula validation and information lookup using cached DGII data
"""
import json
import re
from typing import Optional, Dict
from django.core.cache import cache


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
            }
        """
        if not rnc_or_cedula:
            return {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula es requerido',
            }

        # Check format
        if not cls._is_valid_format(rnc_or_cedula):
            return {
                'is_valid': False,
                'exists': False,
                'is_active': False,
                'data': None,
                'message': 'Formato de RNC/Cédula inválido. Debe tener 11 dígitos.',
            }

        # Lookup in database
        data = cls.lookup(rnc_or_cedula)

        if not data:
            return {
                'is_valid': True,  # Format is valid
                'exists': False,   # But doesn't exist in DGII
                'is_active': False,
                'data': None,
                'message': 'RNC/Cédula no encontrado en base de datos DGII',
            }

        # Found in database
        is_active = data['is_active']

        return {
            'is_valid': True,
            'exists': True,
            'is_active': is_active,
            'data': data,
            'message': 'RNC/Cédula encontrado' if is_active else 'RNC/Cédula encontrado pero está SUSPENDIDO',
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
