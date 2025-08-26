#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 클래스 (C 코드와 동일한 패킷 구조)
"""

import os
import time
import select
from typing import Optional
from packet_utils import make_packet, make_lpa_packet, parse_multiple_packets


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
    
    def make_packet(self, add_num: int, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
        """IPC 패킷 생성 (packet_utils의 함수 호출)"""
        return make_packet(add_num, ipc_cmd1, ipc_cmd2, data_length)
    
    def make_lpa_packet(self, ipc_buff: bytes, ipc_cmd1: int, ipc_cmd2: int, data_length: int) -> bytes:
        """LPA 패킷 생성 (packet_utils의 함수 호출)"""
        return make_lpa_packet(ipc_buff, ipc_cmd1, ipc_cmd2, data_length)
    
    def parse_multiple_packets(self, data: bytes):
        """여러 IPC 패킷을 분리하여 개별 처리 (packet_utils의 함수 호출)"""
        parse_multiple_packets(data)
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.open_device()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close_device()
