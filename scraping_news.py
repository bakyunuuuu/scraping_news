import requests
import time
import random
from dotenv import load_dotenv
import os
import pandas as pd
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

# .env 파일에서 환경 변수 로드
load_dotenv()

class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
    
    def _random_delay(self):  # random delay
        time.sleep(random.uniform(0.8, 1.5))
    
    def get_news_links(self, date):
        print(f"< 날짜: {date} 시작 >")
        options = Options()
        options.add_argument(f"user-agent={self.ua.random}")
        # 자동화 감지 방지
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=options)
        
        URL = "https://news.naver.com/breakingnews/section/101/262?date=" + str(date)
        driver.get(URL)

        self._random_delay()

        wait = WebDriverWait(driver, 5)
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:  # 더보기 버튼 찾기
            self._random_delay()
            # 스크롤을 부드럽게 내리기
            driver.execute_script("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            self._random_delay()
            
            # 새로운 높이 계산
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 스크롤이 실제로 내려갔는지 확인
            if new_height == last_height:
                try:
                    more_btn = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "_CONTENT_LIST_LOAD_MORE_BUTTON")))
                    if more_btn.is_displayed():
                        more_btn.click()
                        print("더보기 버튼 클릭")
                        self._random_delay()
                    else:
                        break
                except:
                    print("더보기 버튼 X")
                    break
            
            last_height = new_height
        
        soup = BeautifulSoup(driver.page_source, "html.parser")

        news_links = []
        for a in soup.select("a.sa_text_title"):
            href = a.get("href")
            if href:
                news_links.append((date, href)) 
        
        driver.quit()
        print(f"날짜: {date} 총 링크 개수: {len(news_links)}")
        return news_links
        
    # [TODO] 실제 뉴스 본문, 제목 등 파싱하는 함수는 아래에 새로 만들어야 함
    def get_news(self, url):
        # (1) Selenium이나 requests로 url 접속
        # (2) BeautifulSoup으로 html 파싱
        # (3) 제목, 본문 등 필요한 정보 추출
        # (4) dict 등으로 반환
        pass


if __name__ == "__main__":
    scraper = NewsScraper()

    # 테스트용 날짜 설정
    test_date = 20240101

    # [1] 단일 날짜 테스트
    print(f"날짜 {test_date} 크롤링 시작")
    links = scraper.get_news_links(test_date)
    print(f"수집된 링크 개수: {len(links)}")


    # [2] 링크를 CSV로 저장
    import csv
    with open('news/news_links.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'url'])
        for date, url in links:
            writer.writerow([date, url])

    print("크롤링 완료")

    # [6] (추후) 저장된 링크를 불러와서 get_news(url)로 본문 등 크롤링
    # for date, url in all_links:
    #     news_data = scraper.get_news(url)
    #     # 결과 저장

    # [피드백]
    # - 링크만 저장하지 말고 날짜와 함께 저장하면 나중에 분석/재사용에 유리함
    # - 본문 크롤링 함수(get_news)는 반드시 별도로 만들어두는 게 확장성에 좋음
    # - parse_news 함수는 현재 안 쓰고 있으니, 필요 없으면 삭제해도 됨
    # - 코드가 길어지면 함수별로 파일을 분리하는 것도 고려해볼 것

 

