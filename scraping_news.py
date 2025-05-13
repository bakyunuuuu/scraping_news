import requests
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import re
import csv
import os


class BaseCollector:
    def __init__(self, filename):
        self.session = requests.Session()  # 세션 초기화
        self.ua = UserAgent()  # 유저 에이전트 초기화
        self.save_interval = 10  # 몇 개마다 저장할지
        self.request_count = 0  # 요청 횟수 초기화
        self.max_requests_per_session = 30  # 세션당 최대 요청 횟수
        self.session_delay = 60  # 세션 간격
        self.long_delay_interval = 5  # 긴 휴식 간격
        self.long_delay_time = 180  # 긴 휴식 시간
        self.filename = filename

    def _random_delay(self):
        time.sleep(random.uniform(1.0, 3.0))

    def _check_session(self):
        self.request_count += 1
        if self.request_count >= self.max_requests_per_session:
            if self.request_count % (self.max_requests_per_session * self.long_delay_interval) == 0:
                print(f"긴 휴식: {self.long_delay_time}초 대기 중...")
                time.sleep(self.long_delay_time)
            else:
                print(f"짧은 휴식: {self.session_delay}초 대기 중...")
                time.sleep(self.session_delay)
            
            self.session = requests.Session()
            self.request_count = 0
            self._random_delay()

    def set_options(self):
        options = Options()
        options.add_argument(f"user-agent={self.ua.random}")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-notifications')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        return options

    def save_to_csv(self, data, headers, mode='a'):        
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            write_header = mode == 'w' or not os.path.exists(self.filename)
            
            with open(self.filename, mode, newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(headers)
                writer.writerows(data)
            
            print(f"데이터가 {self.filename}에 저장되었습니다.")
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")

class LinkCollector(BaseCollector):
    def __init__(self, filename='news/news_links_2023.csv'):
        super().__init__(filename)
        self.temp_links = []
        self.max_workers = 3  # 동시 처리할 날짜 수

    def get_news_links(self, date):
        print(f"< 날짜: {date} 시작 >")
        options = self.set_options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            URL = "https://news.naver.com/breakingnews/section/101/262?date=" + str(date)
            driver.get(URL)
            self._check_session()
            self._random_delay()

            wait = WebDriverWait(driver, 5)
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._random_delay()
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    try:
                        more_btn = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "_CONTENT_LIST_LOAD_MORE_BUTTON")))
                        if more_btn.is_displayed():
                            more_btn.click()
                            self._random_delay()
                            self._check_session()
                        else:
                            break
                    except:
                        break
                
                last_height = new_height
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            news_links = [(date, a.get("href")) for a in soup.select("a.sa_text_title") if a.get("href")]
            return news_links
            
        finally:
            driver.quit()
            print(f"날짜: {date} 총 링크 개수: {len(news_links)}")

    def add_links(self, new_links):
        self.temp_links.extend(new_links)
        if len(self.temp_links) >= self.save_interval:
            self.save_to_csv(self.temp_links, ['date', 'url'])
            self.temp_links = []

    def collect_links_by_date_range(self, start_date, end_date):
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=1)

        try:
            # 다중 스레드로 링크 수집
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_date = {executor.submit(self.get_news_links, date): date for date in date_list}
                for future in as_completed(future_to_date):
                    date = future_to_date[future]
                    try:
                        links = future.result()
                        self.add_links(links)
                    except Exception as e:
                        print(f"날짜 {date} 처리 중 오류 발생: {e}")

            # 남은 링크 저장
            if self.temp_links:
                self.save_to_csv(self.temp_links, ['date', 'url'])
                
        except KeyboardInterrupt:
            print("\n프로그램이 중단되었습니다. 현재까지 수집된 데이터를 저장합니다...")
            if self.temp_links:
                self.save_to_csv(self.temp_links, ['date', 'url'])
            print("저장이 완료되었습니다. 프로그램을 종료합니다.")
            exit(0)

class ContentCollector(BaseCollector):
    def __init__(self, input_filename='news/news_links_2023.csv', output_filename='news/news_content_2023.csv'):
        super().__init__(output_filename)
        self.input_filename = input_filename
        self.processed_news = []
        self.max_workers = 5  # 동시 처리할 URL 수

    def clean_content(self, content):
        if not content:
            return None
        
        for tag in content.find_all('strong', class_='media_end_summary'):
            tag.decompose()
        
        for tag in content.find_all(['table', 'script', 'style', 'aside', 'footer']):
            tag.decompose()

        paragraphs = [p.get_text(strip=True) for p in content.select("span.article_p")]
        text = '\n'.join(paragraphs)

        text = re.sub(r'([가-힣])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])([가-힣])', r'\1 \2', text)

        return text.strip()

    def get_news(self, url):
        options = self.set_options()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.get(url)
            self._check_session()
            self._random_delay()

            soup = BeautifulSoup(driver.page_source, "html.parser")
            title = soup.select_one("h2.media_end_head_headline") or soup.select_one("h3.media_end_head_headline")
            content = soup.select_one("div#newsct_article")
            content_clean = self.clean_content(content)

            if title and content_clean:
                return {
                    'title': title.get_text(strip=True),
                    'content': content_clean
                }
            return None

        except Exception as e:
            print(f"오류 발생: {e}")
            return None
        finally:
            driver.quit()

    def process_single_news(self, row):  # 단일 뉴스 처리
        date, url = row
        print(f"처리 중: {url}")
        
        news_data = self.get_news(url)
        if news_data:
            return [date, url, news_data['title'], news_data['content']]
        return [date, url, '', '']

    def process_news_content(self):
        try:
            # URL 목록 읽기
            with open(self.input_filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 헤더 건너뛰기
                rows = list(reader)

            # 다중 스레드로 처리
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_url = {executor.submit(self.process_single_news, row): row for row in rows}
                
                for future in as_completed(future_to_url):
                    try:
                        result = future.result()
                        self.processed_news.append(result)
                        
                        # 중간 저장
                        if len(self.processed_news) >= self.save_interval:
                            self.save_to_csv(self.processed_news, ['date', 'url', 'title', 'content'])
                            self.processed_news = []
                            
                    except Exception as e:
                        print(f"URL 처리 중 오류 발생: {e}")

            # 남은 데이터 저장
            if self.processed_news:
                self.save_to_csv(self.processed_news, ['date', 'url', 'title', 'content'])
                
        except Exception as e:
            print(f"본문 처리 중 오류 발생: {e}")
            if self.processed_news:
                self.save_to_csv(self.processed_news, ['date', 'url', 'title', 'content'])

if __name__ == "__main__":
    # 링크 수집
    # link_collector = LinkCollector('news/news_links_2023.csv')
    # start_date = datetime(2023, 1, 1)
    # end_date = datetime(2023, 12, 31)
    # link_collector.collect_links_by_date_range(start_date, end_date)
    
    # 본문 수집
    content_collector = ContentCollector(
        input_filename='news/news_links_2023.csv',
        output_filename='news/news_content_2023.csv'
    )
    content_collector.process_news_content()

    

 

