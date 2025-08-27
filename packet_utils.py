#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패킷 생성 및 파싱 유틸리티 (C 코드와 동일한 패킷 구조)
"""

from crc_utils import calc_crc16
from typing import ByteString


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


# C 매크로 그대로의 비트 연산 (필요한 부분만)
def TIMESTAMP(x: int) -> int:   return (x & 0x1)
def PROTOCOL(x: int) -> int:    return ((x & 0x1) << 6)
def CANEXTID(x: int) -> int:    return ((x & 0x1FFFFFFF) << 7)   # 29-bit
def CANID(x: int) -> int:       return ((x & 0x7FF) << 7)        # 11-bit
def FDF(x: int) -> int:         return ((x & 0x1) << 36)
def RTR(x: int) -> int:         return ((x & 0x1) << 37)
def IDE(x: int) -> int:         return ((x & 0x1) << 38)
def BRS(x: int) -> int:         return ((x & 0x1) << 39)

def build_CANHeader_py(timestamp_onoff: int,uCAN_ID: int, uFDF: int, uIDE: int, uBRS: int,) -> bytes:
    """
    C의 build_CANHeader와 동일한 규칙으로 5바이트 CAN 헤더를 생성하여 리턴.
    반환 바이트 순서는 리틀엔디언(LSB first)로 C 코드와 동일.
    """
    can_header_frame = 0

    if uIDE == 1:  # Extended ID
        if uFDF == 1:  # CAN FD
            can_header_frame = TIMESTAMP(timestamp_onoff) + PROTOCOL(0) + CANEXTID(uCAN_ID) + FDF(1)  + RTR(0) + IDE(1) + BRS(uBRS)
        else:  # classic CAN
            can_header_frame = TIMESTAMP(timestamp_onoff) + PROTOCOL(0) + CANEXTID(uCAN_ID) + FDF(0)  + RTR(0) + IDE(1) + BRS(0)
            
    else:  # Standard ID
        if uFDF == 1:  # CAN FD
            can_header_frame = TIMESTAMP(timestamp_onoff) + PROTOCOL(0) + CANEXTID(uCAN_ID) + FDF(1)  + RTR(0) + IDE(0) + BRS(uBRS)
            
        else:  # classic CAN
            can_header_frame = TIMESTAMP(timestamp_onoff) + PROTOCOL(0) + CANID(uCAN_ID) + FDF(0)  + RTR(0) + IDE(0) + BRS(0)

    # 하위 5바이트만 사용 (C 코드에서 5바이트를 버퍼에 기록)
    return can_header_frame.to_bytes(5, byteorder="little", signed=False)


def build_can_header(can_id: int, is_extended: bool = False, is_fd: bool = False, brs: bool = False) -> bytes:
    """
    C 코드의 build_CANHeader 함수를 Python으로 구현
    
    Args:
        can_id: CAN ID
        is_extended: Extended ID 여부 (False = Standard ID)
        is_fd: CAN FD 여부 (False = Classic CAN)
        brs: Bit Rate Switch (CAN FD에서만 사용)
        
    Returns:
        bytes: 5바이트 CAN 헤더
    """
    # C 코드의 매크로 상수들 (실제 값은 헤더 파일에서 정의됨)
    TIMESTAMP_ON = 1
    PROTOCOL_CAN = 0
    FDF_OFF = 0
    FDF_ON = 1
    RTR_OFF = 0
    IDE_STANDARD = 0
    IDE_EXTENDED = 1
    BRS_OFF = 0
    BRS_ON = 1
    
    # 64비트 헤더 프레임 구성
    can_header_frame = 0
    
    # Timestamp 비트 (C 코드의 TIMESTAMP 매크로)
    can_header_frame |= (TIMESTAMP_ON << 60)
    
    # Protocol 비트 (C 코드의 PROTOCOL 매크로)
    can_header_frame |= (PROTOCOL_CAN << 56)
    
    if is_extended:
        # Extended ID (29비트)
        can_header_frame |= ((can_id & 0x1FFFFFFF) << 27)
        # FDF 비트
        can_header_frame |= (FDF_ON if is_fd else FDF_OFF) << 26
        # RTR 비트
        can_header_frame |= RTR_OFF << 25
        # IDE 비트
        can_header_frame |= IDE_EXTENDED << 24
        # BRS 비트 (CAN FD에서만 사용)
        if is_fd:
            can_header_frame |= (BRS_ON if brs else BRS_OFF) << 23
    else:
        # Standard ID (11비트) - 비트 위치 수정
        can_header_frame |= ((can_id & 0x7FF) << 37)  # 37번 비트부터 시작
        # FDF 비트
        can_header_frame |= (FDF_ON if is_fd else FDF_OFF) << 36
        # RTR 비트
        can_header_frame |= RTR_OFF << 35
        # IDE 비트
        can_header_frame |= IDE_STANDARD << 34
        # BRS 비트 (CAN FD에서만 사용)
        if is_fd:
            can_header_frame |= (BRS_ON if brs else BRS_OFF) << 33
    
    print(f"CAN 헤더: {can_header_frame}")

    # 5바이트로 변환 (C 코드와 동일)
    header = bytearray(5)
    header[0] = (can_header_frame & 0x00000000FF) >> 0
    header[1] = (can_header_frame & 0x000000FF00) >> 8
    header[2] = (can_header_frame & 0x0000FF0000) >> 16
    header[3] = (can_header_frame & 0x00FF000000) >> 24
    header[4] = (can_header_frame & 0xFF00000000) >> 32
    
    return bytes(header)


def make_lpa_packet_with_can_header(data: bytes, can_id: int, is_extended: bool = False, 
                                   cmd: int = 0x0101, port: int = 6) -> bytes:
    """
    C 코드의 LPA_msg 함수와 동일한 방식으로 CAN 헤더를 포함한 LPA 패킷 생성
    
    Args:
        data: CAN 데이터 (최대 8바이트)
        can_id: CAN ID
        is_extended: Extended ID 여부
        cmd: IPC 명령어
        port: 포트 번호
        
    Returns:
        bytes: 생성된 LPA 패킷
    """
    if len(data) > 8:
        raise ValueError("CAN 데이터는 최대 8바이트여야 합니다")
    
    # CAN 헤더 생성 (5바이트)
    # can_header = build_can_header(can_id, is_extended)
    can_header = build_CANHeader_py(0, can_id, 0, 0, 0)
    print(f"CAN 헤더: {can_header.hex()}")
    
    # LPA_TX_HDR_SIZE = 5 (CAN 헤더 크기)
    lpa_tx_hdr_size = 5
    
    # 전체 데이터 길이 계산
    total_data_length = lpa_tx_hdr_size + len(data)
    
    # IPC 패킷 생성
    packet_size = total_data_length + 11  # 헤더(3) + 명령어(6) + 데이터 + CRC(2)
    packet = bytearray(packet_size)
    
    # IPC 헤더 설정
    packet[0] = 0xFF
    packet[1] = 0x55
    packet[2] = 0xAA
    
    # 명령어 설정
    packet[3] = (cmd >> 8) & 0xFF
    packet[4] = cmd & 0xFF
    packet[5] = (port >> 8) & 0xFF
    packet[6] = port & 0xFF
    packet[7] = (total_data_length >> 8) & 0xFF
    packet[8] = total_data_length & 0xFF
    
    # CAN 헤더 복사 (C 코드의 memcpy와 동일)
    packet[9:9+lpa_tx_hdr_size] = can_header
    
    # CAN 데이터 복사 (C 코드의 memcpy와 동일)
    packet[9+lpa_tx_hdr_size:9+lpa_tx_hdr_size+len(data)] = data
    
    # 나머지 영역을 0으로 채움
    for i in range(9+lpa_tx_hdr_size+len(data), packet_size-2):
        packet[i] = 0
    
    # CRC 계산
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
