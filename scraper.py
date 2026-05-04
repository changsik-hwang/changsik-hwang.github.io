import requests
from bs4 import BeautifulSoup
import json

# 1. 긁어올 주소 설정 (네이버 블로그 RSS 피드가 수집하기 가장 쉽습니다)
url = "https://rss.blog.naver.com/kxnexg.xml" 

try:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    items = soup.find_all('item')

    new_data = []
    for item in items[:10]: # 최신글 10개만 가져오기
        new_data.append({
            "title": item.title.text,
            "link": item.link.text,
            "date": item.pubDate.text[:16] # 날짜 예쁘게 자르기
        })

    # 2. 파일로 저장
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    print("성공적으로 수집했습니다!")

except Exception as e:
    print(f"에러 발생: {e}")
