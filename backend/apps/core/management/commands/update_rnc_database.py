# -*- coding: utf-8 -*-
"""
Management command to download and cache DGII RNC database
"""
import csv
import requests
import zipfile
import tempfile
import json
from pathlib import Path
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings


class Command(BaseCommand):
    help = 'Download and cache the DGII RNC database for fast lookups'

    # DGII official bulk download URL (updated as of Oct 2025)
    DGII_CSV_URL = "https://dgii.gov.do/app/WebApps/Consultas/RNC/RNC_CONTRIBUYENTES.zip"

    # Redis cache key for the RNC database
    CACHE_KEY = 'dgii_rnc_database'

    # Cache timeout: 7 days (will be refreshed by Celery task)
    CACHE_TIMEOUT = 60 * 60 * 24 * 7

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force download even if cache exists',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)

        # Check if database already exists in cache
        if not force and cache.get(self.CACHE_KEY):
            self.stdout.write(
                self.style.WARNING('RNC database already in cache. Use --force to refresh.')
            )
            # Show some stats
            self._show_stats()
            return

        self.stdout.write('Downloading DGII RNC database...')

        try:
            # Download the ZIP file
            rnc_data = self._download_rnc_file()

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

    def _download_rnc_file(self):
        """Download and extract the RNC CSV file from DGII"""
        self.stdout.write(f'Downloading from {self.DGII_CSV_URL}...')

        # Download with browser headers to avoid 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(self.DGII_CSV_URL, headers=headers, timeout=120)
        response.raise_for_status()

        self.stdout.write(f'Downloaded {len(response.content) / 1024 / 1024:.1f} MB')

        # Extract ZIP file
        self.stdout.write('Extracting ZIP file...')
        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
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
        """Load the RNC data into Redis cache"""
        self.stdout.write('Loading data into Redis cache...')

        # Store as JSON string to save memory
        cache.set(
            self.CACHE_KEY,
            json.dumps(rnc_data),
            timeout=self.CACHE_TIMEOUT
        )

        # Also store metadata
        cache.set(
            f'{self.CACHE_KEY}_meta',
            {
                'total_records': len(rnc_data),
                'last_updated': self._get_current_timestamp(),
            },
            timeout=self.CACHE_TIMEOUT
        )

    def _show_stats(self):
        """Show statistics about the cached database"""
        meta = cache.get(f'{self.CACHE_KEY}_meta')

        if meta:
            self.stdout.write('\n' + '='*60)
            self.stdout.write('RNC Database Statistics:')
            self.stdout.write('='*60)
            self.stdout.write(f'Total records: {meta["total_records"]:,}')
            self.stdout.write(f'Last updated: {meta["last_updated"]}')
            self.stdout.write('='*60 + '\n')

    def _get_current_timestamp(self):
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
