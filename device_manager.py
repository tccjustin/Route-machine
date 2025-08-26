#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
디바이스 관리 유틸리티
"""

import os
from constants import AXON_IPC_CM0_FILE, AXON_IPC_CM1_FILE, AXON_IPC_CM2_FILE, AXON_IPC_CMN_FILE


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
