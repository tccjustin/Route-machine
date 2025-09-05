#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 데이터를 읽어서 IPC로 CAN 데이터를 전송하는 실제 응용 코드 (멀티스레딩)
"""

import time
import ctypes
import ctypes.util
import threading
import os
import glob
import csv
from axon_ipc_driver import AxonIPCDriver
from constants import AXON_IPC_CM1_FILE, TCC_IPC_CMD_AP_TEST
from packet_utils import make_lpa_packet_with_can_header, parse_lpa_packet_with_can_header, parse_can_header

def can_sender_app():
    """CSV 데이터를 읽어서 IPC로 CAN 데이터를 전송하는 메인 함수 (멀티스레딩)"""
    print("\n=== CSV 기반 CAN 데이터 전송 애플리케이션 (멀티스레딩) ===")
    
    try:
        # CSV 파일 경로 설정
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
        print(f"대상 파일: {os.path.basename(target_csv)}")

        # CSV 데이터 읽기 및 파싱
        csv_data = []
        with open(target_csv, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            
            # 1행: 헤더(사용 안함)
            _header = next(reader, None)
            if _header is None:
                print("빈 CSV 파일입니다.")
                return

            # 2행: 컬럼명 위치 파악
            second_row = next(reader, None)
            if second_row is None:
                print("2번째 행(데이터)이 존재하지 않습니다.")
                return

            # 2번째 줄에서 컬럼명 위치 자동 감지 (중복 등장까지 수집)
            normalized_cells = [(c or '').strip() for c in second_row]

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

            print(f"컬럼 위치 확인:")
            print(f"첫 번째 세트 - Channel: {idx_channel_1}, MsgID: {idx_msgid_1}, MsgValue: {idx_msgvalue_1}, CycleTime: {idx_cycle_1}")
            print(f"두 번째 세트 - Channel: {idx_channel_2}, MsgID: {idx_msgid_2}, MsgValue: {idx_msgvalue_2}, CycleTime: {idx_cycle_2}")

            # 3행부터 데이터 읽기
            for row in reader:
                def safe_get(row, index):
                    return row[index] if 0 <= index < len(row) else ''

                # 첫 번째 세트 (송신용)
                src_ch = safe_get(row, idx_channel_1)
                snt_msg = safe_get(row, idx_msgvalue_1)
                snt_msg_id = safe_get(row, idx_msgid_1)
                snt_cycle_time = safe_get(row, idx_cycle_1)

                # 두 번째 세트 (수신용 - 참고용)
                dst_ch = safe_get(row, idx_channel_2)
                rsv_msg = safe_get(row, idx_msgvalue_2)
                rsv_msg_id = safe_get(row, idx_msgid_2)
                rsv_cycle_time = safe_get(row, idx_cycle_2)

                # 데이터 유효성 검사
                if src_ch and snt_msg and snt_msg_id and snt_cycle_time:
                    try:
                        # src_ch 문자열을 파싱해서 포트 번호로 변환
                        if src_ch.startswith('CANHS'):
                            port_n = int(src_ch[5:])  # CANHS1 -> 1, CANHS8 -> 8
                        elif src_ch.startswith('CANFD'):
                            port_n = int(src_ch[5:]) + 8  # CANFD1 -> 9, CANFD8 -> 16
                        elif src_ch.startswith('LIN'):
                            port_n = int(src_ch[3:])  # CANFD1 -> 9, CANFD8 -> 16
                        else:
                            print(f"알 수 없는 채널 형식: {src_ch}")
                            continue
                        
                        # dst_ch 문자열을 파싱해서 포트 번호로 변환
                        if dst_ch.startswith('CANHS'):
                            dst_port_n = int(dst_ch[5:])  # CANHS1 -> 1, CANHS8 -> 8
                        elif dst_ch.startswith('CANFD'):
                            dst_port_n = int(dst_ch[5:]) + 8  # CANFD1 -> 9, CANFD8 -> 16
                        elif dst_ch.startswith('LIN'):
                            dst_port_n = int(dst_ch[3:])  # CANFD1 -> 9, CANFD8 -> 16
                        else:
                            dst_port_n = 0  # 기본값
                        
                        can_id = int(snt_msg_id, 16) if snt_msg_id.startswith('0x') else int(snt_msg_id)
                        cycle_time = float(snt_cycle_time) / 1000.0  # ms를 초로 변환
                        
                        # MsgValue를 바이트 데이터로 변환
                        if snt_msg.startswith('0x'):
                            # 16진수 문자열인 경우
                            data = bytes.fromhex(snt_msg[2:])
                        else:
                            # 일반 문자열인 경우
                            data = snt_msg.encode('utf-8')
                        
                        csv_data.append({
                            'port_n': port_n,
                            'can_id': can_id,
                            'data': data,
                            'cycle_time': cycle_time,
                            'dst_port_n': dst_port_n,
                            'row_data': {
                                'src_ch': src_ch,
                                'snt_msg': snt_msg,
                                'snt_msg_id': snt_msg_id,
                                'snt_cycle_time': snt_cycle_time,
                                'dst_ch': dst_ch,
                                'rsv_msg': rsv_msg,
                                'rsv_msg_id': rsv_msg_id,
                                'rsv_cycle_time': rsv_cycle_time
                            }
                        })
                    except (ValueError, TypeError) as e:
                        print(f"데이터 변환 오류 (행 {len(csv_data) + 3}): {e}")
                        continue

        if not csv_data:
            print("유효한 CSV 데이터가 없습니다.")
            return

        print(f"\n총 {len(csv_data)}개의 유효한 데이터를 읽었습니다.")

        # 메인 스레드에서 IPC 디바이스 열기
        print("IPC 디바이스 열기 시도...")
        try:
            ipc_driver = AxonIPCDriver(AXON_IPC_CM1_FILE)
            if not ipc_driver.open_device():
                print("IPC 디바이스 열기 실패")
                return
            print("IPC 디바이스 열기 성공")
        except Exception as e:
            print(f"IPC 디바이스 열기 오류: {e}")
            return

        # 스레드 간 통신을 위한 변수들
        stop_event = threading.Event()
        received_count = 0
        received_lock = threading.Lock()
        send_completed = threading.Event()
        
        # IPC 디바이스 접근을 위한 락
        ipc_lock = threading.Lock()

        test_start_ns = 0
        accumulated_cycle_time_sec = 0

        def sender_thread():
            """CAN 데이터 송신 스레드"""
            nonlocal stop_event, send_completed, test_start_ns, accumulated_cycle_time_sec
            
            print(f"[송신 스레드] 시작 - Thread ID: {threading.current_thread().ident}")
            print("[송신 스레드] 데이터 전송을 시작합니다...")

            try:
                # 리눅스 시스템 콜을 위한 라이브러리 로드
                libc = ctypes.CDLL(ctypes.util.find_library('c'))
                CLOCK_MONOTONIC_RAW = 4

                class timespec(ctypes.Structure):
                    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

                clock_gettime = libc.clock_gettime
                clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
                clock_gettime.restype = ctypes.c_int

                firstflag = 0

                # 데이터 전송
                for idx, item in enumerate(csv_data, start=1):
                    if stop_event.is_set():
                        break
                        
                    try:
                        # 전송 시작 시간 측정
                        send_start_ts = timespec()
                        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(send_start_ts))

                        if firstflag == 0:
                            firstflag = 1
                            test_start_ns = send_start_ts.tv_sec * 1_000_000_000 + send_start_ts.tv_nsec
                            continue

                        # LPA 패킷 생성 (CAN 헤더 포함)
                        packet = make_lpa_packet_with_can_header(
                            item['data'], 
                            item['can_id'], 
                            False, 
                            TCC_IPC_CMD_AP_TEST, 
                            item['port_n']
                        )

                        # IPC 디바이스에 안전하게 패킷 전송
                        with ipc_lock:
                            bytes_written = ipc_driver.write_data(packet)

                        # 전송 종료 시간 측정
                        send_end_ts = timespec()
                        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(send_end_ts))

                        # 전송 시간 계산
                        send_start_ns = send_start_ts.tv_sec * 1_000_000_000 + send_start_ts.tv_nsec
                        send_end_ns = send_end_ts.tv_sec * 1_000_000_000 + send_end_ts.tv_nsec
                        send_time_ns = send_end_ns - send_start_ns
                        send_time_ms = send_time_ns / 1_000_000
                        relative_time_ms = (send_start_ns - test_start_ns) / 1_000_000

                        accumulated_cycle_time_sec += item['cycle_time']
                        sleep_time = accumulated_cycle_time_sec - (send_time_ms + relative_time_ms)/1000.0

                        print(f"[송신 스레드] [{idx:04d}/{len(csv_data)}] 전송 완료 | "
                              f"Port: {item['port_n']}, CAN ID: 0x{item['can_id']:X}, "
                              f"Data: {item['data'].hex()}, "
                              f"전송시간: {send_time_ms:.3f}ms, "
                              f"대기시간: {item['cycle_time']:.3f}초,"
                              f"상대시간: {relative_time_ms:.3f}ms"
                              f"누적시간: {accumulated_cycle_time_sec:.3f}ms"
                              f"대기시간: {(send_time_ms + relative_time_ms)/1000:.3f}초"
                            f"sleep_time: {sleep_time:.3f}초"
                              )
                        
                        


                        # CycleTime만큼 대기
                        # time.sleep(item['cycle_time'])
                        time.sleep(sleep_time)

                    except Exception as e:
                        print(f"[송신 스레드] [{idx:04d}/{len(csv_data)}] 전송 오류: {e}")
                        continue

                print(f"[송신 스레드] 전송 완료! 총 {len(csv_data)}개 패킷 전송")
                send_completed.set()

            except Exception as e:
                print(f"[송신 스레드] 오류: {e}")

        def receiver_thread():
            """CAN 데이터 수신 스레드"""
            nonlocal stop_event, received_count, received_lock, send_completed, test_start_ns
            
            print(f"[수신 스레드] 시작 - Thread ID: {threading.current_thread().ident}")
            print("[수신 스레드] 수신 대기 시작...")

            try:
                # 리눅스 시스템 콜을 위한 라이브러리 로드
                libc = ctypes.CDLL(ctypes.util.find_library('c'))
                CLOCK_MONOTONIC_RAW = 4

                class timespec(ctypes.Structure):
                    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

                clock_gettime = libc.clock_gettime
                clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
                clock_gettime.restype = ctypes.c_int

                # 시작 시간 측정
                start_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
                start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec

                while not stop_event.is_set():
                    # 수신 시작 시간 측정
                    recv_start_ts = timespec()
                    clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(recv_start_ts))

                    # IPC 디바이스에서 안전하게 데이터 수신
                    data = None
                    with ipc_lock:
                        data = ipc_driver.read_data()

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

                        relative_time_ms = (recv_end_ns - test_start_ns) / 1_000_000

                        # LPA 패킷 파싱 시도
                        parsed = parse_lpa_packet_with_can_header(data)
                        if parsed['valid']:
                            # CAN 헤더 상세 파싱
                            can_info = parse_can_header(parsed['can_header'])
                            
                            print(f"[수신 스레드] 패킷 {current_count:3d}: {len(data)}바이트 | "
                                  f"수신시간: {recv_time_ms:.3f}ms | "
                                  f"총경과: {total_elapsed_ms:.3f}ms | "
                                  f"수신타임스탬프: {recv_end_ts.tv_sec:10d}.{recv_end_ts.tv_nsec:09d} | "
                                  f"상대시간: {relative_time_ms:.3f}ms")
                            print(f"  ✓ LPA 패킷 파싱 성공!")
                            print(f"  CMD: 0x{parsed['cmd']:04x}, Port: {parsed['port']}")
                            print(f"  CAN ID: 0x{can_info['can_id']:X} ({'Extended' if can_info['is_extended'] else 'Standard'})")
                            print(f"  CAN FD: {can_info['is_fd']}, RTR: {can_info['rtr']}, BRS: {can_info['brs']}")
                            print(f"  CAN 헤더: {parsed['can_header'].hex()}")
                            print(f"  실제 Payload: {parsed['payload'].hex()}")
                            print(f"  CRC: 0x{parsed['crc']:04x} ({'유효' if parsed['crc_valid'] else '무효'})")
                            print(f"  전체 데이터: {data.hex()}")
                        else:
                            # 파싱 실패 시 기존 방식으로 출력
                            print(f"[수신 스레드] 패킷 {current_count:3d}: {len(data)}바이트 | "
                                  f"수신시간: {recv_time_ms:.3f}ms | "
                                  f"총경과: {total_elapsed_ms:.3f}ms | "
                                  f"수신타임스탬프: {recv_end_ts.tv_sec:10d}.{recv_end_ts.tv_nsec:09d} | "
                                  f"데이터: {data.hex()} | "
                                  f"상대시간: {relative_time_ms:.3f}ms")
                            print(f"  ⚠ LPA 패킷 파싱 실패 - 일반 데이터로 처리")
                    else:
                        # 데이터가 없으면 잠시 대기
                        time.sleep(0.001)

                print(f"[수신 스레드] 수신 완료 - 총 {received_count}개 패킷 수신")

            except Exception as e:
                print(f"[수신 스레드] 오류: {e}")

        # 스레드 생성 및 시작
        print("멀티스레딩 시작...")
        
        # 수신 스레드 먼저 시작 (송신보다 먼저 대기)
        receiver = threading.Thread(target=receiver_thread)
        receiver.start()
        time.sleep(0.1)  # 수신 스레드가 준비될 시간
        
        # 송신 스레드 시작
        sender = threading.Thread(target=sender_thread)
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
            print(f"멀티스레딩 애플리케이션 완료! 전송: {len(csv_data)}개, 수신: {received_count}개")
        finally:
            # IPC 디바이스 정리
            try:
                if ipc_driver and ipc_driver.is_open:
                    ipc_driver.close()
                    print("IPC 디바이스 정리 완료")
            except Exception as e:
                print(f"IPC 디바이스 정리 오류: {e}")

    except Exception as e:
        print(f"CAN 전송 애플리케이션 실행 실패: {e}")

if __name__ == "__main__":
    can_sender_app()
