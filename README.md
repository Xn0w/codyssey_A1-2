# 여행 추천 프로그램 (A1-2)

날짜를 입력하면 AI(Gemini)가 여행지를 추천하고, 그 지역의 맛집을 카카오맵에서 검색해 하나의 여행 리포트(Markdown)로 만들어주는 CLI 프로그램입니다.

## 1. 프로그램 개요

전체 흐름은 아래 4단계로 진행됩니다.

1. 사용자가 입력한 날짜(`-date "YYYY-MM-DD"`)를 확인합니다.
2. Gemini API에게 해당 날짜에 여행하기 좋은 도시를 물어보고, 도시/날씨/행사/추천 이유를 JSON으로 받습니다.
3. 추천받은 도시 이름으로 카카오맵(Kakao Local API)에서 맛집 5곳을 검색합니다.
4. 위 결과를 종합해 Gemini에게 최종 여행 리포트 작성을 요청하고, `results/` 폴더에 원본 데이터(JSON)와 리포트(Markdown)를 저장합니다.

## 2. 실행 방법

### 2-1. 가상환경 생성 및 활성화

시스템 파이썬을 보호하기 위해 프로젝트 전용 가상환경(venv)을 사용합니다.

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2-2. 라이브러리 설치

```bash
pip install google-genai requests python-dotenv
```

### 2-3. 프로그램 실행

```bash
python3 main.py -date "YYYY-MM-DD"
```

예시:
```bash
python3 main.py -date "2026-08-15"
```

`-date`는 필수 옵션이며, `"YYYY-MM-DD"` 형식이 아니면 사용법을 안내하고 프로그램이 종료됩니다.

## 3. API 키 설정 방법

이 프로그램은 아래 2개의 API 키가 필요합니다.

| 키 이름 | 발급처 |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| `KAKAO_API_KEY` | [카카오 디벨로퍼스](https://developers.kakao.com) → 앱 선택 → 앱 키 → **REST API 키** |

카카오 API 키 발급 시, **제품 설정 > 카카오맵** 메뉴에서 활성화 상태를 반드시 켜주어야 합니다. 꺼져 있으면 요청이 403 오류로 거부됩니다.

프로젝트 최상위 폴더에 `.env` 파일을 만들고 아래처럼 작성합니다.

```
GEMINI_API_KEY=발급받은_Gemini_키
KAKAO_API_KEY=발급받은_카카오_REST_API_키
```

`.env` 파일은 `.gitignore`에 등록되어 있어 저장소에 올라가지 않습니다.

## 4. 결과물 확인 방법

실행이 끝나면 `results/` 폴더에 아래 2개 파일이 생성됩니다.

- `results/{날짜}_raw.json` — 1차 추천 정보(도시/날씨/행사/이유), 맛집 검색 결과, 진행 중 발생한 오류 목록(`errors`)이 담긴 원본 데이터
- `results/{날짜}_report.md` — 사람이 읽기 좋은 형태로 정리된 최종 여행 리포트 (추천 지역, 날씨, 행사, 맛집 리스트, 하루 일정 제안 포함)

맛집 검색 결과가 없거나 API 호출이 실패한 경우에도 프로그램은 중단되지 않고, 해당 항목을 "데이터 없음"으로 표시한 뒤 계속 진행됩니다.

## 5. 주의 사항 (API 키 보안)

- API 키는 코드에 직접 작성하지 않고 `.env` 파일에서 읽어옵니다 (`python-dotenv` 사용).
- `.env` 파일은 반드시 `.gitignore`에 포함시켜 저장소에 올라가지 않도록 합니다.
- 결과 파일(`results/`) 및 로그에도 API 키 값이 노출되지 않습니다.
- 이 저장소를 공유하거나 스크린샷을 찍을 때는 `.env` 내용이 화면에 보이지 않도록 주의합니다.

## 6. 개발 환경

- Python 3.10 이상 (개발 환경: Python 3.12)
- 터미널(CLI) 실행 기준이며 별도의 웹 UI는 없습니다.
- LLM: Gemini API (`google-genai` SDK, `gemini-2.5-flash` 모델)
- 장소 검색: Kakao Local API
