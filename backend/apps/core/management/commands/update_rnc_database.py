# -*- coding: utf-8 -*-
"""
Management command to download and cache DGII RNC database
"""
import csv
import requests
import zipfile
from io import BytesIO
from urllib.parse import urlsplit
from django.core.management.base import BaseCommand
from constance import config as constance_config

from apps.core.services.rnc_lookup import RNCLookupService, store_rnc_records

# Únicos hosts desde los que se descarga el padrón de la DGII. La URL vive en
# Constance (editable desde el admin), así que se valida antes de cualquier red.
ALLOWED_RNC_HOSTS = {'dgii.gov.do', 'www.dgii.gov.do'}

_HEADERS = {
    # Cabeceras de navegador para evitar el 403 de la DGII
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


def _validate_rnc_url(url):
    """`ValueError` si la URL no es https en un host de ALLOWED_RNC_HOSTS."""
    try:
        parts = urlsplit(url or '')
        port = parts.port
    except ValueError:
        raise ValueError('URL de descarga del RNC no permitida')
    if (
        parts.scheme != 'https'
        or '@' in parts.netloc
        or (parts.hostname or '') not in ALLOWED_RNC_HOSTS
        or port not in (None, 443)
    ):
        raise ValueError('URL de descarga del RNC no permitida')


def _download_rnc_file(url, timeout=120):
    """Descarga el ZIP del RNC desde un host de la DGII y devuelve sus bytes.

    No sigue redirecciones: una 3xx podría llevar fuera de la lista permitida.
    """
    _validate_rnc_url(url)
    response = requests.get(
        url, headers=_HEADERS, stream=True, timeout=timeout, allow_redirects=False,
    )
    try:
        if 300 <= response.status_code < 400:
            raise ValueError('La descarga del RNC devolvió una redirección; no se sigue')
        response.raise_for_status()
        return response.content
    finally:
        response.close()


class Command(BaseCommand):
    help = 'Download and cache the DGII RNC database for fast lookups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force download even if cache exists',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)

        # Check if RNC feature is enabled
        if not constance_config.DGII_RNC_ENABLED:
            self.stdout.write(
                self.style.WARNING(
                    'DGII RNC validation is disabled. '
                    'Enable it in Admin > Configuration > DGII/RNC Database'
                )
            )
            return

        # Check if database already exists in cache
        if not force and RNCLookupService.is_database_loaded():
            self.stdout.write(
                self.style.WARNING('RNC database already in cache. Use --force to refresh.')
            )
            # Show some stats
            self._show_stats()
            return

        self.stdout.write('Downloading DGII RNC database...')
        self.stdout.write(f'Using URL: {constance_config.DGII_RNC_DATABASE_URL}')

        try:
            # Download the ZIP file
            rnc_data = self._download_and_parse()

            # Parse and load into cache
            self._load_to_cache(rnc_data)

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully loaded {len(rnc_data):,} RNC records into cache'
                )
            )

            # Show stats
            self._show_stats()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating RNC database: {str(e)}')
            )
            raise

    def _download_and_parse(self):
        """Download and extract the RNC CSV file from DGII"""
        content = _download_rnc_file(constance_config.DGII_RNC_DATABASE_URL, timeout=120)

        self.stdout.write(f'Downloaded {len(content) / 1024 / 1024:.1f} MB')

        # Extract ZIP file
        self.stdout.write('Extracting ZIP file...')
        with zipfile.ZipFile(BytesIO(content)) as zip_file:
            # Get the CSV file name (should be only one file in the ZIP)
            csv_filename = zip_file.namelist()[0]
            self.stdout.write(f'Found file: {csv_filename}')

            # Read and parse CSV
            with zip_file.open(csv_filename) as csv_file:
                return self._parse_csv(csv_file)

    def _parse_csv(self, csv_file):
        """Parse the CSV file and return a dictionary of RNC records"""
        self.stdout.write('Parsing CSV file...')

        rnc_data = {}

        # Read CSV with Latin-1 encoding (used by DGII)
        csv_content = csv_file.read().decode('latin-1')
        reader = csv.DictReader(csv_content.splitlines())

        count = 0
        for row in reader:
            rnc = row['RNC'].strip()

            # Store record data
            rnc_data[rnc] = {
                'razon_social': row['RAZÓN SOCIAL'].strip(),
                'actividad_economica': row['ACTIVIDAD ECONÓMICA'].strip(),
                'fecha_inicio': row['FECHA DE INICIO OPERACIONES'].strip(),
                'estado': row['ESTADO'].strip(),
                'regimen_pago': row['RÉGIMEN DE PAGO'].strip(),
            }

            count += 1
            if count % 100000 == 0:
                self.stdout.write(f'  Processed {count:,} records...')

        self.stdout.write(f'Parsed {count:,} total records')
        return rnc_data

    def _load_to_cache(self, rnc_data):
        """Load the RNC data into the cache, one key per RNC"""
        self.stdout.write('Loading data into Redis cache...')

        # Get cache timeout from configuration (convert days to seconds)
        cache_timeout = constance_config.DGII_RNC_CACHE_TIMEOUT_DAYS * 24 * 60 * 60
        store_rnc_records(rnc_data, source='update_rnc_database', timeout=cache_timeout)

    def _show_stats(self):
        """Show statistics about the cached database"""
        meta = RNCLookupService.get_database_stats()

        if meta:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('RNC Database Statistics:')
            self.stdout.write('='*60)
            self.stdout.write(f'Total records: {meta["count"]:,}')
            self.stdout.write(f'Last updated: {meta["loaded_at"]}')
            self.stdout.write(f'Source: {meta.get("source", "N/A")}')
            self.stdout.write(f'Cache timeout: {constance_config.DGII_RNC_CACHE_TIMEOUT_DAYS} days')

            auto_update = constance_config.DGII_RNC_AUTO_UPDATE
            self.stdout.write(f'Auto-update: {"Enabled" if auto_update else "Disabled"}')
            if auto_update:
                self.stdout.write(f'Update hour: {constance_config.DGII_RNC_UPDATE_HOUR}:00 UTC')

            self.stdout.write('='*60 + '\n')
