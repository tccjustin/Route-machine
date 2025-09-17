#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AXON IPC 드라이버 상수 정의
"""

# IPC 디바이스 파일 경로
AXON_IPC_CM0_FILE = "/dev/axon_ipc_cm0"
AXON_IPC_CM1_FILE = "/dev/axon_ipc_cm1"
AXON_IPC_CM2_FILE = "/dev/axon_ipc_cm2"
AXON_IPC_CMN_FILE = "/dev/axon_ipc_cmn"

# IPC 명령어 상수 (C 코드에서 정의된 값들)
TCC_IPC_CMD_AP_TEST = 0x01
TCC_IPC_CMD_AP_SEND = 0x0fff
