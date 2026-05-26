import FinanceDataReader as fdr
import pandas as pd
import json
import datetime
import time

# 섹터 분류 매핑 (KRX 업종명 → 간단한 섹터명)
SECTOR_MAP = {
    '반도체': '반도체',
    '전기·전자': '전자',
    '의약품': '바이오',
    '바이오': '바이오',
    '제약': '바이오',
    '자동차': '자동차',
    '운수장비': '자동차',
    '은행': '금융',
    '금융업': '금융',
    '증권': '금융',
    '보험': '보험',
    '화학': '화학',
    '철강금속': '철강',
    '조선': '조선',
    '통신업': '통신',
    '유통업': '유통',
    '건설업': '건설',
    '음식료품': '소비재',
    '서비스업': 'IT',
    '운수창고': '물류',
    '기계': '기계',
    '전기가스업': '에너지',
    '비금속광물': '소재',
    '종이목재': '소재',
    '섬유의복': '소비재',
}

def map_sector(industry):
    if not industry or pd.isna(industry):
        return '기타'
    for key, val in SECTOR_MAP.items():
        if key in str(industry):
            return val
    return '기타'

def get_date_range():
    end = datetime.date.today()
    start = end - datetime.timedelta(days=50)  # 여유있게 50일치 요청
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

def fetch_price_data(code, start, end, retries=3):
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

def main():
    print('KRX 전체 상장 정보 로딩 중...')
    try:
        krx = fdr.StockListing('KRX')
        print(f'  전체 종목 수: {len(krx)}')
        print(f'  컬럼 목록: {list(krx.columns)}')
    except Exception as e:
        print(f'KRX 로딩 실패: {e}')
        return

    # 시가총액 컬럼 찾기
    cap_col = None
    for col in ['Marcap', 'MarCap', 'marcap', 'market_cap', 'Cap', '시가총액']:
        if col in krx.columns:
            cap_col = col
            break

    if not cap_col:
        print(f'시가총액 컬럼을 찾을 수 없습니다. 컬럼: {list(krx.columns)}')
        return

    print(f'  시가총액 컬럼: {cap_col}')

    # 종목코드 컬럼 찾기
    code_col = None
    for col in ['Code', 'Symbol', 'ticker', 'code']:
        if col in krx.columns:
            code_col = col
            break

    name_col = None
    for col in ['Name', 'name', '종목명', 'korName']:
        if col in krx.columns:
            name_col = col
            break

    print(f'  코드 컬럼: {code_col}, 이름 컬럼: {name_col}')

    # 시가총액 기준 상위 30 추출 (KOSPI만)
    market_col = None
    for col in ['Market', 'market', 'Exchange']:
        if col in krx.columns:
            market_col = col
            break

    if market_col:
        kospi = krx[krx[market_col].str.upper().str.contains('KOSPI', na=False)]
    else:
        kospi = krx  # KOSPI 필터 불가 시 전체 사용

    kospi = kospi.copy()
    kospi[cap_col] = pd.to_numeric(kospi[cap_col], errors='coerce')
    kospi = kospi.dropna(subset=[cap_col])
    top30 = kospi.sort_values(cap_col, ascending=False).head(30)

    print(f'\n오늘 기준 시가총액 Top 30:')
    for i, row in top30.iterrows():
        cap_jo = row[cap_col] / 1_000_000_000_000
        print(f'  {row[name_col]} ({row[code_col]}): {cap_jo:.1f}조')

    # 날짜 범위
    start, end = get_date_range()
    print(f'\n수집 기간: {start} ~ {end}')

    # 업종 컬럼 찾기
    industry_col = None
    for col in ['Sector', 'Industry', 'sector', 'industry', '업종']:
        if col in krx.columns:
            industry_col = col
            break

    output = {
        'generated_at': datetime.date.today().strftime('%Y-%m-%d'),
        'source': 'KRX via FinanceDataReader',
        'unit': '조원',
        'stocks': []
    }

    for _, stock_row in top30.iterrows():
        code = str(stock_row[code_col]).zfill(6)
        name = stock_row[name_col]
        today_cap_jo = stock_row[cap_col] / 1_000_000_000_000

        # 섹터 분류
        industry = stock_row.get(industry_col, '') if industry_col else ''
        sector = map_sector(industry)

        print(f'\n수집 중: {name} ({code}) - {sector}')

        df = fetch_price_data(code, start, end)
        if df is None:
            print(f'  → 데이터 없음, 스킵')
            continue

        # 최근 30영업일
        df = df.tail(30)
        close_col = 'Close' if 'Close' in df.columns else df.columns[0]
        closes = df[close_col].dropna()

        if len(closes) == 0:
            print(f'  → 종가 데이터 없음, 스킵')
            continue

        # 오늘 시가총액 기준으로 과거 종가 변동률 역산
        last_close = closes.iloc[-1]
        values = []
        for date_idx, price in closes.items():
            ratio = price / last_close if last_close != 0 else 1
            cap = round(today_cap_jo * ratio, 2)
            values.append({
                'date': date_idx.strftime('%Y-%m-%d'),
                'cap': cap
            })

        output['stocks'].append({
            'code': code,
            'name': name,
            'sector': sector,
            'values': values
        })
        print(f'  → {len(values)}일치 완료 (오늘 시가총액: {today_cap_jo:.1f}조)')

        time.sleep(0.3)

    # 저장
    import os
    os.makedirs('data', exist_ok=True)
    with open('data/kospi.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 완료: {len(output["stocks"])}개 종목 → data/kospi.json 저장')

if __name__ == '__main__':
    main()
