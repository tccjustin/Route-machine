#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 Scapy 패킷 전송 스크립트
"""

from scapy.all import *
import subprocess
import re

def get_available_interfaces():
    """사용 가능한 네트워크 인터페이스 목록을 가져옴"""
    try:
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        interfaces = []
        for line in result.stdout.split('\n'):
            if ': ' in line and 'state' in line:
                # 인터페이스 이름 추출 (예: "2: eth0: <BROADCAST...")
                match = re.search(r'^\d+: (\w+):', line)
                if match:
                    interface_name = match.group(1)
                    # lo (loopback) 제외
                    if interface_name != 'lo':
                        interfaces.append(interface_name)
        return interfaces
    except Exception as e:
        print(f"인터페이스 목록을 가져오는 중 오류: {e}")
        return []

def send_packet():
    """지정된 소스와 목적지로 패킷 전송"""
    
    # 사용 가능한 인터페이스 확인
    available_interfaces = get_available_interfaces()
    print("사용 가능한 인터페이스:")
    for i, iface in enumerate(available_interfaces):
        print(f"  {i+1}. {iface}")
    
    # 인터페이스 선택 (fp_phy0을 우선으로 하되, 없으면 첫 번째 사용 가능한 것)
    preferred_interface = "fp_phy0"
    if preferred_interface in available_interfaces:
        interface = preferred_interface
    elif available_interfaces:
        interface = available_interfaces[0]
    else:
        print("사용 가능한 인터페이스가 없습니다!")
        return
    
    # 설정값
    source_ip = "100.1.1.1"
    source_mac = "00:00:00:00:11:11"
    dest_ip = "100.1.1.2"
    dest_mac = "00:00:00:00:22:22"
    
    print(f"\n패킷 전송 시작...")
    print(f"선택된 인터페이스: {interface}")
    print(f"소스: {source_ip} ({source_mac})")
    print(f"목적지: {dest_ip} ({dest_mac})")
    
    try:
        # 패킷 생성 및 전송
        packet = Ether(src=source_mac, dst=dest_mac) / \
                 IP(src=source_ip, dst=dest_ip) / \
                 ICMP() / \
                 Raw(b"Test packet")
        
        print(f"\n생성된 패킷:")
        packet.show()
        
        # 패킷 전송
        print(f"\n패킷을 {interface} 인터페이스로 전송 중...")
        sendp(packet, iface=interface, verbose=True)
        print("패킷 전송 완료!")
        
    except Exception as e:
        print(f"패킷 전송 중 오류 발생: {e}")
        print("다른 인터페이스를 시도해보세요.")

if __name__ == "__main__":
    send_packet()