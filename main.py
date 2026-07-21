"""
여행 추천 프로그램 (A1-2)
--------------------------------
사용법 예시:
    python main.py -date "2026-08-15"

전체 흐름 (프로그램이 하는 일 4단계):
    1) 사용자가 입력한 날짜를 확인한다.
    2) Gemini(AI)에게 "이 날짜에 여행하기 좋은 도시"를 물어보고 JSON으로 받는다.
    3) 그 도시 이름으로 카카오맵에서 맛집을 검색한다.
    4) 위 결과들을 합쳐서 Gemini에게 "여행 리포트"를 Markdown으로 작성해달라고 요청하고,
       results/ 폴더에 파일로 저장한다.
"""

import os
import json
import argparse
from datetime import datetime

from google import genai              # Gemini API 최신 통합 SDK (pip install google-genai)
                                        # * 예전 google-generativeai 패키지는 서비스가 종료(deprecated)되어
                                        #   더 이상 사용하지 않습니다.
import requests                        # 카카오 API 호출용 (pip install requests)
from dotenv import load_dotenv         # .env 파일을 읽어오는 라이브러리

GEMINI_MODEL_NAME = "gemini-2.5-flash"  # 현재(2026년 기준) 사용 가능한 Gemini 모델명


# ============================================================
# 0. 환경변수(API 키) 불러오기
#    .env 파일 안에 적어둔 GEMINI_API_KEY, KAKAO_API_KEY 값을
#    이 프로그램이 사용할 수 있게 메모리로 가져오는 단계입니다.
# ============================================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

_genai_client = None  # Gemini 클라이언트를 한 번만 만들어서 재사용하기 위한 저장 공간


def get_genai_client():
    """
    Gemini 클라이언트를 처음 호출될 때 딱 한 번만 생성하고,
    이후에는 이미 만들어둔 걸 재사용합니다 (매번 새로 만들 필요가 없기 때문).
    """
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


def check_api_keys():
    """
    API 키가 하나라도 없으면(=.env 설정을 안 했으면) 프로그램을 바로 종료합니다.
    나중에 이상한 에러 메시지를 보는 대신, 여기서 미리 친절하게 안내하는 것이 목적입니다.
    """
    if not GEMINI_API_KEY:
        print("[오류] GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        print('예시: GEMINI_API_KEY=your_key_here')
        exit(1)  # exit(1) = "정상 종료가 아니라 에러 때문에 멈췄다"는 신호

    if not KAKAO_API_KEY:
        print("[오류] KAKAO_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        print('예시: KAKAO_API_KEY=your_key_here')
        exit(1)


# ============================================================
# 1. CLI 입력값(날짜) 받기 & 검증하기
#    argparse는 "터미널에서 프로그램을 실행할 때 옵션을 입력받게 해주는" 도구입니다.
#    예: python main.py -date "2026-08-15" 를 실행하면
#        args.date 안에 "2026-08-15" 라는 문자열이 담깁니다.
# ============================================================
def parse_arguments():
    parser = argparse.ArgumentParser(description="날짜 기반 여행 추천 프로그램")
    parser.add_argument(
        "-date",
        required=True,                  # 반드시 입력해야 하는 필수 옵션
        help='여행 날짜 (형식: "YYYY-MM-DD", 예: "2026-08-15")'
    )
    args = parser.parse_args()

    # 사용자가 입력한 날짜가 진짜 "YYYY-MM-DD" 형식인지 확인합니다.
    # 형식이 다르면(예: "2026/08/15") 에러를 내고 프로그램을 종료합니다.
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print('[오류] 날짜 형식이 올바르지 않습니다. "YYYY-MM-DD" 형식으로 입력해주세요.')
        parser.print_usage()
        exit(1)

    return args.date


# ============================================================
# 2. Gemini에게 "1차 추천" 요청하기 (도시 / 날씨 / 행사 / 이유)
#    AI에게 질문(프롬프트)을 보내고, 답변을 JSON 형태로 받는 단계입니다.
# ============================================================
def get_travel_recommendation(date_str, retry=True):
    """
    date_str: 사용자가 입력한 날짜 (예: "2026-08-15")
    retry: JSON 파싱이 실패했을 때 한 번 더 시도할지 여부 (기본 True = 1회 재시도 허용)

    반환값: {"recommended_city": ..., "weather": ..., "events": [...], "reason": ...} 형태의 딕셔너리
    """
    # AI에게 "반드시 이 형식의 JSON만 출력해줘"라고 명확하게 지시하는 것이 핵심입니다.
    # 사람 말투로 설명을 덧붙이면 JSON 파싱이 깨지기 쉬우므로, 형식을 못박아둡니다.
    prompt = f"""
    {date_str}에 한국에서 여행하기 좋은 도시 1곳을 추천해줘.
    아래 JSON 형식으로만 응답하고, 다른 설명이나 코드블록 표시(```)는 절대 붙이지 마.

    {{
        "recommended_city": "도시 이름 (예: 제주)",
        "weather": "그 시기의 일반적인 날씨 요약 (한 문장)",
        "events": ["행사/축제 후보 1", "행사/축제 후보 2"],
        "reason": "추천 이유 (2~4문장)"
    }}
    """

    # 빈 값(기본 실패 응답) 하나를 미리 만들어둡니다.
    # -> API 호출 자체가 실패하든, JSON 파싱이 실패하든 항상 "같은 모양"의 딕셔너리를 반환하게 해서
    #    이후 코드(generate_report 등)가 굳이 None 체크를 복잡하게 하지 않아도 되게 합니다.
    empty_result = {
        "recommended_city": None,
        "weather": None,
        "events": [],
        "reason": None,
    }

    try:
        # 네트워크 오류, 인증 오류, 쿼터 초과 등 Gemini 호출 자체가 실패할 수 있는 모든 경우를 여기서 잡습니다.
        client = get_genai_client()
        response = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt)
        raw_text = response.text.strip()
    except Exception as e:
        print(f"[오류] Gemini API 호출에 실패했습니다: {e}")
        return empty_result

    # 혹시 AI가 ```json ... ``` 처럼 코드블록으로 감싸서 답했을 경우를 대비해 제거합니다.
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw_text)  # 문자열을 진짜 파이썬 딕셔너리로 변환
        return data
    except json.JSONDecodeError:
        # JSON으로 변환이 안 됐다면 -> 한 번만 더 시도해봅니다 (무한 재시도는 하지 않음).
        if retry:
            print("[안내] AI 응답을 JSON으로 읽지 못해 한 번 더 요청합니다...")
            return get_travel_recommendation(date_str, retry=False)
        else:
            # 두 번째도 실패하면 빈 값으로 채워서 프로그램이 멈추지 않게 합니다.
            print("[오류] AI 응답을 JSON으로 변환하는 데 실패했습니다.")
            return empty_result


# ============================================================
# 3. 카카오맵으로 맛집 검색하기
#    추천받은 도시 이름으로 "맛집"을 검색해서 상위 5곳을 가져옵니다.
# ============================================================
def search_restaurants(city_name, limit=5):
    """
    city_name: 검색할 도시 이름 (예: "제주")
    limit: 가져올 맛집 개수 (기본 5곳)

    반환값: [{"name":..., "address":..., "category":..., "url":..., "x":..., "y":...}, ...]
            검색 결과가 없으면 빈 리스트 []를 반환합니다 (프로그램이 멈추지 않도록).
    """
    if not city_name:
        # 애초에 도시 이름을 못 받았다면 검색을 시도할 필요가 없습니다.
        return []

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}  # 카카오 API는 이 방식으로 인증합니다.
    params = {"query": f"{city_name} 맛집", "size": limit}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()  # 401/403/네트워크 오류 등이면 여기서 예외를 발생시킵니다.
        results = response.json().get("documents", [])

        restaurants = []
        for place in results:
            restaurants.append({
                "name": place.get("place_name"),
                "address": place.get("road_address_name") or place.get("address_name"),
                "category": place.get("category_name"),
                "url": place.get("place_url"),
                "x": place.get("x"),  # 경도
                "y": place.get("y"),  # 위도
            })
        return restaurants

    except requests.exceptions.RequestException as e:
        # 네트워크 오류, 인증 오류(401/403), 쿼터 초과 등 -> 프로그램을 멈추지 않고 빈 리스트로 처리합니다.
        print(f"[경고] 맛집 검색에 실패했습니다: {e}")
        return []


# ============================================================
# 4. 최종 리포트 만들기 (Markdown 형식) - Gemini에게 작성을 맡깁니다
#    과제 요구사항: "LLM API 연동 - 최종 리포트 생성" 단계이므로,
#    지금까지 모은 정보(1차 추천 + 맛집 목록)를 다시 Gemini에게 보내서
#    사람이 읽기 좋은 여행 리포트 글을 받아옵니다.
# ============================================================
def generate_report(date_str, travel_info, restaurants):
    """
    travel_info: get_travel_recommendation()의 결과 (도시/날씨/행사/이유)
    restaurants: search_restaurants()의 결과 (맛집 리스트, 0개일 수 있음)

    반환값: Markdown 형식의 문자열 (그대로 .md 파일로 저장하면 됨)
    """
    # 맛집 리스트를 Gemini가 이해하기 쉬운 텍스트로 미리 정리해둡니다.
    if restaurants:
        restaurant_text = "\n".join(
            f"- {r['name']} ({r['category']}) - {r['address']}"
            for r in restaurants
        )
    else:
        restaurant_text = "검색된 맛집 없음 (데이터 없음으로 표기할 것)"

    # 1차 추천 결과와 맛집 목록을 프롬프트에 그대로 넣어서
    # "이 정보들을 바탕으로 리포트를 써줘"라고 요청합니다.
    prompt = f"""
    아래 정보를 바탕으로 {date_str} 여행 리포트를 Markdown 형식으로 작성해줘.
    다른 설명 없이 Markdown 리포트 본문만 출력해.

    [1차 추천 정보]
    - 추천 도시: {travel_info.get("recommended_city") or "정보 없음"}
    - 추천 이유: {travel_info.get("reason") or "정보 없음"}
    - 날씨: {travel_info.get("weather") or "정보 없음"}
    - 행사/축제: {", ".join(travel_info.get("events") or []) or "정보 없음"}

    [맛집 목록]
    {restaurant_text}

    리포트에는 반드시 아래 항목이 모두 포함되어야 해:
    1. 추천 지역 + 추천 이유 요약
    2. 날씨 요약
    3. 행사/축제 목록
    4. 맛집 리스트 (맛집이 없으면 "데이터 없음"이라고 표시)
    5. 오전/오후/저녁으로 나눈 하루 일정 제안
    """

    try:
        client = get_genai_client()
        response = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt)
        report_text = response.text.strip()
        # 혹시 코드블록(```)으로 감싸서 응답했다면 제거합니다.
        report_text = report_text.replace("```markdown", "").replace("```", "").strip()
        return report_text

    except Exception as e:
        # Gemini 리포트 생성이 실패해도 프로그램이 죽지 않도록,
        # 최소한의 내용을 직접 조립해서 대신 반환합니다 (완전히 빈 결과보다는 낫습니다).
        print(f"[경고] 리포트 생성 중 Gemini 호출에 실패해 기본 형식으로 대체합니다: {e}")
        city = travel_info.get("recommended_city") or "추천 도시 정보 없음"
        return (
            f"# {date_str} 여행 추천 리포트\n\n"
            f"## 추천 지역\n{city}\n\n"
            f"## 맛집 추천\n{restaurant_text}\n"
        )


# ============================================================
# 5. 결과 저장하기 (results/ 폴더에 JSON + Markdown 저장)
# ============================================================
def save_results(date_str, travel_info, restaurants, report_text, errors):
    os.makedirs("results", exist_ok=True)  # results 폴더가 없으면 새로 만듭니다.

    # 5-1) 원본 데이터(JSON) 저장 -> 나중에 다시 확인하거나 디버깅할 때 유용합니다.
    raw_data = {
        "date": date_str,
        "travel_info": travel_info,
        "restaurants": restaurants,
        "errors": errors,  # 진행 중 발생한 오류들을 기록 (없으면 빈 리스트)
    }
    json_path = f"results/{date_str}_raw.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    # 5-2) 최종 리포트(Markdown) 저장
    report_path = f"results/{date_str}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return json_path, report_path


# ============================================================
# 6. 전체 실행 흐름 (프로그램의 "목차" 역할)
#    실제 실행 순서를 한눈에 볼 수 있도록 순서대로 함수를 호출합니다.
# ============================================================
def main():
    errors = []  # 진행 중 발생하는 오류 메시지를 모아두는 리스트 (요구사항: errors 섹션)

    print("[1/5] API 키를 확인합니다...")
    check_api_keys()

    print("[2/5] 입력값을 확인합니다...")
    date_str = parse_arguments()

    print(f"[3/5] {date_str} 기준으로 여행지를 추천받는 중...")
    travel_info = get_travel_recommendation(date_str)
    if not travel_info.get("recommended_city"):
        errors.append("Gemini 추천 결과를 받아오지 못했습니다.")

    city = travel_info.get("recommended_city")
    print(f"[4/5] {city}의 맛집을 검색하는 중...")
    restaurants = search_restaurants(city)
    if not restaurants:
        errors.append("맛집 검색 결과가 없거나 검색에 실패했습니다.")

    print("[5/5] 최종 리포트를 작성하고 저장하는 중...")
    report_text = generate_report(date_str, travel_info, restaurants)
    json_path, report_path = save_results(date_str, travel_info, restaurants, report_text, errors)

    print("\n완료되었습니다!")
    print(f"- 원본 데이터: {json_path}")
    print(f"- 여행 리포트: {report_path}")


# 이 파일을 직접 실행했을 때만 main()을 호출합니다.
# (다른 파일에서 이 파일을 import만 할 때는 자동 실행되지 않도록 하는 파이썬의 관례입니다.)
if __name__ == "__main__":
    main()