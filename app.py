import hashlib

# -*- coding: utf-8 -*-
# Stock 대시보드 (야후 파이낸스 기반)
# - 관심목록 여러 개 저장 / 표에 보일 항목 체크 / 신호등 색 표시 켜고 끄기

import os, io, json, time, uuid, datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Stock", page_icon="chart_with_upwards_trend",
                   layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2.5rem; max-width: 1500px;}
h1 {font-size: 1.55rem !important; margin-bottom: .2rem !important;}
h2 {font-size: 1.15rem !important; margin-top: .9rem !important;}
h3 {font-size: 1.0rem !important;}
div[data-testid="stMetricValue"] {font-size: 1.35rem;}
div[data-testid="stMetricLabel"] {font-size: .78rem; color:#555;}
.stTabs [data-baseweb="tab-list"] {gap: 2px; border-bottom: 1px solid #e3e3e3;}
.stTabs [data-baseweb="tab"] {padding: 8px 14px; font-size: .93rem;}
div[data-testid="stDataFrame"] {font-size: .86rem;}
hr {margin: .7rem 0 !important;}
/* 휴대폰: 오른쪽에 빈 띠를 남겨 화면 전체 스크롤을 잡을 수 있게 함 */
@media (max-width: 820px) {
  .block-container {padding-left: .7rem !important; padding-right: 2.6rem !important;}
}
/* ---- 주 버튼(조회하기·찾기 시작·분석하기)만 하늘색 ---- */
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background-color:#0ea5e9 !important; border-color:#0ea5e9 !important; color:#ffffff !important;}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  background-color:#0284c7 !important; border-color:#0284c7 !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================================================
# 종목 이름 사전
# ============================================================
NAME_MAP = {
    "AAPL": "애플", "MSFT": "마이크로소프트", "NVDA": "엔비디아", "GOOGL": "알파벳(구글)",
    "AMZN": "아마존", "META": "메타(페이스북)", "TSLA": "테슬라", "AVGO": "브로드컴",
    "AMD": "AMD", "INTC": "인텔", "QCOM": "퀄컴", "TXN": "텍사스인스트루먼트",
    "MU": "마이크론", "ASML": "ASML", "TSM": "TSMC", "ARM": "ARM",
    "ORCL": "오라클", "CRM": "세일즈포스", "ADBE": "어도비", "NOW": "서비스나우",
    "PLTR": "팔란티어", "SNOW": "스노우플레이크", "PANW": "팔로알토", "CRWD": "크라우드스트라이크",
    "NFLX": "넷플릭스", "DIS": "디즈니", "UBER": "우버", "ABNB": "에어비앤비",
    "SHOP": "쇼피파이", "SQ": "블록", "PYPL": "페이팔", "COIN": "코인베이스",
    "V": "비자", "MA": "마스터카드", "JPM": "JP모건", "BAC": "뱅크오브아메리카",
    "WFC": "웰스파고", "GS": "골드만삭스", "MS": "모건스탠리", "BRK-B": "버크셔해서웨이",
    "BLK": "블랙록", "SCHW": "찰스슈왑", "AXP": "아메리칸익스프레스",
    "LLY": "일라이릴리", "JNJ": "존슨앤존슨", "UNH": "유나이티드헬스", "ABBV": "애브비",
    "MRK": "머크", "PFE": "화이자", "TMO": "써모피셔", "ABT": "애보트",
    "AMGN": "암젠", "ISRG": "인튜이티브서지컬", "VRTX": "버텍스", "REGN": "리제네론",
    "NVO": "노보노디스크",
    "KO": "코카콜라", "PEP": "펩시코", "PG": "프록터앤갬블", "COST": "코스트코",
    "WMT": "월마트", "MCD": "맥도날드", "SBUX": "스타벅스", "NKE": "나이키",
    "HD": "홈디포", "LOW": "로우스", "TGT": "타겟", "CL": "콜게이트",
    "MDLZ": "몬델리즈", "PM": "필립모리스", "MO": "알트리아",
    "XOM": "엑슨모빌", "CVX": "셰브론", "COP": "코노코필립스", "SLB": "슐럼버거",
    "CAT": "캐터필라", "DE": "디어", "BA": "보잉", "GE": "GE에어로스페이스",
    "HON": "하니웰", "LMT": "록히드마틴", "RTX": "RTX", "UNP": "유니온퍼시픽",
    "UPS": "UPS", "FDX": "페덱스", "MMM": "3M",
    "LIN": "린데", "SHW": "셔윈윌리엄스", "NEE": "넥스트에라", "DUK": "듀크에너지",
    "SO": "서던컴퍼니", "T": "AT&T", "VZ": "버라이즌", "TMUS": "T모바일",
    "AMT": "아메리칸타워", "PLD": "프로로지스", "SPGI": "S&P글로벌",
    "SPY": "S&P500 ETF", "QQQ": "나스닥100 ETF", "VOO": "S&P500 ETF(뱅가드)",
    "SCHD": "SCHD 배당ETF", "DIA": "다우존스 ETF",
}
NAME2TICK = {}
for _t, _n in NAME_MAP.items():
    NAME2TICK[_n] = _t
    NAME2TICK[_n.replace(" ", "")] = _t
    NAME2TICK[_t] = _t

SCREEN_UNIVERSE = ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","AMD","QCOM",
    "TXN","MU","ORCL","CRM","ADBE","NOW","NFLX","DIS","UBER","V","MA","JPM","BAC","WFC",
    "GS","MS","BRK-B","BLK","AXP","LLY","JNJ","UNH","ABBV","MRK","PFE","TMO","ABT","AMGN",
    "ISRG","VRTX","KO","PEP","PG","COST","WMT","MCD","SBUX","NKE","HD","LOW","CL","MDLZ",
    "PM","XOM","CVX","COP","CAT","DE","HON","LMT","RTX","UNP","UPS","MMM","LIN","NEE",
    "T","VZ","TMUS","SPGI"]

# ============================================================
# 표 항목 정의
# ============================================================
COL_GROUPS = {
    "기본": ["티커", "현재가($)", "시가총액(B)", "데이터출처"],
    "밸류에이션": ["PER", "선행PER", "PBR", "PSR", "PEG"],
    "성장 전망": ["매출성장 올해(E,%)", "매출성장 내년(E,%)", "EPS성장 올해(E,%)",
                 "EPS성장 내년(E,%)", "EPS성장 5년(E,%)", "5년출처", "과거EPS성장(%)",
                 "추정상향(30일)", "추정하향(30일)"],
    "수익성·안정성": ["ROE(%)", "영업이익률(%)", "순이익률(%)", "부채비율(%)",
                     "순부채/EBITDA", "이자보상배율"],
    "재무 성장(실적)": ["영업이익성장 3년(연,%)", "영업이익률변화 1년(%p)",
                       "영업이익률변화 3년(%p)", "ROE변화(%p)"],
    "현금흐름": ["FCF(B)", "FCF수익률(%)", "FCF마진(%)", "현금전환율(%)"],
    "주주환원": ["배당수익률(%)", "자사주(B)", "자사주수익률(%)", "총주주환원율(%)", "주식수변동(%)"],
    "애널리스트": ["목표주가($)", "상승여력(%)", "애널리스트수", "매수의견", "보유의견", "매도의견",
                  "매수비율(%)", "실적발표일", "D-day"],
}
ALL_COLS = [c for g in COL_GROUPS.values() for c in g]

# 항목 세트(프리셋): 버튼 하나로 이 항목들만 표에 보이게 함 (티커는 항상 보임)
DEFAULT_PRESETS = {
    "밸류·성장": ["현재가($)", "시가총액(B)", "PER", "선행PER", "PEG",
                 "매출성장 올해(E,%)", "매출성장 내년(E,%)", "EPS성장 올해(E,%)",
                 "EPS성장 내년(E,%)", "EPS성장 5년(E,%)"],
    "애널리스트": ["현재가($)", "목표주가($)", "상승여력(%)", "애널리스트수", "매수의견",
                  "보유의견", "매도의견", "매수비율(%)", "추정상향(30일)", "추정하향(30일)",
                  "실적발표일", "D-day"],
    "재무": ["ROE(%)", "영업이익률(%)", "순이익률(%)", "부채비율(%)", "순부채/EBITDA",
            "이자보상배율", "FCF(B)", "FCF수익률(%)", "FCF마진(%)", "배당수익률(%)",
            "총주주환원율(%)"],
    "재무성장": ["영업이익성장 3년(연,%)", "영업이익률(%)", "영업이익률변화 1년(%p)",
               "영업이익률변화 3년(%p)", "ROE(%)", "ROE변화(%p)"],
}
# 나중에 새로 추가한 기본 세트: 이미 쓰던 사람 설정에도 한 번만 끼워 넣음
NEW_PRESETS = [("재무성장", "재무", "fin_growth_v1")]
# 재무성장 세트 구성을 바꾼 기록: 이미 저장된 재무성장 세트를 새 구성으로 한 번만 바꿔 줌
PRESET_UPDATES = [("재무성장", "fin_growth_v2")]

def table_height(n):
    """휴대폰 한 화면에 머리글 + 약 11줄이 보이는 높이"""
    return min(38 + 35 * max(int(n), 1), 422)

FMT = {
    "현재가($)": "{:,.2f}", "시가총액(B)": "{:,.1f}",
    "PER": "{:.1f}", "선행PER": "{:.1f}", "PBR": "{:.2f}", "PSR": "{:.2f}", "PEG": "{:.2f}",
    "매출성장 올해(E,%)": "{:+.1f}", "매출성장 내년(E,%)": "{:+.1f}",
    "EPS성장 올해(E,%)": "{:+.1f}", "EPS성장 내년(E,%)": "{:+.1f}",
    "EPS성장 5년(E,%)": "{:+.1f}", "과거EPS성장(%)": "{:+.1f}",
    "추정상향(30일)": "{:.0f}", "추정하향(30일)": "{:.0f}",
    "ROE(%)": "{:.1f}", "영업이익률(%)": "{:.1f}", "순이익률(%)": "{:.1f}",
    "부채비율(%)": "{:,.0f}", "순부채/EBITDA": "{:.2f}", "이자보상배율": "{:.1f}",
    "FCF(B)": "{:,.2f}", "FCF수익률(%)": "{:.2f}", "FCF마진(%)": "{:.1f}", "현금전환율(%)": "{:.0f}",
    "배당수익률(%)": "{:.2f}", "자사주(B)": "{:,.2f}", "자사주수익률(%)": "{:.2f}",
    "총주주환원율(%)": "{:.2f}", "주식수변동(%)": "{:+.2f}",
    "목표주가($)": "{:,.2f}", "상승여력(%)": "{:+.1f}", "애널리스트수": "{:.0f}",
    "매수의견": "{:.0f}", "보유의견": "{:.0f}", "매도의견": "{:.0f}", "매수비율(%)": "{:.0f}",
    "영업이익성장 3년(연,%)": "{:+.1f}",
    "영업이익률변화 1년(%p)": "{:+.1f}", "영업이익률변화 3년(%p)": "{:+.1f}", "ROE변화(%p)": "{:+.1f}",
}

# (방향, 좋음기준, 나쁨기준)  방향 high = 클수록 좋음
TH = {
    "PER": ("low", 18, 35), "선행PER": ("low", 18, 35), "PBR": ("low", 2.0, 6.0),
    "PSR": ("low", 3.0, 10.0), "PEG": ("low", 1.2, 2.5),
    "매출성장 올해(E,%)": ("high", 10, 0), "매출성장 내년(E,%)": ("high", 10, 0),
    "EPS성장 올해(E,%)": ("high", 10, 0), "EPS성장 내년(E,%)": ("high", 10, 0),
    "EPS성장 5년(E,%)": ("high", 12, 5), "과거EPS성장(%)": ("high", 10, 0),
    "추정상향(30일)": ("high", 3, None), "추정하향(30일)": ("low", 0, 3),
    "ROE(%)": ("high", 15, 8), "영업이익률(%)": ("high", 20, 5), "순이익률(%)": ("high", 15, 3),
    "부채비율(%)": ("low", 100, 200), "순부채/EBITDA": ("low", 2.0, 3.5),
    "이자보상배율": ("high", 8, 3),
    "FCF(B)": ("high", None, 0), "FCF수익률(%)": ("high", 5, 2),
    "FCF마진(%)": ("high", 15, 5), "현금전환율(%)": ("high", 80, 50),
    "배당수익률(%)": ("high", 3, None), "자사주수익률(%)": ("high", 3, None),
    "총주주환원율(%)": ("high", 4, 1), "주식수변동(%)": ("low", -1, 1),
    "상승여력(%)": ("high", 20, 0), "애널리스트수": ("high", 15, 3),
    "매수비율(%)": ("high", 70, 40),
    "영업이익성장 3년(연,%)": ("high", 10, 0),
    "영업이익률변화 1년(%p)": ("high", 1, -1), "영업이익률변화 3년(%p)": ("high", 2, -2),
    "ROE변화(%p)": ("high", 1, -1),
}

# ============================================================
# 설정 저장 / 복원
# ============================================================
SET_DIR = ".user_settings"
LS_KEY = "usstock_settings_v4"
UID_KEY = "usstock_uid_v4"

DEFAULT_SETTINGS = {
    "lists": {
        "내 관심종목": "애플, 마이크로소프트, 엔비디아, 일라이릴리, 코카콜라",
        "빅테크": "애플, 마이크로소프트, 엔비디아, 알파벳, 아마존, 메타, 브로드컴, 테슬라",
        "배당·안정": "코카콜라, 펩시코, 존슨앤존슨, 프록터앤갬블, 맥도날드, 홈디포, 비자, 유나이티드헬스",
    },
    "active": "내 관심종목",
    "groups": ["기본", "밸류에이션", "성장 전망"],
    "hide": [c for g, cs in COL_GROUPS.items()
             if g not in ("기본", "밸류에이션", "성장 전망") for c in cs],
    "color": False,
    "sort_col": "(정렬 안 함)",
    "sort_desc": True,
    "presets": DEFAULT_PRESETS,
    "memos": {},
    "migr": [m for _, _, m in NEW_PRESETS] + [m for _, m in PRESET_UPDATES],
}

def _get_ls():
    if "_ls" not in st.session_state:
        try:
            from streamlit_local_storage import LocalStorage
            st.session_state["_ls"] = LocalStorage()
        except Exception:
            st.session_state["_ls"] = None
    return st.session_state["_ls"]

def _ls_get(key):
    ls = _get_ls()
    if ls is None:
        return None
    try:
        v = ls.getItem(key)
        if isinstance(v, dict):
            v = v.get("value")
        return v
    except Exception:
        return None

def _ls_set(key, value):
    ls = _get_ls()
    if ls is None:
        return
    try:
        st.session_state["_ls_n"] = st.session_state.get("_ls_n", 0) + 1
        ls.setItem(key, value, key="ls_w_%s_%d" % (key, st.session_state["_ls_n"]))
    except Exception:
        pass

def _file_path(uid):
    return os.path.join(SET_DIR, "%s.json" % uid)

def _file_load(uid):
    try:
        with open(_file_path(uid), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _file_save(uid, data):
    try:
        os.makedirs(SET_DIR, exist_ok=True)
        with open(_file_path(uid), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def _clean(raw):
    s = dict(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return json.loads(json.dumps(s))
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    li = raw.get("lists")
    if isinstance(li, dict) and li:
        out["lists"] = {str(k): str(v) for k, v in li.items() if str(k).strip()}
    act = str(raw.get("active", ""))
    out["active"] = act if act in out["lists"] else list(out["lists"].keys())[0]
    gr = raw.get("groups")
    if isinstance(gr, list):
        gr = [g for g in gr if g in COL_GROUPS]
        if gr:
            out["groups"] = gr
    hd = raw.get("hide")
    if isinstance(hd, list):
        out["hide"] = [c for c in hd if c in ALL_COLS]
    out["color"] = bool(raw.get("color", False))
    sc = str(raw.get("sort_col", "(정렬 안 함)"))
    out["sort_col"] = sc if (sc in ALL_COLS or sc == "(정렬 안 함)") else "(정렬 안 함)"
    out["sort_desc"] = bool(raw.get("sort_desc", True))
    ps = raw.get("presets")
    if isinstance(ps, dict):
        clean_ps = {}
        for k, v in ps.items():
            k = str(k).strip()
            if k and isinstance(v, list):
                clean_ps[k] = [c for c in v if c in ALL_COLS]
        out["presets"] = clean_ps
    mm = raw.get("memos")
    if isinstance(mm, dict):
        out["memos"] = {str(k).strip().upper(): str(v) for k, v in mm.items()
                        if str(k).strip() and str(v).strip()}
    # 새로 추가된 기본 세트/항목을 예전 설정에 한 번만 반영
    mg = raw.get("migr")
    done = [str(x) for x in mg] if isinstance(mg, list) else []
    for _pname, _after, _mark in NEW_PRESETS:
        if _mark in done:
            continue
        done.append(_mark)
        if _pname not in out["presets"]:
            new_ps = {}
            for k, v in out["presets"].items():
                new_ps[k] = v
                if k == _after:
                    new_ps[_pname] = list(DEFAULT_PRESETS[_pname])
            if _pname not in new_ps:
                new_ps[_pname] = list(DEFAULT_PRESETS[_pname])
            out["presets"] = new_ps
        # 새 항목은 처음엔 표에서 숨겨 둠 (세트 버튼으로 켜면 됨)
        if isinstance(hd, list):
            out["hide"] = out["hide"] + [c for c in COL_GROUPS["재무 성장(실적)"]
                                         if c not in out["hide"]]
    for _pname, _mark in PRESET_UPDATES:
        if _mark in done:
            continue
        done.append(_mark)
        if _pname in out["presets"]:
            out["presets"][_pname] = list(DEFAULT_PRESETS[_pname])
        # 새로 생긴 칸은 처음엔 숨겨 둠 (재무성장 버튼으로 켜면 됨)
        if isinstance(hd, list):
            out["hide"] = out["hide"] + [c for c in ("영업이익률변화 1년(%p)", "영업이익률변화 3년(%p)")
                                         if c not in out["hide"]]
    out["migr"] = done
    return out

# ---------- 기기 간 공유 (GitHub 비밀 메모장 = Gist) ----------
# Streamlit 설정의 Secrets 에 GITHUB_TOKEN 을 넣어 두면 켜집니다. 없으면 예전 방식 그대로 동작합니다.
GIST_FILE = "usstock_settings.json"

def _gh_token():
    try:
        return str(st.secrets.get("GITHUB_TOKEN", "") or "").strip()
    except Exception:
        return ""

def _gh_headers(tok):
    return {"Authorization": "Bearer %s" % tok,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}

def _gist_id(tok):
    gid = st.session_state.get("_gist_id")
    if gid:
        return gid
    import requests
    try:
        for page in range(1, 4):
            r = requests.get("https://api.github.com/gists", headers=_gh_headers(tok),
                             params={"per_page": 100, "page": page}, timeout=10)
            if r.status_code != 200:
                st.session_state["_cloud_err"] = "목록 조회 실패 (코드 %s)" % r.status_code
                return None
            arr = r.json() or []
            for g in arr:
                if GIST_FILE in (g.get("files") or {}):
                    st.session_state["_gist_id"] = g.get("id")
                    return g.get("id")
            if len(arr) < 100:
                break
    except Exception as e:
        st.session_state["_cloud_err"] = "연결 실패 (%s)" % type(e).__name__
    return None

def _canon(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True)

def cloud_on():
    return bool(_gh_token())

def cloud_load():
    tok = _gh_token()
    if not tok:
        return None
    gid = _gist_id(tok)
    if not gid:
        return None
    import requests
    try:
        r = requests.get("https://api.github.com/gists/%s" % gid, headers=_gh_headers(tok), timeout=10)
        if r.status_code != 200:
            st.session_state["_cloud_err"] = "불러오기 실패 (코드 %s)" % r.status_code
            return None
        f = (r.json().get("files") or {}).get(GIST_FILE) or {}
        txt = f.get("content") or ""
        if f.get("truncated") and f.get("raw_url"):
            txt = requests.get(f["raw_url"], headers=_gh_headers(tok), timeout=10).text
        data = json.loads(txt) if txt else None
        if isinstance(data, dict):
            st.session_state["_cloud_err"] = ""
            return data
    except Exception as e:
        st.session_state["_cloud_err"] = "불러오기 실패 (%s)" % type(e).__name__
    return None

def cloud_save(data):
    tok = _gh_token()
    if not tok:
        return
    can = _canon(data)
    if can == st.session_state.get("_cloud_last"):
        return
    import requests
    body = {"files": {GIST_FILE: {"content": json.dumps(data, ensure_ascii=False, indent=1)}}}
    try:
        gid = _gist_id(tok)
        if gid:
            r = requests.patch("https://api.github.com/gists/%s" % gid, headers=_gh_headers(tok),
                               json=body, timeout=10)
        else:
            body["description"] = "미국주식 앱 설정 (자동 저장)"
            body["public"] = False
            r = requests.post("https://api.github.com/gists", headers=_gh_headers(tok),
                              json=body, timeout=10)
            if r.status_code in (200, 201):
                st.session_state["_gist_id"] = r.json().get("id")
        if r.status_code in (200, 201):
            st.session_state["_cloud_last"] = can
            st.session_state["_cloud_err"] = ""
        else:
            st.session_state["_cloud_err"] = "저장 실패 (코드 %s)" % r.status_code
    except Exception as e:
        st.session_state["_cloud_err"] = "저장 실패 (%s)" % type(e).__name__

def load_settings():
    if "S" in st.session_state:
        return st.session_state["S"]
    src = "기본값"
    uid = None
    try:
        uid = st.query_params.get("u")
    except Exception:
        uid = None
    if not uid:
        uid = _ls_get(UID_KEY)
    if not uid:
        uid = uuid.uuid4().hex[:12]
    raw = None
    craw = cloud_load()
    if craw is not None:
        raw = craw
        src = "클라우드 (모든 기기 공유)"
    js = _ls_get(LS_KEY) if raw is None else None
    if js:
        try:
            raw = json.loads(js) if isinstance(js, str) else js
            src = "휴대폰(브라우저) 저장소"
        except Exception:
            raw = None
    if raw is None:
        raw = _file_load(uid)
        if raw is not None:
            src = "서버 보관 파일"
    if raw is None:
        try:
            w = st.query_params.get("w")
        except Exception:
            w = None
        if w:
            raw = {"lists": {"내 관심종목": w}, "active": "내 관심종목"}
            src = "주소(URL) 기록"
    S = _clean(raw)
    st.session_state["S"] = S
    st.session_state["_uid"] = uid
    st.session_state["_src"] = src
    if craw is not None:
        st.session_state["_cloud_last"] = _canon(S)
    elif cloud_on() and src != "기본값":
        # 공유 저장소가 비어 있으면 이 기기의 설정을 처음 한 번 올려 둠
        st.session_state["_dirty"] = True
    return S

def mark_dirty():
    st.session_state["_dirty"] = True

def persist():
    if not st.session_state.get("_dirty"):
        return
    S = st.session_state.get("S")
    uid = st.session_state.get("_uid")
    if not S or not uid:
        return
    txt = json.dumps(S, ensure_ascii=False)
    _file_save(uid, S)
    cloud_save(S)
    _ls_set(UID_KEY, uid)
    _ls_set(LS_KEY, txt)
    try:
        cur = dict(st.query_params)
        w = S["lists"].get(S["active"], "")
        if cur.get("u") != uid or cur.get("w") != w:
            st.query_params["u"] = uid
            st.query_params["w"] = w
    except Exception:
        pass
    st.session_state["_dirty"] = False

# ============================================================
# 숫자 도우미
# ============================================================
def _f(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(",", "").strip()
            if x in ("", "-", "None", "nan"):
                return None
        v = float(x)
        if not np.isfinite(v):
            return None
        return v
    except Exception:
        return None

def _mul100(v):
    v = _f(v)
    return None if v is None else v * 100.0

def _div(a, b):
    a, b = _f(a), _f(b)
    if a is None or b is None or b == 0:
        return None
    return a / b

def _row_val(df, names, col=0):
    try:
        if df is None or getattr(df, "empty", True):
            return None
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna()
                if len(s) > col:
                    return _f(s.iloc[col])
    except Exception:
        return None
    return None

def _row_series(df, names):
    """재무제표에서 한 줄을 날짜 최신순으로 꺼냄 (빈 값 제외)"""
    try:
        if df is None or getattr(df, "empty", True):
            return None
        for n in names:
            if n in df.index:
                ser = pd.to_numeric(df.loc[n], errors="coerce").dropna()
                if len(ser):
                    ser.index = pd.to_datetime(ser.index)
                    return ser.sort_index(ascending=False)
    except Exception:
        return None
    return None

def _ago(ser, days_lo, days_hi):
    """맨 앞(최신) 값과, 그보다 days_lo~days_hi일 전의 값을 돌려줌"""
    if ser is None or len(ser) < 2:
        return None, None
    t0 = ser.index[0]
    for t, v in ser.iloc[1:].items():
        gap = (t0 - t).days
        if days_lo <= gap <= days_hi:
            return _f(ser.iloc[0]), _f(v)
    return None, None

def _growth(new, old):
    """성장률(%). 예전 값이 0 이하(적자)면 계산하지 않음"""
    if new is None or old is None or old <= 0:
        return None
    return (new / old - 1.0) * 100.0

def _ratio_change(num, den, days_lo=300, days_hi=430):
    """최근 연도 비율(%) - 비교 연도 비율(%)  (단위: %p). 기본은 1년 전, 1000~1200일이면 3년 전"""
    if num is None or den is None:
        return None
    both = [t for t in num.index if t in den.index]
    both = sorted(both, reverse=True)
    vals = []
    for t in both:
        dv = _f(den.loc[t])
        nv = _f(num.loc[t])
        if dv and dv > 0 and nv is not None:
            vals.append((t, nv / dv * 100.0))
    if len(vals) < 2:
        return None
    for t, v in vals[1:]:
        gap = (vals[0][0] - t).days
        if days_lo <= gap <= days_hi:
            return vals[0][1] - v
    return None

def _fin_growth(d, inc, bs, qinc):
    rev_s = _row_series(inc, ["Total Revenue", "Operating Revenue"])
    oi_s = _row_series(inc, ["Operating Income", "EBIT"])
    ni_s = _row_series(inc, ["Net Income", "Net Income Common Stockholders"])
    eq_s = _row_series(bs, ["Stockholders Equity", "Common Stock Equity",
                            "Total Equity Gross Minority Interest"])
    n3, o3 = _ago(oi_s, 1000, 1200)
    if n3 and o3 and n3 > 0 and o3 > 0:
        d["영업이익성장 3년(연,%)"] = ((n3 / o3) ** (1.0 / 3.0) - 1.0) * 100.0
    d["영업이익률변화 1년(%p)"] = _ratio_change(oi_s, rev_s, 300, 430)
    d["영업이익률변화 3년(%p)"] = _ratio_change(oi_s, rev_s, 1000, 1200)
    d["ROE변화(%p)"] = _ratio_change(ni_s, eq_s)

def _row_sum4(df, names):
    try:
        if df is None or getattr(df, "empty", True):
            return None
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna()
                if len(s) >= 4:
                    return _f(s.iloc[:4].sum())
                if len(s) >= 1:
                    return None
    except Exception:
        return None
    return None

def resolve(text):
    t = (text or "").strip()
    if not t:
        return None
    if t in NAME2TICK:
        return NAME2TICK[t]
    if t.replace(" ", "") in NAME2TICK:
        return NAME2TICK[t.replace(" ", "")]
    return t.upper().replace(".", "-")

def parse_list(text):
    out, seen = [], set()
    for part in (text or "").replace("\n", ",").split(","):
        sym = resolve(part)
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out

# ============================================================
# 데이터 받아오기
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_base(sym):
    d = {c: None for c in ALL_COLS}
    d["티커"] = sym
    d["종목명"] = NAME_MAP.get(sym, sym)
    src = []

    tk = yf.Ticker(sym)

    info = {}
    for i in range(2):
        try:
            info = tk.get_info() or {}
            if info:
                break
        except Exception:
            time.sleep(0.5)
    if not isinstance(info, dict):
        info = {}
    if len(info) > 12:
        src.append("야후상세")

    price = _f(info.get("currentPrice")) or _f(info.get("regularMarketPrice"))
    mcap = _f(info.get("marketCap"))
    shares = _f(info.get("sharesOutstanding")) or _f(info.get("impliedSharesOutstanding"))

    if price is None or mcap is None or shares is None:
        try:
            fi = tk.fast_info
            price = price or _f(fi.get("lastPrice") if hasattr(fi, "get") else getattr(fi, "last_price", None))
            mcap = mcap or _f(fi.get("marketCap") if hasattr(fi, "get") else getattr(fi, "market_cap", None))
            shares = shares or _f(fi.get("shares") if hasattr(fi, "get") else getattr(fi, "shares", None))
            if price is not None:
                src.append("빠른시세")
        except Exception:
            pass
    if price is None:
        try:
            h = tk.history(period="7d")
            if h is not None and not h.empty:
                price = _f(h["Close"].dropna().iloc[-1])
                src.append("시세표")
        except Exception:
            pass

    inc = bs = cf = qinc = qcf = None
    try:
        inc = tk.income_stmt
    except Exception:
        pass
    try:
        bs = tk.balance_sheet
    except Exception:
        pass
    try:
        cf = tk.cashflow
    except Exception:
        pass
    try:
        qinc = tk.quarterly_income_stmt
    except Exception:
        pass
    try:
        qcf = tk.quarterly_cashflow
    except Exception:
        pass
    if inc is not None and not getattr(inc, "empty", True):
        src.append("재무제표")

    rev = _row_sum4(qinc, ["Total Revenue", "Operating Revenue"]) or _row_val(inc, ["Total Revenue", "Operating Revenue"])
    ni = _row_sum4(qinc, ["Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations"]) \
         or _row_val(inc, ["Net Income", "Net Income Common Stockholders"])
    ebit = _row_sum4(qinc, ["Operating Income", "EBIT"]) or _row_val(inc, ["Operating Income", "EBIT"])
    ebitda = _f(info.get("ebitda")) or _row_sum4(qinc, ["EBITDA", "Normalized EBITDA"]) or _row_val(inc, ["EBITDA", "Normalized EBITDA"])
    intexp = _row_sum4(qinc, ["Interest Expense", "Interest Expense Non Operating"]) or _row_val(inc, ["Interest Expense"])
    equity = _row_val(bs, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
    debt = _row_val(bs, ["Total Debt"])
    if debt is None:
        sd = _row_val(bs, ["Current Debt And Capital Lease Obligation", "Current Debt", "Short Term Debt"]) or 0
        ld = _row_val(bs, ["Long Term Debt And Capital Lease Obligation", "Long Term Debt"]) or 0
        debt = (sd + ld) if (sd or ld) else None
    cash = _row_val(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
    sh_now = _row_val(bs, ["Ordinary Shares Number", "Share Issued"], 0)
    sh_prev = _row_val(bs, ["Ordinary Shares Number", "Share Issued"], 1)

    ocf = _row_sum4(qcf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]) \
          or _row_val(cf, ["Operating Cash Flow"])
    capex = _row_sum4(qcf, ["Capital Expenditure", "Purchase Of PPE"]) or _row_val(cf, ["Capital Expenditure"])
    fcf_rep = _row_sum4(qcf, ["Free Cash Flow"]) or _row_val(cf, ["Free Cash Flow"])
    buyback = _row_sum4(qcf, ["Repurchase Of Capital Stock", "Common Stock Payments"]) or _row_val(cf, ["Repurchase Of Capital Stock", "Common Stock Payments"])
    divpaid = _row_sum4(qcf, ["Cash Dividends Paid", "Common Stock Dividend Paid"]) or _row_val(cf, ["Cash Dividends Paid", "Common Stock Dividend Paid"])

    if mcap is None and price is not None and shares is not None:
        mcap = price * shares
    if shares is None and mcap is not None and price:
        shares = mcap / price

    d["현재가($)"] = price
    d["시가총액(B)"] = None if mcap is None else mcap / 1e9

    # 밸류에이션
    per = _f(info.get("trailingPE"))
    if per is None and price is not None and ni is not None and shares:
        eps = ni / shares
        per = price / eps if eps and eps > 0 else None
    d["PER"] = per
    d["선행PER"] = _f(info.get("forwardPE"))
    pbr = _f(info.get("priceToBook"))
    if pbr is None and mcap is not None and equity and equity > 0:
        pbr = mcap / equity
    d["PBR"] = pbr
    psr = _f(info.get("priceToSalesTrailing12Months"))
    if psr is None and mcap is not None and rev:
        psr = mcap / rev
    d["PSR"] = psr
    peg = _f(info.get("trailingPegRatio")) or _f(info.get("pegRatio"))
    d["PEG"] = peg

    # 성장 전망
    def _est(getter, idx, colnames):
        try:
            df = getter()
            if df is None or getattr(df, "empty", True) or idx not in df.index:
                return None
            row = df.loc[idx]
            for c in colnames:
                if c in df.columns:
                    v = _f(row[c])
                    if v is not None:
                        return v
            return None
        except Exception:
            return None

    rev_est = lambda: tk.revenue_estimate
    eps_est = lambda: tk.earnings_estimate
    grw_est = lambda: tk.growth_estimates

    d["매출성장 올해(E,%)"] = _mul100(_est(rev_est, "0y", ["growth"]))
    d["매출성장 내년(E,%)"] = _mul100(_est(rev_est, "+1y", ["growth"]))
    if d["매출성장 올해(E,%)"] is None:
        d["매출성장 올해(E,%)"] = _mul100(info.get("revenueGrowth"))
    d["EPS성장 올해(E,%)"] = _mul100(_est(eps_est, "0y", ["growth"]))
    d["EPS성장 내년(E,%)"] = _mul100(_est(eps_est, "+1y", ["growth"]))
    if d["EPS성장 올해(E,%)"] is None:
        d["EPS성장 올해(E,%)"] = _mul100(_est(grw_est, "0y", ["stock", "stockTrend", "growth"]))
    if d["EPS성장 내년(E,%)"] is None:
        d["EPS성장 내년(E,%)"] = _mul100(_est(grw_est, "+1y", ["stock", "stockTrend", "growth"]))

    g5 = _mul100(_est(grw_est, "+5y", ["stock", "stockTrend", "growth"]))
    if g5 is not None and abs(g5) > 0.001:
        d["EPS성장 5년(E,%)"] = g5
        d["5년출처"] = "야후직접"
    else:
        base = per if per and per > 0 else d["선행PER"]
        if peg and peg > 0 and base and base > 0:
            d["EPS성장 5년(E,%)"] = base / peg
            d["5년출처"] = "PEG역산"
        else:
            d["5년출처"] = "없음"

    # 과거 EPS 연평균 성장률
    try:
        eps_ser = None
        if inc is not None and not getattr(inc, "empty", True):
            for n in ["Diluted EPS", "Basic EPS"]:
                if n in inc.index:
                    eps_ser = inc.loc[n].dropna()
                    break
        if eps_ser is None and inc is not None and not getattr(inc, "empty", True) and shares:
            for n in ["Net Income", "Net Income Common Stockholders"]:
                if n in inc.index:
                    eps_ser = inc.loc[n].dropna() / shares
                    break
        if eps_ser is not None and len(eps_ser) >= 2:
            new = _f(eps_ser.iloc[0])
            old = _f(eps_ser.iloc[-1])
            yrs = len(eps_ser) - 1
            if new and old and new > 0 and old > 0 and yrs > 0:
                d["과거EPS성장(%)"] = ((new / old) ** (1.0 / yrs) - 1.0) * 100.0
    except Exception:
        pass

    # 추정치 상향/하향
    try:
        rv = tk.eps_revisions
        if rv is not None and not getattr(rv, "empty", True):
            idx = "+1y" if "+1y" in rv.index else ("0y" if "0y" in rv.index else None)
            if idx:
                r = rv.loc[idx]
                for c in ["upLast30days", "upLast30Days", "up"]:
                    if c in rv.columns:
                        d["추정상향(30일)"] = _f(r[c]); break
                for c in ["downLast30days", "downLast30Days", "down"]:
                    if c in rv.columns:
                        d["추정하향(30일)"] = _f(r[c]); break
    except Exception:
        pass

    # 수익성 / 안정성
    roe = _mul100(info.get("returnOnEquity"))
    if roe is None:
        roe = _mul100(_div(ni, equity))
    d["ROE(%)"] = roe
    d["영업이익률(%)"] = _mul100(info.get("operatingMargins")) or _mul100(_div(ebit, rev))
    d["순이익률(%)"] = _mul100(info.get("profitMargins")) or _mul100(_div(ni, rev))
    dr = _f(info.get("debtToEquity"))
    if dr is None:
        dr = _mul100(_div(debt, equity))
    d["부채비율(%)"] = dr
    if debt is not None and ebitda and ebitda > 0:
        d["순부채/EBITDA"] = (debt - (cash or 0)) / ebitda
    if ebit is not None and intexp and intexp > 0:
        d["이자보상배율"] = ebit / abs(intexp)

    # 재무 성장 (실제 실적 기준) - 이미 받은 재무제표로 계산, 추가 요청 없음
    try:
        _fin_growth(d, inc, bs, qinc)
    except Exception:
        pass

    # 현금흐름
    fcf = fcf_rep
    if fcf is None and ocf is not None:
        fcf = ocf - abs(capex or 0)
    d["FCF(B)"] = None if fcf is None else fcf / 1e9
    if fcf is not None and mcap:
        d["FCF수익률(%)"] = fcf / mcap * 100.0
    d["FCF마진(%)"] = _mul100(_div(fcf, rev))
    d["현금전환율(%)"] = _mul100(_div(fcf, ni)) if (ni and ni > 0) else None

    # 주주환원
    dy = _f(info.get("dividendYield"))
    if dy is not None and dy < 1:
        dy = dy * 100.0
    if dy is None and divpaid is not None and mcap:
        dy = abs(divpaid) / mcap * 100.0
    d["배당수익률(%)"] = dy
    bb = None if buyback is None else abs(buyback)
    d["자사주(B)"] = None if bb is None else bb / 1e9
    if bb is not None and mcap:
        d["자사주수익률(%)"] = bb / mcap * 100.0
    tot = 0.0
    any_t = False
    if bb is not None and mcap:
        tot += bb / mcap * 100.0; any_t = True
    if divpaid is not None and mcap:
        tot += abs(divpaid) / mcap * 100.0; any_t = True
    elif dy is not None:
        tot += dy; any_t = True
    d["총주주환원율(%)"] = tot if any_t else None
    if sh_now and sh_prev and sh_prev > 0:
        d["주식수변동(%)"] = (sh_now / sh_prev - 1.0) * 100.0

    # 애널리스트
    tgt = _f(info.get("targetMeanPrice"))
    nan_ = _f(info.get("numberOfAnalystOpinions"))
    if tgt is None:
        try:
            apt = tk.analyst_price_targets
            if isinstance(apt, dict):
                tgt = _f(apt.get("mean")) or _f(apt.get("median"))
        except Exception:
            pass
    d["목표주가($)"] = tgt
    d["애널리스트수"] = nan_
    if tgt and price:
        d["상승여력(%)"] = (tgt / price - 1.0) * 100.0

    edate = None
    try:
        cal = tk.calendar
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, (list, tuple)) and ed:
                edate = ed[0]
            elif ed is not None:
                edate = ed
    except Exception:
        pass
    if edate is None:
        try:
            ed = tk.get_earnings_dates(limit=8)
            if ed is not None and not ed.empty:
                today = pd.Timestamp.now(tz=ed.index.tz) if ed.index.tz else pd.Timestamp.now()
                fut = [x for x in ed.index if x >= today]
                if fut:
                    edate = min(fut)
        except Exception:
            pass
    if edate is not None:
        try:
            d["실적발표일"] = pd.Timestamp(edate).strftime("%Y-%m-%d")
        except Exception:
            d["실적발표일"] = str(edate)[:10]

    d["데이터출처"] = "+".join(sorted(set(src))) if src else "실패"
    return d

# ============================================================
# 성장 전망 · 애널리스트 의견 보충 (막히면 다른 경로로 다시 받기)
# ============================================================
def _rv(x):
    """야후 값이 {"raw": 1.2} 모양이어도 숫자로 꺼내기"""
    if isinstance(x, dict):
        x = x.get("raw")
    return _f(x)

def _qs_json(sym):
    """야후 '분석' 자료를 한 번에 받기 (성장 전망 + 의견 + 목표주가)"""
    try:
        from yfinance.data import YfData
    except Exception:
        return None
    url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/%s" % sym
    params = {"modules": "earningsTrend,recommendationTrend,financialData",
              "formatted": "false", "lang": "en-US", "region": "US",
              "corsDomain": "finance.yahoo.com"}
    try:
        js = YfData().get_raw_json(url, params=params)
    except Exception:
        return None
    try:
        res = ((js or {}).get("quoteSummary") or {}).get("result") or []
        return res[0] if res and isinstance(res[0], dict) else None
    except Exception:
        return None

def _extra_once(sym):
    """성공하면 dict(빈 dict 가능), 연결 자체가 실패하면 None"""
    out = {}
    ok = False
    q = _qs_json(sym)
    if q is not None:
        ok = True
        for t in ((q.get("earningsTrend") or {}).get("trend") or []):
            per_ = t.get("period")
            if per_ not in ("0y", "+1y"):
                continue
            yr = "올해" if per_ == "0y" else "내년"
            rg = _rv((t.get("revenueEstimate") or {}).get("growth"))
            eg = _rv((t.get("earningsEstimate") or {}).get("growth"))
            if eg is None:
                eg = _rv(t.get("growth"))
            if rg is not None:
                out["매출성장 %s(E,%%)" % yr] = rg * 100.0
            if eg is not None:
                out["EPS성장 %s(E,%%)" % yr] = eg * 100.0
            if per_ == "+1y" or "추정상향(30일)" not in out:
                rv = t.get("epsRevisions") or {}
                up = _rv(rv.get("upLast30days"))
                dn = _rv(rv.get("downLast30days"))
                if up is not None:
                    out["추정상향(30일)"] = up
                if dn is not None:
                    out["추정하향(30일)"] = dn
        for t in ((q.get("recommendationTrend") or {}).get("trend") or []):
            if t.get("period") == "0m":
                out["_rec"] = [_rv(t.get(k)) or 0 for k in
                               ("strongBuy", "buy", "hold", "sell", "strongSell")]
                break
        fd = q.get("financialData") or {}
        tg = _rv(fd.get("targetMeanPrice")) or _rv(fd.get("targetMedianPrice"))
        if tg:
            out["목표주가($)"] = tg
        na = _rv(fd.get("numberOfAnalystOpinions"))
        if na:
            out["애널리스트수"] = na
    # 다른 경로: yfinance 기본 기능으로 의견 수 받기
    if "_rec" not in out:
        tk = yf.Ticker(sym)
        for getter in (lambda: tk.recommendations, lambda: tk.recommendations_summary):
            try:
                rc = getter()
                if rc is None or getattr(rc, "empty", True):
                    continue
                ok = True
                row = rc[rc["period"] == "0m"].iloc[0] if "period" in rc.columns and (rc["period"] == "0m").any() else rc.iloc[0]
                out["_rec"] = [_f(row.get(k)) or 0 for k in
                               ("strongBuy", "buy", "hold", "sell", "strongSell")]
                break
            except Exception:
                continue
    return out if ok else None

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_extra(sym):
    for i in range(2):
        r = _extra_once(sym)
        if r is not None:
            return r
        time.sleep(0.8 + i)
    # 실패는 보관하지 않음 (다음 조회 때 다시 시도)
    raise RuntimeError("analysis blocked")

def fetch_one(sym):
    d = dict(_fetch_base(sym))
    if d.get("현재가($)") is None:
        return d
    try:
        ex = _fetch_extra(sym)
    except Exception:
        ex = {}
    for k, v in ex.items():
        if k.startswith("_") or v is None:
            continue
        if d.get(k) is None:
            d[k] = v
    rec = ex.get("_rec")
    if rec and sum(rec) > 0:
        buy = rec[0] + rec[1]
        hold = rec[2]
        sell = rec[3] + rec[4]
        tot = buy + hold + sell
        d["매수의견"] = buy
        d["보유의견"] = hold
        d["매도의견"] = sell
        d["매수비율(%)"] = buy / tot * 100.0 if tot else None
        if d.get("애널리스트수") is None:
            d["애널리스트수"] = tot
    if d.get("상승여력(%)") is None and d.get("목표주가($)") and d.get("현재가($)"):
        d["상승여력(%)"] = (d["목표주가($)"] / d["현재가($)"] - 1.0) * 100.0
    return d

def add_dday(rows):
    today = dt.date.today()
    for r in rows:
        s = r.get("실적발표일")
        if s:
            try:
                dd = (dt.date.fromisoformat(s) - today).days
                r["D-day"] = ("D-%d" % dd) if dd >= 0 else "지남"
            except Exception:
                r["D-day"] = None
    return rows

def fetch_many(syms, label="불러오는 중"):
    rows, bad = [], []
    bar = st.progress(0.0, text="%s... 0/%d" % (label, len(syms)))
    for i, s in enumerate(syms):
        try:
            r = fetch_one(s)
            if r.get("현재가($)") is None:
                bad.append(s)
            else:
                rows.append(r)
        except Exception:
            bad.append(s)
        bar.progress((i + 1) / max(len(syms), 1), text="%s... %d/%d" % (label, i + 1, len(syms)))
    bar.empty()
    return add_dday(rows), bad


# ============================================================
# 스크리닝 범위 넓히기 (S&P 500 / 러셀 3000)
# ============================================================
UNI_OPTS = ["대표 70개 (빠름)", "S&P 500", "S&P 500 + 러셀 3000"]
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
ISHARES = {
    "IVV": "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax"
           "?fileType=csv&fileName=IVV_holdings&dataType=fund",
    "IWV": "https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax"
           "?fileType=csv&fileName=IWV_holdings&dataType=fund",
}
SP500_BACKUP = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
US_EXCH = {"NMS", "NYQ", "NGM", "NCM", "ASE", "PCX", "BTS", "NAS", "NYS"}

def _norm_tk(t):
    t = str(t or "").strip().upper().replace(".", "-").replace("/", "-").replace(" ", "")
    return t if (t and t not in ("-", "NAN") and len(t) <= 7) else ""

@st.cache_data(ttl=86400, show_spinner=False)
def _ishares_list(code):
    """iShares ETF 보유종목표에서 (티커, 이름) 목록. 비중 큰 순."""
    import requests
    try:
        r = requests.get(ISHARES[code], headers=_UA, timeout=25)
        if r.status_code != 200:
            return []
        txt = r.text.replace("\ufeff", "")
        pos = txt.find("Ticker,")
        if pos < 0:
            return []
        df = pd.read_csv(io.StringIO(txt[pos:]), on_bad_lines="skip")
        if "Asset Class" in df.columns:
            df = df[df["Asset Class"].astype(str).str.strip() == "Equity"]
        out, seen = [], set()
        for t, n in zip(df["Ticker"], df.get("Name", df["Ticker"])):
            t = _norm_tk(t)
            if t and t not in seen:
                seen.add(t)
                out.append((t, str(n).title()))
        return out
    except Exception:
        return []

@st.cache_data(ttl=86400, show_spinner=False)
def _sp500_backup():
    try:
        df = pd.read_csv(SP500_BACKUP)
        out = []
        for t, n in zip(df["Symbol"], df.get("Security", df["Symbol"])):
            t = _norm_tk(t)
            if t:
                out.append((t, str(n)))
        return out
    except Exception:
        return []

def get_members(uni):
    """검사 범위에 들어갈 (티커, 이름) 목록"""
    sp = _ishares_list("IVV") or _sp500_backup()
    if uni == UNI_OPTS[1]:
        return sp
    r3 = _ishares_list("IWV")
    seen = set(t for t, _ in r3)
    return r3 + [x for x in sp if x[0] not in seen]

@st.cache_data(ttl=3600, show_spinner=False)
def yahoo_screen_us(min_mcap=1.0e8, limit=6000):
    """야후 일괄 검색: 미국 상장 주식 전체를 시가총액 큰 순으로 한 번에 받기"""
    try:
        from yfinance import EquityQuery
    except Exception:
        try:
            from yfinance.screener import EquityQuery
        except Exception:
            return None
    try:
        import inspect
        params = inspect.signature(yf.screen).parameters
        q = EquityQuery("and", [EquityQuery("eq", ["region", "us"]),
                                EquityQuery("gte", ["intradaymarketcap", min_mcap])])
    except Exception:
        return None
    quotes, off, size = [], 0, 250
    while off < limit:
        kw = {"size": size, "sortField": "intradaymarketcap", "sortAsc": False}
        if "offset" in params:
            kw["offset"] = off
        res = None
        for _i in range(3):
            try:
                res = yf.screen(q, **kw)
                break
            except Exception:
                time.sleep(1.0)
        if not res:
            break
        page = res.get("quotes") or []
        quotes.extend(page)
        if len(page) < size or "offset" not in params:
            break
        off += size
        time.sleep(0.3)
    rows, seen = [], set()
    for x in quotes:
        t = _norm_tk(x.get("symbol"))
        if not t or t in seen:
            continue
        if x.get("quoteType") not in (None, "EQUITY"):
            continue
        if x.get("exchange") and x.get("exchange") not in US_EXCH:
            continue
        seen.add(t)
        mc = _f(x.get("marketCap"))
        rows.append({"티커": t,
                     "이름": x.get("shortName") or x.get("longName") or t,
                     "시가총액(B)": mc / 1e9 if mc else None,
                     "PER": _f(x.get("trailingPE")),
                     "선행PER": _f(x.get("forwardPE")),
                     "PBR": _f(x.get("priceToBook"))})
    if not rows:
        return None
    return pd.DataFrame(rows)

def build_stage1(uni):
    """1차 후보표 (티커, 이름, 시가총액, PER, 선행PER, PBR) 와 방식 설명"""
    mem = get_members(uni)
    q = yahoo_screen_us()
    if q is not None and len(q):
        if mem:
            have = set(q["티커"])
            want = {}
            for t, n in mem:
                if t not in have and len(t) >= 4 and (t[:-1] + "-" + t[-1]) in have:
                    t = t[:-1] + "-" + t[-1]   # BRKB -> BRK-B
                want[t] = n
            q = q[q["티커"].isin(want.keys())].copy()
            how = "야후 일괄 검색 + 지수 구성종목"
        else:
            q = q.head(500 if uni == UNI_OPTS[1] else 3000).copy()
            how = "야후 일괄 검색 (시가총액 상위로 지수 근사)"
        q = q.sort_values("시가총액(B)", ascending=False, na_position="last")
        return q.reset_index(drop=True), how
    if mem:
        df = pd.DataFrame([{"티커": t, "이름": n, "시가총액(B)": None, "PER": None,
                            "선행PER": None, "PBR": None} for t, n in mem])
        return df, "지수 구성종목 목록 (야후 일괄 검색 실패 → 큰 기업 순)"
    df = pd.DataFrame([{"티커": t, "이름": NAME_MAP.get(t, t), "시가총액(B)": None, "PER": None,
                        "선행PER": None, "PBR": None} for t in SCREEN_UNIVERSE])
    return df, "목록을 못 받아 대표 70개로 대신함"

# ============================================================
# 표 그리기
# ============================================================
def style_table(df, color_on):
    fmt = {k: v for k, v in FMT.items() if k in df.columns}
    sty = df.style.format(fmt, na_rep="-")
    if not color_on:
        return sty

    def paint(d):
        out = pd.DataFrame("", index=d.index, columns=d.columns)
        for c in d.columns:
            rule = TH.get(c)
            if not rule:
                continue
            mode, good, bad = rule
            for i in d.index:
                v = _f(d.at[i, c])
                if v is None:
                    continue
                tag = None
                if mode == "high":
                    if good is not None and v >= good:
                        tag = "g"
                    elif bad is not None and v <= bad:
                        tag = "b"
                else:
                    if good is not None and v <= good:
                        tag = "g"
                    elif bad is not None and v >= bad:
                        tag = "b"
                if tag == "g":
                    out.at[i, c] = "background-color:#e3f4e6;color:#14532d"
                elif tag == "b":
                    out.at[i, c] = "background-color:#fdeaea;color:#7f1d1d"
        return out

    return sty.apply(paint, axis=None)


def show_table(view, color_on, height):
    """티커 칸을 왼쪽에 고정해서 표를 그림 (좌우로 밀어도 티커가 보임)"""
    view = view.copy()
    if "종목명" in view.columns:
        view = view.drop(columns=["종목명"])
    if "티커" in view.columns:
        view = view[["티커"] + [c for c in view.columns if c != "티커"]]
    for c in view.columns:
        if c in FMT:
            view[c] = pd.to_numeric(view[c], errors="coerce")
        elif c in ("5년출처", "실적발표일", "D-day", "데이터출처"):
            view[c] = view[c].where(view[c].notna(), "-")
    try:
        cfg = {"티커": st.column_config.TextColumn("티커", pinned=True, width="small")}
        st.dataframe(style_table(view, color_on), use_container_width=True,
                     hide_index=True, height=height, column_config=cfg)
        return
    except TypeError:
        pass
    # 옛 버전 스트림릿: 티커를 맨 왼쪽 고정칸(인덱스)으로 옮겨서 고정
    v2 = view.copy()
    if "티커" in v2.columns:
        v2.index = pd.Index(v2["티커"].astype(str).tolist(), name="티커")
        v2 = v2.drop(columns=["티커"])
    st.dataframe(style_table(v2, color_on), use_container_width=True, height=height)


def _wkey(base, seq):
    return "%s_%d" % (base, abs(hash(tuple(seq))) % 100000000)

# ============================================================
# 화면 시작
# ============================================================
S = load_settings()

st.title("Stock")
st.caption("한글 이름(애플)이나 티커(AAPL) 아무거나 입력하면 됩니다. 시세는 야후 파이낸스 기준 15~20분 지연.")

# ---------------- 사이드바 ----------------
with st.sidebar:
    st.markdown("### 설정")
    st.caption("불러온 곳: %s" % st.session_state.get("_src", "기본값"))
    if cloud_on():
        st.caption("기기 간 공유: 켜짐 (휴대폰·패드·PC가 같은 목록 사용)")
        if st.session_state.get("_cloud_err"):
            st.caption("공유 오류: %s" % st.session_state["_cloud_err"])
        if st.button("다른 기기에서 바꾼 내용 불러오기", use_container_width=True):
            _raw = cloud_load()
            if _raw is not None:
                st.session_state["S"] = _clean(_raw)
                st.session_state["_cloud_last"] = _canon(st.session_state["S"])
                for _k in list(st.session_state.keys()):
                    if str(_k).startswith(("cbcol_", "ta_", "ren_", "pset_", "memo_")) or _k in ("pick_list", "tg_color", "preset_pick"):
                        del st.session_state[_k]
                st.rerun()
            else:
                st.warning("불러오지 못했습니다.")
    else:
        st.caption("기기 간 공유: 꺼짐 (GITHUB_TOKEN 설정 필요)")

    with st.expander("용어 설명", expanded=False):
        st.markdown("""
- **PER** 주가 ÷ 1주당 순이익. 낮으면 싸다는 뜻
- **선행PER** 내년 예상 이익 기준 PER
- **PBR** 주가 ÷ 1주당 순자산
- **PSR** 시가총액 ÷ 매출
- **PEG** PER ÷ 5년 성장률. 1 아래면 성장 대비 저평가
- **ROE** 자기자본으로 낸 이익률. 15% 이상이면 우수
- **부채비율** 부채 ÷ 자기자본. 100% 이하면 무난
- **순부채/EBITDA** 빚 갚는 데 걸리는 햇수. 2배 이하 양호
- **이자보상배율** 영업이익 ÷ 이자. 8배 이상 안전
- **FCF** 벌어서 쓰고 남은 진짜 현금
- **FCF수익률** FCF ÷ 시가총액. 국채금리보다 높으면 매력
- **FCF마진** FCF ÷ 매출
- **현금전환율** FCF ÷ 순이익. 80% 이상이면 이익이 진짜 현금
- **총주주환원율** (자사주+배당) ÷ 시가총액. 3~5% 건전
- **주식수변동** 마이너스여야 내 지분이 늘어남
- **매수/보유/매도의견** 애널리스트 의견별 인원 (이번 달 기준)
- **매수비율** 전체 의견 중 매수 비율. 70% 이상이면 강한 매수 분위기
- **영업이익성장 3년(연)** 3년 동안 영업이익이 해마다 평균 몇 %씩 늘었는지 (예상치 아님, 실제 실적)
- **영업이익률변화 1년(%p)** 영업이익률이 1년 전보다 몇 %포인트 올랐는지. 플러스면 장사가 더 남는 쪽으로 좋아지는 중
- **영업이익률변화 3년(%p)** 영업이익률이 3년 전보다 몇 %포인트 올랐는지. 긴 흐름을 볼 때
- **ROE변화(%p)** ROE가 전년보다 몇 %포인트 올랐는지
- 예전 값이 적자(0 이하)였으면 성장률을 계산할 수 없어 빈칸으로 나옵니다
        """)

    with st.expander("신호등 색 기준", expanded=False):
        st.markdown("""
초록은 좋은 편, 빨강은 나쁜 편, 색 없음은 보통입니다.
**업종을 감안하지 않은 일반 기준**이니 참고용으로만 보세요.
성장주는 PER이 빨강이어도 정상일 수 있습니다.
        """)
        rows = []
        for c in ALL_COLS:
            if c in TH:
                mode, g, b = TH[c]
                rows.append({"항목": c,
                             "초록(좋음)": ("%s 이상" % g) if mode == "high" and g is not None else (("%s 이하" % g) if g is not None else "-"),
                             "빨강(나쁨)": ("%s 이하" % b) if mode == "high" and b is not None else (("%s 이상" % b) if b is not None else "-")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.expander("설정 백업 / 복원", expanded=False):
        st.caption("휴대폰을 바꾸거나 저장이 풀렸을 때 쓰세요.")
        st.download_button("설정 내려받기", data=json.dumps(S, ensure_ascii=False, indent=1),
                           file_name="stock_settings.json", mime="application/json",
                           use_container_width=True)
        up = st.file_uploader("설정 파일 올리기", type=["json"], label_visibility="collapsed")
        if up is not None:
            try:
                st.session_state["S"] = _clean(json.loads(up.read().decode("utf-8")))
                mark_dirty()
                st.success("복원했습니다.")
                st.rerun()
            except Exception as e:
                st.error("복원 실패: %s" % e)

    with st.expander("연결 진단", expanded=False):
        if st.button("애플(AAPL)로 검사", use_container_width=True):
            msgs = []
            try:
                h = yf.Ticker("AAPL").history(period="5d")
                msgs.append("시세: 성공 (%.2f 달러)" % float(h["Close"].dropna().iloc[-1]) if h is not None and not h.empty else "시세: 빈 값")
            except Exception as e:
                msgs.append("시세: 실패 - %s" % e)
            try:
                inf = yf.Ticker("AAPL").get_info() or {}
                msgs.append("상세정보: 성공 (항목 %d개)" % len(inf) if len(inf) > 12 else "상세정보: 차단됨 (항목 %d개)" % len(inf))
            except Exception as e:
                msgs.append("상세정보: 실패 - %s" % e)
            try:
                fin = yf.Ticker("AAPL").income_stmt
                msgs.append("재무제표: 성공" if fin is not None and not fin.empty else "재무제표: 빈 값")
            except Exception as e:
                msgs.append("재무제표: 실패 - %s" % e)
            try:
                ex = _extra_once("AAPL")
                if ex is None:
                    msgs.append("성장전망·의견: 차단됨")
                else:
                    msgs.append("성장전망·의견: 성공 (항목 %d개)" % len(ex))
            except Exception as e:
                msgs.append("성장전망·의견: 실패 - %s" % e)
            for m in msgs:
                st.write("- " + m)

    st.caption("받아온 값은 1시간 동안 보관했다가 다시 씁니다. 최신 시세를 보려면 아래 버튼을 누르세요.")
    if st.button("데이터 새로 받기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------- 탭 ----------------
t1, t2, t3, t4, t5 = st.tabs(["① 관심목록 비교", "② 종목 자세히 보기", "③ 조건으로 찾기", "④ 다른 사이트 확인", "⑤ 메모"])

# ============================================================
# 탭 1
# ============================================================
with t1:
    names = list(S["lists"].keys())
    if S["active"] not in names:
        S["active"] = names[0]

    def _on_pick():
        S["active"] = st.session_state["pick_list"]
        mark_dirty()
    st.selectbox("보고 있는 목록", names, index=names.index(S["active"]),
                 key="pick_list", on_change=_on_pick)

    active = S["active"]

    def _on_text():
        S["lists"][S["active"]] = st.session_state["ta_%s" % S["active"]]
        mark_dirty()
    st.text_area("종목 (쉼표로 구분)", value=S["lists"][active],
                 key="ta_%s" % active, height=80, on_change=_on_text)

    with st.expander("목록 관리 (새로 만들기 · 이름 바꾸기 · 삭제)", expanded=False):
        m1, m2, m3 = st.columns(3)
        with m1:
            nn = st.text_input("새 목록 이름", key="new_name", placeholder="예: 반도체")
            if st.button("새로 만들기", use_container_width=True):
                nn = (nn or "").strip()
                if not nn:
                    st.warning("이름을 입력하세요.")
                elif nn in S["lists"]:
                    st.warning("같은 이름이 있습니다.")
                else:
                    S["lists"][nn] = ""
                    S["active"] = nn
                    mark_dirty()
                    st.rerun()
        with m2:
            rn = st.text_input("이름 바꾸기", value=active, key="ren_%s" % active)
            if st.button("이름 바꾸기", use_container_width=True):
                rn = (rn or "").strip()
                if not rn:
                    st.warning("이름을 입력하세요.")
                elif rn != active and rn in S["lists"]:
                    st.warning("같은 이름이 있습니다.")
                elif rn != active:
                    S["lists"] = {(rn if k == active else k): v for k, v in S["lists"].items()}
                    S["active"] = rn
                    mark_dirty()
                    st.rerun()
        with m3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("이 목록 삭제", use_container_width=True):
                if len(S["lists"]) <= 1:
                    st.warning("목록이 하나뿐이라 삭제할 수 없습니다.")
                else:
                    S["lists"].pop(active, None)
                    S["active"] = list(S["lists"].keys())[0]
                    mark_dirty()
                    st.rerun()
        st.divider()
        if st.button("처음 상태로 되돌리기 (목록 전부 초기화)"):
            st.session_state["S"] = json.loads(json.dumps(DEFAULT_SETTINGS))
            mark_dirty()
            st.rerun()

    st.divider()

    # ---- 표에 보일 항목 고르기 (체크로 켜고 끄기) ----
    FIXED_COLS = ["티커"]
    if not isinstance(S.get("presets"), dict):
        S["presets"] = json.loads(json.dumps(DEFAULT_PRESETS))

    def _cb_key(c):
        return "cbcol_%d" % ALL_COLS.index(c)

    for _c in ALL_COLS:
        _k = _cb_key(_c)
        if _k not in st.session_state:
            st.session_state[_k] = (_c not in S["hide"])

    def _cur_show():
        return [c for c in ALL_COLS if c in FIXED_COLS or c not in S["hide"]]

    def _match_preset():
        cur = set(_cur_show()) - set(FIXED_COLS)
        for _n, _cs in S["presets"].items():
            if set(_cs) - set(FIXED_COLS) == cur:
                return _n
        return None

    def _apply_hide(hide_list):
        hs = set(hide_list)
        S["hide"] = [c for c in ALL_COLS if c in hs and c not in FIXED_COLS]
        for c in ALL_COLS:
            st.session_state[_cb_key(c)] = (c not in S["hide"])
        st.session_state["preset_pick"] = _match_preset()
        mark_dirty()

    def _apply_preset(name):
        cols = set(S["presets"].get(name, []))
        _apply_hide([c for c in ALL_COLS if c not in cols])

    def _on_col_cb(col, key):
        hs = set(S["hide"])
        if st.session_state.get(key, True):
            hs.discard(col)
        else:
            hs.add(col)
        S["hide"] = [c for c in ALL_COLS if c in hs and c not in FIXED_COLS]
        st.session_state["preset_pick"] = _match_preset()
        mark_dirty()

    def _on_preset_pick():
        name = st.session_state.get("preset_pick")
        if name == "(직접 고름)":
            name = None
        if name and name in S["presets"]:
            _apply_preset(name)

    def _on_all_on():
        _apply_hide([])

    def _on_basic():
        _apply_hide([c for c in ALL_COLS if c not in COL_GROUPS["기본"]])

    def _on_save_preset():
        name = str(st.session_state.get("pset_name", "")).strip()
        if not name:
            st.session_state["_pset_msg"] = "세트 이름을 적어 주세요."
            return
        S["presets"][name] = [c for c in _cur_show() if c not in FIXED_COLS]
        st.session_state["pset_name"] = ""
        st.session_state["preset_pick"] = name
        st.session_state["_pset_msg"] = "'%s' 세트를 저장했습니다." % name
        mark_dirty()

    def _on_del_preset():
        name = st.session_state.get("pset_del")
        if name and name in S["presets"]:
            S["presets"].pop(name, None)
            st.session_state.pop("pset_del", None)
            st.session_state["preset_pick"] = _match_preset()
            st.session_state["_pset_msg"] = "'%s' 세트를 지웠습니다." % name
            mark_dirty()

    if "preset_pick" not in st.session_state or (
            st.session_state.get("preset_pick") not in S["presets"]
            and st.session_state.get("preset_pick") is not None):
        st.session_state["preset_pick"] = _match_preset()

    show_cols = [c for c in ALL_COLS
                 if c in FIXED_COLS or st.session_state.get(_cb_key(c), c not in S["hide"])]

    # ---- 항목 세트 버튼 한 줄 ----
    _pnames = list(S["presets"].keys())
    if _pnames:
        if hasattr(st, "pills"):
            st.pills("항목 세트", _pnames, key="preset_pick", on_change=_on_preset_pick,
                     label_visibility="collapsed")
        else:
            _opts = ["(직접 고름)"] + _pnames
            if st.session_state.get("preset_pick") not in _opts:
                st.session_state["preset_pick"] = "(직접 고름)"
            st.radio("항목 세트", _opts, key="preset_pick", on_change=_on_preset_pick,
                     horizontal=True, label_visibility="collapsed")

    o1, o2 = st.columns([1.4, 1])
    with o1:
        with st.popover("표에 보일 항목 (%d개)" % len(show_cols), use_container_width=True):
            b1, b2 = st.columns(2)
            with b1:
                st.button("전체 켜기", use_container_width=True, on_click=_on_all_on)
            with b2:
                st.button("기본만 보기", use_container_width=True, on_click=_on_basic)
            for _g, _cols in COL_GROUPS.items():
                st.markdown("**%s**" % _g)
                for _c in _cols:
                    if _c in FIXED_COLS:
                        continue
                    _k = _cb_key(_c)
                    st.checkbox(_c, key=_k, on_change=_on_col_cb, args=(_c, _k))
            st.divider()
            st.markdown("**지금 체크 상태를 세트로 저장**")
            st.text_input("세트 이름", key="pset_name", placeholder="예: 내 단골 항목")
            st.button("세트로 저장", use_container_width=True, on_click=_on_save_preset,
                      help="같은 이름이 있으면 지금 상태로 덮어씁니다.")
            if _pnames:
                st.markdown("**세트 지우기**")
                st.selectbox("지울 세트", _pnames, key="pset_del")
                st.button("선택한 세트 지우기", use_container_width=True, on_click=_on_del_preset)
            if st.session_state.get("_pset_msg"):
                st.caption(st.session_state.pop("_pset_msg"))
    with o2:
        def _on_color():
            S["color"] = st.session_state["tg_color"]
            mark_dirty()
        st.toggle("신호등 색 표시", value=S["color"], key="tg_color", on_change=_on_color,
                  help="초록은 좋은 편, 빨강은 나쁜 편입니다. 기준은 사이드바에서 볼 수 있습니다.")

    run = st.button("조회하기", type="primary", use_container_width=True)

    syms = parse_list(S["lists"][active])

    if run:
        if not syms:
            st.session_state["t1_rows"] = []
            st.session_state["t1_bad"] = []
            st.warning("종목을 입력하세요.")
        else:
            _rows, _bad = fetch_many(syms, "종목 정보 불러오는 중")
            st.session_state["t1_rows"] = _rows
            st.session_state["t1_bad"] = _bad

    rows = st.session_state.get("t1_rows") or []
    bad = st.session_state.get("t1_bad") or []

    if rows:
        if bad:
            st.warning("못 불러온 종목: %s" % ", ".join(bad))
        df = pd.DataFrame(rows)
        for c in ALL_COLS:
            if c not in df.columns:
                df[c] = None
        view = df[[c for c in show_cols if c in df.columns]].copy()
        view = view.reset_index(drop=True)
        show_table(view, S["color"], table_height(len(view)))
        st.caption("표의 머리글을 누르면 그 항목 기준으로 정렬됩니다. - 표시는 야후에 값이 없는 항목입니다.")

        if "FCF수익률(%)" in df.columns or "총주주환원율(%)" in df.columns:
            g1, g2 = st.columns(2)
            with g1:
                sub = df[["티커", "FCF수익률(%)"]].dropna()
                if len(sub):
                    st.markdown("**FCF 수익률 (%) — 5% 이상이면 매력적**")
                    st.bar_chart(sub.set_index("티커"), height=230)
            with g2:
                sub = df[["티커", "총주주환원율(%)"]].dropna()
                if len(sub):
                    st.markdown("**총주주환원율 (%) — 3~5%면 건전**")
                    st.bar_chart(sub.set_index("티커"), height=230)
    elif run:
        st.error("가져온 데이터가 없습니다. 사이드바의 연결 진단을 눌러보세요.")

# ============================================================
# 탭 2
# ============================================================
with t2:
    st.markdown("### 종목 하나 자세히 보기")
    q = st.text_input("종목", value="애플", key="detail_q")
    if st.button("분석하기", type="primary"):
        st.session_state["t2_sym"] = resolve(q)
    sym = st.session_state.get("t2_sym")
    if sym:
        with st.spinner("불러오는 중..."):
            d = add_dday([fetch_one(sym)])[0]
        if d.get("현재가($)") is None:
            st.error("데이터를 못 가져왔습니다. 티커를 확인해 주세요.")
        else:
            st.markdown("## %s (%s)" % (d["종목명"], d["티커"]))
            k = st.columns(5)
            k[0].metric("현재가", "-" if d["현재가($)"] is None else "$%.2f" % d["현재가($)"])
            k[1].metric("시가총액", "-" if d["시가총액(B)"] is None else "%.1fB" % d["시가총액(B)"])
            k[2].metric("PER", "-" if d["PER"] is None else "%.1f" % d["PER"])
            k[3].metric("ROE", "-" if d["ROE(%)"] is None else "%.1f%%" % d["ROE(%)"])
            k[4].metric("FCF수익률", "-" if d["FCF수익률(%)"] is None else "%.2f%%" % d["FCF수익률(%)"])

            k2 = st.columns(5)
            k2[0].metric("PBR", "-" if d["PBR"] is None else "%.2f" % d["PBR"])
            k2[1].metric("PEG", "-" if d["PEG"] is None else "%.2f" % d["PEG"])
            k2[2].metric("부채비율", "-" if d["부채비율(%)"] is None else "%.0f%%" % d["부채비율(%)"])
            k2[3].metric("총주주환원율", "-" if d["총주주환원율(%)"] is None else "%.2f%%" % d["총주주환원율(%)"])
            k2[4].metric("실적발표", (d.get("실적발표일") or "-") + ("" if not d.get("D-day") else " (%s)" % d["D-day"]))

            if d.get("매수의견") is not None:
                st.caption("애널리스트 의견: 매수 %d · 보유 %d · 매도 %d (매수비율 %.0f%%)" % (
                    d["매수의견"], d["보유의견"] or 0, d["매도의견"] or 0, d.get("매수비율(%)") or 0))
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**성장 전망 (애널리스트 예상)**")
                g = pd.DataFrame([
                    {"구분": "매출 올해(E)", "값(%)": d["매출성장 올해(E,%)"]},
                    {"구분": "매출 내년(E)", "값(%)": d["매출성장 내년(E,%)"]},
                    {"구분": "EPS 올해(E)", "값(%)": d["EPS성장 올해(E,%)"]},
                    {"구분": "EPS 내년(E)", "값(%)": d["EPS성장 내년(E,%)"]},
                    {"구분": "EPS 5년(E) [%s]" % (d["5년출처"] or "-"), "값(%)": d["EPS성장 5년(E,%)"]},
                    {"구분": "과거 EPS 연평균(실적)", "값(%)": d["과거EPS성장(%)"]},
                ])
                st.dataframe(g.style.format({"값(%)": "{:+.1f}"}, na_rep="-"),
                             hide_index=True, use_container_width=True)
                st.caption("5년 전망이 과거 실적보다 훨씬 높으면 낙관적으로 잡힌 것일 수 있습니다.")
            with cc2:
                st.markdown("**현금흐름 · 주주환원**")
                g2 = pd.DataFrame([
                    {"구분": "FCF (10억$)", "값": d["FCF(B)"]},
                    {"구분": "FCF 마진(%)", "값": d["FCF마진(%)"]},
                    {"구분": "현금전환율(%)", "값": d["현금전환율(%)"]},
                    {"구분": "자사주 매입 (10억$)", "값": d["자사주(B)"]},
                    {"구분": "배당수익률(%)", "값": d["배당수익률(%)"]},
                    {"구분": "주식수 변동(%)", "값": d["주식수변동(%)"]},
                ])
                st.dataframe(g2.style.format({"값": "{:,.2f}"}, na_rep="-"),
                             hide_index=True, use_container_width=True)
                st.caption("주식수 변동이 마이너스여야 내 지분이 실제로 늘어납니다.")

            st.markdown("**재무 성장 (실제 실적, 사업성이 좋아지는지)**")
            g3 = pd.DataFrame([
                {"구분": "영업이익 성장 3년 연평균(%)", "값": d.get("영업이익성장 3년(연,%)")},
                {"구분": "영업이익률 변화 1년(%p)", "값": d.get("영업이익률변화 1년(%p)")},
                {"구분": "영업이익률 변화 3년(%p)", "값": d.get("영업이익률변화 3년(%p)")},
                {"구분": "ROE 변화(%p)", "값": d.get("ROE변화(%p)")},
            ])
            st.dataframe(g3.style.format({"값": "{:+.1f}"}, na_rep="-"),
                         hide_index=True, use_container_width=True)

            st.divider()
            try:
                tk = yf.Ticker(sym)
                inc = tk.income_stmt
                if inc is not None and not inc.empty:
                    pick = {"매출": ["Total Revenue"], "영업이익": ["Operating Income", "EBIT"],
                            "순이익": ["Net Income", "Net Income Common Stockholders"]}
                    data = {}
                    for label, keys in pick.items():
                        for kk in keys:
                            if kk in inc.index:
                                data[label] = inc.loc[kk].dropna() / 1e9
                                break
                    if data:
                        fin = pd.DataFrame(data)
                        fin.index = [str(x)[:4] for x in fin.index]
                        fin = fin.iloc[::-1]
                        st.markdown("**연간 실적 (단위: 10억 달러)**")
                        st.bar_chart(fin, height=280)
            except Exception as e:
                st.caption("실적 그래프를 못 그렸습니다: %s" % e)

            try:
                h = yf.Ticker(sym).history(period="2y")
                if h is not None and not h.empty:
                    st.markdown("**최근 2년 주가 ($)**")
                    st.line_chart(h["Close"], height=260)
            except Exception:
                pass

# ============================================================
# 탭 3
# ============================================================
with t3:
    st.markdown("### 조건으로 종목 찾기")
    u1, u2 = st.columns([2, 1])
    with u1:
        uni = st.radio("검사 범위", UNI_OPTS, horizontal=True, key="sc_uni")
    with u2:
        depth = st.select_slider("자세히 검사할 최대 종목 수", [50, 100, 150, 200, 300], value=100,
                                 key="sc_depth", disabled=(uni == UNI_OPTS[0]))
    if uni == UNI_OPTS[0]:
        st.caption("미국 대표 %d개 종목을 검사합니다. 처음 한 번은 1~2분 걸립니다. "
                   "슬라이더를 0으로 두면 그 조건은 무시합니다." % len(SCREEN_UNIVERSE))
    else:
        st.caption("1차로 전체 종목을 PER·선행PER·PBR·시가총액으로 한 번에 거른 뒤, 남은 종목 중 "
                   "시가총액 큰 순으로 최대 %d개를 자세히 검사합니다 (약 %d~%d분). "
                   "검사 중에는 휴대폰 화면을 켜 두세요." % (depth, max(1, depth // 50), max(2, depth // 30)))

    # (저장이름, 처음값, 화면에 쓸 이름, 비교할 표 항목, ge=이상 / le=이하)
    SCR = [
        ("sc_per",  40,  "PER 최대",              "PER",              "le"),
        ("sc_peg",  0.0, "PEG 최대",              "PEG",              "le"),
        ("sc_roe",  10,  "ROE 최소 (%)",          "ROE(%)",           "ge"),
        ("sc_mcap", 0,   "시가총액 최소 (B)",      "시가총액(B)",       "ge"),
        ("sc_fper", 0,   "선행PER 최대",           "선행PER",           "le"),
        ("sc_pbr",  0,   "PBR 최대",              "PBR",              "le"),
        ("sc_psr",  0.0, "PSR 최대",              "PSR",              "le"),
        ("sc_rg",   0,   "내년 매출성장 최소 (%)",  "매출성장 내년(E,%)", "ge"),
        ("sc_eg",   0,   "내년 EPS성장 최소 (%)",  "EPS성장 내년(E,%)",  "ge"),
        ("sc_g5",   0,   "5년 EPS성장 최소 (%)",   "EPS성장 5년(E,%)",   "ge"),
        ("sc_upr",  0,   "추정상향 최소 (건)",      "추정상향(30일)",     "ge"),
        ("sc_opm",  0,   "영업이익률 최소 (%)",     "영업이익률(%)",      "ge"),
        ("sc_npm",  0,   "순이익률 최소 (%)",       "순이익률(%)",        "ge"),
        ("sc_dr",   0,   "부채비율 최대 (%)",       "부채비율(%)",        "le"),
        ("sc_nd",   0.0, "순부채/EBITDA 최대",      "순부채/EBITDA",     "le"),
        ("sc_icr",  0,   "이자보상배율 최소",        "이자보상배율",       "ge"),
        ("sc_fcfy", 0.0, "FCF수익률 최소 (%)",     "FCF수익률(%)",      "ge"),
        ("sc_fcfm", 0,   "FCF마진 최소 (%)",       "FCF마진(%)",        "ge"),
        ("sc_ccr",  0,   "현금전환율 최소 (%)",      "현금전환율(%)",      "ge"),
        ("sc_div",  0.0, "배당수익률 최소 (%)",      "배당수익률(%)",      "ge"),
        ("sc_shy",  0.0, "총주주환원율 최소 (%)",    "총주주환원율(%)",    "ge"),
        ("sc_ups",  0,   "상승여력 최소 (%)",       "상승여력(%)",        "ge"),
        ("sc_buy",  0,   "매수비율 최소 (%)",       "매수비율(%)",        "ge"),
    ]
    SCR_RANGE = {
        "sc_per": (0, 100, 1), "sc_peg": (0.0, 5.0, 0.1), "sc_roe": (0, 50, 1),
        "sc_mcap": (0, 2000, 10), "sc_fper": (0, 100, 1), "sc_pbr": (0, 30, 1),
        "sc_psr": (0.0, 20.0, 0.5), "sc_rg": (0, 40, 1), "sc_eg": (0, 50, 1),
        "sc_g5": (0, 40, 1), "sc_upr": (0, 20, 1), "sc_opm": (0, 60, 1),
        "sc_npm": (0, 50, 1), "sc_dr": (0, 500, 10), "sc_nd": (0.0, 6.0, 0.5),
        "sc_icr": (0, 30, 1), "sc_fcfy": (0.0, 15.0, 0.5), "sc_fcfm": (0, 40, 1),
        "sc_ccr": (0, 150, 5), "sc_div": (0.0, 10.0, 0.5), "sc_shy": (0.0, 15.0, 0.5),
        "sc_ups": (0, 60, 5), "sc_buy": (0, 100, 5),
    }
    SCR_LABEL = {k: lb for k, _d, lb, _c, _o in SCR}
    SCR_DEF = {k: d for k, d, _lb, _c, _o in SCR}
    POS_ONLY = ("PER", "선행PER", "PEG", "PBR", "PSR")

    for _k, _v in SCR_DEF.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v

    def _scr_set(d):
        for _k, _v in SCR_DEF.items():
            st.session_state[_k] = d.get(_k, 0.0 if isinstance(_v, float) else 0)

    def _sl(key):
        lo, hi, stp = SCR_RANGE[key]
        st.slider(SCR_LABEL[key], lo, hi, step=stp, key=key)

    PRESETS = {
        "저평가 가치주": {"sc_per": 20, "sc_pbr": 5, "sc_roe": 12, "sc_dr": 200, "sc_fcfy": 4.0},
        "성장주": {"sc_peg": 2.5, "sc_roe": 12, "sc_rg": 10, "sc_eg": 15, "sc_g5": 12},
        "배당·주주환원": {"sc_per": 25, "sc_roe": 10, "sc_icr": 8, "sc_div": 2.0, "sc_shy": 4.0},
    }
    pc = st.columns(4)
    for _i, _nm in enumerate(PRESETS):
        with pc[_i]:
            if st.button(_nm, use_container_width=True, key="scr_pre_%d" % _i):
                _scr_set(PRESETS[_nm])
                st.rerun()
    with pc[3]:
        if st.button("조건 모두 끄기", use_container_width=True, key="scr_pre_off"):
            _scr_set({})
            st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _sl("sc_per")
    with c2:
        _sl("sc_peg")
    with c3:
        _sl("sc_roe")
    with c4:
        _sl("sc_mcap")

    with st.expander("조건 더 보기", expanded=False):
        st.markdown("**밸류에이션**")
        v1, v2, v3 = st.columns(3)
        with v1:
            _sl("sc_fper")
        with v2:
            _sl("sc_pbr")
        with v3:
            _sl("sc_psr")

        st.markdown("**성장 전망**")
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            _sl("sc_rg")
        with g2:
            _sl("sc_eg")
        with g3:
            _sl("sc_g5")
        with g4:
            _sl("sc_upr")

        st.markdown("**수익성 · 안정성**")
        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            _sl("sc_opm")
        with p2:
            _sl("sc_npm")
        with p3:
            _sl("sc_dr")
        with p4:
            _sl("sc_nd")
        with p5:
            _sl("sc_icr")

        st.markdown("**현금흐름 · 주주환원 · 애널리스트**")
        h1, h2, h3, h4, h5, h6 = st.columns(6)
        with h1:
            _sl("sc_fcfy")
        with h2:
            _sl("sc_fcfm")
        with h3:
            _sl("sc_ccr")
        with h4:
            _sl("sc_div")
        with h5:
            _sl("sc_shy")
        with h6:
            _sl("sc_ups")
        a1, _a2, _a3 = st.columns(3)
        with a1:
            _sl("sc_buy")

    _on = [x for x in SCR if _f(st.session_state.get(x[0])) not in (None, 0)]
    st.caption("지금 켜진 조건 %d개: %s"
               % (len(_on), ", ".join(x[2] for x in _on) if _on else "없음"))

    if st.button("찾기 시작", type="primary", use_container_width=True, key="scr_run"):
        if uni == UNI_OPTS[0]:
            _rows3, _ = fetch_many(SCREEN_UNIVERSE, "종목 검사 중")
            st.session_state["t3_rows"] = _rows3
            st.session_state["t3_meta"] = ""
        else:
            with st.spinner("1차: 전체 종목 목록과 기본 지표 받는 중... (30초 안팎)"):
                base1, how1 = build_stage1(uni)
            total1 = len(base1)
            cand = base1
            # 1차 거름: 일괄 검색에서 받은 항목만, 살짝 넉넉하게 (최종 판단은 2차에서)
            for _key, _d, _lb, _col, _op in SCR:
                v = _f(st.session_state.get(_key))
                if not v or _col not in cand.columns or cand[_col].notna().sum() == 0:
                    continue
                if _op == "le":
                    cand = cand[cand[_col].apply(lambda x, v=v: _f(x) is not None and 0 < _f(x) <= v * 1.15)]
                else:
                    cand = cand[cand[_col].apply(lambda x, v=v: _f(x) is not None and _f(x) >= v * 0.85)]
            pass1 = len(cand)
            cand = cand.head(int(depth))
            nm1 = dict(zip(cand["티커"], cand["이름"]))
            _rows3, _ = fetch_many(cand["티커"].tolist(), "2차: 자세히 검사 중")
            for r in _rows3:
                if r.get("종목명") == r.get("티커") and nm1.get(r.get("티커")):
                    r["종목명"] = nm1[r["티커"]]
            st.session_state["t3_rows"] = _rows3
            msg = "%s · 검사 범위 %s개 → 1차 통과 %s개 → 자세히 검사 %d개" % (
                how1, format(total1, ","), format(pass1, ","), len(cand))
            if pass1 > len(cand):
                msg += " (1차 통과가 많아 시가총액 큰 %d개만 봤습니다. 조건을 좁히거나 검사 수를 늘리세요)" % len(cand)
            st.session_state["t3_meta"] = msg

    rows3 = st.session_state.get("t3_rows") or []
    if st.session_state.get("t3_meta"):
        st.caption(st.session_state["t3_meta"])
    if rows3:
        df = pd.DataFrame(rows3)
        m = pd.Series(True, index=df.index)
        for _key, _d, _lb, _col, _op in SCR:
            v = _f(st.session_state.get(_key))
            if not v or _col not in df.columns:
                continue
            if _op == "le":
                if _col in POS_ONLY:
                    m &= df[_col].apply(lambda x, v=v: (_f(x) is not None and 0 < _f(x) <= v))
                else:
                    m &= df[_col].apply(lambda x, v=v: (_f(x) is not None and _f(x) <= v))
            else:
                m &= df[_col].apply(lambda x, v=v: (_f(x) is not None and _f(x) >= v))
        res = df[m]
        st.success("조건에 맞는 종목 %d개" % len(res))
        if len(res):
            base = ["티커", "현재가($)", "시가총액(B)", "PER", "PEG", "ROE(%)"]
            cols = base + [x[3] for x in _on if x[3] not in base]
            out = res[[c for c in cols if c in res.columns]].reset_index(drop=True)
            show_table(out, S["color"], table_height(len(out)))
            st.caption("아래 티커를 복사해서 ① 탭의 종목 칸에 붙여넣을 수 있습니다.")
            st.code(", ".join(res["티커"].astype(str).tolist()))

# ============================================================
# 탭 4
# ============================================================
with t4:
    st.markdown("### 다른 사이트에서 교차 확인")
    st.caption("야후 값이 이상하거나 5년 전망을 직접 확인하고 싶을 때 쓰세요. 아래 링크는 자동 수집이 아니라 해당 종목 페이지로 바로 가는 링크입니다.")
    qq = st.text_input("종목", value="애플", key="link_q")
    sym = resolve(qq)
    if sym:
        st.markdown("**%s (%s)**" % (NAME_MAP.get(sym, sym), sym))
        links = [
            ("Finviz — EPS next 5Y 확인", "https://finviz.com/quote.ashx?t=%s" % sym),
            ("Stock Analysis — 향후 매출·EPS 전망표", "https://stockanalysis.com/stocks/%s/forecast/" % sym),
            ("Zacks — Next 5 Years 성장률", "https://www.zacks.com/stock/quote/%s/detailed-estimates" % sym),
            ("Alphaspread — 적정가치", "https://www.alphaspread.com/security/nasdaq/%s/summary" % sym),
            ("Seeking Alpha — 전망·의견", "https://seekingalpha.com/symbol/%s" % sym),
            ("Macrotrends — 10년 재무 추이", "https://www.macrotrends.net/stocks/charts/%s/x/revenue" % sym),
            ("SEC EDGAR — 공시 원문", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker=%s&type=10-K" % sym),
            ("야후 파이낸스 — 원본", "https://finance.yahoo.com/quote/%s/" % sym),
        ]
        for label, url in links:
            st.markdown("- [%s](%s)" % (label, url))
        st.info("앱의 EPS성장 5년(E) 값과 Finviz의 EPS next 5Y를 비교해 보세요. 2%p 안쪽이면 역산이 잘 맞는 것입니다.")

# ============================================================
# 탭 5: 메모 (종목별 짧은 메모)
# ============================================================
with t5:
    if not isinstance(S.get("memos"), dict):
        S["memos"] = {}
    MEMO_ALL = "(메모 쓴 종목 전체)"
    _mnames = list(S["lists"].keys()) + [MEMO_ALL]
    if st.session_state.get("memo_pick") not in _mnames:
        st.session_state["memo_pick"] = S["active"] if S["active"] in _mnames else _mnames[0]
    _mp = st.selectbox("목록", _mnames, key="memo_pick")

    if _mp == MEMO_ALL:
        _msyms = sorted(S["memos"].keys())
    else:
        _msyms = parse_list(S["lists"].get(_mp, ""))

    # 표에 넣는 바탕 자료를 "목록이 바뀔 때만" 새로 만들어 고정해 둡니다.
    # (메모를 쓸 때마다 바탕 자료가 바뀌면 줄 순서가 흔들릴 수 있어서)
    _msig = _mp + "|" + ",".join(_msyms)
    _mkey = "memo_ed_" + hashlib.md5(_msig.encode("utf-8")).hexdigest()[:12]
    _mbase = st.session_state.get("_memo_base")
    if not isinstance(_mbase, dict) or _mbase.get("sig") != _msig:
        _mbase_syms = list(_msyms)
        _mbase = {
            "sig": _msig,
            "syms": _mbase_syms,
            "memos": [S["memos"].get(t, "") for t in _mbase_syms],
        }
        st.session_state["_memo_base"] = _mbase
        # 목록을 바꾸면 예전 편집 기록을 지우고 새로 그립니다
        for _k in [k for k in list(st.session_state.keys()) if str(k).startswith("memo_ed_")]:
            try:
                del st.session_state[_k]
            except Exception:
                pass

    if not _mbase["syms"]:
        st.info("이 목록에 종목이 없습니다. 종목은 ① 탭에서 넣을 수 있습니다.")
    else:
        _mdf = pd.DataFrame({
            "티커": _mbase["syms"],
            "메모": _mbase["memos"],
        })
        _mcfg = {
            "티커": st.column_config.TextColumn("티커", width="small", disabled=True),
            "메모": st.column_config.TextColumn("메모", width="large", max_chars=500),
        }
        try:
            _mcfg["티커"] = st.column_config.TextColumn("티커", width="small", disabled=True, pinned=True)
        except TypeError:
            pass
        _medited = st.data_editor(
            _mdf,
            key=_mkey,
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            height=38 + 35 * len(_mbase["syms"]),
            column_config=_mcfg,
        )
        _changed = False
        for _t, _v in zip(_medited["티커"], _medited["메모"]):
            _v = "" if _v is None or (isinstance(_v, float) and np.isnan(_v)) else str(_v).strip()
            if _v != S["memos"].get(_t, ""):
                if _v:
                    S["memos"][_t] = _v
                else:
                    S["memos"].pop(_t, None)
                _changed = True
        if _changed:
            mark_dirty()
        st.caption("메모 칸을 누르면 바로 쓸 수 있고, 자동으로 저장됩니다. 같은 종목은 어느 목록에서 봐도 같은 메모가 보입니다.")

persist()
