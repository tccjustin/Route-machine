#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 Python 메인 실행 파일
"""

from device_manager import check_devices
from test_functions import test_can_command, clean_interrupt_monitoring

def main():
    """메인 함수"""
    print("AXON IPC 드라이버 Python 테스트 (C 코드와 동일한 패킷 구조)")
    
    # 디바이스 상태 확인
    check_devices()
    test_can_command()
    # 간단한 모니터링만 실행
    print("\n=== 간단한 IPC 모니터링 시작 ===")
    clean_interrupt_monitoring()
    
    print("\n모든 테스트 완료!")

if __name__ == "__main__":
    main()
