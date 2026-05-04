import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# =============================================
# 설정
# =============================================

# 탭1: 경쟁사
COMPANY_KEYWORDS = {
    "시큐아이":   ["시큐아이", "secui"],
    "안랩":       ["안랩", "AhnLab"],
    "넥스지":     ["KX넥스지", "케이엑스넥스지", "KXNEXG"],
    "퓨처시스템": ["퓨처시스템"],
    "윈스":       ["wins", "윈스테크넷"],
}

# 탭2: 기술 트렌드
TREND_KEYWORDS = {
    "AI보안":    ["AI 보안", "AI 위협탐지", "인공지능 보안"],
    "PQC":       ["PQC", "양자암호", "양자내성암호", "후양자암호"],
    "제로트러스트": ["제로트러스트", "Zero Trust"],
}

# 공식 블로그 (경쟁사)
BLOGS = {
    "안랩": "ahnlab_official",
    "넥스지": "kxnexg",
}

# =============================================
# 수집 함수
# =============================================

def fetch_naver_news(keyword):
    """네이버 뉴스 검색 RSS"""
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
            desc = item.description.text.strip() if item.description else ""
            if not title:
                continue
            results.append({
                "title": title,
                "link": link,
                "date": date,
                "description": desc[:120] if desc else ""
            })
    except Exception as e:
        print(f"  [오류] '{keyword}': {e}")
    return results


def fetch_naver_blog(blog_id):
    """네이버 블로그 RSS"""
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
                "title": title,
                "link": link,
                "date": date,
                "description": ""
            })
    except Exception as e:
        print(f"  [오류] 블로그 {blog_id}: {e}")
    return results


def deduplicate(data):
    """링크 기준 중복 제거"""
    seen = set()
    result = []
    for item in data:
        key = item.get("link") or item.get("title")
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


# =============================================
# 메인
# =============================================

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")

    print("=" * 45)
    print(f"  수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 45)

    # ── 탭1: 경쟁사 ──────────────────────────
    print("\n[탭1: 경쟁사 동향]")
    competitor_data = []

    for company, keywords in COMPANY_KEYWORDS.items():
        for keyword in keywords:
            print(f"  검색: '{keyword}'...")
            for item in fetch_naver_news(keyword):
                item["company"] = company
                item["tab"] = "competitor"
                item["source"] = "네이버뉴스"
                item["is_today"] = item["date"].startswith(today_str)
                competitor_data.append(item)

    for company, blog_id in BLOGS.items():
        print(f"  블로그: {company}...")
        for item in fetch_naver_blog(blog_id):
            item["company"] = company
            item["tab"] = "competitor"
            item["source"] = "공식블로그"
            item["is_today"] = item["date"].startswith(today_str)
            competitor_data.append(item)

    competitor_data = deduplicate(competitor_data)
    competitor_data.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"\n  → 경쟁사 총 {len(competitor_data)}건")
    for c in COMPANY_KEYWORDS:
        cnt = sum(1 for d in competitor_data if d["company"] == c)
        today_cnt = sum(1 for d in competitor_data if d["company"] == c and d.get("is_today"))
        print(f"     {c}: {cnt}건 (오늘 {today_cnt}건)")

    # ── 탭2: 기술 트렌드 ─────────────────────
    print("\n[탭2: 기술 트렌드]")
    trend_data = []

    for category, keywords in TREND_KEYWORDS.items():
        for keyword in keywords:
            print(f"  검색: '{keyword}'...")
            for item in fetch_naver_news(keyword):
                item["category"] = category
                item["keyword"] = keyword
                item["tab"] = "trend"
                item["source"] = "네이버뉴스"
                item["is_today"] = item["date"].startswith(today_str)
                trend_data.append(item)

    trend_data = deduplicate(trend_data)
    trend_data.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"\n  → 트렌드 총 {len(trend_data)}건")
    for c in TREND_KEYWORDS:
        cnt = sum(1 for d in trend_data if d["category"] == c)
        print(f"     {c}: {cnt}건")

    # ── 저장 ─────────────────────────────────
    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "competitor": competitor_data,
        "trend": trend_data
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"\n✅ 저장 완료 (competitor: {len(competitor_data)}건 / trend: {len(trend_data)}건)")

if __name__ == "__main__":
    main()
