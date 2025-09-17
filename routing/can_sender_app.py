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
        
        # 데이터 검증을 위한 변수들
        validation_results = []
        validation_lock = threading.Lock()
        send_timestamps = {}  # 송신 시간 기록용
        send_timestamps_lock = threading.Lock()

        def validate_received_data(received_data, rx_frame_info, recv_time_ns):
            """수신된 데이터를 CSV의 예상 데이터와 비교하여 검증"""
            try:
                # 수신된 데이터에서 정보 추출
                received_port = rx_frame_info['source_port']
                received_can_id = rx_frame_info['can_id'] if not rx_frame_info['is_extended'] else rx_frame_info['ext_can_id']
                received_payload = received_data
                
                # 송신 데이터와 매칭되는 항목 찾기
                best_match = None
                min_time_diff = float('inf')
                
                with send_timestamps_lock:
                    for idx, send_info in send_timestamps.items():
                        # CAN ID와 포트가 일치하는지 확인
                        if send_info['can_id'] == received_can_id:
#                        and send_info['port'] == received_port

                            
                            # 시간 차이 계산 (가장 가까운 송신 시간 찾기)
                            time_diff = abs(recv_time_ns - send_info['send_time_ns'])
                            if time_diff < min_time_diff:
                                min_time_diff = time_diff
                                best_match = (idx, send_info)
                
                if best_match is None:
                    return {
                        'valid': False,
                        'reason': '매칭되는 송신 데이터를 찾을 수 없음',
                        'received_port': received_port,
                        'received_can_id': f"0x{received_can_id:X}",
                        'received_payload': received_payload.hex()
                    }
                
                idx, send_info = best_match
                delay_ms = min_time_diff / 1_000_000
                
                # 예상 데이터와 비교
                expected_data_hex = send_info['expected_data']
                if expected_data_hex.startswith('0x'):
                    expected_data = bytes.fromhex(expected_data_hex[2:])
                else:
                    expected_data = expected_data_hex.encode('utf-8')
                
                # 데이터 검증
                data_match = received_payload == expected_data
                port_match = received_port == send_info['expected_dst_port']
                can_id_match = received_can_id == send_info['can_id']
                
                validation_result = {
                    'valid': data_match and port_match and can_id_match,
                    'send_index': idx,
                    'delay_ms': delay_ms,
                    'received_port': received_port,
                    'expected_port': send_info['expected_dst_port'],
                    'received_can_id': f"0x{received_can_id:X}",
                    'expected_can_id': f"0x{send_info['can_id']:X}",
                    'received_payload': received_payload.hex(),
                    'expected_payload': expected_data.hex(),
                    'data_match': data_match,
                    'port_match': port_match,
                    'can_id_match': can_id_match,
                    'expected_msg_id': send_info['expected_msg_id'],
                    'expected_cycle_time': send_info['expected_cycle_time']
                }
                
                return validation_result
                
            except Exception as e:
                return {
                    'valid': False,
                    'reason': f'검증 중 오류 발생: {e}',
                    'received_port': received_port if 'received_port' in locals() else 'unknown',
                    'received_can_id': f"0x{received_can_id:X}" if 'received_can_id' in locals() else 'unknown',
                    'received_payload': received_payload.hex() if 'received_payload' in locals() else 'unknown'
                }

        def sender_thread():
            """CAN 데이터 송신 스레드"""
            nonlocal stop_event, send_completed, test_start_ns, accumulated_cycle_time_sec, send_timestamps
            
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
                        
                        # 송신 시간 기록 (검증용)
                        with send_timestamps_lock:
                            send_timestamps[idx] = {
                                'send_time_ns': send_end_ns,
                                'can_id': item['can_id'],
                                'port': item['port_n'],
                                'data': item['data'],
                                'expected_dst_port': item['dst_port_n'],
                                'expected_data': item['row_data']['rsv_msg'],
                                'expected_msg_id': item['row_data']['rsv_msg_id'],
                                'expected_cycle_time': item['row_data']['rsv_cycle_time']
                            }

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
            nonlocal stop_event, received_count, received_lock, send_completed, test_start_ns, validation_results, send_timestamps
            
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
                            # 수신 프레임 헤더 파싱 (15바이트)
                            rx_frame_info = parse_can_header(parsed['can_header'])
                            
                            # 데이터 검증 수행
                            validation_result = validate_received_data(parsed['payload'], rx_frame_info, recv_end_ns)
                            
                            # 검증 결과 저장
                            with validation_lock:
                                validation_results.append(validation_result)
                            
                            print(f"[수신 스레드] 패킷 {current_count:3d}: {len(data)}바이트 | "
                                  f"수신시간: {recv_time_ms:.3f}ms | "
                                  f"총경과: {total_elapsed_ms:.3f}ms | "
                                  f"수신타임스탬프: {recv_end_ts.tv_sec:10d}.{recv_end_ts.tv_nsec:09d} | "
                                  f"상대시간: {relative_time_ms:.3f}ms")
                            print(f"  ✓ LPA 패킷 파싱 성공!")
                            print(f"  CMD: 0x{parsed['cmd']:04x}, Port: {parsed['port']}")
                            print(f"  CRC: 0x{parsed['crc']:04x} ({'유효' if parsed['crc_valid'] else '무효'})")
                            print(f"  --- 수신 프레임 정보 ---")
                            print(f"  프레임 타입: {rx_frame_info['frame_type']}")
                            print(f"  소스 포트: {rx_frame_info['source_port']}")
                            print(f"  타임스탬프 (ns): {rx_frame_info['timestamp_ns']}")
                            print(f"  타임스탬프 (us): {rx_frame_info['timestamp_us_h']:08x}{rx_frame_info['timestamp_us_l']:08x}")
                            print(f"  프로토콜 타입: {rx_frame_info['protocol_type']}")
                            if rx_frame_info['is_extended']:
                                print(f"  Extended CAN ID: 0x{rx_frame_info['ext_can_id']:08X}")
                            else:
                                print(f"  Standard CAN ID: 0x{rx_frame_info['can_id']:03X}")
                            print(f"  LIN ID: {rx_frame_info['lin_id']}")
                            print(f"  CAN FD: {rx_frame_info['is_fd']}, RTR: {rx_frame_info['is_remote']}")
                            print(f"  --- 진짜 Payload ---")
                            print(f"  실제 CAN 데이터: {parsed['payload'].hex()}")
                            print(f"  Payload 길이: {len(parsed['payload'])}바이트")
                            print(f"  전체 데이터: {data.hex()}")
                            
                            # 검증 결과 출력
                            print(f"  --- 데이터 검증 결과 ---")
                            if validation_result['valid']:
                                print(f"  ✅ 검증 성공!")
                                print(f"  송신 인덱스: {validation_result['send_index']}")
                                print(f"  지연 시간: {validation_result['delay_ms']:.3f}ms")
                                print(f"  예상 포트: {validation_result['expected_port']} ✓")
                                print(f"  예상 CAN ID: {validation_result['expected_can_id']} ✓")
                                print(f"  예상 데이터: {validation_result['expected_payload']} ✓")
                                print(f"  예상 메시지 ID: {validation_result['expected_msg_id']}")
                                print(f"  예상 주기: {validation_result['expected_cycle_time']}ms")
                            else:
                                print(f"  ❌ 검증 실패!")
                                if 'reason' in validation_result:
                                    print(f"  실패 이유: {validation_result['reason']}")
                                else:
                                    print(f"  포트 매칭: {'✓' if validation_result.get('port_match', False) else '✗'}")
                                    print(f"  CAN ID 매칭: {'✓' if validation_result.get('can_id_match', False) else '✗'}")
                                    print(f"  데이터 매칭: {'✓' if validation_result.get('data_match', False) else '✗'}")
                                    print(f"  수신 포트: {validation_result.get('received_port', 'unknown')}")
                                    print(f"  예상 포트: {validation_result.get('expected_port', 'unknown')}")
                                    print(f"  수신 CAN ID: {validation_result.get('received_can_id', 'unknown')}")
                                    print(f"  예상 CAN ID: {validation_result.get('expected_can_id', 'unknown')}")
                                    print(f"  수신 데이터: {validation_result.get('received_payload', 'unknown')}")
                                    print(f"  예상 데이터: {validation_result.get('expected_payload', 'unknown')}")
                                    if 'delay_ms' in validation_result:
                                        print(f"  지연 시간: {validation_result['delay_ms']:.3f}ms")
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
            
            # 검증 통계 출력
            print(f"\n=== 데이터 검증 통계 ===")
            with validation_lock:
                total_validations = len(validation_results)
                successful_validations = sum(1 for v in validation_results if v['valid'])
                failed_validations = total_validations - successful_validations
                
                print(f"총 검증된 패킷: {total_validations}개")
                print(f"검증 성공: {successful_validations}개 ({successful_validations/total_validations*100:.1f}%)")
                print(f"검증 실패: {failed_validations}개 ({failed_validations/total_validations*100:.1f}%)")
                
                if successful_validations > 0:
                    delays = [v['delay_ms'] for v in validation_results if v['valid'] and 'delay_ms' in v]
                    if delays:
                        avg_delay = sum(delays) / len(delays)
                        min_delay = min(delays)
                        max_delay = max(delays)
                        print(f"지연 시간 통계:")
                        print(f"  평균: {avg_delay:.3f}ms")
                        print(f"  최소: {min_delay:.3f}ms")
                        print(f"  최대: {max_delay:.3f}ms")
                
                # 실패한 검증 상세 정보
                if failed_validations > 0:
                    print(f"\n=== 검증 실패 상세 정보 ===")
                    for i, result in enumerate(validation_results):
                        if not result['valid']:
                            print(f"실패 #{i+1}:")
                            if 'reason' in result:
                                print(f"  이유: {result['reason']}")
                            else:
                                print(f"  포트: {result.get('received_port', 'unknown')} vs {result.get('expected_port', 'unknown')}")
                                print(f"  CAN ID: {result.get('received_can_id', 'unknown')} vs {result.get('expected_can_id', 'unknown')}")
                                print(f"  데이터: {result.get('received_payload', 'unknown')} vs {result.get('expected_payload', 'unknown')}")
            
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
