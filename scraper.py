import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from collections import Counter
from kiwipiepy import Kiwi

# =============================================
# 설정
# =============================================

KST       = timezone(timedelta(hours=9))
KEEP_DAYS = 180  # 6개월 보관

COMPANY_KEYWORDS = {
    "시큐아이":   ["시큐아이", "secui", "SECUI"],
    "안랩":       ["안랩", "AhnLab"],
    "넥스지":     ["KX넥스지", "케이엑스넥스지", "KXNEXG"],
    "퓨처시스템": ["퓨처시스템"],
    "윈스":       ["윈스", "윈스테크넷"],
}

TREND_KEYWORDS = {
    "AI보안":      ["AI 보안", "AI 위협탐지", "인공지능 보안"],
    "PQC":         ["PQC", "양자암호", "양자내성암호"],
    "제로트러스트": ["제로트러스트", "Zero Trust", "ZTNA"],
}

BLOGS = {
    "안랩": "ahnlab_official",
    "넥스지": "kxnexg",
}

STOPWORDS = {
    "안랩", "시큐아이", "넥스지", "퓨처시스템", "윈스", "윈스테크넷",
    "AhnLab", "SECUI", "NEXG", "WINS",
    "보안", "사이버", "양자", "기술", "시스템", "플랫폼", "솔루션",
    "서비스", "소프트웨어", "하드웨어", "네트워크", "데이터", "클라우드",
    "관련", "통해", "위해", "대한", "있는", "하는", "이번", "지난", "올해",
    "이후", "기반", "강화", "제공", "발표", "출시", "진행", "구축", "운영",
    "지원", "확대", "활용", "적용", "도입", "공급", "수주", "계약", "체결",
    "분야", "업체", "회사", "기업", "시장", "사업", "협력", "파트너", "추진",
    "대표", "부문", "사장", "본부", "센터", "부장", "이사", "전무", "대리",
    "하여", "되어", "위한", "통한", "대해", "에서", "으로", "까지",
    "가장", "더욱", "새로운", "다양한", "국내", "글로벌", "전문",
    "제품", "업데이트", "버전", "기능", "환경", "인프라", "관리",
    "공격", "위협", "악성", "탐지", "차단", "방어", "대응", "분석",
}

# =============================================
# 날짜 파싱
# =============================================

def parse_date(date_str):
    if not date_str:
        return ""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        return date_str[:16]
    except Exception:
        return ""

def date_sort_key(item):
    return item.get("date", "")

# =============================================
# 기존 데이터 로드
# =============================================

def load_existing_data():
    if not os.path.exists("data.json"):
        return [], [], {}, {}
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return (
            data.get("competitor", []),
            data.get("trend", []),
            data.get("competitor_monthly_keywords", {}),
            data.get("trend_monthly_keywords", {}),
        )
    except Exception as e:
        print(f"  [오류] 기존 데이터 로드 실패: {e}")
        return [], [], {}, {}

def filter_old_data(data, cutoff_str):
    return [d for d in data if d.get("date", "") >= cutoff_str]

# =============================================
# 수집 함수
# =============================================

def fetch_google_news(keyword):
    results = []
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        for item in items[:100]:
            title    = item.title.text.strip() if item.title else ""
            link     = item.link.text.strip() if item.link else ""
            pub_date = item.pubDate.text.strip() if item.pubDate else ""
            date     = parse_date(pub_date)

            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()

            if not title:
                continue

            results.append({
                "title":       title,
                "link":        link,
                "date":        date,
                "description": ""
            })

    except Exception as e:
        print(f"  [오류] '{keyword}': {e}")
    return results


def fetch_naver_blog(blog_id):
    results = []
    try:
        url = f"https://rss.blog.naver.com/{blog_id}.xml"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        for item in items[:100]:
            title    = item.title.text.strip() if item.title else ""
            link     = item.link.text.strip() if item.link else ""
            pub_date = item.pubDate.text.strip() if item.pubDate else ""
            date     = parse_date(pub_date)

            if not title:
                continue

            results.append({
                "title":       title,
                "link":        link,
                "date":        date,
                "description": ""
            })

    except Exception as e:
        print(f"  [오류] 블로그 {blog_id}: {e}")
    return results


def deduplicate(data):
    seen_links  = set()
    seen_titles = set()
    result      = []

    for item in data:
        link             = item.get("link", "")
        title            = item.get("title", "").strip()
        title_normalized = ''.join(c for c in title if c.isalnum() or '\uAC00' <= c <= '\uD7A3')

        if link and link in seen_links:
            continue
        if title_normalized and title_normalized in seen_titles:
            continue
        if link:
            seen_links.add(link)
        if title_normalized:
            seen_titles.add(title_normalized)

        result.append(item)

    return result

# =============================================
# 월별 키워드 추출
# =============================================

def extract_monthly_keywords(data, now_kst, top_n=5):
    """
    최근 3개월치를 월별로 따로 키워드 추출
    반환: { "2026-05": [...], "2026-04": [...], "2026-03": [...] }
    """
    try:
        kiwi = Kiwi()
        monthly = {}

        for i in range(3):  # 이번 달, 전달, 전전달
            # 해당 월 계산
            target_dt    = now_kst - timedelta(days=30 * i)
            target_month = target_dt.strftime("%Y-%m")

            # 해당 월 기사만 필터링
            month_data = [d for d in data if d.get("date", "").startswith(target_month)]
            print(f"  {target_month}: {len(month_data)}건 분석 중...")

            if not month_data:
                monthly[target_month] = []
                continue

            titles = " ".join([d.get("title", "") for d in month_data])
            result = kiwi.analyze(titles)
            nouns  = []

            for token in result[0][0]:
                word = token.form
                tag  = str(token.tag)
                if tag in ["NNG", "NNP"]:
                    if len(word) >= 2 and word not in STOPWORDS:
                        nouns.append(word)

            counter      = Counter(nouns)
            top_keywords = counter.most_common(top_n)
            monthly[target_month] = [{"keyword": k, "count": c} for k, c in top_keywords]
            print(f"    → {monthly[target_month]}")

        return monthly

    except Exception as e:
        print(f"  [오류] 월별 키워드 추출 실패: {e}")
        return {}

# =============================================
# 메인
# =============================================

def main():
    now_kst    = datetime.now(KST)
    today_str  = now_kst.strftime("%Y-%m-%d")
    cutoff_dt  = now_kst - timedelta(days=KEEP_DAYS)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d")

    print("=" * 45)
    print(f"  수집 시작 (KST): {now_kst.strftime('%Y-%m-%d %H:%M')}")
    print(f"  보관 기준: {cutoff_str} 이후 데이터만 유지")
    print("=" * 45)

    old_competitor, old_trend, _, _ = load_existing_data()
    old_competitor = filter_old_data(old_competitor, cutoff_str)
    old_trend      = filter_old_data(old_trend, cutoff_str)

    # ── 탭1: 경쟁사 ──────────────────────────
    print("\n[탭1: 경쟁사 동향]")
    new_competitor = []

    for company, keywords in COMPANY_KEYWORDS.items():
        for keyword in keywords:
            print(f"  검색: '{keyword}'...")
            for item in fetch_google_news(keyword):
                item["company"]  = company
                item["tab"]      = "competitor"
                item["source"]   = "구글뉴스"
                item["is_today"] = item["date"].startswith(today_str)
                new_competitor.append(item)

    for company, blog_id in BLOGS.items():
        print(f"  블로그: {company}...")
        for item in fetch_naver_blog(blog_id):
            item["company"]  = company
            item["tab"]      = "competitor"
            item["source"]   = "공식블로그"
            item["is_today"] = item["date"].startswith(today_str)
            new_competitor.append(item)

    competitor_data = deduplicate(old_competitor + new_competitor)
    competitor_data.sort(key=date_sort_key, reverse=True)

    print(f"\n  → 경쟁사 총 {len(competitor_data)}건")
    for c in COMPANY_KEYWORDS:
        cnt       = sum(1 for d in competitor_data if d["company"] == c)
        today_cnt = sum(1 for d in competitor_data if d["company"] == c and d.get("is_today"))
        print(f"     {c}: {cnt}건 (오늘 {today_cnt}건)")

    # ── 탭2: 기술 트렌드 ─────────────────────
    print("\n[탭2: 기술 트렌드]")
    new_trend = []

    for category, keywords in TREND_KEYWORDS.items():
        for keyword in keywords:
            print(f"  검색: '{keyword}'...")
            for item in fetch_google_news(keyword):
                item["category"] = category
                item["keyword"]  = keyword
                item["tab"]      = "trend"
                item["source"]   = "구글뉴스"
                item["is_today"] = item["date"].startswith(today_str)
                new_trend.append(item)

    trend_data = deduplicate(old_trend + new_trend)
    trend_data.sort(key=date_sort_key, reverse=True)

    print(f"\n  → 트렌드 총 {len(trend_data)}건")

    # ── 월별 키워드 추출 ──────────────────────
    print("\n[월별 키워드 분석]")
    print("  경쟁사 키워드 추출 중...")
    competitor_monthly = extract_monthly_keywords(competitor_data, now_kst, top_n=5)

    print("  트렌드 키워드 추출 중...")
    trend_monthly = extract_monthly_keywords(trend_data, now_kst, top_n=5)

    # ── 저장 ─────────────────────────────────
    output = {
        "updated":                      now_kst.strftime("%Y-%m-%d %H:%M"),
        "current_month":                now_kst.strftime("%Y-%m"),
        "competitor":                   competitor_data,
        "trend":                        trend_data,
        "competitor_monthly_keywords":  competitor_monthly,
        "trend_monthly_keywords":       trend_monthly,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"\n✅ 저장 완료")
    print(f"   경쟁사: {len(competitor_data)}건")
    print(f"   트렌드: {len(trend_data)}건")

if __name__ == "__main__":
    main()
