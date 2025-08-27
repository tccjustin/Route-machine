#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 Python 메인 실행 파일 (정리된 버전)
"""

from test_functions import (
    test_linux_time_counting,
    test_linux_time_precision_counting,
    test_linux_time_with_ipc_counting,
    test_linux_time_visual_counting,
    test_linux_native_timing,
    test_can_packet_send,
    test_can_packet_send_with_timing,
    test_can_packet_continuous_send,
    test_can_multithreading
)

def main():
    
    # 멀티스레딩 CAN 송신/수신 테스트 실행
    print("\n멀티스레딩 CAN 송신/수신 테스트를 시작합니다...")
    test_can_multithreading()
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    main()
