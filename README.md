# 진·삼국무쌍 MULTI RAID 2 (PSP) 비공식 한글패치

PSP 일본판 **真・三國無双 MULTI RAID 2 (진·삼국무쌍 멀티레이드 2, ULJM-05637)** 비공식 한국어 패치입니다. 이 저장소에는 제작 도구와 기술 문서만 있고, 패치 파일(xdelta)은 [Releases](../../releases)에서 받을 수 있습니다. 게임 원본·일본어 원문·번역 대본은 포함하지 않습니다.

## 적용 방법
1. 아래 해시와 일치하는 **원본 `.iso`** 를 준비합니다. (CSO·CHD 등으로 변환한 이미지에는 적용할 수 없습니다.)
   - PowerShell: `Get-FileHash -Algorithm MD5 -LiteralPath '.$X'`
2. xdeltaUI 같은 도구로 원본 `.iso` 에 `ShinSangokuMusou_MultiRaid2_KO_v1.0.xdelta` 를 적용합니다. (Patch = xdelta, Source File = 원본 ISO, Output File = 새 파일명)
   - 명령줄: `xdelta3 -d -s "Shin Sangoku Musou - Multi Raid 2 (Japan).iso" ShinSangokuMusou_MultiRaid2_KO_v1.0.xdelta "Shin Sangoku Musou - Multi Raid 2 (Korean).iso"`
3. 만들어진 ISO를 PPSSPP 또는 커스텀 펌웨어(PSP·PS Vita Adrenaline 등)에서 실행합니다.

| 항목 | 값 |
| --- | --- |
| 원본 ISO 크기 | 1,703,280,640 바이트 |
| 원본 ISO MD5 | `1623a293edca9a32bc9e768fa5e37233` |
| 원본 ISO SHA-256 | `b054dd69f34b20c21bb982e4baaea1a19446644cd1d0bc8c13c822eea7485a1c` |
| xdelta SHA-256 | `49ce86f18126cf73c395d383e2a5db82d11fa293f584b2499f556dd5fca79996` |
| 결과 ISO 크기 | 1,703,280,640 바이트 |
| 결과 ISO SHA-256 | `7d5404141a442ab18f8f5d71903779a173131a36eaa6213f99fb728ce369cf91` |

## 주의
- 복호화한 실행 파일을 EBOOT로 넣었기 때문에 **PPSSPP·커스텀 펌웨어 전용**입니다. 정품 펌웨어에서는 부팅되지 않습니다.
- 원본이나 다른 버전 패치에서 만든 **상태저장(세이브 스테이트)** 은 불러오지 마세요. 일반 세이브는 그대로 쓸 수 있습니다.
- xdelta는 압축하지 않은 형식(`-0`)입니다(약 42MB).

## 한글화 내용
- 실행 파일 문자열 8,042개 직접 번역 — 메뉴, 도움말, 시설 안내, 무기·무환·아이템 이름과 설명, 퀘스트 개요, 무장 열전, 전투 메시지, 시스템 메시지
- 스테이지 메시지 슬롯 4,215개 — 전투 중 무장 대사, 이벤트 내레이션, 튜토리얼
- 무장 카드 53종, 인명·지명 472개(한국 삼국지 관례 한자음)
- 그림 글자 188장 — 타이틀 메뉴(처음부터/이어하기/옵션/다운로드), 옵션·세이브 화면, 장 이름(서장/패왕편/요선편/최종장), 전투 HUD, 메뉴 패널
- 동영상(오프닝·이벤트) 일본어 자막 아래에 한국어 자막 추가
- 게임 글꼴 텍스처(12px·14px)에 한글 글리프 추가
- 글꼴: 본문·그림 글자 서울한강체·나눔스퀘어네오, 아주 작은 글자 갈무리

## 그대로 둔 것
- 음성, 체험판 안내 화면 데이터(제품판에서 표시되지 않음), 영문 로고·크레디트 이미지

## 검증 범위
PPSSPP에서 타이틀, 세이브/로드, 스토리 도입, 장안 거점 튜토리얼과 메뉴, 오프닝 동영상 자막을 확인했습니다. 실행 파일·데이터의 문자열과 UI 텍스처를 전수 검사해 일본어가 남지 않은 것을 확인했습니다. 전체 플레이 검증은 하지 않았습니다. 문제를 발견하면 Issues에 알려 주세요.

## 문서
- [CHANGELOG.md](CHANGELOG.md) — 변경 기록
- [docs/TECHNICAL.md](docs/TECHNICAL.md) — 파일 형식과 한글화 방법
- [docs/BUILD.md](docs/BUILD.md) — 직접 빌드하는 방법
- [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) — 번역 지침
- [docs/FONT_CREDITS.md](docs/FONT_CREDITS.md) — 글꼴
- [RIGHTS.md](RIGHTS.md) — 권리 및 외부 자료
