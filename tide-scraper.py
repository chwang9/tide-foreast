#!/usr/bin/python
"""
Tide Forecast Scraper

Scrapes the daytime low-tides from www.tide-forecast.com and reports
them in a parseable format.
"""

import datetime
import json
import re
import sys
import time

import requests
from lxml import html


class TideForecastPage:
    """
    A tide forecast scraper
    """
    TIDE_FORECAST_BY_LOCATION = 'https://www.tide-forecast.com/locations'
    ALL_DAYS = 'tides/latest'
    TIDE_TABLE = '//table[contains(@class, "tide-day-tides")]'
    LOW_TIDES_KEY = 'low-tides'

    def scrape_low_tides(self, locations):
        """
        Scrapes "useful" low-tide times(during the day) for a set of locations
        """
        location_map = dict()
        for location_name in locations:
            if location_name:
                location = self._normalize_location_name(location_name)
                location_map[location] = self._scrape_location(location)
        return location_map

    @staticmethod
    def _read(url):
        """
        Request a page and parse it into an lxml tree
        """
        session = requests.Session()
        session.trust_env = False
        session.verify = False
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            print(f"Fetching URL: {url}")
            page = session.get(url, headers=headers, timeout=30)
            page.raise_for_status()
            
            content = page.content.decode('utf-8', errors='ignore')
            print(f"Response length: {len(content)} characters")
            print(f"Response preview: {content[:200]}...")
            
            return html.fromstring(page.content)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            raise

    def _scrape_location(self, location):
        """
        Scrapes a single location for a number of data points for all days available on the page
        """
        try:
            location_page = self._read(
                '/'.join((self.TIDE_FORECAST_BY_LOCATION, location, self.ALL_DAYS))
            )
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {location}: {e}")
            return {}
        
        print(f"Searching for tide tables with XPath: {self.TIDE_TABLE}")
        tide_tables = location_page.xpath(self.TIDE_TABLE)
        print(f"Found {len(tide_tables)} tide table(s)")
        
        result = dict()
        if tide_tables:
            low_tides = {}
            for table in tide_tables:
                day_low_tides = self._parse_daylight_low_tide(table)
                low_tides.update(day_low_tides)
            
            if low_tides:
                result[self.LOW_TIDES_KEY] = low_tides
            else:
                print(f"No low tides found for location: {location}")
        else:
            print(f"No tide table found for location: {location}")

        return result

    @staticmethod
    def _parse_daylight_low_tide(table, max_days=None):
        """
        Parse the tide table into a set of time's mapped to tide height ( excluding
        times after sunset and before sunrise
        """

        low_tides = dict()
        
        print(f"Processing table with {len(table.xpath('.//tr'))} rows")
        
        for tr in table.xpath('.//tr'):
            fields = tr.xpath('.//td')
            
            if not fields or len(fields) < 3:
                continue
                
            first_cell = fields[0].text_content().strip()
            print(f"Row first cell: '{first_cell}', fields count: {len(fields)}")
            
            if 'Low Tide' in first_cell:
                print(f"Found Low Tide row with {len(fields)} fields")
                for i, field in enumerate(fields):
                    content = field.text_content().strip()
                    print(f"  Field {i}: '{content}'")
                
                if len(fields) >= 3:
                    time_field = fields[1].text_content().strip()
                    height_field = fields[2].text_content().strip()
                    print(f"  Extracted: time='{time_field}', height='{height_field}'")
                    if time_field:
                        low_tides[time_field] = height_field
                        
        print(f"Total low tides found: {len(low_tides)}")
        return low_tides

    @staticmethod
    def _normalize_location_name(location):
        """
        Returns the location name as-is, since input is already in the correct format.
        """
        return location.strip()


def main(*args):
    """
    Read the tide forecast page, parse, query based on input, return results.
    """
    input_filename = args[1]
    tide_forecast_page = TideForecastPage()
    results = tide_forecast_page.scrape_low_tides(
        locations=[line.strip() for line in open(input_filename)]
    )

    with open(datetime.datetime.now().date().isoformat(), 'w') as outfile:
        json.dump(results, outfile, indent=4)
    print(json.dumps(results, indent=4))

if __name__ == '__main__':
    main(*sys.argv)
