#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 생성 및 파싱 유틸리티 (C 코드와 동일한 패킷 구조)
"""

from crc_utils import calc_crc16


def make_packet(add_num: int, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
    """
    IPC 패킷 생성 (C 코드의 ipc_make_packet 함수와 동일)
    
    Args:
        add_num: 추가 번호
        ipc_cmd1: 명령어 1
        ipc_cmd2: 명령어 2
        data_length: 데이터 길이
        
    Returns:
        bytes: 생성된 패킷
    """
    packet_size = data_length + 11
    packet = bytearray(packet_size)
    
    # 헤더 설정 (C 코드와 동일)
    packet[0] = 0xFF
    packet[1] = 0x55
    packet[2] = 0xAA
    
    # 명령어 설정 (C 코드와 동일)
    packet[3] = (ipc_cmd1 >> 8) & 0xFF
    packet[4] = ipc_cmd1 & 0xFF
    packet[5] = (ipc_cmd2 >> 8) & 0xFF
    packet[6] = ipc_cmd2 & 0xFF
    packet[7] = (data_length >> 8) & 0xFF
    packet[8] = data_length & 0xFF
    
    # 데이터 영역 설정 (C 코드와 동일)
    for i in range(9, packet_size - 2):
        packet[i] = add_num + 1
    
    # CRC 계산 (C 코드와 동일)
    crc = calc_crc16(packet[:packet_size-2], 0)
    packet[packet_size-2] = (crc >> 8) & 0xFF
    packet[packet_size-1] = crc & 0xFF
    
    return bytes(packet)


def make_lpa_packet(ipc_buff: bytes, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
    """
    LPA 패킷 생성 (C 코드의 ipc_Lpa_packet 함수와 동일)
    
    Args:
        ipc_buff: IPC 버퍼 데이터
        ipc_cmd1: 명령어 1
        ipc_cmd2: 명령어 2
        data_length: 데이터 길이
        
    Returns:
        bytes: 생성된 패킷
    """
    packet_size = data_length + 11
    packet = bytearray(packet_size)
    
    # 헤더 설정 (C 코드와 동일)
    packet[0] = 0xFF
    packet[1] = 0x55
    packet[2] = 0xAA
    
    # 명령어 설정 (C 코드와 동일)
    packet[3] = (ipc_cmd1 >> 8) & 0xFF
    packet[4] = ipc_cmd1 & 0xFF
    packet[5] = (ipc_cmd2 >> 8) & 0xFF
    packet[6] = ipc_cmd2 & 0xFF
    packet[7] = (data_length >> 8) & 0xFF
    packet[8] = data_length & 0xFF
    
    # 데이터 영역 설정 (C 코드와 동일)
    for i in range(9, packet_size - 2):
        if i - 9 < len(ipc_buff):
            packet[i] = ipc_buff[i-9]
        else:
            packet[i] = 0  # 버퍼가 부족한 경우 0으로 채움
    
    # CRC 계산 (C 코드와 동일)
    crc = calc_crc16(packet[:packet_size-2], 0)
    packet[packet_size-2] = (crc >> 8) & 0xFF
    packet[packet_size-1] = crc & 0xFF
    
    return bytes(packet)


def parse_multiple_packets(data: bytes):
    """여러 IPC 패킷을 분리하여 개별 처리"""
    print(f"\n  === 여러 패킷 분석 ===")
    
    offset = 0
    packet_num = 0
    
    while offset < len(data):
        # IPC 헤더 찾기 (0xFF 0x55 0xAA)
        header_pos = data.find(b'\xff\x55\xaa', offset)
        if header_pos == -1:
            break
        
        # 헤더 위치로 이동
        offset = header_pos
        
        # 최소 패킷 크기 확인 (헤더 3바이트 + 명령어 6바이트 + CRC 2바이트 = 11바이트)
        if offset + 11 > len(data):
            break
        
        # 명령어와 데이터 길이 추출
        cmd1 = (data[offset + 3] << 8) | data[offset + 4]
        cmd2 = (data[offset + 5] << 8) | data[offset + 6]
        data_len = (data[offset + 7] << 8) | data[offset + 8]
        
        # 전체 패킷 크기 계산
        packet_size = 11 + data_len  # 헤더(3) + 명령어(6) + 데이터(data_len) + CRC(2)
        
        # 패킷이 완전한지 확인
        if offset + packet_size > len(data):
            break
        
        packet_num += 1
        print(f"  [패킷 {packet_num}]")
        print(f"    위치: {offset} ~ {offset + packet_size - 1}")
        print(f"    크기: {packet_size} 바이트")
        print(f"    CMD1: 0x{cmd1:04x}, CMD2: 0x{cmd2:04x}, Length: {data_len}")
        
        # 패킷 데이터 추출
        packet_data = data[offset:offset + packet_size]
        print(f"    전체 패킷: {packet_data.hex()}")
        
        # 실제 데이터 추출 (헤더와 CRC 제외)
        if data_len > 0:
            actual_data = packet_data[9:9 + data_len]
            print(f"    실제 데이터: {actual_data.hex()}")
            
            # 원본 데이터와 비교
            if actual_data == b'\x22\xbe\x2a\x3e\x85\x0f\x00\x00\x00\x00\x00':
                print(f"    ✓ 원본 데이터와 일치!")
            else:
                print(f"    ⚠ 원본 데이터와 다름")
        
        # CRC 확인
        if packet_size >= 11:
            received_crc = (packet_data[-2] << 8) | packet_data[-1]
            print(f"    CRC: 0x{received_crc:04x}")
        
        print()
        
        # 다음 패킷 위치로 이동
        offset += packet_size
    
    if packet_num == 0:
        print(f"  유효한 IPC 패킷을 찾을 수 없습니다.")
    else:
        print(f"  총 {packet_num}개의 IPC 패킷을 발견했습니다.")
