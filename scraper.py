import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

# =============================================
# 네이버 뉴스 검색 RSS 기반 경쟁사 모니터링
# =============================================

# 회사별 검색 키워드 설정
# 검색어가 너무 짧으면 관계없는 기사도 잡히므로 구체적으로 설정
COMPANY_KEYWORDS = {
    "시큐아이": ["시큐아이"],
    "안랩": ["안랩", "AhnLab"],
    "넥스지": ["KX넥스지", "케이엑스넥스지", "KXNEXG", "nexg 보안"],
    "퓨처시스템": ["퓨처시스템"],
    "윈스": ["윈스 보안", "윈스테크넷"],
}

def fetch_naver_news(company, keyword):
    """네이버 뉴스 검색 RSS로 기사 수집"""
    results = []
    try:
        url = f"https://rss.news.naver.com/search/news?query={requests.utils.quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        for item in items[:20]:
            title = item.title.text.strip() if item.title else ""
            link = item.link.text.strip() if item.link else ""
            date = item.pubDate.text[:16] if item.pubDate else ""
            description = item.description.text.strip() if item.description else ""

            if not title:
                continue

            results.append({
                "company": company,
                "title": title,
                "link": link,
                "date": date,
                "source": "네이버뉴스",
                "description": description[:100] if description else ""
            })

    except Exception as e:
        print(f"  [오류] {company}/{keyword}: {e}")
    return results


def fetch_naver_blog(company, blog_id):
    """네이버 블로그 RSS 수집"""
    results = []
    try:
        url = f"https://rss.blog.naver.com/{blog_id}.xml"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        for item in items[:10]:
            title = item.title.text.strip() if item.title else ""
            link = item.link.text.strip() if item.link else ""
            date = item.pubDate.text[:16] if item.pubDate else ""

            if not title:
                continue

            results.append({
                "company": company,
                "title": title,
                "link": link,
                "date": date,
                "source": "공식블로그",
                "description": ""
            })

    except Exception as e:
        print(f"  [오류] {company} 블로그: {e}")
    return results


def main():
    all_data = []

    print("=" * 45)
    print("  경쟁사 동향 수집 시작")
    print(f"  실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 45)

    # 1. 네이버 뉴스 검색 RSS 수집
    print("\n[네이버 뉴스 검색]")
    for company, keywords in COMPANY_KEYWORDS.items():
        company_results = []
        for keyword in keywords:
            print(f"  검색 중: '{keyword}'...")
            results = fetch_naver_news(company, keyword)
            company_results.extend(results)
            print(f"    → {len(results)}건")
        all_data.extend(company_results)

    # 2. 공식 블로그 RSS 수집 (있는 회사만)
    print("\n[공식 블로그]")
    BLOGS = {
        "안랩": "ahnlab_official",
        "넥스지": "kxnexg",
    }
    for company, blog_id in BLOGS.items():
        print(f"  수집 중: {company} 블로그...")
        results = fetch_naver_blog(company, blog_id)
        all_data.extend(results)
        print(f"    → {len(results)}건")

    # 3. 중복 제거 (링크 기준)
    seen = set()
    unique_data = []
    for item in all_data:
        key = item.get("link") or item.get("title")
        if key and key not in seen:
            seen.add(key)
            unique_data.append(item)

    # 4. 날짜 최신순 정렬
    unique_data.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 5. 오늘 날짜 태그 추가 (상단 카드에서 '오늘 새 기사' 계산용)
    today_str = datetime.now().strftime("%Y-%m-%d")
    for item in unique_data:
        item["is_today"] = item.get("date", "").startswith(today_str)

    # 6. 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=4)

    # 7. 결과 요약 출력
    print("\n" + "=" * 45)
    print(f"  ✅ 총 {len(unique_data)}건 저장 완료")
    print("=" * 45)
    companies = ["시큐아이", "안랩", "넥스지", "퓨처시스템", "윈스"]
    for company in companies:
        total = sum(1 for d in unique_data if d["company"] == company)
        today = sum(1 for d in unique_data if d["company"] == company and d.get("is_today"))
        print(f"  {company}: 전체 {total}건 (오늘 {today}건)")

if __name__ == "__main__":
    main()
