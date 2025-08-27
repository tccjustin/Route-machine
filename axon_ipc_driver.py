#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 클래스 (C 코드와 동일한 패킷 구조)
"""

import os
import time
import select
import ctypes
import ctypes.util
from typing import Optional
from packet_utils import make_packet, parse_multiple_packets


class AxonIPCDriver:
    """AXON IPC 드라이버 클래스"""
    
    def __init__(self, device_path: str, can_id: int = 0x185, is_extended: bool = False):
        """
        초기화
        
        Args:
            device_path: IPC 디바이스 경로
            can_id: CAN ID (기본값: 0x185)
            is_extended: Extended ID 여부 (기본값: False = Standard ID)
        """
        self.device_path = device_path
        self.fd = None
        self.is_open = False
        self.can_id = can_id
        self.is_extended = is_extended
        
    def check_device_exists(self) -> bool:
        """디바이스 파일이 존재하는지 확인"""
        return os.path.exists(self.device_path)
        
    def open_device(self) -> bool:
        """
        IPC 디바이스 열기 (non-blocking 모드)
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 디바이스 파일 존재 확인
            if not self.check_device_exists():
                print(f"디바이스 파일이 존재하지 않습니다: {self.device_path}")
                return False
            
            print(f"디바이스 파일 열기 시도 (non-blocking): {self.device_path}")
            
            # 디바이스 파일 열기 (읽기/쓰기 모드 + non-blocking)
            self.fd = os.open(self.device_path, os.O_RDWR | os.O_NONBLOCK)
            print(f"파일 디스크립터 획득 (non-blocking): {self.fd}")
            
            self.is_open = True
            print(f"IPC 디바이스 열기 성공 (non-blocking): {self.device_path}, fd: {self.fd}")
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
    
    def reopen_device(self) -> bool:
        """
        디바이스 재연결 (닫고 다시 열기)
        
        Returns:
            bool: 성공 여부
        """
        print("디바이스 재연결을 시도합니다...")
        self.close_device()
        time.sleep(1.0) # 재시도 간 대기 시간 추가
        return self.open_device()
    
    def write_data(self, data: bytes) -> int:
        """
        IPC를 통해 데이터 쓰기
        
        Args:
            data: 쓸 데이터
            
        Returns:
            int: 쓴 바이트 수 (-1은 실패)
        """
        try:
            if not self.is_open or self.fd is None:
                print("디바이스가 열려있지 않습니다")
                return -1
            
            bytes_written = os.write(self.fd, data)
            print(f"데이터 쓰기 성공: {bytes_written} 바이트")
            return bytes_written
            
        except Exception as e:
            print(f"데이터 쓰기 실패: {e}")
            return -1
    
    def read_data(self, buffer_size: int = 512) -> Optional[bytes]:
        """
        IPC를 통해 데이터 읽기 (기본)
        
        Args:
            buffer_size: 읽을 버퍼 크기
            
        Returns:
            Optional[bytes]: 읽은 데이터 또는 None
        """
        try:
            if not self.is_open or self.fd is None:
                print("디바이스가 열려있지 않습니다")
                return None
            
            data = os.read(self.fd, buffer_size)
            if data:
                print(f"데이터 읽기 성공: {len(data)} 바이트")
                return data
            else:
                print("읽을 데이터가 없습니다")
                return None
                
        except BlockingIOError:
            # non-blocking 모드에서 데이터가 없는 경우
            return None
        except Exception as e:
            print(f"데이터 읽기 실패: {e}")
            return None
    
    def make_packet(self, seq_num: int, cmd1: int, cmd2: int, data_length: int) -> bytes:
        """C 코드와 동일한 패킷 생성"""
        return make_packet(seq_num, cmd1, cmd2, data_length)
    
    def parse_packets(self, data: bytes) -> list:
        """여러 패킷 파싱"""
        return parse_multiple_packets(data)
    
    def __enter__(self):
        """Context manager 진입"""
        self.open_device()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close_device()

    # ============================================================================
    # 리눅스 네이티브 시간 측정 함수들
    # ============================================================================

    def read_data_linux_native_timing(self, timeout_seconds: float = 5.0, buffer_size: int = 1024) -> tuple[Optional[bytes], dict]:
        """
        리눅스 네이티브 CLOCK_MONOTONIC을 사용한 시간 측정
        
        Args:
            timeout_seconds: 타임아웃 시간 (초)
            buffer_size: 버퍼 크기
            
        Returns:
            tuple: (데이터, 측정 통계)
        """
        # 리눅스 시스템 콜을 위한 라이브러리 로드
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        
        # CLOCK_MONOTONIC 정의
        CLOCK_MONOTONIC = 1
        
        # timespec 구조체 정의
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
        
        # clock_gettime 함수 정의
        clock_gettime = libc.clock_gettime
        clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        clock_gettime.restype = ctypes.c_int
        
        print(f"\n=== 리눅스 네이티브 타이밍 측정 (CLOCK_MONOTONIC) ===")
        print(f"타임아웃: {timeout_seconds}초, 버퍼 크기: {buffer_size}")
        
        try:
            if not self.is_open or self.fd is None:
                print("디바이스가 열려있지 않습니다")
                return None, {}
            
            # 측정 시작 시간
            start_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC, ctypes.byref(start_ts))
            start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
            
            print(f"측정 시작: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
            
            # 데이터 읽기 시도
            data = None
            read_start_ts = None
            read_end_ts = None
            
            end_time = time.time() + timeout_seconds
            
            while time.time() < end_time:
                try:
                    # 읽기 시작 시간
                    read_start_ts = timespec()
                    clock_gettime(CLOCK_MONOTONIC, ctypes.byref(read_start_ts))
                    
                    # 데이터 읽기
                    data = os.read(self.fd, buffer_size)
                    
                    # 읽기 종료 시간
                    read_end_ts = timespec()
                    clock_gettime(CLOCK_MONOTONIC, ctypes.byref(read_end_ts))
                    
                    if data:
                        break
                        
                except BlockingIOError:
                    # 데이터가 없으면 잠시 대기
                    time.sleep(0.001)
                    continue
                except Exception as e:
                    print(f"읽기 오류: {e}")
                    break
            
            # 측정 종료 시간
            end_ts = timespec()
            clock_gettime(CLOCK_MONOTONIC, ctypes.byref(end_ts))
            end_ns = end_ts.tv_sec * 1_000_000_000 + end_ts.tv_nsec
            
            # 통계 계산
            stats = {
                'total_time_ns': end_ns - start_ns,
                'total_time_ms': (end_ns - start_ns) / 1_000_000,
                'start_time': f"{start_ts.tv_sec}.{start_ts.tv_nsec:09d}",
                'end_time': f"{end_ts.tv_sec}.{end_ts.tv_nsec:09d}",
                'data_size': len(data) if data else 0,
                'success': data is not None
            }
            
            if read_start_ts and read_end_ts:
                read_start_ns = read_start_ts.tv_sec * 1_000_000_000 + read_start_ts.tv_nsec
                read_end_ns = read_end_ts.tv_sec * 1_000_000_000 + read_end_ts.tv_nsec
                stats['read_time_ns'] = read_end_ns - read_start_ns
                stats['read_time_ms'] = (read_end_ns - read_start_ns) / 1_000_000
            
            print(f"측정 완료: {end_ts.tv_sec}.{end_ts.tv_nsec:09d}")
            print(f"총 소요 시간: {stats['total_time_ms']:.3f}ms")
            if 'read_time_ms' in stats:
                print(f"읽기 시간: {stats['read_time_ms']:.3f}ms")
            print(f"데이터 크기: {stats['data_size']} 바이트")
            
            return data, stats
            
        except Exception as e:
            print(f"측정 중 오류 발생: {e}")
            return None, {}

    def read_data_linux_high_resolution(self, timeout_seconds: float = 5.0, buffer_size: int = 1024,
                                       measurement_rounds: int = 5) -> tuple[Optional[bytes], dict]:
        """
        리눅스 네이티브 CLOCK_MONOTONIC_RAW를 사용한 고해상도 시간 측정
        
        Args:
            timeout_seconds: 타임아웃 시간 (초)
            buffer_size: 버퍼 크기
            measurement_rounds: 측정 라운드 수
            
        Returns:
            tuple: (데이터, 측정 통계)
        """
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
        
        print(f"\n=== 리눅스 고해상도 타이밍 측정 (CLOCK_MONOTONIC_RAW) ===")
        print(f"타임아웃: {timeout_seconds}초, 버퍼 크기: {buffer_size}, 측정 라운드: {measurement_rounds}")
        
        try:
            if not self.is_open or self.fd is None:
                print("디바이스가 열려있지 않습니다")
                return None, {}
            
            measurements = []
            final_data = None
            
            for round_num in range(measurement_rounds):
                print(f"\n--- 측정 라운드 {round_num + 1}/{measurement_rounds} ---")
                
                # 측정 시작 시간
                start_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(start_ts))
                start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
                
                # 데이터 읽기 시도
                data = None
                read_start_ts = None
                read_end_ts = None
                
                end_time = time.time() + timeout_seconds
                
                while time.time() < end_time:
                    try:
                        # 읽기 시작 시간
                        read_start_ts = timespec()
                        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(read_start_ts))
                        
                        # 데이터 읽기
                        data = os.read(self.fd, buffer_size)
                        
                        # 읽기 종료 시간
                        read_end_ts = timespec()
                        clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(read_end_ts))
                        
                        if data:
                            final_data = data
                            break
                            
                    except BlockingIOError:
                        time.sleep(0.001)
                        continue
                    except Exception as e:
                        print(f"읽기 오류: {e}")
                        break
                
                # 측정 종료 시간
                end_ts = timespec()
                clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.byref(end_ts))
                end_ns = end_ts.tv_sec * 1_000_000_000 + end_ts.tv_nsec
                
                # 라운드 통계
                round_stats = {
                    'round': round_num + 1,
                    'total_time_ns': end_ns - start_ns,
                    'total_time_ms': (end_ns - start_ns) / 1_000_000,
                    'success': data is not None
                }
                
                if read_start_ts and read_end_ts:
                    read_start_ns = read_start_ts.tv_sec * 1_000_000_000 + read_start_ts.tv_nsec
                    read_end_ns = read_end_ts.tv_sec * 1_000_000_000 + read_end_ts.tv_nsec
                    round_stats['read_time_ns'] = read_end_ns - read_start_ns
                    round_stats['read_time_ms'] = (read_end_ns - read_start_ns) / 1_000_000
                
                measurements.append(round_stats)
                print(f"라운드 {round_num + 1} 완료: {round_stats['total_time_ms']:.3f}ms")
                
                if data:
                    break  # 데이터를 읽었으면 다음 라운드로
            
            # 전체 통계 계산
            total_times = [m['total_time_ms'] for m in measurements]
            read_times = [m.get('read_time_ms', 0) for m in measurements if 'read_time_ms' in m]
            
            stats = {
                'measurement_rounds': measurement_rounds,
                'successful_rounds': len([m for m in measurements if m['success']]),
                'avg_total_time_ms': sum(total_times) / len(total_times) if total_times else 0,
                'min_total_time_ms': min(total_times) if total_times else 0,
                'max_total_time_ms': max(total_times) if total_times else 0,
                'avg_read_time_ms': sum(read_times) / len(read_times) if read_times else 0,
                'min_read_time_ms': min(read_times) if read_times else 0,
                'max_read_time_ms': max(read_times) if read_times else 0,
                'data_size': len(final_data) if final_data else 0,
                'measurements': measurements
            }
            
            print(f"\n=== 측정 결과 요약 ===")
            print(f"성공한 라운드: {stats['successful_rounds']}/{measurement_rounds}")
            print(f"평균 총 시간: {stats['avg_total_time_ms']:.3f}ms")
            print(f"평균 읽기 시간: {stats['avg_read_time_ms']:.3f}ms")
            print(f"데이터 크기: {stats['data_size']} 바이트")
            
            return final_data, stats
            
        except Exception as e:
            print(f"측정 중 오류 발생: {e}")
            return None, {}

    def read_data_linux_realtime(self, timeout_seconds: float = 5.0, buffer_size: int = 1024) -> tuple[Optional[bytes], dict]:
        """
        리눅스 네이티브 CLOCK_REALTIME을 사용한 실시간 시간 측정
        
        Args:
            timeout_seconds: 타임아웃 시간 (초)
            buffer_size: 버퍼 크기
            
        Returns:
            tuple: (데이터, 측정 통계)
        """
        # 리눅스 시스템 콜을 위한 라이브러리 로드
        libc = ctypes.CDLL(ctypes.util.find_library('c'))
        
        # CLOCK_REALTIME 정의
        CLOCK_REALTIME = 0
        
        # timespec 구조체 정의
        class timespec(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]
        
        # clock_gettime 함수 정의
        clock_gettime = libc.clock_gettime
        clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        clock_gettime.restype = ctypes.c_int
        
        print(f"\n=== 리눅스 실시간 타이밍 측정 (CLOCK_REALTIME) ===")
        print(f"타임아웃: {timeout_seconds}초, 버퍼 크기: {buffer_size}")
        
        try:
            if not self.is_open or self.fd is None:
                print("디바이스가 열려있지 않습니다")
                return None, {}
            
            # 측정 시작 시간
            start_ts = timespec()
            clock_gettime(CLOCK_REALTIME, ctypes.byref(start_ts))
            start_ns = start_ts.tv_sec * 1_000_000_000 + start_ts.tv_nsec
            
            print(f"측정 시작: {start_ts.tv_sec}.{start_ts.tv_nsec:09d}")
            
            # 데이터 읽기 시도
            data = None
            read_start_ts = None
            read_end_ts = None
            
            end_time = time.time() + timeout_seconds
            
            while time.time() < end_time:
                try:
                    # 읽기 시작 시간
                    read_start_ts = timespec()
                    clock_gettime(CLOCK_REALTIME, ctypes.byref(read_start_ts))
                    
                    # 데이터 읽기
                    data = os.read(self.fd, buffer_size)
                    
                    # 읽기 종료 시간
                    read_end_ts = timespec()
                    clock_gettime(CLOCK_REALTIME, ctypes.byref(read_end_ts))
                    
                    if data:
                        break
                        
                except BlockingIOError:
                    time.sleep(0.001)
                    continue
                except Exception as e:
                    print(f"읽기 오류: {e}")
                    break
            
            # 측정 종료 시간
            end_ts = timespec()
            clock_gettime(CLOCK_REALTIME, ctypes.byref(end_ts))
            end_ns = end_ts.tv_sec * 1_000_000_000 + end_ts.tv_nsec
            
            # 통계 계산
            stats = {
                'total_time_ns': end_ns - start_ns,
                'total_time_ms': (end_ns - start_ns) / 1_000_000,
                'start_time': f"{start_ts.tv_sec}.{start_ts.tv_nsec:09d}",
                'end_time': f"{end_ts.tv_sec}.{end_ts.tv_nsec:09d}",
                'data_size': len(data) if data else 0,
                'success': data is not None
            }
            
            if read_start_ts and read_end_ts:
                read_start_ns = read_start_ts.tv_sec * 1_000_000_000 + read_start_ts.tv_nsec
                read_end_ns = read_end_ts.tv_sec * 1_000_000_000 + read_end_ts.tv_nsec
                stats['read_time_ns'] = read_end_ns - read_start_ns
                stats['read_time_ms'] = (read_end_ns - read_start_ns) / 1_000_000
            
            print(f"측정 완료: {end_ts.tv_sec}.{end_ts.tv_nsec:09d}")
            print(f"총 소요 시간: {stats['total_time_ms']:.3f}ms")
            if 'read_time_ms' in stats:
                print(f"읽기 시간: {stats['read_time_ms']:.3f}ms")
            print(f"데이터 크기: {stats['data_size']} 바이트")
            
            return data, stats
            
        except Exception as e:
            print(f"측정 중 오류 발생: {e}")
            return None, {}
