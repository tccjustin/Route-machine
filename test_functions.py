#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 함수들
"""

import time
from axon_ipc_driver import AxonIPCDriver
from constants import AXON_IPC_CM1_FILE, TCC_IPC_CMD_AP_TEST


def test_wr1_command():
    """C 코드의 wr1 명령어와 동일한 테스트"""
    print("=== wr1 명령어 테스트 (C 코드와 동일) ===")
    
    # C 코드에서 사용하는 값들
    send_num = 5
    ipc_cmd1 = 0x01
    ipc_cmd2 = 0x01
    ipc_data_length = 501
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("디바이스 열기 실패")
            return
        
        print(f"send_num: {send_num}, cmd1: 0x{ipc_cmd1:02x}, cmd2: 0x{ipc_cmd2:02x}, data_length: {ipc_data_length}")
        
        # C 코드의 wr1 명령어와 동일한 로직
        for i in range(send_num):
            print(f"\n패킷 {i+1}/{send_num} 생성 및 전송:")
            
            # C 코드의 ipc_make_packet과 동일한 패킷 생성
            packet = ipc.make_packet(i, ipc_cmd1, ipc_cmd2, ipc_data_length)
            print(f"패킷 크기: {len(packet)} 바이트")
            print(f"패킷 헥스: {packet.hex()}")
            
            # C 코드의 ipc_write1과 동일한 데이터 전송
            bytes_written = ipc.write_data(packet)
            print(f"전송된 바이트: {bytes_written}")
            
            # 잠시 대기
            time.sleep(0.1)


def test_can_command():
    """C 코드의 can 명령어와 동일한 테스트"""
    print("\n=== can 명령어 테스트 (C 코드와 동일) ===")
    
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
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("디바이스 열기 실패")
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


def continuous_read_test():
    """연속 읽기 테스트"""
    print("\n=== 연속 읽기 테스트 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("디바이스 열기 실패")
            return
        
        print("10초간 데이터를 모니터링합니다...")
        start_time = time.time()
        
        while time.time() - start_time < 10:
            data = ipc.read_data()
            if data:
                print(f"수신: {data.hex()}")
            time.sleep(0.1)


def wait_for_channel1_interrupt():
    """1번 채널을 인터럽트 방식으로 대기"""
    print("\n=== 1번 채널 인터럽트 대기 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("CM1 디바이스 열기 실패")
            return
        
        print("1번 채널에서 인터럽트 방식으로 데이터를 기다리는 중...")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        try:
            while True:
                # 인터럽트 방식으로 데이터 대기 (5초 타임아웃)
                if ipc.wait_for_data_interrupt(5.0):
                    # 데이터가 준비되었으면 읽기
                    data = ipc.read_data()
                    if data:
                        print(f"\n=== 인터럽트 데이터 수신 ===")
                        print(f"데이터 크기: {len(data)} 바이트")
                        print(f"데이터 (hex): {data.hex()}")
                        
                        # 패킷 구조 분석
                        if len(data) >= 9 and data[0:3] == b'\xff\x55\xaa':
                            cmd1 = (data[3] << 8) | data[4]
                            cmd2 = (data[5] << 8) | data[6]
                            data_len = (data[7] << 8) | data[8]
                            
                            print(f"CMD1: 0x{cmd1:04x}, CMD2: 0x{cmd2:04x}, Length: {data_len}")
                        
                        print("=" * 50)
                else:
                    print(".", end="", flush=True)  # 진행 표시
                
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단되었습니다.")
        except Exception as e:
            print(f"\n오류 발생: {e}")


def monitor_channel1_interrupt_efficient():
    """효율적인 인터럽트 방식 모니터링"""
    print("\n=== 효율적인 인터럽트 모니터링 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("CM1 디바이스 열기 실패")
            return
        
        print("효율적인 인터럽트 방식으로 데이터를 모니터링합니다...")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        try:
            packet_count = 0
            while True:
                # 인터럽트 방식으로 데이터 읽기 (무한 대기)
                data = ipc.read_data_with_interrupt(timeout_seconds=None)
                
                if data:
                    packet_count += 1
                    print(f"\n[패킷 {packet_count}] 인터럽트 수신: {len(data)} 바이트")
                    print(f"데이터: {data.hex()}")
                    
                    # 간단한 패킷 분석
                    if len(data) >= 3 and data[0:3] == b'\xff\x55\xaa':
                        print("✓ 유효한 IPC 패킷")
                    else:
                        print("⚠ 일반 데이터")
                
        except KeyboardInterrupt:
            print(f"\n모니터링 완료: {packet_count}개 패킷 수신")
        except Exception as e:
            print(f"\n오류 발생: {e}")


def test_interrupt_methods():
    """인터럽트 방식 테스트"""
    print("\n=== 인터럽트 방식 테스트 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("CM1 디바이스 열기 실패")
            return
        
        print("1. 논블로킹 읽기 테스트 (즉시 반환)")
        data = ipc.read_data_nonblocking()
        if data:
            print(f"   데이터 수신: {len(data)} 바이트")
        else:
            print("   데이터 없음")
        
        print("\n2. 인터럽트 대기 테스트 (20000초 타임아웃)")
        if ipc.wait_for_data_interrupt(20000.0):
            print("   데이터 준비됨")
            data = ipc.read_data()
            if data:
                print(f"   데이터 수신: {len(data)} 바이트")
        else:
            print("   타임아웃")
        
        print("\n3. 인터럽트 읽기 테스트 (2초 타임아웃)")
        data = ipc.read_data_with_interrupt(timeout_seconds=2.0)
        if data:
            print(f"   데이터 수신: {len(data)} 바이트")
        else:
            print("   타임아웃")


def continuous_interrupt_monitoring():
    """계속 인터럽트 방식으로 데이터를 받고 출력"""
    print("\n=== 계속 인터럽트 모니터링 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("CM1 디바이스 열기 실패")
            return
        
        print("계속 인터럽트 방식으로 데이터를 모니터링합니다...")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        packet_count = 0
        start_time = time.time()
        
        try:
            while True:
                # 인터럽트 방식으로 데이터 대기 (무한 대기)
                if ipc.wait_for_data_interrupt(None):  # None은 무한 대기
                    # 데이터가 준비되었으면 읽기
                    data = ipc.read_data()
                    if data:
                        packet_count += 1
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        
                        print(f"\n=== [패킷 {packet_count}] 인터럽트 수신 (경과: {elapsed_time:.1f}초) ===")
                        print(f"데이터 크기: {len(data)} 바이트")
                        print(f"데이터 (hex): {data.hex()}")
                        
                        # 패킷 구조 분석
                        if len(data) >= 9 and data[0:3] == b'\xff\x55\xaa':
                            cmd1 = (data[3] << 8) | data[4]
                            cmd2 = (data[5] << 8) | data[6]
                            data_len = (data[7] << 8) | data[8]
                            
                            print(f"✓ 유효한 IPC 패킷")
                            print(f"  CMD1: 0x{cmd1:04x}, CMD2: 0x{cmd2:04x}, Length: {data_len}")
                            
                            # 데이터 영역 출력 (첫 32바이트만)
                            if len(data) > 9:
                                payload = data[9:-2] if len(data) > 11 else data[9:]
                                if len(payload) > 32:
                                    print(f"  Payload (first 32 bytes): {payload[:32].hex()}")
                                else:
                                    print(f"  Payload: {payload.hex()}")
                            
                            # CRC 확인
                            if len(data) >= 11:
                                received_crc = (data[-2] << 8) | data[-1]
                                print(f"  CRC: 0x{received_crc:04x}")
                        else:
                            print("⚠ 일반 데이터 (IPC 패킷 아님)")
                        
                        print("=" * 60)
                
        except KeyboardInterrupt:
            print(f"\n모니터링 중단됨")
            print(f"총 {packet_count}개 패킷 수신")
            print(f"총 경과 시간: {time.time() - start_time:.1f}초")
        except Exception as e:
            print(f"\n오류 발생: {e}")
            print(f"총 {packet_count}개 패킷 수신")
            print(f"총 경과 시간: {time.time() - start_time:.1f}초")


def clean_interrupt_monitoring():
    """깨끗한 인터럽트 모니터링 (버퍼 클리어 후 읽기)"""
    print("\n=== 깨끗한 인터럽트 모니터링 ===")
    
    with AxonIPCDriver(AXON_IPC_CM1_FILE) as ipc:
        if not ipc.is_open:
            print("CM1 디바이스 열기 실패")
            return
        
        print("깨끗한 인터럽트 방식으로 데이터를 모니터링합니다...")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        packet_count = 0
        start_time = time.time()
        
        try:
            while True:
                # 깨끗한 데이터 읽기 (버퍼 클리어 후 새로운 데이터 대기)
                data = ipc.read_clean_data()
                
                if data:
                    packet_count += 1
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    
                    print(f"\n=== [패킷 {packet_count}] 깨끗한 데이터 수신 (경과: {elapsed_time:.1f}초) ===")
                    print(f"데이터 크기: {len(data)} 바이트")
                    print(f"데이터 (hex): {data.hex()}")
                    
                    # 패킷 구조 분석
                    if len(data) >= 9 and data[0:3] == b'\xff\x55\xaa':
                        cmd1 = (data[3] << 8) | data[4]
                        cmd2 = (data[5] << 8) | data[6]
                        data_len = (data[7] << 8) | data[8]
                        
                        print(f"✓ 유효한 IPC 패킷")
                        print(f"  CMD1: 0x{cmd1:04x}, CMD2: 0x{cmd2:04x}, Length: {data_len}")
                        
                        # 실제 데이터 추출 (헤더와 CRC 제외)
                        if len(data) > 9:
                            payload = data[9:-2] if len(data) > 11 else data[9:]
                            print(f"  실제 데이터: {payload.hex()}")
                            
                            # 원본 데이터와 비교
                            print(f"  보낸 데이터: 22 BE 2A 3E 85 0F 00 00 00 00 00")
                            print(f"  수신 데이터: {payload.hex()}")
                            
                            # 여러 패킷이 있을 경우 분리
                            ipc.parse_multiple_packets(data)
                        
                        # CRC 확인
                        if len(data) >= 11:
                            received_crc = (data[-2] << 8) | data[-1]
                            print(f"  CRC: 0x{received_crc:04x}")
                    else:
                        print("⚠ 일반 데이터 (IPC 패킷 아님)")
                    
                    print("=" * 60)
                
        except KeyboardInterrupt:
            print(f"\n모니터링 중단됨")
            print(f"총 {packet_count}개 패킷 수신")
            print(f"총 경과 시간: {time.time() - start_time:.1f}초")
        except Exception as e:
            print(f"\n오류 발생: {e}")
            print(f"총 {packet_count}개 패킷 수신")
            print(f"총 경과 시간: {time.time() - start_time:.1f}초")
