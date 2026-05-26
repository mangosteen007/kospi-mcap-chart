# 📈 KOSPI 시가총액 Top 30 추이 대시보드

매일 낮 12시에 자동 업데이트되는 KOSPI 시가총액 상위 30종목 선그래프 대시보드입니다.

🔗 **[사이트 바로가기](https://mangosteen007.github.io/kospi-mcap-chart/)**

---

## 주요 기능

- 시가총액 상위 30종목의 최근 30영업일 추이를 선그래프로 시각화
- **절대값(조원) / 등락률(%)** 전환
- **Y축 범위 슬라이더** — 보고 싶은 구간만 드래그로 확대
- **마우스 오버** 시 해당 선의 종목 정보 표시
- **종목 클릭** 시 해당 종목 하이라이트
- 매일 오전 12시 자동 갱신 (월~금)

---

## 기술 스택

| 역할 | 도구 |
|------|------|
| 호스팅 | GitHub Pages |
| 자동화 | GitHub Actions |
| 데이터 수집 | FinanceDataReader (KRX) |
| 시각화 | D3.js |

---

## 프로젝트 구조

```
kospi-mcap-chart/
├── index.html                        # D3.js 기반 차트 프론트엔드
├── data/
│   └── kospi.json                    # 자동 생성되는 시가총액 데이터
├── scripts/
│   └── generate_data.py              # KRX 데이터 수집 스크립트
└── .github/
    └── workflows/
        └── update-data.yml           # 자동화 스케줄러
```

---

## 동작 방식

```
[GitHub Actions - 매일 낮 12시, 월~금]
    ↓
[generate_data.py 실행]
    ↓ FinanceDataReader로 KRX 접속
    ↓ 당일 시가총액 기준 KOSPI Top 30 자동 추출
    ↓ 각 종목의 최근 30영업일 종가 수집
    ↓ 오늘 시가총액 기준으로 과거 시가총액 역산
    ↓
[data/kospi.json 자동 커밋]
    ↓
[GitHub Pages에서 index.html이 JSON 읽어 차트 렌더링]
```

---

## 데이터 출처

- **KRX (한국거래소)** via [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)
- 시가총액 = 오늘 KRX 시가총액 기준 × 과거 종가 변동률 역산
- API 키 불필요 / 완전 무료

---

## 운영 비용

| 항목 | 비용 |
|------|------|
| GitHub Pages 호스팅 | 무료 |
| GitHub Actions 실행 | 무료 (월 2,000분 이내) |
| 데이터 수집 API | 무료 |
| **합계** | **$0** |

---

## 로컬 실행

```bash
# 패키지 설치
pip install finance-datareader pandas

# 데이터 수집 실행
python scripts/generate_data.py

# index.html을 브라우저로 열면 확인 가능
# (로컬에서는 CORS 때문에 로컬 서버 필요)
python -m http.server 8000
# → http://localhost:8000 접속
```
