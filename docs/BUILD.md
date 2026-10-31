# 빌드 방법

번역 대본·원문은 저장소에 없으므로, 아래는 자신이 가진 원본과 번역 파일로 다시 빌드하는 절차입니다.

## 준비물
- 원본 ISO `Shin Sangoku Musou - Multi Raid 2 (Japan).iso` (MD5 `1623a293edca9a32bc9e768fa5e37233`)
- Python 3.12+ : `pip install pillow numpy opencv-python imageio-ffmpeg websocket-client`
- 글꼴: `SeoulHangang*.ttf`, `NanumSquareNeo-*.ttf` (작업 폴더), `Galmuri*.ttf` (`work/fonts/`)

## 폴더 구성
```
<작업 폴더>/
  Shin Sangoku Musou - Multi Raid 2 (Japan).iso
  *.ttf
  tools/        (이 저장소의 tools)
  trans/        eboot_ko.json, stage_ko.json, cards_ko.json, names.json, images.json, clut_00030.json, movie_ko.json, parts/  (번역 — 저장소 미포함)
  work/         charmap.json, eboot_strings.json, tr_in/, fonts/, mvbuild/ ...
```

## 순서
1. ISO 풀기: `python tools/extract_iso.py "Shin Sangoku Musou - Multi Raid 2 (Japan).iso" work/iso`
2. 원문 추출: `python tools/extract_eboot.py`, `python tools/extract_text.py` → `work/eboot_strings.json` 등, 번역 배치는 `python tools/make_batches.py` → `work/tr_in/*.json`
3. 번역: `trans/parts/<배치>.json` = `{"id": "번역"}` 작성 후 `python tools/check_batch.py <배치>` 로 길이·제어 코드 검사, `python tools/merge.py` 로 `trans/eboot_ko.json`·`stage_ko.json` 병합 (지침: `docs/TRANSLATION_GUIDE.md`)
4. 그림 글자: `trans/images.json` 직접 작성 (`tools/imgpatch.py` 상단 형식 설명 참고)
5. 동영상 자막: `cd tools/movie && python build.py RE_06 opening` → `work/mvbuild/`
6. 빌드: `python tools/build.py "Shin Sangoku Musou - Multi Raid 2 (Korean).iso"`
7. 차분: `xdelta3 -0 -f -e -s 원본.iso 한글.iso 패치.xdelta`

PPSSPP 원격 디버거로 자동 확인할 때는 `python tools/emu.py` 를 씁니다.
