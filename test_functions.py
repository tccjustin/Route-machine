#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리눅스 시간 측정 테스트 함수들
"""

import time
import ctypes
import ctypes.util
import multiprocessing as mp
import threading
from axon_ipc_driver import AxonIPCDriver
from constants import AXON_IPC_CM0_FILE, AXON_IPC_CM1_FILE, TCC_IPC_CMD_AP_TEST


def test_linux_time_counting():
    """리눅스 시간을 1초 단위로 카운트하는 테스트"""
    print("\n=== 리눅스 시간 카운트 테스트 ===")
    
    # 리눅스 시스템 콜을 위한 라이브러리 로드
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    
    # CLOCK_MONOTONIC_RAW 정의
    CLOCK_MONOTONIC_RAW = 4
    
    # timespec 구조체 정의
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
    
    # clock_gettime 함수 정의
    clock_gettime = libc.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
    clock_gettime.restype = ctypes.c_int
    
    print("리눅스 시간을 1초 단위로 카운트합니다...")
    print("종료하려면 Ctrl+C를 누르세요.")
    print()
    
    try:
        count = 0
        start_ts = timespec()
        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
        start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
        
        print(f"시작 시간: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
        print("=" * 60)
        
        while True:
            count += 1
            
            # 현재 시간 측정
            current_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(current_ts))
            current_ns = current_ts.tv_sec * 1_000_000_000 + current_ts.tv_nsec
            
            # 경과 시간 계산
            elapsed_ns = current_ns - start_ns
            elapsed_sec = elapsed_ns / 1_000_000_000
            
            print(f"카운트: {count:3d} | "
                  f"현재시간: {current_ts.tv_sec:10d}.{current_ts.tv_nsec:09d} | "
                  f"경과시간: {elapsed_sec:6.1f}초")
            
            # 1초 대기
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("=" * 60)
        print(f"카운트 테스트 완료. 총 {count}회 카운트했습니다.")


def test_linux_time_precision_counting():
    """리눅스 시간을 0.1초 단위로 고정밀 카운트하는 테스트"""
    print("\n=== 리눅스 고정밀 시간 카운트 테스트 ===")
    
    # 리눅스 시스템 콜을 위한 라이브러리 로드
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    
    # CLOCK_MONOTONIC_RAW 정의
    CLOCK_MONOTONIC_RAW = 4
    
    # timespec 구조체 정의
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
    
    # clock_gettime 함수 정의
    clock_gettime = libc.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
    clock_gettime.restype = ctypes.c_int
    
    print("리눅스 시간을 0.1초 단위로 고정밀 카운트합니다...")
    print("종료하려면 Ctrl+C를 누르세요.")
    print()
    
    try:
        count = 0
        start_ts = timespec()
        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
        start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
        
        print(f"시작 시간: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
        print("=" * 80)
        
        while True:
            count += 1
            
            # 현재 시간 측정
            current_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(current_ts))
            current_ns = current_ts.tv_sec * 1_000_000_000 + current_ts.tv_nsec
            
            # 경과 시간 계산
            elapsed_ns = current_ns - start_ns
            elapsed_sec = elapsed_ns / 1_000_000_000
            
            # 예상 시간 (0.1초 단위)
            expected_sec = count * 0.1
            
            print(f"카운트: {count:4d} | "
                  f"현재시간: {current_ts.tv_sec:10d}.{current_ts.tv_nsec:09d} | "
                  f"경과시간: {elapsed_sec:8.3f}초 | "
                  f"예상시간: {expected_sec:8.3f}초 | "
                  f"차이: {(elapsed_sec - expected_sec):+6.3f}초")
            
            # 0.1초 대기
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("=" * 80)
        print(f"고정밀 카운트 테스트 완료. 총 {count}회 카운트했습니다.")


def test_linux_time_with_ipc_counting():
    """IPC와 함께 리눅스 시간을 카운트하는 테스트"""
    print("\n=== IPC와 함께 리눅스 시간 카운트 테스트 ===")
    
    # 리눅스 시스템 콜을 위한 라이브러리 로드
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    
    # CLOCK_MONOTONIC_RAW 정의
    CLOCK_MONOTONIC_RAW = 4
    
    # timespec 구조체 정의
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
    
    # clock_gettime 함수 정의
    clock_gettime = libc.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
    clock_gettime.restype = ctypes.c_int
    
    print("IPC와 함께 리눅스 시간을 카운트합니다...")
    print("종료하려면 Ctrl+C를 누르세요.")
    print()
    
    try:
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            count = 0
            start_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
            start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
            
            print(f"시작 시간: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
            print("=" * 100)
            
            while True:
                count += 1
                
                # 현재 시간 측정
                current_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(current_ts))
                current_ns = current_ts.tv_sec * 1_000_000_000 + current_ts.tv_nsec
                
                # 경과 시간 계산
                elapsed_ns = current_ns - start_ns
                elapsed_sec = elapsed_ns / 1_000_000_000
                
                # IPC 데이터 읽기 시도
                ipc_data = ipc.read_data()
                data_info = f"데이터: {len(ipc_data)}바이트" if ipc_data else "데이터: 없음"
                
                print(f"카운트: {count:3d} | "
                      f"현재시간: {current_ts.tv_sec:10d}.{current_ts.tv_nsec:09d} | "
                      f"경과시간: {elapsed_sec:6.1f}초 | "
                      f"{data_info}")
                
                # 1초 대기
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("=" * 100)
        print(f"IPC 카운트 테스트 완료. 총 {count}회 카운트했습니다.")


def test_linux_time_visual_counting():
    """리눅스 시간을 시각적으로 확인할 수 있는 카운트"""
    print("\n=== 리눅스 시간 시각적 카운트 테스트 ===")
    
    # 리눅스 시스템 콜을 위한 라이브러리 로드
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    
    # CLOCK_MONOTONIC_RAW 정의
    CLOCK_MONOTONIC_RAW = 4
    
    # timespec 구조체 정의
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
    
    # clock_gettime 함수 정의
    clock_gettime = libc.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
    clock_gettime.restype = ctypes.c_int
    
    print("리눅스 시간을 시각적으로 확인합니다...")
    print("종료하려면 Ctrl+C를 누르세요.")
    print()
    
    try:
        count = 0
        start_ts = timespec()
        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
        start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
        
        print(f"시작 시간: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
        print("=" * 80)
        
        while True:
            count += 1
            
            # 현재 시간 측정
            current_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(current_ts))
            current_ns = current_ts.tv_sec * 1_000_000_000 + current_ts.tv_nsec
            
            # 경과 시간 계산
            elapsed_ns = current_ns - start_ns
            elapsed_sec = elapsed_ns / 1_000_000_000
            
            # 시각적 출력
            print(f"카운트: {count:4d} | "
                  f"현재시간: {current_ts.tv_sec:10d}.{current_ts.tv_nsec:09d} | "
                  f"경과시간: {elapsed_sec:8.3f}초 | "
                  f"예상시간: {count:8.1f}초 | "
                  f"차이: {(elapsed_sec - count):+6.3f}초")
            
            # 1초 대기
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("=" * 80)
        print(f"시각적 카운트 테스트 완료. 총 {count}회 카운트했습니다.")


def test_linux_native_timing():
    """리눅스 네이티브 타이밍 함수 테스트"""
    print("\n=== 리눅스 네이티브 타이밍 테스트 ===")
    
    try:
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            print("1. CLOCK_MONOTONIC 타이밍 테스트")
            data, stats = ipc.read_data_linux_native_timing(timeout_seconds=3.0)
            print(f"결과: {stats}")
            print()
            
            print("2. CLOCK_MONOTONIC_RAW 고해상도 타이밍 테스트")
            data, stats = ipc.read_data_linux_high_resolution(timeout_seconds=3.0, measurement_rounds=3)
            print(f"결과: {stats}")
            print()
            
            print("3. CLOCK_REALTIME 실시간 타이밍 테스트")
            data, stats = ipc.read_data_linux_realtime(timeout_seconds=3.0)
            print(f"결과: {stats}")
            
    except Exception as e:
        print(f"네이티브 타이밍 테스트 실패: {e}")


def test_can_packet_send():
    """CAN 패킷 전송 테스트"""
    print("\n=== CAN 패킷 전송 테스트 ===")
    
    # C 코드에서 사용하는 값들
    data_len = 8
    ipc_len = data_len + 5  # LPA_TX_HDR_SIZE = 5
    port_n = 3  # CAN channel 1
    can_id = 0x52  # CAN ID
    
    # 데이터 생성 (C 코드와 동일)
    data = bytearray(data_len)
    for i in range(data_len):
        data[i] = i
    
    print(f"CAN channel: {port_n}, CAN ID: 0x{can_id:03x}, Data length: {data_len}")
    print(f"Data: {data.hex()}")
    
    try:
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            # LPA 패킷 생성 (C 코드의 ipc_Lpa_packet과 동일)
            packet = ipc.make_lpa_packet(data, TCC_IPC_CMD_AP_TEST, port_n, ipc_len)
            print(f"LPA 패킷 크기: {len(packet)} 바이트")
            print(f"LPA 패킷 헥스: {packet.hex()}")
            
            # 데이터 전송
            bytes_written = ipc.write_data(packet)
            print(f"전송된 바이트: {bytes_written}")
            
            # 잠시 대기 후 응답 확인
            time.sleep(0.2)
            received = ipc.read_data()
            if received:
                print(f"수신된 데이터: {received.hex()}")
            else:
                print("수신된 데이터 없음")
                
    except Exception as e:
        print(f"CAN 패킷 전송 테스트 실패: {e}")


def test_can_packet_send_with_timing():
    """CAN 패킷 전송 + 타이밍 측정 테스트"""
    print("\n=== CAN 패킷 전송 + 타이밍 측정 테스트 ===")
    
    # CAN 패킷 데이터 준비
    data_len = 8
    ipc_len = data_len + 5
    port_n = 3
    can_id = 0x52
    
    data = bytearray(data_len)
    for i in range(data_len):
        data[i] = i
    
    print(f"CAN channel: {port_n}, CAN ID: 0x{can_id:03x}, Data length: {data_len}")
    print(f"Data: {data.hex()}")
    
    try:
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            # LPA 패킷 생성
            packet = ipc.make_lpa_packet(data, TCC_IPC_CMD_AP_TEST, port_n, ipc_len)
            print(f"LPA 패킷 크기: {len(packet)} 바이트")
            
            # 패킷 전송
            print("패킷 전송 중...")
            bytes_written = ipc.write_data(packet)
            print(f"전송 완료: {bytes_written} 바이트")
            
            # 타이밍 측정으로 응답 대기
            print("응답 대기 중 (타이밍 측정)...")
            response_data, timing_stats = ipc.read_data_linux_high_resolution(
                timeout_seconds=5.0, 
                measurement_rounds=1
            )
            
            if response_data:
                print(f"응답 수신: {len(response_data)} 바이트")
                print(f"응답 데이터: {response_data.hex()}")
                print(f"응답 시간: {timing_stats.get('avg_read_time_ms', 0):.3f}ms")
            else:
                print("응답 없음 (타임아웃)")
                print(f"대기 시간: {timing_stats.get('avg_total_time_ms', 0):.3f}ms")
                
    except Exception as e:
        print(f"CAN 패킷 전송 + 타이밍 테스트 실패: {e}")


def test_can_packet_continuous_send():
    """CAN 패킷 연속 전송 테스트"""
    print("\n=== CAN 패킷 연속 전송 테스트 ===")
    
    data_len = 8
    ipc_len = data_len + 5
    port_n = 3
    can_id = 0x52
    
    print(f"CAN channel: {port_n}, CAN ID: 0x{can_id:03x}")
    print("연속 전송을 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    print()
    
    try:
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            count = 0
            while True:
                count += 1
                
                # 데이터 생성 (카운터 포함)
                data = bytearray(data_len)
                for i in range(data_len):
                    data[i] = (count + i) % 256
                
                # LPA 패킷 생성
                packet = ipc.make_lpa_packet(data, TCC_IPC_CMD_AP_TEST, port_n, ipc_len)
                
                # 패킷 전송
                bytes_written = ipc.write_data(packet)
                
                print(f"전송 {count:4d}: {bytes_written}바이트 | 데이터: {data.hex()}")
                
                # 응답 확인
                response = ipc.read_data()
                if response:
                    print(f"  응답: {len(response)}바이트 | {response.hex()}")
                
                # 1초 대기
                time.sleep(1)
                
    except KeyboardInterrupt:
        print(f"\n연속 전송 완료. 총 {count}개 패킷 전송했습니다.")
    except Exception as e:
        print(f"연속 전송 테스트 실패: {e}")

def test_can_multithreading():
    """멀티스레딩 CAN 송신/수신 테스트"""
    print("\n=== 멀티스레딩 CAN 송신/수신 테스트 ===")
    
    send_count = 1  # 전송할 패킷 수
    interval_seconds = 0.005 # 전송 간격
    receive_timeout_seconds = 15.0  # 수신 타임아웃
    
    print(f"설정: {send_count}개 패킷 전송, {interval_seconds}초 간격, {receive_timeout_seconds}초 수신 타임아웃")
    print("수신 스레드는 프로그램 강제 종료(Ctrl+C)까지 계속 실행됩니다.")
    print()
    
    # 스레드 간 통신을 위한 이벤트
    stop_event = threading.Event()
    received_count = 0
    received_lock = threading.Lock()
    
    # 송신 시간 기록을 위한 리스트
    send_times = []
    send_times_lock = threading.Lock()
    
    def sender_thread():
        """CAN 패킷 송신 스레드"""
        nonlocal stop_event, send_times, send_times_lock
        
        print(f"[송신 스레드] 시작 - Thread ID: {threading.current_thread().ident}")
        
        # 리눅스 시스템 콜을 위한 라이브러리 로드
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        CLOCK_MONOTONIC_RAW = 4
        
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
        
        clock_gettime = libc.clock_gettime
        clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        clock_gettime.restype = ctypes.c_int
        
        data_len = 8
        ipc_len = data_len + 5
        port_n = 11
        can_id = 0x137
        
        try:
            print(f"[송신 스레드] {send_count}개 패킷 전송 시작")
            
            for i in range(send_count):
                if stop_event.is_set():
                    break
                
                # 송신 시작 시간 측정
                send_start_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(send_start_ts))
                
                # 데이터 생성 (카운터 포함)
                data = bytearray(data_len)
                for j in range(data_len):
                    data[j] = (i + j) % 256
                
                # LPA 패킷 생성 (CAN 헤더 포함)
                from packet_utils import make_lpa_packet_with_can_header
                packet = make_lpa_packet_with_can_header(data, can_id, False, TCC_IPC_CMD_AP_TEST, port_n)
                
                # 패킷 전송
                bytes_written = ipc.write_data(packet)
                
                # 송신 종료 시간 측정
                send_end_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(send_end_ts))
                
                # 송신 시간 계산
                send_start_ns = send_start_ts.tv_sec * 1_000_000_000 + send_start_ts.tv_nsec
                send_end_ns = send_end_ts.tv_sec * 1_000_000_000 + send_end_ts.tv_nsec
                send_time_ns = send_end_ns - send_start_ns
                send_time_ms = send_time_ns / 1_000_000
                
                # 송신 시간 기록
                with send_times_lock:
                    send_times.append({
                        'packet_num': i + 1,
                        'send_time_ns': send_time_ns,
                        'send_time_ms': send_time_ms,
                        'send_timestamp_ns': send_end_ns,
                        'data': data.hex(),
                        'packet': packet.hex()
                    })
                
                print(f"[송신 스레드] 패킷 {i+1:3d}/{send_count}: {bytes_written}바이트 | "
                      f"송신시간: {send_time_ms:.3f}ms | "
                      f"송신타임스탬프: {send_end_ts.tv_sec:10d}.{send_end_ts.tv_nsec:09d} | "
                      f"데이터: {data.hex()} | "
                      f"전체패킷: {packet.hex()}")
                
                # 간격 대기
                time.sleep(interval_seconds)
            
            print(f"[송신 스레드] 전송 완료 - 총 {send_count}개 패킷")
            print(f"[송신 스레드] 수신 스레드는 계속 실행 중... (Ctrl+C로 종료)")
            
        except Exception as e:
            print(f"[송신 스레드] 오류: {e}")
    
    def receiver_thread():
        """CAN 패킷 수신 스레드 (프로그램 종료까지 계속 실행)"""
        nonlocal stop_event, received_count, received_lock, send_times, send_times_lock
        
        print(f"[수신 스레드] 시작 - Thread ID: {threading.current_thread().ident}")
        
        # 리눅스 시스템 콜을 위한 라이브러리 로드
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        CLOCK_MONOTONIC_RAW = 4
        
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
        
        clock_gettime = libc.clock_gettime
        clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        clock_gettime.restype = ctypes.c_int
        
        try:
            print(f"[수신 스레드] 수신 대기 시작 (무한 루프)")
            
            # 시작 시간 측정
            start_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
            start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
            
            while not stop_event.is_set():
                # 수신 시작 시간 측정
                recv_start_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(recv_start_ts))
                
                # 데이터 수신
                data = ipc.read_data()
                
                # 수신 종료 시간 측정
                recv_end_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(recv_end_ts))
                
                if data:
                    with received_lock:
                        received_count += 1
                        current_count = received_count
                    
                    # 수신 시간 계산
                    recv_start_ns = recv_start_ts.tv_sec * 1_000_000_000 + recv_start_ts.tv_nsec
                    recv_end_ns = recv_end_ts.tv_sec * 1_000_000_000 + recv_end_ts.tv_nsec
                    recv_time_ns = recv_end_ns - recv_start_ns
                    recv_time_ms = recv_time_ns / 1_000_000
                    
                    # 전체 경과 시간
                    current_ns = recv_end_ts.tv_sec * 1_000_000_000 + recv_end_ts.tv_nsec
                    total_elapsed_ns = current_ns - start_ns
                    total_elapsed_ms = total_elapsed_ns / 1_000_000
                    
                    # 가장 가까운 송신 시간 찾기
                    closest_send_info = None
                    min_time_diff = float('inf')
                    
                    with send_times_lock:
                        for send_info in send_times:
                            time_diff = abs(recv_end_ns - send_info['send_timestamp_ns'])
                            if time_diff < min_time_diff:
                                min_time_diff = time_diff
                                closest_send_info = send_info
                    
                    # 송신-수신 간격 계산
                    if closest_send_info:
                        send_to_recv_ns = recv_end_ns - closest_send_info['send_timestamp_ns']
                        send_to_recv_ms = send_to_recv_ns / 1_000_000
                        send_info_str = f"송신패킷: {closest_send_info['packet_num']}, 송신시간: {closest_send_info['send_time_ms']:.3f}ms, 송수신간격: {send_to_recv_ms:.3f}ms"
                    else:
                        send_info_str = "송신정보: 없음"
                    
                    print(f"[수신 스레드] 패킷 {current_count:3d}: {len(data)}바이트 | "
                          f"수신시간: {recv_time_ms:.3f}ms | "
                          f"총경과: {total_elapsed_ms:.3f}ms | "
                          f"수신타임스탬프: {recv_end_ts.tv_sec:10d}.{recv_end_ts.tv_nsec:09d} | "
                          f"{send_info_str} | "
                          f"데이터: {data.hex()}")
                else:
                    # 데이터가 없으면 잠시 대기
                    time.sleep(0.001)
            
            print(f"[수신 스레드] 수신 완료 - 총 {received_count}개 패킷 수신")
            
        except Exception as e:
            print(f"[수신 스레드] 오류: {e}")
    
    try:
        # IPC 디바이스 열기 (공유 사용)
        with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
            if not ipc.is_open:
                print("IPC 디바이스 열기 실패")
                return
            
            print("스레드 시작...")
            
            # 송신 스레드 생성
            sender = threading.Thread(target=sender_thread)
            
            # 수신 스레드 생성
            receiver = threading.Thread(target=receiver_thread)
            
            # 수신 스레드 먼저 시작 (송신보다 먼저 대기)
            receiver.start()
            time.sleep(0.1)  # 수신 스레드가 준비될 시간
            
            # 송신 스레드 시작
            sender.start()
            
            print("스레드 실행 중...")
            
            # 송신 스레드 완료 대기
            sender.join()
            
            print("송신 완료. 수신 스레드는 계속 실행 중...")
            print("프로그램을 종료하려면 Ctrl+C를 누르세요.")
            
            # 수신 스레드는 계속 실행 (Ctrl+C로 종료)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nCtrl+C 감지됨. 프로그램을 종료합니다...")
                stop_event.set()
                receiver.join(timeout=2)
                print(f"멀티스레딩 테스트 완료! 전송: {send_count}개, 수신: {received_count}개")
            
            # 전체 통계 출력
            if send_times:
                total_send_time_ms = sum(info['send_time_ms'] for info in send_times)
                avg_send_time_ms = total_send_time_ms / len(send_times)
                print(f"\n=== 송신 통계 ===")
                print(f"총 송신 시간: {total_send_time_ms:.3f}ms")
                print(f"평균 송신 시간: {avg_send_time_ms:.3f}ms")
                print(f"송신 패킷 수: {len(send_times)}개")
            
    except Exception as e:
        print(f"멀티스레딩 테스트 실패: {e}")


if __name__ == "__main__":
    print("리눅스 시간 측정 테스트 함수들")
    print("사용 가능한 함수:")
    print("1. test_linux_time_counting() - 1초 단위 카운트")
    print("2. test_linux_time_precision_counting() - 0.1초 단위 고정밀 카운트")
    print("3. test_linux_time_with_ipc_counting() - IPC와 함께 카운트")
    print("4. test_linux_time_visual_counting() - 시각적 카운트")
    print("5. test_linux_native_timing() - 네이티브 타이밍 함수 테스트")
    print("6. test_can_packet_send() - CAN 패킷 전송 테스트")
    print("7. test_can_packet_send_with_timing() - CAN 패킷 전송 + 타이밍 측정")
    print("8. test_can_packet_continuous_send() - CAN 패킷 연속 전송")
    print("9. test_can_multiprocessing() - 멀티프로세싱 CAN 송신/수신")
    print("10. test_can_multithreading() - 멀티스레딩 CAN 송신/수신")
