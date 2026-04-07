"""
DGII Web Scraper - Layer 3 Validation
Scrapes DGII website for RNC/Cédula validation when not found in local database
"""
import requests
import logging
from bs4 import BeautifulSoup
from typing import Optional, Dict
import time

logger = logging.getLogger(__name__)


class DGIIScraper:
    """
    Scraper for DGII website to validate RNC/Cédula
    """

    # DGII consultation URL
    DGII_URL = "https://dgii.gov.do/app/WebApps/ConsultasWeb/consultas/rnc.aspx"

    # Headers to mimic browser request
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Timeout for requests (seconds)
    TIMEOUT = 10

    @classmethod
    def scrape_rnc(cls, rnc: str) -> Optional[Dict]:
        """
        Scrape DGII website for RNC/Cédula information

        Args:
            rnc: RNC or Cédula to validate (cleaned, no dashes)

        Returns:
            Dictionary with taxpayer information or None if not found
        """
        try:
            logger.info(f'DGII Scraper: Attempting to scrape RNC/Cédula {rnc}')

            # Prepare request
            session = requests.Session()

            # First, get the page to obtain any necessary tokens/viewstate
            initial_response = session.get(
                cls.DGII_URL,
                headers=cls.HEADERS,
                timeout=cls.TIMEOUT
            )

            if initial_response.status_code != 200:
                logger.error(f'DGII Scraper: Failed to load page, status {initial_response.status_code}')
                return None

            # Parse the initial page to get form tokens
            soup = BeautifulSoup(initial_response.text, 'html.parser')

            # Get ASP.NET form tokens (ViewState, EventValidation, etc.)
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            viewstate_value = viewstate['value'] if viewstate else ''

            event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
            event_validation_value = event_validation['value'] if event_validation else ''

            viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
            viewstate_generator_value = viewstate_generator['value'] if viewstate_generator else ''

            # Prepare POST data for RNC query
            post_data = {
                '__VIEWSTATE': viewstate_value,
                '__VIEWSTATEGENERATOR': viewstate_generator_value,
                '__EVENTVALIDATION': event_validation_value,
                'ctl00$cphMain$txtRNCCedula': rnc,
                'ctl00$cphMain$btnBuscarPorRNC': 'Buscar',
            }

            # Submit the form
            response = session.post(
                cls.DGII_URL,
                data=post_data,
                headers=cls.HEADERS,
                timeout=cls.TIMEOUT
            )

            if response.status_code != 200:
                logger.error(f'DGII Scraper: Query failed, status {response.status_code}')
                return None

            # Parse the response
            result = cls._parse_dgii_response(response.text, rnc)

            if result:
                logger.info(f'DGII Scraper: Successfully scraped data for {rnc}')
            else:
                logger.info(f'DGII Scraper: No data found for {rnc}')

            return result

        except requests.Timeout:
            logger.error(f'DGII Scraper: Timeout while scraping {rnc}')
            return None
        except requests.RequestException as e:
            logger.error(f'DGII Scraper: Request error for {rnc}: {str(e)}')
            return None
        except Exception as e:
            logger.error(f'DGII Scraper: Unexpected error scraping {rnc}: {str(e)}', exc_info=True)
            return None

    @classmethod
    def _parse_dgii_response(cls, html: str, rnc: str) -> Optional[Dict]:
        """
        Parse DGII HTML response to extract taxpayer information

        Args:
            html: HTML response from DGII
            rnc: Original RNC queried

        Returns:
            Dictionary with taxpayer data or None if not found
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Look for the results table or error message
            # DGII typically shows results in a table or displays "No encontrado"

            # Check for "no encontrado" or similar error messages
            error_indicators = [
                'no se encontró',
                'no encontrado',
                'no existe',
                'no registrado',
            ]

            page_text = soup.get_text().lower()
            if any(error in page_text for error in error_indicators):
                logger.info(f'DGII Scraper: RNC {rnc} not found on DGII website')
                return None

            # Try to find the data table
            # DGII uses various table structures, we'll try common ones
            data = {}

            # Method 1: Look for labeled fields in spans/labels
            fields_map = {
                'razón social': 'razon_social',
                'razon social': 'razon_social',
                'nombre': 'razon_social',
                'actividad económica': 'actividad_economica',
                'actividad economica': 'actividad_economica',
                'estado': 'estado',
                'régimen de pago': 'regimen_pago',
                'regimen de pago': 'regimen_pago',
            }

            # Try to extract data from table rows
            for row in soup.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    for key, field in fields_map.items():
                        if key in label:
                            data[field] = value
                            break

            # Method 2: Look for specific span/label IDs (DGII specific)
            label_ids = {
                'lblRazonSocial': 'razon_social',
                'lblNombre': 'razon_social',
                'lblActividadEconomica': 'actividad_economica',
                'lblEstado': 'estado',
                'lblRegimen': 'regimen_pago',
            }

            for label_id, field in label_ids.items():
                element = soup.find(id=lambda x: x and label_id.lower() in x.lower())
                if element:
                    data[field] = element.get_text(strip=True)

            # If we found at least razon_social (name), consider it successful
            if data.get('razon_social'):
                # Determine if active
                estado = data.get('estado', '').upper()
                is_active = 'ACTIVO' in estado

                result = {
                    'rnc': rnc,
                    'razon_social': data.get('razon_social', ''),
                    'actividad_economica': data.get('actividad_economica', ''),
                    'fecha_inicio': '',  # Usually not available via scraping
                    'estado': data.get('estado', 'DESCONOCIDO'),
                    'regimen_pago': data.get('regimen_pago', 'DESCONOCIDO'),
                    'is_active': is_active,
                    'source': 'dgii_scraper',  # Mark as scraped data
                }

                logger.info(f'DGII Scraper: Extracted data for {rnc}: {result["razon_social"]}')
                return result

            # If no data found, return None
            logger.warning(f'DGII Scraper: Could not extract data from response for {rnc}')
            return None

        except Exception as e:
            logger.error(f'DGII Scraper: Error parsing response for {rnc}: {str(e)}', exc_info=True)
            return None


def scrape_dgii_rnc(rnc: str) -> Optional[Dict]:
    """
    Convenience function to scrape DGII for RNC/Cédula

    Args:
        rnc: RNC or Cédula to validate (cleaned)

    Returns:
        Dictionary with taxpayer information or None
    """
    return DGIIScraper.scrape_rnc(rnc)
