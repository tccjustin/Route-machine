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

    if uCAN_ID > 0x7FF:
        uIDE = 1
    else:
        uIDE = 0

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
#    if len(data) > 8:
#        raise ValueError("CAN 데이터는 최대 8바이트여야 합니다")
    
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


def parse_lpa_packet_with_can_header(packet_data: bytes):
    """
    make_lpa_packet_with_can_header로 생성된 패킷을 파싱하여 실제 payload 추출
    
    Args:
        packet_data: 수신된 패킷 데이터
        
    Returns:
        dict: 파싱된 정보
        {
            'valid': bool,           # 패킷 유효성
            'cmd': int,              # IPC 명령어
            'port': int,             # 포트 번호
            'can_header': bytes,     # CAN 헤더 (5바이트)
            'payload': bytes,        # 실제 CAN 데이터 (payload)
            'crc': int,              # CRC 값
            'crc_valid': bool        # CRC 검증 결과
        }
    """
    result = {
        'valid': False,
        'cmd': 0,
        'port': 0,
        'can_header': b'',
        'payload': b'',
        'crc': 0,
        'crc_valid': False
    }
    
    # 최소 패킷 크기 확인 (IPC 헤더 3 + 명령어 4 + 데이터길이 2 + CAN헤더 5 + CRC 2 = 16바이트)
    # 최소 패킷 크기 확인 (IPC 헤더 3 + 명령어 4 + 데이터길이 2 + Timestamp 15 바이트 + CAN헤더 5 + CRC 2 = 16바이트)


    if len(packet_data) < 16:
        return result
    
    # IPC 헤더 확인 (0xFF 0x55 0xAA)
    if packet_data[0:3] != b'\xff\x55\xaa':
        return result
    
    # 명령어와 포트 추출
    cmd = (packet_data[3] << 8) | packet_data[4]
    port = (packet_data[5] << 8) | packet_data[6]
    data_length = (packet_data[7] << 8) | packet_data[8]
    
    # 전체 패킷 크기 확인
    expected_packet_size = 11 + data_length  # 헤더(3) + 명령어(4) + 데이터길이(2) + 데이터(data_length) + CRC(2)
    if len(packet_data) < expected_packet_size:
        return result
    
    # CAN 헤더 추출 (5바이트)
    can_header = packet_data[9:24]

    
    # 실제 payload 추출 (CAN 헤더 이후부터 CRC 이전까지)
    payload_length = data_length - 15   # 전체 데이터 길이에서 CAN 헤더(5바이트) 제외
    if payload_length > 0:
        payload = packet_data[24:24 + payload_length]
    else:
        payload = b''
    
    # CRC 추출 및 검증
    received_crc = (packet_data[-2] << 8) | packet_data[-1]
    calculated_crc = calc_crc16(packet_data[:-2], 0)
    crc_valid = (received_crc == calculated_crc)
    
    result.update({
        'valid': True,
        'cmd': cmd,
        'port': port,
        'can_header': can_header,
        'payload': payload,
        'crc': received_crc,
        'crc_valid': crc_valid
    })
    
    return result


def parse_can_header(buffer: bytes):
    """
    수신 프레임 헤더(15바이트)를 파싱하여 수신 정보 추출
    
    Args:
        buffer: 15바이트 수신 프레임 헤더
        
    Returns:
        dict: 수신 프레임 정보
        {
            'frame_type': int,           # 프레임 타입 (0 또는 1)
            'source_port': int,          # 소스 포트 번호
            'timestamp_ns': int,         # 나노초 타임스탬프
            'timestamp_us_l': int,       # 마이크로초 타임스탬프 (하위 32비트)
            'timestamp_us_h': int,       # 마이크로초 타임스탬프 (상위 32비트)
            'protocol_type': int,        # 프로토콜 타입 (0 또는 1)
            'can_id': int,              # CAN ID (Standard)
            'lin_id': int,              # LIN ID
            'ext_can_id': int,          # Extended CAN ID
            'fdf': int,                 # FDF 비트 (0 또는 1)
            'rtr': int,                 # RTR 비트 (0 또는 1)
            'ide': int,                 # IDE 비트 (0 또는 1)
            'is_extended': bool,        # Extended ID 여부
            'is_fd': bool,             # CAN FD 여부
            'is_remote': bool           # RTR 여부
        }
    """
    result = {
        'frame_type': 0,
        'source_port': 0,
        'timestamp_ns': 0,
        'timestamp_us_l': 0,
        'timestamp_us_h': 0,
        'protocol_type': 0,
        'can_id': 0,
        'lin_id': 0,
        'ext_can_id': 0,
        'fdf': 0,
        'rtr': 0,
        'ide': 0,
        'is_extended': False,
        'is_fd': False,
        'is_remote': False
    }
    
    if len(buffer) < 15:
        return result
    
    # C 코드와 동일한 비트 연산으로 파싱
    # rx_frame_type = buffer[0] & 0x01U;
    result['frame_type'] = buffer[0] & 0x01
    
    # rx_sourcePort = ((buffer[0] & 0xFEU) >> 1U) + ((buffer[1] & 0x01U) << 7U);
    result['source_port'] = ((buffer[0] & 0xFE) >> 1) + ((buffer[1] & 0x01) << 7)
    
    # rx_timeStamp_ns = (((uint16)buffer[1] & 0xFEU) >> 1U);
    # rx_timeStamp_ns |= (((uint16)buffer[2] & 0x01U) << 7U);
    # rx_timeStamp_ns *= 10U;
    result['timestamp_ns'] = (((buffer[1] & 0xFE) >> 1) | ((buffer[2] & 0x01) << 7)) * 10
    
    # rx_timeStamp_us_L = ((uint32)buffer[2] >> 1U);
    # rx_timeStamp_us_L |= ((uint32)buffer[3] << 7U);
    # rx_timeStamp_us_L |= ((uint32)buffer[4] << 15U);
    # rx_timeStamp_us_L |= ((uint32)buffer[5] << 23U);
    # rx_timeStamp_us_L |= (((uint32)buffer[6] & 0x01U) << 31U);
    result['timestamp_us_l'] = ((buffer[2] >> 1) | 
                               (buffer[3] << 7) | 
                               (buffer[4] << 15) | 
                               (buffer[5] << 23) | 
                               ((buffer[6] & 0x01) << 31))
    
    # rx_timeStamp_us_H = ((uint32)buffer[6] >> 1U);
    # rx_timeStamp_us_H |= ((uint32)buffer[7] << 7U);
    # rx_timeStamp_us_H |= ((uint32)buffer[8] << 15U);
    # rx_timeStamp_us_H |= ((uint32)buffer[9] << 23U);
    # rx_timeStamp_us_H |= (((uint32)buffer[10] & 0x01U) << 31U);
    result['timestamp_us_h'] = ((buffer[6] >> 1) | 
                               (buffer[7] << 7) | 
                               (buffer[8] << 15) | 
                               (buffer[9] << 23) | 
                               ((buffer[10] & 0x01) << 31))
    
    # rx_protocol_type = ((buffer[10] & 0x80U) == 0x80U)?1U:0U;
    result['protocol_type'] = 1 if (buffer[10] & 0x80) == 0x80 else 0
    
    # rx_can_id = lpa_u16add((uint16)buffer[11], ((uint16)buffer[12] & 0x07U) << 8U);
    result['can_id'] = buffer[11] + ((buffer[12] & 0x07) << 8)
    
    # rx_lin_id = (uint16)buffer[11] & 0x3FU;
    result['lin_id'] = buffer[11] & 0x3F
    
    # rx_extCan_id = (uint32)buffer[11];
    # rx_extCan_id |= ((uint32)buffer[12] << 8U);
    # rx_extCan_id |= ((uint32)buffer[13] << 16U);
    # rx_extCan_id |= (((uint32)buffer[14] & 0x1FU) << 24U);
    result['ext_can_id'] = (buffer[11] | 
                           (buffer[12] << 8) | 
                           (buffer[13] << 16) | 
                           ((buffer[14] & 0x1F) << 24))
    
    # rx_fdf = ((buffer[14] & 0x20U) == 0x20U)?1U:0U;
    result['fdf'] = 1 if (buffer[14] & 0x20) == 0x20 else 0
    
    # rx_rtr = ((buffer[14] & 0x40U) == 0x40U)?1U:0U;
    result['rtr'] = 1 if (buffer[14] & 0x40) == 0x40 else 0
    
    # rx_ide = ((buffer[14] & 0x80U) == 0x80U)?1U:0U;
    result['ide'] = 1 if (buffer[14] & 0x80) == 0x80 else 0
    
    # 편의를 위한 boolean 값들
    result['is_extended'] = bool(result['ide'])
    result['is_fd'] = bool(result['fdf'])
    result['is_remote'] = bool(result['rtr'])
    
    return result


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
        
        # LPA 패킷 파싱 시도
        parsed = parse_lpa_packet_with_can_header(packet_data)
        if parsed['valid']:
            print(f"    ✓ LPA 패킷 파싱 성공!")
            print(f"    CMD: 0x{parsed['cmd']:04x}, Port: {parsed['port']}")
            print(f"    CAN 헤더: {parsed['can_header'].hex()}")
            print(f"    Payload: {parsed['payload'].hex()}")
            print(f"    CRC: 0x{parsed['crc']:04x} ({'유효' if parsed['crc_valid'] else '무효'})")
            
            # CAN 헤더 상세 파싱
            can_info = parse_can_header(parsed['can_header'])
            print(f"    CAN ID: 0x{can_info['can_id']:X} ({'Extended' if can_info['is_extended'] else 'Standard'})")
            print(f"    CAN FD: {can_info['is_fd']}, RTR: {can_info['rtr']}, BRS: {can_info['brs']}")
        else:
            # 기존 방식으로 파싱
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
