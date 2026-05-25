# craft-knowledge

도메인 지식 베이스를 구축하고 탐색하는 Claude Code 스킬.  
노트를 Obsidian에 작성하고, 의미 기반으로 검색하며, 에이전트가 필요한 것을 즉시 찾을 수 있도록 한다.

---

## 어떤 문제를 해결하는가?

### 문제 1 — 노트가 많아질수록 찾기가 어려워진다

새로운 도메인을 배울 때 노트를 작성하는 것은 생산적으로 느껴진다. 처음에는 그렇다. 하지만 노트가 20개, 50개가 되면 "추출 온도에 대해 어디에 썼더라?"라는 질문이 생긴다. 일반 검색은 정확한 키워드 매칭을 요구하기 때문에 "적정 수율"을 검색해도 `extraction-ratio`를 설명한 노트를 찾아주지 않는다.

### 문제 2 — 에이전트는 세션이 끝나면 모든 것을 잊는다

새로운 Claude Code 세션을 열고 "발효 화학에 대해 설명해줘"라고 물으면, 에이전트는 이전에 공부한 내용을 전혀 기억하지 못한다. 따라잡으려면 볼트의 노트를 하나씩 읽어야 한다. 노트 30개라면 관리 가능하다. 100개라면 시작 비용이 볼트 크기에 비례해서 커진다.

### 해결책

두 문제는 동일한 해결책을 공유한다.

- **의미 기반 검색**: 볼트에 연결된 벡터 검색 엔진은 키워드가 아닌 의미를 이해한다. "적정 수율"을 검색하면 `extraction-ratio`에 관한 노트를 찾아준다.
- **O(1) 탐색**: 모든 파일을 읽는 대신, 에이전트가 "이 주제와 관련된 노트는?" 한 번 물어보면 — 노트 수에 관계없이 — 상위 결과를 돌려받는다.

> **벡터 검색이란?** 텍스트를 의미를 담은 고차원 수치 배열(벡터)로 변환한다. 의미가 비슷한 텍스트는 이 공간에서 가까이 위치한다. 그래서 정확한 단어가 일치하지 않아도 의미적으로 관련된 노트가 나타난다.

---

## 핵심 개념

시작하기 전에 이해해 두어야 할 몇 가지 아이디어.

### 소스 vs. 파생 산출물

노트(마크다운 파일)는 **소스**다. 사람이 작성하고, 에이전트가 읽으며, git이 추적한다.

벡터 인덱스(`.chromadb/` 폴더)는 **파생 산출물** — 소스에서 자동으로 생성된다. `node_modules`처럼 생각하면 된다: `package.json`에서 만들어지고 언제든 재생성할 수 있으므로 git에 커밋할 필요가 없다.

```
마크다운 노트  →  git 추적   (영구 소스)
.chromadb/    →  gitignore  (embed.py로 재생성)
```

새 머신에서 저장소를 clone한 후 `embed.py`를 한 번 실행하는 것은 `npm install`과 같다.

### WikiLink와 그래프 레이어

Obsidian에서 `[[note-name]]` 문법은 노트 간 링크를 생성한다 — WikiLink라고 부른다. 이 스킬에서 WikiLink는 단순한 탐색 단축키가 아니다. 에이전트가 관련 개념을 따라갈 수 있는 **의도적 관계**다.

벡터 검색은 *유사한* 노트를 찾는다. WikiLink는 단어가 비슷하지 않을 수 있는 *연관된* 노트를 연결한다. 두 레이어가 함께 작동한다.

```
벡터 검색  →  "추출" 쿼리  →  의미적 유사도로 순위가 매겨진 노트 반환
WikiLink   →  그 노트에서 [[물 온도]] 따라가기  →  연결된 개념에 도달
```

### 인사이트

노트 컬렉션과 지식 베이스의 차이는 **인사이트**다.

예를 들어, `extraction-ratio`와 `water-temperature`는 별관계가 없어 보인다. 하지만 함께 읽으면 비자명한 패턴이 드러난다: "온도가 너무 높으면 쓴 성분이 너무 빠르게 추출되어 단 향이 발현되기 전에 목표 수율에 도달한다 — 수율은 맞아 보이지만 맛은 틀렸다." 그 연결은 어느 한 노트에만 있지 않다.

이런 교차 노트 관찰 — 여러 노트를 함께 읽어야만 보이는 것들 — 은 각 MOC(Map of Content)의 `## 인사이트` 섹션에 담긴다. 이것이 지식 베이스를 단순한 참고 매뉴얼이 아닌 가치 있는 것으로 만든다.

---

## 더 큰 그림

스킬은 에이전트가 *어떻게* 행동하는지를 배포한다. 지식 베이스는 에이전트가 *무엇을* 아는지를 배포한다 — 문서를 읽는 것만으로는 보이지 않는, 경험을 통해서만 드러나는 개념 간의 연결.

이 형식이 성숙해지면 패키지로 배포될 수 있다: 누군가 도메인 KB를 게시하고, 다른 사람들이 설치해 에이전트에게 즉각적인 도메인 전문성을 부여한다 — 사전 학습된 모델 가중치가 공유되는 방식과 비슷하지만, 마크다운으로 표현된 구조화된 도메인 이해를 다룬다.

---

## 아키텍처

```
{package-name}/              (패키지 볼트 — 단일 도메인, 배포 단위)
├── kb.yaml                  # 패키지 메타데이터 (name, version, ...)
├── MOC.md                   # Map of Content — 도메인 인덱스 + 인사이트 허브
├── concepts/                # 핵심 아이디어 및 정의
├── people/                  # 주요 인물 (해당되는 경우)
├── tools/                   # 도구, 프레임워크, 라이브러리
├── .chromadb/               # 벡터 인덱스 — 자동 생성, gitignore
└── .gitignore

{vault-name}/                (컨슈머 볼트 — 여러 패키지 통합)
├── kb.json                  # 의존성 선언
├── _MOC/                    # 크로스 패키지 Map of Content
├── domains/
│   └── {package-name}/      # 설치된 패키지 (네임스페이스)
├── .chromadb/
└── .gitignore
```

```
~/.claude/skills/craft-knowledge/
├── skill.md          # 에이전트 워크플로 명세
├── README.md         # 영문 문서
├── README.ko.md      # 한글 문서 (이 파일)
└── scripts/
    ├── embed.py      # 벡터 인덱스 빌드 및 업데이트
    └── query.py      # 의미 기반 노트 검색
```

---

## 설정

### 1. uv 설치 (머신당 한 번)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv`는 `npx`처럼 작동하는 Python 패키지 관리자다. 스크립트를 실행하면 필요한 라이브러리(`chromadb`, `sentence-transformers`)를 격리된 환경에 자동으로 설치한다. 수동 `pip install`이 필요 없다.

### 2. 볼트용 인덱스 빌드

Obsidian 볼트를 만들고 노트를 작성한 후:

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault
```

**첫 실행 시 일어나는 일**:
1. `uv`가 필요한 패키지를 자동으로 설치한다 (~200MB, 이후 캐시됨)
2. 임베딩 모델이 다운로드된다 (~500MB, `~/.cache/`에 저장되어 재사용)
3. 볼트의 모든 `.md` 파일이 벡터로 변환되어 `.chromadb/`에 저장된다

이후 실행은 마지막 인덱스 이후 변경된 파일만 처리한다.

### 3. .gitignore 추가

볼트가 버전 관리 하에 있다면 `.chromadb/`를 제외해야 한다:

```
.chromadb/
```

---

## 사용법

### 새 도메인 KB 시작

Claude Code에서:

```
/craft-knowledge {domain}에 대한 지식 베이스를 만들어줘. {URL} 참고해줘.
```

에이전트가 볼트 경로와 깊이(입문 / 중급 / 심화)를 물어볼 것이다.

### 새 세션에서 작업 재개

에이전트가 먼저 검색하고 관련 내용만 읽는다:

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/query.py \
  --vault /path/to/vault "주제 또는 질문"

# 출력 예시
[1] domains/coffee/concepts/extraction-ratio.md   관련도: 29%
[2] domains/coffee/concepts/water-temperature.md  관련도: 18%
[3] domains/coffee/tools/grinder-types.md         관련도: 17%
```

해당 노트들을 읽은 뒤 그 안의 `[[WikiLink]]`를 따라 연결된 개념을 탐색한다.

### 노트 작성 또는 편집 후

```bash
# 변경된 파일을 자동 감지하여 해당 파일만 업데이트
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault

# 단일 파일 즉시 업데이트
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py \
  --vault /path/to/vault --file domains/coffee/concepts/extraction-ratio.md
```

### 인덱스가 최신인지 확인

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault /path/to/vault --check

# 최신 상태
Index is up to date. (15 notes)

# 업데이트 필요
2 stale note(s):
  domains/coffee/concepts/extraction-ratio.md
  domains/coffee/concepts/water-temperature.md
```

### 새로 clone한 저장소에서

```bash
git clone {kb-repo}
cd {kb-dir}
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault .
```

---

## 노트 품질 기준

### `status: published` 조건

- 모든 사실적 주장은 **독립적인 출처 2개 이상**으로 검증
- 출처 URL과 접근 날짜가 frontmatter에 기록됨
- 검증되지 않은 주장은 본문에 섞지 않고 callout 블록으로 분리:

```markdown
> [!question]- 검증 필요 #needs-verification
> {확인되지 않은 주장}
> 확인한 출처: {목록}
```

이렇게 하면 검증되지 않은 내용을 `#needs-verification`으로 grep 가능하게 유지하면서 노트 본문을 오염시키지 않는다.

### 인사이트 의무사항

모든 published 노트는 다음 중 하나 이상을 포함해야 한다:

**함께 고려할 것** — "이 노트만 읽으면 독자가 무엇을 놓치는가?" 이 노트와 함께 읽을 때 그림이 완성되는 2-3개의 다른 노트를 명시한다. 조합이 왜 중요한지 설명한다.

**이것이 잘못되면** — 이 개념을 잘못 이해하거나 잘못 설정했을 때의 하류 증상을 추적한다. "X를 하면 Z에서 Y가 발생한다" — 구체적인 인과 관계.

**결정 기준** — 유사한 대안이 있을 때, 이것을 선택하는 경우와 그렇지 않은 경우를 설명한다. 독자의 모호함을 제거한다.

### MOC 인사이트 섹션

MOC는 단순한 목차가 아니다. 여러 노트를 함께 읽어야만 보이는 교차적 관찰을 담은 `## 인사이트` 섹션을 포함해야 한다:

```markdown
## 인사이트

> **[인사이트 제목]**: {단일 노트에서는 보이지 않는 관찰}. [[note-a]], [[note-b]] 참고.
```

도메인당 3-7개의 인사이트를 목표로 한다. 인사이트 섹션이 비어 있다면 지식 베이스가 미완성이라는 의미다.

---

## 현재 한계 및 개선 방향

이 구조가 아직 해결하지 못하는 것에 대한 솔직한 평가.

### 1. 콘텐츠가 오래된다

**현재**: 기술 KB는 빠르게 낡는다. 라이브러리가 새 메이저 버전을 출시하거나 모범 사례가 바뀌면 기존 노트가 오히려 오해를 불러일으킬 수 있다. `refresh_after` frontmatter 필드는 존재하지만 자동으로 확인되거나 처리되지 않아 수동 검토가 필요하다.

**방향**:
- 출처 URL을 주기적으로 다시 가져와 내용 변경을 감지하는 `check-sources.py` 추가
- `refresh_after` 날짜가 지난 노트에 `#needs-refresh` 자동 태그를 달아 다음 세션에서 에이전트가 우선 처리하도록
- 소비자가 알려진 안정 버전에 고정할 수 있도록 KB 패키지에 semver 버전 관리 도입

### 2. 새 머신마다 인덱스를 재빌드해야 한다

**현재**: `.chromadb/`가 gitignore되어 있기 때문에 KB를 받은 사람은 직접 `embed.py`를 실행해야 한다. 첫 실행에는 수 분이 걸린다 (모델 다운로드 + 인덱싱).

**방향**:
- KB 패키지 메타데이터 표준(`kb.yaml`) 정의:
  ```yaml
  name: coffee-brewing
  version: 1.0.0
  embedding_model: paraphrase-multilingual-MiniLM-L12-v2
  notes: 15
  insights: 5
  ```
- 다운로드와 인덱싱을 한 번에 처리하는 `craft-knowledge install {kb-name}` 명령어
- 공유 임베딩 서비스를 통한 사전 빌드된 인덱스 배포는 기술적으로 가능하지만 현재의 로컬 실행 원칙과 충돌

### 3. 객관적인 품질 측정 수단이 없다

**현재**: 노트 수는 품질을 나타내지 않는다. 풍부한 교차 노트 인사이트를 가진 15개짜리 KB가 고립된 사실들의 100개짜리 KB보다 가치 있을 수 있다. 현재는 사람의 판단이 필요하다.

**방향**:
- 자동으로 다음을 보고하는 `audit.py` 스크립트:
  - 인사이트 섹션이 있는 노트 비율
  - 노트당 평균 WikiLink 수
  - `#needs-verification` 노트 비율
  - 만료된 `refresh_after` 날짜 수
- 마켓플레이스 맥락에서 이 지표를 품질 배지로 사용: `verified: 93%`, `insights: 5`, `freshness: 2026-05`

### 4. WikiLink 순회가 수동이다

**현재**: `query.py`가 진입점 노트를 반환한 후, WikiLink를 따라 연결된 개념을 발견하는 것은 에이전트가 수동으로 해야 한다 — 자동화되어 있지 않다.

**방향**:
- `query.py`에 `--expand` 플래그 추가: 반환된 노트의 WikiLink를 파싱하고 연결된 노트를 결과에 자동으로 포함
- 이렇게 하면 벡터 검색(유사도 기반)과 그래프 순회(관계 기반)가 단일 명령어로 결합됨

### 5. KB 구축이 단일 저자에 의존한다

**현재**: KB를 만들고 유지하는 것은 한 사람(또는 하나의 에이전트 세션)에 달려 있다. 팀이 협력해서 도메인 지식을 구축하거나 커뮤니티가 공유 KB를 유지하는 구조가 없다.

**방향**:
- 노트 frontmatter에 노트별 소유권을 위한 `author` 필드 추가
- 마크다운이 소스이므로 표준 git PR 워크플로가 자연스럽게 적용됨 — 여러 기여자가 각자의 전문 분야 노트를 작성하고 PR로 병합
- 마켓플레이스 맥락에서 이는 npm의 패키지 소유권 + 커뮤니티 PR 모델과 직접적으로 대응

---

## 명령어 참조

### embed.py

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/embed.py --vault {path} [options]
```

| 옵션 | 설명 |
|------|------|
| `--vault PATH` | 볼트 루트 경로 (필수) |
| `--file RELPATH` | 단일 파일 인덱싱. 볼트 루트 기준 상대 경로 |
| `--check` | 수정 없이 오래된 파일 보고 |

옵션 없이 실행하면 변경된 파일을 자동 감지하여 해당 파일만 재인덱싱한다.

### query.py

```bash
uv run ~/.claude/skills/craft-knowledge/scripts/query.py --vault {path} "쿼리"
```

| 옵션 | 설명 |
|------|------|
| `--vault PATH` | 볼트 루트 경로 (필수) |
| `--top N` | 반환할 결과 수 (기본값: 3) |
| `query` | 검색 쿼리. 한국어와 영어 모두 지원 |

**임베딩 모델**: `paraphrase-multilingual-MiniLM-L12-v2`  
50개 이상의 언어를 지원한다. ONNX를 통해 로컬에서 실행되며 API 키가 필요 없다.  
모델 가중치는 첫 실행 시 `~/.cache/chroma/onnx_models/`에 다운로드되어 재사용된다.

---

## 설계 결정 기록

| 결정 | 고려한 대안 | 이유 |
|------|------------|------|
| `.chromadb/` gitignore | 인덱스 커밋 | 바이너리 파일은 무의미한 diff를 생성하고 저장소를 비대하게 만든다. 소스에서 재현 가능 |
| `uv run`으로 의존성 관리 | 전역 `pip install` | 시스템 Python 오염 없음. 머신 간 재현 가능. 수동 설치 단계 없음 |
| 다국어 임베딩 모델 | 영어 전용 모델 | 영어 전용 모델은 한국어 쿼리에서 0-3% 관련도를 반환했다. 다국어 모델: 29-53% |
| 벡터 검색 + WikiLink 이중 레이어 | 벡터 검색만 사용 | 벡터는 유사한 노트를 찾는다. 인사이트는 비유사한 노트를 연결할 때 나온다. WikiLink가 그 공백을 채운다 |
| `_status.md` 요약 파일 없음 | 세션 상태 요약 파일 | 유지 비용이 노트 수에 비례해 증가한다. 오래된다. 대신 벡터 검색으로 해결 |
| mtime 기반 오래됨 감지 | 매 실행 시 전체 재인덱싱 | 변경된 파일만 처리하여 볼트 크기에 관계없이 업데이트 시간을 일정하게 유지 |
