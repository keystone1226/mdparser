# MD Parser

오피스 파일을 드래그앤드랍 한 번으로 깔끔한 **마크다운(.md)** 으로 변환해 주는 로컬 웹 앱입니다.
내부적으로 Microsoft의 [`markitdown`](https://github.com/microsoft/markitdown) 을 사용하며, 이미지/스캔 PDF 의 OCR · 캡션은 사내 Fabrix LLM API 를 통해 수행됩니다.

- PDF · DOCX · XLSX · PPTX · HTML · CSV · JSON · XML · EPUB · ZIP · 이미지 등 지원
- 드래그앤드랍, 실시간 상태 표시, 마크다운 미리보기, 개별/전체 ZIP 다운로드
- 변환 결과는 24시간 후 자동 삭제 (설정 가능)
- 로컬 실행, 사내망에 공유 가능

---

## 빠른 시작

### Windows (권장)

1. `python --version` 또는 `py -3 --version` 으로 Python 3.10 이상이 설치되어 있는지 확인합니다. 없으면 https://www.python.org/downloads/ 에서 설치 (설치 시 *Add Python to PATH* 체크).
2. 저장소를 내려받은 뒤 `run.bat` 을 **더블클릭**.
3. 최초 실행 시 `.venv` 생성 및 의존성 설치가 자동으로 진행됩니다 (수 분 소요).
4. 브라우저가 자동으로 열립니다: <http://localhost:8000>
5. (선택) `.env` 파일이 자동 생성됩니다. Fabrix 사용을 원하면 값을 채워 넣은 뒤 창을 닫고 다시 `run.bat` 실행.

### macOS / Linux

```bash
bash run.sh
```

---

## Fabrix LLM 설정 (이미지 설명 / OCR 활성화)

`.env` 파일에 아래 값을 채워 넣습니다.

```dotenv
FABRIX_ENDPOINT_URL=https://.../openapi/llm/v1
FABRIX_CLIENT_KEY=eyJXXX...              # x-fabrix-client
FABRIX_OPENAPI_TOKEN=Bearer eyJXXX...    # x-openapi-token
FABRIX_MODEL_ID=312                      # x-llm-model-id (/v1/models 조회 결과)
FABRIX_MODEL_NAME=gpt-4o                 # 요청 body 의 model 값
FABRIX_USER_EMAIL=you@samsung.com        # 선택
```

위 5개 필수 항목을 모두 채우면 상단 우측 상태 배지가 **"LLM 활성"** 으로 바뀌고, 이미지/스캔 PDF 에 자동으로 캡션/OCR 이 적용됩니다.

> 참고: markitdown 의 `llm_client` 매개변수는 OpenAI SDK 와 호환되어야 합니다. 본 앱은 `openai` 파이썬 SDK 에 `base_url` 과 `default_headers` 를 주입해 Fabrix 사용자 지정 헤더(`X-FABRIX-CLIENT`, `X-OPENAPI-TOKEN`, `X-LLM-MODEL-ID`) 를 자동으로 실어 보냅니다.

---

## 팀에 공유하기

기본 바인딩은 `0.0.0.0` 입니다. 같은 사내망에 있는 동료는 브라우저에서 `http://<내-컴퓨터-IP>:8000` 으로 바로 접속할 수 있습니다.

- Windows 방화벽에서 Python 이 8000 포트를 수신하도록 허용하세요.
- 공유를 원치 않으면 `.env` 의 `HOST=127.0.0.1` 로 변경 후 재실행.

인증은 기본 제공되지 않으므로 **신뢰할 수 있는 사내망에서만** 공유하세요. LLM 호출 비용은 `.env` 에 설정된 토큰 소유자 계정에 과금됩니다.

---

## 설정 항목 (`.env`)

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | 바인딩 주소. 공유 안 하려면 `127.0.0.1` |
| `PORT` | `8000` | 포트 |
| `MAX_FILE_SIZE_MB` | `100` | 파일당 최대 업로드 크기 |
| `MAX_FILES_PER_UPLOAD` | `10` | 한 번에 업로드 가능한 파일 수 |
| `RETENTION_HOURS` | `24` | 변환 결과 보관 시간. `0` 이면 비활성 |
| `FABRIX_*` | - | 위 *Fabrix LLM 설정* 참고 |

---

## 디렉토리 구조

```
mdparser/
├── app/
│   ├── main.py          # FastAPI 엔드포인트
│   ├── config.py        # .env 로더
│   ├── converter.py     # markitdown 래퍼
│   ├── llm.py           # Fabrix OpenAI 호환 클라이언트
│   ├── storage.py       # 변환 기록 저장소 (JSON 인덱스)
│   ├── cleanup.py       # 주기적 만료 정리
│   └── static/          # 프론트엔드 (HTML/CSS/JS)
├── storage/             # (런타임 생성) 변환된 .md 파일과 index.json
├── requirements.txt
├── .env.example
├── run.bat              # Windows 원클릭
├── run.sh               # macOS / Linux
└── README.md
```

---

## 자주 묻는 질문

**Q. 지원되는 파일 종류는?**
A. markitdown 이 처리 가능한 모든 포맷 (PDF/DOCX/XLSX/PPTX/HTML/CSV/JSON/XML/EPUB/ZIP, 이미지 등).

**Q. 변환한 파일은 어디에 저장되나요?**
A. 저장소 루트의 `storage/` 폴더에 `.md` 파일로 저장되며, `RETENTION_HOURS` 가 지나면 자동 삭제됩니다. 서버는 30분마다 정리 작업을 수행합니다.

**Q. 의존성 설치를 다시 하고 싶어요.**
A. `.venv` 폴더를 지우고 다시 `run.bat` / `run.sh` 를 실행하면 됩니다.

**Q. 포트가 이미 사용 중입니다.**
A. `.env` 에서 `PORT` 를 다른 값으로 변경한 뒤 재실행하세요.
