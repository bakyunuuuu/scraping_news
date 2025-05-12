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


class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.save_interval = 10  # 며칠마다 저장할지
        self.temp_links = []  # 임시 저장용 링크 리스트
        self.request_count = 0  # 요청 횟수 카운터
        self.max_requests_per_session = 30  # 세션당 최대 요청 수
        self.session_delay = 60  # 세션 재시작 시 대기 시간(초)
        self.long_delay_interval = 5  # 몇 번의 세션마다 긴 대기 시간을 가질지
        self.long_delay_time = 180  # 긴 대기 시간(초)
    
    def _random_delay(self):  # random delay
        time.sleep(random.uniform(1.0, 2.0))  # 대기 시간
    
    def _check_session(self):
        self.request_count += 1
        if self.request_count >= self.max_requests_per_session:
            # 긴 대기 시간이 필요한 경우
            if self.request_count % (self.max_requests_per_session * self.long_delay_interval) == 0:
                print(f"긴 휴식: {self.long_delay_time}초 대기 중...")
                time.sleep(self.long_delay_time)
            else:
                print(f"짧은 휴식: {self.session_delay}초 대기 중...")
                time.sleep(self.session_delay)
            
            self.session = requests.Session()  # 새로운 세션 생성
            self.request_count = 0
            self._random_delay()  # 추가 딜레이

    def save_links_to_csv(self, links, filename='news/news_links_2023.csv', mode='a'):  # csv 파일 저장
        import csv
        import os
        
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 파일이 없거나 'w' 모드일 때는 헤더 추가
        write_header = mode == 'w' or not os.path.exists(filename)
        
        with open(filename, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['date', 'url'])
            for date, url in links:
                writer.writerow([date, url])
        
        print(f"{len(links)}개의 링크가 {filename}에 저장되었습니다.")
    
    def add_links(self, new_links):  # 새로운 링크 추가 및 저장
        self.temp_links.extend(new_links)
        
        if len(self.temp_links) >= self.save_interval:
            self.save_links_to_csv(self.temp_links)
            self.temp_links = []  # 임시 리스트 초기화

    def get_news_links(self, date):  # 뉴스 링크 크롤링
        print(f"< 날짜: {date} 시작 >")
        options = Options()
        options.add_argument(f"user-agent={self.ua.random}")
        # 자동화 감지 방지
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  
        options.add_experimental_option('useAutomationExtension', False)
        
        # 추가적인 자동화 감지 방지
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-notifications')
        
        # 헤드리스 모드 추가
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=options)
        
        try:
            URL = "https://news.naver.com/breakingnews/section/101/262?date=" + str(date)
            driver.get(URL)
            self._check_session()  # 세션 체크

            self._random_delay()

            wait = WebDriverWait(driver, 5)
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:  # 더보기 버튼 찾기
                # 일반 스크롤 사용 (부드러운 스크롤 대신)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._random_delay()
                
                # 새로운 높이 계산
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # 스크롤이 실제로 내려갔는지 확인
                if new_height == last_height:
                    try:
                        more_btn = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "_CONTENT_LIST_LOAD_MORE_BUTTON")))
                        if more_btn.is_displayed():
                            more_btn.click()
                            # print("더보기 버튼 클릭")
                            self._random_delay()
                            self._check_session()  # 세션 체크
                        else:
                            break
                    except:
                        # print("더보기 버튼 X")
                        break
                
                last_height = new_height
            
            soup = BeautifulSoup(driver.page_source, "html.parser")

            news_links = []
            for a in soup.select("a.sa_text_title"):
                href = a.get("href")
                if href:
                    news_links.append((date, href)) 
            
            return news_links
            
        finally:
            driver.quit()
            print(f"날짜: {date} 총 링크 개수: {len(news_links)}")
        
    # [TODO] 실제 뉴스 본문, 제목 등 파싱하는 함수는 아래에 새로 만들어야 함
    def get_news(self, url):
        # 01. Selenium이나 requests로 url 접속
        # 02. BeautifulSoup으로 html 파싱
        # 03. 제목, 본문 등 필요한 정보 추출
        # 04. dict 등으로 반환
        pass


if __name__ == "__main__":
    scraper = NewsScraper()

    # 날짜 지정 
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)

    # 날짜 리스트 생성
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)

    try:
        # 다중 스레드로 크롤링
        with ThreadPoolExecutor(max_workers=3) as executor:  # 동시에 3개의 날짜 처리
            future_to_date = {executor.submit(scraper.get_news_links, date): date for date in date_list}
            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    links = future.result()
                    scraper.add_links(links)  # 중간 저장 기능 사용
                except Exception as e:
                    print(f"날짜 {date} 처리 중 오류 발생: {e}")

        # 남은 링크 저장
        if scraper.temp_links:
            scraper.save_links_to_csv(scraper.temp_links)
            
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다. 현재까지 수집된 데이터를 저장합니다...")
        if scraper.temp_links:
            scraper.save_links_to_csv(scraper.temp_links)
        print("저장이 완료되었습니다. 프로그램을 종료합니다.")
        exit(0)

    print("크롤링 완료")

    # 저장된 링크를 불러와서 get_news(url)로 본문 등 크롤링
    # for date, url in all_links:
    #     news_data = scraper.get_news(url)
    #     # 결과 저장

 

