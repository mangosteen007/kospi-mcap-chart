import FinanceDataReader as fdr
import pandas as pd
import json
import datetime
import time

# KOSPI 시가총액 상위 30종목 (2025년 기준 고정 리스트)
STOCKS = [
    {"code": "005930", "name": "삼성전자",     "sector": "반도체"},
    {"code": "000660", "name": "SK하이닉스",   "sector": "반도체"},
    {"code": "207940", "name": "삼성바이오로직스", "sector": "바이오"},
    {"code": "005380", "name": "현대차",        "sector": "자동차"},
    {"code": "000270", "name": "기아",          "sector": "자동차"},
    {"code": "105560", "name": "KB금융",        "sector": "금융"},
    {"code": "068270", "name": "셀트리온",      "sector": "바이오"},
    {"code": "055550", "name": "신한지주",      "sector": "금융"},
    {"code": "006400", "name": "삼성SDI",       "sector": "배터리"},
    {"code": "035420", "name": "NAVER",         "sector": "IT"},
    {"code": "051910", "name": "LG화학",        "sector": "화학"},
    {"code": "005490", "name": "POSCO홀딩스",   "sector": "철강"},
    {"code": "086790", "name": "하나금융지주",  "sector": "금융"},
    {"code": "012330", "name": "현대모비스",    "sector": "자동차"},
    {"code": "028260", "name": "삼성물산",      "sector": "건설"},
    {"code": "329180", "name": "HD현대중공업",  "sector": "조선"},
    {"code": "066570", "name": "LG전자",        "sector": "전자"},
    {"code": "003550", "name": "LG",            "sector": "지주"},
    {"code": "032830", "name": "삼성생명",      "sector": "보험"},
    {"code": "017670", "name": "SK텔레콤",      "sector": "통신"},
    {"code": "042660", "name": "한화오션",      "sector": "조선"},
    {"code": "096770", "name": "SK이노베이션",  "sector": "에너지"},
    {"code": "034730", "name": "SK",            "sector": "지주"},
    {"code": "030200", "name": "KT",            "sector": "통신"},
    {"code": "006260", "name": "LS",            "sector": "전력기기"},
    {"code": "316140", "name": "우리금융지주",  "sector": "금융"},
    {"code": "011200", "name": "HMM",           "sector": "해운"},
    {"code": "010950", "name": "S-Oil",         "sector": "에너지"},
    {"code": "003490", "name": "대한항공",      "sector": "항공"},
    {"code": "010140", "name": "삼성중공업",    "sector": "조선"},
]

def get_date_range():
    """최근 30영업일 날짜 범위 계산"""
    end = datetime.date.today()
    # 45일치 가져와서 영업일 30일 확보
    start = end - datetime.timedelta(days=45)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def fetch_stock_data(code, start, end, retries=3):
    """종목 데이터 수집 (재시도 포함)"""
    for attempt in range(retries):
        try:
            df = fdr.DataReader(code, start, end)
            if df.empty:
                return None
            return df
        except Exception as e:
            print(f"  [{code}] 시도 {attempt+1}/{retries} 실패: {e}")
            time.sleep(2)
    return None

def calc_market_cap(df, code):
    """
    시가총액 계산: 종가 × 상장주식수
    FinanceDataReader에서 직접 시가총액을 제공하지 않으므로
    KRX 상장주식수 데이터를 활용합니다.
    """
    try:
        # KRX 전체 종목 정보에서 시가총액 가져오기
        krx = fdr.StockListing('KRX')
        row = krx[krx['Code'] == code]
        if row.empty:
            return None
        
        # 상장주식수
        shares = row['Stocks'].values[0] if 'Stocks' in row.columns else None
        if shares is None or shares == 0:
            return None

        # 일별 종가 × 상장주식수 → 시가총액 (조원)
        result = []
        close_col = 'Close' if 'Close' in df.columns else df.columns[0]
        for date, row_data in df.iterrows():
            cap_won = row_data[close_col] * shares          # 원
            cap_jo = cap_won / 1_000_000_000_000            # 조원
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "cap": round(float(cap_jo), 2)
            })
        return result

    except Exception as e:
        print(f"  시가총액 계산 오류: {e}")
        return None

def calc_market_cap_from_price(df):
    """
    대안: 종가 기준 상대적 변동만 계산
    (상장주식수를 못 가져올 경우 fallback)
    """
    close_col = 'Close' if 'Close' in df.columns else df.columns[0]
    prices = df[close_col].dropna()
    
    result = []
    for date, price in prices.items():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "cap": round(float(price), 0)   # 종가 그대로 (원)
        })
    return result

def main():
    start, end = get_date_range()
    print(f"수집 기간: {start} ~ {end}")

    output = {
        "generated_at": datetime.date.today().strftime("%Y-%m-%d"),
        "source": "KRX via FinanceDataReader",
        "unit": "조원",
        "stocks": []
    }

    # KRX 전체 상장 정보 (시가총액 포함) 한 번만 로드
    print("KRX 상장 정보 로딩...")
    try:
        krx_all = fdr.StockListing('KRX')
        # 시가총액 컬럼명 확인
        cap_col = None
        for col in ['Marcap', 'MarCap', 'market_cap', 'Cap']:
            if col in krx_all.columns:
                cap_col = col
                break
        print(f"  시가총액 컬럼: {cap_col}")
        print(f"  컬럼 목록: {list(krx_all.columns)}")
    except Exception as e:
        print(f"KRX 로딩 실패: {e}")
        krx_all = None
        cap_col = None

    for stock in STOCKS:
        code = stock["code"]
        name = stock["name"]
        print(f"수집 중: {name} ({code})")

        df = fetch_stock_data(code, start, end)
        if df is None:
            print(f"  → 데이터 없음, 스킵")
            continue

        # 최근 30영업일만
        df = df.tail(30)

        # 시가총액 계산 시도
        values = None

        # 방법 1: KRX 시가총액 직접 사용 (오늘 기준 1개 값만 있음)
        if krx_all is not None and cap_col:
            try:
                row = krx_all[krx_all['Code'] == code]
                if not row.empty:
                    today_cap_won = row[cap_col].values[0]
                    today_cap_jo = today_cap_won / 1_000_000_000_000

                    # 오늘 시가총액 기준 + 과거 종가 변동률 역산
                    close_col = 'Close' if 'Close' in df.columns else df.columns[0]
                    closes = df[close_col].dropna()
                    last_close = closes.iloc[-1]

                    values = []
                    for date, price in closes.items():
                        ratio = price / last_close if last_close != 0 else 1
                        cap = round(today_cap_jo * ratio, 2)
                        values.append({
                            "date": date.strftime("%Y-%m-%d"),
                            "cap": cap
                        })
                    print(f"  → 시가총액 역산 성공: 오늘 {today_cap_jo:.1f}조")
            except Exception as e:
                print(f"  → 시가총액 역산 실패: {e}")

        # 방법 2: fallback - 종가 그대로 (원)
        if values is None:
            close_col = 'Close' if 'Close' in df.columns else df.columns[0]
            closes = df[close_col].dropna()
            values = [{"date": d.strftime("%Y-%m-%d"), "cap": round(float(p), 0)} for d, p in closes.items()]
            output["unit"] = "원 (종가)"
            print(f"  → fallback: 종가 사용")

        if values:
            output["stocks"].append({
                "code": code,
                "name": name,
                "sector": stock["sector"],
                "values": values
            })
            print(f"  → {len(values)}일치 수집 완료")

        time.sleep(0.5)  # API 과부하 방지

    # 저장
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/kospi.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {len(output['stocks'])}개 종목 → data/kospi.json 저장")

if __name__ == "__main__":
    main()
