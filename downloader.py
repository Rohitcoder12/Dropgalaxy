import requests
import time
from bs4 import BeautifulSoup
import re

def get_dropgalaxy_link(url):
    client = requests.Session()
    client.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    try:
        initial_response = client.get(url, timeout=15)
        initial_response.raise_for_status()
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        form_data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input', {'type': 'hidden'})}
        form_data['method_free'] = 'Free Download'
        time.sleep(3)
        second_page_response = client.post(url, data=form_data, timeout=15)
        second_page_response.raise_for_status()
        soup = BeautifulSoup(second_page_response.text, 'html.parser')
        if soup.find('div', class_='g-recaptcha'):
            return None, "CAPTCHA detected. Cannot proceed."
        wait_time = 12
        time.sleep(wait_time)
        form_data_2 = {inp.get('name'): inp.get('value') for inp in soup.find_all('input', {'type': 'hidden'})}
        create_link_button = soup.find('button', {'type': 'submit'})
        if not create_link_button:
            return None, "Could not find 'Create Download Link' button."
        form_data_2[create_link_button.get('name')] = create_link_button.get('value', '')
        final_page_response = client.post(url, data=form_data_2, timeout=15)
        final_page_response.raise_for_status()
        soup = BeautifulSoup(final_page_response.text, 'html.parser')
        download_button = soup.find('a', class_=re.compile(r'btn-primary'))
        if not download_button or not download_button.get('href'):
            return None, "Could not find the final download link."
        final_link = download_button.get('href')
        return final_link, None
    except requests.exceptions.RequestException as e:
        return None, f"A network error occurred: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"