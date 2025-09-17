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
import os
import glob
import csv
from axon_ipc_driver import AxonIPCDriver
from constants import AXON_IPC_CM0_FILE, AXON_IPC_CM1_FILE, TCC_IPC_CMD_AP_TEST

def test_can_multithreading():
    """멀티스레딩 CAN 송신/수신 테스트"""
    print("\n=== 멀티스레딩 CAN 송신/수신 테스트 ===")
    
    send_count = 100  # 전송할 패킷 수
    interval_seconds = 0.02 # 전송 간격
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
    print("사용 가능한 함수:")
    print("9. test_can_multiprocessing() - 멀티프로세싱 CAN 송신/수신")
    print("10. test_can_multithreading() - 멀티스레딩 CAN 송신/수신")

def test():
    """csv-file 폴더의 CSV 파일 하나를 읽어 값(일부 행)을 출력"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_dir = os.path.join(base_dir, 'csv-file')
        if not os.path.isdir(csv_dir):
            print(f"CSV 디렉터리를 찾을 수 없습니다: {csv_dir}")
            return

        csv_files = sorted(glob.glob(os.path.join(csv_dir, '*.csv')))
        if not csv_files:
            print(f"CSV 파일이 없습니다: {csv_dir}")
            return

        target_csv = csv_files[0]
        print(f"\n=== CSV 출력 테스트 ===\n대상 파일: {os.path.basename(target_csv)}")

        with open(target_csv, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            max_rows_to_print = 20
            for idx, row in enumerate(reader, start=1):
                print(f"[{idx:04d}] ", row)
                if idx >= max_rows_to_print:
                    print(f"... (총 {max_rows_to_print}행만 표시) ...")
                    break
    except Exception as e:
        print(f"CSV 출력 테스트 실패: {e}")

def test2():
    """2번째 행에서 컬럼 위치(2,4,6,7)를 확인 후, 3번째 행의 동일 컬럼 값 출력"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_dir = os.path.join(base_dir, 'csv-file')
        if not os.path.isdir(csv_dir):
            print(f"CSV 디렉터리를 찾을 수 없습니다: {csv_dir}")
            return

        csv_files = sorted(glob.glob(os.path.join(csv_dir, '*.csv')))
        if not csv_files:
            print(f"CSV 파일이 없습니다: {csv_dir}")
            return

        target_csv = csv_files[0]
        print(f"\n=== CSV 선택 컬럼 연속 출력 테스트 ===\n대상 파일: {os.path.basename(target_csv)}")

        with open(target_csv, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)

            # 1행: 헤더(사용은 안 하지만 소비)
            _header = next(reader, None)
            if _header is None:
                print("빈 CSV 파일입니다.")
                return

            # 2행: 확인용 한 줄 읽기
            second_row = next(reader, None)
            if second_row is None:
                print("2번째 행(데이터)이 존재하지 않습니다.")
                return

            # 2번째 줄에서 컬럼명 위치 자동 감지 (중복 등장까지 수집)
            normalized_cells = [ (c or '').strip() for c in second_row ]

            targets = {
                'Channel': ['Channel'],
                'MsgID': ['MsgID', 'Msg ID', 'MessageID', 'Message ID'],
                'MsgValue': ['MsgValue', 'MessageValue', 'Value'],
                'CycleTime (ms)': ['CycleTime (ms)', 'CycleTime(ms)', 'Cycle Time (ms)']
            }

            def find_indices(candidates):
                candidate_set = set(candidates)
                return [i for i, val in enumerate(normalized_cells) if val in candidate_set]

            channel_idxs = find_indices(targets['Channel'])
            msgid_idxs = find_indices(targets['MsgID'])
            msgvalue_idxs = find_indices(targets['MsgValue'])
            cycle_idxs = find_indices(targets['CycleTime (ms)'])

            # 최소 2개까지 확보 (부족하면 경고)
            if len(channel_idxs) < 2 or len(msgid_idxs) < 2 or len(msgvalue_idxs) < 2 or len(cycle_idxs) < 2:
                print("필수 컬럼명이 2개 이상 존재하지 않습니다.")
                print(f"Channel idxs: {channel_idxs}")
                print(f"MsgID idxs: {msgid_idxs}")
                print(f"MsgValue idxs: {msgvalue_idxs}")
                print(f"CycleTime(ms) idxs: {cycle_idxs}")
                return

            idx_channel_1, idx_channel_2 = channel_idxs[0], channel_idxs[1]
            idx_msgid_1, idx_msgid_2 = msgid_idxs[0], msgid_idxs[1]
            idx_msgvalue_1, idx_msgvalue_2 = msgvalue_idxs[0], msgvalue_idxs[1]
            idx_cycle_1, idx_cycle_2 = cycle_idxs[0], cycle_idxs[1]

            def safe_get(row, index):
                return row[index] if 0 <= index < len(row) else ''

            # 2번째 줄 기준 첫/두번째 세트 확인 출력
            SrcCH = safe_get(second_row, idx_channel_1)
            SntMsg = safe_get(second_row, idx_msgvalue_1)
            SntMsgID = safe_get(second_row, idx_msgid_1)
            SntCycleTime = safe_get(second_row, idx_cycle_1)

            DstCH = safe_get(second_row, idx_channel_2)
            RsvMsg = safe_get(second_row, idx_msgvalue_2)
            RsvMsgID = safe_get(second_row, idx_msgid_2)
            RsvCycleTime = safe_get(second_row, idx_cycle_2)

            print("[2번째 행 확인]")
            print(f"SrcCH={SrcCH}, SntMsg={SntMsg}, SntMsgID={SntMsgID}, SntCycleTime={SntCycleTime}")
            print(f"DstCH={DstCH}, RsvMsg={RsvMsg}, RsvMsgID={RsvMsgID}, RsvCycleTime={RsvCycleTime}")

            # 3행부터 50행까지 동일 컬럼 출력
            print("\n[3번째 행부터 50번째 행까지 출력]")
            line_no = 3
            for row in reader:
                SrcCH = safe_get(row, idx_channel_1)
                SntMsg = safe_get(row, idx_msgvalue_1)
                SntMsgID = safe_get(row, idx_msgid_1)
                SntCycleTime = safe_get(row, idx_cycle_1)

                DstCH = safe_get(row, idx_channel_2)
                RsvMsg = safe_get(row, idx_msgvalue_2)
                RsvMsgID = safe_get(row, idx_msgid_2)
                RsvCycleTime = safe_get(row, idx_cycle_2)

                print(f"[{line_no:04d}] SrcCH={SrcCH}, SntMsg={SntMsg}, SntMsgID={SntMsgID}, SntCycleTime={SntCycleTime} | "
                      f"DstCH={DstCH}, RsvMsg={RsvMsg}, RsvMsgID={RsvMsgID}, RsvCycleTime={RsvCycleTime}")
                if line_no >= 50:
                    break
                line_no += 1
    except Exception as e:
        print(f"CSV 선택 컬럼 출력 테스트 실패: {e}")
