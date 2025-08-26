#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 Python 구현 (C 코드와 동일한 패킷 구조)
C 코드 axon-ipc-dev.c의 ipc_make_packet 함수를 정확히 구현
"""

import os
import time
import select
from typing import Optional

# IPC 디바이스 파일 경로
AXON_IPC_CM0_FILE = "/dev/axon_ipc_cm0"
AXON_IPC_CM1_FILE = "/dev/axon_ipc_cm1"
AXON_IPC_CM2_FILE = "/dev/axon_ipc_cm2"
AXON_IPC_CMN_FILE = "/dev/axon_ipc_cmn"

# IPC 명령어 상수 (C 코드에서 정의된 값들)
TCC_IPC_CMD_AP_TEST = 0x01
TCC_IPC_CMD_AP_SEND = 0x0fff

class AxonIPCDriver:
    """AXON IPC 드라이버 클래스 (C 코드와 동일한 패킷 구조)"""
    
    def __init__(self, device_path: str):
        """
        IPC 드라이버 초기화
        
        Args:
            device_path: IPC 디바이스 파일 경로
        """
        self.device_path = device_path
        self.fd = None
        self.is_open = False
        
    def check_device_exists(self) -> bool:
        """디바이스 파일이 존재하는지 확인"""
        return os.path.exists(self.device_path)
        
    def open_device(self) -> bool:
        """
        IPC 디바이스 열기
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 디바이스 파일 존재 확인
            if not self.check_device_exists():
                print(f"디바이스 파일이 존재하지 않습니다: {self.device_path}")
                return False
            
            print(f"디바이스 파일 열기 시도: {self.device_path}")
            
            # 디바이스 파일 열기 (읽기/쓰기 모드)
            self.fd = os.open(self.device_path, os.O_RDWR)
            print(f"파일 디스크립터 획득: {self.fd}")
            
            self.is_open = True
            print(f"IPC 디바이스 열기 성공: {self.device_path}, fd: {self.fd}")
            return True
            
        except Exception as e:
            print(f"IPC 디바이스 열기 실패: {e}")
            self.is_open = False
            return False
    
    def close_device(self) -> bool:
        """
        IPC 디바이스 닫기
        
        Returns:
            bool: 성공 여부
        """
        try:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
                self.is_open = False
                print(f"IPC 디바이스 닫기 성공: {self.device_path}")
                return True
        except Exception as e:
            print(f"IPC 디바이스 닫기 실패: {e}")
        return False
    
    def write_data(self, data: bytes) -> int:
        """
        IPC를 통해 데이터 쓰기
        
        Args:
            data: 쓸 데이터
            
        Returns:
            int: 쓴 바이트 수 (-1은 실패)
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return -1
                
            bytes_written = os.write(self.fd, data)
            print(f"데이터 쓰기 성공: {bytes_written} 바이트")
            return bytes_written
            
        except Exception as e:
            print(f"데이터 쓰기 실패: {e}")
            return -1
    
    def read_data(self, buffer_size: int = 512) -> Optional[bytes]:
        """
        IPC를 통해 데이터 읽기
        
        Args:
            buffer_size: 읽을 버퍼 크기
            
        Returns:
            bytes: 읽은 데이터 또는 None
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return None
                
            data = os.read(self.fd, buffer_size)
            print(f"데이터 읽기 성공: {len(data)} 바이트")
            return data
            
        except Exception as e:
            print(f"데이터 읽기 실패: {e}")
            return None
    
    def clear_buffer(self):
        """IPC 버퍼 클리어"""
        try:
            if not self.is_open:
                return
            
            # 버퍼에 남아있는 모든 데이터를 읽어서 버림
            while True:
                ready, _, _ = select.select([self.fd], [], [], 0)  # 즉시 반환
                if not ready:
                    break
                
                data = os.read(self.fd, 512)
                if not data:
                    break
                print(f"버퍼 클리어: {len(data)} 바이트 제거")
                
        except Exception as e:
            print(f"버퍼 클리어 실패: {e}")
    
    def read_clean_data(self, buffer_size: int = 512) -> Optional[bytes]:
        """
        깨끗한 데이터 읽기 (버퍼 클리어 후 읽기)
        
        Args:
            buffer_size: 읽을 버퍼 크기
            
        Returns:
            bytes: 읽은 데이터 또는 None
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return None
            
            # 먼저 버퍼 클리어
            self.clear_buffer()
            
            # 새로운 데이터 대기
            if self.wait_for_data_interrupt(5.0):  # 5초 타임아웃
                data = os.read(self.fd, buffer_size)
                if data:
                    print(f"깨끗한 데이터 읽기: {len(data)} 바이트")
                    return data
            
            return None
            
        except Exception as e:
            print(f"깨끗한 데이터 읽기 실패: {e}")
            return None
    
    def read_data_nonblocking(self, buffer_size: int = 512) -> Optional[bytes]:
        """
        논블로킹 방식으로 데이터 읽기 (인터럽트 대기)
        
        Args:
            buffer_size: 읽을 버퍼 크기
            
        Returns:
            bytes: 읽은 데이터 또는 None (데이터가 없으면 None)
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return None
            
            # select를 사용하여 데이터가 있는지 확인
            ready, _, _ = select.select([self.fd], [], [], 0)  # 0초 타임아웃 (즉시 반환)
            
            if ready:
                data = os.read(self.fd, buffer_size)
                if data:
                    print(f"데이터 읽기 (논블로킹): {len(data)} 바이트")
                    return data
            
            return None
            
        except Exception as e:
            print(f"논블로킹 데이터 읽기 실패: {e}")
            return None
    
    def wait_for_data_interrupt(self, timeout_seconds: float = None) -> bool:
        """
        인터럽트 방식으로 데이터 대기 (select 사용)
        
        Args:
            timeout_seconds: 타임아웃 (초), None은 무한 대기
            
        Returns:
            bool: 데이터가 준비되었으면 True, 타임아웃이면 False
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return False
            
            # select를 사용하여 데이터 대기
            ready, _, _ = select.select([self.fd], [], [], timeout_seconds)
            
            if ready:
                print("데이터가 준비되었습니다!")
                return True
            else:
                print("타임아웃: 데이터가 없습니다.")
                return False
                
        except Exception as e:
            print(f"인터럽트 대기 실패: {e}")
            return False
    
    def read_data_with_interrupt(self, buffer_size: int = 512, timeout_seconds: float = None) -> Optional[bytes]:
        """
        인터럽트 방식으로 데이터 읽기 (대기 후 읽기)
        
        Args:
            buffer_size: 읽을 버퍼 크기
            timeout_seconds: 타임아웃 (초), None은 무한 대기
            
        Returns:
            bytes: 읽은 데이터 또는 None
        """
        try:
            if not self.is_open:
                print("디바이스가 열려있지 않습니다.")
                return None
            
            # 먼저 데이터가 준비될 때까지 대기
            if self.wait_for_data_interrupt(timeout_seconds):
                # 데이터가 준비되었으면 읽기
                data = os.read(self.fd, buffer_size)
                if data:
                    print(f"인터럽트 데이터 읽기: {len(data)} 바이트")
                    return data
            
            return None
            
        except Exception as e:
            print(f"인터럽트 데이터 읽기 실패: {e}")
            return None
    
    def parse_multiple_packets(self, data: bytes):
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
    
    def calc_crc16(self, data: bytes, init: int) -> int:
        """
        CRC16 계산 (C 코드의 IPC_CalcCrc16 함수와 동일)
        
        Args:
            data: 데이터
            init: 초기값
            
        Returns:
            int: CRC16 값
        """
        crc_table = [
            0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
            0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
            0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
            0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
            0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
            0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
            0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
            0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
            0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
            0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
            0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
            0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
            0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
            0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
            0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
            0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
            0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
            0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
            0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
            0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
            0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
            0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
            0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
            0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
            0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
            0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
            0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
            0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
            0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
            0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
            0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
            0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
        ]
        
        crc_code = init
        
        for byte in data:
            temp = (((crc_code & 0xFF00) >> 8) ^ byte) & 0x00FF
            crc_code = (crc_table[temp] ^ ((crc_code & 0x00FF) << 8)) & 0xFFFF
        
        return crc_code
    
    def make_packet(self, add_num: int, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
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
        crc = self.calc_crc16(packet[:packet_size-2], 0)
        packet[packet_size-2] = (crc >> 8) & 0xFF
        packet[packet_size-1] = crc & 0xFF
        
        return bytes(packet)
    
    def make_lpa_packet(self, ipc_buff: bytes, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
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
        crc = self.calc_crc16(packet[:packet_size-2], 0)
        packet[packet_size-2] = (crc >> 8) & 0xFF
        packet[packet_size-1] = crc & 0xFF
        
        return bytes(packet)
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.open_device()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close_device()


def check_devices():
    """사용 가능한 IPC 디바이스 확인"""
    devices = [
        ("CM0", AXON_IPC_CM0_FILE),
        ("CM1", AXON_IPC_CM1_FILE),
        ("CM2", AXON_IPC_CM2_FILE),
        ("CMN", AXON_IPC_CMN_FILE)
    ]
    
    print("=== IPC 디바이스 상태 확인 ===")
    for name, path in devices:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    print(f"✓ {name}: {path} (접근 가능)")
            except PermissionError:
                print(f"✗ {name}: {path} (권한 없음)")
            except Exception as e:
                print(f"? {name}: {path} (기타 오류: {e})")
        else:
            print(f"✗ {name}: {path} (파일 없음)")


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

