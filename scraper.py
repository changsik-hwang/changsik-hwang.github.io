import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# =============================================
# 경쟁사 모니터링 - 최종 설정
# =============================================

COMPANIES = ["시큐아이", "안랩", "넥스지", "퓨처시스템", "윈스"]

# =============================================
# 1. RSS 수집 (가장 안정적인 방법)
# =============================================

RSS_SOURCES = [
    # 보안뉴스 - 5개사 소식이 모두 등장하는 핵심 소스
    {
        "name": "보안뉴스",
        "url": "https://www.boannews.com/media/news_rss.asp",
    },
    # 안랩 공식 블로그
    {
        "name": "안랩블로그",
        "url": "https://rss.blog.naver.com/ahnlab_official.xml",
    },
    # 안랩 ASEC 보안분석 블로그
    {
        "name": "안랩ASEC",
        "url": "https://asec.ahnlab.com/ko/feed/",
    },
    # 넥스지 공식 네이버 블로그 (가장 안정적)
    {
        "name": "넥스지블로그",
        "url": "https://rss.blog.naver.com/kxnexg.xml",
    },
]

def fetch_rss(source):
    """RSS 피드 수집 - 경쟁사 이름이 포함된 기사만 필터링"""
    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(source["url"], headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        for item in items[:50]:
            title = item.title.text.strip() if item.title else ""
            
            # link 처리 (네이버 블로그는 다른 태그 사용)
            link = ""
            if item.link:
                link = item.link.text.strip()
            if not link and item.find("link"):
                link = item.find("link").get_text().strip()

            # 날짜 처리
            date = ""
            if item.pubDate:
                date = item.pubDate.text[:16]
            elif item.find("pubDate"):
                date = item.find("pubDate").text[:16]

            if not title:
                continue

            # 넥스지 블로그는 모든 글이 넥스지 소식
            if source["name"] == "넥스지블로그":
                results.append({
                    "company": "넥스지",
                    "title": title,
                    "link": link,
                    "date": date,
                    "source": "넥스지블로그"
                })
                continue

            # 안랩 블로그/ASEC은 모두 안랩 소식
            if source["name"] in ["안랩블로그", "안랩ASEC"]:
                results.append({
                    "company": "안랩",
                    "title": title,
                    "link": link,
                    "date": date,
                    "source": source["name"]
                })
                continue

            # 보안뉴스는 경쟁사 이름 포함 여부로 필터링
            for company in COMPANIES:
                if company in title:
                    results.append({
                        "company": company,
                        "title": title,
                        "link": link,
                        "date": date,
                        "source": source["name"]
                    })
                    break

    except Exception as e:
        print(f"  [오류] {source['name']}: {e}")
    return results


# =============================================
# 2. 시큐아이 공홈 보도자료 직접 파싱
# =============================================

def fetch_secui_news():
    """시큐아이 공식 홈페이지 보도자료"""
    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = "https://www.secui.com/about/news"
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        # 링크 중 보도자료 링크 추출
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            
            # 보도자료 링크 패턴 확인
            if "news" in href and "view" in href and len(title) > 10:
                full_url = href if href.startswith("http") else "https://www.secui.com" + href
                results.append({
                    "company": "시큐아이",
                    "title": title,
                    "link": full_url,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "시큐아이공홈"
                })

        print(f"  → 시큐아이 공홈: {len(results)}건")
    except Exception as e:
        print(f"  [오류] 시큐아이 공홈: {e}")
    return results[:10]


# =============================================
# 메인 실행
# =============================================

def main():
    all_data = []

    print("=" * 40)
    print("  경쟁사 동향 수집 시작")
    print("=" * 40)

    # RSS 수집
    for source in RSS_SOURCES:
        print(f"수집 중: {source['name']}...")
        results = fetch_rss(source)
        all_data.extend(results)
        print(f"  → {len(results)}건")

    # 시큐아이 공홈
    print("수집 중: 시큐아이 공홈...")
    all_data.extend(fetch_secui_news())

    # 중복 제거 (링크 기준)
    seen = set()
    unique_data = []
    for item in all_data:
        key = item.get("link", item["title"])
        if key and key not in seen:
            seen.add(key)
            unique_data.append(item)

    # 날짜 최신순 정렬
    unique_data.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=4)

    print("\n" + "=" * 40)
    print(f"  ✅ 총 {len(unique_data)}건 저장 완료")
    print("=" * 40)
    for company in COMPANIES:
        count = sum(1 for d in unique_data if d["company"] == company)
        print(f"  {company}: {count}건")

if __name__ == "__main__":
    main()
