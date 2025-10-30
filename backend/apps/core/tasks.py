# -*- coding: utf-8 -*-
"""
Celery tasks for core app
"""
import csv
import requests
import zipfile
import json
from io import BytesIO
from celery import shared_task
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def update_rnc_database(self):
    """
    Celery task to download and update the DGII RNC database in Redis cache

    This task:
    1. Downloads the latest RNC CSV file from DGII
    2. Parses and processes the data
    3. Stores it in Redis for fast lookups
    4. Updates metadata (last updated timestamp, record count, etc.)

    Scheduled to run weekly via Celery Beat
    """
    logger.info("Starting RNC database update task")

    try:
        # Download and parse the RNC file
        rnc_data = _download_and_parse_rnc_file()

        # Load into Redis cache
        _load_to_cache(rnc_data)

        logger.info(f"Successfully updated RNC database with {len(rnc_data):,} records")

        return {
            'status': 'success',
            'total_records': len(rnc_data),
            'message': f'RNC database updated successfully with {len(rnc_data):,} records'
        }

    except requests.RequestException as e:
        logger.error(f"Network error downloading RNC file: {str(e)}")
        # Retry on network errors
        raise self.retry(exc=e)

    except Exception as e:
        logger.error(f"Error updating RNC database: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


def _download_and_parse_rnc_file():
    """Download and parse the RNC CSV file from DGII"""
    # DGII official bulk download URL
    DGII_CSV_URL = "https://dgii.gov.do/app/WebApps/Consultas/RNC/RNC_CONTRIBUYENTES.zip"

    logger.info(f"Downloading RNC file from {DGII_CSV_URL}")

    # Download with browser headers to avoid 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(DGII_CSV_URL, headers=headers, timeout=180)
    response.raise_for_status()

    logger.info(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

    # Extract and parse ZIP file
    rnc_data = {}

    with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
        # Get the CSV file name (should be only one file in the ZIP)
        csv_filename = zip_file.namelist()[0]
        logger.info(f"Extracting file: {csv_filename}")

        # Read and parse CSV
        with zip_file.open(csv_filename) as csv_file:
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
                    logger.info(f"Processed {count:,} records...")

            logger.info(f"Parsed {count:,} total records")

    return rnc_data


def _load_to_cache(rnc_data):
    """Load the RNC data into Redis cache"""
    CACHE_KEY = 'dgii_rnc_database'
    CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days

    logger.info('Loading data into Redis cache...')

    # Store as JSON string to save memory
    cache.set(
        CACHE_KEY,
        json.dumps(rnc_data),
        timeout=CACHE_TIMEOUT
    )

    # Also store metadata
    from datetime import datetime
    cache.set(
        f'{CACHE_KEY}_meta',
        {
            'total_records': len(rnc_data),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        timeout=CACHE_TIMEOUT
    )

    logger.info(f'Successfully cached {len(rnc_data):,} records')


@shared_task
def test_celery():
    """Simple test task to verify Celery is working"""
    logger.info("Test Celery task executed successfully")
    return "Celery is working!"
