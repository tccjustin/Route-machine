# AXON IPC 드라이버 Python 구현

AXON IPC 드라이버의 Python 구현으로, C 코드와 동일한 패킷 구조를 사용합니다.

## 📁 파일 구조

```
├── constants.py          # 상수 정의
├── crc_utils.py          # CRC 계산 유틸리티
├── packet_utils.py       # 패킷 생성 및 파싱
├── axon_ipc_driver.py    # 메인 드라이버 클래스
├── device_manager.py     # 디바이스 관리 유틸리티
├── test_functions.py     # 테스트 함수들
├── main.py              # 메인 실행 파일
├── requirements.txt     # 의존성 파일
└── README.md           # 프로젝트 설명
```

## 🚀 사용법

### 기본 실행
```bash
python main.py
```

### 개별 모듈 사용
```python
from axon_ipc_driver import AxonIPCDriver
from constants import AXON_IPC_CM1_FILE

# 드라이버 초기화
with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
    # 데이터 전송
    packet = ipc.make_packet(0, 0x01, 0x01, 501)
    ipc.write_data(packet)
    
    # 데이터 수신
    data = ipc.read_data()
    if data:
        print(f"수신: {data.hex()}")
```

## 🔧 주요 기능

### 1. IPC 패킷 생성
- `make_packet()`: 기본 IPC 패킷 생성
- `make_lpa_packet()`: LPA 패킷 생성

### 2. 데이터 통신
- `write_data()`: 데이터 전송
- `read_data()`: 데이터 수신
- `read_data_nonblocking()`: 논블로킹 읽기

### 3. 인터럽트 처리
- `wait_for_data_interrupt()`: 인터럽트 대기
- `read_data_with_interrupt()`: 인터럽트 읽기
- `read_clean_data()`: 깨끗한 데이터 읽기

### 4. 버퍼 관리
- `clear_buffer()`: 버퍼 클리어
- `parse_multiple_packets()`: 여러 패킷 분리

## 📋 테스트 함수

- `test_wr1_command()`: wr1 명령어 테스트
- `test_can_command()`: can 명령어 테스트
- `continuous_read_test()`: 연속 읽기 테스트
- `clean_interrupt_monitoring()`: 깨끗한 인터럽트 모니터링

## 🔗 의존성

현재는 Python 표준 라이브러리만 사용합니다:
- `os`: 파일 시스템 및 디바이스 접근
- `time`: 시간 관련 함수
- `select`: 비동기 I/O
- `typing`: 타입 힌트

## 📝 참고사항

- C 코드의 `axon-ipc-dev.c`의 `ipc_make_packet` 함수와 동일한 패킷 구조 사용
- IPC 디바이스 파일 경로: `/dev/axon_ipc_cm0`, `/dev/axon_ipc_cm1`, `/dev/axon_ipc_cm2`, `/dev/axon_ipc_cmn`
- 컨텍스트 매니저(`with` 문) 지원으로 자동 리소스 관리